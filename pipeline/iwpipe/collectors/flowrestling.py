"""FloWrestling, through the schedule API its own site calls.

The public pages return 406 to plain HTTP clients, but the API host does
not, so no browser is needed. The API is better than the HTML anyway: it
returns coordinates and a logo URL, so these events need no geocoding.

Request shape was found by watching the site's own network traffic:

    POST https://prod-web-api.flowrestling.org/api/schedule/events
    {"tz": "...", "limit": 100, "filters": [{"id": "...", "value": "..."}],
     "cursor": "<meta.nextCursor from the previous page>"}
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from ..config import EVENT_TZ
from ..schema import blank_event, note

SOURCE = "flowrestling"
API_ROOT = "https://prod-web-api.flowrestling.org/api"
API = f"{API_ROOT}/schedule"
SITE = "https://www.flowrestling.org"

# From POST /api/schedule/filters/administrative-region.
REGIONS = {
    "PA": "29USPA00000000000",
    "OH": "29USOH00000000000",
    "NY": "29USNY00000000000",
    "NJ": "29USNJ00000000000",
}
DEFAULT_REGIONS = ["PA"]

MAX_LIMIT = 100
MAX_PAGES = 12

# Flo shows its own branded still for events with no logo of their own.
# Putting another company's mark on an iWrestle event would be misleading,
# so these fall through to the monogram tile instead.
GENERIC_LOGOS = ("Wrestling-Logo-Overlay",)

API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": SITE,
    "Referer": SITE + "/",
}


CORE_ID = re.compile(r"/events/(\d+)/")
HREF = re.compile(r'href="([^"]+)"')


def detail_url(core_id: str) -> str:
    # The event-hub lives beside /schedule, not under it.
    return f"{API_ROOT}/event-hub/{core_id}"


def _get(session: requests.Session, url: str) -> dict[str, Any] | None:
    try:
        response = session.get(url, headers=API_HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def fetch_detail(session: requests.Session, core_id: str) -> dict[str, Any] | None:
    """GET /api/event-hub/{coreId}: contact, full address, organizer site."""
    payload = _get(session, detail_url(core_id))
    return (payload or {}).get("data") if payload else None


def _website_from(descriptions: list[dict[str, Any]]) -> str:
    for item in descriptions or []:
        match = HREF.search(item.get("description") or "")
        if match:
            url = match.group(1).strip()
            if url.startswith("//"):
                url = "https:" + url
            elif not url.startswith("http"):
                url = "https://" + url
            scheme, _, rest = url.partition("://")
            host, slash, path = rest.partition("/")
            return f"{scheme}://{host.lower()}{slash}{path}"
    return ""


def apply_detail(event: dict[str, Any], detail: dict[str, Any]) -> None:
    """Fold the event-hub record into an event from the listing."""
    contact = detail.get("eventContact") or {}
    if contact.get("email") and not event["contact"].get("email"):
        event["contact"]["email"] = contact["email"].strip()
    name = (contact.get("name") or "").strip()
    if name and not event["contact"].get("firstName"):
        first, _, last = name.rpartition(" ")
        role_word = re.search(
            r"(team|club|admin|wrestling|group|inc|director|coordinator|staff|committee|tbd|office)",
            name, re.I,
        )
        if first and not role_word:
            event["contact"]["firstName"], event["contact"]["lastName"] = first, last
        else:
            event["contact"]["firstName"], event["contact"]["lastName"] = name, "(Organizer)"
        event["organizer"] = event.get("organizer") or name

    address = (detail.get("location") or {}).get("address") or {}
    venue = (detail.get("location") or {}).get("name") or ""
    parts = [venue, address.get("line1"), address.get("city"),
             " ".join(filter(None, [address.get("state"), address.get("zipCode")]))]
    full = ", ".join(p for p in parts if p)
    if address.get("line1") and full:
        event["address"] = full

    site = _website_from(detail.get("subEventDescriptions") or [])
    if site and not event.get("organizerWebsite"):
        event["organizerWebsite"] = site

    registration = detail.get("registration") or {}
    if isinstance(registration, dict) and registration.get("url") and not event.get("registration"):
        event["registration"] = registration["url"]


def _post(session: requests.Session, path: str, body: dict[str, Any]) -> dict[str, Any]:
    response = session.post(
        f"{API}/{path}", headers=API_HEADERS, json=body, timeout=30
    )
    response.raise_for_status()
    return response.json()


def fetch_region(session: requests.Session, region: str) -> list[dict[str, Any]]:
    """Every scheduled event in one state, following the cursor to the end."""
    base = {
        "tz": EVENT_TZ,
        "limit": MAX_LIMIT,
        "filters": [{"id": "administrative-region", "value": REGIONS[region]}],
    }

    raw: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(MAX_PAGES):
        payload = _post(session, "events", {**base, "cursor": cursor} if cursor else base)
        for day in payload.get("data", []):
            raw.extend(day.get("events", []))

        meta = payload.get("meta") or {}
        next_cursor = meta.get("nextCursor")
        if not meta.get("hasMore") or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return raw


def _to_event(item: dict[str, Any]) -> dict[str, Any] | None:
    location = item.get("location") or {}
    coordinates = location.get("coordinates") or {}
    if not item.get("name") or not item.get("startTime"):
        return None

    event = blank_event(SOURCE)
    event["name"] = item["name"]
    event["sourceUrl"] = item.get("url") or SITE
    event["rawText"] = json.dumps(
        {k: item.get(k) for k in ("name", "status", "daySegmentName")}
    )

    # Already a UTC instant, which is exactly what CloudKit stores.
    event["date"] = item["startTime"].replace(".000Z", "Z")
    if item.get("startTimeTbd"):
        note(event, "start time was TBD at the source")

    parts = [
        location.get("venueName"),
        location.get("city"),
        " ".join(filter(None, [location.get("region")])),
    ]
    event["address"] = ", ".join(part for part in parts if part)

    if coordinates.get("latitude") is not None:
        event["location"] = {
            "latitude": coordinates["latitude"],
            "longitude": coordinates["longitude"],
        }

    registration = item.get("registration") or {}
    if registration.get("url"):
        event["registration"] = registration["url"]

    logo_url = item.get("logoUrl") or ""
    if logo_url and not any(mark in logo_url for mark in GENERIC_LOGOS):
        event["logoUrl"] = logo_url
    elif logo_url:
        note(event, "source logo was a FloWrestling placeholder, using monogram")

    # The API says nothing about divisions, so collect.py's default applies.
    event["divisionsText"] = ""
    event["formatText"] = item.get("daySegmentName") or ""
    note(event, "divisions not published by the source, verify")
    return event


def collect(
    session: requests.Session,
    *,
    fixture: Path | None = None,
    limit: int | None = None,
    dump_unparsed: bool = False,
    regions: list[str] | None = None,
) -> list[dict[str, Any]]:
    if fixture:
        raw = json.loads(Path(fixture).read_text())
    else:
        raw = []
        for region in regions or DEFAULT_REGIONS:
            raw.extend(fetch_region(session, region))

    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        event = _to_event(item)
        if event is None:
            continue
        # A multi-day event appears once per day with the same id.
        identity = item.get("id") or event["name"]
        if identity in seen:
            continue
        seen.add(identity)
        if not fixture:
            core = CORE_ID.search(item.get("url") or "")
            detail = fetch_detail(session, core.group(1)) if core else None
            if detail:
                apply_detail(event, detail)
            else:
                note(event, "event details unavailable")
        events.append(event)
        if limit and len(events) >= limit:
            break
    return events
