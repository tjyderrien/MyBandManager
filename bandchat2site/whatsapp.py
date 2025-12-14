from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

WHATSAPP_LINE = re.compile(
    r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}),\s(?P<time>\d{1,2}:\d{2})(?:\s?(?P<ampm>[APap][Mm]))?\s-\s(?P<author>[^:]+):\s(?P<text>.*)$"
)


DT_PATTERNS = [
    "%m/%d/%y, %I:%M %p",
    "%m/%d/%y, %H:%M",
    "%m/%d/%Y, %I:%M %p",
    "%m/%d/%Y, %H:%M",
]


def _parse_datetime(date_part: str, time_part: str, ampm: str | None) -> datetime:
    base = f"{date_part}, {time_part}{' ' + ampm if ampm else ''}"
    for pattern in DT_PATTERNS:
        try:
            return datetime.strptime(base, pattern)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized WhatsApp timestamp: {base}")


def parse_export_lines(lines: Iterable[str]) -> List[dict]:
    messages: List[dict] = []
    current: dict | None = None

    for raw in lines:
        line = raw.rstrip("\n")
        match = WHATSAPP_LINE.match(line)
        if match:
            if current:
                messages.append(current)
            dt = _parse_datetime(match.group("date"), match.group("time"), match.group("ampm"))
            current = {
                "ts": dt.isoformat(),
                "author": match.group("author").strip(),
                "text": match.group("text").strip(),
            }
        elif current:
            current["text"] += "\n" + line.strip()
    if current:
        messages.append(current)
    return messages


def parse_export_file(path: str | Path) -> List[dict]:
    return parse_export_lines(Path(path).read_text(encoding="utf-8").splitlines())


def export_messages_json(input_path: str | Path, output_path: str | Path) -> Path:
    messages = parse_export_file(input_path)
    out_path = Path(output_path)
    out_path.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
