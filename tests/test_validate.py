import pytest
from pydantic import ValidationError

from plan_agent.allergens import exclusion_matches
from plan_agent.schemas import PlanRequest, MealPlan
from plan_agent.validate import validate_plan
from tests.plan_fixtures import meal_plan, workout_plan


def meal_request(**changes):
    return PlanRequest(plan_type='meal', days=3, meals_per_day=3, **changes)


def codes(plan, request):
    return {issue.code for issue in validate_plan(plan, request)}


def test_complete_meal_plan_passes():
    assert validate_plan(meal_plan(), meal_request(exclusions=['nuts'], must_include=['chicken'])) == []


@pytest.mark.parametrize('where', ['ingredient', 'dish', 'instructions', 'groceries'])
def test_almond_flour_blocks_display_in_every_food_location(where):
    plan = meal_plan()
    if where == 'ingredient':
        plan.days[0].meals[0].ingredients[0].item = 'ALMOND flour'
    elif where == 'dish':
        plan.days[0].meals[0].dish = 'Almond-flour pancakes'
    elif where == 'instructions':
        plan.days[0].meals[0].instructions = ['Coat in almond flour.']
    else:
        plan.grocery_list[0].item = 'almond flour'
    issues = validate_plan(plan, meal_request(exclusions=['nuts']))
    assert any(issue.code == 'exclusion' and issue.blocking for issue in issues)


def test_nut_boundaries_and_explicit_other_exclusions():
    assert not exclusion_matches('coconut and nutmeg', 'nuts')
    assert exclusion_matches('coconut flakes', 'coconut')
    assert exclusion_matches('Roasted CASHEWS', 'nuts')
    assert exclusion_matches('peanut butter', 'tree nuts')
    assert not exclusion_matches('eggplant', 'eggs')


def test_missing_chicken_cannot_be_satisfied_by_dish_title():
    plan = meal_plan()
    for day in plan.days:
        for meal in day.meals:
            meal.ingredients[0].item = 'tofu'
    assert 'inclusion' in codes(plan, meal_request(must_include=['chicken']))


def test_wrong_days_and_meals():
    plan = meal_plan(2, 2)
    assert {'days', 'meals'} <= codes(plan, meal_request())


def test_calorie_target_and_floor_are_checked_per_day():
    plan = meal_plan()
    assert 'calorie_target' in codes(plan, meal_request(calorie_target=2000))
    plan.days[0].meals[0].calories = 100
    assert any(issue.code == 'calorie_floor' and issue.blocking for issue in validate_plan(plan, meal_request()))


def test_grocery_coverage_and_duplicates():
    plan = meal_plan()
    plan.grocery_list[1] = plan.grocery_list[0].model_copy()
    assert {'grocery_missing', 'grocery_duplicates'} <= codes(plan, meal_request())


def test_required_details_and_finite_macros_enforced_by_schema():
    data = meal_plan().model_dump()
    data['days'][0]['meals'][0]['protein_g'] = float('nan')
    with pytest.raises(ValidationError):
        MealPlan.model_validate(data)
    data['days'][0]['meals'][0]['protein_g'] = 10
    data['days'][0]['meals'][0]['instructions'] = []
    with pytest.raises(ValidationError):
        MealPlan.model_validate(data)


def test_low_volume_rejects_high_volume_and_too_many_sets():
    plan = workout_plan()
    request = PlanRequest(plan_type='workout', days=4, volume='low')
    assert not validate_plan(plan, request)
    plan.days[0].exercises *= 2
    plan.days[0].exercises[0].sets = 4
    assert {'volume', 'sets'} <= codes(plan, request)


def test_injury_and_session_duration_are_flagged():
    request = PlanRequest(plan_type='workout', days=4, injuries_or_limits=['knee pain'],
                          session_length_minutes=20)
    assert {'injury_conflict', 'duration', 'professional_review'} <= codes(workout_plan(), request)
