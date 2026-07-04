import streamlit as st

st.set_page_config(page_title="Low Volume Strength", page_icon="💪", layout="centered")

st.page_link("BMI2.py", label= "← Back to BMI Calculator")

# --- Header ---
st.markdown("## 💪 Low Volume Strength")
st.markdown("**Category:** Low Volume")
st.markdown("**Goal:** Get stronger with minimal weekly sets")

st.divider()

# --- Overview Stats ---
col1, col2, col3 = st.columns(3)
col1.metric("Days / Week", "3")
col2.metric("Session Length", "45 min")
col3.metric("Split", "Full Body")

st.divider()

# --- Weekly Overview ---
st.markdown("### 📅 Weekly Overview")
st.info("A low-volume plan for busy schedules, focusing on a few high-value lifts per session.")

st.markdown("")

# --- Schedule ---
schedule = [
    {
        "day": "Day 1",
        "title": "Full Body A",
        "duration": 45,
        "exercises": [
            {"name": "Barbell Squat",  "sets": 3, "reps": "5",     "muscle": "Quads", "equipment": "Barbell",       "rest": 150},
            {"name": "Bench Press",    "sets": 3, "reps": "5",     "muscle": "Chest", "equipment": "Barbell",       "rest": 150},
            {"name": "Lat Pulldown",   "sets": 2, "reps": "8-10",  "muscle": "Back",  "equipment": "Cable Machine", "rest": 90},
        ],
    },
    {
        "day": "Day 2",
        "title": "Full Body B",
        "duration": 45,
        "exercises": [
            {"name": "Romanian Deadlift", "sets": 3, "reps": "6",          "muscle": "Hamstrings", "equipment": "Barbell",               "rest": 150},
            {"name": "Shoulder Press",    "sets": 3, "reps": "6",          "muscle": "Shoulders",  "equipment": "Dumbbells or Barbell",  "rest": 120},
            {"name": "Walking Lunge",     "sets": 2, "reps": "10 each leg","muscle": "Glutes",     "equipment": "Dumbbells",             "rest": 75},
        ],
    },
    {
        "day": "Day 3",
        "title": "Full Body C",
        "duration": 45,
        "exercises": [
            {"name": "Front Squat",           "sets": 3, "reps": "5",          "muscle": "Quads",    "equipment": "Barbell",                  "rest": 150},
            {"name": "Chest-Supported Row",   "sets": 3, "reps": "8",          "muscle": "Back",     "equipment": "Dumbbells or Machine",     "rest": 90},
            {"name": "Pallof Press",          "sets": 2, "reps": "10 each side","muscle": "Obliques","equipment": "Cable Machine or Band",    "rest": 45},
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