"""Events a person has decided should not be in the directory.

Review can mark an event skip for a day, but the next collect regenerates
the file and the event comes back. This list is the durable answer: a key
here is skipped by every future collect, and removing it from CloudKit is
part of adding it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .config import DATA_DIR

EXCLUDED_PATH = DATA_DIR / "excluded.json"


def load() -> dict[str, Any]:
    if EXCLUDED_PATH.exists():
        try:
            return json.loads(EXCLUDED_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save(entries: dict[str, Any]) -> None:
    EXCLUDED_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXCLUDED_PATH.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")


def add(source_key: str, reason: str, name: str = "") -> None:
    entries = load()
    entries[source_key] = {
        "reason": reason,
        "name": name,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save(entries)


def remove(source_key: str) -> bool:
    entries = load()
    if source_key not in entries:
        return False
    del entries[source_key]
    save(entries)
    return True


def reason_for(source_key: str) -> str | None:
    entry = load().get(source_key)
    return entry["reason"] if entry else None
