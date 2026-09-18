import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from plan_agent.config import PLAN_MODEL, PlanAgentError
from plan_agent.extract import extract_request
from plan_agent.generate import generate_plan
from plan_agent.schemas import PlanRequest
from tests.plan_fixtures import meal_plan


def response(data, stop_reason='end_turn'):
    return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps(data))], stop_reason=stop_reason)


def client_for(data):
    client = Mock()
    client.messages.create.return_value = response(data)
    return client


def test_extract_meal_example_with_mock_api():
    client = client_for(dict(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'],
                             must_include=['chicken'], provided_fields=['plan_type', 'days', 'meals_per_day', 'exclusions', 'must_include']))
    request = extract_request("Build me a 3 day meal plan with 3 meals a day, don't include any nuts, but make sure to add chicken", [], client)
    assert request.days == 3 and request.meals_per_day == 3
    assert request.exclusions == ['nuts'] and request.must_include == ['chicken']
    assert request.calorie_target is None and request.goal is None and not request.missing_fields
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs['model'] == PLAN_MODEL == 'claude-sonnet-5'
    assert 'JSON schema:' in kwargs['system']


def test_extract_workout_example_marks_missing_and_injuries():
    client = client_for(dict(plan_type='workout', days=4, volume='low', goal='weight loss'))
    request = extract_request('Build me a low volume 4 day a week exercise plan that targets losing weight', [], client)
    assert request.volume == 'low' and request.days == 4
    assert set(request.missing_fields) == {'experience_level', 'equipment', 'injuries_or_limits'}


def test_vegetarian_example_does_not_invent_calories():
    client = client_for(dict(plan_type='meal', days=5, meals_per_day=4, diet_style='vegetarian', exclusions=['dairy']))
    request = extract_request('Vegetarian 5 day plan, 4 meals, no dairy', [], client)
    assert request.diet_style == 'vegetarian' and request.exclusions == ['dairy']
    assert request.calorie_target is None and not request.missing_fields


def test_followup_preserves_exclusions_days_and_required_foods():
    previous = PlanRequest(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'], must_include=['chicken'])
    client = client_for(dict(days=5, provided_fields=['days']))
    result = extract_request('make it 5 days', [{'role': 'user', 'content': 'no nuts, include chicken'}], client, previous)
    assert (result.days, result.meals_per_day, result.plan_type) == (5, 3, 'meal')
    assert result.exclusions == ['nuts'] and result.must_include == ['chicken']


def test_no_injuries_is_distinct_from_unknown_and_no_equipment_is_bodyweight():
    previous = PlanRequest(plan_type='workout', days=4, goal='weight loss')
    client = client_for(dict(experience_level='beginner', equipment=['bodyweight'], injuries_mentioned=True,
                             provided_fields=['experience_level', 'equipment', 'injuries_mentioned']))
    request = extract_request('beginner, no equipment, no injuries', [], client, previous)
    assert request.injuries_mentioned and not request.missing_fields


def test_invalid_json_is_retried_once_and_explained():
    client = Mock()
    client.messages.create.side_effect = [response({'days': 99}), response({'plan_type': 'meal', 'days': 3, 'meals_per_day': 3})]
    assert extract_request('3 day meal plan', [], client).days == 3
    assert client.messages.create.call_count == 2
    assert 'Schema/parse errors' in client.messages.create.call_args.kwargs['messages'][-1]['content']
    client.messages.create.side_effect = [response({'days': 99}), response({'days': 99})]
    with pytest.raises(PlanAgentError, match='invalid data twice'):
        extract_request('3 day meal plan', [], client)


def test_generation_rebuilds_combined_groceries_from_actual_recipes():
    plan = meal_plan()
    client = client_for(plan.model_dump())
    result = generate_plan(PlanRequest(plan_type='meal', days=3, meals_per_day=3), client)
    assert result.grocery_list[0].amount == '1350 g'
    assert result.daily_calorie_estimate == 1500
    assert client.messages.create.call_args.kwargs['max_tokens'] == 6000


def test_large_plan_is_generated_in_bounded_daily_chunks():
    client = Mock()
    outputs = []
    for day in range(1, 6):
        plan = meal_plan(1, 4)
        plan.days[0].day_number = day
        outputs.append(response(plan.model_dump()))
    client.messages.create.side_effect = outputs
    plan = generate_plan(PlanRequest(plan_type='meal', days=5, meals_per_day=4), client)
    assert len(plan.days) == 5 and client.messages.create.call_count == 5
    assert plan.grocery_list[0].amount == '3000 g'
