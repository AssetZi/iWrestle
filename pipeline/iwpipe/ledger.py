"""What has already been pushed, by natural key.

cktool has no upsert, so the pipeline remembers its own writes. The ledger is
committed to git: it is the record of what exists in CloudKit and the reason a
rerun of a collector does not create duplicates.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .config import LEDGER_PATH


def load() -> dict[str, Any]:
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save(entries: dict[str, Any]) -> None:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")


def entry_key(source_key: str, environment: str) -> str:
    """Development and production are separate databases, tracked separately."""
    return f"{environment}:{source_key}"


def contains(source_key: str, environment: str) -> bool:
    return entry_key(source_key, environment) in load()


def record(
    source_key: str, environment: str, record_name: str, name: str
) -> None:
    entries = load()
    entries[entry_key(source_key, environment)] = {
        "recordName": record_name,
        "sourceKey": source_key,
        "environment": environment,
        "name": name,
        "pushedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save(entries)


def forget(source_key: str, environment: str) -> dict[str, Any] | None:
    entries = load()
    removed = entries.pop(entry_key(source_key, environment), None)
    if removed:
        save(entries)
    return removed


def find_cross_source(name_slug: str, day: str) -> list[str]:
    """Keys already pushed for the same event name and day from another source.

    The natural key is source-prefixed, so the same tournament listed by two
    sites would otherwise be pushed twice. This cannot be resolved
    automatically (the two listings may differ), so it is surfaced in review.
    """
    suffix = f":{name_slug}:{day}"
    return [
        entry["sourceKey"]
        for entry in load().values()
        if entry["sourceKey"].endswith(suffix)
    ]
