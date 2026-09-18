from unittest.mock import Mock, patch

import pytest

from plan_agent.agent import build_checked_plan, finalize_request, process_message, start_over
from plan_agent.config import PlanAgentError
from plan_agent.extract import merge_requirements
from plan_agent.schemas import PlanRequest
from tests.plan_fixtures import meal_plan, workout_plan


def test_two_clarifications_then_defaults_with_notes():
    state = {}
    request = PlanRequest(plan_type='meal', missing_fields=['days', 'meals_per_day'])
    with patch('plan_agent.agent.extract_request', return_value=request), \
         patch('plan_agent.agent.generate_plan', return_value=meal_plan()) as generate:
        process_message('Make me a meal plan', state, Mock())
        assert state['clarification_rounds'] == 1 and state['request_count'] == 0
        process_message('Whatever works', state, Mock())
        assert state['clarification_rounds'] == 2
        process_message('You choose', state, Mock())
        assert generate.call_count == 1 and state['request_count'] == 1
        assert state['current_plan'] is not None
        assert any('days was not provided: 3' in note for note in state['current_plan'].notes)


def test_workout_asks_one_combined_question_including_injuries():
    request = merge_requirements(None, PlanRequest(plan_type='workout', days=4, goal='weight loss', volume='low'))
    state = {}
    with patch('plan_agent.agent.extract_request', return_value=request):
        process_message('Low volume four day weight loss plan', state, Mock())
    reply = state['messages'][-1]['content']
    assert all(word in reply for word in ('experience', 'equipment', 'injuries'))
    assert state['current_plan'] is None


def test_calorie_minimum_is_explicit_and_not_diagnosed_as_personal_target():
    request = finalize_request(PlanRequest(plan_type='meal', days=3, meals_per_day=3, calorie_target=800))
    assert request.calorie_target == 1200
    assert any('800-calorie target was raised' in note for note in request.assumptions)


def test_repair_receives_specific_errors_then_passes():
    bad = meal_plan()
    bad.days[0].meals[0].ingredients[0].item = 'almond flour'
    request = PlanRequest(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'])
    with patch('plan_agent.agent.generate_plan', side_effect=[bad, meal_plan()]) as generate:
        plan, issues = build_checked_plan(request, Mock())
    assert plan is not None and not issues
    assert generate.call_count == 2
    assert any('excluded nuts' in message for message in generate.call_args.kwargs['errors'])


def test_exclusion_failure_is_hidden_after_exactly_two_repairs():
    bad = meal_plan()
    bad.days[0].meals[0].instructions = ['Add almond flour.']
    request = PlanRequest(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'])
    with patch('plan_agent.agent.generate_plan', return_value=bad) as generate:
        plan, issues = build_checked_plan(request, Mock())
    assert plan is None and any(issue.blocking for issue in issues)
    assert generate.call_count == 3


def test_nonblocking_failed_checks_return_plan_with_warnings():
    request = PlanRequest(plan_type='workout', days=4, volume='low', session_length_minutes=10)
    with patch('plan_agent.agent.generate_plan', return_value=workout_plan()) as generate:
        plan, issues = build_checked_plan(request, Mock())
    assert plan is not None and 'duration' in {issue.code for issue in issues}
    assert generate.call_count == 3


def test_repair_api_failure_never_releases_excluded_food():
    bad = meal_plan()
    bad.days[0].meals[0].dish = 'Peanut chicken'
    with patch('plan_agent.agent.generate_plan', side_effect=[bad, PlanAgentError('offline')]):
        plan, issues = build_checked_plan(PlanRequest(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts']), Mock())
    assert plan is None and any(issue.code == 'repair_unavailable' for issue in issues)


def test_edit_keeps_current_plan_and_earlier_requirements_in_prompt():
    old = meal_plan()
    request = PlanRequest(plan_type='meal', days=3, meals_per_day=3, exclusions=['nuts'], must_include=['chicken'])
    state = {'current_plan': old, 'plan_request': request}
    with patch('plan_agent.agent.extract_request', return_value=request), \
         patch('plan_agent.agent.generate_plan', return_value=meal_plan()) as generate:
        process_message('swap day 2 lunch for something with rice', state, Mock())
    args = generate.call_args.args
    assert args[0].exclusions == ['nuts'] and args[2] is old
    assert 'swap day 2 lunch' in args[3]


def test_limit_is_not_reset_by_start_over_and_logs_stay_intact():
    state = {'request_count': 10, 'food_log': [{'food': 'private'}], 'firstrep_user': {'id': 'abc'},
             'current_plan': meal_plan(), 'plan_builder_audio_cache': {'abc': 'transcript'}}
    start_over(state)
    assert state['current_plan'] is None and state['messages'] == []
    assert state['food_log'] == [{'food': 'private'}] and state['firstrep_user']['id'] == 'abc'
    assert 'plan_builder_audio_cache' not in state
    with patch('plan_agent.agent.extract_request') as extract:
        with pytest.raises(PlanAgentError, match='10 plan builds'):
            process_message('Build a plan', state, Mock())
        extract.assert_not_called()


def test_new_workout_after_meal_defaults_still_asks_about_injuries():
    state = {'clarification_rounds': 2}
    meal_request = PlanRequest(plan_type='meal', days=3, meals_per_day=3)
    workout_request = merge_requirements(None, PlanRequest(plan_type='workout', days=4, goal='fitness',
                                                          experience_level='beginner', equipment=['bodyweight']))
    with patch('plan_agent.agent.extract_request', side_effect=[meal_request, workout_request]), \
         patch('plan_agent.agent.generate_plan', return_value=meal_plan()):
        process_message('Use the meal defaults', state, Mock())
        process_message('Now a beginner four-day bodyweight workout', state, Mock())
    assert 'injuries' in state['messages'][-1]['content']
    assert state['clarification_rounds'] == 1 and state['request_count'] == 1
