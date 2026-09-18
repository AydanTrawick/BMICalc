"""Bounded tool loop with resumable, per-action confirmation and durable history."""
from dataclasses import dataclass, field
import json
import logging
import re

from pydantic import ValidationError

from assistant import db
from assistant.config import AssistantError, MAX_LOOPS, MAX_MESSAGES, MAX_TEXT, MAX_TOKENS, MODEL, today
from assistant.executor import execute_read, execute_write, prepare_write, prepare_undo
from assistant.prompts import system_prompt
from assistant.tools import TOOL_SCHEMAS, WRITE_TOOLS
from plan_agent.api import call_with_retry
from plan_agent.config import PlanAgentError

logger = logging.getLogger(__name__)


@dataclass
class PendingTurn:
    user_id: str | None
    messages: list
    actions: list
    results: list
    user_text: str
    source: str
    iterations: int
    tool_audit: list = field(default_factory=list)


def initialize(state, user_id):
    owner = user_id or 'guest'
    if state.get('training_owner') != owner:
        for key in list(state):
            if (key.startswith('training_') and key != 'training_dialog_open') or key in ('pending_action', 'last_write'):
                del state[key]
        state.update(training_owner=owner, training_messages=[], training_count=0,
                     pending_action=None, last_write=None, training_loaded=False, training_audio_version=0,
                     training_speak_enabled=True)
    if not state['training_loaded']:
        state['training_messages'] = db.load_messages(user_id) if user_id else []
        state['training_loaded'] = True


def append_message(state, user_id, role, content, metadata=None):
    message = {'role': role, 'content': content, 'tool_calls': metadata}
    # Keep the local reply even if persisting it fails after a successful write.
    state['training_messages'].append(message)
    if user_id:
        try:
            message['id'] = db.save_message(user_id, role, content, metadata)
        except AssistantError:
            state['training_notice'] = 'This conversation message could not be saved. Any confirmed activity changes retain their database receipts.'
    return message


def clear_conversation(state, user_id):
    pending = state.get('pending_action')
    if pending and any(item['action'].attempted for item in pending.actions):
        raise AssistantError('Resolve the attempted save with Confirm or Cancel before clearing the conversation.')
    if user_id:
        db.clear_conversation(user_id)
    state['training_messages'] = []
    state['pending_action'] = None
    state.pop('training_resume', None)
    state.pop('training_audio', None)
    state.pop('training_notice', None)
    state['training_audio_version'] += 1
    # Keep the cost counter and last-write undo record across a conversation clear.


def _result(identifier, content, error=False):
    return {'type': 'tool_result', 'tool_use_id': identifier,
            'content': json.dumps(db.plain(content)), 'is_error': error}


def _system(user_id, state):
    titles = []
    if user_id:
        for kind in ('workout', 'meal'):
            try:
                plan = db.get_active_plan(user_id, kind)
                if plan:
                    titles.append(plan['title'])
            except AssistantError:
                titles.append('Saved plan lookup unavailable')
                break
    last = state.get('last_write')
    context = {key: last[key] for key in ('id', 'kind') if key in last} if last else None
    return system_prompt(today(), titles, context)


def _finish(text, turn, state):
    append_message(state, turn.user_id, 'assistant', text, {'tools': turn.tool_audit})
    state.pop('training_resume', None)
    return text


def _loop(turn, state, client):
    if client is None:
        state['training_resume'] = turn
        raise AssistantError('Add ANTHROPIC_API_KEY to get a reply. Any changes already listed as confirmed remain saved.')
    while turn.iterations < MAX_LOOPS:
        turn.iterations += 1
        state['training_resume'] = turn
        response = call_with_retry(lambda: client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, thinking={'type': 'disabled'},
            system=_system(turn.user_id, state), messages=turn.messages, tools=TOOL_SCHEMAS,
        ), 'Claude')
        blocks = [block.model_dump(exclude_none=True) if hasattr(block, 'model_dump') else dict(vars(block)) for block in response.content]
        blocks = [block for block in blocks if block.get('type') in ('text', 'tool_use')]
        text = '\n'.join(block['text'] for block in blocks if block['type'] == 'text').strip()
        calls = [block for block in blocks if block['type'] == 'tool_use']
        if response.stop_reason == 'max_tokens':
            return _finish('The reply reached its size limit before it was complete. No new proposed actions were executed; please ask for one item at a time.', turn, state)
        if not calls:
            return _finish(text or 'Please rephrase your request with a little more detail.', turn, state)
        turn.messages.append({'role': 'assistant', 'content': blocks})
        turn.results = []
        turn.actions = []
        for index, call in enumerate(calls):
            try:
                if index >= 10:
                    raise AssistantError('Please request at most ten actions at once.')
                name, arguments = call['name'], call['input']
                if name in WRITE_TOOLS:
                    action = prepare_write(name, arguments, turn.user_id, turn.source, turn.user_text, client)
                    turn.actions.append({'tool_id': call['id'], 'action': action})
                else:
                    result = execute_read(name, arguments, turn.user_id, turn.user_text)
                    turn.results.append(_result(call['id'], result))
                    turn.tool_audit.append({'name': name, 'result': result})
            except (AssistantError, PlanAgentError, ValidationError) as error:
                logger.warning('Assistant tool %s rejected: %s', call.get('name'), error)
                turn.results.append(_result(call['id'], {'error': str(error)}, True))
        if turn.actions:
            state['pending_action'] = turn
            state.pop('training_resume', None)
            append_message(state, turn.user_id, 'assistant', 'Please review the proposed change below. Nothing in this preview has been saved yet.',
                           {'pending': [{'name': item['action'].name, 'preview': item['action'].preview} for item in turn.actions]})
            return None
        turn.messages.append({'role': 'user', 'content': turn.results})
    return _finish('I reached the five-step limit for this request. Please ask a narrower question. Only changes you explicitly confirmed have been saved.', turn, state)


def begin(text, state, user_id, client, source='text'):
    initialize(state, user_id)
    if state.get('pending_action'):
        raise AssistantError('Confirm, edit, or cancel the pending action first.')
    if state['training_count'] >= MAX_MESSAGES:
        raise AssistantError('You have reached 30 assistant requests in this session. You can still confirm pending actions and undo recent changes.')
    text = text.strip()
    if not text or len(text) > MAX_TEXT:
        raise AssistantError('Please send a request between 1 and 4,000 characters.')
    state['training_count'] += 1
    context = [{'role': item['role'], 'content': item['content']} for item in state['training_messages'][-20:]]
    append_message(state, user_id, 'user', text)
    turn = PendingTurn(user_id, context + [{'role': 'user', 'content': text}], [], [], text, source, 0)
    # Exact undo phrases bind to the actual last write, including plan changes.
    if re.fullmatch(r'(?:actually\s+)?(?:undo|delete)\s+(?:that(?:\s+last\s+one)?|the\s+last\s+one)[.!]?', text.lower()):
        last = state.get('last_write')
        if 'delete' in text.lower():
            if not last or last.get('kind') not in ('log', 'restore'):
                raise AssistantError('The most recent change is not an active log entry. Use “undo that” to reverse a different kind of change.')
            action = prepare_write('delete_log_entry', {'entry_id': last['id']}, user_id)
        else:
            action = prepare_undo(user_id, last)
        turn.actions = [{'tool_id': None, 'action': action}]
        state['pending_action'] = turn
        return None
    return _loop(turn, state, client)


def resolve_pending(state, user_id, client, confirm):
    turn = state.get('pending_action')
    if not turn or turn.user_id != user_id:
        raise AssistantError('This pending action does not belong to the signed-in account.')
    item = turn.actions[0]
    action = item['action']
    if confirm:
        result = execute_write(action, user_id, confirmed=True)
        state['last_write'] = dict(result, user_id=user_id)
        receipt = f'Confirmed {action.name.replace("_", " ")}. Saved ID: {result["id"]}.'
        append_message(state, user_id, 'assistant', receipt, {'confirmed': result})
        turn.tool_audit.append({'name': action.name, 'result': result})
    else:
        saved = db.operation_result(user_id, action.operation_id) if action.attempted else None
        if saved:
            result = saved
            state['last_write'] = dict(saved, user_id=user_id)
            append_message(state, user_id, 'assistant', f'This change was already saved before cancellation (ID {saved["id"]}). Use Undo to reverse it.', {'confirmed': saved})
        else:
            result = {'declined': True, 'message': 'The user declined this action. Do not execute or propose it again unless asked.'}
    if item['tool_id']:
        turn.results.append(_result(item['tool_id'], result))
    turn.actions.pop(0)
    if turn.actions:
        return None
    state['pending_action'] = None
    if item['tool_id']:
        turn.messages.append({'role': 'user', 'content': turn.results})
        # The write is already committed even if the provider fails from here.
        return _loop(turn, state, client)
    return _finish('Your change is saved.' if confirm or not result.get('declined') else 'Cancelled. Nothing was changed.', turn, state)


def stage_local(action, state):
    if state.get('pending_action'):
        raise AssistantError('Finish the pending action first.')
    state['pending_action'] = PendingTurn(action.user_id, [], [{'tool_id': None, 'action': action}], [], '', 'text', 0)


def retry_reply(state, user_id, client):
    turn = state.get('training_resume')
    if not turn or turn.user_id != user_id or state.get('pending_action'):
        raise AssistantError('There is no interrupted reply to retry for this account.')
    return _loop(turn, state, client)
