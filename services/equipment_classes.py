"""Equipment class names shown in the Streamlit feedback UI.

Must be kept in sync with CLASS_NAMES in equipment_api/equipment_api.py --
that FastAPI service runs separately and owns the trained model, so this
list can't be imported directly from it.
"""

CLASS_NAMES = [
    "Adductor Machine",
    "Bench Press",
    "Calf raise",
    "Captains chair",
    "Chest Press",
    "Dumbbells",
    "Hip thrust",
    "Lat Pulldown",
    "Leg Curl",
    "Leg Extension",
    "Leg Press",
    "Pec Deck",
    "Smith Machine",
    "Squat",
    "Treadmill",
    "bike",
    "elliptical",
    "lateral raise",
    "pull up bar",
    "rowing machine",
    "seated cable row",
    "shoulder press",
    "stair master",
    "t-bar row",
]
