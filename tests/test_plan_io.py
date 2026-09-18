import io
import wave
from unittest.mock import Mock, patch

import anthropic
import httpx
import pytest

from plan_agent.api import call_with_retry
from plan_agent.config import DISCLAIMER, PlanAgentError
from plan_agent.export import export_plan
from plan_agent.schemas import PlanRequest
from plan_agent.transcribe import transcribe_audio
from tests.plan_fixtures import meal_plan, workout_plan


def wav_data(seconds):
    output = io.BytesIO()
    with wave.open(output, 'wb') as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(16000)
        recording.writeframes(b'\0\0' * int(16000 * seconds))
    return output.getvalue()


def test_voice_length_validated_before_api_and_whisper_contract():
    client = Mock()
    for data in [wav_data(61), b'not audio', wav_data(1)[:-20]]:
        with pytest.raises(PlanAgentError):
            transcribe_audio(data, client=client)
    client.audio.transcriptions.create.assert_not_called()
    client.audio.transcriptions.create.return_value = '  Three day meal plan  '
    assert transcribe_audio(wav_data(60), client=client) == 'Three day meal plan'
    assert client.audio.transcriptions.create.call_args.kwargs['model'] == 'whisper-1'
    client.audio.transcriptions.create.return_value = ' '
    with pytest.raises(PlanAgentError, match='No speech'):
        transcribe_audio(wav_data(1), client=client)


def test_network_retry_is_bounded_and_friendly():
    error = anthropic.APIConnectionError(request=httpx.Request('POST', 'https://example.invalid'))
    operation = Mock(side_effect=[error, 'success'])
    with patch('plan_agent.api.time.sleep'):
        assert call_with_retry(operation, 'Claude') == 'success'
        operation.side_effect = [error, error]
        with pytest.raises(PlanAgentError, match='after a retry'):
            call_with_retry(operation, 'Claude')
    assert operation.call_count == 4


def test_exports_include_detail_disclaimers_and_review_warnings():
    request = PlanRequest(plan_type='workout', days=4, volume='low', session_length_minutes=10)
    text = export_plan(workout_plan(), request)
    assert 'Unresolved checks' in text and 'exceeds the 10-minute limit' in text
    assert 'Easier:' in text and 'Cooldown:' in text and 'RPE 6' in text
    assert all(disclaimer in text for disclaimer in DISCLAIMER)
    request = PlanRequest(plan_type='meal', days=3, meals_per_day=3)
    text = export_plan(meal_plan(), request, plain_text=True)
    assert not text.startswith('#') and 'Grocery list' in text and 'Protein 35 g' in text


def test_exports_recheck_exclusions_and_calorie_floor():
    request = PlanRequest(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'])
    plan = meal_plan()
    plan.days[0].meals[0].dish = 'Peanut rice'
    with pytest.raises(PlanAgentError):
        export_plan(plan, request)
    plan = meal_plan()
    for meal in plan.days[0].meals:
        meal.calories = 100
    with pytest.raises(PlanAgentError):
        export_plan(plan, request)
