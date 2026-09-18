import unittest
from unittest.mock import patch

from services import tracking
from services.tracking_store import StorageError

FOOD = dict(date='2026-09-12', food='Lunch', protein_g=30, carbs_g=40, fat_g=10)


class PersistenceTests(unittest.TestCase):
    def test_guest_logs_require_explicit_import_and_logout_clears_private_state(self):
        state = {'food_log': [FOOD], 'workout_notes_0': 'private'}
        with patch.object(tracking.st, 'session_state', state):
            tracking.change_user({'id': 'alice'})
            self.assertNotIn('food_log', state)
            self.assertEqual(state['_guest_logs']['food_log'], [FOOD])
            state['food_log'] = [dict(FOOD, id='saved')]
            tracking.change_user(None)
            self.assertNotIn('food_log', state)
            self.assertNotIn('_guest_logs', state)
            self.assertNotIn('workout_notes_0', state)

    def test_failed_save_keeps_input_and_retry_uses_same_ids(self):
        state = {'firstrep_user': {'id': 'alice'}, 'food_log': []}
        with patch.object(tracking.st, 'session_state', state), patch.object(tracking.storage, 'append') as save:
            save.side_effect = StorageError('unavailable')
            with self.assertRaises(StorageError):
                tracking.append_records('food_log', [FOOD])
            self.assertEqual(state['food_log'], [])
            requested = save.call_args.args[2]
            save.side_effect = None
            save.return_value = requested
            tracking.append_records('food_log', [FOOD])
            self.assertEqual(save.call_args.args[2], requested)
            self.assertEqual(state['food_log'], requested)

    def test_bmi_retry_keeps_timestamp_and_ids(self):
        state = {'firstrep_user': {'id': 'alice'}, 'bmi_log': []}
        reading = dict(recorded_at='2026-09-12T12:00:00', height_cm=175, weight_kg=70)
        with patch.object(tracking.st, 'session_state', state), patch.object(tracking.storage, 'append') as save:
            save.side_effect = StorageError('unavailable')
            with self.assertRaises(StorageError):
                tracking.append_records('bmi_log', [reading])
            requested = save.call_args.args[2]
            save.side_effect = None
            save.return_value = requested
            tracking.append_records('bmi_log', [dict(reading, recorded_at='2026-09-12T12:01:00')])
            self.assertEqual(save.call_args.args[2], requested)

    def test_editor_rejects_unowned_ids(self):
        state = {'firstrep_user': {'id': 'alice'}, 'food_log': [dict(FOOD, id='alice-row')]}
        with patch.object(tracking.st, 'session_state', state), patch.object(tracking.storage, 'replace') as save:
            with self.assertRaises(ValueError):
                tracking.replace_records('food_log', [dict(FOOD, id='bob-row')], preserve_ids=True)
            save.assert_not_called()

    def test_failed_edit_preserves_snapshot(self):
        original = dict(FOOD, id='alice-row')
        state = {'firstrep_user': {'id': 'alice'}, 'food_log': [original]}
        with patch.object(tracking.st, 'session_state', state), patch.object(tracking.storage, 'replace', side_effect=StorageError('offline')):
            with self.assertRaises(StorageError):
                tracking.replace_records('food_log', [dict(original, protein_g=50)], preserve_ids=True)
            self.assertEqual(state['food_log'], [original])
