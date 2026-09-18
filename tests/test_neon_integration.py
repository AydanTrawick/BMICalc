"""Opt-in live checks. Creates and removes only unique test accounts."""
import os
import secrets
import unittest
from uuid import uuid4
from unittest.mock import patch
import io

from streamlit.testing.v1 import AppTest
from services.auth_service import create_account, get_database_connection
from services import tracking_store as store


def row(**values):
    return dict(values, id=str(uuid4()))


def click(app, label):
    next(button for button in app.button if button.label == label).click().run(timeout=30)


@unittest.skipUnless(os.getenv('FIRSTREP_RUN_NEON_TESTS') == '1', 'Live Neon checks are opt-in')
class NeonIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.users = []
        cls.password = secrets.token_urlsafe(24)
        cls.addClassCleanup(cls.cleanup)
        for _ in range(2):
            cls.users.append(create_account('FirstRep integration test', f'firstrep-test-{uuid4()}@example.invalid', cls.password))

    @classmethod
    def cleanup(cls):
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                for user in cls.users:
                    cursor.execute('DELETE FROM public.firstrep_users WHERE id = %s', (user['id'],))
        with get_database_connection() as conn:
            with conn.cursor() as cursor:
                for user in cls.users:
                    cursor.execute('SELECT id FROM public.firstrep_users WHERE id = %s', (user['id'],))
                    assert cursor.fetchone() is None

    def setUp(self):
        for user in self.users:
            for kind in store.TABLES:
                existing = store.load(user['id'], kind)
                store.replace(user['id'], kind, existing, [])

    def test_transactional_storage_and_account_isolation(self):
        alice, bob = [user['id'] for user in self.users]
        workout = row(date='2026-09-12', exercise='Squat', sets=1, reps=8, weight_kg=60.0, rpe=8.0, notes='Test')
        first = store.append(alice, 'workout_log', [workout])
        self.assertEqual(first, [workout])
        self.assertEqual(store.append(alice, 'workout_log', [workout]), first)
        self.assertEqual(store.load(bob, 'workout_log'), [])
        with self.assertRaises(store.StorageError):
            store.replace(bob, 'workout_log', [], [dict(workout, reps=5)])
        self.assertEqual(store.load(alice, 'workout_log'), first)
        edited = [dict(workout, reps=6)]
        self.assertEqual(store.replace(alice, 'workout_log', first, edited), edited)
        self.assertEqual(store.replace(alice, 'workout_log', first, edited), edited)
        with self.assertRaises(store.ConflictError):
            store.replace(alice, 'workout_log', first, [])
        valid = dict(workout, id=str(uuid4()))
        invalid = dict(workout, id=str(uuid4()), rpe=11)
        with self.assertRaises(store.StorageError):
            store.append(alice, 'workout_log', [valid, invalid])
        self.assertEqual(store.load(alice, 'workout_log'), edited)
        store.replace(alice, 'workout_log', edited, [])
        self.assertEqual(store.load(alice, 'workout_log'), [])

    def login(self, user):
        app = AppTest.from_file('BMI2.py').run(timeout=30)
        next(field for field in app.text_input if field.label == 'Email').set_value(user['email'])
        next(field for field in app.text_input if field.label == 'Password').set_value(self.password)
        click(app, 'Log in')
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['firstrep_user']['id'], user['id'])
        return app

    def test_pages_persist_across_login_and_csv_restore(self):
        app = self.login(self.users[0])
        app.switch_page('pages/BMI_Calculator.py').run(timeout=30)
        click(app, 'Calculate BMI')
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '24.1')
        app.switch_page('pages/Workout_Log.py').run(timeout=30)
        app.text_input[0].set_value('Bench press')
        app.number_input(key='workout_weight_0').set_value(135.0)
        click(app, 'Add set')
        app.number_input(key='workout_weight_1').set_value(155.0)
        app.number_input(key='workout_reps_1').set_value(6)
        click(app, 'Save workout')
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, '2,010')
        app.session_state['workout_log_editor'] = {'edited_rows': {0: {'reps': 10}}, 'added_rows': [], 'deleted_rows': []}
        click(app, 'Save changes')
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        saved = store.load(self.users[0]['id'], 'workout_log')
        self.assertIn(10, [entry['reps'] for entry in saved])
        app.switch_page('pages/Food_Log.py').run(timeout=30)
        click(app, 'Save food')
        self.assertFalse(app.exception)
        fresh = self.login(self.users[0])
        for filename, kind, count in [('BMI_Calculator', 'bmi_log', 1), ('Workout_Log', 'workout_log', 2), ('Food_Log', 'food_log', 1)]:
            fresh.switch_page(f'pages/{filename}.py').run(timeout=30)
            self.assertFalse(fresh.exception)
            self.assertEqual(len(fresh.session_state[kind]), count)
        upload = io.BytesIO(b'date,food,protein_g,carbs_g,fat_g\n2026-09-12,Lunch,30,40,10\n')
        upload.size = len(upload.getvalue())
        fresh.checkbox(key='food_log_confirm_restore').check()
        with patch('streamlit.file_uploader', return_value=upload):
            click(fresh, 'Restore log')
        self.assertFalse(fresh.exception)
        self.assertFalse(fresh.error)
        self.assertEqual(store.load(self.users[0]['id'], 'food_log')[0]['food'], 'Lunch')
        fresh.session_state['food_log_editor'] = {'edited_rows': {}, 'added_rows': [], 'deleted_rows': [0]}
        click(fresh, 'Save changes')
        self.assertFalse(fresh.exception)
        self.assertEqual(store.load(self.users[0]['id'], 'food_log'), [])
        fresh.switch_page('BMI2.py').run(timeout=30)
        click(fresh, 'Log out')
        self.assertNotIn('bmi_log', fresh.session_state)
        self.assertNotIn('workout_log', fresh.session_state)
        for kind in store.TABLES:
            self.assertEqual(store.load(self.users[1]['id'], kind), [])

    def test_guest_import_is_explicit(self):
        app = AppTest.from_file('BMI2.py').run(timeout=30)
        app.switch_page('pages/Food_Log.py').run(timeout=30)
        click(app, 'Save food')
        app.switch_page('BMI2.py').run(timeout=30)
        next(field for field in app.text_input if field.label == 'Email').set_value(self.users[0]['email'])
        next(field for field in app.text_input if field.label == 'Password').set_value(self.password)
        click(app, 'Log in')
        self.assertEqual(store.load(self.users[0]['id'], 'food_log'), [])
        app.switch_page('pages/Food_Log.py').run(timeout=30)
        click(app, 'Add guest entries to my account')
        self.assertFalse(app.exception)
        self.assertEqual(len(store.load(self.users[0]['id'], 'food_log')), 1)
