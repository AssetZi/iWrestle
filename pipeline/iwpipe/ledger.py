"""What has already been pushed, by natural key.

cktool has no upsert, so the pipeline remembers its own writes. The ledger is
committed to git: it is the record of what exists in CloudKit and the reason a
rerun of a collector does not create duplicates.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from typing import Any

from .config import LEDGER_PATH

# Two listings of one tournament rarely share a name across sites, but they
# do share a gym and a weekend.
NEAR_KM = 2.0
NEAR_DAYS = 2


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
    source_key: str, environment: str, record_name: str, name: str,
    *, day: str = "", location: dict[str, float] | None = None,
    content_hash: str = "",
) -> None:
    entries = load()
    entries[entry_key(source_key, environment)] = {
        "recordName": record_name,
        "sourceKey": source_key,
        "environment": environment,
        "name": name,
        "date": day,
        "location": location,
        "contentHash": content_hash,
        "pushedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save(entries)


def get(source_key: str, environment: str) -> dict[str, Any] | None:
    return load().get(entry_key(source_key, environment))


def forget(source_key: str, environment: str) -> dict[str, Any] | None:
    entries = load()
    removed = entries.pop(entry_key(source_key, environment), None)
    if removed:
        save(entries)
    return removed


def _km(a: dict[str, float], b: dict[str, float]) -> float:
    lat1, lon1 = math.radians(a["latitude"]), math.radians(a["longitude"])
    lat2, lon2 = math.radians(b["latitude"]), math.radians(b["longitude"])
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(h))


def _days_apart(a: str, b: str) -> int | None:
    try:
        return abs((date.fromisoformat(a[:10]) - date.fromisoformat(b[:10])).days)
    except ValueError:
        return None


def find_similar(source_key: str, name_slug: str, day: str, location: dict[str, float] | None) -> list[str]:
    """Keys already pushed that look like the same event from another source.

    A match is the same name slug on the same day, or a listing within a
    couple of kilometres and a couple of days. This cannot be resolved
    automatically (the two listings may differ), so it is surfaced in review.
    """
    matches: list[str] = []
    source = source_key.split(":", 1)[0]
    for entry in load().values():
        other = entry["sourceKey"]
        if other == source_key or other in matches:
            continue
        if other.endswith(f":{name_slug}:{day}"):
            matches.append(other)
            continue
        # A site listing two events at one gym on one day means two events
        # (an open and a dual, say). Proximity only matters across sites.
        if other.split(":", 1)[0] == source:
            continue
        if not location or not entry.get("location") or not entry.get("date"):
            continue
        gap = _days_apart(day, entry["date"])
        if gap is not None and gap <= NEAR_DAYS and _km(location, entry["location"]) <= NEAR_KM:
            matches.append(other)
    return matches
