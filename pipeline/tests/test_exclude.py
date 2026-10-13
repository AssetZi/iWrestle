"""Excluding by key: the key has to name something the source still lists."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from iwpipe import cktool, exclusions, ledger  # noqa: E402


def _wire(tmp_path, monkeypatch, files):
    import exclude as exclude_cli

    monkeypatch.setattr(exclude_cli, "DATA_DIR", tmp_path)
    monkeypatch.setattr(exclusions, "EXCLUDED_PATH", tmp_path / "excluded.json")
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    monkeypatch.setattr(cktool, "rest_client", lambda environment: None)
    for day, keys in files.items():
        events = [{"sourceKey": key, "name": "Delete Delete Delete", "date": "2026-12-19T17:00:00Z"} for key in keys]
        (tmp_path / f"events.trackwrestling.{day}.json").write_text(json.dumps({"source": "trackwrestling", "events": events}))
    return exclude_cli


def _run(exclude_cli, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["exclude", *argv])
    return exclude_cli.main()


BARE = "trackwrestling:delete-delete-delete:2026-12-19"


def test_a_key_the_source_has_since_split_is_listed_not_excluded(tmp_path, monkeypatch, capsys):
    """Last week's bare key matched an old file; this week's listing has a suffix."""
    cli = _wire(tmp_path, monkeypatch, {"20261005": [BARE], "20261012": [BARE + ":1028577132"]})
    assert _run(cli, monkeypatch, BARE) == 1
    assert exclusions.load() == {}
    assert BARE + ":1028577132" in capsys.readouterr().out

    assert _run(cli, monkeypatch, BARE + ":1028577132") == 0
    assert list(exclusions.load()) == [BARE + ":1028577132"]


def test_a_key_that_names_nothing_is_refused(tmp_path, monkeypatch):
    cli = _wire(tmp_path, monkeypatch, {"20261012": [BARE]})
    assert _run(cli, monkeypatch, "trackwrestling:delete-delete:2026-12-19") == 1
    assert exclusions.load() == {}


def test_a_key_only_an_older_file_has_is_still_excludable(tmp_path, monkeypatch):
    """The listing left the source but its record may still be in CloudKit."""
    cli = _wire(tmp_path, monkeypatch, {"20261005": [BARE], "20261012": ["trackwrestling:other:2026-12-19"]})
    assert _run(cli, monkeypatch, BARE) == 0
    assert list(exclusions.load()) == [BARE]
