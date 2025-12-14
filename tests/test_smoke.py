from __future__ import annotations

import json
from pathlib import Path
import unittest

from bandchat2site.creative import build_creative_site
from bandchat2site.ops import build_ops_site
from bandchat2site.public import build_public_site


FAKE_MESSAGES = [
    {"ts": "2024-01-01T12:00:00", "author": "Ada", "text": "Book studio?"},
    {"ts": "2024-01-02T09:00:00", "author": "Lin", "text": "We have a gig at Town Hall"},
]


def fake_llm_text(_system: str, _user: str, *, model=None):  # noqa: ANN001
    return "# Heading\n- Stub content"


def fake_ops_json(_system: str, _user: str, _schema, *, model=None, name="response"):  # noqa: ANN001
    return {
        "band": {"name": "Test Band", "members": ["Ada", "Lin"]},
        "rehearsals": [],
        "gigs": [],
        "tasks": [],
        "decisions": [],
        "gear": [],
        "links": [],
        "open_questions": [],
    }


def fake_creative_json(_system: str, _user: str, _schema, *, model=None, name="response"):  # noqa: ANN001
    return {
        "songs": [],
        "setlists": [],
        "recordings": [],
        "decisions": [],
        "open_questions": [],
    }


def fake_public_json(_system: str, _user: str, _schema, *, model=None, name="response"):  # noqa: ANN001
    return {
        "band": {
            "name": "Test Band",
            "tagline": "Stub", 
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


class SmokeBuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self._testMethodName)
        if self.tmp.exists():
            for child in self.tmp.iterdir():
                if child.is_file():
                    child.unlink()
                else:
                    for inner in child.iterdir():
                        inner.unlink()
                    child.rmdir()
            self.tmp.rmdir()
        self.tmp.mkdir()

    def tearDown(self) -> None:
        for child in self.tmp.iterdir():
            if child.is_file():
                child.unlink()
            else:
                for inner in child.iterdir():
                    inner.unlink()
                child.rmdir()
        self.tmp.rmdir()

    def test_ops_build(self) -> None:
        out = self.tmp / "ops"
        build_ops_site(FAKE_MESSAGES, out, llm_text=fake_llm_text, llm_json=fake_ops_json)
        self.assertTrue((out / "index.html").exists())
        payload = json.loads((out / "knowledge.json").read_text())
        self.assertEqual(payload["band"]["name"], "Test Band")

    def test_creative_build(self) -> None:
        out = self.tmp / "creative"
        build_creative_site(FAKE_MESSAGES, out, llm_text=fake_llm_text, llm_json=fake_creative_json)
        self.assertTrue((out / "index.html").exists())
        payload = json.loads((out / "knowledge.json").read_text())
        self.assertEqual(payload["songs"], [])

    def test_public_build(self) -> None:
        out = self.tmp / "public"
        build_public_site(FAKE_MESSAGES, out, llm_text=fake_llm_text, llm_json=fake_public_json)
        self.assertTrue((out / "index.html").exists())
        payload = json.loads((out / "knowledge.json").read_text())
        self.assertEqual(payload["band"]["name"], "Test Band")


if __name__ == "__main__":
    unittest.main()
