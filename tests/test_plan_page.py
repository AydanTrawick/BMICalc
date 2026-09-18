from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from plan_agent.config import PlanAgentError
from plan_agent.schemas import PlanRequest
from tests.plan_fixtures import meal_plan, workout_plan
from tests.test_extract import response


def open_page():
    app = AppTest.from_file('BMI2.py')
    app.session_state['firstrep_user'] = {
        'id': 'plan-builder-test-user', 'display_name': 'Test User',
        'email': 'plan-builder@example.com', 'role': 'customer',
    }
    app.session_state['_auth_checked_at'] = 1
    return app.run(timeout=30).switch_page('pages/AI_Plan_Builder.py').run(timeout=30)


def test_guest_is_blocked_and_sees_login_prompt():
    app = AppTest.from_file('BMI2.py').run(timeout=30).switch_page('pages/AI_Plan_Builder.py').run(timeout=30)
    assert not app.exception
    assert any('log in' in info.value.lower() for info in app.info)
    assert not app.chat_input
    assert 'messages' not in app.session_state


def test_page_missing_key_has_setup_message_and_no_crash():
    with patch('plan_agent.config.secret_key', return_value=''):
        app = open_page()
    assert not app.exception
    assert any('ANTHROPIC_API_KEY' in warning.value for warning in app.warning)
    assert app.chat_input[0].disabled


def test_page_clarification_build_edit_export_and_reset():
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    plan = meal_plan()
    changed = meal_plan()
    changed.days[1].meals[1].dish = 'Chicken rice pilaf'
    client.messages.create.side_effect = [
        response(dict(plan_type='meal')),
        response(dict(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'], must_include=['chicken'],
                      provided_fields=['days', 'meals_per_day', 'exclusions', 'must_include'])),
        response(plan.model_dump()),
        response(dict(plan_type='meal', provided_fields=[])),
        response(changed.model_dump()),
    ]
    with patch('plan_agent.config.secret_key', return_value='mock-key'), \
         patch('plan_agent.api.claude_client', return_value=client):
        app = open_page()
        app.chat_input[0].set_value('Make me a meal plan').run(timeout=30)
        assert not app.exception
        assert 'how many days' in app.session_state['messages'][-1]['content']
        app.chat_input[0].set_value('3 days, 3 meals, no nuts, include chicken').run(timeout=30)
        assert not app.exception
        assert len(app.tabs) == 4 and app.tabs[-1].label == 'Grocery list', (app.session_state['messages'], [error.value for error in app.error])
        assert len(app.get('download_button')) == 2
        assert app.session_state['request_count'] == 1
        app.chat_input[0].set_value('swap day 2 lunch for something with rice').run(timeout=30)
        assert not app.exception
        assert app.session_state['current_plan'].days[1].meals[1].dish == 'Chicken rice pilaf'
        assert app.session_state['plan_request'].exclusions == ['nuts']
        assert client.messages.create.call_count == 5
        next(button for button in app.button if button.label == 'Start over').click().run(timeout=30)
        assert not app.exception and app.session_state['current_plan'] is None
        assert app.session_state['request_count'] == 2


def test_new_exclusion_hides_old_plan_even_if_generation_fails():
    from plan_agent.agent import process_message
    old = meal_plan()
    old.days[0].meals[0].dish = 'Peanut chicken'
    request = PlanRequest(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'])
    state = {'current_plan': old}
    with patch('plan_agent.agent.extract_request', return_value=request), \
         patch('plan_agent.agent.generate_plan', side_effect=PlanAgentError('offline')):
        try:
            process_message('Also exclude nuts', state, Mock())
        except PlanAgentError:
            pass
    assert state['current_plan'] is None and state['plan_blocked']


def test_workout_page_shows_injury_review_and_exercise_details():
    request = PlanRequest(plan_type='workout', days=4, goal='weight loss', experience_level='beginner',
                          equipment=['bodyweight'], volume='low', injuries_mentioned=True,
                          injuries_or_limits=['wrist pain'])
    with patch('plan_agent.config.secret_key', return_value=''):
        app = open_page()
        app.session_state['current_plan'] = workout_plan()
        app.session_state['plan_display_request'] = request
        app.run()
    assert not app.exception and len(app.tabs) == 4
    assert len(app.dataframe) == 4 and len(app.expander) == 12
    assert any('professional review' in warning.value for warning in app.warning)
    assert len(app.get('download_button')) == 2


def test_voice_requires_confirmation_and_sends_edited_transcript():
    import io
    from tests.test_plan_io import wav_data

    audio = io.BytesIO(wav_data(1))
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.messages.create.return_value = response(dict(plan_type='meal'))
    with patch('plan_agent.config.secret_key', return_value='mock-key'), \
         patch('plan_agent.api.claude_client', return_value=client), \
         patch('streamlit.audio_input', return_value=audio), \
         patch('plan_agent.transcribe.transcribe_audio', return_value='Make me a meal plan') as transcribe:
        app = open_page()
        next(button for button in app.button if button.label == 'Transcribe recording').click().run()
        assert not app.exception and transcribe.call_count == 1
        client.messages.create.assert_not_called()
        app.text_area[0].set_value('Make me a vegetarian meal plan')
        next(button for button in app.button if button.label == 'Send edited transcript').click().run()
        assert not app.exception
        assert app.session_state['messages'][0]['content'] == 'Make me a vegetarian meal plan'
        next(button for button in app.button if button.label == 'Transcribe recording').click().run()
        assert transcribe.call_count == 1
