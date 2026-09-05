"""Logo and flyer files for every pushed event.

Event.init?(safeRecord:) drops any record whose logo or flyer asset is
missing, so the pipeline always produces both. Preference order:

  logo:  crop from the banner (AI-located) > source logo URL > monogram tile
  flyer: the source's real PDF > the banner graphic as a PDF > a text page

Every link on a flyer is a real PDF link annotation, so it is tappable in
the app's QuickLook viewer.
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
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as pdf_canvas

from .config import ASSET_DIR, BANNER_MAX_BYTES, GOLD, INK, SLATE_200, SLATE_800
from .dates import EASTERN
from .http import get

LOGO_SIZE = 512
MAX_FLYER_BYTES = 10 * 1024 * 1024

# A logo crop this small is noise; this large is the whole banner.
CROP_MIN_FRACTION = 0.05
CROP_MAX_FRACTION = 0.90
CROP_PAD_FRACTION = 0.06

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Futura.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _rgb(color: tuple[int, int, int]) -> tuple[float, float, float]:
    return tuple(c / 255 for c in color)


# --- Logos ------------------------------------------------------------------

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


def crop_logo_from_banner(
    banner_path: Path, bbox: dict[str, float], destination: Path,
    pad: float = CROP_PAD_FRACTION,
) -> Path | None:
    """Cut the logo the vision pass located out of the banner, as a square.

    bbox is normalized (0-1, top-left origin). The box is padded, then the
    shorter side is grown to make a square, shifted to stay inside the image.
    Returns None when the box is implausible so the caller falls back.
    """
    try:
        image = Image.open(banner_path).convert("RGB")
    except (OSError, ValueError):
        return None
    width, height = image.size

    try:
        x, y = float(bbox["x"]) * width, float(bbox["y"]) * height
        w, h = float(bbox["w"]) * width, float(bbox["h"]) * height
    except (KeyError, TypeError, ValueError):
        return None

    for side, limit in ((w, width), (h, height)):
        if side < limit * CROP_MIN_FRACTION or side > limit * CROP_MAX_FRACTION:
            return None

    margin = max(w, h) * pad
    x, y, w, h = x - margin, y - margin, w + 2 * margin, h + 2 * margin

    side = min(max(w, h), width, height)
    cx, cy = x + w / 2, y + h / 2
    left = min(max(cx - side / 2, 0), width - side)
    top = min(max(cy - side / 2, 0), height - side)

    crop = image.crop((int(left), int(top), int(left + side), int(top + side)))
    crop.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS).save(destination, "PNG")
    return destination


# --- Downloads --------------------------------------------------------------

def _download(session: requests.Session, url: str, limit: int) -> bytes | None:
    try:
        response = get(session, url, stream=True)
    except Exception:
        return None
    chunks, total = [], 0
    for chunk in response.iter_content(65536):
        total += len(chunk)
        if total > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def download_flyer(
    session: requests.Session, url: str, destination: Path
) -> Path | None:
    """Save a source PDF, rejecting anything that is not really a PDF."""
    body = _download(session, url, MAX_FLYER_BYTES)
    if not body or not body.startswith(b"%PDF"):
        return None
    destination.write_bytes(body)
    return destination


def ensure_banner(session: requests.Session, event: dict[str, Any]) -> Path | None:
    """Fetch the event's banner graphic once; it feeds both the flyer and enrich."""
    url = event.get("bannerUrl")
    if not url:
        return None
    folder = event_asset_dir(event["sourceKey"])
    path = folder / "banner.jpg"
    if not path.exists():
        body = _download(session, url, BANNER_MAX_BYTES)
        if not body:
            return None
        try:
            Image.open(io.BytesIO(body)).verify()
        except Exception:
            return None
        path.write_bytes(body)
    event.setdefault("banner", {})["path"] = str(path)
    return path


def render_pdf_page(pdf_path: Path, destination: Path, scale: float = 1.5) -> Path | None:
    """First page of a flyer PDF as a PNG, so the vision pass can see it."""
    if destination.exists():
        return destination
    try:
        import pypdfium2

        document = pypdfium2.PdfDocument(str(pdf_path))
        image = document[0].render(scale=scale).to_pil()
        image.convert("RGB").save(destination, "PNG")
        return destination
    except Exception:
        return None


# --- Flyers -----------------------------------------------------------------

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


def _when(event: dict[str, Any]) -> str:
    if not event.get("date"):
        return ""
    stamp = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
    return stamp.astimezone(EASTERN).strftime("%A, %B %-d, %Y at %-I:%M %p")


def _link_row(page, label: str, url: str, x: float, y: float) -> float:
    """A labelled, underlined, tappable link. Returns the next baseline."""
    label_font, url_font, size = "Helvetica", "Helvetica", 11
    page.setFont(label_font, size)
    page.setFillColorRGB(*_rgb(SLATE_200))
    page.drawString(x, y, label)
    label_width = stringWidth(label, label_font, size) + 8

    shown = url if len(url) <= 78 else url[:75] + "..."
    x1 = x + label_width
    width = stringWidth(shown, url_font, size)
    page.setFillColorRGB(*_rgb(GOLD))
    page.drawString(x1, y, shown)
    page.setStrokeColorRGB(*_rgb(GOLD))
    page.setLineWidth(0.6)
    page.line(x1, y - 2, x1 + width, y - 2)
    # The annotation is what makes it tappable; the underline just says so.
    page.linkURL(url, (x1, y - 4, x1 + width, y + size), relative=0, thickness=0)
    return y - 20


def _detail_rows(page, event: dict[str, Any], x: float, y: float) -> float:
    page.setFont("Helvetica", 11)
    page.setFillColorRGB(*_rgb(SLATE_200))
    details = event.get("details") or {}
    rows = []
    if event.get("ageGroups"):
        rows.append("Divisions: " + ", ".join(event["ageGroups"]))
    if details.get("startTime"):
        rows.append("Start: " + details["startTime"])
    if details.get("weighInTime"):
        rows.append("Weigh-in: " + details["weighInTime"])
    if details.get("entryFee"):
        rows.append("Entry: " + details["entryFee"])
    for row in rows:
        page.drawString(x, y, row)
        y -= 16
    return y


def _link_rows(page, event: dict[str, Any], x: float, y: float) -> float:
    links = [
        ("Register", event.get("registration")),
        ("Event page", event.get("sourceUrl")),
        ("Organizer", event.get("organizerWebsite")),
    ]
    for label, url in links:
        if url and url.startswith("http"):
            y = _link_row(page, label, url, x, y)
    return y


def _footer(page, height: float) -> None:
    page.setFont("Helvetica-Oblique", 9)
    page.setFillColorRGB(*_rgb(SLATE_200))
    page.drawString(
        1 * inch, 0.8 * inch,
        "Flyer assembled by iWrestle from the organizer's public listing.",
    )


def render_flyer(event: dict[str, Any], destination: Path) -> Path:
    """One-page flyer built from the event's own text, for sources with none."""
    page = pdf_canvas.Canvas(str(destination), pagesize=LETTER)
    width, height = LETTER
    x = 1 * inch

    page.setFillColorRGB(*_rgb(INK))
    page.rect(0, 0, width, height, stroke=0, fill=1)

    page.setFillColorRGB(*_rgb(GOLD))
    page.setFont("Helvetica-Bold", 30)
    y = height - 1.4 * inch
    for line in _wrap(event.get("name", "Event"), 30):
        page.drawString(x, y, line)
        y -= 34

    page.setFillColorRGB(1, 1, 1)
    page.setFont("Helvetica", 15)
    y -= 18
    for line in [_when(event)] + _wrap(event.get("address", ""), 52):
        if line:
            page.drawString(x, y, line)
            y -= 22

    y -= 10
    y = _detail_rows(page, event, x, y)
    y -= 6
    _link_rows(page, event, x, y)
    _footer(page, height)
    page.showPage()
    page.save()
    return destination


def render_image_flyer(
    event: dict[str, Any], banner_path: Path, destination: Path
) -> Path:
    """The organizer's own banner graphic, with the essentials and links under it."""
    page = pdf_canvas.Canvas(str(destination), pagesize=LETTER)
    width, height = LETTER
    x = 0.6 * inch
    content_width = width - 2 * x

    page.setFillColorRGB(*_rgb(INK))
    page.rect(0, 0, width, height, stroke=0, fill=1)

    with Image.open(banner_path) as banner:
        aspect = banner.height / banner.width
    banner_height = content_width * aspect
    top = height - 0.6 * inch
    page.drawImage(
        str(banner_path), x, top - banner_height, content_width, banner_height,
        preserveAspectRatio=True, anchor="n",
    )

    y = top - banner_height - 0.55 * inch
    page.setFillColorRGB(*_rgb(GOLD))
    page.setFont("Helvetica-Bold", 22)
    for line in _wrap(event.get("name", "Event"), 40):
        page.drawString(x, y, line)
        y -= 26

    page.setFillColorRGB(1, 1, 1)
    page.setFont("Helvetica", 13)
    y -= 6
    for line in [_when(event)] + _wrap(event.get("address", ""), 64):
        if line:
            page.drawString(x, y, line)
            y -= 18

    y -= 8
    y = _detail_rows(page, event, x, y)
    y -= 6
    _link_rows(page, event, x, y)
    _footer(page, height)
    page.showPage()
    page.save()
    return destination


# --- Orchestration ----------------------------------------------------------

def ensure_assets(
    session: requests.Session, event: dict[str, Any], *, force: bool = False
) -> tuple[Path, Path, list[str]]:
    """Guarantee a logo and a flyer on disk. Returns (logo, flyer, notes).

    force regenerates the logo and flyer from current event data; it never
    re-downloads a real PDF or banner that is already on disk.
    """
    notes: list[str] = []
    folder = event_asset_dir(event["sourceKey"])
    banner = ensure_banner(session, event)

    logo_path = folder / "logo.png"
    if force or not logo_path.exists():
        made = None
        bbox = event.get("logoBBox")
        source_image = None
        if bbox and event.get("logoSource") == "flyer":
            source_image = folder / "flyer-page1.png"
            if not source_image.exists() and (folder / "source-flyer.pdf").exists():
                source_image = render_pdf_page(folder / "source-flyer.pdf", source_image)
        elif bbox and banner:
            source_image = banner
        if bbox and source_image and Path(source_image).exists():
            made = crop_logo_from_banner(Path(source_image), bbox, logo_path)
            if made:
                where = "flyer" if event.get("logoSource") == "flyer" else "banner"
                notes.append(f"logo cropped from {where}, verify")
        if made is None and event.get("logoUrl"):
            try:
                response = get(session, event["logoUrl"])
                image = Image.open(io.BytesIO(response.content))
                image.convert("RGB").resize((LOGO_SIZE, LOGO_SIZE)).save(logo_path, "PNG")
                made = logo_path
            except Exception:
                notes.append("source logo failed, used monogram")
        if made is None:
            make_monogram_logo(event["name"], logo_path)
            if "source logo failed, used monogram" not in notes:
                notes.append("monogram logo")

    flyer_path = folder / "flyer.pdf"
    real_pdf = folder / "source-flyer.pdf"
    if force or not flyer_path.exists():
        flyer_url = (event.get("flyer") or {}).get("url")
        if flyer_url and not real_pdf.exists():
            download_flyer(session, flyer_url, real_pdf)
        if real_pdf.exists():
            flyer_path.write_bytes(real_pdf.read_bytes())
        elif banner:
            render_image_flyer(event, banner, flyer_path)
            notes.append("banner flyer")
        else:
            render_flyer(event, flyer_path)
            notes.append("rendered flyer")

    return logo_path, flyer_path, notes
