"""Address -> latitude/longitude via Nominatim, cached on disk.

The app filters by CloudKit's distanceToLocation:, so a missing or wrong
coordinate hides the event entirely. Results are cached in
data/geocache.json and committed, so reruns cost nothing and the pipeline
stays reproducible offline.
"""
from __future__ import annotations

import json
from typing import Any

import requests

from .config import GEOCACHE_PATH, NOMINATIM_EMAIL
from .http import get

ENDPOINT = "https://nominatim.openstreetmap.org/search"

# Nominatim's usage policy refuses clients that pose as a browser, so these
# replace the shared session's browser-shaped headers for this one host.
HEADERS = {
    "User-Agent": "iWrestle-events-pipeline/1.0 (wrestling event directory)",
    "Accept": "application/json",
    "Upgrade-Insecure-Requests": None,
}

# Set when Nominatim refuses a request or answers with something other than
# results. The rest of this process (one source's collect) reads the cache
# and asks nothing more.
_unavailable = False


class Unavailable(Exception):
    """Nominatim gave no usable answer; says nothing about the address."""

# Coordinate precision that still resolves a city; enough for a mile filter.
CITY_LEVEL_TYPES = {"city", "town", "village", "municipality", "administrative"}


def _load_cache() -> dict[str, Any]:
    if GEOCACHE_PATH.exists():
        try:
            return json.loads(GEOCACHE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict[str, Any]) -> None:
    GEOCACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GEOCACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


def _normalize(address: str) -> str:
    return " ".join(address.lower().split())


def _query(session: requests.Session, text: str) -> dict[str, Any] | None:
    params = {"q": text, "format": "jsonv2", "limit": 1, "countrycodes": "us"}
    if NOMINATIM_EMAIL:
        params["email"] = NOMINATIM_EMAIL
    try:
        response = get(session, ENDPOINT, params=params, headers=HEADERS)
    except requests.HTTPError as error:
        status = getattr(error.response, "status_code", None)
        raise Unavailable(f"HTTP {status}" if status else "request refused") from error
    except (requests.RequestException, RuntimeError) as error:
        raise Unavailable("no answer after retries") from error
    try:
        results = response.json()
        if not results:
            return None
        hit = results[0]
        return {
            "latitude": float(hit["lat"]),
            "longitude": float(hit["lon"]),
            "confidence": "city" if hit.get("type") in CITY_LEVEL_TYPES else "precise",
            "matched": hit.get("display_name", ""),
        }
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        # A block page, an error object, or a result without coordinates.
        raise Unavailable("reply was not geocoding results") from error


def candidates(address: str) -> list[str]:
    """Progressively coarser queries: full address, then venue+city, then city."""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    queries = [address]
    if len(parts) >= 3:
        queries.append(", ".join(parts[-3:]))
    if len(parts) >= 2:
        queries.append(", ".join(parts[-2:]))
    seen: list[str] = []
    for query in queries:
        if query and query not in seen:
            seen.append(query)
    return seen


def lookup(
    session: requests.Session, address: str, *, use_cache: bool = True
) -> dict[str, Any] | None:
    """Geocode an address, returning None when every fallback misses.

    A miss is cached. A refusal is not: the address stays unlocated for this
    run and is asked again on the next one.
    """
    global _unavailable

    if not address.strip():
        return None

    key = _normalize(address)
    cache = _load_cache()
    if use_cache and key in cache:
        return cache[key]

    if _unavailable:
        return None

    result = None
    try:
        for query in candidates(address):
            result = _query(session, query)
            if result:
                break
    except Unavailable as error:
        _unavailable = True
        print(
            f"geocoder unavailable ({error}): addresses not already cached "
            "stay unlocated this run"
        )
        return None

    cache[key] = result
    _save_cache(cache)
    return result
