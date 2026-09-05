"""Parser tests against a saved Trackwrestling results page (PA, one season)."""
from pathlib import Path

import pytest

from iwpipe.collectors import trackwrestling

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "trackwrestling-pa.html"


@pytest.fixture(scope="module")
def events():
    return trackwrestling.collect(None, fixture=FIXTURE)


def test_rows_parse(events):
    assert len(events) >= 5
    for event in events:
        assert event["name"] and event["dateText"] and event["address"]


def test_known_row(events):
    den = next(e for e in events if e["name"] == "Takedown in the Den")
    assert den["dateText"] == "09/19/2026"
    assert den["address"] == "Elizabethtown Area High School, 600 East High Street, Elizabethtown, PA 17022"
    assert den["registration"] == "https://www.trackwrestling.com/registration/TW_Register.jsp?tournamentGroupId=288785132"
    assert den["logoUrl"].startswith("https://www.trackwrestling.com/tw/uploads/")
    assert den["region"] == "PA"


def test_search_url_keeps_the_filter_when_paging():
    url = trackwrestling.search_url("1", "abc", "39", "09/01/2026", "08/31/2027", index=3)
    assert "tournamentIndex=3" in url
    assert "state=39" in url and "sDate=09/01/2026" in url


def test_session_id_is_read_from_the_landing_page():
    assert trackwrestling.SESSION.search("Login.jsp?TIM=1788601082654&twSessionId=jlsymdzgjx&x").groups() == (
        "1788601082654", "jlsymdzgjx",
    )


def test_a_block_is_a_skipped_run_not_a_failure(monkeypatch):
    class Response:
        status_code = 406
        text = ""
        def raise_for_status(self):
            raise AssertionError("should not be called on 406")

    class Session:
        headers = {}
        def get(self, *a, **k):
            return Response()

    monkeypatch.setattr(trackwrestling, "_plain_session", lambda: Session())
    monkeypatch.setattr(trackwrestling.time, "sleep", lambda s: None)
    assert trackwrestling.collect(None) == []


def test_rows_flo_already_has_are_dropped(monkeypatch, events):
    from iwpipe.collectors import flowrestling, trackwrestling as t

    html = FIXTURE.read_text()
    monkeypatch.setattr(t, "_plain_session", lambda: None)
    monkeypatch.setattr(t, "_session", lambda s: ("1", "abc"))
    pages = iter([html, ""])
    monkeypatch.setattr(t, "_fetch", lambda s, url: next(pages))
    monkeypatch.setattr(flowrestling, "search_by_name", lambda s, name, day: {"id": "x", "location": {"coordinates": {"latitude": 1, "longitude": 2}}} if "Hurst" in name else None)
    kept = t.collect(None, flo_session=object())
    names = [e["name"] for e in kept]
    assert "Hurst Invitational" not in names
    assert any("Track-only event" in n for e in kept for n in e["review"]["notes"])


def test_source_url_is_never_the_landing_page(events):
    for event in events:
        assert event["sourceUrl"] != trackwrestling.LANDING
        assert event["sourceUrl"].startswith("https://www.trackwrestling.com/")


def test_first_day_parsing():
    assert trackwrestling._first_day("10/17 - 10/18/2026") == "2026-10-17"
    assert trackwrestling._first_day("09/19/2026") == "2026-09-19"
