"""Generation, day batching for long plans, and deterministic grocery aggregation."""
from collections import OrderedDict
from fractions import Fraction
import re

from plan_agent.allergens import normalize
from plan_agent.api import structured_call
from plan_agent.config import GENERATION_TOKENS
from plan_agent.prompts import GENERATION_SYSTEM
from plan_agent.schemas import Ingredient, MealPlan, WorkoutPlan


def _combined_amount(amounts):
    groups = OrderedDict()
    for amount in amounts:
        match = re.fullmatch(r'(\d+(?:\.\d+)?(?:/\d+)?)\s+(.+)', amount.strip())
        if not match:
            return ' + '.join(amounts)
        number, unit = match.groups()
        try:
            quantity = Fraction(number)
        except (ValueError, ZeroDivisionError):
            return ' + '.join(amounts)
        unit = normalize(unit)
        groups[unit] = groups.get(unit, Fraction(0)) + quantity
    return ' + '.join(f'{float(quantity):g} {unit}' for unit, quantity in groups.items())


def rebuild_groceries(plan):
    groceries = OrderedDict()
    for day in plan.days:
        for meal in day.meals:
            for item in meal.ingredients:
                key = normalize(item.item)
                groceries.setdefault(key, []).append(item.amount)
    plan.grocery_list = [Ingredient(item=name, amount=_combined_amount(amounts))
                         for name, amounts in groceries.items()]
    plan.daily_calorie_estimate = sum(m.calories for d in plan.days for m in d.meals) / len(plan.days)
    return plan


def generate_plan(request, client, current_plan=None, change_request=None, errors=None, progress=None):
    schema = MealPlan if request.plan_type == 'meal' else WorkoutPlan
    payload = {
        'requirements': request.model_dump(),
        'current_plan': current_plan.model_dump() if current_plan else None,
        'change_request': change_request,
        'validation_errors': errors or [],
    }
    # Detailed 7-day plans cannot reliably fit in one 6,000-token response.
    # Generate one day at a time for large requests and assemble a complete plan.
    batch = (request.plan_type == 'meal' and request.days * request.meals_per_day > 9) or (
        request.plan_type == 'workout' and request.days > 3)
    if not batch:
        result = structured_call(client, schema, GENERATION_SYSTEM, payload, GENERATION_TOKENS)
    else:
        parts = []
        for day in range(1, request.days + 1):
            if progress:
                progress(f'Building day {day} of {request.days}…')
            day_payload = dict(payload, output_scope=f'Only day {day} of the full plan. days must have exactly one entry with day_number={day}. All other schema fields are still required.',
                               earlier_days=[part.days[0].model_dump() for part in parts])
            part = structured_call(client, schema, GENERATION_SYSTEM, day_payload, GENERATION_TOKENS)
            if len(part.days) != 1 or part.days[0].day_number != day:
                from plan_agent.config import PlanAgentError
                raise PlanAgentError('The plan service returned the wrong day while building the plan. Please try again.')
            parts.append(part)
        result = parts[0].model_copy(deep=True)
        result.days = [part.days[0] for part in parts]
        result.notes = list(dict.fromkeys(note for part in parts for note in part.notes))[:30]
        if isinstance(result, WorkoutPlan):
            result.days_per_week = request.days
            result.progression_notes = list(dict.fromkeys(note for part in parts for note in part.progression_notes))[:12]
            result.cardio_notes = list(dict.fromkeys(note for part in parts for note in part.cardio_notes))[:12]
    if isinstance(result, MealPlan):
        # The export quantities come from the actual recipes, never a separate guess.
        result = rebuild_groceries(result)
    return result
