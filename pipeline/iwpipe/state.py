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

begin_run marks a run as started in the private repo. That run's push
clears the mark only once its pushed.json is on GitHub, on main or a
data/ledger-* branch (ledger_landed). A mark still there at the next
begin_run means a run created development records whose ledger never left
its session, and this run would create them again. When the session got as
far as pushing its state, its ledger files are saved under ledger/ in the
private repo, to recover from.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import github
from .config import DATA_DIR, PIPELINE_ROOT, REPO_ROOT

STATE_REPO = os.getenv("PIPELINE_STATE_REPO", "")
STATE_DIR = PIPELINE_ROOT / ".state"
BRANCH = "main"

DATA_FILES = ("flo-details.json", "enrich-cache.json")
ASSET_FILES = ("logo.png", "flyer.pdf", "source-flyer.pdf", "banner.jpg")
LEDGER_FILE = "pushed.json"
# What a run's step 7 commits; all of it has to reach GitHub.
LEDGER_FILES = ("pushed.json", "excluded.json", "renamed.json")
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


def _repo_slug(repo: str) -> str | None:
    """owner/name from a repo URL, None for a local path (the tests).

    Read from the end of the path, so a proxy URL such as
    http://127.0.0.1:8080/git/owner/name works too."""
    # Only a local path is skipped. Anything else, including an SSH remote
    # written without a user (github.com:owner/name) or an SSH alias, is
    # checked: a skipped check could send the caches to a public repo.
    if repo.startswith(("file://", "/", ".", "~")) or Path(repo).exists():
        return None
    path = repo.split("://", 1)[1] if "://" in repo else repo.split(":", 1)[-1]
    parts = [part for part in path.rstrip("/").removesuffix(".git").split("/") if part]
    if len(parts) < 2:
        raise StateError(f"cannot tell which GitHub repo {repo!r} is; nothing was pushed")
    return "/".join(parts[-2:])


def _require_private(repo: str) -> None:
    """Refuse to write to a repo that is not private on GitHub: the caches
    hold organizer emails."""
    slug = _repo_slug(repo)
    if slug is None:
        return
    try:
        response = requests.get(f"https://api.github.com/repos/{slug}", headers=github.headers(), timeout=30)
        response.raise_for_status()
        private = response.json().get("private") is True
    except requests.HTTPError as error:
        status = getattr(error.response, "status_code", None)
        if status in (401, 403, 404):
            raise StateError(
                f"GitHub would not show {slug} ({status}), so it could not be confirmed "
                "private; nothing was pushed. This machine needs a token that can read it: "
                "PIPELINE_STATE_TOKEN in the cloud environment, or a gh login on the Mac "
                "(gh auth login)."
            ) from error
        raise StateError(
            f"could not confirm that {slug} is private ({str(error)[:120]}); "
            "nothing was pushed. Retry make state-push."
        ) from error
    except (requests.RequestException, ValueError) as error:
        raise StateError(
            f"could not confirm that {slug} is private ({str(error)[:120]}); "
            "nothing was pushed. Retry make state-push."
        ) from error
    if not private:
        raise StateError(
            f"{slug} is not private, and the caches hold organizer emails; "
            "nothing was pushed. Make the repo private, then retry make state-push."
        )


def ledger_landed(data_dir: Path) -> bool:
    """This run's ledger files are on GitHub where they will reach main
    (see _ledger_landed)."""
    def open_branches() -> set[str]:
        try:
            return {pr["head"]["ref"] for pr in github.open_ledger_prs()}
        except (requests.RequestException, ValueError) as error:
            raise StateError(
                f"could not check GitHub for this run's ledger pull request ({str(error)[:120]}); "
                "nothing was pushed. Retry make state-push."
            ) from error

    return _ledger_landed(data_dir, REPO_ROOT, open_branches)


def _ledger_landed(data_dir: Path, repo_root: Path, open_branches) -> bool:
    """The ledger files in data_dir (pushed.json, excluded.json,
    renamed.json) all match one ref on origin: main, or a data/ledger-*
    branch with an open pull request (open_branches() lists those). A
    pushed branch with no open pull request does not count: nothing would
    merge it, and the next run, finding no open one, would start from
    main's older ledger. A run that changed nothing matches main."""
    local = {}
    for name in LEDGER_FILES:
        if (data_dir / name).exists():
            local[name] = json.loads((data_dir / name).read_text())
    if not local:
        return True
    prefix = (data_dir.resolve()).relative_to(repo_root.resolve()).as_posix()
    git = ["git", "-C", str(repo_root)]
    fetch = subprocess.run(
        git + ["fetch", "--quiet", "origin",
               "+refs/heads/main:refs/remotes/origin/main",
               "+refs/heads/data/ledger-*:refs/remotes/origin/data/ledger-*"],
        capture_output=True, text=True,
    )
    if fetch.returncode != 0:
        raise StateError(
            f"could not check GitHub for this run's ledger ({fetch.stderr.strip()[-150:]}); "
            "nothing was pushed. Retry make state-push."
        )
    refs = subprocess.run(
        git + ["for-each-ref", "--format=%(refname)", "refs/remotes/origin/main", "refs/remotes/origin/data/"],
        capture_output=True, text=True, check=True,
    ).stdout.split()

    def matches(ref: str) -> bool:
        for name, mine in local.items():
            shown = subprocess.run(git + ["show", f"{ref}:{prefix}/{name}"], capture_output=True, text=True)
            try:
                theirs = json.loads(shown.stdout) if shown.returncode == 0 else None
            except ValueError:
                return False
            if theirs != mine and not (theirs is None and mine == {}):
                return False
        return True

    branches = None
    for ref in refs:
        if not matches(ref):
            continue
        if ref == "refs/remotes/origin/main":
            return True
        if branches is None:
            branches = open_branches()
        if ref.removeprefix("refs/remotes/origin/") in branches:
            return True
    return False


def _active_run(state_dir: Path) -> bool:
    """This clone began a run, its mark is on GitHub, and the run has not
    finished its push."""
    running, mine, marker = state_dir / RUNNING, _run_id(state_dir), _marker(state_dir)
    if not (running.exists() and mine.exists() and marker.exists()):
        return False
    if running.read_text() != mine.read_text():
        return False
    try:
        return marker.read_text().strip() == _git("rev-parse", "HEAD", cwd=state_dir).strip()
    except StateError:
        return False


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
    # A collected file changed here since it was pulled holds this
    # machine's review or exclusions (make review, make exclude); keep it.
    record = _pulled(state_dir)
    seen = json.loads(record.read_text()) if record.exists() else {}
    kept_local.clear()
    for path in sorted(current):
        local = data_dir / path
        if EVENTS_FILE.fullmatch(path.name) and local.exists() and path.name in seen:
            if _digest(local) != seen[path.name] and _digest(local) != _digest(stored / path):
                kept_local.append(path.name)
    copied = _copy(current - {Path(name) for name in kept_local}, stored, data_dir)
    record.write_text(json.dumps({
        path.name: _digest(stored / path) for path in current if EVENTS_FILE.fullmatch(path.name)
    } | {name: seen[name] for name in kept_local}) + "\n")
    # Written last: a pull that failed partway does not count as one.
    _marker(state_dir).write_text((head or "") + "\n")
    return copied


kept_local: list[str] = []  # collected files the last pull left as edited here


def _pulled(state_dir: Path) -> Path:
    """Digests of the collected files as last pulled (inside .git)."""
    return state_dir / ".git" / "iwrestle-pulled.json"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    _require_private(repo)
    head = _checkout(repo, state_dir)
    _require_writer(head)
    running = state_dir / RUNNING
    if running.exists():
        saved = sorted(path.name for path in (state_dir / "ledger").glob("*.json"))
        where = (
            f"Its ledger files ({', '.join(saved)}) are saved under ledger/ in the private "
            "repo (pipeline/.state/ledger/ here): put them on a data/ledger-<date> branch "
            "cut from origin/main and open its pull request."
            if saved else
            "It never saved its state, so its pushed.json is lost: make reconcile lists the "
            "development records the ledger doesn't know."
        )
        raise StateError(
            f"the run that started {running.read_text().strip()} never got its ledger onto "
            "GitHub. If it pushed events to development, this run would create them again. "
            f"{where} If it stopped before pushing anything, or its ledger pull request was "
            "merged after all, there is nothing to recover. Then clear "
            "the mark with .venv/bin/python bin/state.py clear-run and start again."
        )
    marker = _marker(state_dir)
    if head and (not marker.exists() or marker.read_text().strip() != head):
        raise StateError("run make state-pull first")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mark = f"{stamp} on {socket.gethostname()}"
    running.write_text(mark + "\n")
    # Written first, so a push that reached GitHub without saying so is
    # still recognized as this run's own mark on the next cloud-start.
    _run_id(state_dir).write_text(mark + "\n")
    _commit_and_push(state_dir, f"Run started {stamp}", retry="run make cloud-start again")


def clear_run(repo: str = STATE_REPO, state_dir: Path = STATE_DIR, *, force: bool = False) -> bool:
    """Remove a stale run mark by hand. Returns whether there was one.

    A mark younger than RUN_MARK_HOURS is left alone unless forced: its run
    may still be going, and its push would then be refused. Like any write,
    it is the cloud routine's (a session with Brock, in the cloud)."""
    _require_private(repo)
    head = _checkout(repo, state_dir)
    _require_writer(head)
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


def _commit_and_push(
    state_dir: Path, message: str, *, synced: bool = True, retry: str = "retry make state-push",
) -> int:
    _git("add", "--all", cwd=state_dir)
    changed = [line for line in _git("status", "--porcelain", cwd=state_dir).splitlines() if line]
    if not changed:
        return 0
    _git(
        "-c", "user.name=iWrestle pipeline", "-c", "user.email=pipeline@users.noreply.github.com",
        "commit", "--quiet", "-m", message, cwd=state_dir,
    )
    pending = _pending(state_dir)
    pending.write_text(_git("rev-parse", "HEAD", cwd=state_dir).strip() + "\n")
    try:
        _git("push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}", cwd=state_dir)
    except StateError as error:
        text = str(error)
        if _push_arrived(state_dir):
            # The server took it; only the reply was lost.
            pass
        elif any(word in text for word in ("rejected", "non-fast-forward", "fetch first")):
            raise StateError(f"{error}. Something else wrote the private repo during this run. {DO_NOT_PULL}") from error
        else:
            raise StateError(f"{error}. Nothing else wrote the repo, so {retry}.") from error
    if synced:
        _marker(state_dir).write_text(_git("rev-parse", "HEAD", cwd=state_dir).strip() + "\n")
    pending.unlink(missing_ok=True)
    return len(changed)


def _pending(state_dir: Path) -> Path:
    """The commit this clone last tried to push (inside .git). If GitHub
    took it but the reply was lost, the next push finds it there."""
    return state_dir / ".git" / "iwrestle-pushing"


def _push_arrived(state_dir: Path) -> bool:
    try:
        _git("fetch", "--quiet", "origin", cwd=state_dir)
        remote = _git("rev-parse", f"origin/{BRANCH}", cwd=state_dir).strip()
        return remote == _git("rev-parse", "HEAD", cwd=state_dir).strip()
    except StateError:
        return False


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
    pending = _pending(state_dir)
    if head and synced != head and pending.exists() and pending.read_text().strip() == head:
        # This clone's own last push, which GitHub took without saying so.
        marker.write_text(head + "\n")
        pending.unlink()
        synced = head
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

    # This run's mark comes off only once its ledger is on GitHub. A push
    # never touches a mark another clone set.
    running, mine, saved = state_dir / RUNNING, _run_id(state_dir), state_dir / "ledger"
    stranded = False
    if _active_run(state_dir):
        shutil.rmtree(saved, ignore_errors=True)
        if ledger_landed(data_dir):
            running.unlink()
        else:
            # Every ledger file the run has, for recovery: exclusions and
            # renames would be lost too, not only the pushes.
            stranded = True
            saved.mkdir()
            for name in LEDGER_FILES:
                if (data_dir / name).exists():
                    shutil.copyfile(data_dir / name, saved / name)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    changed = _commit_and_push(state_dir, f"State after the run of {stamp}")
    if stranded:
        raise StateError(
            "this run's files are saved, but its ledger is not on GitHub (neither main nor "
            "a data/ledger-* branch with an open pull request has it), so the run mark stays and the next run "
            "will stop. Commit and push the ledger as in step 7, then run make state-push "
            "again to clear the mark."
        )
    if not running.exists():
        mine.unlink(missing_ok=True)
    return changed
