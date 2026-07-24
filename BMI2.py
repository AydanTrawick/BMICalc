import streamlit as st


st.set_page_config(
    page_title="FirstRep Toolkit",
    page_icon="🏋️",
    layout="centered",
)


st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .block-container {
            padding-top: 2rem;
            max-width: 860px;
        }

        .home-title {
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: 0;
            margin-bottom: 0.25rem;
        }

        .home-subtitle {
            color: #64748b;
            font-size: 1.05rem;
            line-height: 1.6;
            margin-bottom: 2rem;
        }

        .section-label {
            color: #475569;
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0.08rem;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown('<h1 class="home-title">FirstRep Toolkit</h1>', unsafe_allow_html=True)
st.markdown(
    """
    <p class="home-subtitle">
        Quick tools and training guides for checking your starting point,
        choosing a workout path, and learning smarter recovery basics.
    </p>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="section-label">NEW!</p>', unsafe_allow_html=True)
st.page_link(
    "pages/Meal_Plans.py",
    label= "Meal Plan Generator",
    icon="🍽️",

)
st.caption("Create meal plans based on your goals, budget, and schedule!")
st.divider()

st.markdown('<p class="section-label">Latest read</p>', unsafe_allow_html=True)
st.page_link(
    "pages/Enhancers.py",
    label="10 Trending Enhancers",
    icon="🧬",
)
st.caption("A new guide covering commonly discussed hormones, peptides, steroids, and performance-enhancing compounds.")

st.divider()

st.markdown('<p class="section-label">BMI Calculator</p>', unsafe_allow_html=True)
st.page_link(
    "pages/BMI_Calculator.py",
    label="Open BMI Calculator",
    icon="⚖️",
)
st.caption("Calculate your BMI, review your healthy weight range, and get suggested workout plans.")

st.divider()

st.markdown('<p class="section-label">Guides</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/Recovery.py", label="4th of July/Hangover Recovery Guide", icon="🤕")
    st.page_link("pages/FullBody.py", label="3 Day Full Body Routine", icon="💪")
    st.page_link("pages/UpperLower.py", label="Upper / Lower Routine", icon="🏋️")

with col2:
    st.page_link("pages/PPL.py", label="Push Pull Legs", icon="📋")
    st.page_link("pages/Hybrid.py", label="Lift + Cardio Hybrid", icon="💪")
    st.page_link("pages/Cardio.py", label="Cardio + Strength", icon="🏃")
