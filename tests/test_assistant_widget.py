from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

from tests.test_assistant_agent import call, response, text

SOURCE = '''
import streamlit as st
from assistant.widget import assistant_widget
st.session_state['firstrep_user'] = {'id': 'widget-user'}
st.session_state['_auth_checked_at'] = 1
st.session_state['base_runs'] = st.session_state.get('base_runs', 0) + 1
st.title('Test page')
assistant_widget()
'''


def test_dialog_confirmation_edit_and_fragment_navigation_state():
    client = MagicMock()
    client.__enter__.return_value = client
    client.messages.create.side_effect = [response(call()), response(text('Logged a four-mile run today.'))]
    with patch('assistant.widget.secret_key', return_value='mock-key'), \
         patch('assistant.widget.claude_client', return_value=client), \
         patch('assistant.agent.db.load_messages', return_value=[]), \
         patch('assistant.agent.db.save_message', return_value=1), \
         patch('assistant.agent.db.get_active_plan', return_value=None), \
         patch('assistant.executor.db.log_activity', return_value={'id': 17, 'kind': 'log', 'undo': {'kind': 'delete_log', 'id': 17}}) as write, \
         patch('assistant.widget.speech_audio', return_value=(None, None)) as speech:
        app = AppTest.from_string(SOURCE).run(timeout=30)
        app.button(key='training_assistant_launcher').click().run(timeout=30)
        assert not app.exception
        app.toggle(key='training_speak_toggle').set_value(False).run()
        app.chat_input(key='training_chat_input').set_value('Log a three mile run today').run(timeout=30)
        assert not app.exception
        # AppTest simulates full reruns; the native browser exercises fragment reruns.
        write.assert_not_called()
        speech.assert_not_called()
        next(button for button in app.button if button.label == 'Edit').click().run()
        next(field for field in app.text_input if field.label == 'Distance').set_value('4')
        next(button for button in app.button if button.label == 'Review edited action').click().run(timeout=30)
        assert not app.exception
        # AppTest retains stale form elements after an explicit rerun; rebuild its
        # tree without resubmitting those removed widgets (a browser removes them).
        app._run(timeout=30)
        next(button for button in app.button if button.label == 'Confirm').click().run(timeout=30)
        assert not app.exception and write.call_count == 1
        assert write.call_args.args[3]['distance'] == 4
        assert speech.call_args.kwargs['enabled'] is False
        assert app.session_state['last_write']['id'] == 17
        # A full page rerun retains the conversation even though the dialog closes.
        app.run()
        app.button(key='training_assistant_launcher').click().run()
        assert not app.exception and len(app.session_state['training_messages']) >= 3


GUEST_SOURCE = '''
import streamlit as st
from assistant.widget import assistant_widget
st.session_state['_auth_checked_at'] = 1
st.title('Test page')
assistant_widget()
'''


def test_guest_sees_login_prompt_instead_of_chat():
    app = AppTest.from_string(GUEST_SOURCE).run(timeout=30)
    app.button(key='training_assistant_launcher').click().run(timeout=30)
    assert not app.exception
    assert any('log in' in info.value.lower() for info in app.info)
    assert not app.chat_input
    assert 'training_messages' not in app.session_state


def test_widget_does_not_call_providers_when_closed():
    with patch('assistant.widget.claude_client') as client, patch('assistant.widget.speech_audio') as speech:
        app = AppTest.from_string(SOURCE).run(timeout=30)
    assert not app.exception
    client.assert_not_called()
    speech.assert_not_called()


def test_voice_clip_is_transcribed_once_and_the_input_key_changes():
    import io
    from tests.test_plan_io import wav_data

    client = MagicMock()
    client.__enter__.return_value = client
    client.messages.create.return_value = response(call())
    seen_keys = []
    def recording(label, **kwargs):
        seen_keys.append(kwargs['key'])
        return io.BytesIO(wav_data(1)) if kwargs['key'] == 'training_recording_0' else None
    with patch('assistant.widget.secret_key', return_value='mock-key'), \
         patch('assistant.widget.claude_client', return_value=client), \
         patch('assistant.agent.db.load_messages', return_value=[]), \
         patch('assistant.agent.db.save_message', return_value=1), \
         patch('assistant.agent.db.get_active_plan', return_value=None), \
         patch('streamlit.audio_input', side_effect=recording), \
         patch('assistant.widget.transcribe_audio', return_value='Log a three mile run today') as transcribe, \
         patch('assistant.widget.speech_audio') as speech:
        app = AppTest.from_string(SOURCE).run(timeout=30)
        app.button(key='training_assistant_launcher').click().run(timeout=30)
        assert not app.exception and transcribe.call_count == 1
        assert app.session_state['training_audio_version'] == 1
        assert app.session_state['pending_action'].source == 'voice'
        assert {'training_recording_0', 'training_recording_1'} <= set(seen_keys)
        speech.assert_not_called()
