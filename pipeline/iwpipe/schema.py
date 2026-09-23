"""The normalized event record the whole pipeline passes around.

Events live as plain dicts so a human can open the JSON and edit it during
review. This module owns the shape, the natural key, and validation.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SCHEMA_VERSION

AGE_GROUPS = ["Novice", "Youth", "Jr High", "High School", "Open"]
EVENT_TYPES = ["tournament", "camp", "clinic", "Duals"]

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_SKIP = "skip"


def slug(text: str) -> str:
    """Lowercase ASCII slug used in natural keys and asset paths."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower())
    return cleaned.strip("-")


def source_key(source: str, name: str, iso_date: str) -> str:
    """Stable identity for an event: source, name slug, calendar day.

    The day comes from the UTC timestamp, which is what gets pushed, so the
    key is reproducible from the stored record alone.
    """
    day = (iso_date or "")[:10]
    return f"{source}:{slug(name)}:{day}"


def base_key(key: str) -> str:
    """The natural key without the ":<id>" suffix disambiguate_keys adds.

    "flowrestling:x-y:2026-11-18:2gPX" -> "flowrestling:x-y:2026-11-18".
    """
    parts = key.split(":")
    return ":".join(parts[:3]) if len(parts) > 3 else key


# Notes collect leaves when no source gave a contact email. Enrichment and
# the flyer reader remove them when they find a real one.
DEFAULT_EMAIL_NOTES = (
    "default contact email",
    "placeholder contact email: set a real DEFAULT_CONTACT_EMAIL in .env",
    "no contact email: set DEFAULT_CONTACT_EMAIL in .env",
)


def is_default_email(email: str) -> bool:
    """Empty, the .env fallback, or an example.com placeholder."""
    from . import config

    return not email or email == config.DEFAULT_CONTACT_EMAIL or email.endswith("example.com")


def drop_notes(event: dict[str, Any], texts) -> None:
    notes = event.setdefault("review", {}).setdefault("notes", [])
    event["review"]["notes"] = [n for n in notes if n not in texts]


def blank_event(source: str) -> dict[str, Any]:
    return {
        "sourceKey": "",
        "sourceUrl": "",
        "source": source,
        "name": "",
        "eventType": "tournament",
        "date": None,
        "address": "",
        "location": None,
        "ageGroups": [],
        "registration": "",
        "contact": {"firstName": "", "lastName": "", "email": "", "phone": ""},
        "logo": None,
        "flyer": {"url": None, "path": None},
        "review": {"status": STATUS_PENDING, "notes": []},
    }


def note(event: dict[str, Any], text: str) -> None:
    """Record a reviewer-facing flag without duplicating it."""
    notes = event.setdefault("review", {}).setdefault("notes", [])
    if text not in notes:
        notes.append(text)


def validate(event: dict[str, Any]) -> list[str]:
    """Return the reasons this event cannot be pushed yet.

    Mirrors Event.init?(safeRecord:) in iWrestle/Models/Event.swift: a record
    missing any of these is silently dropped from every fetch in the app.
    """
    problems: list[str] = []

    if not event.get("name", "").strip():
        problems.append("missing name")
    if event.get("eventType") not in EVENT_TYPES:
        problems.append(f"bad eventType {event.get('eventType')!r}")
    if not event.get("date"):
        problems.append("missing date")
    if not event.get("address", "").strip():
        problems.append("missing address")

    location = event.get("location")
    if not isinstance(location, dict) or location.get("latitude") is None:
        problems.append("missing location")
    elif not (-90 <= location["latitude"] <= 90 and -180 <= location.get("longitude", 999) <= 180):
        # CloudKit rejects these outright; Flo sometimes swaps the two.
        problems.append("coordinates out of range")

    groups = event.get("ageGroups") or []
    if not groups:
        problems.append("missing ageGroups")
    for group in groups:
        if group not in AGE_GROUPS:
            problems.append(f"bad ageGroup {group!r}")

    # Phone is optional: the app hides an empty row. It is still written as ""
    # because the shipping build's decode guard needs the field to exist.
    contact = event.get("contact") or {}
    for field in ("firstName", "lastName", "email"):
        if not str(contact.get(field, "")).strip():
            problems.append(f"missing contact.{field}")

    if not event.get("logo"):
        problems.append("missing logo")
    if not (event.get("flyer") or {}).get("path"):
        problems.append("missing flyer")

    return problems


def is_pushable(event: dict[str, Any]) -> bool:
    return (
        event.get("review", {}).get("status") == STATUS_APPROVED
        and not validate(event)
    )


def dump(path: Path, source: str, events: list[dict[str, Any]]) -> None:
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "source": source,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "events": events,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(
            f"{path} is schemaVersion {payload.get('schemaVersion')}, "
            f"expected {SCHEMA_VERSION}"
        )
    return payload


def disambiguate_keys(events: list[dict[str, Any]]) -> int:
    """Give events that collapsed to one natural key distinct, stable keys.

    Flo lists a dual meet's men's and women's (or varsity and JV) matches
    under the same name and day; with one key they replaced each other's
    record on every push. The event with the smallest stable id keeps the
    plain key, so existing ledger entries stay valid; the rest get the id
    appended. Returns how many keys were changed.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        groups.setdefault(event["sourceKey"], []).append(event)

    changed = 0
    for key, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=_stable_id)
        for event in members[1:]:
            event["sourceKey"] = f"{key}:{_stable_id(event)}"
            note(event, "same name and day as another listing here; kept both")
            changed += 1
    return changed


def _stable_id(event: dict[str, Any]) -> str:
    for field in ("floId", "trackId"):
        if event.get(field):
            return str(event[field])
    import hashlib

    return hashlib.sha1((event.get("sourceUrl") or event.get("name", "")).encode()).hexdigest()[:8]
