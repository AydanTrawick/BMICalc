import streamlit as st

st.set_page_config(page_title="Cardio + Strength", page_icon="🏃", layout="centered")

st.page_link("Toolkit.py", label="← Back to Home")

# --- Header ---
st.markdown("## 🏃 Cardio + Strength")
st.markdown("**Category:** Cardio Focused")
st.markdown("**Goal:** Maximize endurance and burn with minimal lifting")

st.divider()

# --- Overview Stats ---
col1, col2, col3 = st.columns(3)
col1.metric("Days / Week", "4")
col2.metric("Session Length", "50-60 min")
col3.metric("Split", "Cardio / Strength")

st.divider()

# --- Weekly Overview ---
st.markdown("### 📅 Weekly Overview")
st.info("Four days of high-output cardio paired with short, low-volume strength work. Each session leads with cardio and finishes with 1–2 compound lifts to preserve muscle.")

st.markdown("")

# --- Schedule ---
schedule = [
    {
        "day": "Day 1",
        "title": "HIIT + Upper",
        "duration": 55,
        "exercises": [
            {"name": "Treadmill Intervals (1 min sprint / 1 min walk)", "sets": 10, "reps": "1 min on / 1 min off", "muscle": "Conditioning", "equipment": "Treadmill", "rest": 0},
            {"name": "Jump Rope", "sets": 3, "reps": "2 min", "muscle": "Conditioning", "equipment": "Jump Rope", "rest": 30},
            {"name": "Bench Press", "sets": 3, "reps": "6-8", "muscle": "Chest", "equipment": "Barbell", "rest": 90},
            {"name": "Lat Pulldown", "sets": 3, "reps": "8-10", "muscle": "Back", "equipment": "Cable Machine", "rest": 75},
        ],
    },
    {
        "day": "Day 2",
        "title": "Steady State + Lower",
        "duration": 60,
        "exercises": [
            {"name": "Incline Treadmill Walk", "sets": 1, "reps": "25-30 min", "muscle": "Conditioning", "equipment": "Treadmill", "rest": 0},
            {"name": "Stationary Bike", "sets": 1, "reps": "10 min moderate pace", "muscle": "Conditioning", "equipment": "Bike", "rest": 0},
            {"name": "Leg Press", "sets": 3, "reps": "8-10", "muscle": "Quads", "equipment": "Machine", "rest": 90},
            {"name": "Leg Curl", "sets": 3, "reps": "10", "muscle": "Hamstrings", "equipment": "Machine", "rest": 75},
            {"name": "Calf Raise", "sets": 2, "reps": "15-20", "muscle": "Calves", "equipment": "Machine", "rest": 45},
        ],
    },
    {
        "day": "Day 3",
        "title": "Circuit + Core",
        "duration": 50,
        "exercises": [
            {"name": "Rowing Machine", "sets": 4, "reps": "500m", "muscle": "Conditioning", "equipment": "Rowing Machine", "rest": 60},
            {"name": "Box Jumps", "sets": 4, "reps": "10", "muscle": "Conditioning", "equipment": "Plyo Box", "rest": 45},
            {"name": "Hollow Body Hold", "sets": 3, "reps": "30-45 sec", "muscle": "Abs", "equipment": "Bodyweight", "rest": 30},
            {"name": "Pallof Press", "sets": 3, "reps": "10 each side", "muscle": "Obliques", "equipment": "Cable Machine or Band", "rest": 45},
        ],
    },
    {
        "day": "Day 4",
        "title": "Assault Bike + Full Body",
        "duration": 55,
        "exercises": [
            {"name": "Assault Bike Intervals (20 sec sprint / 40 sec rest)", "sets": 12, "reps": "20 sec on / 40 sec off", "muscle": "Conditioning", "equipment": "Air Bike", "rest": 0},
            {"name": "Barbell Squat", "sets": 3, "reps": "5-6", "muscle": "Quads", "equipment": "Barbell", "rest": 120},
            {"name": "Dumbbell Row", "sets": 3, "reps": "8-10 each side", "muscle": "Back", "equipment": "Dumbbells", "rest": 75},
            {"name": "Farmer Carry", "sets": 3, "reps": "40 meters", "muscle": "Full Body", "equipment": "Dumbbells or Kettlebells", "rest": 60},
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
