"""Typed provider outputs; missing request values are never silently defaulted."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class PlanRequest(Model):
    plan_type: Literal['meal', 'workout', 'unknown'] = 'unknown'
    goal: Text | None = None
    days: int | None = Field(default=None, ge=1, le=7)
    meals_per_day: int | None = Field(default=None, ge=1, le=6)
    calorie_target: int | None = Field(default=None, gt=0, le=20000)
    exclusions: list[Text] = Field(default_factory=list, max_length=40)
    must_include: list[Text] = Field(default_factory=list, max_length=40)
    diet_style: Text | None = None
    volume: Literal['low', 'moderate', 'high'] | None = None
    experience_level: Text | None = None
    equipment: list[Text] = Field(default_factory=list, max_length=40)
    session_length_minutes: int | None = Field(default=None, ge=5, le=240)
    injuries_or_limits: list[Text] = Field(default_factory=list, max_length=40)
    missing_fields: list[str] = Field(default_factory=list)
    # Distinguishes "no injuries" from a question the user has not answered.
    injuries_mentioned: bool = False
    # Fields explicitly provided/changed in the latest message, for safe merging.
    provided_fields: list[str] = Field(default_factory=list)
    assumptions: list[Text] = Field(default_factory=list)


class Ingredient(Model):
    item: Text
    amount: Text


class Meal(Model):
    name: Text
    dish: Text
    ingredients: list[Ingredient] = Field(min_length=1, max_length=30)
    instructions: list[Text] = Field(min_length=1, max_length=15)
    calories: Nonnegative
    protein_g: Nonnegative
    carbs_g: Nonnegative
    fat_g: Nonnegative
    prep_minutes: int = Field(ge=0, le=1440)


class MealDay(Model):
    day_number: int = Field(ge=1, le=7)
    meals: list[Meal] = Field(min_length=1, max_length=6)


class MealPlan(Model):
    title: Text
    summary: Text
    daily_calorie_estimate: Nonnegative
    days: list[MealDay] = Field(min_length=1, max_length=7)
    grocery_list: list[Ingredient] = Field(min_length=1, max_length=250)
    notes: list[Text] = Field(default_factory=list, max_length=40)


class Exercise(Model):
    name: Text
    sets: int = Field(ge=1, le=20)
    reps: Text
    rest_seconds: int = Field(ge=0, le=600)
    rpe_or_rir: Text
    form_cues: list[Text] = Field(min_length=1, max_length=8)
    easier_option: Text
    harder_option: Text


class WorkoutDay(Model):
    day_number: int = Field(ge=1, le=7)
    focus: Text
    warmup: list[Text] = Field(min_length=1, max_length=10)
    exercises: list[Exercise] = Field(min_length=1, max_length=12)
    cooldown: list[Text] = Field(min_length=1, max_length=10)
    est_minutes: int = Field(ge=1, le=240)


class WorkoutPlan(Model):
    title: Text
    summary: Text
    goal: Text
    days_per_week: int = Field(ge=1, le=7)
    days: list[WorkoutDay] = Field(min_length=1, max_length=7)
    progression_notes: list[Text] = Field(min_length=1, max_length=12)
    cardio_notes: list[Text] = Field(default_factory=list, max_length=12)
    notes: list[Text] = Field(default_factory=list, max_length=40)


Plan = MealPlan | WorkoutPlan
