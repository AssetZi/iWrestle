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


def test_details_are_not_fetched_for_names_set_aside(monkeypatch, tmp_path):
    """A dual meet or a placeholder never reaches the directory, so its
    event-hub record is not worth a request: half the national listing is duals."""
    from datetime import datetime, timedelta, timezone

    soon = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT15:00:00.000Z")
    listing = [
        {"id": "1", "name": "Alta @ Bountiful", "startTime": soon,
         "url": "https://www.flowrestling.org/nextgen/events/111/information"},
        {"id": "2", "name": "Air Force vs Army", "startTime": soon,
         "url": "https://www.flowrestling.org/nextgen/events/222/information"},
        {"id": "3", "name": "CANCELLED Beast of the East", "startTime": soon,
         "url": "https://www.flowrestling.org/nextgen/events/333/information"},
        {"id": "4", "name": "Beast of the East", "startTime": soon,
         "url": "https://www.flowrestling.org/nextgen/events/444/information"},
    ]
    asked = []

    def fake_detail(session, core_id, cache=None):
        asked.append(core_id)
        return {"eventContact": {"email": "beast@example.com", "name": "Beast Staff"}}

    monkeypatch.setattr(flowrestling, "enumerate_all", lambda session: listing)
    monkeypatch.setattr(flowrestling, "fetch_detail", fake_detail)
    monkeypatch.setattr(flowrestling, "DETAIL_CACHE_PATH", tmp_path / "flo-details.json")

    events = {e["name"]: e for e in flowrestling.collect(None)}

    assert asked == ["444"]
    assert events["Beast of the East"]["contact"]["email"] == "beast@example.com"
    for name in ("Alta @ Bountiful", "Air Force vs Army", "CANCELLED Beast of the East"):
        assert "event details not fetched, set aside by name" in events[name]["review"]["notes"], name


def test_expired_cache_entries_nobody_asked_for_are_pruned():
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=40)).isoformat(timespec="seconds")
    fresh = (now - timedelta(days=2)).isoformat(timespec="seconds")
    cache = {
        "1": {"fetchedAt": old, "data": {}},     # expired, not wanted: gone
        "2": {"fetchedAt": old, "data": {}},     # expired but wanted: kept (refetched by collect)
        "3": {"fetchedAt": fresh, "data": {}},   # fresh, not wanted: kept until it expires
    }
    flowrestling._prune_detail_cache(cache, {"2"}, now)
    assert sorted(cache) == ["2", "3"]
