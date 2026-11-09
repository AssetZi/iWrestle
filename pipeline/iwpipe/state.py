"""The pipeline's working data, kept in a private git repo between runs.

The cloud routine starts from a fresh clone, which has none of the
gitignored files a run depends on: the rendered logos and flyers the push
compares byte for byte, the downloaded banners and flyer PDFs, and the Flo
and enrichment caches. `pull` copies them out of the private repo into
data/, and `push` copies them back and commits. This repo is public; those
files hold organizer emails, so they never go in it.

flyer-page1.png and fields.json are rebuilt on every run and not kept.
geocache.json is tracked in this repo, so it is not kept there too.

`push` also keeps a copy of the ledger files under ledger/. They are never
copied back into data/: main's ledger is the one the pipeline uses. The
copy only lets a cloud run see that last run's ledger never reached main
(ledger_differences), before it pushes those events a second time.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR, PIPELINE_ROOT

STATE_REPO = os.getenv("PIPELINE_STATE_REPO", "")
STATE_DIR = PIPELINE_ROOT / ".state"
BRANCH = "main"

DATA_FILES = ("flo-details.json", "enrich-cache.json")
ASSET_FILES = ("logo.png", "flyer.pdf", "source-flyer.pdf", "banner.jpg")
LEDGER_FILES = ("pushed.json", "excluded.json", "renamed.json")

# A push may drop at most this share of the files the private repo holds
# (events past their date do leave), unless allow_shrink is given.
MAX_SHRINK = 0.10


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
        copied += 1
    return copied


def pull(repo: str = STATE_REPO, state_dir: Path = STATE_DIR, data_dir: Path = DATA_DIR) -> int:
    """Copy the kept files into data/. Returns how many changed.

    Local files the private repo lacks are left alone."""
    head = _checkout(repo, state_dir)
    copied = _copy(_files(state_dir / "data"), state_dir / "data", data_dir)
    # Written last: a pull that failed partway does not count as one.
    _marker(state_dir).write_text((head or "") + "\n")
    return copied


def push(
    repo: str = STATE_REPO, state_dir: Path = STATE_DIR, data_dir: Path = DATA_DIR,
    *, allow_shrink: bool = False,
) -> int:
    """Mirror data/'s kept files into the private repo and commit.

    A kept file deleted locally is deleted there too, so a push is refused
    unless this clone pulled (or pushed) the private repo's current commit,
    and when it would drop more than MAX_SHRINK of its files. Returns how
    many files the commit changed (0: nothing to commit)."""
    head = _checkout(repo, state_dir)
    marker = _marker(state_dir)
    synced = marker.read_text().strip() if marker.exists() else None
    if head and synced != head:
        raise StateError(
            "the private repo has changed since this machine's last state pull "
            "(or it never pulled); run make state-pull first, so a push cannot "
            "delete files from another machine's run"
        )

    local = _files(data_dir)
    stored = state_dir / "data"
    held = _files(stored)
    dropped = held - local
    if held and len(dropped) > MAX_SHRINK * len(held) and not allow_shrink:
        raise StateError(
            f"this push would delete {len(dropped)} of {len(held)} kept files from the "
            "private repo. data/ looks incomplete; if that many really went, push "
            "again with --allow-shrink"
        )
    for path in dropped:
        (stored / path).unlink()
        folder = (stored / path).parent
        if folder != stored and not any(folder.iterdir()):
            folder.rmdir()
    _copy(local, data_dir, stored)
    ledger = {Path(name) for name in LEDGER_FILES if (data_dir / name).is_file()}
    _copy(ledger, data_dir, state_dir / "ledger")

    _git("add", "--all", cwd=state_dir)
    changed = [line for line in _git("status", "--porcelain", cwd=state_dir).splitlines() if line]
    if not changed:
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    _git(
        "-c", "user.name=iWrestle pipeline", "-c", "user.email=pipeline@users.noreply.github.com",
        "commit", "--quiet", "-m", f"State after the run of {stamp}", cwd=state_dir,
    )
    _git("push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}", cwd=state_dir)
    marker.write_text(_git("rev-parse", "HEAD", cwd=state_dir).strip() + "\n")
    return len(changed)


def ledger_differences(state_dir: Path = STATE_DIR, data_dir: Path = DATA_DIR) -> list[str]:
    """Ledger files whose copy from the last state push differs from data/.

    Run after pull on a fresh clone of main: a difference means the last
    run's ledger did not reach main (its pull request failed, or a push
    was never recorded), and this run would push those events again."""
    differ = []
    for name in LEDGER_FILES:
        kept, local = state_dir / "ledger" / name, data_dir / name
        if not kept.exists():
            continue
        try:
            same = local.exists() and json.loads(kept.read_text()) == json.loads(local.read_text())
        except ValueError:
            same = False
        if not same:
            differ.append(name)
    return differ
