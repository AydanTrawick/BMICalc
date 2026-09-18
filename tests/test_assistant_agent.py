from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from assistant.agent import begin, initialize, resolve_pending, clear_conversation, retry_reply
from assistant.config import AssistantError
from plan_agent.config import PlanAgentError


def response(*blocks):
    return SimpleNamespace(content=[SimpleNamespace(**block) for block in blocks],
                           stop_reason='tool_use' if any(block['type'] == 'tool_use' for block in blocks) else 'end_turn')


def text(value):
    return {'type': 'text', 'text': value}


def call(name='log_cardio', identifier='call-1', **args):
    return {'type': 'tool_use', 'id': identifier, 'name': name, 'input': args or {'activity': 'run', 'distance': 3, 'distance_unit': 'miles'}}


@pytest.fixture
def database():
    with patch('assistant.agent.db.load_messages', return_value=[]), \
         patch('assistant.agent.db.save_message', return_value=4), \
         patch('assistant.agent.db.get_active_plan', return_value=None), \
         patch('assistant.agent.db.clear_conversation', return_value=5):
        yield


def test_write_is_staged_then_confirmed_then_tool_result_is_sent(database):
    state, client = {}, Mock()
    client.messages.create.side_effect = [response(call()), response(text('Logged your three-mile run.'))]
    with patch('assistant.executor.db.log_activity', return_value={'id': 17, 'kind': 'log', 'undo': {'kind': 'delete_log', 'id': 17}}) as write:
        assert begin('Log a 3 mile run for today', state, 'u1', client, source='voice') is None
        write.assert_not_called()
        assert state['pending_action'].actions[0]['action'].preview['duration_minutes'] is None
        assert resolve_pending(state, 'u1', client, True) == 'Logged your three-mile run.'
    assert write.call_count == 1 and write.call_args.args[4] == 'voice'
    assert state['last_write']['id'] == 17 and state['pending_action'] is None
    assert client.messages.create.call_args.kwargs['messages'][-1]['content'][0]['type'] == 'tool_result'


def test_cancel_executes_nothing_and_notifies_model(database):
    state, client = {}, Mock()
    client.messages.create.side_effect = [response(call()), response(text('Cancelled.'))]
    with patch('assistant.agent.execute_write') as execute:
        begin('Log a 3 mile run', state, 'u1', client)
        resolve_pending(state, 'u1', client, False)
        execute.assert_not_called()
    assert 'declined' in client.messages.create.call_args.kwargs['messages'][-1]['content'][0]['content']


def test_reads_continue_without_confirmation_and_errors_are_tool_results(database):
    state, client = {}, Mock()
    client.messages.create.side_effect = [response(call('get_todays_date', date='bad')), response(call('get_todays_date', **{})), response(text('Today is Thursday.'))]
    # The helper's default args are intentionally invalid for this tool on both calls.
    begin('What day is it?', state, 'u1', client)
    assert client.messages.create.call_count == 3 and state['pending_action'] is None
    assert client.messages.create.call_args.kwargs['messages'][-1]['content'][0]['is_error']


def test_read_executes_immediately_and_general_reply_uses_no_tools(database):
    state, client = {}, Mock()
    client.messages.create.side_effect = [response({'type': 'tool_use', 'id': 'date', 'name': 'get_todays_date', 'input': {}}), response(text('Today is Thursday.'))]
    assert begin('What day is today?', state, 'u1', client) == 'Today is Thursday.'
    assert state['pending_action'] is None
    client.messages.create.side_effect = [response(text('Soreness can occur after unfamiliar exercise; persistent or severe pain needs medical assessment.'))]
    with patch('assistant.agent.execute_read') as read:
        begin('Is soreness common?', state, 'u1', client)
        read.assert_not_called()


def test_partial_batch_failure_can_retry_without_repeating_first_write(database):
    state, client = {}, Mock()
    client.messages.create.side_effect = [response(call(identifier='a'), call(identifier='b')), response(text('Both saved.'))]
    begin('Log two runs', state, 'u1', client)
    with patch('assistant.agent.execute_write', side_effect=[{'id': 1, 'kind': 'log'}, AssistantError('offline'), {'id': 2, 'kind': 'log'}]) as write:
        resolve_pending(state, 'u1', client, True)
        with pytest.raises(AssistantError):
            resolve_pending(state, 'u1', client, True)
        assert len(state['pending_action'].actions) == 1 and state['last_write']['id'] == 1
        resolve_pending(state, 'u1', client, True)
    assert write.call_args_list[0].args[0].operation_id != write.call_args_list[1].args[0].operation_id
    assert write.call_args_list[1].args[0].operation_id == write.call_args_list[2].args[0].operation_id


def test_reply_failure_after_commit_is_resumable_without_duplicate_write(database):
    state, client = {}, Mock()
    client.messages.create.side_effect = [response(call()), PlanAgentError('offline'), response(text('Saved.'))]
    with patch('assistant.agent.execute_write', return_value={'id': 9, 'kind': 'log'}) as write:
        begin('Log a run', state, 'u1', client)
        with pytest.raises(PlanAgentError):
            resolve_pending(state, 'u1', client, True)
        assert state['pending_action'] is None and state['last_write']['id'] == 9
        assert retry_reply(state, 'u1', client) == 'Saved.'
        assert write.call_count == 1


def test_owner_limit_context_and_clear_do_not_bypass_cap(database):
    state, client = {}, Mock()
    initialize(state, 'u1')
    state['training_messages'] = [{'role': 'user', 'content': str(index)} for index in range(25)]
    client.messages.create.return_value = response(text('Hello.'))
    begin('Hi', state, 'u1', client)
    assert len(client.messages.create.call_args.kwargs['messages']) == 21
    state['training_count'] = 30
    clear_conversation(state, 'u1')
    with pytest.raises(AssistantError, match='30 assistant'):
        begin('Hi again', state, 'u1', client)
    initialize(state, 'u2')
    assert not state['training_messages'] and state['last_write'] is None


def test_tool_loop_stops_at_five_and_undo_requires_confirmation(database):
    state, client = {}, Mock()
    client.messages.create.return_value = response({'type': 'tool_use', 'id': 'date', 'name': 'get_todays_date', 'input': {}})
    assert 'five-step limit' in begin('Keep checking', state, 'u1', client)
    assert client.messages.create.call_count == 5
    state['last_write'] = {'user_id': 'u1', 'id': 10, 'kind': 'log', 'undo': {'kind': 'delete_log', 'id': 10}}
    with patch('assistant.agent.execute_write') as write:
        begin('Actually undo that last one', state, 'u1', client)
        assert state['pending_action'].actions[0]['action'].name == 'undo'
        write.assert_not_called()


def test_cancel_after_unknown_commit_checks_receipt_instead_of_claiming_no_save(database):
    state, client = {}, Mock()
    client.messages.create.side_effect = [response(call()), response(text('The earlier save succeeded; you can undo it.'))]
    begin('Log my run', state, 'u1', client)
    state['pending_action'].actions[0]['action'].attempted = True
    with patch('assistant.agent.db.operation_result', return_value={'id': 9, 'kind': 'log', 'undo': {'kind': 'delete_log', 'id': 9}}), \
         patch('assistant.agent.execute_write') as write:
        resolve_pending(state, 'u1', client, False)
        write.assert_not_called()
    assert state['last_write']['id'] == 9
    assert any('already saved before cancellation' in item['content'] for item in state['training_messages'])
