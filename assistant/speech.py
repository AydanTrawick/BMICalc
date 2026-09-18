"""Short ElevenLabs replies, with a cache scoped to the user and credential hash."""
import hashlib
import logging
import re

import streamlit as st
from elevenlabs.client import ElevenLabs

from assistant.config import TTS_MODEL, secret_key

logger = logging.getLogger(__name__)


def spoken_summary(text):
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'[*#`|]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    selected = []
    for sentence in sentences[:2]:
        if len(' '.join([*selected, sentence])) > 300:
            break
        selected.append(sentence)
    return ' '.join(selected) or 'Your reply is ready. Please read the details in the chat.'


@st.cache_data(ttl=3600, max_entries=128, show_spinner=False)
def _cached_audio(text_hash, user_scope, credential_hash, voice_id, _text, _api_key):
    client = ElevenLabs(api_key=_api_key, timeout=30)
    response = client.text_to_speech.convert(voice_id=voice_id, text=_text,
                                             model_id=TTS_MODEL, output_format='mp3_44100_128')
    return b''.join(response)


def speech_audio(text, user_scope, enabled=True):
    if not enabled:
        return None, None
    key, voice = secret_key('ELEVENLABS_API_KEY'), secret_key('ELEVENLABS_VOICE_ID')
    if not key or not voice:
        return None, 'Voice unavailable: configure ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.'
    short = spoken_summary(text)
    try:
        audio = _cached_audio(hashlib.sha256(short.encode()).hexdigest(), user_scope,
                              hashlib.sha256(key.encode()).hexdigest(), voice, short, key)
        return (audio, None) if audio else (None, 'Voice unavailable for this reply.')
    except Exception:
        logger.exception('ElevenLabs speech generation failed')
        return None, 'Voice unavailable right now. Your text reply is still here.'
