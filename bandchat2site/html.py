from __future__ import annotations

from pathlib import Path


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_to_html_basic(md: str) -> str:
    lines = md.splitlines()
    html, in_ul = [], False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            html.append("</ul>")
            in_ul = False

    for line in lines:
        if line.startswith("### "):
            close_ul()
            html.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("## "):
            close_ul()
            html.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{escape(line[2:])}</li>")
        elif line.strip() == "":
            close_ul()
        else:
            close_ul()
            html.append(f"<p>{escape(line)}</p>")
    close_ul()
    return "\n".join(html)


def write_html_page(out_dir: Path, title: str, nav: list[tuple[str, str]], slug: str, body_html: str) -> None:
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
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{slug}.html").write_text(page, encoding="utf-8")
