import streamlit as st

st.set_page_config(page_title="Lift + Cardio Hybrid", page_icon="💪", layout="centered")

st.page_link("BMI2.py", label="← Back to Home")
# --- Header ---
st.markdown("## 💪 Lift + Cardio Hybrid")
st.markdown("**Category:** Hybrid Athlete")
st.markdown("**Goal:** Maintain muscle while improving endurance")

st.divider()

# --- Overview Stats ---
col1, col2, col3 = st.columns(3)
col1.metric("Days / Week", "5")
col2.metric("Session Length", "55 min")
col3.metric("Split", "Hybrid")

st.divider()

# --- Weekly Overview ---
st.markdown("### 📅 Weekly Overview")
st.info("A five-day week alternating lifting, incline walking and interval-style conditioning.")

st.markdown("")

# --- Schedule ---
schedule = [
    {
        "day": "Day 1",
        "title": "Upper Strength",
        "duration": 55,
        "exercises": [
            {"name": "Bench Press",   "sets": 4, "reps": "5",       "muscle": "Chest",       "equipment": "Barbell",              "rest": 150},
            {"name": "Lat Pulldown",  "sets": 4, "reps": "8",       "muscle": "Back",        "equipment": "Cable Machine",        "rest": 90},
            {"name": "Face Pull",     "sets": 3, "reps": "12-15",   "muscle": "Shoulders",   "equipment": "Cable Machine",        "rest": 60},
        ],
    },
    {
        "day": "Day 2",
        "title": "Incline Conditioning",
        "duration": 45,
        "exercises": [
            {"name": "Incline Treadmill Walk", "sets": 1, "reps": "30-40 min",    "muscle": "Conditioning", "equipment": "Treadmill",                   "rest": 0},
            {"name": "Pallof Press",           "sets": 3, "reps": "10 each side", "muscle": "Obliques",     "equipment": "Cable Machine or Band",        "rest": 45},
        ],
    },
    {
        "day": "Day 3",
        "title": "Lower Strength",
        "duration": 55,
        "exercises": [
            {"name": "Barbell Squat", "sets": 4, "reps": "5",      "muscle": "Quads",      "equipment": "Barbell",  "rest": 150},
            {"name": "Leg Curl",      "sets": 3, "reps": "10",     "muscle": "Hamstrings", "equipment": "Machine",  "rest": 75},
            {"name": "Calf Raise",    "sets": 4, "reps": "12-20",  "muscle": "Calves",     "equipment": "Machine",  "rest": 60},
        ],
    },
    {
        "day": "Day 4",
        "title": "Bike Intervals",
        "duration": 40,
        "exercises": [
            {"name": "Assault Bike",      "sets": 10, "reps": "20 sec sprint", "muscle": "Conditioning", "equipment": "Air Bike",    "rest": 60},
            {"name": "Hollow Body Hold",  "sets": 3,  "reps": "30 sec",        "muscle": "Abs",          "equipment": "Bodyweight",  "rest": 45},
        ],
    },
    {
        "day": "Day 5",
        "title": "Full Body Pump",
        "duration": 55,
        "exercises": [
            {"name": "Dumbbell Floor Press",   "sets": 3, "reps": "10-12",       "muscle": "Chest",  "equipment": "Dumbbells",            "rest": 75},
            {"name": "Chest-Supported Row",    "sets": 3, "reps": "10-12",       "muscle": "Back",   "equipment": "Dumbbells or Machine", "rest": 75},
            {"name": "Walking Lunge",          "sets": 3, "reps": "12 each leg", "muscle": "Glutes", "equipment": "Dumbbells",            "rest": 75},
        ],
    },
]

# --- Render Each Day ---
for day in schedule:
    with st.expander(f"📌 {day['day']} — {day['title']}  ({day['duration']} min)"):

        # Table header
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 2])
        col1.markdown("**Exercise**")
        col2.markdown("**Sets**")
        col3.markdown("**Reps**")
        col4.markdown("**Muscle**")
        col5.markdown("**Equipment**")

        st.markdown("---")

        # Table rows
        for ex in day["exercises"]:
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 2])
            col1.write(ex["name"])
            col2.write(ex["sets"])
            col3.write(ex["reps"])
            col4.write(ex["muscle"])
            col5.write(ex["equipment"])

            if ex["rest"] > 0:
                st.caption(f"⏱ Rest: {ex['rest']} sec")

st.divider()
st.caption("⚠️ Always warm up before training")
