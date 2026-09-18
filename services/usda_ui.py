"""USDA food selection, portion preview, and saving to the existing tracker."""
from datetime import date

import streamlit as st

from services import usda
from services.portions import default_amount, describe_portion, grams_from_amount, usda_portion_units
from services.tracking import append_records, StorageError


def render_usda_entry():
    key = usda.api_key()
    if not key:
        st.info('USDA search is not connected yet. You can still use common foods or enter macros manually.')
        return
    with st.form('usda_search'):
        query = st.text_input('Search USDA foods', max_chars=200, placeholder='e.g. chicken breast, oats, or a brand name')
        searched = st.form_submit_button('Search foods')
    if searched:
        st.session_state['usda_query'] = query.strip()
        st.session_state['usda_page'] = 1
        st.session_state.pop('usda_selection', None)
    active_query = st.session_state.get('usda_query')
    if not active_query:
        if searched:
            st.info('Enter a food name or brand to search.')
        return
    page = st.session_state.get('usda_page', 1)
    try:
        with st.spinner('Searching USDA…'):
            result = usda.search_foods(active_query, key, page)
    except usda.USDAError as error:
        st.error(str(error))
        return
    foods = result['foods']
    if not foods:
        st.info('No matching foods found. Try another food name or brand.')
        return
    st.caption(f"Results for ‘{active_query}’ · Page {page} of {max(1, result['totalPages'])}")
    previous, following = st.columns(2)
    if previous.button('Previous results', disabled=page <= 1):
        st.session_state['usda_page'] = page - 1
        st.session_state.pop('usda_selection', None)
        st.rerun()
    if following.button('Next results', disabled=page >= result['totalPages']):
        st.session_state['usda_page'] = page + 1
        st.session_state.pop('usda_selection', None)
        st.rerun()
    choices = {food['fdcId']: food for food in foods}
    selected = st.selectbox('Select a USDA food', list(choices), index=None,
                            format_func=lambda value: usda.food_label(choices[value]),
                            key='usda_selection', placeholder='Choose a food to view its macros')
    if selected is None:
        return
    try:
        with st.spinner('Loading food nutrients…'):
            food = usda.food_details(selected, key)
        portion_units = usda_portion_units(food)
        amount_column, unit_column = st.columns(2)
        unit = unit_column.selectbox('Unit', list(portion_units), key=f'usda_unit_{selected}')
        maximum = 10000.0 / portion_units[unit]
        default = default_amount(unit, maximum)
        amount = amount_column.number_input('Amount', min_value=0.01, max_value=maximum,
                                            value=default, step=0.25,
                                            key=f'usda_amount_{selected}_{unit}')
        grams = grams_from_amount(amount, portion_units[unit])
        macros = usda.macros_for_portion(food, grams)
    except usda.USDAError as error:
        st.warning(str(error))
        return
    st.caption(f'Match the food and preparation you ate. This portion converts to {grams:,.1f} g for the macro calculation.')
    st.markdown(f'[Source: USDA FoodData Central](https://fdc.nal.usda.gov/food-details/{selected}/nutrients)')
    calories = macros['protein_g'] * 4 + macros['carbs_g'] * 4 + macros['fat_g'] * 9
    columns = st.columns(4)
    for column, label, value in zip(columns, ['Portion calories', 'Portion protein (g)', 'Portion carbs (g)', 'Portion fat (g)'],
                                    [calories, macros['protein_g'], macros['carbs_g'], macros['fat_g']]):
        column.metric(label, f'{value:,.1f}')
    with st.form('usda_add'):
        day = st.date_input('Date', value=date.today(), key='usda_date')
        save = st.form_submit_button('Add to food log', type='primary')
    if save:
        # Keep brand and source ID in the existing food name so exports retain provenance.
        description = str(food.get('description') or choices[selected]['description'])
        brand = food.get('brandOwner') or food.get('brandName')
        suffix = f" · {brand}" if brand else ''
        source = f' (USDA {selected}; {describe_portion(amount, unit, grams)})'
        name = description + suffix + source
        try:
            append_records('food_log', [dict(date=day.isoformat(), food=name, **macros)])
            st.success('Food saved.')
        except (ValueError, StorageError) as error:
            st.error(str(error))
