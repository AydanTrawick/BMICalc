"""Typed arguments are also the model's tool schemas. Identity is never an argument."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Positive = Annotated[float, Field(gt=0, le=10000, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, le=10000, allow_inf_nan=False)]


class Arguments(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Dated(Arguments):
    date: str = Field(default='today', description='Original date phrase from the user, e.g. yesterday or 2026-09-15. Python resolves it. Omitted means today.')


class Strength(Dated):
    exercise: Text
    sets: int = Field(ge=1, le=100)
    reps: int | Text
    weight: Nonnegative | None = None
    unit: Literal['lb', 'kg'] | None = None
    rpe: int | None = Field(default=None, ge=1, le=10)
    notes: Text | None = None

    @model_validator(mode='after')
    def check(self):
        if isinstance(self.reps, int) and not 1 <= self.reps <= 1000:
            raise ValueError('Reps must be between 1 and 1000, or a meaningful range/timed description.')
        if self.weight is not None and self.unit is None:
            raise ValueError('Ask whether the weight is in lb or kg; never guess a unit.')
        return self


class Cardio(Dated):
    activity: Literal['run', 'walk', 'bike', 'swim', 'row', 'elliptical', 'other']
    distance: Positive | None = None
    distance_unit: Literal['miles', 'km'] | None = None
    duration_minutes: Positive | None = None
    notes: Text | None = None

    @model_validator(mode='after')
    def check(self):
        if self.distance is None and self.duration_minutes is None:
            raise ValueError('Ask for distance or duration before logging cardio.')
        if (self.distance is None) != (self.distance_unit is None):
            raise ValueError('A distance and its unit must be supplied together.')
        return self


class FoodItem(Arguments):
    food: Text
    amount: Text


class Meal(Dated):
    meal_name: Literal['breakfast', 'lunch', 'dinner', 'snack']
    items: list[FoodItem] = Field(min_length=1, max_length=30)
    calories: int | None = Field(default=None, ge=0, le=20000)
    protein_g: int | None = Field(default=None, ge=0, le=2000)
    notes: Text | None = None


class Bodyweight(Dated):
    weight: Positive
    unit: Literal['lb', 'kg']


class PlanType(Arguments):
    plan_type: Literal['workout', 'meal']


class UpdatePlan(PlanType):
    day_number: int = Field(ge=1, le=7)
    change_description: Text
    old_item: Text
    new_item: Text


class DeleteEntry(Arguments):
    entry_id: int = Field(gt=0)


class DateRange(Arguments):
    start_date: str
    end_date: str


class Logs(DateRange):
    log_type: Literal['strength', 'cardio', 'meal', 'bodyweight'] | None = None
    exercise_filter: Text | None = None


MODELS = {'log_strength': Strength, 'log_cardio': Cardio, 'log_meal': Meal,
          'log_bodyweight': Bodyweight, 'update_active_plan': UpdatePlan,
          'delete_log_entry': DeleteEntry, 'get_logs': Logs, 'get_active_plan': PlanType,
          'get_progress_summary': DateRange, 'get_todays_date': Arguments}
WRITE_TOOLS = {'log_strength', 'log_cardio', 'log_meal', 'log_bodyweight', 'update_active_plan', 'delete_log_entry'}
DESCRIPTIONS = {
    'log_strength': 'Stage a strength entry for confirmation, returning the saved ID only after approval. Use for completed lifting. Require exercise, sets, reps; ask for lb/kg if a weight is given without a unit. Never invent weight or RPE.',
    'log_cardio': 'Stage completed cardio for confirmation. Return saved activity ID after approval. A 3 mile run needs distance=3, distance_unit=miles and duration_minutes=null if no duration was supplied. Never guess pace.',
    'log_meal': 'Stage a meal with the foods and amounts the user provided. Leave calories and protein null unless provided. Returns saved ID after confirmation.',
    'log_bodyweight': 'Stage a bodyweight measurement using an explicit weight and lb/kg unit. Returns saved ID after confirmation.',
    'update_active_plan': 'Stage a preview of replacing one exact meal dish or exercise on a numbered day of the saved active plan. Read get_active_plan first. Calendar weekdays are NOT day numbers: ask which day if the plan has no explicit mapping. Returns saved plan ID only after confirmation.',
    'delete_log_entry': 'Stage soft deletion of a specific owned activity entry, including undo that/delete that for the last logged ID. Read the entry if its ID is unknown. Returns the affected ID after confirmation; never hard deletes.',
    'get_logs': 'Read active activities in an inclusive date range. Returns entries with IDs, dates, type, details, and a truncation flag. exercise_filter is a literal substring of an exercise name, not a muscle group: for legs read strength entries and identify leg exercises from results.',
    'get_active_plan': 'Read the saved active meal/workout plan with ID, title, structured data and constraints; returns null if none. This is a saved copy, not an unsaved Builder draft.',
    'get_progress_summary': 'Read progress for a date range: training sessions (distinct date/type), counts, distances by activity, known strength volume, current streak, historical weight PRs achieved in range, bodyweight change and coverage notes. Never treat missing values as measured zeros.',
    'get_todays_date': 'Read the current local date and day of week for date context. Relative dates are resolved in Python; copy the original user date phrase into date arguments.',
}
TOOL_SCHEMAS = [{'name': name, 'description': DESCRIPTIONS[name], 'input_schema': model.model_json_schema()}
                for name, model in MODELS.items()]
