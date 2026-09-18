"""Explicit provider choices, bounded work, and shared notices."""

TRANSCRIPTION_MODEL = 'whisper-1'
PLAN_MODEL = 'claude-sonnet-5'
MAX_AUDIO_SECONDS = 60
MAX_AUDIO_BYTES = 24 * 1024 * 1024
MAX_GENERATIONS = 10
MAX_CLARIFICATIONS = 2
MAX_REPAIRS = 2
GENERATION_TOKENS = 6000
MAX_INPUT_CHARS = 6000
MIN_DAILY_CALORIES = 1200
DISCLAIMER = (
    'This plan is general information, not medical or dietary advice.',
    'If you have food allergies, always check ingredient labels.',
    'Consult a doctor before starting a new exercise program, especially with injuries or health conditions.',
)
PROFESSIONAL_NOTE = 'Discuss your reported injuries, pain, or health conditions with a qualified professional before following this plan.'


class PlanAgentError(ValueError):
    """A message safe to show to the user, without provider credentials."""


def secret_key(name):
    import streamlit as st
    try:
        value = st.secrets.get(name, '')
    except FileNotFoundError:
        return ''
    return value.strip() if isinstance(value, str) else ''
