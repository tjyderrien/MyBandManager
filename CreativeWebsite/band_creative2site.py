#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from datetime import datetime

def call_llm(system_prompt: str, user_prompt: str) -> str:
    raise NotImplementedError("Plug in your model provider here.")

PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
def redact(t: str) -> str:
    return EMAIL_RE.sub("[REDACTED_EMAIL]", PHONE_RE.sub("[REDACTED_PHONE]", t))

def ensure_ids(msgs):
    for i, m in enumerate(msgs, start=1):
        m.setdefault("id", i)
    return msgs

def chunk_messages(messages, max_chars=12000, min_gap_minutes=240):
    chunks, cur, cur_chars, last_ts = [], [], 0, None
    def flush():
        nonlocal cur, cur_chars
        if cur: chunks.append(cur)
        cur, cur_chars = [], 0
    for m in messages:
        ts = datetime.fromisoformat(m["ts"])
        if last_ts is not None:
            if (ts - last_ts).total_seconds()/60 >= min_gap_minutes:
                flush()
        line = f'[{m["id"]}] {m["ts"]} {m["author"]}: {redact(m["text"])}\n'
        if cur and cur_chars + len(line) > max_chars:
            flush()
        cur.append(m); cur_chars += len(line); last_ts = ts
    flush(); return chunks

def escape(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def md_to_html_basic(md: str) -> str:
    lines = md.splitlines()
    html, in_ul = [], False
    def close_ul():
        nonlocal in_ul
        if in_ul: html.append("</ul>"); in_ul = False
    for line in lines:
        if line.startswith("### "): close_ul(); html.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("## "): close_ul(); html.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            if not in_ul: html.append("<ul>"); in_ul = True
            html.append(f"<li>{escape(line[2:])}</li>")
        elif line.strip() == "": close_ul()
        else: close_ul(); html.append(f"<p>{escape(line)}</p>")
    close_ul(); return "\n".join(html)

def write_html_page(out_dir: Path, title: str, nav: list[tuple[str,str]], slug: str, body_html: str):
    nav_html = " ".join([f'<a href="{href}">{escape(label)}</a>' for label, href in nav])
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{escape(title)}</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0}}
header{{padding:16px 18px;border-bottom:1px solid #ccc;position:sticky;top:0;background:#fff}}
main{{max-width:980px;margin:0 auto;padding:18px}}
nav a{{margin-right:10px;text-decoration:none}}
h2{{margin-top:22px}}
</style></head>
<body><header><div><strong>{escape(title)}</strong></div><nav>{nav_html}</nav></header>
<main>{body_html}</main></body></html>"""
    (out_dir / f"{slug}.html").write_text(page, encoding="utf-8")

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

EMPTY = {"songs":[], "setlists":[], "recordings":[], "decisions":[], "open_questions":[]}

def extract_creative(chunk):
    transcript = "\n".join(
        f'[{m["id"]}] {m["ts"]} {m["author"]}: {redact(m["text"])}'
        for m in chunk
    )
    user = f"""Extract creative info from these messages.

MESSAGES:
{transcript}

Return STRICT JSON only. If nothing found, return:
{json.dumps(EMPTY)}
"""
    return json.loads(call_llm(CREATIVE_EXTRACT_SYSTEM, user))

def merge(base, part):
    for k in base.keys():
        base[k].extend(part.get(k, []))
    return base

CREATIVE_WRITE_SYSTEM = """Write clean creative-band hub webpages in Markdown.
Rules:
- Don’t quote chat.
- Use only provided JSON.
- Make it musician-friendly: clear sections, actionable todo lists, links.
"""

def write_page(slug: str, knowledge: dict) -> str:
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
    return call_llm(CREATIVE_WRITE_SYSTEM, user)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--messages", required=True)
    ap.add_argument("--out", default="site_creative")
    ap.add_argument("--title", default="Band Creative Hub")
    args = ap.parse_args()

    msgs = ensure_ids(json.loads(Path(args.messages).read_text(encoding="utf-8")))
    chunks = chunk_messages(msgs)

    knowledge = json.loads(json.dumps(EMPTY))
    for ch in chunks:
        knowledge = merge(knowledge, extract_creative(ch))

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "knowledge.json").write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = [("index","Home"),("songs","Songs"),("setlists","Setlists"),("recordings","Recordings"),("decisions","Decisions"),("review","Review")]
    nav = [(label, f"{slug}.html") for slug, label in pages]

    for slug, _ in pages:
        md = write_page(slug, knowledge)
        write_html_page(out, args.title, nav, slug, md_to_html_basic(md))

    print(f"✅ Built: {out.resolve() / 'index.html'}")

if __name__ == "__main__":
    main()

