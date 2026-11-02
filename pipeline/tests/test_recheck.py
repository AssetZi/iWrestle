"""recheck redoes collect's ledger step on a file that is already collected."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import recheck as recheck_cli  # noqa: E402

from iwpipe import exclusions, ledger, renames, schema  # noqa: E402

FLO = "flowrestling:everett-tournament:2026-12-12"
PYW = "pywrestling:bloody-run-brawl:2026-12-12"


@pytest.fixture(autouse=True)
def _temp_data(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    monkeypatch.setattr(exclusions, "EXCLUDED_PATH", tmp_path / "excluded.json")
    monkeypatch.setattr(renames, "RENAMED_PATH", tmp_path / "renamed.json")


def _event(key, name, status, notes):
    event = schema.blank_event(key.split(":")[0])
    event.update(sourceKey=key, name=name, date="2026-12-12T14:00:00Z",
                 address="Everett High School, 1 Renaissance Circle, Everett, PA 15537",
                 location={"latitude": 40.01, "longitude": -78.37})
    event["review"] = {"status": status, "notes": list(notes)}
    return event


def _run(tmp_path, monkeypatch, events):
    path = tmp_path / "events.pywrestling.20261005.json"
    schema.dump(path, "pywrestling", events)
    monkeypatch.setattr(sys, "argv", ["recheck.py", str(path)])
    assert recheck_cli.main() == 0
    return {e["sourceKey"]: e for e in schema.load(path)["events"]}


def test_the_kept_copy_is_freed_once_its_partner_is_excluded(monkeypatch, tmp_path):
    event = _event(PYW, "Bloody Run Brawl", schema.STATUS_SKIP, [f"possible duplicate of {FLO}", "email from flyer PDF"])
    exclusions.add(FLO, "same-date duplicate")  # and exclude.py dropped it from the ledger

    after = _run(tmp_path, monkeypatch, [event])[PYW]

    assert after["review"]["status"] == schema.STATUS_PENDING
    assert after["review"]["notes"] == ["email from flyer PDF"]


def test_a_copy_whose_partner_is_still_pushed_stays_set_aside(monkeypatch, tmp_path):
    ledger.record(FLO, "development", "REC1", "Everett Tournament", day="2026-12-12",
                  location={"latitude": 40.01, "longitude": -78.37})
    event = _event(PYW, "Bloody Run Brawl", schema.STATUS_SKIP, [f"possible duplicate of {FLO}"])

    after = _run(tmp_path, monkeypatch, [event])[PYW]

    assert after["review"]["status"] == schema.STATUS_SKIP
    assert after["review"]["notes"] == [f"possible duplicate of {FLO}"]


def test_a_dual_meet_is_set_aside_and_stays_set_aside(monkeypatch, tmp_path):
    dual = _event(FLO, "Everett @ Bedford", schema.STATUS_APPROVED, [])
    versus = _event(PYW, "Everett vs. Bedford", schema.STATUS_APPROVED, [])

    after = _run(tmp_path, monkeypatch, [dual, versus])
    assert after[FLO]["review"]["status"] == schema.STATUS_SKIP
    assert after[FLO]["review"]["notes"] == ["dual meet"]
    assert after[PYW]["review"]["status"] == schema.STATUS_SKIP
    assert after[PYW]["review"]["notes"] == ["dual meet"]
    after = after[FLO]

    path = tmp_path / "events.pywrestling.20261005.json"
    monkeypatch.setattr(sys, "argv", ["recheck.py", str(path)])
    assert recheck_cli.main() == 0
    again = schema.load(path)["events"][0]
    assert again["review"]["status"] == schema.STATUS_SKIP
    assert again["review"]["notes"] == ["dual meet"]


def test_a_college_event_is_not_freed_by_losing_its_duplicate_note(monkeypatch, tmp_path):
    event = _event(PYW, "Bloody Run Open", schema.STATUS_SKIP, ["college-level event", f"possible duplicate of {FLO}"])

    after = _run(tmp_path, monkeypatch, [event])[PYW]

    assert after["review"]["status"] == schema.STATUS_SKIP


def test_a_newly_excluded_event_is_set_aside_and_an_approved_one_is_left_alone(monkeypatch, tmp_path):
    gone = _event(FLO, "Everett Tournament", schema.STATUS_APPROVED, [])
    kept = _event(PYW, "Bloody Run Brawl", schema.STATUS_APPROVED, [])
    exclusions.add(FLO, "same-date duplicate")

    after = _run(tmp_path, monkeypatch, [gone, kept])

    assert after[FLO]["review"]["status"] == schema.STATUS_SKIP
    assert after[FLO]["review"]["notes"] == ["excluded: same-date duplicate"]
    assert after[PYW]["review"]["status"] == schema.STATUS_APPROVED
