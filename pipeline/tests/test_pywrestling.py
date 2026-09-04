"""Parser tests against a saved copy of the real page, so they run offline."""
from pathlib import Path

import pytest

from iwpipe.collectors import pywrestling
from iwpipe.collectors.pywrestling import _split_street_city, _title_case

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "pywrestling-index.html"


@pytest.fixture(scope="module")
def events():
    return pywrestling.collect(None, fixture=FIXTURE)


def test_finds_the_whole_calendar(events):
    """The page listed 34 events when the fixture was saved."""
    assert len(events) >= 30


def test_every_event_has_the_basics(events):
    for event in events:
        assert event["name"]
        assert event["dateText"]
        assert event["address"]


def test_address_is_comma_separated_for_addressparts(events):
    """AddressParts in the app splits on commas: venue, street, city, ST ZIP."""
    for event in events:
        assert event["address"].count(",") >= 2, event["address"]


def test_a_known_event_parses_exactly(events):
    match = next(e for e in events if "Takedown In The Den" in e["name"])
    assert match["organizer"] == "Elizabethtown Mat Club"
    assert match["address"] == (
        "Elizabethtown Area School District, 600 East High Street, "
        "Elizabethtown, PA 17022"
    )
    assert match["divisionsText"] == "Youth, Jr High, High School"


def test_events_that_link_offsite_are_still_found(events):
    """Battle in the Burg links to the organizer's own site, not a PYW page."""
    assert any("Battle In The Burg" in e["name"] for e in events)


def test_venue_split_across_elements_is_rejoined(events):
    match = next(e for e in events if "Lebanon Girls" in e["name"])
    assert match["address"].startswith("Lebanon High School,")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("275 Swamp Road Newtown, PA 18940", "275 Swamp Road, Newtown, PA 18940"),
        ("256 US-6 E Milford, PA 18337", "256 US-6 E, Milford, PA 18337"),
        ("1 University Avenue Mechanicsburg, PA 17055",
         "1 University Avenue, Mechanicsburg, PA 17055"),
    ],
)
def test_street_city_split(raw, expected):
    assert _split_street_city(raw) == expected


def test_acronyms_survive_title_casing():
    assert _title_case("MAT-TOWN USA FALL CLASSIC") == "Mat-Town USA Fall Classic"
    assert _title_case("HAROLD WINSHEL MEMORIAL") == "Harold Winshel Memorial"
