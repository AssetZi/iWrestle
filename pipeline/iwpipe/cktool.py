"""The CloudKit record an event becomes, and the client that writes it.

The fields file format is cktool's (`xcrun cktool create-record`), kept
because it is the documented, typed shape and the tests pin it against
Event.Field in the app. Writes go through the REST client in ckws.py with
a server-to-server key; cktool's own write path needed a browser-session
token that lapsed in thirty minutes, and was removed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import requests

from . import ckws
from .config import (
    ADMIN_RECORD_NAME,
    CLOUDKIT_KEY_PATH,
    cloudkit_key_id,
    CONTAINER_ID,
    RECORD_TYPE,
)

DEVELOPMENT = "development"
PRODUCTION = "production"


class NoWriteAccess(RuntimeError):
    """No server-to-server key is configured for this environment."""


# cktool names stringType, int64Type, timestampType, assetType and
# assetListType in its own docs but not the location or reference encodings.
# These two were confirmed against the development database on the first
# push: the record came back with the coordinates and the admin reference
# intact, matching records the app itself writes.
def _reference_value() -> Any:
    return {"recordName": ADMIN_RECORD_NAME, "action": "NONE"}


def _location_value(latitude: float, longitude: float) -> Any:
    return {"latitude": latitude, "longitude": longitude}


def build_fields(event: dict[str, Any]) -> dict[str, Any]:
    """The typed fields, mirroring createEvent in the app.

    Keys match Event.Field in iWrestle/Models/Event.swift. `registration` is
    omitted when empty, exactly as CloudKitEventCRUD.createEvent does.
    """
    location = event["location"]
    contact = event["contact"]

    fields: dict[str, Any] = {
        "userID": {
            "type": "referenceType",
            "value": _reference_value(),
        },
        "eventType": {"type": "stringType", "value": event["eventType"]},
        "name": {"type": "stringType", "value": event["name"]},
        "date": {"type": "timestampType", "value": event["date"]},
        "location": {
            "type": "locationType",
            "value": _location_value(
                location["latitude"], location["longitude"]
            ),
        },
        "address": {"type": "stringType", "value": event["address"]},
        "ageGroups": {"type": "stringListType", "value": event["ageGroups"]},
        "logo": {"type": "assetType", "value": "LOGO"},
        "flyer": {"type": "assetType", "value": "FLYER"},
        "eventContactFirstName": {
            "type": "stringType", "value": contact["firstName"],
        },
        "eventContactLastName": {
            "type": "stringType", "value": contact["lastName"],
        },
        "eventContactEmail": {"type": "stringType", "value": contact["email"]},
        # Phone is optional in the app's UI, but the App Store build's
        # Event.init?(safeRecord:) still requires the field to exist, so an
        # empty string is written rather than omitting it.
        "eventContactPhone": {
            "type": "stringType", "value": contact.get("phone") or "",
        },
    }

    if event.get("registration"):
        fields["registration"] = {
            "type": "stringType", "value": event["registration"],
        }
    return fields


def content_hash(fields: dict[str, Any], logo_path: Path, flyer_path: Path) -> str:
    """What was pushed, in one string, so a later run can tell if it changed.

    The flyer bytes are part of it, which only works because the renderer
    is invariant (assets.py): the same event renders to the same bytes.
    """
    digest = hashlib.sha256()
    digest.update(json.dumps(fields, sort_keys=True).encode())
    for path in (logo_path, flyer_path):
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.exists() else b"-")
    return digest.hexdigest()[:16]


# --- Backend ------------------------------------------------------------------

def rest_client(environment: str) -> ckws.Client | None:
    """The REST client when a server-to-server key is configured, else None."""
    key_id = cloudkit_key_id(environment)
    if not key_id or not CLOUDKIT_KEY_PATH.exists():
        return None
    return ckws.Client(CLOUDKIT_KEY_PATH, key_id, CONTAINER_ID, environment)


def require_client(environment: str) -> ckws.Client:
    client = rest_client(environment)
    if client is None:
        which = "CLOUDKIT_KEY_ID_PRODUCTION" if environment == PRODUCTION else "CLOUDKIT_KEY_ID"
        raise NoWriteAccess(
            f"no server-to-server key for {environment}: set {which} in pipeline/.env "
            f"and put the key at {CLOUDKIT_KEY_PATH}"
        )
    return client


def backend_name(environment: str = DEVELOPMENT) -> str:
    return f"CloudKit REST (server-to-server key, {environment})"


def create_record(
    client: ckws.Client, fields: dict[str, Any], logo_path: Path, flyer_path: Path
) -> str:
    """Upload both assets, then create the record that points at them."""
    uploaded = {
        "LOGO": client.upload_asset(RECORD_TYPE, "logo", logo_path),
        "FLYER": client.upload_asset(RECORD_TYPE, "flyer", flyer_path),
    }
    try:
        return client.create_record(RECORD_TYPE, ckws.to_ckws_fields(fields, uploaded))
    except (ckws.CKWSError, requests.RequestException) as error:
        # A timeout or 5xx after the server committed the record would be
        # reported as a failure, and the retry would create a twin. Look
        # for the record before giving up; the first production push left
        # 43 such twins behind.
        name = fields.get("name", {}).get("value", "")
        day = str(fields.get("date", {}).get("value", ""))[:10]
        existing = None
        if name and day:
            try:
                existing = client.find_record(RECORD_TYPE, name, day)
            except (ckws.CKWSError, requests.RequestException) as lookup_error:
                print(f"    could not check for an existing record: {str(lookup_error)[:80]}")
        if existing:
            print(f"    create errored but the record exists; adopting {existing[:8]}")
            return existing
        raise ckws.CKWSError(str(error)) from error
