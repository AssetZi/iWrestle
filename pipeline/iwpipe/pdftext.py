"""Text and contacts from an organizer's flyer PDF.

Most PYW flyers are real text PDFs, so an email or phone printed on them
can be pulled without a model. Anything more (who the contact is, the
divisions, the times) is left to enrich, which gets the same PDF.
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+\w")
PHONE = re.compile(r"\(?\b\d{3}\)?[-.\s]?\d{3}[-.\s]\d{4}\b")
TEXT_LIMIT = 4000


def extract_text(path: Path, limit: int = TEXT_LIMIT) -> str:
    """Plain text of every page, or "" for a scanned or unreadable PDF."""
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join((page.extract_text() or "") for page in pdf.pages)
    except Exception:
        return ""
    return text[:limit]


def contacts_from_text(text: str, ignore: set[str] = frozenset()) -> tuple[str, str]:
    """(email, phone) as printed, empty when absent. Site-wide addresses skipped."""
    email = next((m for m in EMAIL.findall(text) if m.lower() not in ignore), "")
    phone = ""
    match = PHONE.search(text)
    if match:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 10:
            phone = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return email, phone


STOPWORDS = {
    "the", "of", "and", "at", "in", "on", "a", "an", "for", "to", "annual",
    "tournament", "wrestling", "classic", "open", "duals", "dual", "round",
    "robin", "memorial", "youth", "invitational", "takedown", "girls", "boys",
    "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th",
}


def _significant(name: str) -> set[str]:
    words = {w for w in re.findall(r"[a-z0-9]+", name.lower()) if len(w) > 2}
    return words - STOPWORDS


def pdf_matches_event(text: str, event: dict) -> bool | None:
    """Does this flyer describe this event?

    Two events on the site can share one registration form, which means one
    of them gets the other's PDF. None when the PDF has no readable text
    (scanned) and the decision is left to review and enrich.
    """
    if not text or len(text.strip()) < 40:
        return None
    lowered = text.lower()
    words = _significant(event.get("name", ""))
    if words:
        hits = sum(1 for w in words if w in lowered)
        if hits / len(words) >= 0.5:
            return True
    parts = [p.strip() for p in (event.get("address") or "").split(",") if p.strip()]
    city = parts[-2].lower() if len(parts) >= 2 else ""
    if city and re.search(r"\b" + re.escape(city) + r"\b", lowered):
        return True
    return False
