"""Portable text exports with the same blocking checks as the page."""
import re

from plan_agent.config import DISCLAIMER, PlanAgentError
from plan_agent.schemas import MealPlan
from plan_agent.validate import validate_plan


def export_plan(plan, request, issues=(), plain_text=False):
    checked = validate_plan(plan, request)
    if any(issue.blocking for issue in checked):
        raise PlanAgentError('This plan cannot be downloaded because an exclusion or safety check failed.')
    lines = [f'# {plan.title}', '', plan.summary, '']
    warnings = list(dict.fromkeys(issue.message for issue in [*checked, *issues]))
    if warnings:
        lines += ['## Unresolved checks', *[f'- {message}' for message in warnings], '']
    if isinstance(plan, MealPlan):
        lines += [f'Estimated daily calories: {plan.daily_calorie_estimate:g}', '']
        for day in plan.days:
            lines += [f'## Day {day.day_number}', '']
            for meal in day.meals:
                lines += [f'### {meal.name}: {meal.dish}', f'Prep: {meal.prep_minutes} minutes',
                          f'{meal.calories:g} kcal | Protein {meal.protein_g:g} g | Carbs {meal.carbs_g:g} g | Fat {meal.fat_g:g} g', '',
                          'Ingredients:', *[f'- {item.item}: {item.amount}' for item in meal.ingredients], '',
                          'Instructions:', *[f'{i}. {step}' for i, step in enumerate(meal.instructions, 1)], '']
        lines += ['## Grocery list', *[f'- {item.item}: {item.amount}' for item in plan.grocery_list], '']
    else:
        lines += [f'Goal: {plan.goal} | {plan.days_per_week} days per week', '']
        for day in plan.days:
            lines += [f'## Day {day.day_number}: {day.focus}', f'Estimated time: {day.est_minutes} minutes', '',
                      'Warmup:', *[f'- {step}' for step in day.warmup], '']
            for exercise in day.exercises:
                lines += [f'### {exercise.name}', f'{exercise.sets} sets × {exercise.reps} | Rest {exercise.rest_seconds} seconds | {exercise.rpe_or_rir}',
                          *[f'- {cue}' for cue in exercise.form_cues], f'Easier: {exercise.easier_option}', f'Harder: {exercise.harder_option}', '']
            lines += ['Cooldown:', *[f'- {step}' for step in day.cooldown], '']
        lines += ['## Progression', *[f'- {note}' for note in plan.progression_notes], '',
                  '## Cardio', *[f'- {note}' for note in plan.cardio_notes], '']
    lines += ['## Notes', *[f'- {note}' for note in plan.notes], '',
              '## Disclaimers', *[f'- {note}' for note in DISCLAIMER], '']
    text = '\n'.join(lines)
    return re.sub(r'^#{1,6} ', '', text, flags=re.MULTILINE) if plain_text else text
