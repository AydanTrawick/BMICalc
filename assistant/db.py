"""Exact supplied tables; parameterized, owner-scoped SQL, with no DDL.

One locked cached connection serializes transactions safely. Only establishing a
connection is retried; uncertain writes are retried via durable operation receipts.
"""
from contextlib import contextmanager
from datetime import date, datetime
import hashlib
import json
import logging
import threading
import time

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
import streamlit as st

from assistant.config import AssistantError, secret_key

logger = logging.getLogger(__name__)


def plain(value):
    return json.loads(json.dumps(value, default=lambda item: item.isoformat() if isinstance(item, (date, datetime)) else str(item)))


class ConnectionStore:
    def __init__(self, url):
        self.url, self.connection = url, None
        self.lock = threading.RLock()

    def connect(self):
        for attempt in range(2):
            try:
                if self.connection is not None and not self.connection.closed:
                    self.connection.execute('SELECT 1')
                    return self.connection
                self.connection = psycopg.connect(self.url, sslmode='require', connect_timeout=10,
                                                   autocommit=True, row_factory=dict_row)
                return self.connection
            except psycopg.Error:
                logger.exception('Assistant database connection failed (attempt %s)', attempt + 1)
                self.close()
                if attempt == 0:
                    time.sleep(.25)
        raise AssistantError('Could not connect to your saved activities after a retry. Please try again.')

    def close(self):
        if self.connection is not None:
            self.connection.close()
        self.connection = None


@st.cache_resource(show_spinner=False)
def connection_store(url):
    return ConnectionStore(url)


@contextmanager
def transaction(user_id):
    if not isinstance(user_id, str) or not user_id:
        raise AssistantError('Sign in to read or change your saved activities.')
    url = secret_key('NEON_DATABASE_URL')
    if not url:
        raise AssistantError('Add NEON_DATABASE_URL to Streamlit secrets to enable saved activities.')
    store = connection_store(url)
    with store.lock:
        try:
            connection = store.connect()
            with connection.transaction():
                connection.execute("SET LOCAL statement_timeout = '15s'")
                connection.execute("SET LOCAL lock_timeout = '10s'")
                yield connection
        except psycopg.Error:
            logger.exception('Assistant database transaction failed')
            store.close()
            raise AssistantError('Could not confirm the database operation. Check that the three assistant tables exist and try again. Retrying the same confirmation will not duplicate a saved entry.') from None


def get_logs(user_id, start_date, end_date, log_type=None, exercise_filter=None, limit=500):
    with transaction(user_id) as conn:
        rows = conn.execute('''SELECT id, log_date, log_type, details, source, notes, updated_at
            FROM public.activity_logs WHERE user_id = %s AND deleted_at IS NULL
            AND log_date BETWEEN %s AND %s AND (%s::text IS NULL OR log_type = %s)
            AND (%s::text IS NULL OR details->>'exercise' ILIKE %s)
            ORDER BY log_date DESC, id DESC LIMIT %s''',
            (user_id, start_date, end_date, log_type, log_type, exercise_filter,
             '%' + exercise_filter.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%' if exercise_filter else None, limit + 1)).fetchall()
    return {'entries': plain(rows[:limit]), 'truncated': len(rows) > limit}


def get_entry(user_id, entry_id):
    with transaction(user_id) as conn:
        row = conn.execute('''SELECT id, log_date, log_type, details, source, notes, updated_at
            FROM public.activity_logs WHERE user_id = %s AND deleted_at IS NULL AND id = %s''', (user_id, entry_id)).fetchone()
    if not row:
        raise AssistantError('That active entry was not found in your account.')
    return plain(row)


def get_active_plan(user_id, plan_type):
    with transaction(user_id) as conn:
        row = conn.execute('''SELECT id, plan_type, title, plan_data, updated_at
            FROM public.user_plans WHERE user_id = %s AND plan_type = %s AND is_active = TRUE
            ORDER BY updated_at DESC NULLS LAST, id DESC LIMIT 1''', (user_id, plan_type)).fetchone()
    return plain(row) if row else None


def load_messages(user_id):
    with transaction(user_id) as conn:
        rows = conn.execute('''SELECT id, role, content, tool_calls FROM public.assistant_messages
            WHERE user_id = %s AND COALESCE(tool_calls->>'kind', '') NOT IN ('receipt', 'clear')
            AND id > COALESCE((SELECT MAX(id) FROM public.assistant_messages
                WHERE user_id = %s AND tool_calls->>'kind' = 'clear'), 0)
            ORDER BY id DESC LIMIT 20''', (user_id, user_id)).fetchall()
    return list(reversed(plain(rows)))


def save_message(user_id, role, content, tool_calls=None):
    if role not in ('user', 'assistant'):
        raise AssistantError('Invalid conversation role.')
    with transaction(user_id) as conn:
        row = conn.execute('''INSERT INTO public.assistant_messages
            (user_id, role, content, tool_calls, created_at) VALUES (%s, %s, %s, %s, NOW()) RETURNING id''',
            (user_id, role, content, Jsonb(plain(tool_calls)) if tool_calls is not None else None)).fetchone()
    return row['id']


def clear_conversation(user_id):
    # Preserve the audit trail without deleting messages; future history starts here.
    return save_message(user_id, 'assistant', 'Conversation cleared.', {'kind': 'clear'})


def operation_result(user_id, operation_id):
    with transaction(user_id) as conn:
        row = conn.execute('''SELECT tool_calls FROM public.assistant_messages
            WHERE user_id = %s AND tool_calls->>'kind' = 'receipt'
            AND tool_calls->>'operation_id' = %s ORDER BY id DESC LIMIT 1''', (user_id, operation_id)).fetchone()
    return row['tool_calls']['result'] if row else None


def _write(user_id, operation_id, payload, action):
    fingerprint = hashlib.sha256(json.dumps(plain(payload), sort_keys=True).encode()).hexdigest()
    with transaction(user_id) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', (user_id,))
        receipt = conn.execute('''SELECT id, tool_calls FROM public.assistant_messages
            WHERE user_id = %s AND tool_calls->>'kind' = 'receipt'
            AND tool_calls->>'operation_id' = %s ORDER BY id DESC LIMIT 1''', (user_id, operation_id)).fetchone()
        if receipt:
            data = receipt['tool_calls']
            if data['fingerprint'] != fingerprint:
                raise AssistantError('This action was already saved with different values. Start a new request to change it.')
            return data['result']
        result = plain(action(conn))
        conn.execute('''INSERT INTO public.assistant_messages
            (user_id, role, content, tool_calls, created_at) VALUES (%s, %s, %s, %s, NOW()) RETURNING id''',
            (user_id, 'assistant', 'Confirmed data change.', Jsonb({'kind': 'receipt', 'operation_id': operation_id,
             'fingerprint': fingerprint, 'result': result}))).fetchone()
        return result


def log_activity(user_id, log_type, log_date, details, source, notes, operation_id):
    payload = dict(log_type=log_type, log_date=log_date, details=details, source=source, notes=notes)
    def action(conn):
        row = conn.execute('''INSERT INTO public.activity_logs
            (user_id, log_date, log_type, details, source, notes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), clock_timestamp()) RETURNING id''',
            (user_id, log_date, log_type, Jsonb(details), source, notes)).fetchone()
        return {'id': row['id'], 'kind': 'log', 'saved': payload, 'undo': {'kind': 'delete_log', 'id': row['id']}}
    return _write(user_id, operation_id, payload, action)


def delete_log_entry(user_id, entry_id, operation_id):
    def action(conn):
        row = conn.execute('''UPDATE public.activity_logs SET deleted_at = NOW(), updated_at = clock_timestamp()
            WHERE user_id = %s AND deleted_at IS NULL AND id = %s RETURNING id, deleted_at''', (user_id, entry_id)).fetchone()
        if not row:
            raise AssistantError('That entry is already deleted or does not belong to this account.')
        return {'id': row['id'], 'kind': 'delete', 'undo': {'kind': 'restore_log', 'id': row['id'], 'deleted_at': plain(row['deleted_at'])}}
    return _write(user_id, operation_id, {'delete': entry_id}, action)


def restore_log_entry(user_id, entry_id, deleted_at, operation_id):
    def action(conn):
        row = conn.execute('''UPDATE public.activity_logs SET deleted_at = NULL, updated_at = clock_timestamp()
            WHERE user_id = %s AND id = %s AND deleted_at = %s RETURNING id''', (user_id, entry_id, deleted_at)).fetchone()
        if not row:
            raise AssistantError('This entry changed after deletion. Reload your activities before undoing.')
        return {'id': row['id'], 'kind': 'restore', 'undo': {'kind': 'delete_log', 'id': row['id']}}
    return _write(user_id, operation_id, {'restore': entry_id, 'deleted_at': deleted_at}, action)


def update_plan(user_id, before, plan_data, operation_id):
    def action(conn):
        row = conn.execute('''UPDATE public.user_plans SET plan_data = %s, title = %s, updated_at = clock_timestamp()
            WHERE user_id = %s AND id = %s AND is_active = TRUE AND plan_data = %s
            AND updated_at IS NOT DISTINCT FROM %s RETURNING id, updated_at''',
            (Jsonb(plan_data), plan_data['plan']['title'], user_id, before['id'], Jsonb(before['plan_data']), before['updated_at'])).fetchone()
        if not row:
            raise AssistantError('The active plan changed in another session. Cancel and request a fresh preview.')
        after = dict(before, plan_data=plan_data, updated_at=plain(row['updated_at']))
        return {'id': row['id'], 'kind': 'plan', 'undo': {'kind': 'restore_plan', 'before': after, 'plan_data': before['plan_data']}}
    return _write(user_id, operation_id, {'before': before, 'after': plan_data}, action)


def save_active_plan(user_id, plan_type, plan_data, expected_active, operation_id):
    def action(conn):
        active = conn.execute('''SELECT id, plan_data, updated_at FROM public.user_plans
            WHERE user_id = %s AND plan_type = %s AND is_active = TRUE ORDER BY id FOR UPDATE''', (user_id, plan_type)).fetchall()
        if plain(active) != expected_active:
            raise AssistantError('The active plan changed. Request a fresh save preview.')
        conn.execute('''UPDATE public.user_plans SET is_active = FALSE, updated_at = clock_timestamp()
            WHERE user_id = %s AND plan_type = %s AND is_active = TRUE RETURNING id''', (user_id, plan_type)).fetchall()
        row = conn.execute('''INSERT INTO public.user_plans
            (user_id, plan_type, title, plan_data, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, TRUE, NOW(), clock_timestamp()) RETURNING id, updated_at''',
            (user_id, plan_type, plan_data['plan']['title'], Jsonb(plan_data))).fetchone()
        return {'id': row['id'], 'kind': 'save_plan', 'undo': {'kind': 'deactivate_plan', 'id': row['id'],
                'updated_at': plain(row['updated_at']), 'prior_ids': [item['id'] for item in active], 'plan_type': plan_type}}
    return _write(user_id, operation_id, {'plan_type': plan_type, 'plan_data': plan_data, 'expected': expected_active}, action)


def active_plan_versions(user_id, plan_type):
    with transaction(user_id) as conn:
        return plain(conn.execute('''SELECT id, plan_data, updated_at FROM public.user_plans
            WHERE user_id = %s AND plan_type = %s AND is_active = TRUE ORDER BY id''', (user_id, plan_type)).fetchall())


def deactivate_plan(user_id, undo, operation_id):
    def action(conn):
        row = conn.execute('''UPDATE public.user_plans SET is_active = FALSE, updated_at = clock_timestamp()
            WHERE user_id = %s AND id = %s AND is_active = TRUE
            AND updated_at IS NOT DISTINCT FROM %s RETURNING id''', (user_id, undo['id'], undo['updated_at'])).fetchone()
        if not row:
            raise AssistantError('The saved plan changed. It cannot be undone from this old preview.')
        conn.execute('''UPDATE public.user_plans SET is_active = TRUE, updated_at = clock_timestamp()
            WHERE user_id = %s AND id = ANY(%s) AND plan_type = %s RETURNING id''',
            (user_id, undo['prior_ids'], undo['plan_type'])).fetchall()
        return {'id': row['id'], 'kind': 'undo_save_plan', 'undo': None}
    return _write(user_id, operation_id, undo, action)


def progress_rows(user_id, end_date):
    with transaction(user_id) as conn:
        rows = conn.execute('''SELECT id, log_date, log_type, details FROM public.activity_logs
            WHERE user_id = %s AND deleted_at IS NULL AND log_date <= %s
            ORDER BY log_date, id LIMIT 10001''', (user_id, end_date)).fetchall()
    if len(rows) > 10000:
        raise AssistantError('There are too many activities for a complete summary. Review a smaller export instead.')
    return plain(rows)
