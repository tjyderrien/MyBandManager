import os
from openai import OpenAI

client = OpenAI()

def call_llm_text(system_prompt: str, user_prompt: str) -> str:
    model = os.getenv("OPENAI_MODEL_TEXT", "gpt-5-mini")  # or "gpt-4.1-mini", etc.
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_output_tokens=2500,
        store=False,  # privacy-friendly
    )
    return resp.output_text

