from typing import Any

from openai import OpenAI


SYSTEM_PROMPT = """
You are FirstRep Coach, a concise fitness and nutrition assistant inside a
Streamlit fitness toolkit. Help users with training, recovery, BMI context,
meal planning ideas, and safe next steps. Keep answers practical and friendly.
Do not diagnose medical conditions, prescribe drugs, or give steroid protocols.
For serious symptoms or medical concerns, encourage the user to contact a
qualified professional.
""".strip()


def generate_chat_reply(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
) -> str:
    if not api_key:
        raise ValueError("The OpenAI API key is missing.")

    client = OpenAI(api_key=api_key)
    recent_messages = messages[-12:]

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            *recent_messages,
        ],
    )

    return response.output_text.strip()
