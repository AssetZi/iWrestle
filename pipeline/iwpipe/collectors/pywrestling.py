"""Pennsylvania Youth Wrestling (pywrestling.com).

The index page is static HTML whose class names are generated, so blocks are
found by content rather than by selector. Each event has up to three pages:
an info page (`slug-M-D.html`), a sign-up page (`slug-M-D-or.html`), and
sometimes only an organizer's own site. The organizer's flyer PDF lives
inside a JotForm on either page, as a PDF Embedder widget.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

from ..config import FIXTURE_DIR
from ..http import get
from ..schema import blank_event, note

BASE_URL = "https://www.pywrestling.com/"
SOURCE = "pywrestling"

# slug-9-12.html is the info page; slug-9-12-or.html is online registration.
EVENT_HREF = re.compile(r"^(?!https?:)[a-z0-9-]+-\d{1,2}-\d{1,2}(-or)?\.html$")
SIGNUP_HREF = re.compile(r"-or\.html$")

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
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+\w")
PHONE = re.compile(r"\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]\d{4}\b")
DETAIL_TEXT_LIMIT = 3000

REGISTRATION_HOSTS = re.compile(
    r"(trackwrestling|flowrestling|floarena|wrestlereg|register|signup|sign-up)", re.I
)
JOTFORM_HOST = "https://www.jotform.com"

# Filled by collect(): webmaster addresses that must not become contacts.
SITE_EMAILS: set[str] = set()

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
    "MAC", "NCAA", "II", "III", "IV", "LLC", "TBD", "DV", "BTC", "GTE",
}


# --- Small parsers -----------------------------------------------------------

def _decode_emn(html: str) -> list[str]:
    """Recover the obfuscated addresses a page's emN() functions would open."""
    found = []
    for encoded in EMN_SCRIPT.findall(html):
        decoded = "".join(chr(ord(ch) - 1) for ch in encoded)
        if EMAIL.fullmatch(decoded) and decoded not in found:
            found.append(decoded)
    return found


def _site_emails(html: str) -> set[str]:
    """Addresses that belong to the site itself, printed on every page."""
    found = {m.lower() for m in EMAIL.findall(html)}
    found.update(e.lower() for e in _decode_emn(html))
    return found


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


def _banner_url(block) -> str:
    """The block's event graphic, preferring the larger rendition."""
    candidates = [
        img.get("src", "") for img in block.find_all("img") if BANNER_IMG.search(img.get("src", ""))
    ]
    if not candidates:
        return ""
    candidates.sort(key=lambda src: "-1280." in src, reverse=True)
    return requests.compat.urljoin(BASE_URL, candidates[0])


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


def _pages(block) -> dict[str, str | None]:
    """The event's info page, sign-up page and organizer's own site, if any."""
    info = signup = external = None
    for anchor in block.find_all("a", href=True):
        href = anchor["href"]
        if EVENT_HREF.match(href):
            url = requests.compat.urljoin(BASE_URL, href)
            if SIGNUP_HREF.search(href):
                signup = signup or url
            else:
                info = info or url
        elif href.startswith("http") and "pywrestling.com" not in href and "maps" not in href:
            if not REGISTRATION_HOSTS.search(href):
                external = external or href
    return {"info": info, "signup": signup, "external": external}


def pdf_from_jotform(form_html: str) -> str:
    """The flyer PDF a JotForm shows through its PDF Embedder widget.

    The widget's settings sit in a hidden input as URL-encoded JSON with the
    uploaded file's path; the form's HTML never links the PDF directly.
    """
    soup = BeautifulSoup(form_html, "html.parser")
    for field in soup.select("input.form-widget-settings"):
        try:
            settings = json.loads(unquote(field.get("value", "")))
        except (ValueError, TypeError):
            continue
        for item in settings if isinstance(settings, list) else []:
            value = item.get("value") if isinstance(item, dict) else None
            path = str(value.get("path", "")) if isinstance(value, dict) else ""
            if path.lower().endswith(".pdf"):
                return f"{JOTFORM_HOST}{path}?serveInlineWithCache=1"
    return ""


# --- Blocks ------------------------------------------------------------------

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

    pages = _pages(block)
    event["pages"] = pages
    # Never the site root: an event with no page of its own gets no link.
    event["sourceUrl"] = pages["info"] or pages["signup"] or pages["external"] or ""
    if pages["external"]:
        event["organizerWebsite"] = pages["external"]

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
    # read "Venue, Street, City, ST ZIP".
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
        if link["href"].startswith("http") and REGISTRATION_HOSTS.search(link["href"]):
            event["registration"] = link["href"]
            break

    event["bannerUrl"] = _banner_url(block)

    if not event["name"] or not event["dateText"]:
        return None
    return event


# --- Detail pages ------------------------------------------------------------

def _fetch(session, url: str) -> str | None:
    try:
        return get(session, url).text
    except Exception:
        return None


def _enrich_from_detail(session, event, site_emails: set[str] = frozenset()) -> None:
    """Follow the event's own pages for its flyer PDF, registration and contact.

    site_emails are the webmaster addresses that appear on every page; a
    match there is not the organizer and is ignored. Addresses printed in a
    JotForm's own HTML (the form owner) are ignored the same way.
    """
    pages = event.get("pages") or {}
    ignore = {e.lower() for e in site_emails} | {"example@example.com"}
    texts: list[str] = []
    jotforms: dict[str, str] = {}
    pdf_url = ""
    external_registration = ""

    for kind in ("info", "signup"):
        url = pages.get(kind)
        if not url:
            continue
        html = _fetch(session, url)
        if html is None:
            note(event, f"{kind} page unreachable")
            continue
        soup = BeautifulSoup(html, "html.parser")
        texts.append(soup.get_text(" ", strip=True))

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf") and not pdf_url:
                pdf_url = requests.compat.urljoin(url, href)
            elif href.startswith("http") and REGISTRATION_HOSTS.search(href) and not external_registration:
                external_registration = href
        for tag in soup.find_all(["embed", "iframe"]):
            source = tag.get("src", "")
            if source.lower().endswith(".pdf") and not pdf_url:
                pdf_url = requests.compat.urljoin(url, source)
            elif "jotform.com" in source and kind not in jotforms:
                jotforms[kind] = requests.compat.urljoin(url, source)

        for hidden in _decode_emn(html):
            texts.append(hidden)

    # Registration: an explicit outside link beats the sign-up form, which
    # beats a form embedded on the info page.
    if not event.get("registration"):
        event["registration"] = (
            external_registration or jotforms.get("signup") or jotforms.get("info") or ""
        )

    # The organizer's real flyer usually lives inside the form as a PDF widget.
    flyer = event.setdefault("flyer", {"url": None, "path": None})
    for kind in ("signup", "info"):
        form_url = jotforms.get(kind)
        if pdf_url or not form_url:
            continue
        form_html = _fetch(session, form_url)
        if form_html is None:
            continue
        ignore.update(m.lower() for m in EMAIL.findall(form_html))
        pdf_url = pdf_from_jotform(form_html)
    if pdf_url and not flyer.get("url"):
        flyer["url"] = pdf_url

    text = " ".join(texts)
    event["detailText"] = text[:DETAIL_TEXT_LIMIT]
    event["ignoreEmails"] = sorted(ignore)

    email = next((m for m in EMAIL.findall(text) if m.lower() not in ignore), "")
    if email and not event["contact"].get("email"):
        event["contact"]["email"] = email
    phone = PHONE.search(text)
    if phone and not event["contact"].get("phone"):
        event["contact"]["phone"] = phone.group(0)


# --- Entry point -------------------------------------------------------------

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
        SITE_EMAILS.clear()
        SITE_EMAILS.update(site_emails)
        for event in events:
            _enrich_from_detail(session, event, site_emails)

    if dump_unparsed and unparsed:
        target = FIXTURE_DIR / "pywrestling-unparsed.txt"
        target.write_text("\n".join(unparsed) + "\n")
        print(f"  {len(unparsed)} blocks failed to parse -> {target}")

    return events
