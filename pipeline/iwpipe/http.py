"""One shared HTTP session.

Wrestling sites reject bare User-Agents, so the headers are browser shaped
(the same set that unblocked WrestleStat in Clarion-Money-Match). Retries
cover transient failures only; a 404 or 403 is an answer, not a blip.
"""
from __future__ import annotations

import random
import time

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Upgrade-Insecure-Requests": "1",
}

RETRY_STATUSES = {429, 500, 502, 503, 504}
BACKOFF_SECONDS = (0.5, 1.5, 4.0)
POLITE_DELAY = 1.0

_last_request_at = 0.0


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def get(
    session: requests.Session,
    url: str,
    *,
    timeout: int = 30,
    polite: bool = True,
    **kwargs,
) -> requests.Response:
    """GET with one request per second and three retries on transient failures."""
    global _last_request_at

    last_error: Exception | None = None
    for attempt, backoff in enumerate((0.0,) + BACKOFF_SECONDS):
        if backoff:
            time.sleep(backoff + random.uniform(0, 0.3))
        if polite:
            gap = time.monotonic() - _last_request_at
            if gap < POLITE_DELAY:
                time.sleep(POLITE_DELAY - gap)
        try:
            response = session.get(url, timeout=timeout, **kwargs)
            _last_request_at = time.monotonic()
        except requests.RequestException as error:
            last_error = error
            continue

        if response.status_code in RETRY_STATUSES and attempt < len(BACKOFF_SECONDS):
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(min(int(retry_after), 10))
            continue

        response.raise_for_status()
        _fix_encoding(response)
        return response

    raise RuntimeError(f"GET {url} failed after retries: {last_error}")


def _fix_encoding(response: requests.Response) -> None:
    """Trust the document over a missing charset header.

    pywrestling.com serves UTF-8 with a bare `Content-Type: text/html`, and
    requests then defaults to ISO-8859-1, which turns non-breaking spaces
    into mojibake inside event names.
    """
    content_type = response.headers.get("Content-Type", "")
    if "charset=" not in content_type.lower() and response.encoding == "ISO-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"
