"""Validate microphone WAV recordings before sending them to Whisper."""
import io
import wave

from openai import OpenAI

from plan_agent.api import call_with_retry
from plan_agent.config import MAX_AUDIO_BYTES, MAX_AUDIO_SECONDS, TRANSCRIPTION_MODEL, PlanAgentError


def audio_duration(data):
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise PlanAgentError('Please record a message of up to 60 seconds.')
    try:
        with wave.open(io.BytesIO(data), 'rb') as recording:
            duration = recording.getnframes() / recording.getframerate()
            expected = recording.getnframes() * recording.getnchannels() * recording.getsampwidth()
            if len(recording.readframes(recording.getnframes())) != expected:
                raise ValueError('Incomplete WAV')
    except (wave.Error, EOFError, ValueError, ZeroDivisionError):
        raise PlanAgentError('This recording could not be read. Please record it again.') from None
    if duration <= 0 or duration > MAX_AUDIO_SECONDS:
        raise PlanAgentError('Record between 1 and 60 seconds, then try again.')
    return duration


def transcribe_audio(data, api_key='', client=None):
    audio_duration(data)
    if client is None and not api_key:
        raise PlanAgentError('Add OPENAI_API_KEY to Streamlit secrets to use voice input.')
    owned_client = client is None
    client = client or OpenAI(api_key=api_key, max_retries=0, timeout=60.0)
    try:
        result = call_with_retry(lambda: client.audio.transcriptions.create(
            model=TRANSCRIPTION_MODEL, file=('request.wav', data, 'audio/wav'), response_format='text',
        ), 'Whisper')
    finally:
        if owned_client:
            client.close()
    text = (result if isinstance(result, str) else result.text).strip()
    if not text:
        raise PlanAgentError('No speech was detected. Please try again or type your request.')
    return text
