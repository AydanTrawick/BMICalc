"""One floating launcher per page; conversation interactions rerun only the fragment."""
import json
import logging
from contextlib import nullcontext
from uuid import uuid4

import streamlit as st

from assistant import agent, db
from assistant.config import AssistantError, MAX_MESSAGES, secret_key, today
from assistant.executor import prepare_builder_save, prepare_undo, prepare_write
from assistant.speech import speech_audio
from assistant.transcribe import transcribe_audio
from plan_agent.api import claude_client
from plan_agent.config import PlanAgentError
from services.browser_auth import restore_session

logger = logging.getLogger(__name__)


def _refresh():
    # Browser events rerun only this fragment. A first/full run (including AppTest)
    # needs an app rerun; the open-dialog flag preserves the panel in that case.
    from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
    context = get_script_run_ctx()
    st.rerun(scope='fragment' if context and context.fragment_ids_this_run else 'app')


def _user_id():
    restore_session()
    return (st.session_state.get('firstrep_user') or {}).get('id')


def _speak(reply, user_id):
    if not reply or st.session_state.get('pending_action'):
        return
    audio, note = speech_audio(reply, user_id or st.session_state.setdefault('training_guest_scope', str(uuid4())),
                               enabled=st.session_state.get('training_speak_enabled', True))
    if audio:
        st.session_state['training_audio'] = audio
        st.session_state['training_audio_play'] = True
    if note:
        st.session_state['training_voice_note'] = note


def _run(operation, user_id):
    st.session_state.pop('training_error', None)
    st.session_state.pop('training_voice_note', None)
    st.session_state.pop('training_audio', None)
    try:
        with st.spinner('Working on your request…'):
            key = secret_key('ANTHROPIC_API_KEY')
            with (claude_client(key) if key else nullcontext(None)) as client:
                reply = operation(client)
            _speak(reply, user_id)
    except (AssistantError, PlanAgentError) as error:
        st.session_state['training_error'] = str(error)
    except Exception:
        logger.exception('Unexpected assistant operation failure')
        st.session_state['training_error'] = 'The assistant could not finish this step. Any successful saves are listed in the conversation; pending confirmations can be retried safely.'


def _edited_arguments(action):
    """Blank numeric values stay null. JSON is only used for nested meal items."""
    arguments = dict(action.arguments)
    for name, value in arguments.items():
        key = f'training_edit_{action.operation_id}_{name}'
        label = name.replace('_', ' ').capitalize()
        if name == 'items':
            raw = st.text_area('Foods and amounts (JSON list)', value=json.dumps(value, indent=2), key=key)
            try:
                arguments[name] = json.loads(raw)
            except ValueError:
                arguments[name] = raw  # Typed validation explains the problem on preview.
        elif isinstance(value, int) and name != 'reps':
            arguments[name] = int(st.number_input(label, value=value, step=1, key=key))
        else:
            arguments[name] = st.text_input(label, value='' if value is None else str(value), key=key)
            if arguments[name] == '' and name in ('weight', 'rpe', 'distance', 'distance_unit', 'duration_minutes', 'calories', 'protein_g', 'notes', 'unit'):
                arguments[name] = None
    return arguments


def _pending_card(user_id):
    turn = st.session_state.get('pending_action')
    if not turn:
        return
    action = turn.actions[0]['action']
    with st.container(border=True):
        labels = {'log_strength': 'Log this strength workout?', 'log_cardio': 'Log this cardio activity?',
                  'log_meal': 'Log this meal?', 'log_bodyweight': 'Log this bodyweight?',
                  'delete_log_entry': 'Remove this activity from your log?', 'update_active_plan': 'Apply this plan replacement?',
                  'save_builder_plan': 'Save this Builder plan as your active copy?', 'undo': 'Undo this recent change?'}
        st.markdown('**' + labels.get(action.name, 'Confirm this change?') + '**')
        st.caption(f'{len(turn.actions)} pending action(s). Each change requires its own confirmation.')
        st.json(action.preview, expanded=True)
        editing = st.session_state.get('training_editing') == action.operation_id
        if editing:
            with st.form('training_edit_form_' + action.operation_id):
                values = _edited_arguments(action)
                if st.form_submit_button('Review edited action'):
                    try:
                        with claude_client(secret_key('ANTHROPIC_API_KEY')) as client:
                            # Edited dates are literal input: do not override them with the old utterance.
                            revised = prepare_write(action.name, values, user_id, turn.source, client=client)
                        turn.actions[0]['action'] = revised
                        st.session_state.pop('training_editing', None)
                        _refresh()
                    except PlanAgentError as error:
                        st.error(str(error))
        buttons = st.columns(3)
        if buttons[0].button('Confirm', type='primary', disabled=editing, key='training_confirm_' + action.operation_id):
            _run(lambda client: agent.resolve_pending(st.session_state, user_id, client, True), user_id)
            _refresh()
        if action.attempted:
            st.caption('A save was attempted. Retry Confirm to reconcile it safely, or Cancel to check whether it already committed. Editing is locked until that is resolved.')
        if buttons[1].button('Edit', disabled=action.attempted or action.name in ('undo', 'save_builder_plan'), key='training_edit_' + action.operation_id):
            st.session_state['training_editing'] = action.operation_id
            _refresh()
        if buttons[2].button('Cancel', key='training_cancel_' + action.operation_id):
            _run(lambda client: agent.resolve_pending(st.session_state, user_id, client, False), user_id)
            st.session_state.pop('training_editing', None)
            _refresh()


@st.fragment
def chat_body():
    user_id = _user_id()
    if not user_id:
        st.info('Create an account or log in to use the Training Assistant.')
        from services.ui import render_auth_panel
        render_auth_panel(key_prefix='training_assistant_')
        return
    try:
        agent.initialize(st.session_state, user_id)
    except PlanAgentError as error:
        st.error(str(error))
        if st.button('Retry loading conversation', key='training_load_retry'):
            _refresh()
        return
    st.caption('Ask about training, review your assistant activity history, or confirm changes to your logs and saved plan.')
    st.toggle('Speak replies', value=st.session_state.training_speak_enabled, key='training_speak_toggle',
              on_change=lambda: st.session_state.update(training_speak_enabled=st.session_state.training_speak_toggle))
    if not st.session_state.training_speak_enabled:
        st.session_state.pop('training_audio', None)
        st.session_state.pop('training_voice_note', None)
    if st.button('Clear conversation', key='training_clear'):
        try:
            agent.clear_conversation(st.session_state, user_id)
            _refresh()
        except PlanAgentError as error:
            st.error(str(error))
    st.caption(f'{MAX_MESSAGES - st.session_state.training_count} assistant requests remaining this session.')
    with st.container(height=300, key='training_history'):
        if not st.session_state.training_messages:
            st.write('Try “Log a 3 mile run today” or “What did I do for legs last week?”')
        for message in st.session_state.training_messages:
            with st.chat_message(message['role']):
                st.write(message['content'])
                metadata = message.get('tool_calls')
                confirmed = metadata.get('confirmed') if isinstance(metadata, dict) else None
                last = st.session_state.get('last_write')
                if confirmed and last and confirmed.get('id') == last['id'] and confirmed.get('kind') == last['kind'] and last.get('undo'):
                    if st.button('Undo', key='training_undo_' + str(message.get('id', id(message))), disabled=bool(st.session_state.pending_action)):
                        try:
                            agent.stage_local(prepare_undo(user_id, last), st.session_state)
                            _refresh()
                        except PlanAgentError as error:
                            st.error(str(error))
    for field in ('training_error', 'training_notice'):
        if st.session_state.get(field):
            st.warning(st.session_state[field])
    if st.session_state.get('training_resume') and not st.session_state.pending_action:
        if st.button('Retry interrupted reply', key='training_retry_reply'):
            _run(lambda client: agent.retry_reply(st.session_state, user_id, client), user_id)
            _refresh()
    _pending_card(user_id)
    if st.session_state.get('training_audio') and st.session_state.training_speak_enabled:
        st.audio(st.session_state.training_audio, format='audio/mp3', autoplay=st.session_state.pop('training_audio_play', False))
    if st.session_state.get('training_voice_note'):
        st.caption(st.session_state.training_voice_note)

    configured = bool(secret_key('ANTHROPIC_API_KEY'))
    if not configured:
        st.info('Add ANTHROPIC_API_KEY to Streamlit secrets to enable the training assistant.')
    disabled = not configured or bool(st.session_state.pending_action) or st.session_state.training_count >= MAX_MESSAGES
    audio = st.audio_input('Speak a request (up to 60 seconds)', sample_rate=16000,
                           disabled=disabled or not secret_key('OPENAI_API_KEY'),
                           key=f'training_recording_{st.session_state.training_audio_version}')
    if audio is not None and not disabled:
        # Increment before any provider call, including failures, to avoid replay.
        st.session_state.training_audio_version += 1
        try:
            with st.spinner('Transcribing…'):
                transcript = transcribe_audio(audio.getvalue(), secret_key('OPENAI_API_KEY'))
            _run(lambda client: agent.begin(transcript, st.session_state, user_id, client, source='voice'), user_id)
        except PlanAgentError as error:
            st.session_state.training_error = str(error)
        _refresh()
    prompt = st.chat_input('Ask a question or describe what to log', disabled=disabled, key='training_chat_input')
    if prompt:
        _run(lambda client: agent.begin(prompt, st.session_state, user_id, client), user_id)
        _refresh()

    if user_id and st.session_state.get('current_plan') is not None and st.session_state.get('plan_display_request'):
        if st.button('Save Builder plan as active copy', disabled=bool(st.session_state.pending_action), key='training_save_builder'):
            try:
                action = prepare_builder_save(user_id, st.session_state.current_plan, st.session_state.plan_display_request)
                agent.stage_local(action, st.session_state)
                _refresh()
            except PlanAgentError as error:
                st.error(str(error))
        st.caption('Saving a copy does not change the Builder draft. Assistant edits apply to the saved active copy.')
    with st.expander('Saved active plans'):
        if st.button('Load saved plans', disabled=not user_id, key='training_load_plans'):
            try:
                for kind in ('workout', 'meal'):
                    plan = db.get_active_plan(user_id, kind)
                    if plan:
                        st.write(plan['title'])
                        st.json(plan['plan_data'], expanded=False)
                    else:
                        st.caption(f'No active {kind} plan.')
            except PlanAgentError as error:
                st.error(str(error))
    st.caption('General information, not medical advice. Consult a professional for pain, injury, or health concerns.')


def _close_dialog():
    st.session_state['training_dialog_open'] = False


@st.dialog('Training Assistant', width='large', on_dismiss=_close_dialog)
def _dialog():
    chat_body()


def assistant_widget():
    st.markdown('''<style>
    .st-key-training_assistant_launcher {
        position: fixed; right: max(1.25rem, env(safe-area-inset-right));
        bottom: max(2rem, calc(env(safe-area-inset-bottom) + 1.25rem));
        width: auto; z-index: 1004;
    }
    .st-key-training_assistant_launcher button {
        width: 3.4rem; height: 3.4rem; min-height: 3.4rem; padding: 0;
        border-radius: 50%; background: #e2e8f0; color: #0f172a;
        border: 1px solid #64748b; box-shadow: 0 5px 20px #0006;
    }
    @media (max-width: 640px) {
        .st-key-training_assistant_launcher { right: 1rem; bottom: max(4.5rem, env(safe-area-inset-bottom)); }
        div[data-testid="stDialog"] div[role="dialog"] { width: calc(100vw - 1rem); max-height: 94dvh; overflow-y: auto; }
    }
    </style>''', unsafe_allow_html=True)
    if st.button('🎙️', help='Open Training Assistant', key='training_assistant_launcher'):
        st.session_state['training_dialog_open'] = True
    if st.session_state.get('training_dialog_open'):
        _dialog()


def activity_log_section(log_types):
    """Expose new-schema activity entries without changing legacy tracker calculations."""
    user_id = (st.session_state.get('firstrep_user') or {}).get('id')
    with st.expander('Assistant activity log'):
        st.caption('Activities confirmed in the training assistant are saved here. These entries are separate from the manual tracker totals above.')
        if not user_id:
            st.caption('Sign in to view saved assistant activities.')
            return
        if st.button('Load assistant activities', key='training_activity_load_' + '_'.join(log_types)):
            from dateutil.relativedelta import relativedelta
            try:
                result = db.get_logs(user_id, (today() - relativedelta(years=1)).isoformat(), today().isoformat())
                rows = [row for row in result['entries'] if row['log_type'] in log_types]
                if rows:
                    st.dataframe([{'ID': row['id'], 'Date': row['log_date'], 'Type': row['log_type'],
                                   'Details': json.dumps(row['details']), 'Source': row['source'], 'Notes': row['notes']}
                                  for row in rows], hide_index=True, width='stretch')
                else:
                    st.caption('No assistant activities to show in this range.')
                if result['truncated']:
                    st.caption('Showing the most recent 500 activities; ask the assistant for a narrower date range.')
            except PlanAgentError as error:
                st.error(str(error))
