"""Pennsylvania Youth Wrestling (pywrestling.com).

The index page is static HTML whose class names are generated, so blocks are
found by grouping the links that point at each event's own page rather than
by selector. Divisions are icon images, not text, so they are read from the
image filenames.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from ..config import FIXTURE_DIR
from ..http import get
from ..schema import blank_event, note

BASE_URL = "https://www.pywrestling.com/"
SOURCE = "pywrestling"

EVENT_HREF = re.compile(r"^(?!https?:)[a-z0-9-]+-\d{1,2}-\d{1,2}\.html$")

# Division icons: images/<letter>/<division>-160.jpg
DIVISION_ICONS = {
    "youth": "Youth",
    "juniorhigh": "Jr High",
    "highschool": "High School",
    "novice": "Novice",
    "tot": "Novice",
    "elementary": "Youth",
    "college": "Open",
    "open": "Open",
}
# Icons that describe the region or audience, not an age division.
IGNORED_ICONS = re.compile(
    r"(pa|ohio|maryland|newyork|newjersey|westvirginia|virginia|delaware)-\d+|girls-\d+"
)

DATE_LINE = re.compile(
    r"\b(?:sun|mon|tues?|wed(?:nes)?|thur?s?|fri|sat(?:ur)?)[a-z]*,?\s+"
    r"(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\s+\d{1,2}",
    re.IGNORECASE,
)
ADDRESS_LINE = re.compile(r"\d.*\b[A-Z]{2}\s+\d{5}\b")
PRESENTED_BY = re.compile(r"^presented by\s+", re.IGNORECASE)

# Each block carries one real event graphic at 640 or 1280 wide (2:1). The
# -160 files are division/region icons and the -288 files are buttons.
BANNER_IMG = re.compile(r"images/[a-z0-9]+/[a-z0-9-]+-(640|1280)\.jpe?g$", re.IGNORECASE)

# Emails are hidden behind `function emN(){var c="..."}` where every
# character is shifted up by one.
EMN_SCRIPT = re.compile(r'function\s+em\d+\s*\(\)\s*\{\s*var\s+c\s*=\s*"([^"]+)"')
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
DETAIL_TEXT_LIMIT = 3000


def _decode_emn(html: str) -> list[str]:
    """Recover the obfuscated addresses a page's emN() functions would open."""
    found = []
    for encoded in EMN_SCRIPT.findall(html):
        decoded = "".join(chr(ord(ch) - 1) for ch in encoded)
        if EMAIL.fullmatch(decoded) and decoded not in found:
            found.append(decoded)
    return found


def _banner_url(block) -> str:
    """The block's event graphic, preferring the larger rendition."""
    candidates = [
        img.get("src", "") for img in block.find_all("img") if BANNER_IMG.search(img.get("src", ""))
    ]
    if not candidates:
        return ""
    candidates.sort(key=lambda src: "-1280." in src, reverse=True)
    return requests.compat.urljoin(BASE_URL, candidates[0])


STREET_SUFFIX = re.compile(
    r"\b(street|st|road|rd|avenue|ave|boulevard|blvd|drive|dr|lane|ln|way|pike|"
    r"highway|hwy|route|rt|circle|cir|court|ct|place|pl|parkway|pkwy|terrace|"
    r"trail|turnpike|square|sq|park|extension)\b\.?",
    re.IGNORECASE,
)


# Names are set in all caps; title() would flatten these to "Usa" / "Mswa".
ACRONYMS = {
    "USA", "PA", "OH", "NY", "NJ", "MD", "WV", "DE", "VA",
    "PJW", "PYW", "MSWA", "SEPA", "NHSCA", "AAU", "YMCA", "JV", "HS",
    "MAC", "NCAA", "II", "III", "IV", "LLC", "TBD", "DV", "BTC",
}


def _title_case(text: str) -> str:
    """Title-case an all-caps name while leaving real acronyms alone."""
    words = []
    for word in text.split():
        stripped = word.strip(".,&()").upper()
        words.append(word if stripped in ACRONYMS else word.title())
    return " ".join(words)


def _split_street_city(address_line: str) -> str:
    """"275 Swamp Road Newtown, PA 18940" -> "275 Swamp Road, Newtown, PA 18940"."""
    if not address_line:
        return ""
    head, sep, tail = address_line.rpartition(",")
    if not sep:
        return address_line

    matches = list(STREET_SUFFIX.finditer(head))
    if matches:
        cut = matches[-1].end()
        street, city = head[:cut].strip(), head[cut:].strip(" ,")
    else:
        # No street type (a venue-only line): the last word is the city.
        words = head.split()
        if len(words) < 2:
            return address_line
        street, city = " ".join(words[:-1]), words[-1]

    # "1815 Harrison Avenue NW Canton" splits after "Avenue", leaving the
    # quadrant stranded on the city; it belongs to the street.
    parts = city.split()
    if parts and parts[0].upper().strip(".") in {"N", "S", "E", "W", "NW", "NE", "SW", "SE"}:
        street = f"{street} {parts[0]}"
        city = " ".join(parts[1:])

    if not city:
        return f"{street},{tail}"
    return f"{street}, {city},{tail}"


def _event_blocks(soup):
    """Every element holding exactly one event.

    The site's class names are generated, and some events link to an outside
    site rather than a page here, so blocks are identified by content: the
    smallest element carrying exactly one date line and one street address.
    """
    candidates = []
    for element in soup.find_all(["div", "td", "section", "article", "li"]):
        text = element.get_text("\n", strip=True)
        if not text or len(DATE_LINE.findall(text)) != 1:
            continue
        address = ADDRESS_LINE.search(text)
        if not address:
            continue
        candidates.append((len(text), element, text, address.group(0)))

    smallest: dict[tuple[str, str], Any] = {}
    for _, element, text, address in sorted(candidates, key=lambda c: c[0]):
        key = (DATE_LINE.search(text).group(0), address)
        smallest.setdefault(key, element)
    return list(smallest.values())


def _divisions_from_icons(block) -> str:
    found = []
    for img in block.find_all("img"):
        src = img.get("src", "")
        if IGNORED_ICONS.search(src):
            continue
        stem = Path(src).stem.rsplit("-", 1)[0].lower()
        if stem in DIVISION_ICONS:
            found.append(DIVISION_ICONS[stem])
    return ", ".join(dict.fromkeys(found))


def _parse_block(block) -> dict[str, Any] | None:
    lines = [
        line.replace("\xa0", " ").strip()
        for line in block.get_text("\n", strip=True).split("\n")
        if line.strip()
    ]
    if not lines:
        return None

    event = blank_event(SOURCE)
    event["rawText"] = " | ".join(lines)

    detail = next(
        (
            a["href"]
            for a in block.find_all("a", href=True)
            if EVENT_HREF.match(a["href"])
        ),
        "",
    )
    event["sourceUrl"] = BASE_URL + detail if detail else BASE_URL

    date_line = next((line for line in lines if DATE_LINE.search(line)), "")
    event["dateText"] = date_line

    name = next(
        (
            line
            for line in lines
            if not DATE_LINE.search(line)
            and not PRESENTED_BY.match(line)
            and not ADDRESS_LINE.search(line)
            and len(line) > 3
        ),
        "",
    )
    event["name"] = _title_case(name) if name.isupper() else name

    organizer = next(
        (PRESENTED_BY.sub("", line) for line in lines if PRESENTED_BY.match(line)), ""
    )
    event["organizer"] = organizer

    address_line = next((line for line in lines if ADDRESS_LINE.search(line)), "")
    venue = ""
    if address_line:
        # The venue sits between the "presented by" line and the address, and
        # the site sometimes breaks it across elements ("Lebanon High" /
        # "School"), so take every line in that gap.
        index = lines.index(address_line)
        start = 0
        for position, line in enumerate(lines[:index]):
            if PRESENTED_BY.match(line):
                start = position + 1
        venue = " ".join(
            line
            for line in lines[start:index]
            if line != name and not DATE_LINE.search(line)
        ).strip()
    # The app's AddressParts splits on commas, so the pushed address has to
    # read "Venue, Street, City, ST ZIP". The source writes street and city
    # as one run ("275 Swamp Road Newtown, PA 18940"), so the boundary is
    # found at the last street-type word.
    event["address"] = ", ".join(
        part for part in (venue, _split_street_city(address_line)) if part
    )
    event["venue"] = venue

    event["divisionsText"] = _divisions_from_icons(block)
    event["formatText"] = " ".join(
        line
        for line in lines
        if line not in (date_line, name, address_line)
        and not PRESENTED_BY.match(line)
    )

    for link in block.find_all("a", href=True):
        target = link["href"]
        if re.search(r"(register|signup|sign-up|trackwrestling|flowrestling)", target, re.I):
            event["registration"] = target
            break

    event["bannerUrl"] = _banner_url(block)

    if not event["name"] or not event["dateText"]:
        return None
    return event


def _site_emails(html: str) -> set[str]:
    """Addresses that belong to the site itself, printed on every page."""
    found = {m.lower() for m in EMAIL.findall(html)}
    found.update(e.lower() for e in _decode_emn(html))
    return found


def _enrich_from_detail(session, event, site_emails: set[str] = frozenset()) -> None:
    """Follow the event's own page for a flyer PDF and a contact.

    site_emails are the webmaster addresses that appear on every page; a
    match there is not the organizer and is ignored.
    """
    try:
        response = get(session, event["sourceUrl"])
    except Exception:
        note(event, "detail page unreachable")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().endswith(".pdf"):
            event.setdefault("flyer", {})["url"] = requests.compat.urljoin(
                event["sourceUrl"], href
            )
            break
    for tag in soup.find_all(["embed", "iframe"]):
        source = tag.get("src", "")
        if source.lower().endswith(".pdf") and not event.get("flyer", {}).get("url"):
            event.setdefault("flyer", {})["url"] = requests.compat.urljoin(
                event["sourceUrl"], source
            )

    text = soup.get_text(" ", strip=True)
    event["detailText"] = text[:DETAIL_TEXT_LIMIT]

    candidates = [m for m in EMAIL.findall(text) if m.lower() not in site_emails]
    candidates += [m for m in _decode_emn(response.text) if m.lower() not in site_emails]
    if candidates:
        event["contact"]["email"] = candidates[0]
    phone = PHONE.search(text)
    if phone:
        event["contact"]["phone"] = phone.group(0)

    if not event.get("registration"):
        for link in soup.find_all("a", href=True):
            if re.search(r"(register|signup|trackwrestling|flowrestling)", link["href"], re.I):
                event["registration"] = link["href"]
                break
    if not event.get("registration"):
        # Most PYW events register through an embedded JotForm.
        for frame in soup.find_all("iframe", src=True):
            if "jotform.com" in frame["src"]:
                event["registration"] = requests.compat.urljoin(
                    event["sourceUrl"], frame["src"]
                )
                break


def collect(
    session: requests.Session,
    *,
    fixture: Path | None = None,
    limit: int | None = None,
    dump_unparsed: bool = False,
) -> list[dict[str, Any]]:
    if fixture:
        html = Path(fixture).read_text()
    else:
        html = get(session, BASE_URL).text

    soup = BeautifulSoup(html, "html.parser")

    events: list[dict[str, Any]] = []
    unparsed: list[str] = []

    for block in _event_blocks(soup):
        event = _parse_block(block)
        if event is None:
            unparsed.append(block.get_text(" ", strip=True)[:200])
            continue
        events.append(event)
        if limit and len(events) >= limit:
            break

    if not fixture:
        site_emails = _site_emails(html)
        for event in events:
            _enrich_from_detail(session, event, site_emails)

    if dump_unparsed and unparsed:
        target = FIXTURE_DIR / "pywrestling-unparsed.txt"
        target.write_text("\n".join(unparsed) + "\n")
        print(f"  {len(unparsed)} blocks failed to parse -> {target}")

    return events
