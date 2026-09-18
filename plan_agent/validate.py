"""Deterministic rules, independent of provider output or the UI."""
from dataclasses import dataclass

from plan_agent.allergens import contains_keyword, exclusion_matches, normalize
from plan_agent.config import MIN_DAILY_CALORIES
from plan_agent.schemas import MealPlan, Plan, PlanRequest, WorkoutPlan


@dataclass(frozen=True)
class RuleIssue:
    code: str
    message: str
    blocking: bool = False
    repairable: bool = True


INJURY_PATTERNS = {
    'knee': ['squat', 'lunge', 'jump', 'running', 'run', 'burpee', 'leg extension'],
    'back': ['deadlift', 'bent over row', 'good morning', 'sit up', 'barbell squat'],
    'shoulder': ['overhead press', 'shoulder press', 'bench press', 'dip', 'push up', 'pull up'],
    'wrist': ['push up', 'plank', 'burpee', 'handstand'],
    'ankle': ['jump', 'running', 'run', 'burpee', 'lunge'],
    'hip': ['squat', 'lunge', 'deadlift', 'running'],
    'neck': ['shrug', 'overhead press', 'headstand'],
}


def _meal_text(meal):
    return ' '.join([meal.name, meal.dish, *meal.instructions,
                     *(f'{i.item} {i.amount}' for i in meal.ingredients)])


def validate_meal_plan(plan: MealPlan, request: PlanRequest):
    issues = []
    if len(plan.days) != request.days:
        issues.append(RuleIssue('days', f'Expected {request.days} days; received {len(plan.days)}.'))
    if [day.day_number for day in plan.days] != list(range(1, len(plan.days) + 1)):
        issues.append(RuleIssue('day_numbers', 'Day numbers must be consecutive, starting at 1.'))
    locations = []
    ingredient_text = []
    totals = []
    for day in plan.days:
        if len(day.meals) != request.meals_per_day:
            issues.append(RuleIssue('meals', f'Day {day.day_number}: expected {request.meals_per_day} meals; received {len(day.meals)}.'))
        total = sum(meal.calories for meal in day.meals)
        totals.append(total)
        if total < MIN_DAILY_CALORIES:
            issues.append(RuleIssue('calorie_floor', f'Day {day.day_number} totals {total:g} calories; minimum is 1,200.', True))
        if request.calorie_target and not .85 * request.calorie_target <= total <= 1.15 * request.calorie_target:
            issues.append(RuleIssue('calorie_target', f'Day {day.day_number}: {total:g} calories is outside ±15% of {request.calorie_target}.'))
        for meal in day.meals:
            location = f'Day {day.day_number}, {meal.name}'
            locations.append((location, _meal_text(meal)))
            ingredient_text.extend(i.item for i in meal.ingredients)
            if not meal.ingredients or not meal.instructions or meal.calories <= 0:
                issues.append(RuleIssue('meal_detail', f'{location}: ingredients, instructions, and positive calories are required.'))
    for item in plan.grocery_list:
        locations.append((f'Grocery list: {item.item}', f'{item.item} {item.amount}'))
    for exclusion in request.exclusions:
        for location, text in locations:
            matched = exclusion_matches(text, exclusion)
            if matched:
                issues.append(RuleIssue('exclusion', f'{location}: excluded {exclusion} detected ({", ".join(matched)}).', True))
    for inclusion in request.must_include:
        if not contains_keyword(' '.join(ingredient_text), inclusion):
            issues.append(RuleIssue('inclusion', f'Include {inclusion} in actual meal ingredients at least once across the plan.'))
    grocery_names = [normalize(i.item) for i in plan.grocery_list]
    if len(grocery_names) != len(set(grocery_names)):
        issues.append(RuleIssue('grocery_duplicates', 'Combine duplicate grocery items and their amounts into one row.'))
    for item in sorted(set(normalize(i) for i in ingredient_text)):
        if item not in grocery_names:
            issues.append(RuleIssue('grocery_missing', f'Grocery list is missing {item}; use the same ingredient name in meals and groceries.'))
    if totals and abs(plan.daily_calorie_estimate - sum(totals) / len(totals)) > 1:
        issues.append(RuleIssue('calorie_summary', 'Daily calorie estimate must equal the mean of the actual daily meal totals.'))
    return issues


def validate_workout_plan(plan: WorkoutPlan, request: PlanRequest):
    issues = []
    if len(plan.days) != request.days or plan.days_per_week != request.days:
        issues.append(RuleIssue('days', f'Expected {request.days} training days in both days and days_per_week.'))
    if [day.day_number for day in plan.days] != list(range(1, len(plan.days) + 1)):
        issues.append(RuleIssue('day_numbers', 'Day numbers must be consecutive, starting at 1.'))
    ranges = {'low': (3, 4, 2, 3), 'moderate': (4, 6, 3, 4), 'high': (6, 12, 3, 4)}
    for day in plan.days:
        if request.volume:
            low, high, set_low, set_high = ranges[request.volume]
            if not low <= len(day.exercises) <= high:
                issues.append(RuleIssue('volume', f'Day {day.day_number}: {request.volume} volume needs {low}–{high} exercises.'))
            for exercise in day.exercises:
                if not set_low <= exercise.sets <= set_high:
                    issues.append(RuleIssue('sets', f'Day {day.day_number}, {exercise.name}: {request.volume} volume needs {set_low}–{set_high} sets.'))
        if request.session_length_minutes and day.est_minutes > request.session_length_minutes:
            issues.append(RuleIssue('duration', f'Day {day.day_number}: {day.est_minutes} minutes exceeds the {request.session_length_minutes}-minute limit.'))
        for exercise in day.exercises:
            if not exercise.reps or not exercise.form_cues or not exercise.rpe_or_rir:
                issues.append(RuleIssue('exercise_detail', f'{exercise.name}: reps, effort, and form cues are required.'))
        # Also check warmups, cooldowns, and substitutions for obvious conflicts.
        activities = [*day.warmup, *day.cooldown]
        activities.extend(f'{e.name} {e.easier_option} {e.harder_option}' for e in day.exercises)
        for limitation in request.injuries_or_limits:
            for region, movements in INJURY_PATTERNS.items():
                if contains_keyword(limitation, region):
                    for activity in activities:
                        if any(contains_keyword(activity, movement) for movement in movements):
                            issues.append(RuleIssue('injury_conflict', f'Day {day.day_number}: {activity} may conflict with {limitation}; replace it and flag for professional review.'))
    if request.injuries_or_limits:
        issues.append(RuleIssue('professional_review', 'Injury and medical restrictions need professional review; keyword checks cannot establish that exercises are safe for you.', repairable=False))
    return issues


def validate_plan(plan: Plan, request: PlanRequest):
    if isinstance(plan, MealPlan) and request.plan_type == 'meal':
        return validate_meal_plan(plan, request)
    if isinstance(plan, WorkoutPlan) and request.plan_type == 'workout':
        return validate_workout_plan(plan, request)
    return [RuleIssue('plan_type', 'The output does not match the requested plan type.', True)]
