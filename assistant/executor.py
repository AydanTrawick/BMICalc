"""Validate, preview, and execute tools. A write cannot execute without confirmation."""
from copy import deepcopy
from dataclasses import dataclass, field
import logging
from uuid import uuid4

from pydantic import ValidationError

from assistant import db
from assistant.config import AssistantError, today
from assistant.dates import resolve_date_arguments
from assistant.progress import summary
from assistant.tools import MODELS, WRITE_TOOLS
from plan_agent.api import structured_call
from plan_agent.generate import rebuild_groceries
from plan_agent.schemas import Exercise, Meal, MealPlan, PlanRequest, WorkoutPlan
from plan_agent.validate import validate_plan

logger = logging.getLogger(__name__)


@dataclass
class PendingAction:
    user_id: str
    name: str
    arguments: dict
    preview: dict
    prepared: dict = field(default_factory=dict)
    operation_id: str = field(default_factory=lambda: str(uuid4()))
    attempted: bool = False


def arguments_for(name, arguments, user_text='', anchor=None):
    if name not in MODELS:
        raise AssistantError('Unknown assistant tool.')
    try:
        validated = MODELS[name].model_validate(arguments).model_dump()
        return resolve_date_arguments(validated, user_text, anchor)
    except ValidationError as error:
        logger.warning('Invalid %s arguments: %s', name, error.errors(include_input=False))
        raise AssistantError('; '.join(f'{".".join(map(str, item["loc"]))}: {item["msg"]}' for item in error.errors(include_input=False))) from None


def execute_read(name, arguments, user_id, user_text='', anchor=None):
    args = arguments_for(name, arguments, user_text, anchor)
    if name == 'get_todays_date':
        current = anchor or today()
        return {'date': current.isoformat(), 'day_of_week': current.strftime('%A')}
    if name == 'get_logs':
        return db.get_logs(user_id, **args)
    if name == 'get_active_plan':
        return db.get_active_plan(user_id, **args)
    if name == 'get_progress_summary':
        current = anchor or today()
        return summary(db.progress_rows(user_id, current.isoformat()), **args, today=current)
    raise AssistantError('This tool requires a confirmation preview before it can run.')


def _preview_plan(user_id, args, client):
    before = db.get_active_plan(user_id, args['plan_type'])
    if not before:
        raise AssistantError('There is no saved active plan of this type. Open the Builder, generate a plan, and use Save Builder plan in the assistant.')
    stored = before['plan_data']
    if not isinstance(stored, dict) or not stored.get('request') or not stored.get('plan'):
        raise AssistantError('This plan has no saved requirements in the supported format. Save a validated Builder copy first so edits can preserve its restrictions.')
    request = PlanRequest.model_validate(stored['request'])
    schema = MealPlan if args['plan_type'] == 'meal' else WorkoutPlan
    plan = schema.model_validate(stored['plan'])
    days = [day for day in plan.days if day.day_number == args['day_number']]
    if len(days) != 1:
        raise AssistantError('That numbered day is not present in your active plan.')
    day = days[0]
    items = day.meals if isinstance(plan, MealPlan) else day.exercises
    field_name = 'dish' if isinstance(plan, MealPlan) else 'name'
    matches = [index for index, item in enumerate(items) if getattr(item, field_name).casefold() == args['old_item'].casefold()]
    if len(matches) != 1:
        raise AssistantError('The old item must match exactly one dish or exercise on that day. Read the plan and clarify the item.')
    index = matches[0]
    old = items[index]
    new = structured_call(client, Meal if isinstance(plan, MealPlan) else Exercise,
        'Replace exactly one item in this fitness plan. Return JSON matching the schema. Preserve all request constraints, exclusions, sets/volume and calorie target. Supply fresh instructions or form cues appropriate to the replacement, not the old item. Do not change any other item. No medical claims.',
        {'requirements': request.model_dump(), 'day': day.model_dump(), 'old_item': old.model_dump(),
         'new_name': args['new_item'], 'change_description': args['change_description']}, max_tokens=2000)
    items[index] = new
    if isinstance(plan, MealPlan):
        rebuild_groceries(plan)
    issues = validate_plan(plan, request)
    failures = [issue.message for issue in issues if issue.repairable or issue.blocking]
    if failures:
        raise AssistantError('The proposed replacement did not pass plan checks: ' + '; '.join(failures[:5]))
    after = dict(stored, plan=plan.model_dump())
    return {'before': before, 'after': after}, {'day_number': args['day_number'], 'old_item': old.model_dump(),
                                              'new_item': new.model_dump(), 'review_notes': [issue.message for issue in issues]}


def prepare_write(name, arguments, user_id, source='text', user_text='', client=None, anchor=None):
    if not user_id:
        raise AssistantError('Sign in before changing saved activities.')
    if name not in WRITE_TOOLS:
        raise AssistantError('This is not a supported write tool.')
    args = arguments_for(name, arguments, user_text, anchor)
    preview, prepared = dict(args), {'source': source}
    if name == 'delete_log_entry':
        preview = db.get_entry(user_id, args['entry_id'])
    elif name == 'update_active_plan':
        prepared, preview = _preview_plan(user_id, args, client)
    return PendingAction(user_id, name, args, preview, prepared)


def prepare_builder_save(user_id, plan, request):
    issues = validate_plan(plan, request)
    if any(issue.blocking or issue.repairable for issue in issues):
        raise AssistantError('Resolve the Builder plan checks before saving an active copy.')
    data = {'plan': plan.model_dump(), 'request': request.model_dump()}
    expected = db.active_plan_versions(user_id, request.plan_type)
    return PendingAction(user_id, 'save_builder_plan', {'plan_type': request.plan_type},
                         {'title': plan.title, 'plan_type': request.plan_type, 'plan': plan.model_dump(),
                          'replaces_active_plan': bool(expected)}, {'data': data, 'expected': expected})


def execute_write(action, user_id, *, confirmed=False):
    if not confirmed or user_id != action.user_id:
        raise AssistantError('Confirm this action in the signed-in account before it can run.')
    action.attempted = True
    args, name = action.arguments, action.name
    if name.startswith('log_'):
        args = arguments_for(name, args)  # Dates may have aged since the preview.
        details = {key: value for key, value in args.items() if key not in ('date', 'notes')}
        if name == 'log_cardio':
            details['avg_pace'] = None
        return db.log_activity(user_id, name[4:], args['date'], details,
                               action.prepared['source'], args.get('notes'), action.operation_id)
    if name == 'delete_log_entry':
        return db.delete_log_entry(user_id, args['entry_id'], action.operation_id)
    if name == 'update_active_plan':
        return db.update_plan(user_id, action.prepared['before'], action.prepared['after'], action.operation_id)
    if name == 'save_builder_plan':
        return db.save_active_plan(user_id, args['plan_type'], action.prepared['data'], action.prepared['expected'], action.operation_id)
    if name == 'undo':
        undo = action.prepared
        if undo['kind'] == 'delete_log':
            return db.delete_log_entry(user_id, undo['id'], action.operation_id)
        if undo['kind'] == 'restore_log':
            return db.restore_log_entry(user_id, undo['id'], undo['deleted_at'], action.operation_id)
        if undo['kind'] == 'restore_plan':
            return db.update_plan(user_id, undo['before'], undo['plan_data'], action.operation_id)
        if undo['kind'] == 'deactivate_plan':
            return db.deactivate_plan(user_id, undo, action.operation_id)
    raise AssistantError('Unsupported confirmed action.')


def prepare_undo(user_id, last_write):
    if not last_write or not last_write.get('undo') or last_write.get('user_id') != user_id:
        raise AssistantError('There is no recent change to undo in this session.')
    return PendingAction(user_id, 'undo', {}, {'entry_id': last_write['id'], 'action': last_write['undo']['kind']}, deepcopy(last_write['undo']))
