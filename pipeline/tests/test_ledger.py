"""Cross-source duplicates: the same gym on the same weekend is the same event."""
from iwpipe import ledger


def _seed(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    ledger.record(
        "pywrestling:harold-winshel-memorial-round-robin:2026-09-12", "development",
        "REC1", "Harold Winshel Memorial Round Robin",
        day="2026-09-12", location={"latitude": 40.2394, "longitude": -74.9658},
    )


def test_same_venue_same_weekend_is_flagged(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    found = ledger.find_similar(
        "flowrestling:11th-annual-harold-winshel-memorial:2026-09-12",
        "11th-annual-harold-winshel-memorial", "2026-09-12",
        {"latitude": 40.2390, "longitude": -74.9672},
    )
    assert found == ["pywrestling:harold-winshel-memorial-round-robin:2026-09-12"]


def test_same_gym_a_month_later_is_a_different_event(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    assert ledger.find_similar(
        "flowrestling:x:2026-10-12", "x", "2026-10-12",
        {"latitude": 40.2390, "longitude": -74.9672},
    ) == []


def test_exact_slug_still_matches_without_a_location(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    assert ledger.find_similar(
        "flowrestling:harold-winshel-memorial-round-robin:2026-09-12",
        "harold-winshel-memorial-round-robin", "2026-09-12", None,
    )


def test_an_event_never_matches_itself(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    assert ledger.find_similar(
        "pywrestling:harold-winshel-memorial-round-robin:2026-09-12",
        "harold-winshel-memorial-round-robin", "2026-09-12",
        {"latitude": 40.2394, "longitude": -74.9658},
    ) == []
