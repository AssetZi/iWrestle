"""Each step of collect's normalize, on its own.

bin/collect.py is a script, so it is imported by path the way test_push_replace
imports push.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import collect as collect_cli  # noqa: E402

from iwpipe import ledger, schema  # noqa: E402

TODAY = date(2026, 9, 7)


def raw(**fields):
    event = schema.blank_event("pywrestling")
    event.update(name="Interstate Classic", dateText="Saturday October 17, 2026",
                 address="Clarion Area High School, 219 Liberty St, Clarion, PA 16214")
    event.update(fields)
    return event


def test_type_and_date_come_from_the_listing_text():
    event = raw(formatText="Double elimination tournament")
    collect_cli.classify_type_and_date(event, TODAY)
    assert event["eventType"] == "tournament"
    assert event["date"].startswith("2026-10-17")

    event = raw(dateText="sometime in the fall")
    collect_cli.classify_type_and_date(event, TODAY)
    assert event["date"] is None
    assert any(n.startswith("unparsed date") for n in event["review"]["notes"])


def test_divisions_default_with_a_note_and_college_opens_are_set_aside(monkeypatch):
    event = raw(divisionsText="Youth, Jr High")
    collect_cli.classify_divisions_and_level(event)
    assert event["ageGroups"] == ["Youth", "Jr High"]

    event = raw(divisionsText="")
    collect_cli.classify_divisions_and_level(event)
    assert event["ageGroups"] == collect_cli.DEFAULT_AGE_GROUPS
    assert "no divisions found, defaulted" in event["review"]["notes"]

    monkeypatch.setattr(collect_cli, "INCLUDE_COLLEGE", False)
    event = raw(name="Clarion Open", venue="Clarion University", divisionsText="")
    collect_cli.classify_divisions_and_level(event)
    assert event["ageGroups"] == ["Open"]
    assert event["review"]["status"] == schema.STATUS_SKIP
    assert "college-level event" in event["review"]["notes"]


def test_placeholders_are_skipped_and_tba_venues_are_not_geocoded():
    event = raw(name="CANCELLED - Interstate Classic")
    assert collect_cli.flag_placeholders(event) is True
    assert event["review"]["status"] == schema.STATUS_SKIP

    event = raw(address="TBA")
    assert collect_cli.flag_placeholders(event) is True
    assert event["review"]["status"] == schema.STATUS_PENDING
    assert "venue still TBA at the source" in event["review"]["notes"]

    assert collect_cli.flag_placeholders(raw()) is False


def test_contact_falls_back_to_the_organizer_and_the_env_email(monkeypatch):
    monkeypatch.setattr(collect_cli, "DEFAULT_CONTACT_EMAIL", "me@club.org")
    event = raw(organizer="Clarion Wrestling Club")
    collect_cli.default_contact(event)
    assert (event["contact"]["firstName"], event["contact"]["lastName"]) == ("Clarion Wrestling Club", "(Organizer)")
    assert event["contact"]["email"] == "me@club.org"
    assert "default contact email" in event["review"]["notes"]

    monkeypatch.setattr(collect_cli, "DEFAULT_CONTACT_EMAIL", "")
    event = raw(contact={"firstName": "Jane", "lastName": "Coach", "email": "", "phone": ""})
    collect_cli.default_contact(event)
    assert event["contact"]["firstName"] == "Jane"
    assert "no contact email: set DEFAULT_CONTACT_EMAIL in .env" in event["review"]["notes"]


def test_normalize_assigns_the_key_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr("iwpipe.assets.ASSET_DIR", tmp_path / "assets")
    event = collect_cli.normalize(raw(), None, source="pywrestling", today=TODAY, skip_geocode=True)
    assert event["sourceKey"] == "pywrestling:interstate-classic:2026-10-17"
    assert event["logo"] is None
    assert not (tmp_path / "assets").exists()


def test_twins_get_their_own_asset_folders(tmp_path, monkeypatch):
    """Two listings with one name and day used to share a folder, so one
    twin's flyer named the other."""
    monkeypatch.setattr("iwpipe.assets.ASSET_DIR", tmp_path / "assets")
    a = collect_cli.normalize(raw(floId="2S9X"), None, source="flowrestling", today=TODAY, skip_geocode=True)
    b = collect_cli.normalize(raw(floId="2gPX"), None, source="flowrestling", today=TODAY, skip_geocode=True)
    a["location"] = b["location"] = {"latitude": 41.2, "longitude": -79.4}
    assert schema.disambiguate_keys([a, b]) == 1
    for event in (a, b):
        collect_cli.attach_assets(event, None)
    assert a["logo"] != b["logo"]
    assert Path(a["logo"]).exists() and Path(b["logo"]).exists()
    assert Path(b["logo"]).parent.name.endswith("_2gPX")
    assert schema.validate(a) == [] and schema.validate(b) == []


def test_ledger_notes_use_the_final_key(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    ledger.record("flowrestling:interstate-classic:2026-10-17:2gPX", "production", "R", "Interstate Classic", day="2026-10-17")
    event = raw(sourceKey="flowrestling:interstate-classic:2026-10-17:2gPX", date="2026-10-17T16:00:00Z")
    event["source"] = "flowrestling"
    collect_cli.annotate_from_ledger(event)
    assert "already in production" in event["review"]["notes"]
    assert not any(n.startswith("possible duplicate") for n in event["review"]["notes"])
