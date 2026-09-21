"""Full ElevenLabs replies, with a cache scoped to the user and credential hash."""
import hashlib
import logging
import re

import streamlit as st
from elevenlabs.client import ElevenLabs

from assistant.config import TTS_MODEL, secret_key

logger = logging.getLogger(__name__)


def spoken_text(text):
    """Remove display formatting while retaining the entire reply for speech."""
    text = re.sub(r'```[^\n`]*\n([\s\S]*?)```', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[*#`|]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


@st.cache_data(ttl=3600, max_entries=128, show_spinner=False)
def _cached_audio(text_hash, user_scope, credential_hash, voice_id, _text, _api_key):
    client = ElevenLabs(api_key=_api_key, timeout=120)
    response = client.text_to_speech.convert(voice_id=voice_id, text=_text,
                                             model_id=TTS_MODEL, output_format='mp3_44100_128')
    return b''.join(response)


def speech_audio(text, user_scope, enabled=True):
    if not enabled:
        return None, None
    key, voice = secret_key('ELEVENLABS_API_KEY'), secret_key('ELEVENLABS_VOICE_ID')
    if not key or not voice:
        return None, 'Voice unavailable: configure ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.'
    full_text = spoken_text(text)
    if not full_text:
        return None, None
    try:
        audio = _cached_audio(hashlib.sha256(full_text.encode()).hexdigest(), user_scope,
                              hashlib.sha256(key.encode()).hexdigest(), voice, full_text, key)
        return (audio, None) if audio else (None, 'Voice unavailable for this reply.')
    except Exception:
        logger.exception('ElevenLabs speech generation failed')
        return None, 'Voice unavailable right now. Your text reply is still here.'
