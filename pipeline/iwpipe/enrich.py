"""Read what a scraper cannot: the text printed inside an event's banner.

The listing pages hold no contact, no divisions beyond icons, and no start
time; the organizer's banner graphic often does. Claude reads the image and
returns a strict structure. Merging is conservative: it fills gaps and
defaulted values only, never overwrites anything scraped, and marks every
AI-sourced field so review can see exactly what came from where.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Literal

import anthropic
from pydantic import BaseModel, ValidationError

from . import mapping
from .config import DEFAULT_CONTACT_EMAIL, ENRICH_CACHE_PATH, ENRICH_MODEL
from .schema import note

# Bump when the prompt or schema changes so cached answers are re-asked.
PROMPT_VERSION = 1

DEFAULTED_DIVISIONS_NOTE = "no divisions found, defaulted"
DEFAULT_EMAIL_NOTES = (
    "default contact email",
    "placeholder contact email: set a real DEFAULT_CONTACT_EMAIL in .env",
    "no contact email: set DEFAULT_CONTACT_EMAIL in .env",
)

# Claude Opus 5 list price per million tokens, for the summary line only.
PRICE_INPUT_PER_MTOK = 5.00
PRICE_OUTPUT_PER_MTOK = 25.00


# --- What Claude returns ------------------------------------------------------

class ContactOut(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


class LogoBBox(BaseModel):
    x: float
    y: float
    w: float
    h: float


class BannerExtraction(BaseModel):
    contact: ContactOut
    organizerWebsite: str | None = None
    divisions: list[str] = []
    startTime: str | None = None
    weighInTime: str | None = None
    entryFee: str | None = None
    registrationUrl: str | None = None
    logoBBox: LogoBBox | None = None
    confidence: Literal["low", "medium", "high"]
    evidence: str


SYSTEM_PROMPT = """You read the promotional banner for a youth wrestling event and report only what is legibly printed on it. The pipeline already scraped the listing; you fill the gaps.

Rules:
- Return null for anything that is not printed on the banner or not fully legible. Never guess, and never derive a phone, email, or website from a club or school name.
- contact.name is a person's name printed as a contact, not the club or host. contact.phone must be a 10-digit US number as printed. contact.email must contain an @.
- registrationUrl only if an actual URL is printed. organizerWebsite is a printed website for the host club.
- divisions: every division or age band printed, verbatim, one per item (for example "Tots", "Bantam", "Jr High", "Girls K-12", "1st Year", "Open").
- startTime, weighInTime, entryFee: verbatim as printed.
- logoBBox: the tight box around the distinct logo, crest, or badge artwork only. Not the whole banner, not the title text, not a background photo. Coordinates normalized 0-1 with origin at the top-left (x, y) and size (w, h). Null if the banner has no distinct logo.
- The known fields in the message are context, not targets; do not repeat them. If the banner contradicts a known field (a different date or venue), say so in evidence.
- confidence reflects how legible the banner is overall. evidence is one sentence describing what was readable and what was not."""


# --- Cache ---------------------------------------------------------------------

def banner_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def cache_key(event: dict[str, Any], image_hash: str) -> str:
    return f"{event['sourceKey']}:{image_hash}:v{PROMPT_VERSION}"


def load_cache() -> dict[str, Any]:
    if ENRICH_CACHE_PATH.exists():
        try:
            return json.loads(ENRICH_CACHE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache: dict[str, Any]) -> None:
    ENRICH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENRICH_CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")


# --- Request -------------------------------------------------------------------

def _is_default_email(email: str) -> bool:
    return not email or email == DEFAULT_CONTACT_EMAIL or email.endswith("example.com")


def build_messages(event: dict[str, Any], image_bytes: bytes, media_type: str = "image/jpeg") -> list[dict[str, Any]]:
    contact = event.get("contact") or {}
    notes = event.get("review", {}).get("notes", [])
    known = {
        "name": event.get("name"),
        "date": event.get("date"),
        "address": event.get("address"),
        "organizer": event.get("organizer"),
        "ageGroups": event.get("ageGroups"),
        "ageGroupsWereDefaulted": DEFAULTED_DIVISIONS_NOTE in notes,
        "registration": event.get("registration") or None,
        "contactEmail": contact.get("email") or None,
        "contactEmailIsDefault": _is_default_email(contact.get("email", "")),
    }
    text = "Known fields (context only):\n" + json.dumps(known, indent=1)
    if event.get("detailText"):
        text += "\n\nText from the event's own web page:\n" + event["detailText"]

    return [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.standard_b64encode(image_bytes).decode("ascii"),
                },
            },
            {"type": "text", "text": text},
        ],
    }]


def extract(
    client: anthropic.Anthropic, event: dict[str, Any], image_bytes: bytes
) -> tuple[BannerExtraction | None, Any]:
    """One banner in, one validated extraction out (None on refusal)."""
    response = client.messages.parse(
        model=ENRICH_MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=build_messages(event, image_bytes),
        output_format=BannerExtraction,
    )
    if response.stop_reason == "refusal":
        return None, response.usage
    return response.parsed_output, response.usage


def extract_with_retry(client, event, image_bytes):
    """Most specific failures first; transient ones get one more try."""
    for attempt in (1, 2):
        try:
            return extract(client, event, image_bytes)
        except anthropic.RateLimitError as error:
            if attempt == 2:
                raise
            wait = int(error.response.headers.get("retry-after", "20"))
            time.sleep(min(wait, 60))
    raise RuntimeError("unreachable")


# --- Merge ---------------------------------------------------------------------

def _normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


def _normalize_url(raw: str) -> str:
    """Banners print sites in caps; hostnames are case-insensitive, paths are not."""
    url = raw.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url.lstrip("/")
    scheme, _, rest = url.partition("://")
    host, slash, path = rest.partition("/")
    return f"{scheme.lower()}://{host.lower()}{slash}{path}"


def _remove_notes(event: dict[str, Any], *texts: str) -> None:
    notes = event.setdefault("review", {}).setdefault("notes", [])
    event["review"]["notes"] = [n for n in notes if n not in texts]


def merge(event: dict[str, Any], extraction: BannerExtraction) -> list[str]:
    """Fold an extraction into the event. Returns the names of fields filled.

    Scraped values always win. Only empty or defaulted values are replaced,
    and every replacement leaves an "AI:" note so review can see it.
    """
    filled: list[str] = []
    contact = event.setdefault("contact", {})
    found = extraction.contact

    if found.email and "@" in found.email and _is_default_email(contact.get("email", "")):
        contact["email"] = found.email.strip()
        _remove_notes(event, *DEFAULT_EMAIL_NOTES)
        note(event, "AI: email from banner")
        filled.append("email")

    phone = _normalize_phone(found.phone) if found.phone else None
    if phone and not contact.get("phone"):
        contact["phone"] = phone
        note(event, "AI: phone from banner")
        filled.append("phone")

    if found.name and contact.get("lastName") == "(Organizer)":
        first, _, last = found.name.strip().rpartition(" ")
        if first:
            contact["firstName"], contact["lastName"] = first, last
        else:
            contact["firstName"], contact["lastName"] = last, "(Contact)"
        _remove_notes(event, "organizer used as contact name")
        note(event, "AI: contact name from banner")
        filled.append("contactName")

    if extraction.registrationUrl and not event.get("registration"):
        if extraction.registrationUrl.startswith("http"):
            event["registration"] = extraction.registrationUrl
            note(event, "AI: registration from banner")
            filled.append("registration")

    if extraction.divisions:
        groups, unknown = mapping.normalize_age_groups(", ".join(extraction.divisions))
        notes = event.get("review", {}).get("notes", [])
        if groups and DEFAULTED_DIVISIONS_NOTE in notes:
            event["ageGroups"] = groups
            _remove_notes(event, DEFAULTED_DIVISIONS_NOTE)
            note(event, "AI: divisions from banner")
            filled.append("ageGroups")
        elif groups and groups != event.get("ageGroups"):
            note(event, "AI: banner lists " + ", ".join(groups))
        if unknown:
            note(event, "AI: unmapped division tokens: " + ", ".join(unknown))

    if extraction.organizerWebsite and not event.get("organizerWebsite"):
        event["organizerWebsite"] = _normalize_url(extraction.organizerWebsite)
        note(event, "AI: organizer website from banner")
        filled.append("organizerWebsite")

    details = event.setdefault("details", {})
    for field in ("startTime", "weighInTime", "entryFee"):
        value = getattr(extraction, field)
        if value and not details.get(field):
            details[field] = value
            note(event, f"AI: {field} from banner")
            filled.append(field)

    if extraction.logoBBox and not event.get("logoBBox"):
        event["logoBBox"] = extraction.logoBBox.model_dump()
        note(event, "AI: logo located on banner")
        filled.append("logoBBox")

    note(event, f"AI: enriched, confidence={extraction.confidence}: {extraction.evidence}")
    if extraction.confidence == "low":
        note(event, "AI: low confidence, verify")
    return filled


def record_provenance(event: dict[str, Any], image_hash: str, extraction: BannerExtraction) -> None:
    event["enrich"] = {
        "imageHash": image_hash,
        "model": ENRICH_MODEL,
        "promptVersion": PROMPT_VERSION,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "confidence": extraction.confidence,
        "evidence": extraction.evidence,
    }


# --- Cost ----------------------------------------------------------------------

def usage_totals(usages: list[Any]) -> dict[str, float]:
    input_tokens = sum(getattr(u, "input_tokens", 0) or 0 for u in usages)
    cached = sum(getattr(u, "cache_read_input_tokens", 0) or 0 for u in usages)
    output_tokens = sum(getattr(u, "output_tokens", 0) or 0 for u in usages)
    dollars = (
        (input_tokens + cached * 0.1) / 1e6 * PRICE_INPUT_PER_MTOK
        + output_tokens / 1e6 * PRICE_OUTPUT_PER_MTOK
    )
    return {
        "input": input_tokens, "cached": cached, "output": output_tokens,
        "dollars": round(dollars, 4),
    }


__all__ = [
    "BannerExtraction", "ContactOut", "LogoBBox", "ValidationError",
    "banner_hash", "cache_key", "load_cache", "save_cache", "build_messages",
    "extract", "extract_with_retry", "merge", "record_provenance", "usage_totals",
]
