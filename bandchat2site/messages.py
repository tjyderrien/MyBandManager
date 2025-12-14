from __future__ import annotations

import re
from datetime import datetime
from typing import Callable, Iterable, List, Mapping

PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PRIVATE_TOPICS = re.compile(r"\b(payment|money|rent|drama|fight|argument|complaint|salary|invoice)\b", re.I)


Message = Mapping[str, str]


def redact_contacts(text: str) -> str:
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return text


def sanitize_public(text: str) -> str:
    text = redact_contacts(text)
    if PRIVATE_TOPICS.search(text):
        return "[REDACTED_PRIVATE_CONTEXT]"
    return text


def ensure_ids(msgs: Iterable[Mapping[str, str]]) -> List[dict]:
    result = []
    for i, m in enumerate(msgs, start=1):
        new_m = dict(m)
        new_m.setdefault("id", i)
        result.append(new_m)
    return result


def chunk_messages(
    messages: Iterable[Message],
    *,
    max_chars: int,
    min_gap_minutes: int,
    sanitize: Callable[[str], str],
) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    cur: list[dict] = []
    cur_chars = 0
    last_ts = None

    def flush() -> None:
        nonlocal cur, cur_chars
        if cur:
            chunks.append(cur)
        cur, cur_chars = [], 0

    for msg in messages:
        m = dict(msg)
        ts = datetime.fromisoformat(m["ts"])
        if last_ts is not None:
            gap = (ts - last_ts).total_seconds() / 60
            if gap >= min_gap_minutes:
                flush()
        line = f"[{m['id']}] {m['ts']} {m['author']}: {sanitize(m['text'])}\n"
        if cur and cur_chars + len(line) > max_chars:
            flush()
        cur.append(m)
        cur_chars += len(line)
        last_ts = ts
    flush()
    return chunks
