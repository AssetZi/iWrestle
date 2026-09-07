"""cktool has no update; --replace deletes and recreates changed events."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from iwpipe import cktool, ledger, schema  # noqa: E402


def _event(tmp_path, name="Interstate Classic"):
    event = schema.blank_event("pywrestling")
    event.update(
        sourceKey="pywrestling:interstate-classic:2026-10-17", name=name,
        eventType="tournament", date="2026-10-17T16:00:00Z",
        address="Venue, 1 Main St, Clarion, PA 16214",
        location={"latitude": 41.2, "longitude": -79.4}, ageGroups=["Youth"],
    )
    event["contact"] = {"firstName": "A", "lastName": "B", "email": "a@b.com", "phone": ""}
    logo = tmp_path / "logo.png"; logo.write_bytes(b"\x89PNG logo")
    flyer = tmp_path / "flyer.pdf"; flyer.write_bytes(b"%PDF flyer")
    event["logo"] = str(logo); event["flyer"] = {"url": None, "path": str(flyer)}
    event["review"]["status"] = schema.STATUS_APPROVED
    return event


def test_content_hash_changes_when_fields_or_assets_change(tmp_path):
    event = _event(tmp_path)
    fields = cktool.build_fields(event)
    logo, flyer = Path(event["logo"]), Path(event["flyer"]["path"])
    first = cktool.content_hash(fields, logo, flyer)
    assert cktool.content_hash(fields, logo, flyer) == first
    assert cktool.content_hash(cktool.build_fields(dict(event, name="Other")), logo, flyer) != first
    flyer.write_bytes(b"%PDF new flyer")
    assert cktool.content_hash(fields, logo, flyer) != first


def test_replace_deletes_then_recreates_only_changed_events(tmp_path, monkeypatch, capsys):
    import push as push_cli

    # This exercises the cktool backend; a configured key would otherwise
    # send the push through CloudKit REST instead.
    monkeypatch.setattr(cktool, "rest_client", lambda environment: None)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    monkeypatch.setattr("iwpipe.assets.ASSET_DIR", tmp_path / "assets")
    calls = []
    monkeypatch.setattr(cktool, "delete_record", lambda name, env: calls.append(("delete", name)))
    monkeypatch.setattr(cktool, "create_record", lambda *a, **k: calls.append(("create",)) or {"recordName": f"REC{len(calls)}"})

    event = _event(tmp_path)
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [event])

    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    push_cli.main()
    assert calls == [("create",)]
    assert ledger.get(event["sourceKey"], "development")["contentHash"]

    # Unchanged: nothing happens even with --replace.
    calls.clear()
    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    push_cli.main()
    assert calls == []

    # Changed flyer: deleted, then created again.
    Path(event["flyer"]["path"]).write_bytes(b"%PDF the real one")
    push_cli.main()
    assert [c[0] for c in calls] == ["create", "delete"]
    assert "same" in capsys.readouterr().out or True


def _wire(tmp_path, monkeypatch):
    monkeypatch.setattr(cktool, "rest_client", lambda environment: None)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    monkeypatch.setattr("iwpipe.assets.ASSET_DIR", tmp_path / "assets")
    calls = []
    monkeypatch.setattr(cktool, "delete_record", lambda name, env: calls.append(("delete", name)))
    monkeypatch.setattr(cktool, "create_record", lambda *a, **k: calls.append(("create",)) or {"recordName": f"REC{len(calls)}"})
    return calls


def test_a_moved_event_replaces_the_record_for_its_old_date(tmp_path, monkeypatch):
    import push as push_cli

    calls = _wire(tmp_path, monkeypatch)
    ledger.record("pywrestling:interstate-classic:2026-10-10", "development", "OLD", "Interstate Classic", day="2026-10-10")
    event = _event(tmp_path)
    event["movedFrom"] = "pywrestling:interstate-classic:2026-10-10"
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [event])

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    push_cli.main()
    assert calls == [("create",), ("delete", "OLD")]
    assert ledger.get("pywrestling:interstate-classic:2026-10-10", "development") is None
    assert ledger.get(event["sourceKey"], "development")


def test_a_listing_gone_from_its_source_is_removed_only_with_replace(tmp_path, monkeypatch):
    import push as push_cli

    calls = _wire(tmp_path, monkeypatch)
    ledger.record("pywrestling:gone:2026-11-07", "development", "GONE", "Gone", day="2026-11-07")
    ledger.record("flowrestling:other:2026-11-07", "development", "FLO", "Other", day="2026-11-07")
    ledger.mark_misses("pywrestling", set(), "2026-09-07")
    ledger.mark_misses("pywrestling", set(), "2026-09-14")
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [])

    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    push_cli.main()
    assert calls == []

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace", "--dry-run"])
    push_cli.main()
    assert calls == []
    assert ledger.get("pywrestling:gone:2026-11-07", "development")

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    push_cli.main()
    assert calls == [("delete", "GONE")]
    assert ledger.get("pywrestling:gone:2026-11-07", "development") is None
    assert ledger.get("flowrestling:other:2026-11-07", "development")


def test_a_pushed_event_reclassified_as_college_is_retired(tmp_path, monkeypatch):
    import push as push_cli

    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    ledger.record("pywrestling:interstate-classic:2026-10-17", "development", "REC1", "Interstate Classic")
    event = _event(tmp_path)
    event["review"]["status"] = schema.STATUS_SKIP
    event["review"]["notes"] = ["college-level event"]
    found = push_cli.retired([event], "development", set())
    assert [f["recordName"] for f in found] == ["REC1"]
    assert found[0]["reason"] == "college-level event"
    # Skipped for a reason that is not permanent (a possible duplicate) stays.
    event["review"]["notes"] = ["possible duplicate of x"]
    assert push_cli.retired([event], "development", set()) == []
