"""Opt-in integration against the user's existing tables; all test rows roll back."""
from contextlib import contextmanager
import os
from uuid import uuid4
from unittest.mock import patch

import psycopg
from psycopg.rows import dict_row
import pytest

from assistant import db
from assistant.config import secret_key, today
from plan_agent.schemas import PlanRequest
from tests.plan_fixtures import workout_plan


@pytest.mark.skipif(os.getenv('FIRSTREP_RUN_ASSISTANT_DB_TESTS') != '1', reason='Opt-in Neon test; no permanent rows or schema changes')
def test_existing_neon_tables_transactional_workflow():
    user, other = 'assistant-test-' + uuid4().hex, 'assistant-other-' + uuid4().hex
    with psycopg.connect(secret_key('NEON_DATABASE_URL'), sslmode='require', connect_timeout=10,
                         autocommit=True, row_factory=dict_row) as conn:
        with conn.transaction(force_rollback=True):
            @contextmanager
            def transaction(owner):
                assert owner in (user, other)
                yield conn
            with patch('assistant.db.transaction', transaction):
                details = {'activity': 'run', 'distance': 3, 'distance_unit': 'miles', 'duration_minutes': None, 'avg_pace': None}
                result = db.log_activity(user, 'cardio', today().isoformat(), details, 'voice', None, 'create-test')
                again = db.log_activity(user, 'cardio', today().isoformat(), details, 'voice', None, 'create-test')
                assert again['id'] == result['id']
                assert len(db.get_logs(user, today(), today())['entries']) == 1
                assert not db.get_logs(other, today(), today())['entries']
                deleted = db.delete_log_entry(user, result['id'], 'delete-test')
                assert not db.get_logs(user, today(), today())['entries']
                db.restore_log_entry(user, result['id'], deleted['undo']['deleted_at'], 'restore-test')
                assert len(db.progress_rows(user, today())) == 1
                db.save_message(user, 'user', 'Test conversation')
                assert len(db.load_messages(user)) == 1
                db.clear_conversation(user)
                assert not db.load_messages(user)
                data = {'plan': workout_plan().model_dump(), 'request': PlanRequest(plan_type='workout', days=4, volume='low').model_dump()}
                saved = db.save_active_plan(user, 'workout', data, [], 'save-plan')
                active = db.get_active_plan(user, 'workout')
                assert active['id'] == saved['id'] and db.get_active_plan(other, 'workout') is None
                replacement = {**data, 'plan': dict(data['plan'], title='Updated test title')}
                changed = db.update_plan(user, active, replacement, 'edit-plan')
                restored = db.update_plan(user, changed['undo']['before'], changed['undo']['plan_data'], 'undo-edit')
                assert db.get_active_plan(user, 'workout')['plan_data'] == data
                # Undo-save snapshots reject plans that changed, even if later restored.
                from assistant.config import AssistantError
                with pytest.raises(AssistantError):
                    db.deactivate_plan(user, saved['undo'], 'undo-save-stale')
                versions = db.active_plan_versions(user, 'workout')
                saved2 = db.save_active_plan(user, 'workout', data, versions, 'save-second')
                db.deactivate_plan(user, saved2['undo'], 'undo-save-second')
                assert db.get_active_plan(user, 'workout')['id'] == saved['id']
        # All test records were rolled back, including idempotency receipts.
        assert conn.execute('SELECT COUNT(*) AS count FROM public.activity_logs WHERE user_id = %s', (user,)).fetchone()['count'] == 0
