import streamlit as st
import datetime

# --- Page Config ---
st.set_page_config(
    page_title="BMI Predictor",
    page_icon="⚖️",
    layout="centered"
)

# --- Custom Styles ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .main {
            background-color: #f8f9fb;
        }

        .bmi-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.07);
            margin-bottom: 1.5rem;
        }

        .bmi-result {
            font-size: 4rem;
            font-weight: 700;
            text-align: center;
            line-height: 1;
        }

        .bmi-label {
            text-align: center;
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 0.4rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .bmi-range-bar {
            height: 10px;
            border-radius: 999px;
            background: linear-gradient(to right, #60a5fa, #34d399, #fbbf24, #f87171);
            margin: 1.5rem 0 0.4rem;
        }

        .range-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.72rem;
            color: #9ca3af;
            font-weight: 500;
        }

        .tip-box {
            background: #f0f9ff;
            border-left: 4px solid #38bdf8;
            border-radius: 8px;
            padding: 0.9rem 1.1rem;
            font-size: 0.9rem;
            color: #0369a1;
            margin-top: 1rem;
        }

        h1 {
            font-weight: 700 !important;
            letter-spacing: -0.02em !important;
        }

        .stSlider > div { padding-top: 0.2rem; }
    </style>
""", unsafe_allow_html=True)


# --- Header ---
st.markdown("## ⚖️ Aydan's BMI Predictor")
st.markdown("Enter your details below to calculate your Body Mass Index.")

st.divider()

# --- User Info ---
col1, col2, col3 = st.columns(3)
with col1:
    first_name = st.text_input("First Name")
with col2: 
    last_nmae= st.text_input("Last Name")
with col3:
    date= st.date_input("Date of Birth", max_value= datetime.date.today(), min_value= datetime.date(1900,1,1))

st.markdown("[💪 Lift + Cardio Hybrid](/Hybrid)")
st.markdown("[3 day Full Body Routine](/FullBody)")
st.markdown("[Upper & Lower](/UpperLower)")
# --- Unit Toggle ---
unit = st.radio("Units", ["Metric (kg / cm)", "Imperial (lbs / ft & in)"], horizontal=True)

st.markdown("")

# --- Inputs ---
if unit == "Metric (kg / cm)":
    col1, col2 = st.columns(2)
    with col1:
        weight_kg = st.number_input("Weight (kg)", min_value=1.0, max_value=300.0, value=70.0, step=0.5)
    with col2:
        height_cm = st.number_input("Height (cm)", min_value=50.0, max_value=250.0, value=170.0, step=0.5)
    height_m = height_cm / 100
    weight_for_calc = weight_kg

else:
    col1, col2, col3 = st.columns(3)
    with col1:
        weight_lbs = st.number_input("Weight (lbs)", min_value=1.0, max_value=660.0, value=154.0, step=1.0)
    with col2:
        height_ft = st.number_input("Height (ft)", min_value=1, max_value=8, value=5, step=1)
    with col3:
        height_in = st.number_input("Inches", min_value=0, max_value=11, value=7, step=1)
    total_inches = (height_ft * 12) + height_in
    height_m = total_inches * 0.0254
    weight_for_calc = weight_lbs * 0.453592

st.markdown("")

# --- Calculate ---
if st.button("Calculate BMI", use_container_width=True, type="primary"):

    if height_m <= 0:
        st.error("Height must be greater than zero.")
    else:
        bmi = weight_for_calc / (height_m ** 2)
        bmi_rounded = round(bmi, 1)

        # Determine category + color
        if bmi < 18.5:
            category = "Underweight"
            color = "#60a5fa"
            tip = "💡 A BMI below 18.5 may indicate insufficient caloric intake. Consider speaking with a healthcare professional."
        elif bmi < 25.0:
            category = "Normal Weight"
            color = "#34d399"
            tip = "✅ You're in a healthy BMI range. Keep up your balanced diet and regular activity!"
        elif bmi < 30.0:
            category = "Overweight"
            color = "#fbbf24"
            tip = "💡 A BMI between 25–30 suggests you may benefit from increased physical activity and dietary adjustments."
        else:
            category = "Obese"
            color = "#f87171"
            tip = "💡 A BMI above 30 is associated with increased health risks. Speaking with a doctor is a good next step."

        st.session_state.category= category

        # --- Result Card ---
        st.markdown(f"""
            <div class="bmi-card">
                <div class="bmi-result" style="color: {color};">{bmi_rounded}</div>
                <div class="bmi-label" style="color: {color};">{category}</div>
                <div class="bmi-range-bar"></div>
                <div class="range-labels">
                    <span>Underweight<br/>&lt;18.5</span>
                    <span>Normal<br/>18.5–24.9</span>
                    <span>Overweight<br/>25–29.9</span>
                    <span>Obese<br/>≥30</span>
                </div>
                <div class="tip-box">{tip}</div>
            </div>
        """, unsafe_allow_html=True)
# --- workout plan button -- #

        st.markdown("")
if st.button("💪 Get Free Workout Plan", use_container_width=True):
    category= st.session_state.get("category", None)
    if category == None:
        st.warning("Calculate your BMI first")
    elif category == "Underweight":
        st.session_state.category = category
        st.markdown(" Suggested Workout Plans")
        st.markdown("""
        - **Goal:** Build muscle and increase body weight
        - **3x per week:** Full body strength training
        - **Focus:** Compound lifts — squats, deadlifts, bench press
        - **Cardio:** Keep it light, 1-2x per week max
        - **Tip:** Prioritize eating in a caloric surplus
        """)
    elif category == "Normal Weight":
        st.session_state.category = category
        st.markdown(" Suggested Workout Plans")
        st.markdown("""
        - **Goal:** Maintain and tone
        - **4x per week:** Mix of strength and cardio
        - **Focus:** Upper/lower body split
        - **Cardio:** 2-3x per week, moderate intensity
        - **Tip:** Focus on consistency over intensity
        """)
    elif category == "Overweight":
        st.session_state.category = category
        st.markdown(" Suggested Workout Plans")
        st.markdown("""
        - **Goal:** Fat loss while preserving muscle
        - **4-5x per week:** Strength + cardio combo
        - **Focus:** Circuit training, full body workouts
        - **Cardio:** 3-4x per week, mix of HIIT and steady state
        - **Tip:** Pair with a moderate caloric deficit
        """)
    else:  # Obese
        st.markdown(" Suggested Workout Plans")
        st.markdown("""
        - **Goal:** Sustainable weight loss
        - **3x per week:** Low impact strength training
        - **Focus:** Bodyweight exercises, machines over free weights
        - **Cardio:** Daily walks, swimming, or cycling
        - **Tip:** Start slow and build the habit — consistency beats intensity
        """)

        # --- Healthy weight range ---
        healthy_low = round(18.5 * (height_m ** 2), 1)
        healthy_high = round(24.9 * (height_m ** 2), 1)

        if unit == "Imperial (lbs / ft & in)":
            healthy_low = round(healthy_low / 0.453592, 1)
            healthy_high = round(healthy_high / 0.453592, 1)
            weight_unit = "lbs"
        else:
            weight_unit = "kg"

        st.info(f"**Healthy weight range for your height:** {healthy_low} – {healthy_high} {weight_unit}")

# --- Disclaimer ---
st.markdown("")
st.caption("⚠️ BMI is a screening tool, not a medical diagnosis. It does not account for muscle mass, bone density, or age.")

