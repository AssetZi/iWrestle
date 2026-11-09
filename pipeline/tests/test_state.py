"""The cloud routine keeps its working data in a private repo between runs.

A local bare repo stands in for GitHub.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from iwpipe import state  # noqa: E402


@pytest.fixture
def remote(tmp_path):
    path = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(path)], check=True)
    return str(path)


def _data(root: Path) -> Path:
    folder = root / "assets" / "pywrestling_cup_2026-12-05"
    folder.mkdir(parents=True)
    (folder / "logo.png").write_bytes(b"logo")
    (folder / "flyer.pdf").write_bytes(b"%PDF flyer")
    (folder / "flyer-page1.png").write_bytes(b"big preview")
    (folder / "fields.json").write_text("{}")
    (root / "flo-details.json").write_text('{"a": 1}')
    (root / "enrich-cache.json").write_text("{}")
    (root / "events.flowrestling.20261109.json").write_text("{}")
    return folder


def test_a_fresh_clone_gets_back_what_the_last_run_kept(tmp_path, remote):
    mac = tmp_path / "mac"
    _data(mac)
    assert state.push(remote, tmp_path / "mac-state", mac) > 0

    cloud = tmp_path / "cloud"
    cloud.mkdir()
    assert state.pull(remote, tmp_path / "cloud-state", cloud) == 4
    folder = cloud / "assets" / "pywrestling_cup_2026-12-05"
    assert (folder / "logo.png").read_bytes() == b"logo"
    assert (folder / "flyer.pdf").read_bytes() == b"%PDF flyer"
    assert (cloud / "flo-details.json").read_text() == '{"a": 1}'
    # Rebuilt every run, or not the pipeline's to keep.
    assert not (folder / "flyer-page1.png").exists()
    assert not (folder / "fields.json").exists()
    assert not (cloud / "events.flowrestling.20261109.json").exists()


def test_a_second_run_commits_only_what_changed_and_deletions(tmp_path, remote):
    data = tmp_path / "data"
    folder = _data(data)
    state.push(remote, tmp_path / "s1", data)
    assert state.push(remote, tmp_path / "s1", data) == 0

    (folder / "logo.png").write_bytes(b"new logo")
    (data / "enrich-cache.json").unlink()
    # One of four files is more than the 10% a push may drop on its own.
    assert state.push(remote, tmp_path / "s1", data, allow_shrink=True) == 2

    other = tmp_path / "other"
    other.mkdir()
    state.pull(remote, tmp_path / "s2", other)
    assert (other / "assets" / folder.name / "logo.png").read_bytes() == b"new logo"
    assert not (other / "enrich-cache.json").exists()


def test_pull_keeps_local_files_the_private_repo_lacks(tmp_path, remote):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)
    local = tmp_path / "local"
    extra = local / "assets" / "trackwrestling_new_2026-12-12"
    extra.mkdir(parents=True)
    (extra / "logo.png").write_bytes(b"only here")
    state.pull(remote, tmp_path / "s2", local)
    assert (extra / "logo.png").read_bytes() == b"only here"


def test_no_repo_configured_is_an_error_not_an_empty_run(tmp_path):
    with pytest.raises(state.StateError, match="PIPELINE_STATE_REPO"):
        state.pull("", tmp_path / "s", tmp_path)


def test_the_token_goes_through_the_environment_not_the_command_line(monkeypatch):
    monkeypatch.setenv("PIPELINE_STATE_TOKEN", "tok")
    env = state._git_env()
    assert env["GIT_CONFIG_KEY_0"] == "http.https://github.com/.extraheader"
    assert env["GIT_CONFIG_VALUE_0"].startswith("AUTHORIZATION: basic ")
    assert "tok" not in env["GIT_CONFIG_VALUE_0"]


class _Response:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def test_an_open_ledger_pr_stops_the_cloud_routine(monkeypatch, capsys):
    import ledger_check

    monkeypatch.setattr(ledger_check.state, "ledger_differences", lambda *a: [])
    prs = [
        {"number": 15, "head": {"ref": "data/ledger-2026-11-09"}, "html_url": "https://github.com/AssetZi/iWrestle/pull/15"},
        {"number": 18, "head": {"ref": "feat/cloud"}, "html_url": "u"},
    ]
    monkeypatch.setattr(ledger_check.requests, "get", lambda *a, **k: _Response(prs))
    assert ledger_check.main() == 1
    assert "#15 data/ledger-2026-11-09" in capsys.readouterr().out

    monkeypatch.setattr(ledger_check.requests, "get", lambda *a, **k: _Response(prs[1:]))
    assert ledger_check.main() == 0


def test_a_failed_check_counts_as_open(monkeypatch):
    import ledger_check

    monkeypatch.setattr(ledger_check.state, "ledger_differences", lambda *a: [])

    def down(*a, **k):
        raise ledger_check.requests.ConnectionError("no network")

    monkeypatch.setattr(ledger_check.requests, "get", down)
    assert ledger_check.main() == 1


def test_a_push_without_a_pull_first_is_refused(tmp_path, remote):
    """A fresh clone that skipped or failed its pull has an empty data/.
    Mirroring that would delete everything the last run kept."""
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "mac-state", data)

    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(state.StateError, match="pull"):
        state.push(remote, tmp_path / "cloud-state", empty)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    assert state.pull(remote, tmp_path / "fresh-state", fresh) == 4


def test_a_push_that_would_drop_most_files_is_refused(tmp_path, remote):
    data = tmp_path / "data"
    folders = []
    for n in range(10):
        folder = data / "assets" / f"pywrestling_e{n}_2026-12-05"
        folder.mkdir(parents=True)
        (folder / "logo.png").write_bytes(b"logo")
        folders.append(folder)
    state.push(remote, tmp_path / "s", data)

    for folder in folders[:5]:
        (folder / "logo.png").unlink()
    with pytest.raises(state.StateError, match="5 of 10"):
        state.push(remote, tmp_path / "s", data)
    assert state.push(remote, tmp_path / "s", data, allow_shrink=True) == 5


def test_a_push_after_someone_else_pushed_is_refused(tmp_path, remote):
    """Two machines: the second must pull the first's run before pushing."""
    a, b = tmp_path / "a", tmp_path / "b"
    _data(a)
    state.push(remote, tmp_path / "sa", a)
    b.mkdir()
    state.pull(remote, tmp_path / "sb", b)

    (a / "enrich-cache.json").write_text('{"new": 1}')
    state.push(remote, tmp_path / "sa", a)
    with pytest.raises(state.StateError, match="pull"):
        state.push(remote, tmp_path / "sb", b)


def test_the_ledger_copy_shows_a_ledger_that_never_reached_main(tmp_path, remote):
    """In the cloud, pushed.json lives only in the session's clone until its
    pull request merges. The private repo keeps a copy, so a run whose
    ledger never landed is caught before it pushes those events again."""
    data = tmp_path / "data"
    _data(data)
    (data / "pushed.json").write_text('{"development:a": {"recordName": "R1"}}')
    state.push(remote, tmp_path / "s1", data)

    clone = tmp_path / "clone"
    clone.mkdir()
    (clone / "pushed.json").write_text("{}")
    state.pull(remote, tmp_path / "s2", clone)
    assert (clone / "pushed.json").read_text() == "{}"
    assert state.ledger_differences(tmp_path / "s2", clone) == ["pushed.json"]

    (clone / "pushed.json").write_text('{\n  "development:a": {"recordName": "R1"}\n}')
    assert state.ledger_differences(tmp_path / "s2", clone) == []


def test_leftover_files_from_a_failed_push_are_not_pulled(tmp_path, remote):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s", data)
    stray = tmp_path / "s" / "data" / "assets" / "stray_2026-12-05" / "logo.png"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"from a push that never landed")
    target = tmp_path / "target"
    target.mkdir()
    state.pull(remote, tmp_path / "s", target)
    assert not (target / "assets" / "stray_2026-12-05").exists()


def test_existing_git_config_from_the_environment_is_kept(monkeypatch):
    monkeypatch.setenv("PIPELINE_STATE_TOKEN", "tok")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "http.proxy")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "http://proxy:3128")
    env = state._git_env()
    assert env["GIT_CONFIG_COUNT"] == "2"
    assert env["GIT_CONFIG_KEY_0"] == "http.proxy"
    assert env["GIT_CONFIG_KEY_1"] == "http.https://github.com/.extraheader"


def test_the_check_uses_the_configured_repo_and_token(monkeypatch):
    """A cloud clone's origin can be a local proxy URL, and anonymous API
    calls from shared cloud IPs run out of rate limit."""
    import ledger_check

    monkeypatch.setenv("PIPELINE_STATE_TOKEN", "tok")
    seen = {}

    def get(url, **kwargs):
        seen["url"], seen["auth"] = url, kwargs["headers"].get("Authorization")
        return _Response([])

    monkeypatch.setattr(ledger_check.requests, "get", get)
    monkeypatch.setattr(ledger_check.state, "ledger_differences", lambda *a: [])
    assert ledger_check.main() == 0
    assert seen == {"url": "https://api.github.com/repos/AssetZi/iWrestle/pulls", "auth": "Bearer tok"}


def test_a_ledger_that_never_reached_main_stops_the_cloud_routine(monkeypatch, capsys):
    import ledger_check

    monkeypatch.setattr(ledger_check.requests, "get", lambda *a, **k: _Response([]))
    monkeypatch.setattr(ledger_check.state, "ledger_differences", lambda *a: ["pushed.json"])
    assert ledger_check.main() == 1
    assert "pushed.json" in capsys.readouterr().out
