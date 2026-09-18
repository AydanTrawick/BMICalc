import pandas as pd
import streamlit as st

from services.guides import GLOSSARY_TERMS
from services.ui import render_chat_widget

st.set_page_config(page_title='Glossary', page_icon='📖', layout='centered')

from services.browser_auth import restore_session
restore_session()
st.page_link('BMI2.py', label='← Back to Home')
st.title('Glossary')
st.caption('A quick reference for workout and nutrition terms.')
rows = [
    {'#': index, 'Term': term, 'What it means': definition}
    for index, (term, definition) in enumerate(GLOSSARY_TERMS, 1)
]
st.dataframe(
    pd.DataFrame(rows),
    hide_index=True,
    width='stretch',
    height=(len(rows) + 1) * 35 + 3,
    column_config={
        '#': st.column_config.NumberColumn('#', width='small', format='%d'),
        'Term': st.column_config.TextColumn('Term', width='medium'),
        'What it means': st.column_config.TextColumn('What it means', width='large'),
    },
)
st.page_link('pages/Workout_Log.py', label='Workout log', icon='🏋️')
st.page_link('pages/Food_Log.py', label='Food log', icon='🥗')
from assistant.widget import assistant_widget
assistant_widget()
