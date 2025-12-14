# MyBandManager / bandchat2site

Turn WhatsApp band chats into lightweight static sites for band operations, creative work, and public promo pages.

## What's inside
- `bandchat2site` Python package with shared modules and three pipelines: `ops`, `creative`, and `public`.
- OpenAI Responses API helpers (`call_llm_text`/`call_llm_json`) using the official SDK.
- WhatsApp export parser to convert `.txt` exports into `messages.json`.
- Simple CLI: `bandchat2site ops|creative|public|parse-whatsapp`.

## Setup
1. Install Python 3.11+ and dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure OpenAI credentials:
   ```bash
   export OPENAI_API_KEY=sk-...
   # Optional: override the model (defaults to gpt-4o-mini)
   export OPENAI_MODEL=gpt-4o-mini
   ```

## Convert WhatsApp export to JSON
```bash
python -m bandchat2site parse-whatsapp --input chat.txt --output messages.json
```
`messages.json` will contain objects shaped like `{ "ts": "2024-04-01T19:30:00", "author": "Ada", "text": "Great rehearsal" }`.

## Build sites
Use the same `messages.json` for each pipeline. Outputs are written to a folder with `index.html` and section pages.

```bash
# Operational hub
python -m bandchat2site ops --messages messages.json --out site_ops --title "Band Ops Hub"

# Creative hub
python -m bandchat2site creative --messages messages.json --out site_creative --title "Band Creative Hub"

# Public/promo site
python -m bandchat2site public --messages messages.json --out site_public --title "Band"
```

## Smoke test
Run the bundled smoke test (uses stubbed LLM responses, no API calls):
```bash
python -m unittest tests.test_smoke
```

## Notes
- The LLM helpers use strict JSON schema enforcement for structured extraction.
- Phone numbers, emails, and obviously sensitive lines are redacted before prompting.
- The generated HTML is minimal and self-contained for easy sharing or hosting.
