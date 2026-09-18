import hashlib

import streamlit as st

from plan_agent.agent import initialize_state, process_message, start_over
from plan_agent.api import claude_client
from plan_agent.config import DISCLAIMER, MAX_GENERATIONS, PlanAgentError, secret_key
from plan_agent.render import render_plan
from plan_agent.transcribe import transcribe_audio
from services.browser_auth import restore_session

st.set_page_config(page_title='AI Plan Builder', page_icon='🎙️', layout='wide')
restore_session()
initialize_state(st.session_state)
st.page_link('BMI2.py', label='← Back to Home')
st.title('AI Plan Builder')
st.caption('Speak or type a request to build a meal or workout plan, then refine it together.')
st.info('\n\n'.join(DISCLAIMER))
st.button('Start over', on_click=start_over, args=(st.session_state,))
remaining = MAX_GENERATIONS - st.session_state.request_count
quota = st.empty()
quota.caption(f'{remaining} of {MAX_GENERATIONS} plan builds or edits remaining this session. Start over clears this conversation and keeps the session limit.')

anthropic_key = secret_key('ANTHROPIC_API_KEY')
openai_key = secret_key('OPENAI_API_KEY')
if not anthropic_key:
    st.warning('Setup needed: add ANTHROPIC_API_KEY as a top-level Streamlit secret, then restart the app. This key is required for both typed and spoken plans. See .streamlit/secrets.toml.example.')
if not openai_key:
    st.caption('Voice setup: add OPENAI_API_KEY to Streamlit secrets. Typed requests only need the Anthropic key.')
disabled = not anthropic_key or remaining <= 0

history = st.empty()
notice = st.empty()


def show_conversation():
    with history.container():
        for message in st.session_state.messages:
            with st.chat_message(message['role']):
                st.write(message['content'])
    if st.session_state.get('plan_builder_error'):
        notice.error(st.session_state.plan_builder_error)
    else:
        notice.empty()


show_conversation()

submitted_text = None
voice, typed = st.columns(2)
with voice:
    st.subheader('Speak')
    recording = st.audio_input('Record your request (up to 60 seconds)', sample_rate=16000,
                               disabled=disabled or not openai_key, key='plan_builder_audio')
    if st.button('Transcribe recording', disabled=disabled or not openai_key or recording is None):
        try:
            data = recording.getvalue()
            digest = hashlib.sha256(data).hexdigest()
            cache = st.session_state.get('plan_builder_audio_cache', {})
            with st.spinner('Transcribing…'):
                transcript = cache.get(digest) or transcribe_audio(data, openai_key)
            # Keep only the latest audio result, privately in this browser session.
            st.session_state.plan_builder_audio_cache = {digest: transcript}
            st.session_state.last_transcript = transcript
            st.session_state.plan_builder_transcript_editor = transcript
            st.session_state.pop('plan_builder_error', None)
        except PlanAgentError as error:
            st.error(str(error))
    if st.session_state.last_transcript:
        st.write('You said: ' + st.session_state.last_transcript)
        edited = st.text_area('Edit your transcript before sending', key='plan_builder_transcript_editor')
        if st.button('Send edited transcript', disabled=disabled):
            submitted_text = edited
with typed:
    st.subheader('Type')
    st.caption('For example: “3 days, 3 meals a day, no nuts, include chicken.” After building, try “swap day 2 lunch for something with rice.”')
    typed_message = st.chat_input('Describe your plan, answer a question, or request an edit',
                                  disabled=disabled, key='plan_builder_chat')
    if typed_message:
        submitted_text = typed_message

if submitted_text is not None:
    st.session_state.pop('plan_builder_error', None)
    try:
        with st.status('Understanding your request…', expanded=False) as status:
            with claude_client(anthropic_key) as client:
                process_message(submitted_text, st.session_state, client,
                                progress=lambda message: status.update(label=message))
            status.update(label='Ready', state='complete')
    except PlanAgentError as error:
        suffix = ' Your previous plan is unchanged.' if st.session_state.current_plan else ''
        st.session_state.plan_builder_error = str(error) + suffix
    show_conversation()
    quota.caption(f'{MAX_GENERATIONS - st.session_state.request_count} of {MAX_GENERATIONS} plan builds or edits remaining this session. Start over clears this conversation and keeps the session limit.')

if st.session_state.plan_blocked:
    st.error('No plan is shown because the request could not pass the exclusion or safety checks. Revise the request to continue.')
    for issue in st.session_state.plan_validation_issues:
        st.write(f'• {issue.message}')
elif st.session_state.current_plan is not None:
    render_plan(st.session_state.current_plan, st.session_state.plan_display_request,
                st.session_state.plan_validation_issues)
else:
    st.caption('Your plan will appear here after any follow-up questions. Plans stay in this session; download a copy to keep them.')

from assistant.widget import assistant_widget
assistant_widget()
