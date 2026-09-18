import io
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from streamlit.testing.v1 import AppTest
from services import usda
from services.portions import grams_from_amount, usda_portion_units


FOOD = {
    'fdcId': 123, 'description': 'Test oats', 'brandOwner': 'Test brand',
    'foodNutrients': [
        {'nutrient': {'id': nutrient, 'unitName': 'g'}, 'amount': amount}
        for nutrient, amount in [(1003, 10), (1005, 60), (1004, 5)]
    ],
    'labelNutrients': {'protein': {'value': 999}},
    'foodPortions': [
        {'amount': 1, 'measureUnit': {'name': 'cup'}, 'gramWeight': 80},
        {'measureUnit': {'name': 'undetermined'}, 'modifier': '12345',
         'portionDescription': '1 tablespoon', 'gramWeight': 12},
        {'measureUnit': {'name': 'undetermined'}, 'modifier': '90000',
         'portionDescription': 'Quantity not specified', 'gramWeight': 50},
    ],
    'servingSize': 40,
    'servingSizeUnit': 'g',
}


def button(app, label):
    return next(item for item in app.button if item.label == label)


class USDATests(unittest.TestCase):
    def test_mass_and_household_portion_conversions(self):
        self.assertAlmostEqual(grams_from_amount(2, 28.349523125), 56.69904625)
        portions = usda_portion_units(FOOD)
        self.assertEqual(portions['cup (80 g)'], 80)
        self.assertEqual(portions['tablespoon (12 g)'], 12)
        self.assertNotIn('undetermined, 12345 (12 g)', portions)
        self.assertEqual(portions['Serving (40 g)'], 40)
        with self.assertRaises(ValueError):
            grams_from_amount(100, 453.59237)

    def test_scaling_uses_100g_not_label_serving(self):
        self.assertEqual(usda.macros_for_portion(FOOD, 150),
                         dict(protein_g=15, carbs_g=90, fat_g=7.5))

    def test_missing_invalid_and_zero_macros(self):
        from copy import deepcopy
        for invalid in (None, -1, float('nan'), float('inf')):
            food = deepcopy(FOOD)
            food['foodNutrients'][0]['amount'] = invalid
            with self.assertRaises(usda.USDAError):
                usda.macros_for_portion(food, 100)
        food = deepcopy(FOOD)
        food['foodNutrients'][0]['amount'] = 0
        self.assertEqual(usda.macros_for_portion(food, 100)['protein_g'], 0)
        with self.assertRaises(usda.USDAError):
            usda.macros_for_portion({'foodNutrients': []}, 100)

    def test_request_errors_do_not_expose_key(self):
        for error in [HTTPError('https://example.com?api_key=secret', code, 'bad', {}, None)
                      for code in (403, 429, 500)] + [URLError('secret'), TimeoutError('secret')]:
            with patch('services.usda.urlopen', side_effect=error):
                with self.assertRaises(usda.USDAError) as caught:
                    usda._request('foods/search', 'secret', query='oats')
                self.assertNotIn('secret', str(caught.exception))

    def test_search_parameters_and_details(self):
        usda.search_foods.clear()
        usda.food_details.clear()
        with patch('services.usda.urlopen', return_value=io.BytesIO(b'{"foods": [], "totalPages": 0, "totalHits": 0}')) as request:
            self.assertEqual(usda.search_foods('oats & milk', 'test', 2)['foods'], [])
            self.assertIn('query=oats+%26+milk', request.call_args.args[0])
            self.assertIn('pageNumber=2', request.call_args.args[0])
            self.assertEqual(request.call_args.kwargs['timeout'], 15)
            context = request.call_args.kwargs['context']
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
        with patch('services.usda._request', return_value=FOOD) as request:
            self.assertEqual(usda.food_details(123, 'test'), FOOD)
            request.assert_called_once_with('food/123', 'test')

    def test_search_select_portion_and_save(self):
        result = {'foods': [FOOD], 'totalPages': 2, 'totalHits': 26}
        with patch('services.usda.api_key', return_value='test'), \
             patch('services.usda.search_foods', return_value=result) as search, \
             patch('services.usda.food_details', return_value=FOOD):
            app = AppTest.from_file('BMI2.py').run(timeout=30)
            app.switch_page('pages/Food_Log.py').run()
            app.radio[0].set_value('USDA food search').run()
            next(x for x in app.text_input if x.label == 'Search USDA foods').set_value('oats')
            button(app, 'Search foods').click().run()
            self.assertEqual(app.session_state['food_log'], [])
            button(app, 'Next results').click().run()
            search.assert_called_with('oats', 'test', 2)
            app.selectbox(key='usda_selection').set_value(123).run()
            app.number_input(key='usda_amount_123_Grams (g)').set_value(150.0).run()
            button(app, 'Add to food log').click().run()
            self.assertFalse(app.exception)
            record = app.session_state['food_log'][0]
            self.assertEqual(record['protein_g'], 15)
            self.assertEqual(record['carbs_g'], 90)
            self.assertEqual(record['fat_g'], 7.5)
            self.assertIn('USDA 123; 150 g', record['food'])
            self.assertTrue(any(x.label == 'Calories' and x.value == '487.5' for x in app.metric))
            app.switch_page('pages/Workout_Log.py').run()
            self.assertNotIn('When to ask for help', [x.label for x in app.expander])
            self.assertNotIn('Glossary', [x.label for x in app.expander])
            app.switch_page('pages/Glossary.py').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, 'Glossary')
            self.assertEqual(len(app.dataframe), 1)

    def test_missing_key_and_empty_results(self):
        with patch('services.usda.api_key', return_value=''):
            app = AppTest.from_file('BMI2.py').run(timeout=30)
            app.switch_page('pages/Food_Log.py').run()
            app.radio[0].set_value('USDA food search').run()
            self.assertFalse(app.exception)
            self.assertTrue(any('not connected' in x.value for x in app.info))
            self.assertTrue(any(x.label == 'Calories' for x in app.metric))
        with patch('services.usda.api_key', return_value='test'), \
             patch('services.usda.search_foods', return_value={'foods': [], 'totalPages': 0, 'totalHits': 0}):
            app.run()
            next(x for x in app.text_input if x.label == 'Search USDA foods').set_value('missing')
            button(app, 'Search foods').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any('No matching' in x.value for x in app.info))
