import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest
from services import login_sessions as sessions

USER = dict(id='test-user', email='test@example.com', display_name='Test', role='customer')
TOKEN = 'a' * 43


class SessionTests(unittest.TestCase):
    def test_create_stores_only_hash_and_server_expiry(self):
        connection = MagicMock()
        with patch.object(sessions, 'get_database_connection') as connect:
            connect.return_value.__enter__.return_value = connection
            token = sessions.create_session(USER['id'])
        statement, params = connection.execute.call_args.args
        self.assertIn('INTERVAL', statement)
        self.assertEqual(params, (hashlib.sha256(token.encode()).hexdigest(), USER['id'], 604800))
        self.assertNotIn(token, repr(connection.execute.call_args_list))

    def test_resolve_requires_live_token_and_reads_current_role(self):
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = USER
        with patch.object(sessions, 'get_database_connection') as connect:
            connect.return_value.__enter__.return_value = connection
            self.assertEqual(sessions.resolve_session(TOKEN), USER)
        statement, params = connection.execute.call_args.args
        self.assertIn('expires_at > NOW()', statement)
        self.assertIn('u.role', statement)
        self.assertEqual(params, (sessions.token_digest(TOKEN),))
        with patch.object(sessions, 'get_database_connection') as connect:
            self.assertIsNone(sessions.resolve_session('tampered'))
            connect.assert_not_called()

    def test_revoke_removes_only_this_browser_token(self):
        connection = MagicMock()
        with patch.object(sessions, 'get_database_connection') as connect:
            connect.return_value.__enter__.return_value = connection
            sessions.revoke_session(TOKEN)
        statement, params = connection.execute.call_args.args
        self.assertIn('DELETE FROM firstrep_login_sessions WHERE token_hash = %s', statement)
        self.assertEqual(params, (sessions.token_digest(TOKEN),))

    def test_refresh_restores_before_loading_private_log(self):
        with patch('streamlit.context', SimpleNamespace(cookies={'firstrep_session': TOKEN})), \
             patch('services.browser_auth.resolve_session', return_value=USER), \
             patch('services.tracking.storage.load', return_value=[]) as load:
            # Each AppTest is a fresh Streamlit session, just like a full refresh.
            for _ in range(2):
                app = AppTest.from_file('BMI2.py').run(timeout=30)
                app.switch_page('pages/Food_Log.py').run(timeout=30)
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['firstrep_user'], USER)
                self.assertEqual(app.session_state['_auth_token'], TOKEN)
                load.assert_any_call(USER['id'], 'food_log')

    def test_revoked_cookie_clears_account_and_is_deleted(self):
        def writer(**kwargs):
            return SimpleNamespace(ack={'id': kwargs['data']['id'], 'ok': True})
        with patch('streamlit.context', SimpleNamespace(cookies={'firstrep_session': TOKEN})), \
             patch('services.browser_auth.resolve_session', return_value=None), \
             patch('services.browser_auth._cookie_writer', side_effect=writer) as cookie:
            app = AppTest.from_file('BMI2.py').run(timeout=30)
            app.switch_page('pages/Food_Log.py').run()
            self.assertFalse(app.exception)
            self.assertNotIn('firstrep_user', app.session_state)
            self.assertEqual(cookie.call_args.kwargs['data']['maxAge'], 0)
            self.assertEqual(cookie.call_args.kwargs['data']['token'], '')

    def test_logout_revokes_and_does_not_restore_initial_cookie(self):
        source = '''
import streamlit as st
from services.browser_auth import restore_session, sign_out
restore_session()
if st.button('Log out'):
    sign_out()
    st.rerun()
st.write('Signed in' if st.session_state.get('firstrep_user') else 'Guest')
'''
        def writer(**kwargs):
            return SimpleNamespace(ack={'id': kwargs['data']['id'], 'ok': True})
        with patch('streamlit.context', SimpleNamespace(cookies={'firstrep_session': TOKEN})), \
             patch('services.browser_auth.resolve_session', return_value=USER) as resolve, \
             patch('services.browser_auth.revoke_session') as revoke, \
             patch('services.browser_auth._cookie_writer', side_effect=writer):
            app = AppTest.from_string(source).run()
            app.session_state['food_log'] = [{'food': 'private'}]
            app.button[0].click().run()
            self.assertFalse(app.exception)
            revoke.assert_called_once_with(TOKEN)
            self.assertNotIn('firstrep_user', app.session_state)
            self.assertNotIn('food_log', app.session_state)
            resolve.assert_called_once_with(TOKEN)
            app.run()
            self.assertNotIn('firstrep_user', app.session_state)
