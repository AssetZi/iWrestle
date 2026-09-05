"""Trackwrestling open tournaments.

The site answers 406 to anything that looks like a browser, but is happy to
talk to a plain client, so this uses its own minimal headers rather than the
shared browser-shaped ones. Each visit gets a session (TIM + twSessionId)
from the landing page; the search is a GET with the filters in the query,
and paging only keeps the filter if those same parameters ride along.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from ..schema import blank_event, note

SOURCE = "trackwrestling"
BASE = "https://www.trackwrestling.com/tw/"
LANDING = BASE + "Login.jsp?TIM=1&PageType=OpenTournaments"
REGISTER = "https://www.trackwrestling.com/registration/TW_Register.jsp?tournamentGroupId="

# Anything more browser-like than this (an Accept for HTML, sec-ch-ua,
# Upgrade-Insecure-Requests) earns a 406, so the shared session is not used.
HEADERS = {"User-Agent": "iWrestle-pipeline/1.0"}


def _plain_session() -> requests.Session:
    session = requests.Session()
    session.headers.clear()
    session.headers.update(HEADERS)
    return session

# stateBox option values on the landing page.
STATES = {"PA": "39"}
DEFAULT_STATES = ["PA"]
MONTHS_AHEAD = 12
MAX_PAGES = 20

SESSION = re.compile(r"TIM=(\d+)&twSessionId=(\w+)")
SELECTED = re.compile(r"eventSelected\((\d+),'(.*?)',(\d+),\s*'([^']*)'")
GROUP_ID = re.compile(r"tournamentGroupId=(\d+)")
CITY_LINE = re.compile(r"^(.*),\s*([A-Z]{2})\s+(\d{5})")

# eventSelected's third argument is kept for reference only: on the saved
# page code 3 covered duals and code 1 an individual tournament, so it is
# not a type. The event's name decides, as it does for every source.


def _session(session: requests.Session) -> tuple[str, str]:
    html = session.get(LANDING, headers=HEADERS, timeout=30).text
    match = SESSION.search(html)
    if not match:
        raise RuntimeError("Trackwrestling landing page carried no session id")
    return match.group(1), match.group(2)


def _window(today: date | None = None) -> tuple[str, str]:
    start = today or date.today()
    end = start + timedelta(days=30 * MONTHS_AHEAD)
    return start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")


def search_url(tim: str, sid: str, state_code: str, start: str, end: str, index: int = 0) -> str:
    base = f"{BASE}Login.jsp?TIM={tim}&twSessionId={sid}"
    if index:
        base += f"&tournamentIndex={index}"
    return f"{base}&tName=&state={state_code}&sDate={start}&eDate={end}&lastName=&firstName=&teamName=&sfvString=&city=&gbId=&camps=false"


def parse_rows(html: str) -> list[dict[str, Any]]:
    """Every tournament row on a results page, as raw collector output."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    for item in soup.select("ul.tournament-ul > li"):
        anchor = item.find("a", href=SELECTED)
        if not anchor:
            continue
        match = SELECTED.search(anchor["href"])
        lines = [t.strip() for t in item.get_text("\n", strip=True).split("\n") if t.strip()]
        if len(lines) < 2:
            continue

        event = blank_event(SOURCE)
        event["trackId"] = match.group(1)
        event["name"] = match.group(2).replace("\\'", "'")
        event["typeCode"] = match.group(3)
        logo = match.group(4)
        if logo and logo != "null":
            event["logoUrl"] = logo
        event["dateText"] = lines[1]

        # Venue, street, "City, ST 12345" as printed; the app wants commas.
        place = [line for line in lines[2:] if line not in ("Pre-register", "Website")]
        city_line = next((line for line in place if CITY_LINE.match(line)), "")
        before = place[: place.index(city_line)] if city_line else place
        event["address"] = ", ".join(part for part in before + [city_line] if part)
        event["venue"] = before[0] if before else ""
        if city_line:
            event["region"] = CITY_LINE.match(city_line).group(2)

        registration = item.find("a", href=GROUP_ID)
        if registration:
            event["registration"] = REGISTER + GROUP_ID.search(registration["href"]).group(1)
        website = next(
            (a["href"] for a in item.find_all("a", href=True) if a.get_text(strip=True) == "Website"),
            None,
        )
        if website and website.startswith("http"):
            event["organizerWebsite"] = website

        event["sourceUrl"] = LANDING
        event["formatText"] = ""
        event["divisionsText"] = ""
        note(event, "divisions not published by the source, verify")
        rows.append(event)
    return rows


def collect(
    session: requests.Session,
    *,
    fixture: Path | None = None,
    limit: int | None = None,
    dump_unparsed: bool = False,
    states: list[str] | None = None,
) -> list[dict[str, Any]]:
    if fixture:
        rows = parse_rows(Path(fixture).read_text())
    else:
        session = _plain_session()
        tim, sid = _session(session)
        start, end = _window()
        rows = []
        seen: set[str] = set()
        for state in states or DEFAULT_STATES:
            code = STATES[state]
            for index in range(MAX_PAGES):
                html = session.get(
                    search_url(tim, sid, code, start, end, index), headers=HEADERS, timeout=30
                ).text
                page = [r for r in parse_rows(html) if r["trackId"] not in seen]
                if not page:
                    break
                seen.update(r["trackId"] for r in page)
                rows.extend(page)

    events = []
    for event in rows:
        # The filter is by state; anything else that slips through is noise.
        if event.get("region") and states and event["region"] not in (states or DEFAULT_STATES):
            continue
        events.append(event)
        if limit and len(events) >= limit:
            break
    return events
