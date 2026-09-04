"""Logo and flyer files for every pushed event.

Event.init?(safeRecord:) drops any record whose logo or flyer asset is
missing, so the pipeline always produces both. A source image or PDF is used
when one exists; otherwise a monogram tile and a one-page flyer are rendered
so the event still appears correctly in the app.
"""
from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdf_canvas

from .config import ASSET_DIR, GOLD, INK, SLATE_200, SLATE_800
from .dates import EASTERN
from .http import get

LOGO_SIZE = 512
MAX_FLYER_BYTES = 10 * 1024 * 1024

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]


def monogram(name: str) -> str:
    """Python port of String.monogram in iWrestle/Utilities/EventFormatting.swift.

    "Interstate Classic" -> "IC", "Open" -> "OP".
    """
    words = [w for w in re.split(r"[ \-]+", name) if w and w[0].isalpha()]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    if words:
        return words[0][:2].upper()
    return name[:2].upper()


def event_asset_dir(source_key: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", source_key)
    path = ASSET_DIR / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def make_monogram_logo(name: str, destination: Path) -> Path:
    """Render the same slate tile with gold initials the app falls back to."""
    image = Image.new("RGB", (LOGO_SIZE, LOGO_SIZE), SLATE_800)
    draw = ImageDraw.Draw(image)
    text = monogram(name)
    font = _load_font(int(LOGO_SIZE * 0.42))

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((LOGO_SIZE - (right - left)) / 2 - left,
         (LOGO_SIZE - (bottom - top)) / 2 - top),
        text,
        font=font,
        fill=GOLD,
    )
    image.save(destination, "PNG")
    return destination


def download_flyer(
    session: requests.Session, url: str, destination: Path
) -> Path | None:
    """Save a source PDF, rejecting anything that is not really a PDF."""
    try:
        response = get(session, url, stream=True)
    except Exception:
        return None

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(65536):
        total += len(chunk)
        if total > MAX_FLYER_BYTES:
            return None
        chunks.append(chunk)

    body = b"".join(chunks)
    if not body.startswith(b"%PDF"):
        return None

    destination.write_bytes(body)
    return destination


def _wrap(text: str, width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_flyer(event: dict[str, Any], destination: Path) -> Path:
    """One-page flyer built from the event's own text, for sources with none."""
    page = pdf_canvas.Canvas(str(destination), pagesize=LETTER)
    width, height = LETTER

    page.setFillColorRGB(*[c / 255 for c in INK])
    page.rect(0, 0, width, height, stroke=0, fill=1)

    page.setFillColorRGB(*[c / 255 for c in GOLD])
    page.setFont("Helvetica-Bold", 30)
    y = height - 1.4 * inch
    for line in _wrap(event.get("name", "Event"), 30):
        page.drawString(1 * inch, y, line)
        y -= 34

    when = ""
    if event.get("date"):
        stamp = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        when = stamp.astimezone(EASTERN).strftime("%A, %B %-d, %Y at %-I:%M %p")

    page.setFillColorRGB(1, 1, 1)
    page.setFont("Helvetica", 15)
    y -= 18
    for line in [when] + _wrap(event.get("address", ""), 52):
        if line:
            page.drawString(1 * inch, y, line)
            y -= 22

    page.setFillColorRGB(*[c / 255 for c in SLATE_200])
    page.setFont("Helvetica", 12)
    y -= 16
    details = []
    if event.get("ageGroups"):
        details.append("Divisions: " + ", ".join(event["ageGroups"]))
    if event.get("registration"):
        details.append("Register: " + event["registration"])
    if event.get("sourceUrl"):
        details.append("Details: " + event["sourceUrl"])
    for line in details:
        for wrapped in _wrap(line, 74):
            page.drawString(1 * inch, y, wrapped)
            y -= 18

    page.setFont("Helvetica-Oblique", 9)
    page.drawString(
        1 * inch,
        0.8 * inch,
        "Flyer generated by iWrestle from the organizer's public listing.",
    )
    page.showPage()
    page.save()
    return destination


def ensure_assets(
    session: requests.Session, event: dict[str, Any]
) -> tuple[Path, Path, list[str]]:
    """Guarantee a logo and a flyer on disk. Returns (logo, flyer, notes)."""
    notes: list[str] = []
    folder = event_asset_dir(event["sourceKey"])

    logo_path = folder / "logo.png"
    source_logo = event.get("logoUrl")
    if source_logo and not logo_path.exists():
        try:
            response = get(session, source_logo)
            image = Image.open(io.BytesIO(response.content))
            image.convert("RGB").resize((LOGO_SIZE, LOGO_SIZE)).save(logo_path, "PNG")
        except Exception:
            notes.append("source logo failed, used monogram")
            make_monogram_logo(event["name"], logo_path)
    elif not logo_path.exists():
        make_monogram_logo(event["name"], logo_path)
        notes.append("monogram logo")

    flyer_path = folder / "flyer.pdf"
    if not flyer_path.exists():
        flyer_url = (event.get("flyer") or {}).get("url")
        downloaded = (
            download_flyer(session, flyer_url, flyer_path) if flyer_url else None
        )
        if downloaded is None:
            render_flyer(event, flyer_path)
            notes.append("rendered flyer")

    return logo_path, flyer_path, notes
