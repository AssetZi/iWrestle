"""Source date strings -> a single UTC timestamp.

The app stores one Date per event and groups the Home list by the viewer's
calendar day. A multi-day event uses its first day, and a day with no stated
start time is pinned to noon Eastern so the event cannot slide onto the
previous calendar day for users in Pacific time.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from .config import EVENT_TZ

EASTERN = ZoneInfo(EVENT_TZ)
DEFAULT_HOUR = 12

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_MONTH_NAMES = "january|february|march|april|may|june|july|august|september|october|november|december"
_MONTH_ABBR = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"

# "October 17, 2026", "Oct 17-18, 2026", "Saturday September 5, 2026"
_TEXT_DATE = re.compile(
    rf"\b({_MONTH_NAMES}|{_MONTH_ABBR})\.?\s+(\d{{1,2}})"
    rf"(?:\s*(?:-|–|&|and|to)\s*(?:(?:{_MONTH_NAMES}|{_MONTH_ABBR})\.?\s*)?\d{{1,2}})?"
    rf"(?:\s*,?\s*(\d{{4}}))?",
    re.IGNORECASE,
)

# "10/17/2026", "10/17/26", "10/17"
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")

# "9:00 AM", "10 am"
_TIME = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?\b", re.IGNORECASE)

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?")


def _month_number(name: str) -> int | None:
    return MONTHS.get(name[:3].lower())


def _infer_year(month: int, day: int, today: date) -> int:
    """Pick the next occurrence at or after today for a year-less date."""
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate >= today:
            return year
    return today.year


def parse_time(text: str) -> tuple[int, int] | None:
    """Extract a start time as (hour, minute) in 24-hour form."""
    match = _TIME.search(text or "")
    if not match:
        return None
    hour = int(match.group(1)) % 12
    minute = int(match.group(2) or 0)
    if match.group(3).lower() == "p":
        hour += 12
    return hour, minute


def parse_date(text: str, today: date | None = None) -> date | None:
    """First calendar day mentioned in a source date string."""
    if not text:
        return None
    today = today or datetime.now(EASTERN).date()

    iso = _ISO.search(text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            pass

    textual = _TEXT_DATE.search(text)
    if textual:
        month = _month_number(textual.group(1))
        day = int(textual.group(2))
        year = int(textual.group(3)) if textual.group(3) else None
        if month:
            if year is None:
                year = _infer_year(month, day, today)
            try:
                return date(year, month, day)
            except ValueError:
                return None

    numeric = _NUMERIC_DATE.search(text)
    if numeric:
        month, day = int(numeric.group(1)), int(numeric.group(2))
        raw_year = numeric.group(3)
        if raw_year:
            year = int(raw_year)
            if year < 100:
                year += 2000
        else:
            year = _infer_year(month, day, today) if 1 <= month <= 12 else today.year
        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None


def _iso_passthrough(text: str) -> str | None:
    """Honor a source that already gives a full timestamp (FloWrestling does).

    A trailing Z means the source is already UTC; otherwise the wall time is
    read as Eastern.
    """
    match = _ISO.search(text or "")
    if not match or match.group(4) is None:
        return None
    try:
        naive = datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3)),
            int(match.group(4)), int(match.group(5)),
        )
    except ValueError:
        return None
    tz = timezone.utc if re.search(r"\d{2}:\d{2}(?::\d{2})?Z", text) else EASTERN
    return (
        naive.replace(tzinfo=tz)
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def to_utc_iso(
    date_text: str,
    time_text: str | None = None,
    today: date | None = None,
) -> str | None:
    """Full pipeline: source strings -> "2026-10-17T16:00:00Z"."""
    passthrough = _iso_passthrough(date_text)
    if passthrough:
        return passthrough

    day = parse_date(date_text, today=today)
    if day is None:
        return None

    clock = parse_time(time_text or date_text)
    hour, minute = clock if clock else (DEFAULT_HOUR, 0)

    local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=EASTERN)
    return (
        local.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
