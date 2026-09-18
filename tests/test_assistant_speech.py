from unittest.mock import Mock, patch

from assistant.speech import speech_audio, spoken_summary, _cached_audio


def test_spoken_summary_is_short_and_does_not_read_a_full_plan():
    result = spoken_summary('Saved your run. You ran three miles. ' + 'Extra details. ' * 50)
    assert result == 'Saved your run. You ran three miles.' and len(result) <= 300
    assert len(spoken_summary('A' * 1000)) <= 300


def test_tts_disabled_missing_config_failure_and_cache():
    with patch('assistant.speech.ElevenLabs') as sdk:
        assert speech_audio('Hello.', 'u1', enabled=False) == (None, None)
        sdk.assert_not_called()
    with patch('assistant.speech.secret_key', return_value=''):
        assert 'configure' in speech_audio('Hello.', 'u1')[1]
    _cached_audio.clear()
    client = Mock()
    client.text_to_speech.convert.return_value = [b'audio']
    with patch('assistant.speech.secret_key', return_value='mock-key'), patch('assistant.speech.ElevenLabs', return_value=client):
        assert speech_audio('Hello.', 'u1') == (b'audio', None)
        assert speech_audio('Hello.', 'u1') == (b'audio', None)
        assert client.text_to_speech.convert.call_count == 1
        assert client.text_to_speech.convert.call_args.kwargs['model_id'] == 'eleven_turbo_v2_5'
        # Different users cannot retrieve each other's cached health-related audio.
        speech_audio('Hello.', 'u2')
        assert client.text_to_speech.convert.call_count == 2
    with patch('assistant.speech.secret_key', return_value='mock-key'), patch('assistant.speech.ElevenLabs', side_effect=RuntimeError('offline')):
        audio, note = speech_audio('Different reply.', 'u1')
        assert audio is None and 'Voice unavailable' in note
    _cached_audio.clear()
