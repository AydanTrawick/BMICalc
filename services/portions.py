"""Food portion labels and conversions to grams."""
import math
import re


MASS_UNITS = {
    "Grams (g)": 1.0,
    "Ounces (oz)": 28.349523125,
    "Pounds (lb)": 453.59237,
}

MASS_UNIT_ABBREVIATIONS = {
    "Grams (g)": "g",
    "Ounces (oz)": "oz",
    "Pounds (lb)": "lb",
}


def grams_from_amount(amount, grams_per_unit):
    amount = float(amount)
    grams_per_unit = float(grams_per_unit)
    grams = amount * grams_per_unit
    if not math.isfinite(grams) or not 0 < grams <= 10000:
        raise ValueError("The portion must weigh between 0 and 10,000 grams.")
    return grams


def describe_portion(amount, unit, grams):
    abbreviation = MASS_UNIT_ABBREVIATIONS.get(unit)
    selected = f"{amount:g} {abbreviation}" if abbreviation else f"{amount:g} × {unit}"
    return selected if unit == "Grams (g)" else f"{selected}; {grams:g} g"


def default_amount(unit, maximum):
    preferred = {
        "Grams (g)": 100.0,
        "Ounces (oz)": 4.0,
        "Pounds (lb)": 0.25,
    }.get(unit, 1.0)
    return min(preferred, maximum)


def _description_measure(portion):
    description = str(portion.get("portionDescription") or "").strip()
    if not description or description.casefold() == "quantity not specified":
        return None
    match = re.match(r"^(\d+(?:\.\d+)?|\d+/\d+)\s+(.+)$", description)
    if not match:
        return description, 1.0
    number, name = match.groups()
    if "/" in number:
        numerator, denominator = number.split("/", 1)
        units = float(numerator) / float(denominator)
    else:
        units = float(number)
    return (name.strip(), units) if units > 0 else None


def _portion_measure(portion):
    description = str(portion.get("portionDescription") or "").strip()
    if description.casefold() == "quantity not specified":
        return None
    described = _description_measure(portion)
    unit = portion.get("measureUnit") or {}
    name = str(unit.get("name") or unit.get("abbreviation") or "portion").strip()
    if described and name.casefold() in {"undetermined", "portion"}:
        return described
    modifier = str(portion.get("modifier") or portion.get("portionDescription") or "").strip()
    if modifier and modifier.casefold() not in name.casefold():
        name = f"{name}, {modifier}"
    try:
        units = float(portion.get("amount") or 1)
    except (TypeError, ValueError):
        units = 1.0
    return name, units


def usda_portion_units(food):
    """Return exact mass units plus USDA household measures when supplied."""
    options = dict(MASS_UNITS)
    for portion in food.get("foodPortions") or []:
        measure = _portion_measure(portion)
        if measure is None:
            continue
        name, units = measure
        try:
            gram_weight = float(portion.get("gramWeight"))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(units) or not math.isfinite(gram_weight) or units <= 0 or gram_weight <= 0:
            continue
        grams_per_unit = gram_weight / units
        options[f"{name} ({grams_per_unit:g} g)"] = grams_per_unit

    try:
        serving_size = float(food.get("servingSize"))
        serving_unit = str(food.get("servingSizeUnit") or "").strip().casefold()
    except (TypeError, ValueError):
        serving_size = 0
        serving_unit = ""
    if serving_size > 0 and math.isfinite(serving_size):
        if serving_unit in {"g", "gram", "grams"}:
            serving_grams = serving_size
        elif serving_unit in {"oz", "ounce", "ounces"}:
            serving_grams = serving_size * MASS_UNITS["Ounces (oz)"]
        else:
            serving_grams = 0
        if serving_grams > 0:
            options[f"Serving ({serving_grams:g} g)"] = serving_grams
    return options
