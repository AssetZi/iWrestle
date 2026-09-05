"""FloWrestling, through the schedule API its own site calls.

Flo owns Trackwrestling, so this is the national backbone: its search
endpoint has no date window and lists most Track events too. The public
pages return 406 to plain HTTP clients, but the API host does not, so no
browser is needed. Coordinates come with every event, so none of these
need geocoding; the event-hub record adds the organizer contact, the
street address, the club's website and a registration link.

Endpoints, found by watching the site's own traffic and probing:

    POST /api/schedule/events/search   {"tz","query","limit"<=100,"offset"}
        -> {"data":[{"date","events":[...]}],"meta":{"total","hasMore"}}
    GET  /api/event-hub/{coreId}        (coreId is in each event's url)

`POST /api/schedule/events` (the listing) is stuck to about a week and
ignores its cursor, so it is only kept for the fixture-based tests.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

from ..config import DATA_DIR, EVENT_TZ, MONTHS_AHEAD
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

# Search needs a non-empty query and has no date window; the union of
# these covers essentially every event name in the country.
QUERIES = ["a", "e", "i", "o", "u", "y", "2", "wrestl"]
PAGE = 100
MAX_OFFSET = 5000

DETAIL_CACHE_PATH = DATA_DIR / "flo-details.json"
DETAIL_TTL_DAYS = 30

# Flo shows its own branded still for events with no logo of their own.
# Putting another company's mark on an iWrestle event would be misleading,
# so these fall through to the monogram tile instead.
GENERIC_LOGOS = ("Wrestling-Logo-Overlay", "/images/gb_")

API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": SITE,
    "Referer": SITE + "/",
}

CORE_ID = re.compile(r"/events/(\d+)/")
HREF = re.compile(r'href="([^"]+)"')


# --- HTTP ----------------------------------------------------------------------

def _post(session: requests.Session, path: str, body: dict[str, Any]) -> dict[str, Any]:
    response = session.post(f"{API}/{path}", headers=API_HEADERS, json=body, timeout=30)
    response.raise_for_status()
    return response.json()


def _get(session: requests.Session, url: str) -> dict[str, Any] | None:
    try:
        response = session.get(url, headers=API_HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def detail_url(core_id: str) -> str:
    # The event-hub lives beside /schedule, not under it.
    return f"{API_ROOT}/event-hub/{core_id}"


# --- Listing -------------------------------------------------------------------

def _events_of(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for day in payload.get("data", []) for e in day.get("events", [])]


def search(session: requests.Session, query: str, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
    """One page of the national search: (events, total matches)."""
    payload = _post(session, "events/search", {
        "tz": EVENT_TZ, "query": query, "limit": PAGE, "offset": offset,
    })
    return _events_of(payload), int((payload.get("meta") or {}).get("total") or 0)


def enumerate_all(session: requests.Session, queries: list[str] | None = None) -> list[dict[str, Any]]:
    """Every event the search can reach, once each, in listing order."""
    seen: dict[str, dict[str, Any]] = {}
    for query in queries or QUERIES:
        offset = 0
        while offset < MAX_OFFSET:
            events, total = search(session, query, offset)
            if not events:
                break
            for item in events:
                seen.setdefault(item.get("id") or item["name"], item)
            offset += PAGE
            if offset >= total:
                break
    return list(seen.values())


def search_by_name(session: requests.Session, name: str, day: str) -> dict[str, Any] | None:
    """The Flo record for an event another site lists, matched by name and day.

    Used by the Trackwrestling collector: when Flo has the event, Flo's
    version wins because it carries the contact and a real page.
    """
    query = re.sub(r"[^a-z0-9 ]", " ", name.lower()).strip()
    query = " ".join(query.split()[:4]) or name
    try:
        events, _ = search(session, query)
    except Exception:
        return None
    wanted = datetime.fromisoformat(day).date() if day else None
    for item in events:
        if not wanted or not item.get("startTime"):
            continue
        start = datetime.fromisoformat(item["startTime"].replace("Z", "+00:00")).date()
        if abs((start - wanted).days) <= 1 and _same_event(name, item["name"]):
            return item
    return None


def _same_event(a: str, b: str) -> bool:
    def words(text: str) -> set[str]:
        return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return False
    overlap = len(wa & wb) / min(len(wa), len(wb))
    return overlap >= 0.6


def fetch_region(session: requests.Session, region: str) -> list[dict[str, Any]]:
    """The week-window listing for one state; kept for fixtures and tests."""
    payload = _post(session, "events", {
        "tz": EVENT_TZ, "limit": PAGE,
        "filters": [{"id": "administrative-region", "value": REGIONS[region]}],
    })
    return _events_of(payload)


# --- Details -------------------------------------------------------------------

def _load_detail_cache() -> dict[str, Any]:
    if DETAIL_CACHE_PATH.exists():
        try:
            return json.loads(DETAIL_CACHE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_detail_cache(cache: dict[str, Any]) -> None:
    DETAIL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DETAIL_CACHE_PATH.write_text(json.dumps(cache, indent=1, sort_keys=True))


def fetch_detail(session: requests.Session, core_id: str, cache: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """GET /api/event-hub/{coreId}: contact, full address, organizer site.

    Details rarely change, so they are cached on disk for DETAIL_TTL_DAYS;
    the first national run is the only expensive one.
    """
    now = datetime.now(timezone.utc)
    if cache is not None and core_id in cache:
        entry = cache[core_id]
        fetched = datetime.fromisoformat(entry.get("fetchedAt", "1970-01-01T00:00:00+00:00"))
        if now - fetched < timedelta(days=DETAIL_TTL_DAYS):
            return entry.get("data")
    payload = _get(session, detail_url(core_id))
    data = (payload or {}).get("data") if payload else None
    if cache is not None and data is not None:
        cache[core_id] = {"fetchedAt": now.isoformat(timespec="seconds"), "data": data}
    return data


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

    if detail.get("description"):
        event["detailText"] = (detail["description"] or "")[:3000]


# --- Mapping to the pipeline's event -------------------------------------------

def _to_event(item: dict[str, Any]) -> dict[str, Any] | None:
    location = item.get("location") or {}
    coordinates = location.get("coordinates") or {}
    if not item.get("name") or not item.get("startTime"):
        return None

    event = blank_event(SOURCE)
    event["name"] = item["name"]
    event["floId"] = item.get("id")
    event["sourceUrl"] = item.get("url") or ""
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
    event["venue"] = location.get("venueName") or ""
    event["region"] = location.get("region") or ""

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


def _in_window(item: dict[str, Any], today: datetime) -> bool:
    try:
        start = datetime.fromisoformat(item["startTime"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return False
    return today - timedelta(days=1) <= start <= today + timedelta(days=30 * MONTHS_AHEAD)


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
    elif regions:
        raw = [item for region in regions for item in fetch_region(session, region)]
    else:
        raw = enumerate_all(session)

    today = datetime.now(timezone.utc)
    cache = _load_detail_cache() if not fixture else None
    events: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        for item in raw:
            if not fixture and not _in_window(item, today):
                continue
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
                detail = fetch_detail(session, core.group(1), cache) if core else None
                if detail:
                    apply_detail(event, detail)
                else:
                    note(event, "event details unavailable")
            events.append(event)
            if limit and len(events) >= limit:
                break
    finally:
        if cache is not None:
            _save_detail_cache(cache)
    return events
