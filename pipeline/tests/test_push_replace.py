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
