"""Server-side FoodData Central search and per-100-gram macro normalization."""
import json
import math
import os
import ssl
from functools import lru_cache

import certifi
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import streamlit as st

BASE_URL = 'https://api.nal.usda.gov/fdc/v1'


class USDAError(ValueError):
    """A safe, user-facing API or nutrient-data error."""


def api_key():
    value = os.environ.get('USDA_API_KEY', '').strip()
    if not value:
        try:
            value = str(st.secrets.get('USDA_API_KEY', '')).strip()
        except FileNotFoundError:
            pass
    return value


@lru_cache(maxsize=1)
def _https_context():
    # Retain system/custom trust roots and supplement installations without a CA bundle.
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def _request(path, key, **params):
    if not key:
        raise USDAError('USDA search is not connected yet. You can still use common foods or enter macros manually.')
    url = f'{BASE_URL}/{path}?{urlencode(dict(params, api_key=key))}'
    try:
        with urlopen(url, timeout=15, context=_https_context()) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code in (401, 403):
            message = 'USDA could not authorize the connection. Please check the configured API key.'
        elif error.code == 429:
            message = 'USDA search has reached its request limit. Please try again later.'
        else:
            message = 'USDA is temporarily unavailable. Please try again.'
        raise USDAError(message) from None
    except (URLError, TimeoutError, OSError):
        raise USDAError('Could not reach USDA. Please try again.') from None
    except (ValueError, UnicodeError):
        raise USDAError('USDA returned an unreadable response. Please try again.') from None
    if not isinstance(payload, dict):
        raise USDAError('USDA returned an unexpected response. Please try again.')
    return payload


@st.cache_data(ttl=900, max_entries=128, show_spinner=False)
def search_foods(query, key, page=1):
    query = query.strip()
    if not query:
        raise USDAError('Enter a food name or brand to search.')
    result = _request('foods/search', key, query=query, pageSize=25, pageNumber=page)
    foods = result.get('foods')
    if not isinstance(foods, list):
        raise USDAError('USDA returned an unexpected search response. Please try again.')
    return {
        'foods': [food for food in foods if isinstance(food, dict) and isinstance(food.get('fdcId'), int) and food.get('description')],
        'totalPages': int(result.get('totalPages') or 0),
        'totalHits': int(result.get('totalHits') or 0),
    }


@st.cache_data(ttl=3600, max_entries=256, show_spinner=False)
def food_details(fdc_id, key):
    return _request(f'food/{int(fdc_id)}', key)


def food_label(food):
    brand = food.get('brandOwner') or food.get('brandName')
    return ' · '.join(str(part) for part in (
        food['description'], brand, food.get('dataType'), f"FDC {food['fdcId']}"
    ) if part)


def macros_for_portion(food, grams):
    """Use full-detail nutrient amounts per 100 g, never labelNutrients per serving.

    Missing macros are unknown, not zero. Explicit zero amounts are valid.
    """
    grams = float(grams)
    if not math.isfinite(grams) or not 0 < grams <= 10000:
        raise USDAError('Enter an amount between 0 and 10,000 grams.')
    macros = {}
    wanted = {1003: 'protein_g', 1005: 'carbs_g', 1004: 'fat_g'}
    for entry in food.get('foodNutrients') or []:
        nutrient = entry.get('nutrient') or {}
        field = wanted.get(nutrient.get('id'))
        if field is None or str(nutrient.get('unitName', '')).lower() != 'g':
            continue
        try:
            amount = float(entry.get('amount'))
        except (TypeError, ValueError):
            continue
        if math.isfinite(amount) and amount >= 0:
            macros[field] = amount * grams / 100
    if len(macros) != 3:
        raise USDAError('This USDA item is missing complete protein, carbohydrate, or fat data. Choose another item or enter its label macros manually.')
    return macros
