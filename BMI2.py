import streamlit as st
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# --- Initialize session state defaults ---
if "bmi" not in st.session_state:
    st.session_state.bmi = None
if "color" not in st.session_state:
    st.session_state.color = "#34d399"
if "category" not in st.session_state:
    st.session_state.category = None
if "tip" not in st.session_state:
    st.session_state.tip = ""
if "healthy_low" not in st.session_state:
    st.session_state.healthy_low = None
if "healthy_high" not in st.session_state:
    st.session_state.healthy_high = None
if "weight_unit" not in st.session_state:
    st.session_state.weight_unit = "kg"
if "first_name" not in st.session_state:
    st.session_state.first_name = ""
if "show_workouts" not in st.session_state:
    st.session_state.show_workouts = False
if "show_email_form" not in st.session_state:
    st.session_state.show_email_form = False
if "workout_links" not in st.session_state:
    st.session_state.workout_links = []

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
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .main { background-color: #f8f9fb; }
        .bmi-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.07);
            margin-bottom: 1.5rem;
        }
        .bmi-result { font-size: 4rem; font-weight: 700; text-align: center; line-height: 1; }
        .bmi-label {
            text-align: center; font-size: 1.1rem; font-weight: 600;
            margin-top: 0.4rem; letter-spacing: 0.04em; text-transform: uppercase;
        }
        .bmi-range-bar {
            height: 10px; border-radius: 999px;
            background: linear-gradient(to right, #60a5fa, #34d399, #fbbf24, #f87171);
            margin: 1.5rem 0 0.4rem;
        }
        .range-labels { display: flex; justify-content: space-between; font-size: 0.72rem; color: #9ca3af; font-weight: 500; }
        .tip-box {
            background: #f0f9ff; border-left: 4px solid #38bdf8; border-radius: 8px;
            padding: 0.9rem 1.1rem; font-size: 0.9rem; color: #0369a1; margin-top: 1rem;
        }
        h1 { font-weight: 700 !important; letter-spacing: -0.02em !important; }
        .stSlider > div { padding-top: 0.2rem; }
    </style>
""", unsafe_allow_html=True)


# --- Email Sending Function ---
def send_bmi_email(recipient_email, first_name, bmi, category, color, tip, healthy_low, healthy_high, weight_unit, workout_links):
    sender_email = st.secrets["EMAIL_ADDRESS"]
    sender_password = st.secrets["EMAIL_PASSWORD"]

    workout_html = ""
    for label, url in workout_links:
        workout_html += f'<li><a href="{url}" style="color:#0369a1;">{label}</a></li>'

    badge_colors = {
        "Underweight": "#60a5fa",
        "Normal Weight": "#34d399",
        "Overweight": "#fbbf24",
        "Obese": "#f87171",
    }
    badge_color = badge_colors.get(category, "#888")

    html_body = f"""
    <html>
    <body style="font-family: Inter, sans-serif; background: #f8f9fb; padding: 2rem;">
        <div style="max-width: 520px; margin: 0 auto; background: white; border-radius: 16px;
                    padding: 2rem; box-shadow: 0 2px 12px rgba(0,0,0,0.07);">
            <h2 style="text-align:center; color:#1f2937;">⚖️ Your BMI Results</h2>
            <p style="text-align:center; color:#6b7280;">Hi {first_name}, here's your BMI summary.</p>
            <div style="text-align:center; margin: 1.5rem 0;">
                <div style="font-size: 4rem; font-weight: 700; color: {badge_color};">{bmi}</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: {badge_color};
                            text-transform: uppercase; letter-spacing: 0.04em;">{category}</div>
            </div>
            <div style="height: 10px; border-radius: 999px;
                        background: linear-gradient(to right, #60a5fa, #34d399, #fbbf24, #f87171);
                        margin: 1rem 0 0.4rem;"></div>
            <div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#9ca3af;">
                <span>Underweight &lt;18.5</span>
                <span>Normal 18.5–24.9</span>
                <span>Overweight 25–29.9</span>
                <span>Obese ≥30</span>
            </div>
            <div style="background:#f0f9ff; border-left: 4px solid #38bdf8; border-radius: 8px;
                        padding: 0.9rem 1.1rem; font-size: 0.9rem; color: #0369a1; margin-top: 1rem;">
                {tip}
            </div>
            <div style="background:#f9fafb; border-radius:8px; padding:1rem; margin-top:1.2rem;">
                <strong style="color:#1f2937;">Healthy weight range for your height:</strong>
                <span style="color:#374151;"> {healthy_low} – {healthy_high} {weight_unit}</span>
            </div>
            <div style="margin-top: 1.5rem;">
                <strong style="color:#1f2937;">💪 Suggested Workout Plans:</strong>
                <ul style="margin-top: 0.5rem; padding-left: 1.2rem; color:#374151;">
                    {workout_html}
                </ul>
            </div>
            <p style="font-size:0.75rem; color:#9ca3af; margin-top:2rem; text-align:center;">
                ⚠️ BMI is a screening tool, not a medical diagnosis. It does not account for muscle mass, bone density, or age.
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your BMI Results — {category}"
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())


# --- Header ---
st.markdown("## ⚖️ BMI Calculator")
st.markdown("-Enter your details below to calculate your Body Mass Index")
st.markdown("-Get free workout plans at the end")
st.divider()

# --- User Info ---
col1, col2, col3 = st.columns(3)
with col1:
    first_name = st.text_input("First Name")
with col2:
    last_name = st.text_input("Last Name")
with col3:
    date = st.date_input("Date of Birth", max_value=datetime.date.today(), min_value=datetime.date(1900, 1, 1))

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

# --- Calculate Button ---
# Only saves to session state, never resets show_workouts unless new BMI is calculated
if st.button("Calculate BMI", use_container_width=True, type="primary"):
    if height_m <= 0:
        st.error("Height must be greater than zero.")
    else:
        bmi = weight_for_calc / (height_m ** 2)
        bmi_rounded = round(bmi, 1)

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

        healthy_low = round(18.5 * (height_m ** 2), 1)
        healthy_high = round(24.9 * (height_m ** 2), 1)

        if unit == "Imperial (lbs / ft & in)":
            healthy_low = round(healthy_low / 0.453592, 1)
            healthy_high = round(healthy_high / 0.453592, 1)
            weight_unit = "lbs"
        else:
            weight_unit = "kg"

        st.session_state.bmi = bmi_rounded
        st.session_state.category = category
        st.session_state.color = color
        st.session_state.tip = tip
        st.session_state.healthy_low = healthy_low
        st.session_state.healthy_high = healthy_high
        st.session_state.weight_unit = weight_unit
        st.session_state.first_name = first_name
        st.session_state.show_workouts = False   # reset only on new calculation
        st.session_state.show_email_form = False


# --- Result Card ---
# Uses is not None so it won't show the card before a BMI is calculated
if st.session_state.bmi is not None:
    st.markdown(f"""
        <div class="bmi-card">
            <div class="bmi-result" style="color: {st.session_state.color};">{st.session_state.bmi}</div>
            <div class="bmi-label" style="color: {st.session_state.color};">{st.session_state.category}</div>
            <div class="bmi-range-bar"></div>
            <div class="range-labels">
                <span>Underweight<br/>&lt;18.5</span>
                <span>Normal<br/>18.5–24.9</span>
                <span>Overweight<br/>25–29.9</span>
                <span>Obese<br/>≥30</span>
            </div>
            <div class="tip-box">{st.session_state.tip}</div>
        </div>
    """, unsafe_allow_html=True)

    st.info(f"**Healthy weight range for your height:** {st.session_state.healthy_low} – {st.session_state.healthy_high} {st.session_state.weight_unit}")
    st.markdown("")

    # --- Workout Plan Button ---
    if st.button("💪 Get Free Workout Plan", use_container_width=True):
        st.session_state.show_workouts = True

    # --- Workout Suggestions ---
    if st.session_state.show_workouts:
        category = st.session_state.category
        st.markdown("### Suggested Workout Plans")

        if category == "Underweight":
            workout_links = [
                ("📋 3 Day Full Body Routine", "/FullBody"),
                ("📋 Upper & Lower", "/UpperLower"),
                ("📋 Push Pull Legs", "/PPL"),
            ]
        elif category == "Normal Weight":
            workout_links = [
                ("💪 Lift + Cardio Hybrid", "/Hybrid"),
                ("📋 3 Day Full Body Routine", "/FullBody"),
                ("📋 Upper & Lower", "/UpperLower"),
                ("📋 Push Pull Legs", "/PPL"),
            ]
        elif category == "Overweight":
            workout_links = [
                ("💪 Lift + Cardio Hybrid", "/Hybrid"),
                ("📋 Push Pull Legs", "/PPL"),
            ]
        else:
            workout_links = [
                ("🏃 Cardio + Strength", "/Cardio"),
                ("💪 Lift + Cardio Hybrid", "/Hybrid"),
            ]

        st.session_state.workout_links = workout_links

        for label, url in workout_links:
            st.markdown(f"- [{label}]({url})")

        st.markdown("")

        # --- Email Button ---
        if st.button("📧 Email Me This Plan", use_container_width=True):
            st.session_state.show_email_form = True

    # --- Email Form ---
    if st.session_state.show_email_form:
        st.markdown("### 📧 Send to Your Email")
        recipient = st.text_input("Enter your email address", placeholder="you@example.com")

        if st.button("Send Email", use_container_width=True, type="primary"):
            if not recipient or "@" not in recipient:
                st.error("Please enter a valid email address.")
            else:
                try:
                    send_bmi_email(
                        recipient_email=recipient,
                        first_name=st.session_state.get("first_name", "there"),
                        bmi=st.session_state.bmi,
                        category=st.session_state.category,
                        color=st.session_state.color,
                        tip=st.session_state.tip,
                        healthy_low=st.session_state.healthy_low,
                        healthy_high=st.session_state.healthy_high,
                        weight_unit=st.session_state.weight_unit,
                        workout_links=st.session_state.get("workout_links", []),
                    )
                    st.success(f"✅ Email sent to {recipient}!")
                except Exception as e:
                    st.error(f"Something went wrong: {e}")

# --- Disclaimer ---
st.markdown("")
st.caption("⚠️ BMI is a screening tool, not a medical diagnosis. It does not account for muscle mass, bone density, or age.")