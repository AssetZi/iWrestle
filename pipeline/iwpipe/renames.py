"""Names a person has corrected.

A source keeps listing an event under last season's name ("2026 BGS Brawl"
dated 2027). Editing the day's file fixes it once; the next collect brings
the old name back. A key here keeps its corrected name on every collect.
The source key is still built from the name the source uses, so the event
stays the same record.
"""
from __future__ import annotations

import json

from .config import DATA_DIR

RENAMED_PATH = DATA_DIR / "renamed.json"


def load() -> dict[str, str]:
    if RENAMED_PATH.exists():
        try:
            return json.loads(RENAMED_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def name_for(source_key: str) -> str | None:
    return load().get(source_key)
