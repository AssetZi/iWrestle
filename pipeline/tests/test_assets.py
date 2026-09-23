"""The monogram must match String.monogram in EventFormatting.swift."""
import pytest

from iwpipe.assets import make_monogram_logo, monogram, render_flyer


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Interstate Classic", "IC"),
        ("Christmas Bash 5", "CB"),
        ("Open", "OP"),
        ("Battle-in-the-Burg", "BI"),
        ("5 Star", "ST"),
    ],
)
def test_monogram_matches_swift(name, expected):
    assert monogram(name) == expected


def test_logo_is_a_real_png(tmp_path):
    path = make_monogram_logo("Interstate Classic", tmp_path / "logo.png")
    assert path.read_bytes().startswith(b"\x89PNG")


def test_rendered_flyer_is_a_real_pdf(tmp_path):
    event = {
        "name": "Interstate Classic",
        "date": "2026-10-17T16:00:00Z",
        "address": "Venue, 1 Main St, Clarion, PA 16214",
        "ageGroups": ["Youth"],
        "registration": "https://x.co/r",
        "sourceUrl": "https://pywrestling.com/x.html",
    }
    path = render_flyer(event, tmp_path / "flyer.pdf")
    assert path.read_bytes().startswith(b"%PDF")


def _synthetic_banner(path, box=(400, 60, 200, 200)):
    """A 640x320 banner with a solid red square where a logo would be."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (640, 320), (20, 30, 40))
    x, y, w, h = box
    ImageDraw.Draw(image).rectangle((x, y, x + w, y + h), fill=(220, 30, 30))
    image.save(path, "JPEG", quality=95)
    return path


def test_logo_crop_is_square_and_centered_on_the_box(tmp_path):
    from PIL import Image

    from iwpipe.assets import crop_logo_from_banner

    banner = _synthetic_banner(tmp_path / "banner.jpg")
    bbox = {"x": 400 / 640, "y": 60 / 320, "w": 200 / 640, "h": 200 / 320}
    out = crop_logo_from_banner(banner, bbox, tmp_path / "logo.png")
    assert out is not None
    with Image.open(out) as logo:
        assert logo.size == (512, 512)
        r, g, b = logo.getpixel((256, 256))
        assert r > 180 and g < 80 and b < 80


def test_implausible_logo_boxes_are_rejected(tmp_path):
    from iwpipe.assets import crop_logo_from_banner

    banner = _synthetic_banner(tmp_path / "banner.jpg")
    whole = {"x": 0, "y": 0, "w": 0.99, "h": 0.99}
    speck = {"x": 0.5, "y": 0.5, "w": 0.01, "h": 0.01}
    assert crop_logo_from_banner(banner, whole, tmp_path / "a.png") is None
    assert crop_logo_from_banner(banner, speck, tmp_path / "b.png") is None


def _linked_event():
    return {
        "name": "Interstate Classic",
        "date": "2026-10-17T16:00:00Z",
        "address": "Venue, 1 Main St, Clarion, PA 16214",
        "ageGroups": ["Youth"],
        "registration": "https://form.jotform.com/262174666443159",
        "sourceUrl": "https://www.pywrestling.com/x.html",
        "organizerWebsite": "https://breakthechainswrestling.com",
        "details": {"startTime": "9:00 AM", "weighInTime": "7:30 AM"},
    }


def test_text_flyer_links_are_real_annotations(tmp_path):
    """QuickLook only makes a URL tappable when it is a /Link annotation."""
    path = render_flyer(_linked_event(), tmp_path / "flyer.pdf")
    data = path.read_bytes()
    assert b"/URI" in data
    assert b"form.jotform.com/262174666443159" in data
    assert b"breakthechainswrestling.com" in data


def test_banner_flyer_embeds_the_image_and_links(tmp_path):
    from iwpipe.assets import render_image_flyer

    banner = _synthetic_banner(tmp_path / "banner.jpg")
    path = render_image_flyer(_linked_event(), banner, tmp_path / "flyer.pdf")
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    assert b"/Image" in data
    assert b"/URI" in data
    assert b"form.jotform.com/262174666443159" in data


def test_rendering_the_same_event_twice_gives_identical_bytes(tmp_path):
    """push hashes the flyer bytes; a re-render must not look like a change."""
    event = _linked_event()
    first = render_flyer(event, tmp_path / "a.pdf").read_bytes()
    second = render_flyer(event, tmp_path / "b.pdf").read_bytes()
    assert first == second

    from iwpipe.assets import render_image_flyer

    banner = _synthetic_banner(tmp_path / "banner.jpg")
    first = render_image_flyer(event, banner, tmp_path / "c.pdf").read_bytes()
    second = render_image_flyer(event, banner, tmp_path / "d.pdf").read_bytes()
    assert first == second
