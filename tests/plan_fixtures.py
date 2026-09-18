"""Small complete plans used by offline tests; never real API responses."""
from plan_agent.schemas import MealPlan, WorkoutPlan


def meal_plan(days=3, meals=3):
    return MealPlan.model_validate({
        'title': 'Chicken and rice', 'summary': 'Practical meals.',
        'daily_calorie_estimate': meals * 500,
        'days': [{'day_number': day, 'meals': [
            {'name': f'Meal {meal}', 'dish': 'Chicken rice bowl',
             'ingredients': [{'item': 'chicken', 'amount': '150 g'}, {'item': 'rice', 'amount': '100 g'}],
             'instructions': ['Cook chicken thoroughly and serve with cooked rice.'],
             'calories': 500, 'protein_g': 35, 'carbs_g': 60, 'fat_g': 13, 'prep_minutes': 20}
            for meal in range(1, meals + 1)]} for day in range(1, days + 1)],
        'grocery_list': [{'item': 'chicken', 'amount': f'{150 * days * meals} g'},
                         {'item': 'rice', 'amount': f'{100 * days * meals} g'}], 'notes': [],
    })


def workout_plan(days=4):
    return WorkoutPlan.model_validate({
        'title': 'Low volume routine', 'summary': 'A simple weekly routine.',
        'goal': 'weight loss', 'days_per_week': days,
        'days': [{'day_number': day, 'focus': 'Full body', 'warmup': ['Walk for five minutes.'],
                  'exercises': [dict(name=name, sets=2, reps='8-10', rest_seconds=60,
                                     rpe_or_rir='RPE 6', form_cues=['Move slowly and keep control.'],
                                     easier_option='Reduce the range of motion.', harder_option='Add one rep.')
                                for name in ['Squat', 'Wall push-up', 'Standing calf raise']],
                  'cooldown': ['Gentle walking.'], 'est_minutes': 30}
                 for day in range(1, days + 1)],
        'progression_notes': ['Add one rep when the sets feel easy.'],
        'cardio_notes': ['Walk on rest days if comfortable.'], 'notes': [],
    })
