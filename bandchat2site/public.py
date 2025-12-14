from __future__ import annotations

import json
from pathlib import Path

from .html import md_to_html_basic, write_html_page
from .llm import call_llm_json, call_llm_text
from .messages import chunk_messages, ensure_ids, sanitize_public

PUBLIC_SCHEMA = {
    "type": "object",
    "properties": {
        "band": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "tagline": {"type": "string"},
                "genre_keywords": {"type": "array", "items": {"type": "string"}},
                "city": {"type": "string"},
                "members_public": {"type": "array", "items": {"type": "string"}},
                "short_bio": {"type": "string"},
            },
            "required": ["name", "tagline", "genre_keywords", "city", "members_public", "short_bio"],
            "additionalProperties": False,
        },
        "shows": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "venue": {"type": "string"},
                    "city": {"type": "string"},
                    "notes": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["sources"],
                "additionalProperties": False,
            },
        },
        "media": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "url": {"type": "string"},
                    "notes": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["url", "sources"],
                "additionalProperties": False,
            },
        },
        "press": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "blurb": {"type": "string"},
                    "quotes": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["sources"],
                "additionalProperties": False,
            },
        },
        "contact": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "public_contact_text": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["public_contact_text", "sources"],
                "additionalProperties": False,
            },
        },
        "open_questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["question", "sources"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["band", "shows", "media", "press", "contact", "open_questions"],
    "additionalProperties": False,
}

PUBLIC_EMPTY = {
    "band": {
        "name": "",
        "tagline": "",
        "genre_keywords": [],
        "city": "",
        "members_public": [],
        "short_bio": "",
    },
    "shows": [],
    "media": [],
    "press": [],
    "contact": [],
    "open_questions": [],
}

PUBLIC_EXTRACT_SYSTEM = """You extract ONLY public-safe information about a band from chat.
Hard rules (must follow):
- Exclude private logistics, interpersonal conflict, finances, phone numbers, emails, addresses.
- Use ONLY facts present in messages; if uncertain, omit.
- Sources are message IDs (keep internally).
Return STRICT JSON with exactly these keys:
band{name?,tagline?,genre_keywords[],city?,members_public[],short_bio?},
shows[{date?,venue?,city?,notes?,sources[]}],
media[{label?,url,notes?,sources[]}],
press[{blurb?,quotes?,sources[]}],
contact[{public_contact_text?,sources[]}],
open_questions[{question,sources[]}]
"""

PUBLIC_WRITE_SYSTEM = """Write a clean public-facing band website in Markdown.
Rules:
- Do not quote chat.
- Use ONLY provided JSON.
- Keep it minimal and promo-ready.
"""


def extract_public(chunk: list[dict], *, model: str | None = None, llm_json=call_llm_json) -> dict:
    transcript = "\n".join(
        f"[{m['id']}] {m['ts']} {m['author']}: {sanitize_public(m['text'])}" for m in chunk
    )
    user = f"""Extract public-safe band info from these messages.

MESSAGES:
{transcript}

Return STRICT JSON only. If nothing found, return:
{json.dumps(PUBLIC_EMPTY)}
"""
    return llm_json(PUBLIC_EXTRACT_SYSTEM, user, PUBLIC_SCHEMA, model=model, name="public_extract")


def merge_public(base: dict, part: dict) -> dict:
    b = part.get("band", {})
    if b:
        for key in ["name", "tagline", "city", "short_bio"]:
            if not base["band"].get(key) and b.get(key):
                base["band"][key] = b[key]
        base["band"]["genre_keywords"] = sorted(set(base["band"]["genre_keywords"] + b.get("genre_keywords", [])))
        base["band"]["members_public"] = sorted(set(base["band"]["members_public"] + b.get("members_public", [])))
    for key in ["shows", "media", "press", "contact", "open_questions"]:
        base[key].extend(part.get(key, []))
    return base


def write_public_page(
    slug: str, knowledge: dict, *, model: str | None = None, llm_text=call_llm_text
) -> str:
    user = f"""Create a Markdown page for slug: {slug}

KNOWLEDGE_JSON:
{json.dumps(knowledge, ensure_ascii=False, indent=2)}

Pages:
- index: band name + 1-paragraph bio + top media links + next show
- shows: upcoming/past shows (if present)
- media: links with short labels (music, video, photos, EPK folder)
- contact: ONLY public contact text from JSON (no emails/phones if missing)
- review: open_questions and what’s missing (e.g., “need bio”, “need genre tags”)

Return Markdown only.
"""
    return llm_text(PUBLIC_WRITE_SYSTEM, user, model=model)


def build_public_site(
    messages: list[dict],
    out_dir: Path,
    *,
    title: str = "Band",
    model: str | None = None,
    llm_text=call_llm_text,
    llm_json=call_llm_json,
) -> Path:
    msgs = ensure_ids(messages)
    chunks = chunk_messages(msgs, max_chars=12000, min_gap_minutes=360, sanitize=sanitize_public)

    knowledge = json.loads(json.dumps(PUBLIC_EMPTY))
    for ch in chunks:
        knowledge = merge_public(knowledge, extract_public(ch, model=model, llm_json=llm_json))

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "knowledge.json").write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = [
        ("index", "Home"),
        ("shows", "Shows"),
        ("media", "Media"),
        ("contact", "Contact"),
        ("review", "Review"),
    ]
    nav = [(label, f"{slug}.html") for slug, label in pages]

    for slug, _ in pages:
        md = write_public_page(slug, knowledge, model=model, llm_text=llm_text)
        write_html_page(out_dir, title, nav, slug, md_to_html_basic(md))

    return out_dir
