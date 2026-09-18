from datetime import date

import streamlit as st

from services.guides import render_guides
from services.tracking import frame, log_controls, validate, prepare_log, append_records, StorageError
from services.ui import render_chat_widget

st.set_page_config(page_title='Workout log', page_icon='🏋️', layout='centered')

from services.browser_auth import restore_session
restore_session()
st.sidebar.caption('This app is an educational tool, not medical advice.')
prepare_log('workout_log')
st.page_link('BMI2.py', label='← Back to Home')
st.title('Workout log')
st.caption('Record your work. Follow your progress over a training block.')
data = frame('workout_log')
units = st.radio('Weight units', ['lb', 'kg'], horizontal=True)
names = sorted(data.exercise.unique().tolist())
previous = st.selectbox('Use a previous exercise', ['New exercise', *names])
def add_workout_set():
    st.session_state.workout_set_count += 1


def remove_workout_set():
    st.session_state.workout_set_count -= 1
    index = st.session_state.workout_set_count
    for field in ('reps', 'weight', 'rpe'):
        st.session_state.pop(f'workout_{field}_{index}', None)


st.session_state.setdefault('workout_set_count', 1)
with st.form('workout_entry'):
    day = st.date_input('Session date', value=date.today())
    exercise = st.text_input('Exercise name') if previous == 'New exercise' else previous
    st.caption('Use the same exercise name each time so your progress stays together.')
    set_inputs = []
    for index in range(st.session_state.workout_set_count):
        st.markdown(f'**Set {index + 1}**')
        a, b = st.columns(2)
        reps = a.number_input('Reps', min_value=1, max_value=1000, value=8, key=f'workout_reps_{index}')
        weight = b.number_input(f'Weight ({units})', min_value=0.0, value=0.0, step=0.5, key=f'workout_weight_{index}')
        rpe = st.slider('RPE — how hard did it feel?', 1.0, 10.0, 8.0, 0.5, key=f'workout_rpe_{index}')
        set_inputs.append((reps, weight, rpe))
    a, b = st.columns(2)
    a.form_submit_button('Add set', on_click=add_workout_set, disabled=st.session_state.workout_set_count >= 100)
    b.form_submit_button('Remove last set', on_click=remove_workout_set, disabled=st.session_state.workout_set_count <= 1)
    notes = st.text_area('Notes (optional)', placeholder='How did it feel? Technique, energy, anything to remember…')
    submitted = st.form_submit_button('Save workout', type='primary')
st.caption('Add sets with their own reps, weight, and RPE. Nothing is logged until you press Save workout.')
if submitted:
    try:
        records = validate('workout_log', [
            dict(date=day.isoformat(), exercise=exercise, sets=1, reps=reps,
                 weight_kg=weight * 0.45359237 if units == 'lb' else weight,
                 rpe=rpe, notes=notes)
            for reps, weight, rpe in set_inputs
        ])
        match = next((name for name in names if name.casefold() == records[0]['exercise'].casefold()), None)
        for record in records:
            record['exercise'] = match or record['exercise']
        append_records('workout_log', records)
        st.success(f'Workout saved: {len(records)} set(s).')
    except (ValueError, StorageError) as error:
        st.error(str(error))
data = frame('workout_log')
factor = 1 / 0.45359237 if units == 'lb' else 1
if data.empty:
    st.info('Save your first exercise to see your session totals and progress.')
else:
    display = data.rename(columns={'weight_kg': f'weight_{units}', 'volume_kg': f'volume_{units}'}).copy()
    display[f'weight_{units}'] *= factor
    display[f'volume_{units}'] *= factor
    a, b, c = st.columns(3)
    a.metric('Entries', len(data))
    b.metric('Sessions (distinct dates)', data.date.nunique())
    c.metric(f'Total volume ({units})', f'{data.volume_kg.sum() * factor:,.0f}')
    st.subheader('Volume over time')
    st.line_chart(display.groupby('date')[[f'volume_{units}']].sum())
    st.subheader('Exercise progress')
    selected = st.selectbox('Exercise to track', sorted(data.exercise.unique()))
    single = display[display.exercise == selected].groupby('date').agg({f'weight_{units}': 'max', f'volume_{units}': 'sum'})
    st.caption('Highest logged weight and total volume for each date.')
    st.line_chart(single[[f'weight_{units}']])
    st.line_chart(single[[f'volume_{units}']])
    st.dataframe(display, hide_index=True)
st.caption('Volume = sets × reps × weight. It is a rough measure of total work, not technique or intensity. Zero external load records bodyweight work but contributes no load volume. Sessions are grouped by date.')
log_controls('workout_log', editable=True)
render_guides(['How to read a workout', 'Warm-up and form', 'Glossary'])
from assistant.widget import assistant_widget, activity_log_section
activity_log_section(['strength', 'cardio', 'bodyweight'])
assistant_widget()
