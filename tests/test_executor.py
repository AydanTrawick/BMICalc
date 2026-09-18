from datetime import date
from unittest.mock import Mock, patch

import pytest

from assistant.config import AssistantError
from assistant.executor import arguments_for, execute_read, execute_write, prepare_write, prepare_undo
from assistant.progress import summary
from assistant.tools import MODELS, TOOL_SCHEMAS


def test_every_tool_has_a_schema_and_ownership_cannot_be_supplied():
    assert {item['name'] for item in TOOL_SCHEMAS} == set(MODELS)
    with pytest.raises(AssistantError):
        arguments_for('get_todays_date', {'user_id': 'someone-else'})


@pytest.mark.parametrize('tool,args,kind', [
    ('log_strength', {'exercise': 'bench press', 'sets': 4, 'reps': 8, 'weight': 185, 'unit': 'lb'}, 'strength'),
    ('log_cardio', {'activity': 'run', 'distance': 3, 'distance_unit': 'miles'}, 'cardio'),
    ('log_meal', {'meal_name': 'lunch', 'items': [{'food': 'chicken', 'amount': '6 oz'}]}, 'meal'),
    ('log_bodyweight', {'weight': 178.5, 'unit': 'lb'}, 'bodyweight'),
])
def test_log_routing_only_executes_after_confirmation(tool, args, kind):
    with patch('assistant.executor.db.log_activity', return_value={'id': 4}) as write:
        pending = prepare_write(tool, args, 'user-a')
        write.assert_not_called()
        with pytest.raises(AssistantError):
            execute_write(pending, 'user-a')
        with pytest.raises(AssistantError):
            execute_write(pending, 'user-b', confirmed=True)
        assert execute_write(pending, 'user-a', confirmed=True)['id'] == 4
    assert write.call_args.args[0:2] == ('user-a', kind)
    if kind == 'cardio':
        assert write.call_args.args[3]['duration_minutes'] is None
        assert write.call_args.args[3]['avg_pace'] is None


def test_strength_never_assumes_unit_and_missing_required_fields_fail():
    with pytest.raises(AssistantError, match='lb or kg'):
        arguments_for('log_strength', {'exercise': 'bench press', 'sets': 4, 'reps': 8, 'weight': 185})
    with pytest.raises(AssistantError):
        arguments_for('log_strength', {'sets': 4, 'reps': 8})


def test_read_routing_and_delete_preview():
    with patch('assistant.executor.db.get_logs', return_value={'entries': []}) as logs:
        execute_read('get_logs', {'start_date': 'today', 'end_date': 'today'}, 'user-a')
        assert logs.call_args.args == ('user-a',)
    with patch('assistant.executor.db.get_active_plan', return_value=None) as plan:
        assert execute_read('get_active_plan', {'plan_type': 'workout'}, 'user-a') is None
        plan.assert_called_once_with('user-a', plan_type='workout')
    with patch('assistant.executor.db.progress_rows', return_value=[]) as rows:
        result = execute_read('get_progress_summary', {'start_date': 'today', 'end_date': 'today'}, 'user-a')
        assert result['total_sessions'] == 0 and rows.call_args.args[0] == 'user-a'
    assert execute_read('get_todays_date', {}, None, anchor=date(2026, 9, 17))['day_of_week'] == 'Thursday'
    with patch('assistant.executor.db.get_entry', return_value={'id': 9}), patch('assistant.executor.db.delete_log_entry', return_value={'id': 9}) as delete:
        action = prepare_write('delete_log_entry', {'entry_id': 9}, 'user-a')
        delete.assert_not_called()
        execute_write(action, 'user-a', confirmed=True)
        assert delete.call_args.args[:2] == ('user-a', 9)


def test_plan_change_preview_and_route_preserves_other_days():
    from tests.plan_fixtures import workout_plan
    from plan_agent.schemas import PlanRequest
    plan = workout_plan()
    request = PlanRequest(plan_type='workout', days=4, volume='low', equipment=['gym'], injuries_mentioned=True)
    before = {'id': 5, 'updated_at': '2026-09-17', 'plan_data': {'plan': plan.model_dump(), 'request': request.model_dump()}}
    exercise = plan.days[0].exercises[0].model_copy(update={'name': 'Leg press', 'form_cues': ['Keep your back against the pad.']})
    with patch('assistant.executor.db.get_active_plan', return_value=before), \
         patch('assistant.executor.structured_call', return_value=exercise), \
         patch('assistant.executor.db.update_plan', return_value={'id': 5}) as update:
        action = prepare_write('update_active_plan', {'plan_type': 'workout', 'day_number': 1, 'old_item': 'Squat',
                                                     'new_item': 'Leg press', 'change_description': 'swap squat for leg press'}, 'user-a', client=Mock())
        assert action.preview['new_item']['name'] == 'Leg press'
        assert action.prepared['after']['plan']['days'][1:] == before['plan_data']['plan']['days'][1:]
        update.assert_not_called()
        execute_write(action, 'user-a', confirmed=True)
        assert update.call_args.args[0] == 'user-a'


def test_progress_math_units_missing_reps_streak_and_prs():
    def row(identifier, day, kind, **details):
        return {'id': identifier, 'log_date': day, 'log_type': kind, 'details': details}
    rows = [row(1, '2026-08-01', 'strength', exercise='Squat', sets=3, reps=8, weight=90, unit='kg'),
            row(2, '2026-09-15', 'strength', exercise='Squat', sets=4, reps=8, weight=100, unit='kg'),
            row(3, '2026-09-16', 'cardio', activity='run', distance=3, distance_unit='miles'),
            row(4, '2026-09-17', 'strength', exercise='Bench press', sets=4, reps=8, weight=185, unit='lb'),
            row(5, '2026-09-17', 'strength', exercise='Plank', sets=2, reps='30 sec', weight=None, unit=None),
            row(6, '2026-09-01', 'bodyweight', weight=80, unit='kg'),
            row(7, '2026-09-17', 'bodyweight', weight=79, unit='kg')]
    result = summary(rows, '2026-09-01', '2026-09-17', date(2026, 9, 17))
    assert result['total_sessions'] == 3 and result['current_streak_days'] == 3
    assert result['total_strength_volume_kg'] == round(4 * 8 * (100 + 185 * .45359237), 2)
    assert result['total_cardio_distance_km'] == 4.828
    assert result['bodyweight_change_kg'] == -1 and len(result['prs']) == 1
    assert result['strength_entries_with_unknown_volume'] == 1
