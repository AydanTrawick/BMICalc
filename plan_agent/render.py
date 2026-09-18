"""Streamlit presentation of validated plans."""
import streamlit as st

from plan_agent.config import DISCLAIMER
from plan_agent.export import export_plan
from plan_agent.schemas import MealPlan
from plan_agent.validate import validate_plan


def render_plan(plan, request, issues=()):
    checked = validate_plan(plan, request)
    if any(issue.blocking for issue in checked):
        st.error('This plan failed an exclusion or safety check and cannot be displayed or downloaded.')
        return
    st.header(plan.title)
    st.write(plan.summary)
    warnings = list(dict.fromkeys(issue.message for issue in [*checked, *issues]))
    if warnings:
        st.warning('Review these unresolved checks before using the plan:\n\n' + '\n'.join(f'- {message}' for message in warnings))
    meal_plan = isinstance(plan, MealPlan)
    if meal_plan:
        st.caption(f'Estimated average: {plan.daily_calorie_estimate:,.0f} calories/day. Macros are estimates.')
    else:
        st.caption(f'{plan.goal} · {plan.days_per_week} days/week')
    tabs = st.tabs([f'Day {day.day_number}' for day in plan.days] + (['Grocery list'] if meal_plan else []))
    for day, tab in zip(plan.days, tabs):
        with tab:
            if meal_plan:
                st.caption(f'Daily total: {sum(meal.calories for meal in day.meals):,.0f} calories')
                for meal in day.meals:
                    with st.expander(f'{meal.name} · {meal.dish}', expanded=True):
                        st.caption(f'Prep: {meal.prep_minutes} minutes')
                        st.dataframe([item.model_dump() for item in meal.ingredients], hide_index=True, width='stretch')
                        for index, step in enumerate(meal.instructions, 1):
                            st.write(f'{index}. {step}')
                        for column, label, value, unit in zip(st.columns(4), ['Calories', 'Protein', 'Carbs', 'Fat'],
                                                            [meal.calories, meal.protein_g, meal.carbs_g, meal.fat_g], ['kcal', 'g', 'g', 'g']):
                            column.metric(label, f'{value:g} {unit}')
            else:
                st.subheader(day.focus)
                st.caption(f'Estimated time: {day.est_minutes} minutes')
                st.markdown('**Warmup**')
                for step in day.warmup:
                    st.write(f'• {step}')
                st.dataframe([{'Exercise': exercise.name, 'Sets': exercise.sets, 'Reps': exercise.reps,
                               'Rest (sec)': exercise.rest_seconds, 'RPE / RIR': exercise.rpe_or_rir}
                              for exercise in day.exercises], hide_index=True, width='stretch')
                for exercise in day.exercises:
                    with st.expander(f'{exercise.name}: form and alternatives'):
                        for cue in exercise.form_cues:
                            st.write(f'• {cue}')
                        st.write(f'Easier: {exercise.easier_option}')
                        st.write(f'Harder: {exercise.harder_option}')
                st.markdown('**Cooldown**')
                for step in day.cooldown:
                    st.write(f'• {step}')
    if meal_plan:
        with tabs[-1]:
            st.dataframe([item.model_dump() for item in plan.grocery_list], hide_index=True, width='stretch')
    else:
        st.subheader('Progression and cardio')
        for note in [*plan.progression_notes, *plan.cardio_notes]:
            st.write(f'• {note}')
    st.subheader('Notes')
    for note in plan.notes:
        st.write(f'• {note}')
    st.info('\n\n'.join(DISCLAIMER))
    markdown, plain = st.columns(2)
    markdown.download_button('Download Markdown', export_plan(plan, request, issues), 'fitness-plan.md', 'text/markdown', key='plan_builder_download_md')
    plain.download_button('Download text', export_plan(plan, request, issues, plain_text=True), 'fitness-plan.txt', 'text/plain', key='plan_builder_download_txt')
