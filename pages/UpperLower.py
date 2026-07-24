import streamlit as st

st.set_page_config(page_title="Low Volume Hypertrophy", page_icon="💪", layout="centered")

st.page_link("Toolkit.py", label="← Back to Home")

# --- Header ---
st.markdown("## 💪 Low Volume Hypertrophy")
st.markdown("**Category:** Low Volume")
st.markdown("**Goal:** Build muscle with concise sessions")

st.divider()

# --- Overview Stats ---
col1, col2, col3 = st.columns(3)
col1.metric("Days / Week", "4")
col2.metric("Session Length", "40 min")
col3.metric("Split", "Upper / Lower")

st.divider()

# --- Weekly Overview ---
st.markdown("### 📅 Weekly Overview")
st.info("Short upper/lower sessions with fewer exercises and strong execution.")

st.markdown("")

# --- Schedule ---
schedule = [
    {
        "day": "Day 1",
        "title": "Upper A",
        "duration": 40,
        "exercises": [
            {"name": "Incline Dumbbell Press", "sets": 3, "reps": "8-10",  "muscle": "Chest",     "equipment": "Dumbbells",     "rest": 90},
            {"name": "Seated Row",             "sets": 3, "reps": "8-10",  "muscle": "Back",      "equipment": "Cable Machine", "rest": 90},
            {"name": "Lateral Raise",          "sets": 2, "reps": "12-15", "muscle": "Shoulders", "equipment": "Dumbbells",     "rest": 60},
        ],
    },
    {
        "day": "Day 2",
        "title": "Lower A",
        "duration": 40,
        "exercises": [
            {"name": "Leg Press",  "sets": 3, "reps": "10",    "muscle": "Quads",      "equipment": "Machine", "rest": 90},
            {"name": "Leg Curl",   "sets": 3, "reps": "10",    "muscle": "Hamstrings", "equipment": "Machine", "rest": 75},
            {"name": "Calf Raise", "sets": 2, "reps": "15-20", "muscle": "Calves",     "equipment": "Machine", "rest": 45},
        ],
    },
    {
        "day": "Day 3",
        "title": "Upper B",
        "duration": 40,
        "exercises": [
            {"name": "Machine Chest Press", "sets": 3, "reps": "8-10",  "muscle": "Chest",   "equipment": "Machine",       "rest": 90},
            {"name": "Lat Pulldown",        "sets": 3, "reps": "8-10",  "muscle": "Back",    "equipment": "Cable Machine", "rest": 90},
            {"name": "Cable Curl",          "sets": 2, "reps": "10-12", "muscle": "Biceps",  "equipment": "Cable Machine", "rest": 60},
        ],
    },
    {
        "day": "Day 4",
        "title": "Lower B",
        "duration": 40,
        "exercises": [
            {"name": "Hack Squat",        "sets": 3, "reps": "8-10",  "muscle": "Quads",      "equipment": "Machine",              "rest": 90},
            {"name": "Hip Thrust",        "sets": 3, "reps": "8-10",  "muscle": "Glutes",     "equipment": "Barbell or Machine",   "rest": 90},
            {"name": "Adductor Machine",  "sets": 2, "reps": "12-15", "muscle": "Adductors",  "equipment": "Machine",              "rest": 45},
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
