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
