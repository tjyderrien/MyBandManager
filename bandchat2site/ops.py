from __future__ import annotations

import json
from pathlib import Path

from .html import md_to_html_basic, write_html_page
from .llm import call_llm_json, call_llm_text
from .messages import chunk_messages, ensure_ids, redact_contacts

OPS_SCHEMA = {
    "type": "object",
    "properties": {
        "band": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "members": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "members"],
            "additionalProperties": False,
        },
        "rehearsals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "location": {"type": "string"},
                    "agenda": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["sources"],
                "additionalProperties": False,
            },
        },
        "gigs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "venue": {"type": "string"},
                    "call_time": {"type": "string"},
                    "setlist": {"type": "array", "items": {"type": "string"}},
                    "notes": {"type": "array", "items": {"type": "string"}},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["sources"],
                "additionalProperties": False,
            },
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "owner": {"type": "string"},
                    "due": {"type": "string"},
                    "status": {"type": "string", "enum": ["open", "done", "blocked"]},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["task", "sources"],
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
        "gear": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "who": {"type": "string"},
                    "when": {"type": "string"},
                    "notes": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["item", "sources"],
                "additionalProperties": False,
            },
        },
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "label": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["url", "sources"],
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
    "required": [
        "band",
        "rehearsals",
        "gigs",
        "tasks",
        "decisions",
        "gear",
        "links",
        "open_questions",
    ],
    "additionalProperties": False,
}

OPS_EMPTY = {
    "band": {"name": "", "members": []},
    "rehearsals": [],
    "gigs": [],
    "tasks": [],
    "decisions": [],
    "gear": [],
    "links": [],
    "open_questions": [],
}

OPS_EXTRACT_SYSTEM = """You extract operational band info from chat messages.
Rules:
- Use ONLY facts present in messages. If unsure, omit.
- Keep sources as message IDs.
- Do NOT output phone numbers/emails/addresses (they are redacted).
Output STRICT JSON with exactly these keys:
band{name,members[]},
rehearsals[{date?,time?,location?,agenda[],notes[],sources[]}],
gigs[{date?,time?,venue?,call_time?,setlist[],notes[],sources[]}],
tasks[{task,owner?,due?,status(open|done|blocked)?,sources[]}],
decisions[{date?,decision,sources[]}],
gear[{item,who?,when?,notes?,sources[]}],
links[{url,label?,sources[]}],
open_questions[{question,sources[]}]
"""

OPS_WRITE_SYSTEM = """You write clean operational webpages in Markdown for a band.
Rules:
- Do NOT quote chat.
- Use only the provided JSON.
- Keep it practical: dates, checklists, clear headings.
- If a section has no data, omit it.
"""


def _sanitize_ops(text: str) -> str:
    return redact_contacts(text)


def extract_ops(chunk: list[dict], *, model: str | None = None, llm_json=call_llm_json) -> dict:
    transcript = "\n".join(
        f"[{m['id']}] {m['ts']} {m['author']}: {_sanitize_ops(m['text'])}" for m in chunk
    )
    user = f"""Extract operational band info from these messages.

MESSAGES:
{transcript}

Return STRICT JSON only. If nothing found, return:
{json.dumps(OPS_EMPTY)}
"""
    return llm_json(OPS_EXTRACT_SYSTEM, user, OPS_SCHEMA, model=model, name="ops_extract")


def merge_dict_lists(base: dict, part: dict) -> dict:
    if part.get("band"):
        if not base["band"].get("name") and part["band"].get("name"):
            base["band"]["name"] = part["band"]["name"]
        base["band"]["members"] = sorted(set(base["band"]["members"] + part["band"].get("members", [])))
    for key in ["rehearsals", "gigs", "tasks", "decisions", "gear", "links", "open_questions"]:
        base[key].extend(part.get(key, []))
    return base


def write_ops_page(slug: str, knowledge: dict, *, model: str | None = None, llm_text=call_llm_text) -> str:
    user = f"""Create a Markdown page for slug: {slug}

KNOWLEDGE_JSON:
{json.dumps(knowledge, ensure_ascii=False, indent=2)}

Pages:
- index: next rehearsal + next gig + top 10 open tasks + latest decisions
- rehearsals: upcoming + past notes (if present)
- gigs: upcoming + past, include setlists when present
- tasks: grouped by status/owner
- decisions: chronological
- gear: who brings what
- links: annotated list
- review: open_questions + anything ambiguous

Return Markdown only.
"""
    return llm_text(OPS_WRITE_SYSTEM, user, model=model)


def build_ops_site(
    messages: list[dict],
    out_dir: Path,
    *,
    title: str = "Band Ops Hub",
    model: str | None = None,
    llm_text=call_llm_text,
    llm_json=call_llm_json,
) -> Path:
    msgs = ensure_ids(messages)
    chunks = chunk_messages(msgs, max_chars=12000, min_gap_minutes=180, sanitize=_sanitize_ops)

    knowledge = json.loads(json.dumps(OPS_EMPTY))
    for ch in chunks:
        knowledge = merge_dict_lists(knowledge, extract_ops(ch, model=model, llm_json=llm_json))

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "knowledge.json").write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = [
        ("index", "Home"),
        ("rehearsals", "Rehearsals"),
        ("gigs", "Gigs"),
        ("tasks", "Tasks"),
        ("decisions", "Decisions"),
        ("gear", "Gear"),
        ("links", "Links"),
        ("review", "Review"),
    ]
    nav = [(label, f"{slug}.html") for slug, label in pages]

    for slug, _label in pages:
        md = write_ops_page(slug, knowledge, model=model, llm_text=llm_text)
        write_html_page(out_dir, title, nav, slug, md_to_html_basic(md))

    return out_dir
