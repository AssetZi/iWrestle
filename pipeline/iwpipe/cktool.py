"""Apple's cktool, wrapped.

`xcrun cktool` is the supported way to write CloudKit records from outside an
app. It ships with Xcode, so this only runs on this Mac. Authorization comes
from a token saved once with `xcrun cktool save-token --type user`.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .config import (
    ADMIN_RECORD_NAME,
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
        "eventContactPhone": {"type": "stringType", "value": contact["phone"]},
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
        for field in fields or []:
            args += ["--requested-fields", field]
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
