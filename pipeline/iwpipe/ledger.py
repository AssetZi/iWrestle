"""What has already been pushed, by natural key.

CloudKit has no upsert, so the pipeline remembers its own writes. The
ledger is committed to git: it is the record of what exists in CloudKit and
the reason a rerun of a collector does not create duplicates.

Lifecycle of one entry, and the function that drives each edge:

    collect  ──seen──▶ mark_misses clears missCount
             ──gone──▶ mark_misses  missCount+1 ──(MISS_LIMIT)──▶ due_for_removal ──▶ push deletes
             ──moved─▶ find_moved: new key created, old record deleted (push)
    push     ──college/adult/excluded──▶ mark_retiring retireCount+1 ──(RETIRE_LIMIT)──▶ push deletes

Every write goes through `lock()`: two pushes sharing this file would
otherwise overwrite each other's entries and the next run would create
twins. A ledger that fails to parse is an error, never an empty ledger,
for the same reason.
"""
from __future__ import annotations

import fcntl
import json
import math
import os
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any, Iterator

from .config import LEDGER_PATH
from .schema import base_key

# Two listings of one tournament rarely share a name across sites, but they
# do share a gym and a weekend.
NEAR_KM = 2.0
NEAR_DAYS = 2
# A city-level geocode can sit a few kilometres from the real gym; within
# this radius on the same day the listing is worth a look, not a skip.
MAYBE_KM = 6.0


class LedgerError(RuntimeError):
    """The ledger cannot be trusted; nothing should be pushed until it can."""


class LedgerLocked(LedgerError):
    """Another push, collect or exclude is running."""


def load() -> dict[str, Any]:
    if not LEDGER_PATH.exists():
        return {}
    text = LEDGER_PATH.read_text()
    if not text.strip():
        raise LedgerError(f"{LEDGER_PATH} is empty; restore it with git checkout before pushing")
    try:
        entries = json.loads(text)
    except json.JSONDecodeError as error:
        raise LedgerError(
            f"{LEDGER_PATH} is not valid JSON ({error}); restore it with git checkout before pushing"
        ) from error
    if not isinstance(entries, dict):
        raise LedgerError(f"{LEDGER_PATH} is not a JSON object")
    return entries


def save(entries: dict[str, Any]) -> None:
    """Write the whole file, or none of it: a crash mid-write must not
    leave a half file behind that the next run would read as empty."""
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, LEDGER_PATH)


@contextmanager
def lock() -> Iterator[None]:
    """Hold the ledger for the life of a process that writes it.

    Refuses rather than waits: a second push started by mistake should say
    so and stop, not queue up behind the first and then re-push.
    """
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    path = LEDGER_PATH.with_suffix(".json.lock")
    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise LedgerLocked(
            f"{path} is held by another run (a push, collect or exclude); wait for it to finish"
        )
    try:
        handle.write(str(os.getpid()))
        handle.flush()
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


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
        # base_key drops the ":<id>" a disambiguated twin carries.
        if base_key(other).endswith(f":{name_slug}:{day}"):
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
# A scrape that returns fewer than this share of what the ledger holds for
# the source is a broken scrape, not a wave of cancellations.
PARTIAL_SCRAPE_FRACTION = 0.6


def _source_of(entry: dict[str, Any]) -> str:
    return entry["sourceKey"].split(":", 1)[0]


def upcoming_keys(source: str, today: str) -> set[str]:
    """Distinct source keys this source has pushed for days not yet past."""
    return {
        entry["sourceKey"] for entry in load().values()
        if _source_of(entry) == source and entry.get("date") and entry["date"] >= today[:10]
    }


def looks_partial(source: str, seen_count: int, today: str) -> tuple[bool, int]:
    """(True, expected) when this run saw far fewer listings than the ledger
    expects. Counting misses on such a run would cancel real events."""
    expected = len(upcoming_keys(source, today))
    if expected == 0:
        return False, 0
    return seen_count < PARTIAL_SCRAPE_FRACTION * expected, expected


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


# --- Pushed events a later run sets aside for good ------------------------------
# Reclassified as college or adult, or excluded by hand. One classification
# can be a fluke (the detail text that carried the youth marker failed to
# load), so like a miss it has to happen twice running. An exclusion is a
# person's decision and takes effect at once.
RETIRE_LIMIT = 2


def mark_retiring(source_key: str, environment: str, reason: str) -> int:
    """Count one more run that wants this entry gone. Returns the count."""
    entries = load()
    entry = entries.get(entry_key(source_key, environment))
    if entry is None:
        return 0
    if reason.startswith("excluded:"):
        entry["retireCount"] = RETIRE_LIMIT
    else:
        entry["retireCount"] = entry.get("retireCount", 0) + 1
    entry["retireReason"] = reason
    save(entries)
    return entry["retireCount"]


def clear_retiring(source_keys: set[str], environment: str) -> None:
    """An event pushed again as a youth event is no longer on its way out."""
    entries = load()
    changed = False
    for key in source_keys:
        entry = entries.get(entry_key(key, environment))
        if entry and "retireCount" in entry:
            entry.pop("retireCount", None)
            entry.pop("retireReason", None)
            changed = True
    if changed:
        save(entries)


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
        if old_day and old_day != day and old_day >= today[:10] and base_key(key).endswith(f":{name_slug}:{old_day}"):
            found.append(key)
    return found
