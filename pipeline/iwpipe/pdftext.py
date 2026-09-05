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
