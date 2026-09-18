"""Conversation, clarification, generation, and bounded validation/repair flow."""
from copy import deepcopy

from plan_agent.allergens import exclusion_matches
from plan_agent.config import (
    MAX_CLARIFICATIONS, MAX_GENERATIONS, MAX_INPUT_CHARS, MAX_REPAIRS,
    MIN_DAILY_CALORIES, PROFESSIONAL_NOTE, PlanAgentError,
)
from plan_agent.extract import extract_request, missing_fields
from plan_agent.generate import generate_plan
from plan_agent.schemas import PlanRequest
from plan_agent.validate import validate_plan

STATE_DEFAULTS = {
    'messages': [], 'plan_request': None, 'current_plan': None,
    'clarification_rounds': 0, 'request_count': 0, 'last_transcript': '',
    'plan_validation_issues': [], 'plan_blocked': False,
    'plan_display_request': None, 'plan_edit_context': [],
}


def initialize_state(state):
    for name, value in STATE_DEFAULTS.items():
        if name not in state:
            state[name] = deepcopy(value)


def start_over(state):
    # Reset this feature, not login/food/workout logs. Keep the session cost cap.
    count = state.get('request_count', 0)
    for name in list(state):
        if name in STATE_DEFAULTS or name.startswith('plan_builder_'):
            del state[name]
    initialize_state(state)
    state['request_count'] = count


def clarification_question(request):
    if request.plan_type == 'unknown':
        return 'Would you like a meal plan or workout plan, and—if a workout—do you have any injuries, pain, or limitations?'
    labels = {
        'days': 'how many days (1–7)',
        'meals_per_day': 'how many meals per day (1–6)',
        'goal': 'your goal', 'experience_level': 'your experience level',
        'equipment': 'available equipment (or bodyweight only)',
        'injuries_or_limits': 'any injuries, pain, health conditions, or limitations (or “none”)',
    }
    return 'Please tell me ' + '; '.join(labels[name] for name in request.missing_fields) + '.'


def finalize_request(request):
    request = request.model_copy(deep=True)
    defaults = {'plan_type': 'meal', 'days': 3, 'meals_per_day': 3,
                'goal': 'general fitness', 'experience_level': 'beginner', 'equipment': ['bodyweight']}
    for field in missing_fields(request):
        if field == 'injuries_or_limits':
            request.assumptions.append('Injury status was not provided after clarification. Have a professional review the plan before using it if you have any limitations.')
        else:
            value = defaults[field]
            setattr(request, field, value)
            request.assumptions.append(f'Default used because {field.replace("_", " ")} was not provided: {value}.')
    # Unknown type may just have become meal; fill that type's required fields too.
    for field in missing_fields(request):
        if field in defaults and not getattr(request, field):
            value = defaults[field]
            setattr(request, field, value)
            request.assumptions.append(f'Default used because {field.replace("_", " ")} was not provided: {value}.')
    if request.plan_type == 'workout' and request.volume is None:
        request.volume = 'low'
        request.assumptions.append('No training volume was specified; a low-volume routine was used.')
    if request.calorie_target is not None and request.calorie_target < MIN_DAILY_CALORIES:
        requested = request.calorie_target
        request.calorie_target = MIN_DAILY_CALORIES
        request.assumptions.append(f'The requested {requested}-calorie target was raised to 1,200 calories/day, the minimum this builder supports. This minimum is not a personalized recommendation.')
    request.assumptions = list(dict.fromkeys(request.assumptions))
    request.missing_fields = []
    return request


def _add_required_notes(plan, request):
    extra = list(request.assumptions)
    if request.injuries_or_limits:
        extra.append(PROFESSIONAL_NOTE)
    if request.plan_type == 'meal':
        extra.append('Calories and macros are estimates, not laboratory measurements or USDA-verified totals.')
        if not request.calorie_target:
            extra.append('No calorie target was provided; the portions are illustrative rather than a personalized calorie prescription.')
    plan.notes = list(dict.fromkeys([*plan.notes, *extra]))
    return plan


def build_checked_plan(request, client, current_plan=None, change_request=None, progress=None):
    progress = progress or (lambda message: None)
    progress('Building plan…')
    plan = generate_plan(request, client, current_plan, change_request, progress=progress)
    for repair in range(MAX_REPAIRS + 1):
        progress('Checking plan…')
        plan = _add_required_notes(plan, request)
        issues = validate_plan(plan, request)
        failures = [issue for issue in issues if issue.repairable]
        if not failures or repair == MAX_REPAIRS:
            return (None if any(issue.blocking for issue in issues) else plan), issues
        progress(f'Fixing plan ({repair + 1} of {MAX_REPAIRS})…')
        try:
            plan = generate_plan(request, client, plan, change_request,
                                 errors=[issue.message for issue in failures], progress=progress)
        except PlanAgentError:
            # Revalidate the last complete candidate; only safe candidates can render.
            from plan_agent.validate import RuleIssue
            issues.append(RuleIssue('repair_unavailable', 'The correction service could not finish. The issues below remain unresolved.', repairable=False))
            return (None if any(issue.blocking for issue in issues) else plan), issues
    raise AssertionError('Unreachable repair state')


def process_message(text, state, client, progress=None):
    initialize_state(state)
    text = text.strip()
    if not text:
        raise PlanAgentError('Please type a request or record a clearer message.')
    if len(text) > MAX_INPUT_CHARS:
        raise PlanAgentError(f'Please keep each message under {MAX_INPUT_CHARS:,} characters.')
    if state['request_count'] >= MAX_GENERATIONS:
        raise PlanAgentError('You have reached 10 plan builds or edits for this session. You can still view and download your current plan.')
    progress = progress or (lambda message: None)
    state['messages'].append({'role': 'user', 'content': text})
    progress('Understanding your request…')
    request = extract_request(text, state['messages'][:-1], client, state['plan_request'])
    state['plan_request'] = request
    state['plan_edit_context'].append(text)
    if state['current_plan'] is not None:
        previous_issues = validate_plan(state['current_plan'], request)
        if any(issue.blocking for issue in previous_issues):
            state['current_plan'] = None
            state['plan_blocked'] = True
            state['plan_validation_issues'] = previous_issues
    if request.missing_fields and state['clarification_rounds'] < MAX_CLARIFICATIONS:
        question = clarification_question(request)
        state['clarification_rounds'] += 1
        state['messages'].append({'role': 'assistant', 'content': question})
        return
    request = finalize_request(request)
    state['plan_request'] = request
    conflicts = [food for food in request.must_include
                 if any(exclusion_matches(food, exclusion) for exclusion in request.exclusions)]
    if conflicts:
        # Contradictory inclusions cannot override a strict exclusion.
        state['current_plan'] = None
        state['plan_blocked'] = True
        state['messages'].append({'role': 'assistant', 'content': 'I cannot include ' + ', '.join(conflicts) + ' while respecting your exclusions. Please change the required foods, or start over to change exclusions.'})
        return
    # Count top-level builds/edits including failed attempts; repair calls are bounded
    # inside a build. Clarifying answers alone do not consume a generation.
    state['request_count'] += 1
    plan, issues = build_checked_plan(request, client, state['current_plan'],
                                      '\n'.join(state['plan_edit_context']), progress)
    state['current_plan'] = plan
    state['plan_display_request'] = request
    state['plan_validation_issues'] = issues
    state['plan_blocked'] = plan is None
    state['plan_edit_context'] = []
    # A later edit or a different plan gets its own bounded clarification cycle.
    state['clarification_rounds'] = 0
    if plan is None:
        reply = 'I could not produce a plan that passes the exclusion and minimum-calorie checks. The plan and downloads are hidden. Please revise your request and try again.'
    elif issues:
        reply = 'Your plan is ready for review, with the unresolved checks listed below.'
    else:
        reply = 'Your plan is ready and passed the automated checks. You can request changes or download it below.'
    state['messages'].append({'role': 'assistant', 'content': reply})
