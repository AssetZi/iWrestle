"""Flo collector tests against a saved API response."""
import json
from pathlib import Path

import pytest

from iwpipe.collectors import flowrestling

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "flowrestling-pa.json"


@pytest.fixture(scope="module")
def events():
    return flowrestling.collect(None, fixture=FIXTURE)


def test_parses_the_saved_response(events):
    assert events


def test_multi_day_events_appear_once(events):
    """The API repeats an event once per day; only one record should be made."""
    raw = json.loads(FIXTURE.read_text())
    assert len(events) < len(raw)
    names = [e["name"] for e in events]
    assert len(names) == len(set(names))


def test_coordinates_come_from_the_api(events):
    """These events need no geocoding, unlike the scraped sources."""
    for event in events:
        assert event["location"]["latitude"]
        assert event["location"]["longitude"]


def test_timestamps_are_utc(events):
    for event in events:
        assert event["date"].endswith("Z")


def test_address_is_comma_separated(events):
    for event in events:
        assert event["address"].count(",") >= 1


def test_divisions_are_flagged_as_unknown(events):
    """Flo does not publish age divisions, so every event needs review."""
    for event in events:
        assert any("divisions" in n for n in event["review"]["notes"])


def test_flo_branded_placeholder_is_not_used_as_a_logo(events):
    """Their generic still is Flo's mark, not the event's."""
    for event in events:
        assert "Wrestling-Logo-Overlay" not in (event.get("logoUrl") or "")
