#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from datetime import datetime

# -------------------- LLM PLUG-IN --------------------
def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Implement with your model provider.
    Must return a JSON string when asked for JSON, or Markdown when asked for Markdown.
    """
    raise NotImplementedError("Plug in OpenAI/local model/etc in call_llm().")

# -------------------- Helpers --------------------
PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def redact(text: str) -> str:
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return text

def ensure_ids(msgs):
    for i, m in enumerate(msgs, start=1):
        m.setdefault("id", i)
    return msgs

def chunk_messages(messages, max_chars=12000, min_gap_minutes=180):
    chunks, cur, cur_chars, last_ts = [], [], 0, None
    def flush():
        nonlocal cur, cur_chars
        if cur: chunks.append(cur)
        cur, cur_chars = [], 0

    for m in messages:
        ts = datetime.fromisoformat(m["ts"])
        if last_ts is not None:
            gap = (ts - last_ts).total_seconds() / 60
            if gap >= min_gap_minutes:
                flush()
        line = f'[{m["id"]}] {m["ts"]} {m["author"]}: {redact(m["text"])}\n'
        if cur and cur_chars + len(line) > max_chars:
            flush()
        cur.append(m)
        cur_chars += len(line)
        last_ts = ts
    flush()
    return chunks

def escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def md_to_html_basic(md: str) -> str:
    lines = md.splitlines()
    html, in_ul = [], False
    def close_ul():
        nonlocal in_ul
        if in_ul:
            html.append("</ul>")
            in_ul = False

    for line in lines:
        if line.startswith("### "):
            close_ul(); html.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("## "):
            close_ul(); html.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            if not in_ul:
                html.append("<ul>"); in_ul = True
            html.append(f"<li>{escape(line[2:])}</li>")
        elif line.strip() == "":
            close_ul()
        else:
            close_ul(); html.append(f"<p>{escape(line)}</p>")
    close_ul()
    return "\n".join(html)

def write_html_page(out_dir: Path, title: str, nav: list[tuple[str,str]], slug: str, body_html: str):
    nav_html = " ".join([f'<a href="{href}">{escape(label)}</a>' for label, href in nav])
    page = f"""<!doctype html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{escape(title)}</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0}}
header{{padding:16px 18px;border-bottom:1px solid #ccc;position:sticky;top:0;background:#fff}}
main{{max-width:980px;margin:0 auto;padding:18px}}
nav a{{margin-right:10px;text-decoration:none}}
h2{{margin-top:22px}}
.card{{border:1px solid #ddd;border-radius:14px;padding:12px 14px;margin:12px 0}}
small{{opacity:.7}}
</style>
</head>
<body>
<header>
  <div><strong>{escape(title)}</strong></div>
  <nav>{nav_html}</nav>
</header>
<main>{body_html}</main>
</body></html>
"""
    (out_dir / f"{slug}.html").write_text(page, encoding="utf-8")

# -------------------- OPS Extractor --------------------
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

OPS_EMPTY = {
  "band":{"name":"","members":[]},
  "rehearsals":[], "gigs":[], "tasks":[], "decisions":[], "gear":[], "links":[], "open_questions":[]
}

def extract_ops(chunk):
    transcript = "\n".join(
        f'[{m["id"]}] {m["ts"]} {m["author"]}: {redact(m["text"])}'
        for m in chunk
    )
    user = f"""Extract operational band info from these messages.

MESSAGES:
{transcript}

Return STRICT JSON only. If nothing found, return:
{json.dumps(OPS_EMPTY)}
"""
    raw = call_llm(OPS_EXTRACT_SYSTEM, user)
    return json.loads(raw)

def merge_dict_lists(base, part):
    # lightweight merge with set-dedup for members
    if part.get("band"):
        if not base["band"]["name"]:
            base["band"]["name"] = part["band"].get("name","")
        base["band"]["members"] = sorted(set(base["band"]["members"] + part["band"].get("members",[])))
    for k in ["rehearsals","gigs","tasks","decisions","gear","links","open_questions"]:
        base[k].extend(part.get(k, []))
    return base

OPS_WRITE_SYSTEM = """You write clean operational webpages in Markdown for a band.
Rules:
- Do NOT quote chat.
- Use only the provided JSON.
- Keep it practical: dates, checklists, clear headings.
- If a section has no data, omit it.
"""

def write_ops_page(slug: str, knowledge: dict) -> str:
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
    return call_llm(OPS_WRITE_SYSTEM, user)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--messages", required=True, help="messages.json [{id,ts,author,text}]")
    ap.add_argument("--out", default="site_ops", help="output folder")
    ap.add_argument("--title", default="Band Ops Hub", help="site title")
    args = ap.parse_args()

    msgs = ensure_ids(json.loads(Path(args.messages).read_text(encoding="utf-8")))
    chunks = chunk_messages(msgs)

    knowledge = json.loads(json.dumps(OPS_EMPTY))
    for ch in chunks:
        knowledge = merge_dict_lists(knowledge, extract_ops(ch))

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "knowledge.json").write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = [
        ("index","Home"),
        ("rehearsals","Rehearsals"),
        ("gigs","Gigs"),
        ("tasks","Tasks"),
        ("decisions","Decisions"),
        ("gear","Gear"),
        ("links","Links"),
        ("review","Review"),
    ]
    nav = [(label, f"{slug}.html") for slug, label in pages]

    for slug, _label in pages:
        md = write_ops_page(slug, knowledge)
        html_body = md_to_html_basic(md)
        write_html_page(out, args.title, nav, slug, html_body)

    print(f"✅ Built: {out.resolve() / 'index.html'}")

if __name__ == "__main__":
    main()

