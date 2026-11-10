"""The cloud routine keeps its working data in a private repo between runs.

A local bare repo stands in for GitHub.
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

from iwpipe import state  # noqa: E402


@pytest.fixture(autouse=True)
def writer(monkeypatch):
    """Tests act as the cloud routine, the private repo's one writer, whose
    ledger reached GitHub unless a test says otherwise."""
    monkeypatch.setenv("PIPELINE_STATE_WRITER", "1")
    monkeypatch.setattr(state, "ledger_landed", lambda data_dir: True)


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
    assert state.pull(remote, tmp_path / "cloud-state", cloud) == 5
    folder = cloud / "assets" / "pywrestling_cup_2026-12-05"
    assert (folder / "logo.png").read_bytes() == b"logo"
    assert (folder / "flyer.pdf").read_bytes() == b"%PDF flyer"
    assert (cloud / "flo-details.json").read_text() == '{"a": 1}'
    # Rebuilt every run.
    assert not (folder / "flyer-page1.png").exists()
    assert not (folder / "fields.json").exists()


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
    assert state.pull(remote, tmp_path / "fresh-state", fresh) == 5


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
    assert ledger_check.main() == 0
    assert seen == {"url": "https://api.github.com/repos/AssetZi/iWrestle/pulls", "auth": "Bearer tok"}


def test_the_newest_collected_file_of_each_source_is_kept(tmp_path, remote):
    """Publishing to production reads the newest collected file per source;
    a fresh clone, or a Mac that hasn't collected in weeks, needs the
    cloud run's."""
    data = tmp_path / "data"
    _data(data)
    (data / "events.flowrestling.20261102.json").write_text("old")
    (data / "events.pywrestling.20261109.json").write_text("py")
    state.push(remote, tmp_path / "s1", data)

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    state.pull(remote, tmp_path / "s2", fresh)
    assert (fresh / "events.flowrestling.20261109.json").read_text() == "{}"
    assert (fresh / "events.pywrestling.20261109.json").read_text() == "py"
    assert not (fresh / "events.flowrestling.20261102.json").exists()

    # A newer collect replaces it in the private repo; the local older
    # file stays, as history.
    (data / "events.pywrestling.20261116.json").write_text("newer")
    state.pull(remote, tmp_path / "s1", data)
    state.push(remote, tmp_path / "s1", data)
    state.pull(remote, tmp_path / "s2", fresh)
    assert (fresh / "events.pywrestling.20261109.json").read_text() == "py"
    assert (fresh / "events.pywrestling.20261116.json").read_text() == "newer"


def test_a_file_another_run_deleted_is_deleted_on_pull_too(tmp_path, remote):
    """Otherwise the next push from this machine brings it back."""
    cloud, mac = tmp_path / "cloud", tmp_path / "mac"
    folder = _data(cloud)
    state.push(remote, tmp_path / "sc", cloud)
    mac.mkdir()
    state.pull(remote, tmp_path / "sm", mac)

    state.pull(remote, tmp_path / "sc", cloud)
    (folder / "flyer.pdf").unlink()
    state.push(remote, tmp_path / "sc", cloud, allow_shrink=True)

    state.pull(remote, tmp_path / "sm", mac)
    assert not (mac / "assets" / folder.name / "flyer.pdf").exists()
    assert (mac / "assets" / folder.name / "logo.png").exists()


def test_a_run_that_never_pushed_its_state_blocks_the_next(tmp_path, remote):
    """A run that dies after creating records but before state-push takes
    its ledger with it; the next run would create those records again."""
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)

    state.begin_run(remote, tmp_path / "s1")
    other = tmp_path / "other"
    other.mkdir()
    state.pull(remote, tmp_path / "s2", other)
    with pytest.raises(state.StateError, match="never got its ledger onto GitHub"):
        state.begin_run(remote, tmp_path / "s2")

    # The run that finishes clears it.
    state.push(remote, tmp_path / "s1", data)
    state.pull(remote, tmp_path / "s2", other)
    state.begin_run(remote, tmp_path / "s2")


def test_a_rejected_git_push_says_to_pull_again(tmp_path, remote, monkeypatch):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)
    real = state._git

    def git(*args, cwd=None):
        if args[0] == "push":
            raise state.StateError("git push failed: rejected")
        return real(*args, cwd=cwd)

    monkeypatch.setattr(state, "_git", git)
    (data / "enrich-cache.json").write_text('{"x": 1}')
    with pytest.raises(state.StateError, match="state-pull"):
        state.push(remote, tmp_path / "s1", data)


def test_only_the_cloud_routine_writes_the_private_repo(tmp_path, remote, monkeypatch):
    """Two writers can each overwrite or unguard the other's run. The Mac
    seeds the empty repo once, then only pulls."""
    data = tmp_path / "data"
    _data(data)
    monkeypatch.delenv("PIPELINE_STATE_WRITER")
    assert state.push(remote, tmp_path / "mac", data) > 0
    state.pull(remote, tmp_path / "mac", data)
    (data / "enrich-cache.json").write_text('{"older": 1}')
    with pytest.raises(state.StateError, match="only the cloud routine"):
        state.push(remote, tmp_path / "mac", data)
    with pytest.raises(state.StateError, match="only the cloud routine"):
        state.begin_run(remote, tmp_path / "mac")


def test_clearing_a_run_mark_does_not_count_as_a_pull(tmp_path, remote):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)
    state.begin_run(remote, tmp_path / "s1")

    stale = tmp_path / "stale"
    _data(stale)
    assert state.clear_run(remote, tmp_path / "s2", force=True)
    with pytest.raises(state.StateError, match="state-pull"):
        state.push(remote, tmp_path / "s2", stale)


def test_a_push_clears_only_the_run_mark_it_set(tmp_path, remote):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)
    state.begin_run(remote, tmp_path / "s1")

    other = tmp_path / "other"
    other.mkdir()
    state.pull(remote, tmp_path / "s2", other)
    state.push(remote, tmp_path / "s2", other)
    with pytest.raises(state.StateError, match="never got its ledger onto GitHub"):
        state.begin_run(remote, tmp_path / "s3")


def test_a_refused_push_does_not_advise_a_pull(tmp_path, remote):
    """A pull would overwrite the run's new files with the repo's older ones."""
    a, b = tmp_path / "a", tmp_path / "b"
    _data(a)
    state.push(remote, tmp_path / "sa", a)
    b.mkdir()
    state.pull(remote, tmp_path / "sb", b)
    state.push(remote, tmp_path / "sa", a)
    (a / "enrich-cache.json").write_text('{"new": 1}')
    state.push(remote, tmp_path / "sa", a)
    with pytest.raises(state.StateError) as error:
        state.push(remote, tmp_path / "sb", b)
    assert "do not run make state-pull" in str(error.value)


def test_a_push_that_drops_a_cache_is_refused(tmp_path, remote):
    data = tmp_path / "data"
    for n in range(30):
        folder = data / "assets" / f"e{n}"
        folder.mkdir(parents=True)
        (folder / "logo.png").write_bytes(b"logo")
    (data / "enrich-cache.json").write_text("{}")
    state.push(remote, tmp_path / "s", data)
    (data / "enrich-cache.json").unlink()
    with pytest.raises(state.StateError, match="enrich-cache.json"):
        state.push(remote, tmp_path / "s", data)


def test_a_failed_push_that_was_not_a_conflict_says_to_retry(tmp_path, remote, monkeypatch):
    """A network error at the last step is not another writer; a retry is
    safe, and stopping would lose the run's files and block next week."""
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s", data)
    real = state._git

    def git(*args, cwd=None):
        if args[0] == "push":
            raise state.StateError("git push failed: fatal: unable to access: Could not resolve host")
        return real(*args, cwd=cwd)

    monkeypatch.setattr(state, "_git", git)
    (data / "enrich-cache.json").write_text('{"x": 1}')
    with pytest.raises(state.StateError) as error:
        state.push(remote, tmp_path / "s", data)
    assert "retry make state-push" in str(error.value)
    assert "Something else wrote" not in str(error.value)


def test_the_private_repo_must_be_private(monkeypatch):
    """The caches hold organizer emails; a public repo would publish them."""
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        return _Response({"private": visibility["private"]})

    visibility = {"private": False}
    monkeypatch.setattr(state.requests, "get", get)
    with pytest.raises(state.StateError, match="not private"):
        state._require_private("https://github.com/AssetZi/iwrestle-pipeline-data.git")
    assert calls == ["https://api.github.com/repos/AssetZi/iwrestle-pipeline-data"]

    visibility["private"] = True
    state._require_private("https://github.com/AssetZi/iwrestle-pipeline-data.git")

    def down(*a, **k):
        raise state.requests.ConnectionError("no network")

    monkeypatch.setattr(state.requests, "get", down)
    with pytest.raises(state.StateError, match="private"):
        state._require_private("https://github.com/AssetZi/iwrestle-pipeline-data.git")


def test_a_recent_run_mark_is_not_cleared_without_force(tmp_path, remote):
    """It may belong to a run still going, whose push would then be refused."""
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)
    state.begin_run(remote, tmp_path / "s1")
    with pytest.raises(state.StateError, match="still be running"):
        state.clear_run(remote, tmp_path / "s2")
    assert state.clear_run(remote, tmp_path / "s2", force=True)


def test_cloud_start_twice_in_one_session_does_not_undo_the_run(tmp_path, remote):
    """A second pull would copy the repo's older files over this run's."""
    data = tmp_path / "data"
    folder = _data(data)
    state.push(remote, tmp_path / "s", data)
    state.pull(remote, tmp_path / "s", data)
    state.begin_run(remote, tmp_path / "s")
    (folder / "logo.png").write_bytes(b"drawn this run")

    assert state.pull(remote, tmp_path / "s", data) == 0
    assert (folder / "logo.png").read_bytes() == b"drawn this run"
    state.begin_run(remote, tmp_path / "s")
    state.push(remote, tmp_path / "s", data)
    state.begin_run(remote, tmp_path / "s")  # the mark was cleared


def test_a_pulled_collected_file_is_dated_by_its_name(tmp_path, remote):
    """make promote refuses a file older than STALE_DAYS by its modification
    time; a pull must not make an old file look new."""
    import datetime as dt

    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    state.pull(remote, tmp_path / "s2", fresh)
    stamp = dt.datetime.fromtimestamp((fresh / "events.flowrestling.20261109.json").stat().st_mtime, dt.timezone.utc)
    assert stamp.date() == dt.date(2026, 11, 9)


def test_a_run_whose_ledger_never_reached_github_keeps_its_mark(tmp_path, remote, monkeypatch, capsys):
    """Its records are in CloudKit but its ledger is only in this session.
    The data is still kept; the mark stays so the next run stops, and the
    ledger is saved in the private repo to recover from."""
    data = tmp_path / "data"
    _data(data)
    (data / "pushed.json").write_text('{"development:a": {"recordName": "R1"}}')
    state.push(remote, tmp_path / "s1", data)
    state.begin_run(remote, tmp_path / "s1")

    monkeypatch.setattr(state, "ledger_landed", lambda data_dir: False)
    (data / "enrich-cache.json").write_text('{"new": 1}')
    with pytest.raises(state.StateError, match="not on GitHub"):
        state.push(remote, tmp_path / "s1", data)

    other = tmp_path / "other"
    other.mkdir()
    state.pull(remote, tmp_path / "s2", other)
    assert (other / "enrich-cache.json").read_text() == '{"new": 1}'
    assert (tmp_path / "s2" / "ledger" / "pushed.json").read_text() == '{"development:a": {"recordName": "R1"}}'
    with pytest.raises(state.StateError, match=r"\(pushed.json\) are saved under ledger/"):
        state.begin_run(remote, tmp_path / "s2")


def _public_repo(tmp_path, ledger_text, branch):
    """A clone of the app repo whose origin has pushed.json on a branch."""
    import subprocess as sp

    origin = tmp_path / "origin.git"
    sp.run(["git", "init", "--quiet", "--bare", str(origin)], check=True)
    work = tmp_path / "work"
    sp.run(["git", "clone", "--quiet", str(origin), str(work)], check=True, capture_output=True)
    git = ["git", "-C", str(work), "-c", "user.name=t", "-c", "user.email=t@t"]
    (work / "pipeline" / "data").mkdir(parents=True)
    (work / "pipeline" / "data" / "pushed.json").write_text("{}")
    sp.run(git + ["add", "."], check=True)
    sp.run(git + ["commit", "--quiet", "-m", "main"], check=True)
    sp.run(git + ["push", "--quiet", "origin", "HEAD:refs/heads/main"], check=True, capture_output=True)
    if branch:
        sp.run(git + ["checkout", "--quiet", "-b", branch], check=True)
        (work / "pipeline" / "data" / "pushed.json").write_text(ledger_text)
        sp.run(git + ["commit", "--quiet", "-am", "ledger"], check=True)
        sp.run(git + ["push", "--quiet", "origin", f"HEAD:refs/heads/{branch}"], check=True, capture_output=True)
        sp.run(git + ["checkout", "--quiet", "main"], check=True)
    return work


def test_the_ledger_has_landed_when_github_has_the_same_file(tmp_path):
    ledger_text = '{"development:a": {"recordName": "R1"}}'
    work = _public_repo(tmp_path, ledger_text, "data/ledger-2026-11-16")
    data = work / "pipeline" / "data"
    branch = lambda: {"data/ledger-2026-11-16"}  # noqa: E731
    data.joinpath("pushed.json").write_text('{\n  "development:a": {"recordName": "R1"}\n}')
    assert state._ledger_landed(data, work, branch)

    data.joinpath("pushed.json").write_text('{"development:a": {"recordName": "R2"}}')
    assert not state._ledger_landed(data, work, branch)

    # A run that pushed nothing: its ledger is main's.
    data.joinpath("pushed.json").write_text("{}")
    assert state._ledger_landed(data, work, set)


def test_a_ledger_branch_without_an_open_pr_has_not_landed(tmp_path):
    """Nothing would merge it, and the next run, finding no open pull
    request, would start from main's older ledger."""
    ledger_text = '{"development:a": {"recordName": "R1"}}'
    work = _public_repo(tmp_path, ledger_text, "data/ledger-2026-11-16")
    data = work / "pipeline" / "data"
    data.joinpath("pushed.json").write_text(ledger_text)
    assert not state._ledger_landed(data, work, set)


def test_an_exclusion_alone_has_to_land_too(tmp_path):
    """A run that only excluded an event leaves pushed.json as main's; its
    excluded.json still has to reach GitHub, or the event comes back."""
    work = _public_repo(tmp_path, "{}", None)
    data = work / "pipeline" / "data"
    data.joinpath("excluded.json").write_text('{"pywrestling:x:2026-12-05": {"reason": "duplicate"}}')
    assert not state._ledger_landed(data, work, set)


def test_the_private_check_covers_proxy_urls_and_skips_only_local_paths(monkeypatch):
    seen = []
    monkeypatch.setattr(state.github, "token", lambda: "tok")
    monkeypatch.setattr(state.requests, "get", lambda url, **k: seen.append(url) or _Response({"private": True}))
    state._require_private("http://127.0.0.1:8080/git/AssetZi/iwrestle-pipeline-data")
    state._require_private("git@github.com:AssetZi/iwrestle-pipeline-data.git")
    state._require_private("/tmp/remote.git")
    state._require_private("file:///tmp/remote.git")
    assert seen == ["https://api.github.com/repos/AssetZi/iwrestle-pipeline-data"] * 2


def test_no_access_to_the_private_repo_asks_for_a_token_not_a_retry(monkeypatch):
    class NotFound(_Response):
        status_code = 404

        def raise_for_status(self):
            raise state.requests.HTTPError("404 Not Found", response=self)

    monkeypatch.setattr(state.github, "token", lambda: "")
    monkeypatch.setattr(state.requests, "get", lambda *a, **k: NotFound({}))
    with pytest.raises(state.StateError) as error:
        state._require_private("https://github.com/AssetZi/iwrestle-pipeline-data.git")
    assert "token" in str(error.value) and "Retry" not in str(error.value)


def test_the_mac_uses_the_gh_login_when_no_token_is_set(monkeypatch):
    monkeypatch.delenv("PIPELINE_STATE_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(state.github.shutil, "which", lambda name: "/usr/local/bin/gh")

    class Done:
        returncode, stdout = 0, "gho_x\n"

    monkeypatch.setattr(state.github.subprocess, "run", lambda *a, **k: Done())
    assert state.github.token() == "gho_x"


def test_clearing_a_run_mark_is_the_writers_job(tmp_path, remote, monkeypatch):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s1", data)
    state.begin_run(remote, tmp_path / "s1")
    monkeypatch.delenv("PIPELINE_STATE_WRITER")
    with pytest.raises(state.StateError, match="only the cloud routine"):
        state.clear_run(remote, tmp_path / "s2", force=True)


def test_a_push_the_server_took_before_the_connection_dropped_counts(tmp_path, remote, monkeypatch):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s", data)
    real = state._git

    def git(*args, cwd=None):
        out = real(*args, cwd=cwd)
        if args[0] == "push":
            raise state.StateError("git push failed: error: RPC failed; rejected after send")
        return out

    monkeypatch.setattr(state, "_git", git)
    (data / "enrich-cache.json").write_text('{"x": 1}')
    assert state.push(remote, tmp_path / "s", data) > 0



def test_a_run_start_whose_push_failed_says_to_rerun_cloud_start(tmp_path, remote, monkeypatch):
    """Not state-push: the skill forbids that after a failed cloud-start."""
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s", data)
    state.pull(remote, tmp_path / "s", data)
    real = state._git

    def git(*args, cwd=None):
        if args[0] == "push":
            raise state.StateError("git push failed: Could not resolve host")
        return real(*args, cwd=cwd)

    monkeypatch.setattr(state, "_git", git)
    with pytest.raises(state.StateError) as error:
        state.begin_run(remote, tmp_path / "s")
    assert "make cloud-start" in str(error.value) and "state-push" not in str(error.value)

    # The mark never reached GitHub: a second cloud-start pulls and starts.
    monkeypatch.setattr(state, "_git", real)
    state.pull(remote, tmp_path / "s", data)
    state.begin_run(remote, tmp_path / "s")
    assert (tmp_path / "s" / "RUNNING").exists()


def test_a_run_start_that_reached_github_unconfirmed_is_this_runs_own(tmp_path, remote, monkeypatch):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s", data)
    state.pull(remote, tmp_path / "s", data)
    real = state._git

    def git(*args, cwd=None):
        out = real(*args, cwd=cwd)
        # The push arrives, then the reply and the check after it fail.
        if args[0] == "push" or (args[0] == "fetch" and git.pushed):
            git.pushed = True
            raise state.StateError(f"git {args[0]} failed: connection reset")
        return out

    git.pushed = False
    monkeypatch.setattr(state, "_git", git)
    with pytest.raises(state.StateError, match="cloud-start"):
        state.begin_run(remote, tmp_path / "s")
    assert git.pushed
    monkeypatch.setattr(state, "_git", real)
    state.pull(remote, tmp_path / "s", data)
    state.begin_run(remote, tmp_path / "s")  # its own mark: no refusal
    state.push(remote, tmp_path / "s", data)
    assert not (tmp_path / "s" / "RUNNING").exists()


def test_a_pull_keeps_a_collected_file_edited_here(tmp_path, remote):
    """make exclude and make review edit the newest collected file on the
    Mac; a later pull must not bring back the cloud's unedited copy."""
    cloud, mac = tmp_path / "cloud", tmp_path / "mac"
    _data(cloud)
    state.push(remote, tmp_path / "sc", cloud)
    mac.mkdir()
    state.pull(remote, tmp_path / "sm", mac)

    edited = '{"events": [{"review": {"status": "skip"}}]}'
    (mac / "events.flowrestling.20261109.json").write_text(edited)
    state.pull(remote, tmp_path / "sc", cloud)
    (cloud / "enrich-cache.json").write_text('{"new": 1}')
    state.push(remote, tmp_path / "sc", cloud)

    state.pull(remote, tmp_path / "sm", mac)
    assert (mac / "events.flowrestling.20261109.json").read_text() == edited
    assert (mac / "enrich-cache.json").read_text() == '{"new": 1}'
    assert state.kept_local == ["events.flowrestling.20261109.json"]


def test_a_retry_after_a_push_github_took_is_not_a_conflict(tmp_path, remote, monkeypatch):
    """The reply and the check after it were lost; the retry finds the
    run's own commit on GitHub and carries on."""
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s", data)
    real = state._git

    def git(*args, cwd=None):
        out = real(*args, cwd=cwd)
        if args[0] == "push" or (args[0] == "fetch" and git.pushed):
            git.pushed = True
            raise state.StateError(f"git {args[0]} failed: connection reset")
        return out

    git.pushed = False
    monkeypatch.setattr(state, "_git", git)
    (data / "enrich-cache.json").write_text('{"x": 1}')
    with pytest.raises(state.StateError, match="retry make state-push"):
        state.push(remote, tmp_path / "s", data)
    monkeypatch.setattr(state, "_git", real)
    assert state.push(remote, tmp_path / "s", data) == 0


def test_a_stranded_run_saves_every_ledger_file(tmp_path, remote, monkeypatch):
    data = tmp_path / "data"
    _data(data)
    state.push(remote, tmp_path / "s", data)
    state.pull(remote, tmp_path / "s", data)
    state.begin_run(remote, tmp_path / "s")
    (data / "excluded.json").write_text('{"pywrestling:x:2026-12-05": {"reason": "duplicate"}}')
    monkeypatch.setattr(state, "ledger_landed", lambda data_dir: False)
    with pytest.raises(state.StateError, match="not on GitHub"):
        state.push(remote, tmp_path / "s", data)
    saved = tmp_path / "s" / "ledger"
    assert (saved / "excluded.json").exists()
    assert not (saved / "pushed.json").exists()


def test_ssh_remotes_without_a_user_are_checked_too(monkeypatch):
    seen = []
    monkeypatch.setattr(state.github, "token", lambda: "tok")
    monkeypatch.setattr(state.requests, "get", lambda url, **k: seen.append(url) or _Response({"private": True}))
    state._require_private("github.com:AssetZi/iwrestle-pipeline-data.git")
    state._require_private("gh-alias:AssetZi/iwrestle-pipeline-data")
    assert seen == ["https://api.github.com/repos/AssetZi/iwrestle-pipeline-data"] * 2
