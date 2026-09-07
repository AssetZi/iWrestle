"""Apple's cktool, wrapped.

`xcrun cktool` is the supported way to write CloudKit records from outside an
app. It ships with Xcode, so this only runs on this Mac. Authorization comes
from a token saved once with `xcrun cktool save-token --type user`.
"""
from __future__ import annotations

import hashlib
import json
import subprocess

import requests
from pathlib import Path
from typing import Any

from . import ckws
from .config import (
    ADMIN_RECORD_NAME,
    CLOUDKIT_KEY_PATH,
    cloudkit_key_id,
    CONTAINER_ID,
    DATABASE_TYPE,
    RECORD_TYPE,
    TEAM_ID,
)

DEVELOPMENT = "development"
PRODUCTION = "production"


class CKToolError(RuntimeError):
    """A cktool invocation failed; stderr is carried in the message."""


def _run(args: list[str]) -> str:
    process = subprocess.run(
        ["xcrun", "cktool", *args],
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise CKToolError(
            f"cktool {' '.join(args[:2])} failed ({process.returncode}):\n"
            f"{process.stderr.strip() or process.stdout.strip()}"
        )
    return process.stdout


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
    """The fields file cktool consumes, mirroring createEvent in the app.

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


def create_record(
    fields_path: Path,
    logo_path: Path,
    flyer_path: Path,
    environment: str = DEVELOPMENT,
) -> dict[str, Any]:
    """Create one Event record and return cktool's parsed response."""
    output = _run([
        "create-record",
        "--team-id", TEAM_ID,
        "--container-id", CONTAINER_ID,
        "--environment", environment,
        "--database-type", DATABASE_TYPE,
        "--record-type", RECORD_TYPE,
        "--fields-file", str(fields_path),
        "--asset-files", f"LOGO={logo_path}", f"FLYER={flyer_path}",
    ])
    return json.loads(output)


def query_records(
    environment: str = DEVELOPMENT,
    fields: list[str] | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Every Event record in the database, following continuation tokens."""
    records: list[dict[str, Any]] = []
    continuation: str | None = None

    while True:
        args = [
            "query-records",
            "--team-id", TEAM_ID,
            "--container-id", CONTAINER_ID,
            "--environment", environment,
            "--database-type", DATABASE_TYPE,
            "--record-type", RECORD_TYPE,
            "--limit", str(limit),
        ]
        if fields:
            args += ["--requested-fields", *fields]
        if continuation:
            args += ["--continuation-token", continuation]

        payload = json.loads(_run(args))
        records.extend(payload.get("records", []))
        continuation = payload.get("continuationToken")
        if not continuation:
            return records


def delete_record(record_name: str, environment: str = DEVELOPMENT) -> None:
    _run([
        "delete-record",
        "--container-id", CONTAINER_ID,
        "--environment", environment,
        "--database-type", DATABASE_TYPE,
        "--record-name", record_name,
        "--yes",
    ])


def content_hash(fields: dict[str, Any], logo_path: Path, flyer_path: Path) -> str:
    """What was pushed, in one string, so a later run can tell if it changed."""
    digest = hashlib.sha256()
    digest.update(json.dumps(fields, sort_keys=True).encode())
    for path in (logo_path, flyer_path):
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.exists() else b"-")
    return digest.hexdigest()[:16]


# --- Backend selection ---------------------------------------------------------

def rest_client(environment: str) -> ckws.Client | None:
    """The REST client when a server-to-server key is configured, else None.

    cktool needs a user token that expires within hours; the key behind this
    client never does, which is what lets the routine run unattended.
    """
    key_id = cloudkit_key_id(environment)
    if not key_id or not CLOUDKIT_KEY_PATH.exists():
        return None
    return ckws.Client(CLOUDKIT_KEY_PATH, key_id, CONTAINER_ID, environment)


def backend_name(environment: str = DEVELOPMENT) -> str:
    if cloudkit_key_id(environment):
        return f"CloudKit REST (server-to-server key, {environment})"
    return "cktool (user token)"


def create_record_rest(
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
        try:
            existing = client.find_record(RECORD_TYPE, name, day) if name and day else None
        except Exception:
            existing = None
        if existing:
            print(f"    create errored but the record exists; adopting {existing[:8]}")
            return existing
        raise ckws.CKWSError(str(error)) from error
