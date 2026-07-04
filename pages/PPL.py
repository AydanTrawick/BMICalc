import streamlit as st

st.set_page_config(page_title="Push-Pull-Legs", page_icon="💪", layout="centered")

st.page_link("BMI2.py", label= "← Back to BMI Calculator")

#-- Header -- 
st.markdown("### Push-Pull-Legs")
st.markdown("**Category:** Mass/Strength Building")
st.markdown("**Goal:** Build strength and muscle mass")

st.divider()

#-- Overview -- 
col1,col2,col3= st.columns(3)
col1.metric("Days / Week", "6")
col2.metric("Session Length", "60-90 min")
col3.metric("Split", "Push/Pull/Legs")

st.divider()

#-- Weekly Overview --

st.markdown("### 📅 Weekly Overview")
st.info("This is a 6 day strength and mass building workout routine that requires a lot of energy & effort.")

st.markdown("")

#-- Schedule -- 

schedule = [

{
    "day": "Day 1",
    "title": "Push",
    "duration": 90,
    "exercises": [

        {"name": "Tricep Pushdown", "sets": 3, "reps":"6-10", "muscle": "Tricep", "equipment": "Cable Tower", "rest": 60},
        {"name": "Dips", "sets": 2, "reps":"10-20", "muscle": "Lower Chest", "equipment": "Dip bar", "rest": 60},
        {"name": "Incline Smith Press", "sets": 3, "reps":"6-10", "muscle": "Upper Chest", "equipment": "Smith Machine", "rest": 60},
        {"name": "Shoulder Press", "sets": 3, "reps":"6-10", "muscle": "Shoulders", "equipment": "Smith Machine/ Bar", "rest": 60},
        {"name": "Pec Flys", "sets": 3, "reps":"6-10", "muscle": "Chest", "equipment": "Pec Deck", "rest": 60},

    ],

},


{
    "day": "Day 2",
    "title": "Pull",
    "duration": 90,
    "exercises": [

        {"name": "Pullovers", "sets": 3, "reps":"6-10", "muscle": "Back", "equipment": "Cable Tower", "rest": 60},
        {"name": "Pullups", "sets": 2, "reps":"6-15", "muscle": "Back", "equipment": "Pull-up bar", "rest": 60},
        {"name": "Archer Rows", "sets": 3, "reps":"6-10", "muscle": "Shoulders", "equipment": "Smith Machine", "rest": 60},
        {"name": "Hammer Curls", "sets": 3, "reps":"6-10", "muscle": "Arms", "equipment": "DB's", "rest": 60},
        {"name": "Bicep Curls", "sets": 3, "reps":"6-10", "muscle": "Arms", "equipment": "DB's", "rest": 60},
        {"name": "T-bar Row", "sets": 3, "reps":"6-10", "muscle": "Back", "equipment": "T-bar/ Smith Machine", "rest": 60},

    ],

},

{
    "day": "Day 3",
    "title": "Legs (Hamstring Focus)",
    "duration": 60,
    "exercises": [

        {"name": "Adductor Machine", "sets": 3, "reps":"6-10", "muscle": "Adductors", "equipment": "Adductor Machine", "rest": 60},
        {"name": "RDL's", "sets": 3, "reps":"6-10", "muscle": "Hamstrings", "equipment": "Smith Machine/Bar/DB's", "rest": 60},
        {"name": "Leg Extensions", "sets": 3, "reps":"6-10", "muscle": "Quads", "equipment": "Leg Extension", "rest": 60},
        {"name": "Leg curls", "sets": 3, "reps":"6-10", "muscle": "Arms", "equipment": "DB's", "rest": 60},
        {"name": "Hip Thrust", "sets": 3, "reps":"6-10", "muscle": "Glutes", "equipment": "Hip Thurst Machine/ Smith Machine", "rest": 60},
        {"name": "Calf Raises", "sets": 3, "reps":"15-20", "muscle": "Calfs", "equipment": "DB's", "rest": 60},

    ],

},

{
    "day": "Day 4",
    "title": "Push",
    "duration": 90,
    "exercises": [

        {"name": "Tricep Pushdown", "sets": 3, "reps":"6-10", "muscle": "Tricep", "equipment": "Cable Tower", "rest": 60},
        {"name": "Dips", "sets": 2, "reps":"10-20", "muscle": "Lower Chest", "equipment": "Dip bar", "rest": 60},
        {"name": "Low-to-High Cable fly", "sets": 3, "reps":"6-10", "muscle": "Upper Chest", "equipment": "Cables", "rest": 60},
        {"name": "Lateral Raises", "sets": 3, "reps":"6-10", "muscle": "Shoulders", "equipment": "DB's", "rest": 60},
        {"name": "Overhead Tricep Extensions", "sets": 3, "reps":"6-10", "muscle": "Tricep", "equipment": "Calbles/DB's", "rest": 60},

    ],

},

{
    "day": "Day 5",
    "title": "Pull",
    "duration": 90,
    "exercises": [

        {"name": "Pullovers", "sets": 3, "reps":"6-10", "muscle": "Back", "equipment": "Cable Tower", "rest": 60},
        {"name": "Pullups", "sets": 2, "reps":"10-20", "muscle": "Back", "equipment": "Pull-up bar", "rest": 60},
        {"name": "Archer Rows", "sets": 3, "reps":"6-10", "muscle": "Shoulders", "equipment": "Smith Machine", "rest": 60},
        {"name": "Hammer Curls", "sets": 3, "reps":"6-10", "muscle": "Arms", "equipment": "DB's", "rest": 60},
        {"name": "Bicep Curls", "sets": 3, "reps":"6-10", "muscle": "Arms", "equipment": "DB's", "rest": 60},
        {"name": "T-bar Row", "sets": 3, "reps":"6-10", "muscle": "Back", "equipment": "T-bar/ Smith Machine", "rest": 60},

    ],

},

{
    "day": "Day 6",
    "title": "Legs(Quad Focus)",
    "duration": 90,
    "exercises": [

        {"name": "Adductor Machine", "sets": 3, "reps":"6-10", "muscle": "Adductors", "equipment": "Adductor Machine", "rest": 60},
        {"name": "Squats", "sets": 3, "reps":"6-10", "muscle": "Quads", "equipment": "Smith Machine/Bar/DB's", "rest": 60},
        {"name": "Leg Extensions", "sets": 3, "reps":"6-10", "muscle": "Quads", "equipment": "Leg Extension", "rest": 60},
        {"name": "Leg curls", "sets": 3, "reps":"6-10", "muscle": "Arms", "equipment": "Leg Curl Machine", "rest": 60},
        {"name": "Calf Raises", "sets": 3, "reps":"15-20", "muscle": "Calfs", "equipment": "DB's", "rest": 60},

    ],

},

]

#-- render each day

for day in schedule:
    with st.expander(f"📌 {day['day']} - {day['title']}({day['duration']} min)"):

        col1,col2,col3,col4,col5 = st.columns([3,1,1,2,2])

        col1.markdown("**Exercise**")
        col2.markdown("**Sets**")
        col3.markdown("**Reps**")
        col4.markdown("**Muscle**")
        col5.markdown("**Equipment**")


        st.markdown("---")

        for ex in day ["exercises"]:
            col1,col2,col3,col4,col5 = st.columns([3,1,1,2,2])

            col1.write(ex["name"])
            col2.write(ex["sets"])
            col3.write(ex["reps"])
            col4.write(ex["muscle"])
            col5.write(ex["equipment"])


            if ex["rest"] > 0:
                st.caption(f"⏱ Rest: {ex['rest']} sec")

st.divider()
st.caption("⚠️ Always warm up before training")