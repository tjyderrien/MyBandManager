from __future__ import annotations

import json
from pathlib import Path

from .html import md_to_html_basic, write_html_page
from .llm import call_llm_json, call_llm_text
from .messages import chunk_messages, ensure_ids, redact_contacts

CREATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "songs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["idea", "in_progress", "ready", "parked"],
                    },
                    "key": {"type": "string"},
                    "tempo_bpm": {"type": "string"},
                    "structure_notes": {"type": "string"},
                    "parts_notes": {"type": "string"},
                    "lyrics_notes": {"type": "string"},
                    "todo": {"type": "array", "items": {"type": "string"}},
                    "links": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["title", "sources"],
                "additionalProperties": False,
            },
        },
        "setlists": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "context": {"type": "string"},
                    "songs": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["sources"],
                "additionalProperties": False,
            },
        },
        "recordings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "notes": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["url", "sources"],
                "additionalProperties": False,
            },
        },
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "decision": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["decision", "sources"],
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
    "required": ["songs", "setlists", "recordings", "decisions", "open_questions"],
    "additionalProperties": False,
}

CREATIVE_EMPTY = {
    "songs": [],
    "setlists": [],
    "recordings": [],
    "decisions": [],
    "open_questions": [],
}

CREATIVE_EXTRACT_SYSTEM = """You extract creative band info (songs/arrangements/recordings) from chat.
Rules:
- ONLY use facts in messages. If unsure, omit.
- sources are message IDs.
- Do not output private contacts (redacted).
Return STRICT JSON with exactly these keys:
songs[{title,status(idea|in_progress|ready|parked)?,key?,tempo_bpm?,structure_notes?,parts_notes?,lyrics_notes?,todo[],links[],sources[]}],
setlists[{name?,context?,songs[],notes?,sources[]}],
recordings[{title?,url,notes?,sources[]}],
decisions[{date?,decision,sources[]}],
open_questions[{question,sources[]}]
"""

CREATIVE_WRITE_SYSTEM = """Write clean creative-band hub webpages in Markdown.
Rules:
- Don’t quote chat.
- Use only provided JSON.
- Make it musician-friendly: clear sections, actionable todo lists, links.
"""


def _sanitize_creative(text: str) -> str:
    return redact_contacts(text)


def extract_creative(chunk: list[dict], *, model: str | None = None, llm_json=call_llm_json) -> dict:
    transcript = "\n".join(
        f"[{m['id']}] {m['ts']} {m['author']}: {_sanitize_creative(m['text'])}" for m in chunk
    )
    user = f"""Extract creative info from these messages.

MESSAGES:
{transcript}

Return STRICT JSON only. If nothing found, return:
{json.dumps(CREATIVE_EMPTY)}
"""
    return llm_json(
        CREATIVE_EXTRACT_SYSTEM, user, CREATIVE_SCHEMA, model=model, name="creative_extract"
    )


def merge_creative(base: dict, part: dict) -> dict:
    for key in base.keys():
        base[key].extend(part.get(key, []))
    return base


def write_creative_page(
    slug: str, knowledge: dict, *, model: str | None = None, llm_text=call_llm_text
) -> str:
    user = f"""Create a Markdown page for slug: {slug}

KNOWLEDGE_JSON:
{json.dumps(knowledge, ensure_ascii=False, indent=2)}

Pages:
- index: what we’re working on now (top 10 todos across songs) + newest recordings + current setlist(s)
- songs: list songs grouped by status, with per-song mini-cards (key/tempo/notes/todos/links)
- setlists: setlists with context + notes
- recordings: all recording links, deduped and annotated
- decisions: chronological decisions affecting arrangements
- review: open_questions + ambiguous items

Return Markdown only.
"""
    return llm_text(CREATIVE_WRITE_SYSTEM, user, model=model)


def build_creative_site(
    messages: list[dict],
    out_dir: Path,
    *,
    title: str = "Band Creative Hub",
    model: str | None = None,
    llm_text=call_llm_text,
    llm_json=call_llm_json,
) -> Path:
    msgs = ensure_ids(messages)
    chunks = chunk_messages(msgs, max_chars=12000, min_gap_minutes=240, sanitize=_sanitize_creative)

    knowledge = json.loads(json.dumps(CREATIVE_EMPTY))
    for ch in chunks:
        knowledge = merge_creative(knowledge, extract_creative(ch, model=model, llm_json=llm_json))

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "knowledge.json").write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = [
        ("index", "Home"),
        ("songs", "Songs"),
        ("setlists", "Setlists"),
        ("recordings", "Recordings"),
        ("decisions", "Decisions"),
        ("review", "Review"),
    ]
    nav = [(label, f"{slug}.html") for slug, label in pages]

    for slug, _ in pages:
        md = write_creative_page(slug, knowledge, model=model, llm_text=llm_text)
        write_html_page(out_dir, title, nav, slug, md_to_html_basic(md))

    return out_dir
