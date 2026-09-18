import ast
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

import psycopg
import pytest

from assistant import db
from assistant.config import AssistantError


@contextmanager
def fake_database(conn):
    with patch('assistant.db.transaction') as transaction:
        transaction.return_value.__enter__.return_value = conn
        yield transaction


def test_logs_are_owner_scoped_parameterized_and_exclude_deleted():
    conn = Mock()
    conn.execute.return_value.fetchall.return_value = []
    with fake_database(conn) as transaction:
        assert db.get_logs('user-a', '2026-09-01', '2026-09-17', 'strength', "squat'; DROP TABLE x--") == {'entries': [], 'truncated': False}
    query, params = conn.execute.call_args.args
    assert 'user_id = %s AND deleted_at IS NULL' in query
    assert 'DROP TABLE' not in query and params[0] == 'user-a'
    transaction.assert_called_with('user-a')


def test_cardio_null_duration_and_write_receipt():
    conn = Mock()
    conn.execute.return_value.fetchone.side_effect = [None, {'id': 17}, {'id': 32}]
    with fake_database(conn):
        result = db.log_activity('user-a', 'cardio', '2026-09-17',
                                 {'activity': 'run', 'distance': 3, 'distance_unit': 'miles', 'duration_minutes': None, 'avg_pace': None},
                                 'voice', None, 'unique-op')
    assert result['id'] == 17 and result['undo']['id'] == 17
    insert = next(call for call in conn.execute.call_args_list if 'INSERT INTO public.activity_logs' in call.args[0])
    assert insert.args[1][3].obj['duration_minutes'] is None
    assert insert.args[1][0] == 'user-a'


def test_soft_delete_returns_id_and_undo_snapshot():
    conn = Mock()
    conn.execute.return_value.fetchone.side_effect = [None, {'id': 17, 'deleted_at': '2026-09-17T12:00:00Z'}, {'id': 32}]
    with fake_database(conn):
        result = db.delete_log_entry('user-a', 17, 'op')
    query, params = next(call.args for call in conn.execute.call_args_list if 'UPDATE public.activity_logs' in call.args[0])
    assert 'deleted_at = NOW()' in query and 'user_id = %s AND deleted_at IS NULL' in query
    assert params == ('user-a', 17) and result['undo']['kind'] == 'restore_log'


def test_retry_receipt_prevents_duplicate_insert():
    import hashlib
    import json
    payload = {'delete': 17}
    receipt = {'tool_calls': {'fingerprint': hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
                              'result': {'id': 17}}}
    conn = Mock()
    conn.execute.return_value.fetchone.return_value = receipt
    with fake_database(conn):
        assert db.delete_log_entry('user-a', 17, 'same-operation') == {'id': 17}
    assert not any('UPDATE' in call.args[0] for call in conn.execute.call_args_list)


def test_connection_retries_once_with_ssl_and_timeout():
    store = db.ConnectionStore('postgresql://unused')
    with patch('assistant.db.psycopg.connect', side_effect=[psycopg.OperationalError('offline'), Mock()]) as connect, patch('assistant.db.time.sleep'):
        assert store.connect() is not None
    assert connect.call_count == 2
    assert connect.call_args.kwargs['sslmode'] == 'require'
    assert connect.call_args.kwargs['connect_timeout'] == 10
    with patch('assistant.db.psycopg.connect', side_effect=psycopg.OperationalError('offline')) as connect, patch('assistant.db.time.sleep'):
        with pytest.raises(AssistantError, match='after a retry'):
            db.ConnectionStore('postgresql://unused').connect()
    assert connect.call_count == 2


def test_sql_is_literal_and_never_creates_or_hard_deletes_tables():
    tree = ast.parse(Path('assistant/db.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'execute':
            assert isinstance(node.args[0], ast.Constant)
            sql = node.args[0].value.upper()
            assert 'CREATE TABLE' not in sql and 'DELETE FROM' not in sql
            if 'PUBLIC.' in sql:
                assert '%S' in sql and len(node.args) == 2
                assert 'USER_ID' in sql
