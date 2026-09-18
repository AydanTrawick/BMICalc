"""Interpret user input and preserve earlier requirements during follow-ups."""
from plan_agent.api import structured_call
from plan_agent.config import MAX_INPUT_CHARS, PlanAgentError
from plan_agent.prompts import EXTRACTION_SYSTEM
from plan_agent.schemas import PlanRequest


def missing_fields(request):
    if request.plan_type == 'unknown':
        return ['plan_type']
    required = ['days', 'meals_per_day'] if request.plan_type == 'meal' else [
        'days', 'goal', 'experience_level', 'equipment']
    missing = [name for name in required if not getattr(request, name)]
    if request.plan_type == 'workout' and not request.injuries_mentioned:
        missing.append('injuries_or_limits')
    return missing


def merge_requirements(previous, extracted):
    if previous is None:
        merged = extracted.model_copy(deep=True)
    else:
        data = previous.model_dump()
        supplied = set(extracted.provided_fields)
        if not supplied:
            # A compliant extractor supplies provided_fields. Preserve the earlier
            # request rather than allowing empty/default output to erase it.
            supplied = {key for key in extracted.model_fields_set
                        if getattr(extracted, key) not in (None, [], '', 'unknown', False)}
        for field in supplied:
            if field in PlanRequest.model_fields and field not in {'assumptions', 'missing_fields', 'provided_fields', 'exclusions'}:
                data[field] = getattr(extracted, field)
        # Exclusions remain strict for this conversation, even during swaps.
        data['exclusions'] = list(dict.fromkeys([*previous.exclusions, *extracted.exclusions]))
        data['injuries_mentioned'] = previous.injuries_mentioned or extracted.injuries_mentioned or bool(extracted.injuries_or_limits)
        data['provided_fields'] = extracted.provided_fields
        merged = PlanRequest.model_validate(data)
    merged.injuries_mentioned = merged.injuries_mentioned or bool(merged.injuries_or_limits)
    merged.missing_fields = missing_fields(merged)
    return merged


def extract_request(text, history, client, previous=None):
    text = text.strip()
    if not text:
        raise PlanAgentError('Please describe the plan you want, or try recording again.')
    if len(text) > MAX_INPUT_CHARS:
        raise PlanAgentError(f'Please keep each message under {MAX_INPUT_CHARS:,} characters.')
    extracted = structured_call(client, PlanRequest, EXTRACTION_SYSTEM, {
        'latest_user_message': text,
        'conversation': history[-20:],
        'previous_request': previous.model_dump() if previous else None,
    }, max_tokens=2000)
    return merge_requirements(previous, extracted)
