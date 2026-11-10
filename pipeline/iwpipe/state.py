"""The pipeline's working data, kept in a private git repo between runs.

The cloud routine starts from a fresh clone, which has none of the
gitignored files a run depends on: the rendered logos and flyers the push
compares byte for byte, the downloaded banners and flyer PDFs, and the Flo
and enrichment caches. `pull` copies them out of the private repo into
data/, and `push` copies them back and commits. This repo is public; those
files hold organizer emails, so they never go in it.

The newest collected file of each source (data/events.<source>.<date>.json)
is kept too: publishing to production reads it, and a machine that did not
run this week's collect has none or an old one.

flyer-page1.png and fields.json are rebuilt on every run and not kept.
geocache.json is tracked in this repo, so it is not kept there too.

Only the cloud routine writes the private repo (PIPELINE_STATE_WRITER=1
in its environment). The Mac seeds the empty repo once and after that only
pulls, to publish to production from this week's files. With one writer,
no machine can overwrite another's newer files or clear its run mark.

begin_run marks a run as started in the private repo, and that run's push
clears the mark. A mark still there at the next begin_run means a run died
after it may have created development records but before its ledger was
kept anywhere.

`push` also keeps a copy of pushed.json under ledger/. It is never copied
back into data/: main's ledger is the one the pipeline uses. The copy only
lets a cloud run see that the last run's ledger never reached main
(ledger_differences), before it pushes those events a second time.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import DATA_DIR, PIPELINE_ROOT

STATE_REPO = os.getenv("PIPELINE_STATE_REPO", "")
STATE_DIR = PIPELINE_ROOT / ".state"
BRANCH = "main"

DATA_FILES = ("flo-details.json", "enrich-cache.json")
ASSET_FILES = ("logo.png", "flyer.pdf", "source-flyer.pdf", "banner.jpg")
LEDGER_FILE = "pushed.json"
EVENTS_FILE = re.compile(r"events\.([a-z]+)\.(\d{8})\.json")
RUNNING = "RUNNING"

# A push may drop at most this share of the kept files (a flyer that names
# a different event is deleted on purpose), and no cache, unless
# allow_shrink is given.
MAX_SHRINK = 0.10
WRITER_ENV = "PIPELINE_STATE_WRITER"
# A run mark younger than this may belong to a run still going.
RUN_MARK_HOURS = 6
DO_NOT_PULL = (
    "Stop and report this; do not run make state-pull, which would overwrite "
    "this run's new files with older ones."
)


class StateError(RuntimeError):
    pass


def _git_env() -> dict[str, str]:
    """Credentials for the private repo. On this Mac, git's own credential
    helper has them. In the cloud, PIPELINE_STATE_TOKEN (a fine-grained
    token for that one repo) goes in through the environment, never on the
    command line, where `ps` would show it. Config the environment already
    passes this way (a proxy, say) is kept."""
    env = dict(os.environ)
    token = os.getenv("PIPELINE_STATE_TOKEN", "")
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        index = int(env.get("GIT_CONFIG_COUNT") or 0)
        env[f"GIT_CONFIG_KEY_{index}"] = "http.https://github.com/.extraheader"
        env[f"GIT_CONFIG_VALUE_{index}"] = f"AUTHORIZATION: basic {basic}"
        env["GIT_CONFIG_COUNT"] = str(index + 1)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=_git_env(), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise StateError(f"git {args[0]} failed: {result.stderr.strip()[-300:]}")
    return result.stdout


def _require_writer(head: str | None) -> None:
    """Refuse to write unless this is the cloud routine, or the repo is
    still empty (the one seeding push from the Mac)."""
    if head and os.getenv(WRITER_ENV) != "1":
        raise StateError(
            "only the cloud routine writes the private repo; this machine only pulls "
            f"({WRITER_ENV}=1 is set in the cloud environment)"
        )


def _require_private(repo: str) -> None:
    """Refuse to write to a GitHub repo that is not private: the caches hold
    organizer emails. A local path (the tests) is not checked."""
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", repo)
    if not match:
        return
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("PIPELINE_STATE_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(f"https://api.github.com/repos/{match.group(1)}", headers=headers, timeout=30)
        response.raise_for_status()
        private = response.json().get("private") is True
    except (requests.RequestException, ValueError) as error:
        raise StateError(
            f"could not confirm that {match.group(1)} is private ({str(error)[:120]}); "
            "nothing was pushed. Retry make state-push."
        ) from error
    if not private:
        raise StateError(
            f"{match.group(1)} is not private, and the caches hold organizer emails; "
            "nothing was pushed. Make the repo private, then retry make state-push."
        )


def _active_run(state_dir: Path) -> bool:
    """This clone began a run that has not pushed yet."""
    running, mine = state_dir / RUNNING, _run_id(state_dir)
    return running.exists() and mine.exists() and running.read_text() == mine.read_text()


def _run_id(state_dir: Path) -> Path:
    """The run mark this clone wrote, if it began the run."""
    return state_dir / ".git" / "iwrestle-run"


def _marker(state_dir: Path) -> Path:
    """The commit this clone last pulled or pushed (inside .git: never committed)."""
    return state_dir / ".git" / "iwrestle-synced"


def _checkout(repo: str, state_dir: Path) -> str | None:
    """Clone the private repo, or bring an existing clone exactly up to
    date. Returns the remote's head commit, None for an empty repo."""
    if not repo:
        raise StateError("PIPELINE_STATE_REPO is not set (pipeline/.env, or the cloud environment)")
    if not (state_dir / ".git").exists():
        _git("clone", "--quiet", repo, str(state_dir))
    _git("fetch", "--quiet", "origin", cwd=state_dir)
    if not _git("branch", "--remotes", cwd=state_dir).strip():
        # A new, empty repo: the first push starts its branch.
        _git("symbolic-ref", "HEAD", f"refs/heads/{BRANCH}", cwd=state_dir)
        return None
    _git("reset", "--quiet", "--hard", f"origin/{BRANCH}", cwd=state_dir)
    # Files a failed push left behind would otherwise be pulled as kept data.
    _git("clean", "--quiet", "-fdx", cwd=state_dir)
    return _git("rev-parse", "HEAD", cwd=state_dir).strip()


def _files(root: Path) -> set[Path]:
    """Kept files under a data folder, relative to it."""
    found = {Path(name) for name in DATA_FILES if (root / name).is_file()}
    newest: dict[str, str] = {}
    for path in root.glob("events.*.json") if root.is_dir() else []:
        match = EVENTS_FILE.fullmatch(path.name)
        if match and path.name > newest.get(match.group(1), ""):
            newest[match.group(1)] = path.name
    found |= {Path(name) for name in newest.values()}
    assets = root / "assets"
    if assets.is_dir():
        for folder in assets.iterdir():
            for name in ASSET_FILES:
                if (folder / name).is_file():
                    found.add(Path("assets") / folder.name / name)
    return found


def _same(a: Path, b: Path) -> bool:
    return b.exists() and a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()


def _copy(relative: set[Path], source: Path, destination: Path) -> int:
    copied = 0
    for path in sorted(relative):
        target = destination / path
        if _same(source / path, target):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, target)
        _date_by_name(target)
        copied += 1
    return copied


def _date_by_name(path: Path) -> None:
    """Give a collected file its collect date as its modification time:
    make promote's stale check and `ls -t` go by it, and a copy would
    otherwise look new."""
    match = EVENTS_FILE.fullmatch(path.name)
    if match:
        day = datetime.strptime(match.group(2), "%Y%m%d").replace(hour=12, tzinfo=timezone.utc)
        os.utime(path, (day.timestamp(), day.timestamp()))


def pull(repo: str = STATE_REPO, state_dir: Path = STATE_DIR, data_dir: Path = DATA_DIR) -> int:
    """Copy the kept files into data/. Returns how many changed.

    Local files the private repo lacks are left alone, except the ones it
    had at this machine's last sync and has since deleted: another run
    dropped them on purpose (a flyer that names a different event), and the
    next push from here would bring them back."""
    if _active_run(state_dir):
        # cloud-start ran twice in one session: pulling now would copy the
        # repo's older files over the ones this run made.
        return 0
    marker = _marker(state_dir)
    synced = marker.read_text().strip() if marker.exists() else ""
    head = _checkout(repo, state_dir)
    stored = state_dir / "data"
    current = _files(stored)
    if synced and head and synced != head:
        for path in _tracked(state_dir, synced) - current:
            # An older collected file only left because a newer one came;
            # it stays as history.
            if not EVENTS_FILE.fullmatch(path.name):
                (data_dir / path).unlink(missing_ok=True)
    copied = _copy(current, stored, data_dir)
    # Written last: a pull that failed partway does not count as one.
    _marker(state_dir).write_text((head or "") + "\n")
    return copied


def _tracked(state_dir: Path, commit: str) -> set[Path]:
    """Kept data files in an earlier commit of the private repo."""
    try:
        names = _git("ls-tree", "-r", "--name-only", commit, "--", "data", cwd=state_dir)
    except StateError:
        return set()  # history this clone does not have; nothing to compare
    return {Path(name).relative_to("data") for name in names.splitlines() if name}


def begin_run(repo: str = STATE_REPO, state_dir: Path = STATE_DIR) -> None:
    """Mark a run as started, after pull. Refuses if the last one never
    reached push."""
    if _active_run(state_dir):
        return
    head = _checkout(repo, state_dir)
    _require_writer(head)
    running = state_dir / RUNNING
    if running.exists():
        raise StateError(
            f"a run that started {running.read_text().strip()} never finished make state-push. "
            "If it got as far as pushing, CloudKit has records its ledger lost, and this run "
            "would create them again. Check with make reconcile (records in CloudKit against "
            "the ledger, and the ones it doesn't know). When that is sorted out, clear the mark "
            "with .venv/bin/python bin/state.py clear-run, then start again."
        )
    marker = _marker(state_dir)
    if head and (not marker.exists() or marker.read_text().strip() != head):
        raise StateError("run make state-pull first")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mark = f"{stamp} on {socket.gethostname()}"
    running.write_text(mark + "\n")
    _commit_and_push(state_dir, f"Run started {stamp}")
    _run_id(state_dir).write_text(mark + "\n")


def clear_run(repo: str = STATE_REPO, state_dir: Path = STATE_DIR, *, force: bool = False) -> bool:
    """Remove a stale run mark by hand. Returns whether there was one.

    A mark younger than RUN_MARK_HOURS is left alone unless forced: its run
    may still be going, and its push would then be refused."""
    _checkout(repo, state_dir)
    running = state_dir / RUNNING
    if not running.exists():
        return False
    try:
        started = datetime.strptime(running.read_text()[:20], "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
    except ValueError:
        started = None
    if started and not force:
        hours = (datetime.now(timezone.utc) - started).total_seconds() / 3600
        if hours < RUN_MARK_HOURS:
            raise StateError(
                f"the run mark is {hours:.1f} hours old, so its run may still be running. "
                "Wait, or add --force if you know it stopped."
            )
    running.unlink()
    # Not a sync: this clone has not pulled the files, so it may not push them.
    _commit_and_push(state_dir, "Clear the mark of a run that never finished", synced=False)
    return True


def _commit_and_push(state_dir: Path, message: str, *, synced: bool = True) -> int:
    _git("add", "--all", cwd=state_dir)
    changed = [line for line in _git("status", "--porcelain", cwd=state_dir).splitlines() if line]
    if not changed:
        return 0
    _git(
        "-c", "user.name=iWrestle pipeline", "-c", "user.email=pipeline@users.noreply.github.com",
        "commit", "--quiet", "-m", message, cwd=state_dir,
    )
    try:
        _git("push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}", cwd=state_dir)
    except StateError as error:
        text = str(error)
        if any(word in text for word in ("rejected", "non-fast-forward", "fetch first")):
            raise StateError(f"{error}. Something else wrote the private repo during this run. {DO_NOT_PULL}") from error
        raise StateError(
            f"{error}. Nothing else wrote the repo; data/ and this run's mark are intact, "
            "so retry make state-push."
        ) from error
    if synced:
        _marker(state_dir).write_text(_git("rev-parse", "HEAD", cwd=state_dir).strip() + "\n")
    return len(changed)


def push(
    repo: str = STATE_REPO, state_dir: Path = STATE_DIR, data_dir: Path = DATA_DIR,
    *, allow_shrink: bool = False,
) -> int:
    """Mirror data/'s kept files into the private repo and commit.

    Only the cloud routine may push, after pulling the repo's current
    commit. A kept file deleted locally is deleted there too, so a push is
    also refused when it would drop more than MAX_SHRINK of the files, a
    cache, or a source's only collected file. Returns how many files the
    commit changed (0: nothing to commit)."""
    _require_private(repo)
    try:
        head = _checkout(repo, state_dir)
    except StateError as error:
        raise StateError(f"{error}. Nothing was changed; retry make state-push.") from error
    _require_writer(head)
    marker = _marker(state_dir)
    synced = marker.read_text().strip() if marker.exists() else None
    if head and synced != head:
        raise StateError(
            "the private repo has changed since this run's state pull, or it never "
            f"pulled, so this push could delete or overwrite newer files. {DO_NOT_PULL}"
        )

    local = _files(data_dir)
    stored = state_dir / "data"
    held = _files(stored)
    dropped = held - local
    sources = {EVENTS_FILE.fullmatch(p.name).group(1) for p in local if EVENTS_FILE.fullmatch(p.name)}
    # A collected file replaced by a newer one of its source is expected.
    lost = sorted(
        str(path) for path in dropped
        if not (EVENTS_FILE.fullmatch(path.name) and EVENTS_FILE.fullmatch(path.name).group(1) in sources)
    )
    caches = [name for name in lost if name in DATA_FILES or EVENTS_FILE.fullmatch(name)]
    if not allow_shrink and (caches or (held and len(lost) > MAX_SHRINK * len(held))):
        what = ", ".join(caches) if caches else f"{len(lost)} of {len(held)} kept files"
        raise StateError(
            f"this push would delete {what} from the private repo, so data/ looks "
            "incomplete. If that is really meant, run "
            ".venv/bin/python bin/state.py push --allow-shrink"
        )
    for path in dropped:
        (stored / path).unlink()
        folder = (stored / path).parent
        if folder != stored and not any(folder.iterdir()):
            folder.rmdir()
    _copy(local, data_dir, stored)
    if (data_dir / LEDGER_FILE).is_file():
        _copy({Path(LEDGER_FILE)}, data_dir, state_dir / "ledger")
    # Clear the run mark only if this clone set it: a push from anywhere
    # else must not hide a run that died.
    running, mine = state_dir / RUNNING, _run_id(state_dir)
    if running.exists() and mine.exists() and running.read_text() == mine.read_text():
        running.unlink()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    changed = _commit_and_push(state_dir, f"State after the run of {stamp}")
    if not running.exists():
        mine.unlink(missing_ok=True)
    return changed


def ledger_differences(state_dir: Path = STATE_DIR, data_dir: Path = DATA_DIR) -> list[str]:
    """Development events the last run recorded that main's ledger lacks.

    Run after pull on a fresh clone of main. The cloud writes development
    only, so only those entries are compared. An entry missing from main,
    or with another record name, means the last run's ledger did not reach
    main, and this run would push those events again. An event excluded
    on main since is not counted: make exclude takes it out on purpose.
    Returns their source keys, sorted."""
    kept_path = state_dir / "ledger" / LEDGER_FILE
    if not kept_path.exists():
        return []
    prefix = "development:"
    try:
        kept = json.loads(kept_path.read_text())
    except ValueError:
        # Not knowing is not the same as nothing lost.
        return ["(the kept ledger/pushed.json in the private repo is unreadable)"]
    try:
        main = json.loads((data_dir / LEDGER_FILE).read_text())
    except (OSError, ValueError):
        main = {}
    try:
        excluded = json.loads((data_dir / "excluded.json").read_text())
    except (OSError, ValueError):
        excluded = {}
    lost = []
    for key, entry in kept.items():
        if not key.startswith(prefix):
            continue
        source_key = key[len(prefix):]
        if source_key in excluded:
            continue
        if main.get(key, {}).get("recordName") != entry.get("recordName"):
            lost.append(source_key)
    return sorted(lost)
