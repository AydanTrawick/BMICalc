import html

import streamlit as st
from psycopg import Error as DatabaseError

from services.auth_service import (
    AuthConfigurationError,
    AuthError,
    authenticate_user,
    create_account,
    is_auth_configured,
    is_admin_user,
)
from services.browser_auth import restore_session, sign_in, sign_out


def inject_shared_styles() -> None:
    st.markdown(
        """
        <style>
            .st-key-firstrep_chat_toggle {
                position: fixed;
                right: 1.25rem;
                bottom: 1.25rem;
                z-index: 1005;
            }

            .st-key-firstrep_chat_toggle button {
                width: 3.4rem;
                height: 3.4rem;
                padding: 0;
                border-radius: 999px;
                border: 1px solid #dbe3ef;
                background: #111827;
                color: white;
                font-size: 1.35rem;
                box-shadow: 0 12px 28px rgba(15, 23, 42, 0.24);
            }


                .st-key-firstrep_chat_toggle button {
                    border-color: #475569;
                    background: #e2e8f0;
                    color: #0f172a;
                    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.42);
                }


            .st-key-firstrep_chat_panel {
                position: fixed;
                right: 1.25rem;
                bottom: 5.25rem;
                z-index: 1004;
                width: min(390px, calc(100vw - 2.5rem));
                max-height: min(72vh, 640px);
                overflow-y: auto;
                padding: 1rem;
                border: 1px solid #dbe3ef;
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.98);
                box-shadow: 0 22px 60px rgba(15, 23, 42, 0.22);
            }


                .st-key-firstrep_chat_panel {
                    border-color: #334155;
                    background: rgba(15, 23, 42, 0.98);
                    box-shadow: 0 22px 60px rgba(0, 0, 0, 0.42);
                }


            .firstrep-chat-title {
                margin: 0 0 0.2rem;
                color: #111827;
                font-size: 1rem;
                font-weight: 800;
            }


                .firstrep-chat-title {
                    color: #f8fafc;
                }


            .firstrep-chat-caption {
                margin: 0 0 0.85rem;
                color: #64748b;
                font-size: 0.82rem;
            }


                .firstrep-chat-caption {
                    color: #cbd5e1;
                }


            .firstrep-message {
                padding: 0.7rem 0.8rem;
                margin-bottom: 0.55rem;
                border-radius: 14px;
                font-size: 0.9rem;
                line-height: 1.45;
            }

            .firstrep-message.user {
                margin-left: 2.2rem;
                background: #111827;
                color: white;
            }

            .firstrep-message.assistant {
                margin-right: 1.2rem;
                background: #f1f5f9;
                color: #111827;
            }


                .firstrep-message.user {
                    background: #e2e8f0;
                    color: #0f172a;
                }

                .firstrep-message.assistant {
                    background: #1e293b;
                    color: #f8fafc;
                }


            @media (max-width: 640px) {
                .st-key-firstrep_chat_toggle {
                    right: 1rem;
                    bottom: 1rem;
                }

                .st-key-firstrep_chat_panel {
                    right: 1rem;
                    bottom: 4.9rem;
                    width: calc(100vw - 2rem);
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def current_user() -> dict | None:
    restore_session()
    return st.session_state.get("firstrep_user")


def render_home_user_icon() -> None:
    user = current_user()
    label = "👤"
    if user:
        label = user["display_name"][:1].upper()

    st.markdown(
        """
        <style>
            .st-key-firstrep_home_user_icon {
                position: fixed;
                top: 1.1rem;
                right: 1.25rem;
                z-index: 1003;
            }

            .st-key-firstrep_home_user_icon button {
                width: 2.85rem;
                height: 2.85rem;
                padding: 0;
                border-radius: 999px;
                border: 1px solid #d7e2ee;
                background: white;
                color: #111827;
                font-weight: 800;
                box-shadow: 0 10px 25px rgba(15, 23, 42, 0.13);
            }


                .st-key-firstrep_home_user_icon button {
                    border-color: #475569;
                    background: #e2e8f0;
                    color: #0f172a;
                    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.42);
                }

        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button(label, key="firstrep_home_user_icon", help="Account"):
        st.session_state.firstrep_auth_open = not st.session_state.get(
            "firstrep_auth_open",
            True,
        )
        st.rerun()


def render_auth_panel(key_prefix: str = "") -> None:
    st.markdown('<div id="account"></div>', unsafe_allow_html=True)
    user = current_user()

    if user:
        role_label = user.get("role", "customer").title()
        st.markdown(
            f"""
            <div class="account-card">
                <div class="account-eyebrow">Signed in · {html.escape(role_label)}</div>
                <div class="account-title">Welcome back, {html.escape(user["display_name"])}</div>
                <div class="account-copy">{html.escape(user["email"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Log out", use_container_width=True, key=f"{key_prefix}firstrep_logout"):
            try:
                sign_out()
                st.rerun()
            except (DatabaseError, AuthConfigurationError):
                st.error("Could not log out of account storage. Please try again.")
        return

    try:
        configured = is_auth_configured()
    except st.errors.StreamlitSecretNotFoundError:
        st.warning("Accounts are unavailable because Streamlit secrets are missing or invalid. Check .streamlit/secrets.toml. You can still use the trackers without signing in.")
        return

    if not configured:
        st.warning(
            "Account storage is ready for Neon. Add DATABASE_URL or "
            "NEON_DATABASE_URL to .streamlit/secrets.toml, then restart "
            "Streamlit."
        )

    st.caption("Stay signed in on this browser for 7 days. Log out when using a shared device.")
    login_tab, create_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form(f"{key_prefix}firstrep_login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            try:
                sign_in(authenticate_user(email, password))
                st.success("Logged in.")
                st.rerun()
            except (AuthConfigurationError, AuthError) as error:
                st.error(str(error))
            except DatabaseError:
                st.error("Could not reach account storage. Try again shortly.")

    with create_tab:
        with st.form(f"{key_prefix}firstrep_create_account_form"):
            display_name = st.text_input("Display name", placeholder="Aydan")
            email = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Create password", type="password")
            submitted = st.form_submit_button(
                "Create account",
                use_container_width=True,
            )

        if submitted:
            try:
                sign_in(create_account(
                    display_name,
                    email,
                    password,
                ))
                st.success("Account created.")
                st.rerun()
            except (AuthConfigurationError, AuthError) as error:
                st.error(str(error))
            except DatabaseError:
                st.error("Could not reach account storage. Try again shortly.")


def require_login_access() -> dict:
    user = current_user()

    if not user:
        try:
            configured = is_auth_configured()
        except st.errors.StreamlitSecretNotFoundError:
            configured = False

        if not configured:
            st.error(
                "This feature needs Neon auth. Add DATABASE_URL or "
                "NEON_DATABASE_URL to .streamlit/secrets.toml."
            )
            render_chat_widget()
            st.stop()

        st.info("Create an account or log in to use this feature.")
        render_auth_panel()
        render_chat_widget()
        st.stop()

    return user


def require_admin_access() -> dict:
    user = current_user()

    if not is_auth_configured():
        st.error(
            "Admin access needs Neon auth. Add DATABASE_URL or "
            "NEON_DATABASE_URL to .streamlit/secrets.toml."
        )
        render_chat_widget()
        st.stop()

    if not user:
        st.info("Log in with an owner or admin account to access this page.")
        render_auth_panel()
        render_chat_widget()
        st.stop()

    if not is_admin_user(user):
        st.error("You do not have permission to access this admin page.")
        render_chat_widget()
        st.stop()

    return user


def render_chat_widget() -> None:
    """Compatibility entry point for the shared training assistant."""
    from assistant.widget import assistant_widget
    assistant_widget()
