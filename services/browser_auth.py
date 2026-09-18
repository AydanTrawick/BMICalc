"""Restore login before account-dependent UI or tracker data is loaded."""
import time
import uuid

import streamlit as st
from psycopg import Error as DatabaseError
from streamlit.components.v2 import component

from services.auth_service import AuthConfigurationError
from services.login_sessions import create_session, resolve_session, revoke_session, SESSION_SECONDS

COOKIE_NAME = 'firstrep_session'
_cookie_writer = component('firstrep_session_cookie', js='''
export default function(component) {
    const { data, setStateValue } = component;
    const secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = "firstrep_session=" + encodeURIComponent(data.token) +
        "; Path=/; SameSite=Lax; Max-Age=" + data.maxAge + secure;
    const actual = document.cookie.split("; ").find(row => row.startsWith("firstrep_session="));
    const ok = data.token ? actual === "firstrep_session=" + encodeURIComponent(data.token) : !actual;
    setStateValue("ack", {id: data.id, ok});
}
''')


def _queue_cookie(token):
    st.session_state['_auth_cookie_write'] = {
        'id': uuid.uuid4().hex, 'token': token,
        'maxAge': SESSION_SECONDS if token else 0,
    }


def sign_in(user):
    from services.tracking import change_user
    # Commit the token before showing the account as signed in.
    token = create_session(user['id'])
    change_user(user)
    st.session_state['_auth_token'] = token
    st.session_state['_auth_checked_at'] = time.time()
    _queue_cookie(token)


def sign_out():
    from services.tracking import change_user
    token = st.session_state.get('_auth_token') or st.context.cookies.get(COOKIE_NAME)
    # A database failure leaves the session intact so logout can be retried.
    revoke_session(token)
    change_user(None)
    st.session_state['_auth_checked_at'] = time.time()
    _queue_cookie('')


def restore_session():
    from services.tracking import change_user
    pending = st.session_state.get('_auth_cookie_write')
    if pending:
        result = _cookie_writer(data=pending, key='firstrep_cookie_write_' + pending['id'],
                                on_ack_change=lambda: None, height=0)
        ack = result.ack
        if not ack or ack.get('id') != pending['id']:
            st.caption('Updating your browser session…')
            st.stop()
        st.session_state.pop('_auth_cookie_write', None)
        if not ack.get('ok'):
            st.warning('Your browser blocked the login cookie. Login will last only until this page is refreshed.')
    checked = st.session_state.get('_auth_checked_at')
    token = st.session_state.get('_auth_token')
    if checked is not None and (not token or time.time() - checked < 60):
        return
    # st.context cookies are from the initial connection; don't reuse them after logout.
    if checked is None:
        token = st.context.cookies.get(COOKIE_NAME)
    if not isinstance(token, str) or not token:
        st.session_state['_auth_checked_at'] = time.time()
        return
    try:
        user = resolve_session(token)
    except (DatabaseError, AuthConfigurationError, st.errors.StreamlitSecretNotFoundError):
        st.error('Could not restore your account connection. Please retry.')
        if st.button('Retry account connection'):
            st.rerun()
        st.stop()
    existing = st.session_state.get('firstrep_user')
    if user:
        if not existing or existing['id'] != user['id']:
            change_user(user)
        else:
            st.session_state['firstrep_user'] = user  # refresh role/display name
        st.session_state['_auth_token'] = token
    else:
        change_user(None)
        _queue_cookie('')
    st.session_state['_auth_checked_at'] = time.time()
    if not user:
        st.rerun()
