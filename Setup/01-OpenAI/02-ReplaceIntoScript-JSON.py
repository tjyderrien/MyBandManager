import json
import os
from openai import OpenAI

client = OpenAI()

def call_llm_json(system_prompt: str, user_prompt: str, *, schema_name: str, schema: dict) -> dict:
    # Structured Outputs via json_schema (strict) gives schema-adherent JSON. :contentReference[oaicite:3]{index=3}
    model = os.getenv("OPENAI_MODEL_JSON", "gpt-5-mini")

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
        temperature=0.0,
        max_output_tokens=2500,
        store=False,
    )

    # With strict json_schema this should already be valid+conformant JSON. :contentReference[oaicite:4]{index=4}
    return json.loads(resp.output_text)

