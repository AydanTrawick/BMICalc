import re
import smtplib
from typing import Any

import streamlit as st
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    RateLimitError,
)

from services.email_service import send_meal_plan_email
from services.meal_plan_services import generate_meal_plan
from services.pdf_service import build_meal_plan_pdf

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")



# PAGE CONFIGURATION


st.set_page_config(
    page_title="Meal Planner",
    page_icon="🍽️",
    layout="wide",
)



# SESSION STATE


if "generated_meal_plan" not in st.session_state:
    st.session_state.generated_meal_plan = None


# CUSTOM CSS


st.markdown(
    """
    <style>
        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .meal-planner-hero {
            padding: 2rem;
            margin-bottom: 1.5rem;
            border-radius: 22px;
            background:
                linear-gradient(
                    135deg,
                    rgba(14, 31, 25, 1),
                    rgba(26, 91, 61, 1)
                );
            color: white;
        }

        .hero-label {
            color: white;
            font-size: 0.85rem;
            font-weight: 800;
            letter-spacing: 0.12rem;
            text-transform: uppercase;
        }

        .hero-title {
            margin-top: 0.35rem;
            margin-bottom: 0.7rem;
            font-size: 2.5rem;
            font-weight: 800;
            color: white;
        }

        .hero-description {
            color: white;
            font-size: 1.05rem;
            max-width: 750px;
        }

        .section-heading {
            margin-top: 1.5rem;
            margin-bottom: 0.6rem;
            font-size: 1.4rem;
            font-weight: 800;
            color: white;
        }

        .meal-card {
            padding: 1.1rem;
            margin-bottom: 0.9rem;
            background: white;
            border: 1px solid #e1e8e4;
            border-left: 5px solid #218f57;
            border-radius: 14px;
            box-shadow: 0 4px 15px rgba(15, 23, 42, 0.05);
        }

        .meal-type {
            color: #218f57;
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0.05rem;
            text-transform: uppercase;
        }

        .meal-name {
            margin-top: 0.2rem;
            margin-bottom: 0.4rem;
            font-size: 1.15rem;
            font-weight: 800;
            color: black;
        }

        .macro-line {
            color: #506057;
            font-size: 0.9rem;
        }

        .disclaimer {
            padding: 1rem;
            margin-top: 1rem;
            color: #665620;
            background: #fff8dd;
            border: 1px solid #f2d97f;
            border-radius: 12px;
        }

        div[data-testid="stForm"] {
            padding: 1.3rem;
            background: white;
            border: 1px solid #e1e8e4;
            border-radius: 18px;
        }

        div[data-testid="stForm"] h3,
        div[data-testid="stForm"] label,
        div[data-testid="stForm"] label p,
        div[data-testid="stForm"] div[data-testid="stWidgetLabel"] p {
            color: black;
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 3rem;
            font-weight: 700;
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def format_height(
    measurement_system: str,
    feet: int,
    inches: int,
    centimeters: int,
) -> str:
    if measurement_system == "Imperial":
        return f"{feet} feet {inches} inches"

    return f"{centimeters} centimeters"


def format_weight(
    measurement_system: str,
    pounds: float,
    kilograms: float,
) -> str:
    if measurement_system == "Imperial":
        return f"{pounds:.1f} pounds"

    return f"{kilograms:.1f} kilograms"


def display_macro_metrics(targets: dict[str, Any]) -> None:
    columns = st.columns(4)

    columns[0].metric(
        "Calories",
        f'{targets.get("calories", 0):,.0f}',
    )
    columns[1].metric(
        "Protein",
        f'{targets.get("protein_g", 0):,.0f} g',
    )
    columns[2].metric(
        "Carbohydrates",
        f'{targets.get("carbs_g", 0):,.0f} g',
    )
    columns[3].metric(
        "Fat",
        f'{targets.get("fat_g", 0):,.0f} g',
    )


def display_meal(meal: dict[str, Any]) -> None:
    meal_type = meal.get("meal_type", "Meal")
    meal_name = meal.get("name", "Unnamed meal")

    st.markdown(
        f"""
        <div class="meal-card">
            <div class="meal-type">{meal_type}</div>
            <div class="meal-name">{meal_name}</div>
            <div class="macro-line">
                {meal.get("calories", 0)} calories ·
                {meal.get("protein_g", 0)} g protein ·
                {meal.get("carbs_g", 0)} g carbs ·
                {meal.get("fat_g", 0)} g fat
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_column, right_column = st.columns(2)

    with left_column:
        st.markdown("**Ingredients**")

        ingredients = meal.get("ingredients", [])

        if ingredients:
            for ingredient in ingredients:
                st.markdown(f"- {ingredient}")
        else:
            st.write("No ingredients were provided.")

    with right_column:
        st.markdown("**Suggested Instructions**")

        instructions = meal.get("instructions", [])

        if instructions:
            for step_number, instruction in enumerate(
                instructions,
                start=1,
            ):
                st.markdown(f"{step_number}. {instruction}")
        else:
            st.write("No instructions were provided.")


def display_meal_plan(plan: dict[str, Any]) -> None:
    st.divider()

    st.header(plan.get("plan_title", "Your FirstRep Meal Plan"))
    st.write(plan.get("summary", ""))

    with st.expander("📧 Email me this meal plan"):
        with st.form("email_meal_plan_form"):
            email_address = st.text_input(
                "Your email address",
                placeholder="you@example.com",
            )

            email_submitted = st.form_submit_button("Send meal plan")

        if email_submitted:
            if not _EMAIL_PATTERN.match(email_address.strip()):
                st.error("Enter a valid email address.")
            else:
                try:
                    sender_email = st.secrets["EMAIL_ADDRESS"]
                    sender_password = st.secrets["EMAIL_PASSWORD"]

                    with st.spinner("Sending your meal plan..."):
                        pdf_bytes = build_meal_plan_pdf(plan)

                        send_meal_plan_email(
                            sender_email=sender_email,
                            sender_password=sender_password,
                            to_email=email_address.strip(),
                            plan=plan,
                            pdf_bytes=pdf_bytes,
                        )

                    st.success(
                        f"Sent your meal plan to {email_address.strip()}."
                    )

                except KeyError:
                    st.error(
                        "Email sending is not configured. Add "
                        "EMAIL_ADDRESS and EMAIL_PASSWORD to "
                        ".streamlit/secrets.toml."
                    )

                except smtplib.SMTPAuthenticationError:
                    st.error(
                        "The email server rejected the login "
                        "credentials."
                    )

                except smtplib.SMTPException as error:
                    st.error(f"The email could not be sent: {error}")

    st.markdown(
        '<div class="section-heading">Estimated daily targets</div>',
        unsafe_allow_html=True,
    )

    targets = plan.get("estimated_daily_targets", {})
    display_macro_metrics(targets)

    st.markdown(
        '<div class="section-heading">Daily meal plan</div>',
        unsafe_allow_html=True,
    )

    days = plan.get("days", [])

    for day in days:
        day_number = day.get("day", "?")

        with st.expander(
            f"Day {day_number}",
            expanded=day_number == 1,
        ):
            daily_totals = day.get("daily_totals", {})

            display_macro_metrics(daily_totals)

            st.markdown("### Meals")

            for meal in day.get("meals", []):
                display_meal(meal)

    st.markdown(
        '<div class="section-heading">Grocery list</div>',
        unsafe_allow_html=True,
    )

    grocery_categories = plan.get("grocery_list", [])

    if grocery_categories:
        for category in grocery_categories:
            category_name = category.get("category", "Other")

            st.markdown(f"### {category_name}")

            grocery_rows = []

            for item in category.get("items", []):
                grocery_rows.append(
                    {
                        "Item": item.get("name", ""),
                        "Quantity": item.get("quantity", ""),
                        "Estimated price": (
                            f'${item.get("estimated_price", 0):.2f}'
                        ),
                    }
                )

            if grocery_rows:
                st.dataframe(
                    grocery_rows,
                    use_container_width=True,
                    hide_index=True,
                )

    total = plan.get("estimated_grocery_total", 0)

    st.metric(
        "Estimated grocery total",
        f"${total:,.2f}",
    )

    prep_tips = plan.get("prep_tips", [])

    if prep_tips:
        st.markdown(
            '<div class="section-heading">Meal-prep tips</div>',
            unsafe_allow_html=True,
        )

        for tip in prep_tips:
            st.markdown(f"- {tip}")

    disclaimer = plan.get(
        "disclaimer",
        (
            "This plan is general educational information and is not "
            "medical advice."
            "Keep it 1 sentence max."

        
        ),
    )

    st.markdown(
        f'<div class="disclaimer">{disclaimer}</div>',
        unsafe_allow_html=True,
    )

    pdf_data = build_meal_plan_pdf(plan)

    st.download_button(
        label="Download meal plan",
        data=pdf_data,
        file_name="firstrep_meal_plan.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ---------------------------------------------------------
# PAGE HEADER
# ---------------------------------------------------------

st.markdown("<div style='margin-top: 45px;'></div>", unsafe_allow_html=True)
st.page_link("Toolkit.py", label="⬅ Back to Home")
st.markdown(
    """
    <div class="meal-planner-hero">
        <div class="hero-label">FirstRep Nutrition</div>
        <div class="hero-title">Generalized Meal Planner</div>
        <div class="hero-description">
            Build a personalized meal plan based on your fitness goal,
            dietary needs, schedule, and grocery budget.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# INPUT FORM
# ---------------------------------------------------------

st.subheader("Tell us about yourself")

measurement_system = st.selectbox(
    "Measurement system",
    options=[
        "Imperial",
        "Metric",
    ],
    key="measurement_system",
)

with st.form("meal_plan_form"):
    basic_column_1, basic_column_2 = st.columns(2)

    with basic_column_1:
        age = st.number_input(
            "Age",
            min_value=13,
            max_value=100,
            value=21,
            step=1,
        )

    with basic_column_2:
        sex = st.selectbox(
            "Sex",
            options=[
                "Male",
                "Female",
                "Other",
                "Prefer not to say",
            ],
        )

    measurement_column_1, measurement_column_2 = st.columns(2)

    if measurement_system == "Imperial":
        with measurement_column_1:
            feet_column, inches_column = st.columns(2)

            with feet_column:
                feet = st.number_input(
                    "Height: feet",
                    min_value=2,
                    max_value=8,
                    value=5,
                    step=1,
                )

            with inches_column:
                inches = st.number_input(
                    "Height: inches",
                    min_value=0,
                    max_value=11,
                    value=10,
                    step=1,
                )

        with measurement_column_2:
            pounds = st.number_input(
                "Weight in pounds",
                min_value=50.0,
                max_value=800.0,
                value=175.0,
                step=1.0,
            )

        centimeters = 0
        kilograms = 0.0

    else:
        with measurement_column_1:
            centimeters = st.number_input(
                "Height in centimeters",
                min_value=100,
                max_value=250,
                value=178,
                step=1,
            )

        with measurement_column_2:
            kilograms = st.number_input(
                "Weight in kilograms",
                min_value=30.0,
                max_value=320.0,
                value=79.0,
                step=0.5,
            )

        feet = 0
        inches = 0
        pounds = 0.0

    st.subheader("Set your meal plan preferences")

    preference_column_1, preference_column_2 = st.columns(2)

    with preference_column_1:
        goal = st.selectbox(
            "Primary fitness goal",
            options=[
                "Cut body fat",
                "Build muscle",
                "Maintain weight",
                "Improve general nutrition",
            ],
        )

        activity_level = st.selectbox(
            "Activity level",
            options=[
                "Mostly sedentary",
                "Lightly active",
                "Moderately active",
                "Very active",
                "Athlete-level activity",
            ],
        )

        dietary_preference = st.selectbox(
            "Dietary preference",
            options=[
                "No specific preference",
                "High protein",
                "Vegetarian",
                "Vegan",
                "Pescatarian",
                "Low carbohydrate",
                "Dairy free",
                "Gluten free",
            ],
        )

    with preference_column_2:
        plan_days = st.slider(
            "Number of days",
            min_value=1,
            max_value=7,
            value=7,
        )

        meals_per_day = st.slider(
            "Meals per day",
            min_value=2,
            max_value=6,
            value=4,
        )

        allergies = st.text_area(
            "Allergies or foods to avoid",
            placeholder=(
                "Example: peanuts, shellfish, mushrooms, or none"
            ),
        )

    st.subheader("Set your grocery budget")

    budget_column_1, budget_column_2 = st.columns(2)

    with budget_column_1:
        budget = st.number_input(
            "Budget amount",
            min_value=50.0,
            max_value=2000.0,
            value=100.0,
            step=5.0,
        )

    with budget_column_2:
        budget_period = st.selectbox(
            "Budget period",
            options=[
                "Weekly",
                "Bi-weekly",
             
            ],
        )

    submitted = st.form_submit_button(
        " Create my meal plan",
        use_container_width=True,
    )



# FORM SUBMISSION


if submitted:
    height = format_height(
        measurement_system=measurement_system,
        feet=feet,
        inches=inches,
        centimeters=centimeters,
    )

    weight = format_weight(
        measurement_system=measurement_system,
        pounds=pounds,
        kilograms=kilograms,
    )

    user_data = {
        "age": age,
        "sex": sex,
        "height": height,
        "weight": weight,
        "goal": goal,
        "activity_level": activity_level,
        "plan_days": plan_days,
        "allergies": allergies.strip() or "None reported",
        "dietary_preference": dietary_preference,
        "budget": budget,
        "budget_period": budget_period,
        "meals_per_day": meals_per_day,
    }

    try:
        api_key = st.secrets["OPENAI_API_KEY"]
        model = st.secrets.get(
            "OPENAI_MODEL",
            "gpt-5-mini",
        )

        with st.spinner(
            "Creating your meal plan..."
        ):
            meal_plan = generate_meal_plan(
                api_key=api_key,
                model=model,
                user_data=user_data,
            )

        st.session_state.generated_meal_plan = meal_plan
        st.success("Your meal plan is ready.")

    except KeyError:
        st.error(
            "OPENAI_API_KEY was not found in "
            ".streamlit/secrets.toml."
        )

    except AuthenticationError:
        st.error(
            "The OpenAI API key was rejected. Check that the key "
            "is correct and active."
        )

    except RateLimitError:
        st.error(
            "The OpenAI request limit was reached. Check your API "
            "usage, billing, or rate limits."
        )

    except APIConnectionError:
        st.error(
            "The app could not connect to OpenAI. Check your "
            "internet connection and try again."
        )

    except APIError as error:
        st.error(f"OpenAI returned an API error: {error}")

    except ValueError as error:
        st.error(str(error))

    except Exception as error:
        st.error(
            "An unexpected error occurred while creating the plan."
        )

        # Useful while developing. Remove this before production
        # if you do not want users to see internal errors.
        st.exception(error)



# DISPLAY SAVED RESULT


if st.session_state.generated_meal_plan:
    display_meal_plan(
        st.session_state.generated_meal_plan
    )