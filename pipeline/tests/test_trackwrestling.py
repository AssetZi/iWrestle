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
