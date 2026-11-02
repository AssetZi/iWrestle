"""CloudKit has no update; --replace deletes and recreates changed events.

The client is a stub that records calls; the ledger is a temp file.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from iwpipe import cktool, ckws, ledger, schema  # noqa: E402


def _event(tmp_path, name="Interstate Classic", key="pywrestling:interstate-classic:2026-10-17"):
    event = schema.blank_event("pywrestling")
    event.update(
        sourceKey=key, name=name,
        eventType="tournament", date="2026-10-17T16:00:00Z",
        address="Venue, 1 Main St, Clarion, PA 16214",
        location={"latitude": 41.2, "longitude": -79.4}, ageGroups=["Youth"],
    )
    event["contact"] = {"firstName": "A", "lastName": "B", "email": "a@b.com", "phone": ""}
    slug = key.split(":")[1]
    logo = tmp_path / f"{slug}-logo.png"; logo.write_bytes(b"\x89PNG logo")
    flyer = tmp_path / f"{slug}-flyer.pdf"; flyer.write_bytes(b"%PDF flyer")
    event["logo"] = str(logo); event["flyer"] = {"url": None, "path": str(flyer)}
    event["review"]["status"] = schema.STATUS_APPROVED
    return event


class FakeClient:
    def __init__(self):
        self.calls = []
        self.fail_create = False

    def upload_asset(self, record_type, field, path):
        return {"receipt": field}

    def create_record(self, record_type, fields):
        self.calls.append(("create",))
        if self.fail_create:
            raise ckws.CKWSError("records/modify failed (503)")
        return f"REC{len(self.calls)}"

    def find_record(self, record_type, name, day):
        return None

    def delete_record(self, name):
        self.calls.append(("delete", name))


def _wire(tmp_path, monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(cktool, "rest_client", lambda environment: client)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    monkeypatch.setattr("iwpipe.assets.ASSET_DIR", tmp_path / "assets")
    return client


def test_content_hash_changes_when_fields_or_assets_change(tmp_path):
    event = _event(tmp_path)
    fields = cktool.build_fields(event)
    logo, flyer = Path(event["logo"]), Path(event["flyer"]["path"])
    first = cktool.content_hash(fields, logo, flyer)
    assert cktool.content_hash(fields, logo, flyer) == first
    assert cktool.content_hash(cktool.build_fields(dict(event, name="Other")), logo, flyer) != first
    flyer.write_bytes(b"%PDF new flyer")
    assert cktool.content_hash(fields, logo, flyer) != first


def test_replace_deletes_then_recreates_only_changed_events(tmp_path, monkeypatch):
    import push as push_cli

    client = _wire(tmp_path, monkeypatch)
    event = _event(tmp_path)
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [event])

    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    assert push_cli.main() == 0
    assert client.calls == [("create",)]
    assert ledger.get(event["sourceKey"], "development")["contentHash"]

    # Unchanged: nothing happens even with --replace.
    client.calls.clear()
    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    assert push_cli.main() == 0
    assert client.calls == []

    # Changed flyer: created again, then the old one deleted.
    Path(event["flyer"]["path"]).write_bytes(b"%PDF the real one")
    assert push_cli.main() == 0
    assert [c[0] for c in client.calls] == ["create", "delete"]


def test_a_failed_create_is_reported_in_the_exit_status(tmp_path, monkeypatch):
    import push as push_cli

    client = _wire(tmp_path, monkeypatch)
    client.fail_create = True
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [_event(tmp_path)])
    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    assert push_cli.main() == 1
    assert ledger.get("pywrestling:interstate-classic:2026-10-17", "development") is None


def test_a_dry_run_leaves_the_ledger_alone(tmp_path, monkeypatch):
    import push as push_cli

    client = _wire(tmp_path, monkeypatch)
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [_event(tmp_path)])
    monkeypatch.setattr(sys, "argv", ["push", str(file), "--dry-run"])
    assert push_cli.main() == 0
    assert client.calls == []
    assert not (tmp_path / "pushed.json").exists()


def test_a_moved_event_replaces_the_record_for_its_old_date(tmp_path, monkeypatch):
    import push as push_cli

    client = _wire(tmp_path, monkeypatch)
    ledger.record("pywrestling:interstate-classic:2026-10-10", "development", "OLD", "Interstate Classic", day="2026-10-10")
    event = _event(tmp_path)
    event["movedFrom"] = "pywrestling:interstate-classic:2026-10-10"
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [event])

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    assert push_cli.main() == 0
    assert client.calls == [("create",), ("delete", "OLD")]
    assert ledger.get("pywrestling:interstate-classic:2026-10-10", "development") is None
    assert ledger.get(event["sourceKey"], "development")


def test_a_listing_gone_from_its_source_is_removed_only_with_replace(tmp_path, monkeypatch):
    import push as push_cli

    client = _wire(tmp_path, monkeypatch)
    ledger.record("pywrestling:gone:2026-11-07", "development", "GONE", "Gone", day="2026-11-07")
    ledger.record("flowrestling:other:2026-11-07", "development", "FLO", "Other", day="2026-11-07")
    ledger.mark_misses("pywrestling", set(), "2026-09-07")
    ledger.mark_misses("pywrestling", set(), "2026-09-14")
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [])

    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    push_cli.main()
    assert client.calls == []

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace", "--dry-run"])
    push_cli.main()
    assert client.calls == []
    assert ledger.get("pywrestling:gone:2026-11-07", "development")

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    assert push_cli.main() == 0
    assert client.calls == [("delete", "GONE")]
    assert ledger.get("pywrestling:gone:2026-11-07", "development") is None
    assert ledger.get("flowrestling:other:2026-11-07", "development")


def test_mass_removals_are_blocked_by_the_cap(tmp_path, monkeypatch):
    """Eighteen of twenty entries gone at once is a broken scrape, not eighteen cancellations."""
    import push as push_cli

    client = _wire(tmp_path, monkeypatch)
    for i in range(20):
        ledger.record(f"pywrestling:e{i}:2026-11-07", "development", f"R{i}", f"E{i}", day="2026-11-07")
    kept = {f"pywrestling:e{i}:2026-11-07" for i in (18, 19)}
    ledger.mark_misses("pywrestling", kept, "2026-09-07")
    ledger.mark_misses("pywrestling", kept, "2026-09-14")
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [])

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    assert push_cli.main() == 1
    assert client.calls == []
    assert ledger.get("pywrestling:e0:2026-11-07", "development")

    # A person can raise the cap for one run.
    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace", "--max-removals", "18"])
    assert push_cli.main() == 0
    assert len([c for c in client.calls if c[0] == "delete"]) == 18


def test_a_pushed_event_reclassified_as_college_is_retired_after_two_runs(tmp_path, monkeypatch):
    import push as push_cli

    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    ledger.record("pywrestling:interstate-classic:2026-10-17", "development", "REC1", "Interstate Classic")
    event = _event(tmp_path)
    event["review"]["status"] = schema.STATUS_SKIP
    event["review"]["notes"] = ["college-level event"]
    # First run: counted, not removed. A dry run counts nothing.
    assert push_cli.retired([event], "development", set(), record=False) == []
    assert push_cli.retired([event], "development", set()) == []
    found = push_cli.retired([event], "development", set())
    assert [f["recordName"] for f in found] == ["REC1"]
    assert found[0]["reason"] == "college-level event"

    # Skipped for a reason that is not permanent (a possible duplicate) stays.
    event["review"]["notes"] = ["possible duplicate of x"]
    assert push_cli.retired([event], "development", set()) == []

    # An exclusion is a person's decision: it takes effect at once.
    ledger.clear_retiring({event["sourceKey"]}, "development")
    event["review"]["notes"] = ["excluded: college open"]
    assert [f["recordName"] for f in push_cli.retired([event], "development", set())] == ["REC1"]

    # A dual meet is read off the name alone: at once too, and the dry run says so.
    ledger.clear_retiring({event["sourceKey"]}, "development")
    event["review"]["notes"] = ["dual meet"]
    assert [f["recordName"] for f in push_cli.retired([event], "development", set(), record=False)] == ["REC1"]
    assert "retireCount" not in ledger.get(event["sourceKey"], "development")
    found = push_cli.retired([event], "development", set())
    assert [f["recordName"] for f in found] == ["REC1"]
    assert found[0]["reason"] == "dual meet"


def test_a_second_push_is_refused_while_one_runs(tmp_path, monkeypatch):
    import push as push_cli

    _wire(tmp_path, monkeypatch)
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [_event(tmp_path)])
    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    with ledger.lock():
        assert push_cli.main() == 1
    assert push_cli.main() == 0


def test_no_key_means_no_push(tmp_path, monkeypatch):
    import push as push_cli

    monkeypatch.setattr(cktool, "rest_client", lambda environment: None)
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [_event(tmp_path)])
    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    assert push_cli.main() == 1


def test_development_allows_a_larger_share_of_removals_than_production(tmp_path, monkeypatch):
    import push as push_cli

    _wire(tmp_path, monkeypatch)
    for environment in ("development", "production"):
        for i in range(40):
            ledger.record(f"trackwrestling:e{i}:2026-11-07", environment, f"R{i}", f"E{i}", day="2026-11-07")

    assert push_cli.removal_cap("trackwrestling", cktool.DEVELOPMENT) == 15
    assert push_cli.removal_cap("trackwrestling", cktool.PRODUCTION) == 5


def test_a_dead_connection_stops_the_push_instead_of_failing_every_event(tmp_path, monkeypatch, capsys):
    import push as push_cli
    import requests

    client = _wire(tmp_path, monkeypatch)

    def unreachable(record_type, fields):
        client.calls.append(("create",))
        raise requests.ConnectionError("HTTPSConnectionPool(host='api.apple-cloudkit.com', port=443): Failed to resolve")

    client.create_record = unreachable
    ledger.record("pywrestling:gone:2026-11-07", "development", "GONE", "Gone", day="2026-11-07")
    ledger.mark_misses("pywrestling", set(), "2026-09-07")
    ledger.mark_misses("pywrestling", set(), "2026-09-14")
    events = [_event(tmp_path, name=f"Event {n}", key=f"pywrestling:event-{n}:2026-10-17") for n in range(8)]
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", events)

    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    assert push_cli.main() == 1
    # Three tries, then it stops; the removal waits for a run that can reach CloudKit.
    assert client.calls == [("create",)] * 3
    assert ledger.get("pywrestling:gone:2026-11-07", "development")
    out = capsys.readouterr().out
    assert "network unreachable" in out and "5 events and 1 removals not attempted" in out


def test_one_failed_request_among_good_ones_does_not_stop_the_push(tmp_path, monkeypatch):
    import push as push_cli
    import requests

    client = _wire(tmp_path, monkeypatch)
    real = client.create_record

    def flaky(record_type, fields):
        if len(client.calls) % 2 == 0:
            client.calls.append(("create",))
            raise requests.ConnectionError("reset")
        return real(record_type, fields)

    client.create_record = flaky
    events = [_event(tmp_path, name=f"Event {n}", key=f"pywrestling:event-{n}:2026-10-17") for n in range(8)]
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", events)
    monkeypatch.setattr(sys, "argv", ["push", str(file)])
    assert push_cli.main() == 1
    assert len(client.calls) == 8


def test_a_pushed_listing_renamed_delete_is_retired_after_two_runs(tmp_path, monkeypatch):
    import push as push_cli

    client = _wire(tmp_path, monkeypatch)
    event = _event(tmp_path, name="Bobcat JV-Delete", key="pywrestling:bobcat-jv:2026-10-17")
    ledger.record(event["sourceKey"], "development", "OLD", "Bobcat JV", day="2026-10-17")
    event["review"] = {"status": schema.STATUS_SKIP, "notes": ["cancelled or placeholder listing"]}
    file = tmp_path / "events.json"
    schema.dump(file, "pywrestling", [event])
    monkeypatch.setattr(sys, "argv", ["push", str(file), "--replace"])
    push_cli.main()
    assert client.calls == []
    push_cli.main()
    assert client.calls == [("delete", "OLD")]
