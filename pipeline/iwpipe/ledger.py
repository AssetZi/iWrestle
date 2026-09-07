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
# A city-level geocode can sit a few kilometres from the real gym; within
# this radius on the same day the listing is worth a look, not a skip.
MAYBE_KM = 6.0


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


def _leaving(entry: dict[str, Any]) -> bool:
    """About to be removed (see MISS_LIMIT below); another source's listing
    of the same event should take over rather than be skipped as a duplicate.
    A Track event that Flo picks up is dropped by the Track collector and
    would otherwise vanish from both."""
    return entry.get("missCount", 0) >= MISS_LIMIT


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


def find_nearby(source_key: str, day: str, location: dict[str, float] | None) -> list[str]:
    """Same-day listings from another source a few kilometres away."""
    if not location:
        return []
    source = source_key.split(":", 1)[0]
    found = []
    for entry in load().values():
        other = entry["sourceKey"]
        if other.split(":", 1)[0] == source or not entry.get("location") or not entry.get("date"):
            continue
        if _leaving(entry):
            continue
        if _days_apart(day, entry["date"]) == 0 and NEAR_KM < _km(location, entry["location"]) <= MAYBE_KM:
            found.append(other)
    return found


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
        if other == source_key or other in matches or _leaving(entry):
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


# --- Listings that vanished from their source -----------------------------------
# A cancelled tournament is simply gone from the next scrape. One absence
# could be a flaky page, so a record is only removed after this many runs
# in a row without it.
MISS_LIMIT = 2


def _source_of(entry: dict[str, Any]) -> str:
    return entry["sourceKey"].split(":", 1)[0]


def mark_misses(source: str, seen_keys: set[str], today: str) -> list[dict[str, Any]]:
    """Count, per upcoming entry of `source`, the runs it has been absent.

    Entries seen this run go back to zero. Entries already in the past are
    left alone: the source stops listing them and that means nothing.
    Returns the entries now missing, with their updated counts.
    """
    entries = load()
    missing: list[dict[str, Any]] = []
    for entry in entries.values():
        if _source_of(entry) != source or not entry.get("date") or entry["date"] < today[:10]:
            continue
        if entry["sourceKey"] in seen_keys:
            entry.pop("missCount", None)
            entry.pop("lastMissedAt", None)
            continue
        entry["missCount"] = entry.get("missCount", 0) + 1
        entry["lastMissedAt"] = today[:10]
        missing.append(entry)
    save(entries)
    return missing


def due_for_removal(source: str, environment: str) -> list[dict[str, Any]]:
    """Entries of one source absent MISS_LIMIT runs running, in one environment."""
    return [
        entry for entry in load().values()
        if _source_of(entry) == source and entry["environment"] == environment
        and entry.get("missCount", 0) >= MISS_LIMIT
    ]


def find_moved(source: str, name_slug: str, day: str, seen_keys: set[str], today: str) -> list[str]:
    """Keys from the same source with this name on another upcoming day.

    A tournament whose date changed gets a new key; the old listing is no
    longer on the site (it is not in `seen_keys`), so its record is stale.
    Last season's edition, already in the past, is a different event.
    """
    found: list[str] = []
    for entry in load().values():
        key = entry["sourceKey"]
        if key in seen_keys or key in found or _source_of(entry) != source:
            continue
        old_day = entry.get("date") or ""
        if old_day and old_day != day and old_day >= today[:10] and key.endswith(f":{name_slug}:{old_day}"):
            found.append(key)
    return found
