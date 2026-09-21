from unittest.mock import Mock, patch

from assistant.speech import speech_audio, spoken_text, _cached_audio


def test_spoken_text_preserves_the_entire_long_reply():
    reply = 'Saved your run. You ran three miles. ' + 'Extra details. ' * 50 + 'Final sentence.'
    assert spoken_text(reply) == reply
    assert spoken_text('A' * 1000) == 'A' * 1000


def test_spoken_text_removes_formatting_without_dropping_content():
    assert spoken_text('## Plan\n**Start** with [walking](https://example.com).\n'
                       '```text\nThen rest.\n```\nFinish slowly.') == (
        'Plan Start with walking. Then rest. Finish slowly.')


def test_long_reply_is_sent_in_full_and_all_audio_chunks_are_retained():
    _cached_audio.clear()
    reply = 'Training details. ' * 500 + 'This is the final sentence.'
    client = Mock()
    client.text_to_speech.convert.return_value = iter([b'beginning', b'middle', b'end'])
    with patch('assistant.speech.secret_key', return_value='mock-key'), \
         patch('assistant.speech.ElevenLabs', return_value=client):
        assert speech_audio(reply, 'long-reply-user') == (b'beginningmiddleend', None)
        assert client.text_to_speech.convert.call_args.kwargs['text'] == reply
    _cached_audio.clear()


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
