from datetime import date

import pandas as pd
import streamlit as st

from services.foods import FOODS
from services.portions import MASS_UNITS, default_amount, describe_portion, grams_from_amount
from services.usda_ui import render_usda_entry
from services.guides import render_guides
from services.tracking import frame, log_controls, validate, prepare_log, append_records, StorageError
from services.ui import render_chat_widget

st.set_page_config(page_title='Food log', page_icon='🥗', layout='centered')

from services.browser_auth import restore_session
restore_session()
st.sidebar.caption('This app is an educational tool, not medical advice.')
prepare_log('food_log')
st.page_link('BMI2.py', label='← Back to Home')
st.title('Food log')
st.caption('Log what you ate. Calories are calculated from protein, carbohydrate, and fat.')
frame('food_log')
method = st.radio('Entry method', ['Common food', 'USDA food search', 'Enter macros manually'], horizontal=True)
if method == 'USDA food search':
    render_usda_entry()
else:
    with st.form('food_entry'):
        day = st.date_input('Date', value=date.today())
        if method == 'Common food':
            food = st.selectbox('Food', list(FOODS))
            amount_column, unit_column = st.columns(2)
            unit = unit_column.selectbox('Unit', list(MASS_UNITS))
            maximum = 10000.0 / MASS_UNITS[unit]
            default = default_amount(unit, maximum)
            amount = amount_column.number_input('Amount', min_value=0.01, max_value=maximum,
                                                value=default, key=f'common_amount_{unit}')
            grams = grams_from_amount(amount, MASS_UNITS[unit])
            st.caption('Reference values are approximate per 100 g. Ounces and pounds are converted to grams before macros are calculated.')
            protein, carbs, fat = (macro * grams / 100 for macro in FOODS[food])
            name = f'{food} ({describe_portion(amount, unit, grams)})'
        else:
            name = st.text_input('Food or meal name')
            st.caption('Enter the macros for the entire portion you ate, scaling the label serving if needed.')
            a, b, c = st.columns(3)
            protein = a.number_input('Protein (g)', min_value=0.0, max_value=10000.0, step=0.1)
            carbs = b.number_input('Carbohydrate (g)', min_value=0.0, max_value=10000.0, step=0.1)
            fat = c.number_input('Fat (g)', min_value=0.0, max_value=10000.0, step=0.1)
        submitted = st.form_submit_button('Save food', type='primary')
    if submitted:
        try:
            record = validate('food_log', [dict(date=day.isoformat(), food=name, protein_g=protein, carbs_g=carbs, fat_g=fat)])[0]
            append_records('food_log', [record])
            st.success('Food saved.')
        except (ValueError, StorageError) as error:
            st.error(str(error))
data = frame('food_log')
st.subheader('Daily totals')
selected_day = st.date_input('View date', value=date.today())
daily = data[data.date == selected_day.isoformat()]
totals = daily[['protein_g', 'carbs_g', 'fat_g', 'calories']].sum()
for column, key, label in zip(st.columns(4), ['calories', 'protein_g', 'carbs_g', 'fat_g'], ['Calories', 'Protein (g)', 'Carbs (g)', 'Fat (g)']):
    column.metric(label, f'{totals[key]:,.1f}')
if daily.empty:
    st.info('No foods logged for this date. Add a food or choose another date.')
else:
    if totals.calories > 0:
        st.subheader('Share of calories')
        split = pd.DataFrame({'Macro': ['Protein', 'Carbohydrate', 'Fat'], 'Share (%)': [totals.protein_g * 4, totals.carbs_g * 4, totals.fat_g * 9]})
        split['Share (%)'] = split['Share (%)'] / totals.calories * 100
        st.bar_chart(split, x='Macro', y='Share (%)', horizontal=True)
    st.dataframe(daily, hide_index=True)
st.caption('Calories = protein × 4 + carbohydrate × 4 + fat × 9. This simplified calculation may differ from food labels that account for fibre, sugar alcohols, or rounding.')
log_controls('food_log', editable=True)
render_guides(['Understanding macros', 'When to ask for help', 'Glossary'])
from assistant.widget import assistant_widget, activity_log_section
activity_log_section(['meal'])
assistant_widget()
