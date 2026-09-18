"""Bounded provider calls and schema retries, with redacted diagnostics."""
import json
import logging
import time

import anthropic
import openai
from pydantic import ValidationError

from plan_agent.config import PLAN_MODEL, PlanAgentError
from plan_agent.prompts import with_schema

logger = logging.getLogger(__name__)
PROVIDER_ERRORS = (anthropic.APIError, openai.APIError)


def call_with_retry(operation, provider):
    for attempt in range(2):
        try:
            return operation()
        except PROVIDER_ERRORS as error:
            status = getattr(error, 'status_code', None)
            logger.warning('%s API failure: %s, status=%s, attempt=%s',
                           provider, type(error).__name__, status, attempt + 1)
            if status in (401, 403):
                raise PlanAgentError(f'{provider} could not authorize the request. Check its API key and account access.') from None
            if status == 404:
                raise PlanAgentError(f'{provider} could not access the configured model. Check model access for this account.') from None
            if attempt == 0:
                time.sleep(.25)
                continue
            raise PlanAgentError(f'{provider} could not complete the request after a retry. Please try again shortly.') from None
    raise AssertionError('Unreachable retry state')


def claude_client(api_key):
    if not api_key:
        raise PlanAgentError('Add ANTHROPIC_API_KEY to Streamlit secrets to build plans.')
    return anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=90.0)


def structured_call(client, schema, instruction, payload, max_tokens):
    messages = [{'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}]
    for attempt in range(2):
        response = call_with_retry(lambda: client.messages.create(
            model=PLAN_MODEL, max_tokens=max_tokens, thinking={'type': 'disabled'},
            system=with_schema(instruction, schema), messages=messages,
        ), 'Claude')
        raw = '\n'.join(block.text for block in response.content if getattr(block, 'type', None) == 'text')
        clean = raw.strip()
        if clean.startswith('```'):
            clean = clean.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        try:
            if response.stop_reason == 'max_tokens':
                raise ValueError('The JSON response was cut off by the output limit. Use shorter instructions and summaries while keeping every required field.')
            return schema.model_validate_json(clean)
        except (ValidationError, ValueError) as error:
            detail = (json.dumps(error.errors(include_input=False, include_url=False), default=str)
                      if isinstance(error, ValidationError) else str(error))
            logger.warning('Invalid %s JSON (attempt %s): %s', schema.__name__, attempt + 1, detail)
            if attempt == 0:
                messages.extend([{'role': 'assistant', 'content': raw or '{}'},
                                 {'role': 'user', 'content': 'Return corrected complete JSON. Schema/parse errors: ' + detail}])
                continue
            raise PlanAgentError('The plan service returned incomplete or invalid data twice. Please try again with a shorter request.') from None
