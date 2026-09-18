"""Revocable browser sessions. Only a SHA-256 token digest is stored in Neon."""
import hashlib
import re
import secrets

from services.auth_service import get_database_connection

SESSION_SECONDS = 7 * 24 * 60 * 60
TOKEN_PATTERN = re.compile(r'^[A-Za-z0-9_-]{43}$')
SESSION_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS firstrep_login_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES firstrep_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
)
'''


def token_digest(token):
    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        return None
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    with get_database_connection() as connection:
        connection.execute(SESSION_TABLE_SQL)
        connection.execute('DELETE FROM firstrep_login_sessions WHERE expires_at <= NOW()')
        connection.execute('''
            INSERT INTO firstrep_login_sessions (token_hash, user_id, expires_at)
            VALUES (%s, %s, NOW() + %s * INTERVAL '1 second')
        ''', (token_digest(token), user_id, SESSION_SECONDS))
    return token


def resolve_session(token):
    digest = token_digest(token)
    if digest is None:
        return None
    with get_database_connection() as connection:
        user = connection.execute('''
            SELECT u.id, u.email, u.display_name, u.role
            FROM firstrep_login_sessions s
            JOIN firstrep_users u ON u.id = s.user_id
            WHERE s.token_hash = %s AND s.expires_at > NOW()
        ''', (digest,)).fetchone()
    return dict(user) if user else None


def revoke_session(token):
    digest = token_digest(token)
    if digest:
        with get_database_connection() as connection:
            connection.execute('DELETE FROM firstrep_login_sessions WHERE token_hash = %s', (digest,))
