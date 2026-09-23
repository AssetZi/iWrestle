"""CloudKit Web Services, signed with a server-to-server key.

cktool's user token is a browser session: it lapses in thirty minutes, or
two weeks if you remember to tick a box, which is no way to run a job on
the 1st and 15th. A server-to-server key never expires and reaches exactly
what this pipeline needs, the public database.

Every request carries three headers and a signature over

    <ISO8601 date>:<base64 sha256 of the body>:<url subpath>

made with an ECDSA P-256 key whose public half is registered in the
CloudKit Console. Signatures are good for ten minutes, so the clock has to
be right.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

HOST = "https://api.apple-cloudkit.com"
VERSION = "1"
DATABASE = "public"


class CKWSError(RuntimeError):
    """CloudKit refused a request; the message carries its reason."""


def load_key(path: Path) -> ec.EllipticCurvePrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise CKWSError(f"{path} is not an EC private key")
    return key


def iso_now() -> str:
    """The date format CloudKit signs over: UTC, seconds, no fraction."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def body_hash(body: bytes) -> str:
    return base64.b64encode(hashlib.sha256(body).digest()).decode("ascii")


def subpath(container: str, environment: str, operation: str) -> str:
    return f"/database/{VERSION}/{container}/{environment}/{DATABASE}/{operation}"


def sign(key: ec.EllipticCurvePrivateKey, date: str, body: bytes, path: str) -> str:
    message = f"{date}:{body_hash(body)}:{path}".encode("utf-8")
    signature = key.sign(message, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode("ascii")


class Client:
    """One container, one environment, one key."""

    def __init__(
        self, key_path: Path, key_id: str, container: str, environment: str,
        session: requests.Session | None = None,
    ):
        self.key = load_key(key_path)
        self.key_id = key_id
        self.container = container
        self.environment = environment
        self.session = session or requests.Session()

    def post(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = subpath(self.container, self.environment, operation)
        body = json.dumps(payload).encode("utf-8")
        date = iso_now()
        headers = {
            "Content-Type": "application/json",
            "X-Apple-CloudKit-Request-KeyID": self.key_id,
            "X-Apple-CloudKit-Request-ISO8601Date": date,
            "X-Apple-CloudKit-Request-SignatureV1": sign(self.key, date, body, path),
        }
        response = self.session.post(HOST + path, data=body, headers=headers, timeout=60)
        if response.status_code != 200:
            raise CKWSError(
                f"{operation} failed ({response.status_code}): {response.text[:400]}"
            )
        return response.json()

    # --- Assets -------------------------------------------------------------

    def upload_asset(self, record_type: str, field: str, file_path: Path) -> dict[str, Any]:
        """Two steps: ask for a URL, PUT the bytes, keep the receipt.

        The returned dictionary is what goes in the record's asset field.
        """
        tokens = self.post("assets/upload", {
            "tokens": [{"recordType": record_type, "fieldName": field}],
        })
        try:
            url = tokens["tokens"][0]["url"]
        except (KeyError, IndexError) as error:
            raise CKWSError(f"no upload url for {field}: {tokens}") from error

        # The upload URL is already authorized; it takes no signature.
        response = self.session.post(
            url, data=Path(file_path).read_bytes(),
            headers={"Content-Type": "application/octet-stream"}, timeout=120,
        )
        if response.status_code != 200:
            raise CKWSError(
                f"asset upload for {field} failed ({response.status_code}): {response.text[:200]}"
            )
        single = response.json().get("singleFile")
        if not single:
            raise CKWSError(f"asset upload for {field} returned no file: {response.text[:200]}")
        return single

    # --- Records ------------------------------------------------------------

    def create_record(self, record_type: str, fields: dict[str, Any]) -> str:
        """Create one record; returns its record name."""
        payload = {"operations": [{
            "operationType": "create",
            "record": {"recordType": record_type, "fields": fields},
        }]}
        answer = self.post("records/modify", payload)
        records = answer.get("records") or []
        if not records or "serverErrorCode" in records[0]:
            raise CKWSError(f"create failed: {json.dumps(answer)[:400]}")
        return records[0]["recordName"]

    def change_tag(self, record_name: str) -> str | None:
        """The record's current version, which a delete has to quote."""
        answer = self.post("records/lookup", {
            "records": [{"recordName": record_name}],
        })
        record = (answer.get("records") or [{}])[0]
        if record.get("serverErrorCode"):
            return None
        return record.get("recordChangeTag")

    def find_record(self, record_type: str, name: str, day: str) -> str | None:
        """The record name of an event with this name on this day, if any.

        Used after a create that errored on the client: CloudKit may well
        have committed it, and creating again would leave a duplicate.
        """
        from datetime import datetime, timedelta, timezone

        start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        answer = self.post("records/query", {
            "query": {
                "recordType": record_type,
                "filterBy": [
                    {"fieldName": "name", "comparator": "EQUALS", "fieldValue": {"value": name}},
                    {"fieldName": "date", "comparator": "GREATER_THAN_OR_EQUALS",
                     "fieldValue": {"value": int(start.timestamp() * 1000)}},
                    {"fieldName": "date", "comparator": "LESS_THAN",
                     "fieldValue": {"value": int(end.timestamp() * 1000)}},
                ],
            },
            "resultsLimit": 5, "desiredKeys": ["name"],
        })
        records = [r for r in answer.get("records") or [] if not r.get("serverErrorCode")]
        return records[0]["recordName"] if records else None

    def delete_record(self, record_name: str) -> None:
        """Delete by name. A record that is already gone is not an error."""
        tag = self.change_tag(record_name)
        if tag is None:
            return
        answer = self.post("records/modify", {"operations": [{
            "operationType": "forceDelete",
            "record": {"recordName": record_name, "recordChangeTag": tag},
        }]})
        records = answer.get("records") or []
        if records and records[0].get("serverErrorCode") not in (None, "NOT_FOUND"):
            raise CKWSError(f"delete failed: {json.dumps(answer)[:300]}")

    def ping(self) -> int:
        """One page, no paging: is the key accepted? Returns records seen."""
        answer = self.post("records/query", {
            "query": {"recordType": "Event"}, "resultsLimit": 1,
            "desiredKeys": ["name"],
        })
        return len(answer.get("records") or [])

    def query_records(self, record_type: str, desired: list[str] | None = None,
                      limit: int = 200, max_records: int | None = None) -> list[dict[str, Any]]:
        """Records of a type, following continuation markers.

        max_records stops early; without it this walks the whole database,
        which for a national directory is thousands of round trips.
        """
        found: list[dict[str, Any]] = []
        marker = None
        while True:
            query: dict[str, Any] = {
                "query": {"recordType": record_type},
                "resultsLimit": limit,
            }
            if desired:
                query["desiredKeys"] = desired
            if marker:
                query["continuationMarker"] = marker
            answer = self.post("records/query", query)
            found.extend(answer.get("records") or [])
            marker = answer.get("continuationMarker")
            if not marker or (max_records is not None and len(found) >= max_records):
                return found


# --- Field translation ---------------------------------------------------------

def _timestamp_ms(iso: str) -> int:
    stamp = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return int(stamp.timestamp() * 1000)


def to_ckws_fields(
    fields: dict[str, Any], assets: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """cktool's typed fields -> the shape the REST API wants.

    Web services infers most types from the JSON value, so the wrapper is
    just {"value": ...}. Timestamps go to milliseconds since the epoch, and
    an asset field carries the receipt from upload_asset instead of a key.
    """
    assets = assets or {}
    out: dict[str, Any] = {}
    for name, field in fields.items():
        kind, value = field.get("type"), field.get("value")
        if kind == "assetType":
            uploaded = assets.get(value)
            if uploaded is None:
                raise CKWSError(f"no uploaded asset for {name} (key {value})")
            out[name] = {"value": uploaded}
        elif kind == "timestampType":
            out[name] = {"value": _timestamp_ms(value)}
        else:
            # stringType, stringListType, locationType and referenceType all
            # pass their JSON through unchanged.
            out[name] = {"value": value}
    return out
