import json
from typing import Any

from openai import OpenAI


def build_meal_plan_prompt(user_data: dict[str, Any]) -> str:
    """
    Convert the user's form data into instructions for the AI.
    """

    return f"""
You are the meal-planning assistant for FirstRep, a fitness and nutrition application.

Create a practical meal plan using the following information:

Age: {user_data["age"]}
Sex: {user_data["sex"]}
Height: {user_data["height"]}
Weight: {user_data["weight"]}
Fitness goal: {user_data["goal"]}
Activity level: {user_data["activity_level"]}
Number of days: {user_data["plan_days"]}
Allergies or foods to avoid: {user_data["allergies"]}
Dietary preference: {user_data["dietary_preference"]}
Grocery budget: ${user_data["budget"]:.2f}
Budget period: {user_data["budget_period"]}
Meals per day: {user_data["meals_per_day"]}

Requirements:

1. Create exactly {user_data["plan_days"]} days. Only up to 7 days max.
2. Give each meal a name, ingredients, instructions, calories,
   protein, carbohydrates, and fat.
3. Include estimated daily calories and macros.
4. Respect the allergies, dietary preferences, and grocery budget.
5. Use reasonably accessible grocery-store ingredients.
6. Reuse ingredients when appropriate to reduce cost and waste.
7. Include a combined categorized grocery list.
8. Include an estimated grocery total.
9. Grocery list total must not be more than $5 over the users budget input, but aim to hit it on the dot.
10. Do not claim to diagnose or treat medical conditions.
11. Return valid JSON only. Do not include Markdown fences or commentary.

Return the following JSON structure:

{{
  "plan_title": "string",
  "summary": "string",
  "estimated_daily_targets": {{
    "calories": 0,
    "protein_g": 0,
    "carbs_g": 0,
    "fat_g": 0
  }},
  "days": [
    {{
      "day": 1,
      "daily_totals": {{
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0
      }},
      "meals": [
        {{
          "meal_type": "Breakfast",
          "name": "string",
          "ingredients": ["string"],
          "instructions": ["string"],
          "calories": 0,
          "protein_g": 0,
          "carbs_g": 0,
          "fat_g": 0
        }}
      ]
    }}
  ],
  "grocery_list": [
    {{
      "category": "Protein",
      "items": [
        {{
          "name": "string",
          "quantity": "string",
          "estimated_price": 0.00
        }}
      ]
    }}
  ],
  "estimated_grocery_total": 0.00,
  "prep_tips": ["string"],
  "disclaimer": "string"
}}
""".strip()


def generate_meal_plan(
    api_key: str,
    model: str,
    user_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Send the meal-plan request to OpenAI and return a Python dictionary.
    """

    if not api_key:
        raise ValueError("The OpenAI API key is missing.")

    client = OpenAI(api_key=api_key)

    prompt = build_meal_plan_prompt(user_data)

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You create structured, practical meal plans for "
                    "FirstRep users. Return valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    raw_output = response.output_text.strip()

    # Sometimes a model may still wrap JSON in Markdown.
    if raw_output.startswith("```json"):
        raw_output = raw_output.removeprefix("```json")
        raw_output = raw_output.removesuffix("```")
        raw_output = raw_output.strip()
    elif raw_output.startswith("```"):
        raw_output = raw_output.removeprefix("```")
        raw_output = raw_output.removesuffix("```")
        raw_output = raw_output.strip()

    try:
        return json.loads(raw_output)

    except json.JSONDecodeError as error:
        raise ValueError(
            "OpenAI returned a response that was not valid JSON."
        ) from error