from __future__ import annotations

import json
import os
from typing import Any, Dict

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - handled in _get_client
    OpenAI = None  # type: ignore[assignment]
    _import_error = exc
else:
    _import_error = None

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_client = None


def _get_client() -> "OpenAI":
    if OpenAI is None:  # type: ignore[truthy-bool]
        raise RuntimeError(
            "The openai package is required for LLM calls. Install dependencies with `pip install -r requirements.txt`."
        ) from _import_error
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def _extract_text(response: Any) -> str:
    """Extract the first text segment from a Responses API payload."""
    if getattr(response, "output_text", None):
        return response.output_text
    output = getattr(response, "output", None) or []
    for item in output:
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", "") == "output_text" and getattr(content, "text", None):
                return content.text
            if getattr(content, "text", None):
                return content.text
    raise ValueError("No text content returned from model response")


def call_llm_text(system_prompt: str, user_prompt: str, *, model: str | None = None) -> str:
    """Call the OpenAI Responses API for free-form text (Markdown) output."""
    client = _get_client()
    response = client.responses.create(
        model=model or DEFAULT_MODEL,
        input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
    )
    return _extract_text(response)


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    *,
    model: str | None = None,
    name: str = "response",
) -> Dict[str, Any]:
    """Call the OpenAI Responses API with a strict JSON schema."""
    client = _get_client()
    response = client.responses.create(
        model=model or DEFAULT_MODEL,
        input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "schema": schema,
                "strict": True,
            },
        },
    )
    raw_text = _extract_text(response)
    return json.loads(raw_text)
