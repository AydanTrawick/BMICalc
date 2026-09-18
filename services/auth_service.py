import hashlib
import hmac
import os
import re
import secrets
import uuid
from typing import Any

import streamlit as st

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - handled in the UI at runtime
    psycopg = None
    dict_row = None


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ITERATIONS = 240_000


class AuthConfigurationError(RuntimeError):
    pass


class AuthError(RuntimeError):
    pass


ADMIN_ROLES = {"admin", "owner"}


def get_database_url() -> str:
    for key in ("DATABASE_URL", "NEON_DATABASE_URL"):
        value = os.getenv(key) or st.secrets.get(key)
        if value:
            return value

    neon_config = st.secrets.get("neon", {})
    if isinstance(neon_config, dict):
        value = neon_config.get("database_url")
        if value:
            return value

    return ""


def get_admin_emails() -> set[str]:
    emails: set[str] = set()

    for key in ("OWNER_EMAILS", "ADMIN_EMAILS"):
        value = os.getenv(key) or st.secrets.get(key, "")

        if isinstance(value, str):
            emails.update(
                normalize_email(email)
                for email in value.replace("\n", ",").split(",")
                if email.strip()
            )
        elif isinstance(value, list):
            emails.update(normalize_email(str(email)) for email in value)

    return emails


def role_for_email(email: str) -> str:
    if normalize_email(email) in get_admin_emails():
        return "owner"

    return "customer"


def is_admin_user(user: dict[str, Any] | None) -> bool:
    return bool(user and user.get("role") in ADMIN_ROLES)


def is_auth_configured() -> bool:
    return bool(get_database_url()) and psycopg is not None


def _connect():
    database_url = get_database_url()

    if psycopg is None:
        raise AuthConfigurationError(
            "Install psycopg to enable Neon account storage."
        )

    if not database_url:
        raise AuthConfigurationError(
            "Add DATABASE_URL or NEON_DATABASE_URL to Streamlit secrets."
        )

    connection = psycopg.connect(database_url, sslmode="require", row_factory=dict_row, connect_timeout=10)
    try:
        # Transaction-local settings work with Neon's pooled connections.
        connection.execute("SET LOCAL statement_timeout = '15s'")
        connection.execute("SET LOCAL lock_timeout = '10s'")
    except Exception:
        connection.close()
        raise
    return connection


def get_database_connection():
    return _connect()


def ensure_user_table() -> None:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS firstrep_users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_login_at TIMESTAMPTZ
                )
                """
            )
            cursor.execute(
                """
                ALTER TABLE firstrep_users
                ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'customer'
                """
            )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    ).hex()


def _new_password_hash(password: str) -> tuple[str, str]:
    salt_hex = secrets.token_hex(16)
    return _hash_password(password, salt_hex), salt_hex


def _validate_account_inputs(
    display_name: str,
    email: str,
    password: str,
) -> tuple[str, str]:
    clean_name = display_name.strip()
    clean_email = normalize_email(email)

    if not clean_name:
        raise AuthError("Enter a display name.")

    if not EMAIL_PATTERN.match(clean_email):
        raise AuthError("Enter a valid email address.")

    if len(password) < 8:
        raise AuthError("Use at least 8 characters for your password.")

    return clean_name, clean_email


def create_account(
    display_name: str,
    email: str,
    password: str,
) -> dict[str, Any]:
    clean_name, clean_email = _validate_account_inputs(
        display_name,
        email,
        password,
    )
    password_hash, password_salt = _new_password_hash(password)
    user_id = str(uuid.uuid4())
    role = role_for_email(clean_email)

    ensure_user_table()

    try:
        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO firstrep_users (
                        id,
                        email,
                        display_name,
                        password_hash,
                        password_salt,
                        role
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, email, display_name, role
                    """,
                    (
                        user_id,
                        clean_email,
                        clean_name,
                        password_hash,
                        password_salt,
                        role,
                    ),
                )
                user = cursor.fetchone()
    except Exception as error:
        if getattr(error, "sqlstate", "") == "23505":
            raise AuthError("An account already exists for that email.") from error
        raise

    return dict(user)


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    clean_email = normalize_email(email)

    if not EMAIL_PATTERN.match(clean_email):
        raise AuthError("Enter a valid email address.")

    ensure_user_table()

    with _connect() as connection:
        with connection.cursor() as cursor:
            secret_role = role_for_email(clean_email)
            if secret_role in ADMIN_ROLES:
                cursor.execute(
                    """
                    UPDATE firstrep_users
                    SET role = %s
                    WHERE email = %s AND role <> %s
                    """,
                    (secret_role, clean_email, secret_role),
                )

            cursor.execute(
                """
                SELECT id, email, display_name, password_hash, password_salt, role
                FROM firstrep_users
                WHERE email = %s
                """,
                (clean_email,),
            )
            user = cursor.fetchone()

            if not user:
                raise AuthError("No account was found for that email.")

            attempted_hash = _hash_password(password, user["password_salt"])
            if not hmac.compare_digest(attempted_hash, user["password_hash"]):
                raise AuthError("That password does not match.")

            cursor.execute(
                """
                UPDATE firstrep_users
                SET last_login_at = NOW()
                WHERE id = %s
                """,
                (user["id"],),
            )

    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "role": user["role"],
    }
