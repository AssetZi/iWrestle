"""Trackwrestling open tournaments, as a supplement to FloWrestling.

Flo owns Trackwrestling and its search already lists most Track events
with a contact and a real page, so a Track row is only kept when Flo does
not know the event. The site also blocks aggressively: anything that
looks like a browser gets a 406, and too many requests from one address
gets every client a 406 for a while. This collector therefore uses a bare
client, one session with cookies, a three-second gap between requests,
and reports a block as a skipped run rather than a failure.
"""
from __future__ import annotations

import re
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from ..config import MONTHS_AHEAD
from ..schema import blank_event, note
from . import flowrestling

SOURCE = "trackwrestling"
BASE = "https://www.trackwrestling.com/tw/"
LANDING = BASE + "Login.jsp?TIM=1&PageType=OpenTournaments"
REGISTER = "https://www.trackwrestling.com/registration/TW_Register.jsp?tournamentGroupId="
# What the site's own "Enter Event" button opens, minus the session.
GATEWAY = BASE + "opentournaments/VerifyPassword.jsp?tournamentId={tid}&userType=viewer_ngw"

# Anything more browser-like than this (an Accept for HTML, sec-ch-ua,
# Upgrade-Insecure-Requests) earns a 406, so the shared session is not used.
HEADERS = {"User-Agent": "iWrestle-pipeline/1.0"}
PAUSE_SECONDS = 3.0
MAX_PAGES = 40

# stateBox option values on the landing page; the national run sends none.
STATES = {"PA": "39"}

SESSION = re.compile(r"TIM=(\d+)&twSessionId=(\w+)")
SELECTED = re.compile(r"eventSelected\((\d+),'(.*?)',(\d+),\s*'([^']*)'")
GROUP_ID = re.compile(r"tournamentGroupId=(\d+)")
CITY_LINE = re.compile(r"^(.*),\s*([A-Z]{2})\s+(\d{5})")


class Blocked(RuntimeError):
    """The site answered 406; stop for this run and try again next time."""


def _plain_session() -> requests.Session:
    session = requests.Session()
    session.headers.clear()
    session.headers.update(HEADERS)
    return session


def _fetch(session: requests.Session, url: str) -> str:
    time.sleep(PAUSE_SECONDS)
    response = session.get(url, headers=HEADERS, timeout=30)
    if response.status_code == 406:
        raise Blocked("HTTP 406")
    response.raise_for_status()
    return response.text


def _session(session: requests.Session) -> tuple[str, str]:
    html = _fetch(session, LANDING)
    match = SESSION.search(html)
    if not match:
        raise Blocked("landing page carried no session id")
    return match.group(1), match.group(2)


def _window(today: date | None = None) -> tuple[str, str]:
    start = today or date.today()
    end = start + timedelta(days=30 * MONTHS_AHEAD)
    return start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")


def search_url(tim: str, sid: str, state_code: str, start: str, end: str, index: int = 0) -> str:
    base = f"{BASE}Login.jsp?TIM={tim}&twSessionId={sid}"
    if index:
        base += f"&tournamentIndex={index}"
    state = f"&state={state_code}" if state_code else ""
    return f"{base}&tName={state}&sDate={start}&eDate={end}&lastName=&firstName=&teamName=&sfvString=&city=&gbId=&camps=false"


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
        if logo and logo != "null" and "/images/gb_" not in logo:
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

        # Never the landing page: the registration if any, else the same
        # gateway the site's own Enter Event button opens.
        event["sourceUrl"] = event["registration"] or GATEWAY.format(tid=event["trackId"])
        event["formatText"] = ""
        event["divisionsText"] = ""
        note(event, "divisions not published by the source, verify")
        rows.append(event)
    return rows


def _first_day(date_text: str) -> str:
    """"10/17 - 10/18/2026" or "09/19/2026" -> "2026-10-17"."""
    match = re.search(r"(\d{2})/(\d{2})(?:\s*-\s*\d{2}/\d{2})?/(\d{4})", date_text)
    if not match:
        return ""
    return f"{match.group(3)}-{match.group(1)}-{match.group(2)}"


def collect(
    session: requests.Session,
    *,
    fixture: Path | None = None,
    limit: int | None = None,
    dump_unparsed: bool = False,
    states: list[str] | None = None,
    flo_session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    if fixture:
        rows = parse_rows(Path(fixture).read_text())
    else:
        own = _plain_session()
        rows = []
        try:
            tim, sid = _session(own)
            start, end = _window()
            seen: set[str] = set()
            for code in ([STATES[s] for s in states] if states else [""]):
                for index in range(MAX_PAGES):
                    page = [r for r in parse_rows(_fetch(own, search_url(tim, sid, code, start, end, index)))
                            if r["trackId"] not in seen]
                    if not page:
                        break
                    seen.update(r["trackId"] for r in page)
                    rows.extend(page)
        except Blocked as error:
            print(f"trackwrestling: blocked ({error}), skipped this run")
            return []

    events = []
    for event in rows:
        if states and event.get("region") and event["region"] not in states:
            continue
        if not fixture and flo_session is not None:
            # Flo's version has the contact and a real page; let it win.
            if flowrestling.search_by_name(flo_session, event["name"], _first_day(event["dateText"])):
                continue
            note(event, "Track-only event, no organizer contact available")
        events.append(event)
        if limit and len(events) >= limit:
            break
    return events
