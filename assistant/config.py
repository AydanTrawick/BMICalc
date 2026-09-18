from datetime import datetime
from zoneinfo import ZoneInfo

from plan_agent.config import PLAN_MODEL, PlanAgentError, secret_key

MODEL = PLAN_MODEL
TTS_MODEL = 'eleven_turbo_v2_5'
MAX_MESSAGES = 30
MAX_LOOPS = 5
MAX_TOKENS = 2000
MAX_TEXT = 4000


class AssistantError(PlanAgentError):
    pass


def today():
    return datetime.now(ZoneInfo(secret_key('ASSISTANT_TIMEZONE') or 'America/New_York')).date()
