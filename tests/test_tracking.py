import unittest
from datetime import datetime
from unittest.mock import patch

from services.tracking import frame, validate


class TrackingTests(unittest.TestCase):
    def test_bmi_conversion_and_formula(self):
        records = validate('bmi_log', [dict(recorded_at=datetime.now().isoformat(), height_cm=67 * 2.54, weight_kg=154 * 0.45359237)])
        with patch('services.tracking.st.session_state', {'bmi_log': records}):
            self.assertAlmostEqual(frame('bmi_log').iloc[0].bmi, 24.1194, places=3)

    def test_invalid_records(self):
        for height, weight in [(1.75, 70), (175, -3), (175, float('nan')), (175, float('inf'))]:
            with self.assertRaises(ValueError):
                validate('bmi_log', [dict(recorded_at=datetime.now().isoformat(), height_cm=height, weight_kg=weight)])
        with self.assertRaises(ValueError):
            validate('food_log', [dict(date='2026-02-30', food='Meal', protein_g=30, carbs_g=40, fat_g=10)])

    def test_derived_calories_and_volume(self):
        food = validate('food_log', [dict(date='2026-09-12', food='Meal', protein_g=30, carbs_g=40, fat_g=10)])
        workout = validate('workout_log', [dict(date='2026-09-12', exercise='  Bench   press ', sets=3, reps=8, weight_kg=135 * 0.45359237, rpe=8, notes='')])
        with patch('services.tracking.st.session_state', {'food_log': food, 'workout_log': workout}):
            self.assertEqual(frame('food_log').iloc[0].calories, 370)
            self.assertAlmostEqual(frame('workout_log').iloc[0].volume_kg / 0.45359237, 3240)
            self.assertEqual(workout[0]['exercise'], 'Bench press')

    def test_roundtrip(self):
        import io
        import pandas as pd
        records = validate('food_log', [dict(date='2026-09-12', food='Rice, cooked', protein_g=2.7, carbs_g=28.2, fat_g=0.3)])
        restored = pd.read_csv(io.StringIO(pd.DataFrame(records).to_csv(index=False)), keep_default_na=False)
        self.assertEqual(validate('food_log', restored.to_dict('records')), records)


if __name__ == '__main__':
    unittest.main()
