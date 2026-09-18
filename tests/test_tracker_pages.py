import unittest
from streamlit.testing.v1 import AppTest


def button(app, label):
    return next(item for item in app.button if item.label == label)


def number(app, label):
    return next(item for item in app.number_input if item.label == label)


class PageTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file('BMI2.py').run(timeout=30)
        self.assertFalse(self.app.exception)

    def test_home_log_widgets(self):
        labels = [metric.label for metric in self.app.metric]
        self.assertIn('Calories today', labels)
        self.assertIn('Foods logged', labels)
        self.assertIn('Sets today', labels)
        self.assertIn('Exercises', labels)

    def test_bmi_history_and_validation(self):
        app = self.app.switch_page('pages/BMI_Calculator.py').run()
        button(app, 'Calculate BMI').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '24.1')
        app.radio[0].set_value('Metric (kg / cm)').run()
        number(app, 'Height (cm)').set_value(1.75)
        button(app, 'Calculate BMI').click().run()
        self.assertEqual(len(app.session_state['bmi_log']), 1)
        self.assertTrue(app.error)
        number(app, 'Height (cm)').set_value(175.0)
        button(app, 'Calculate BMI').click().run()
        self.assertEqual(len(app.session_state['bmi_log']), 2)
        self.assertFalse(app.exception)
        app.switch_page('pages/Food_Log.py').run()
        app.switch_page('pages/BMI_Calculator.py').run()
        self.assertEqual(len(app.session_state['bmi_log']), 2)

    def test_restore_replaces_atomically_and_handles_empty_history(self):
        import io
        from unittest.mock import patch

        app = self.app.switch_page('pages/BMI_Calculator.py').run()
        button(app, 'Calculate BMI').click().run()
        original = list(app.session_state['bmi_log'])

        def uploaded(text):
            result = io.BytesIO(text.encode())
            result.size = len(result.getvalue())
            return result

        with patch('streamlit.file_uploader', return_value=uploaded('recorded_at,height_cm,weight_kg\n2026-09-12T12:00:00,1.75,70\n')):
            button(app, 'Restore log').click().run()
        self.assertTrue(app.error)
        self.assertEqual(app.session_state['bmi_log'], original)
        with patch('streamlit.file_uploader', return_value=uploaded('recorded_at,height_cm,weight_kg\n2026-09-12T12:00:00,200,100\n')):
            button(app, 'Restore log').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '25.0')
        self.assertEqual(len(app.session_state['bmi_log']), 1)
        with patch('streamlit.file_uploader', return_value=uploaded('recorded_at,height_cm,weight_kg\n')):
            button(app, 'Restore log').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['bmi_log'], [])
        self.assertEqual(len(app.metric), 0)

    def test_sets_with_different_weights(self):
        app = self.app.switch_page('pages/Workout_Log.py').run()
        self.assertEqual(len(app.number_input), 2)
        app.text_input[0].set_value('Squat')
        app.number_input(key='workout_weight_0').set_value(135.0)
        button(app, 'Add set').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input[0].value, 'Squat')
        self.assertEqual(app.number_input(key='workout_weight_0').value, 135.0)
        self.assertEqual(app.session_state['workout_log'], [])
        app.number_input(key='workout_weight_1').set_value(155.0)
        app.number_input(key='workout_reps_1').set_value(6)
        button(app, 'Add set').click().run()
        button(app, 'Remove last set').click().run()
        self.assertEqual(len(app.number_input), 4)
        self.assertEqual(app.number_input(key='workout_weight_1').value, 155.0)
        button(app, 'Save workout').click().run()
        self.assertFalse(app.exception)
        records = app.session_state['workout_log']
        self.assertEqual(len(records), 2)
        self.assertEqual([row['sets'] for row in records], [1, 1])
        self.assertEqual([row['reps'] for row in records], [8, 6])
        self.assertEqual(app.metric[2].value, '2,010')

    def test_workout_and_food(self):
        app = self.app.switch_page('pages/Workout_Log.py').run()
        app.text_input[0].set_value('Bench press')
        number(app, 'Weight (lb)').set_value(135.0)
        button(app, 'Save workout').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, '1,080')
        # Editing an input must recalculate derived volume after saving.
        app.session_state['workout_log_editor'] = {'edited_rows': {0: {'sets': 4}}, 'added_rows': [], 'deleted_rows': []}
        button(app, 'Save changes').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, '4,320')
        app.switch_page('pages/Food_Log.py').run()
        app.radio[0].set_value('Enter macros manually').run()
        app.text_input[0].set_value('Lunch')
        number(app, 'Protein (g)').set_value(30.0)
        number(app, 'Carbohydrate (g)').set_value(40.0)
        number(app, 'Fat (g)').set_value(10.0)
        button(app, 'Save food').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '370.0')
        app.radio[0].set_value('Common food').run()
        number(app, 'Amount').set_value(150.0)
        button(app, 'Save food').click().run()
        self.assertFalse(app.exception)
        self.assertAlmostEqual(app.session_state['food_log'][-1]['protein_g'], 46.5)

    def test_common_food_ounces_are_converted(self):
        app = self.app.switch_page('pages/Food_Log.py').run()
        next(item for item in app.selectbox if item.label == 'Unit').set_value('Ounces (oz)').run()
        number(app, 'Amount').set_value(1.0)
        button(app, 'Save food').click().run()
        self.assertFalse(app.exception)
        record = app.session_state['food_log'][-1]
        self.assertAlmostEqual(record['protein_g'], 31.0 * 28.349523125 / 100)
        self.assertIn('1 oz', record['food'])


if __name__ == '__main__':
    unittest.main()
