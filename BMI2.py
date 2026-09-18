from datetime import date

import streamlit as st

from services.ui import (
    current_user,
    render_auth_panel,
    render_chat_widget,
    render_home_user_icon,
)
from services.auth_service import is_admin_user
from services.tracking import frame
from services.tracking_store import StorageError
from services import tracking_store


st.set_page_config(
    page_title="FirstRep Toolkit",
    page_icon="🏋️",
    layout="wide",
)

from services.browser_auth import restore_session
restore_session()

st.sidebar.caption("This app is an educational tool, not medical advice.")



st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }




            :root {
                --fr-page-text: #f8fafc;
                --fr-section-heading-text: #f8fafc;
                --fr-muted-text: #dbeafe;
                --fr-soft-text: #cbd5e1;
                --fr-accent-text: #5eead4;
                --fr-link-text: #7dd3fc;
                --fr-surface: #111827;
                --fr-surface-soft: #172033;
                --fr-hero-bg:
                    radial-gradient(circle at 85% 15%, rgba(20, 184, 166, 0.24), transparent 30%),
                    linear-gradient(135deg, #111827 0%, #172033 48%, #0f172a 100%);
                --fr-border: #334155;
                --fr-shadow: rgba(0, 0, 0, 0.34);
                --fr-card-shadow: rgba(0, 0, 0, 0.28);
                --fr-chip-bg: rgba(15, 23, 42, 0.72);
                --fr-chip-text: #e2e8f0;
                --fr-panel-bg: #e2e8f0;
                --fr-panel-text: #0f172a;
                --fr-panel-muted: #334155;
                --fr-panel-accent: #0f766e;
            }


        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 5rem;
        }

        .home-hero {
            display: grid;
            grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
            gap: 1.6rem;
            align-items: stretch;
            padding: 2rem;
            border: 1px solid var(--fr-border);
            border-radius: 24px;
            background: var(--fr-hero-bg);
            box-shadow: 0 18px 50px var(--fr-shadow);
        }

        .home-eyebrow {
            margin-bottom: 0.65rem;
            color: var(--fr-accent-text);
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0.1rem;
            text-transform: uppercase;
        }

        .home-title {
            max-width: 740px;
            margin: 0;
            color: var(--fr-page-text);
            font-size: clamp(2.3rem, 5vw, 4.5rem);
            font-weight: 800;
            line-height: 0.98;
            letter-spacing: 0;
        }

        .home-subtitle {
            max-width: 650px;
            margin: 1rem 0 1.35rem;
            color: var(--fr-muted-text);
            font-size: 1.05rem;
            line-height: 1.65;
        }

        .hero-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
        }

        .hero-pill {
            padding: 0.5rem 0.72rem;
            border: 1px solid var(--fr-border);
            border-radius: 999px;
            background: var(--fr-chip-bg);
            color: var(--fr-chip-text);
            font-size: 0.83rem;
            font-weight: 700;
        }

        .hero-panel {
            display: flex;
            min-height: 260px;
            flex-direction: column;
            justify-content: space-between;
            padding: 1.2rem;
            border-radius: 20px;
            background: var(--fr-panel-bg);
            color: var(--fr-panel-text);
        }

        .hero-panel-label {
            color: var(--fr-panel-accent);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08rem;
            text-transform: uppercase;
        }

        .hero-panel-number {
            margin-top: 0.75rem;
            font-size: 3.4rem;
            font-weight: 800;
            line-height: 1;
        }

        .hero-panel-copy {
            color: var(--fr-panel-muted);
            line-height: 1.5;
        }

        .account-card {
            padding: 1.05rem 1.15rem;
            margin: 1.25rem 0 1.5rem;
            border: 1px solid var(--fr-border);
            border-radius: 18px;
            background: var(--fr-surface);
            box-shadow: 0 12px 30px var(--fr-card-shadow);
        }

        .account-eyebrow,
        .section-label {
            color: var(--fr-accent-text);
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 0.08rem;
            text-transform: uppercase;
        }

        .account-title {
            margin-top: 0.25rem;
            color: var(--fr-page-text);
            font-size: 1.35rem;
            font-weight: 800;
        }

        .account-copy {
            margin-top: 0.2rem;
            color: var(--fr-soft-text);
        }

        .section-heading {
            margin: 1.4rem 0 0.3rem;
            color: var(--fr-section-heading-text);
            font-size: 1.45rem;
            font-weight: 800;
        }

        .section-copy {
            margin: 0 0 0.9rem;
            color: var(--fr-soft-text);
            line-height: 1.55;
        }

        .tool-card {
            min-height: 155px;
            padding: 1.1rem;
            margin-bottom: 0.8rem;
            border: 1px solid var(--fr-border);
            border-radius: 16px;
            background: var(--fr-surface);
            box-shadow: 0 10px 28px var(--fr-card-shadow);
        }

        .tool-kicker {
            color: var(--fr-soft-text);
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.08rem;
            text-transform: uppercase;
        }

        .tool-title {
            margin-top: 0.35rem;
            color: var(--fr-page-text);
            font-size: 1.08rem;
            font-weight: 800;
        }

        .tool-copy {
            margin-top: 0.35rem;
            color: var(--fr-soft-text);
            font-size: 0.9rem;
            line-height: 1.45;
        }

        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] p {
            color: var(--fr-soft-text) !important;
        }

        [data-testid="stPageLink"] a,
        [data-testid="stPageLink"] p {
            color: var(--fr-link-text) !important;
            font-weight: 700;
        }

        div[data-testid="stForm"],
        div[data-testid="stTabs"] {
            border-radius: 16px;
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 2.85rem;
            border-radius: 10px;
            font-weight: 800;
        }

        @media (max-width: 760px) {
            .home-hero {
                grid-template-columns: 1fr;
                padding: 1.25rem;
            }

            .hero-panel {
                min-height: 210px;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_tool_card(
    kicker: str,
    title: str,
    copy: str,
    path: str,
    label: str,
    icon: str,
) -> None:
    st.markdown(
        f"""
        <div class="tool-card">
            <div class="tool-kicker">{kicker}</div>
            <div class="tool-title">{title}</div>
            <div class="tool-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(path, label=label, icon=icon)


if "firstrep_auth_open" not in st.session_state:
    st.session_state.firstrep_auth_open = True

render_home_user_icon()

st.markdown(
    f"""
    <section class="home-hero">
        <div>
            <div class="home-eyebrow">FirstRep fitness hub</div>
            <h1 class="home-title">Build your next smart rep.</h1>
            <p class="home-subtitle">
                A cleaner starting point for BMI checks, meal planning,
                workout paths, equipment help, and quick recovery guidance.
            </p>
            <div class="hero-pills">
                <span class="hero-pill">BMI insights</span>
                <span class="hero-pill">Workout routines</span>
                <span class="hero-pill">Meal plans</span>
                <span class="hero-pill">AI coach</span>
            </div>
        </div>
        <aside class="hero-panel">
            <div>
                <div class="hero-panel-label">Today in FirstRep</div>
                <div class="hero-panel-number">{date.today().strftime("%b %-d")}</div>
            </div>
            <p class="hero-panel-copy">
                Tools and guides organized so you can jump into the next
                useful action instead of hunting through a long page.
            </p>
        </aside>
    </section>
    """,
    unsafe_allow_html=True,
)

if st.session_state.firstrep_auth_open:
    render_auth_panel()
else:
    st.caption(
        "Use the profile icon in the top-right corner to open your account panel."
    )

st.markdown(
    """
    <div class="section-label">Start here</div>
    <div class="section-heading">Quick actions</div>
    <p class="section-copy">
        Pick the tool that matches what you need right now.
    </p>
    """,
    unsafe_allow_html=True,
)

quick_col_1, quick_col_2, quick_col_3 = st.columns(3)

with quick_col_1:
    render_tool_card(
        "Nutrition",
        "Meal Plan Generator",
        "Create a goal-based grocery and meal plan for the week.",
        "pages/Meal_Plans.py",
        "Open Meal Planner",
        "🍽️",
    )

with quick_col_2:
    render_tool_card(
        "Check-in",
        "BMI Calculator",
        "Calculate BMI, review a healthy range, and get routine ideas.",
        "pages/BMI_Calculator.py",
        "Open BMI Calculator",
        "⚖️",
    )

with quick_col_3:
    render_tool_card(
        "Photo tool",
        "Equipment Classifier",
        "Upload gym equipment photos and identify what you are looking at.",
        "pages/EquipmentClassifier.py",
        "Open Classifier",
        "📸",
    )

render_tool_card(
    "Voice + text",
    "AI Plan Builder",
    "Describe a meal or workout plan, answer a few questions, and download your plan.",
    "pages/AI_Plan_Builder.py",
    "Open AI Plan Builder",
    "🎙️",
)

st.markdown(
    """
    <div class="section-label">Training library</div>
    <div class="section-heading">Choose a routine</div>
    <p class="section-copy">
        Start with a focused plan, then adjust volume and conditioning as
        your schedule and recovery allow.
    </p>
    """,
    unsafe_allow_html=True,
)

routine_col_1, routine_col_2, routine_col_3 = st.columns(3)

with routine_col_1:
    st.page_link("pages/FullBody.py", label="3 Day Full Body Routine", icon="💪")
    st.page_link("pages/UpperLower.py", label="Upper / Lower Routine", icon="🏋️")

with routine_col_2:
    st.page_link("pages/PPL.py", label="Push Pull Legs", icon="📋")
    st.page_link("pages/Hybrid.py", label="Lift + Cardio Hybrid", icon="💪")

with routine_col_3:
    st.page_link("pages/Cardio.py", label="Cardio + Strength", icon="🏃")
    st.page_link("pages/Recovery.py", label="Recovery Guide", icon="🤕")

st.markdown(
    """
    <div class="section-label">Learning</div>
    <div class="section-heading">Latest guide</div>
    """,
    unsafe_allow_html=True,
)

st.page_link(
    "pages/Enhancers.py",
    label="10 Trending Enhancers",
    icon="🧬",
)
st.caption(
    "Educational overview of commonly discussed hormones, peptides, "
    "steroids, and performance-enhancing compounds."
)

home_user = current_user()

if is_admin_user(home_user):
    st.markdown(
        """
        <div class="section-label">Admin</div>
        <div class="section-heading">Store management</div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/admin.py", label="Open Admin", icon="🛠️")

st.markdown(
    """
    <div class="section-label">Your logs</div>
    <div class="section-heading">Today's progress</div>
    <p class="section-copy">See today's totals at a glance or open a log to add an entry.</p>
    """,
    unsafe_allow_html=True,
)


def load_home_log(kind):
    if kind not in st.session_state:
        if home_user:
            try:
                st.session_state[kind] = tracking_store.load(home_user['id'], kind)
            except StorageError as error:
                st.warning(f"Could not load this log summary: {error}")
                st.session_state[kind] = []
        else:
            st.session_state[kind] = []
    return frame(kind)


today = date.today().isoformat()
food_today = load_home_log('food_log')
food_today = food_today[food_today.date == today]
workout_today = load_home_log('workout_log')
workout_today = workout_today[workout_today.date == today]

food_widget, workout_widget = st.columns(2)
with food_widget:
    with st.container(border=True):
        st.markdown('### 🥗 Food log')
        food_calories = food_today.calories.sum() if not food_today.empty else 0
        food_entries = len(food_today)
        left, right = st.columns(2)
        left.metric('Calories today', f'{food_calories:,.0f}')
        right.metric('Foods logged', food_entries)
        st.caption(
            f"Protein {food_today.protein_g.sum():,.1f} g · "
            f"Carbs {food_today.carbs_g.sum():,.1f} g · "
            f"Fat {food_today.fat_g.sum():,.1f} g"
        )
        st.page_link("pages/Food_Log.py", label="Open food log", icon="➕")

with workout_widget:
    with st.container(border=True):
        st.markdown('### 🏋️ Workout log')
        workout_sets = int(workout_today.sets.sum()) if not workout_today.empty else 0
        workout_exercises = workout_today.exercise.nunique() if not workout_today.empty else 0
        left, right = st.columns(2)
        left.metric('Sets today', workout_sets)
        right.metric('Exercises', workout_exercises)
        volume = workout_today.volume_kg.sum() if not workout_today.empty else 0
        st.caption(f'Total volume {volume:,.1f} kg')
        st.page_link("pages/Workout_Log.py", label="Open workout log", icon="➕")

st.page_link("pages/Glossary.py", label="Glossary", icon="📖")

from assistant.widget import assistant_widget
assistant_widget()
