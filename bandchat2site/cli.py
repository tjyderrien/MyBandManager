from __future__ import annotations

import argparse
import json
from pathlib import Path

from .creative import build_creative_site
from .ops import build_ops_site
from .public import build_public_site
from .whatsapp import export_messages_json


def _load_messages(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--messages", required=True, help="Path to messages.json [{id,ts,author,text}]")
    parser.add_argument("--out", default=None, help="Output directory")
    parser.add_argument("--title", default=None, help="Site title override")
    parser.add_argument("--model", default=None, help="OpenAI model override (defaults to OPENAI_MODEL/gpt-4o-mini)")


def cmd_ops(args: argparse.Namespace) -> None:
    out = Path(args.out or "site_ops")
    title = args.title or "Band Ops Hub"
    messages = _load_messages(args.messages)
    build_ops_site(messages, out, title=title, model=args.model)
    print(f"✅ Built: {out.resolve() / 'index.html'}")


def cmd_creative(args: argparse.Namespace) -> None:
    out = Path(args.out or "site_creative")
    title = args.title or "Band Creative Hub"
    messages = _load_messages(args.messages)
    build_creative_site(messages, out, title=title, model=args.model)
    print(f"✅ Built: {out.resolve() / 'index.html'}")


def cmd_public(args: argparse.Namespace) -> None:
    out = Path(args.out or "site_public")
    title = args.title or "Band"
    messages = _load_messages(args.messages)
    build_public_site(messages, out, title=title, model=args.model)
    print(f"✅ Built: {out.resolve() / 'index.html'}")


def cmd_whatsapp(args: argparse.Namespace) -> None:
    output = export_messages_json(args.input, args.output)
    print(f"✅ Wrote messages JSON to {output.resolve()}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Turn WhatsApp chat exports into simple band websites")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ops = sub.add_parser("ops", help="Build the operational site")
    _add_common_flags(p_ops)
    p_ops.set_defaults(func=cmd_ops)

    p_creative = sub.add_parser("creative", help="Build the creative site")
    _add_common_flags(p_creative)
    p_creative.set_defaults(func=cmd_creative)

    p_public = sub.add_parser("public", help="Build the public/promo site")
    _add_common_flags(p_public)
    p_public.set_defaults(func=cmd_public)

    p_whatsapp = sub.add_parser("parse-whatsapp", help="Parse WhatsApp export .txt into messages.json")
    p_whatsapp.add_argument("--input", required=True, help="WhatsApp export .txt file")
    p_whatsapp.add_argument("--output", default="messages.json", help="Destination JSON file")
    p_whatsapp.set_defaults(func=cmd_whatsapp)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
