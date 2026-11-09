"""The pipeline's working data, kept in a private git repo between runs.

The cloud routine starts from a fresh clone, which has none of the
gitignored files a run depends on: the rendered logos and flyers the push
compares byte for byte, the downloaded banners and flyer PDFs, and the Flo
and enrichment caches. `pull` copies them out of the private repo into
data/, and `push` copies them back and commits. This repo is public; those
files hold organizer emails, so they never go in it.

Only the files below are kept. flyer-page1.png and fields.json are rebuilt
on every run.
"""
from __future__ import annotations

import base64
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR, PIPELINE_ROOT

STATE_REPO = os.getenv("PIPELINE_STATE_REPO", "")
STATE_DIR = PIPELINE_ROOT / ".state"
BRANCH = "main"

DATA_FILES = ("flo-details.json", "enrich-cache.json", "geocache.json")
ASSET_FILES = ("logo.png", "flyer.pdf", "source-flyer.pdf", "banner.jpg")


class StateError(RuntimeError):
    pass


def _git_env() -> dict[str, str]:
    """Credentials for the private repo. On this Mac, git's own credential
    helper has them. In the cloud, PIPELINE_STATE_TOKEN (a fine-grained
    token for that one repo) goes in through the environment, never on the
    command line, where `ps` would show it."""
    env = dict(os.environ)
    token = os.getenv("PIPELINE_STATE_TOKEN", "")
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        env.update(
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
            GIT_CONFIG_VALUE_0=f"AUTHORIZATION: basic {basic}",
        )
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=_git_env(), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise StateError(f"git {args[0]} failed: {result.stderr.strip()[-300:]}")
    return result.stdout


def _checkout(repo: str, state_dir: Path) -> None:
    """Clone the private repo, or bring an existing clone up to date."""
    if not repo:
        raise StateError("PIPELINE_STATE_REPO is not set (pipeline/.env, or the cloud environment)")
    if not (state_dir / ".git").exists():
        _git("clone", "--quiet", repo, str(state_dir))
    _git("fetch", "--quiet", "origin", cwd=state_dir)
    if _git("branch", "--remotes", cwd=state_dir).strip():
        _git("reset", "--quiet", "--hard", f"origin/{BRANCH}", cwd=state_dir)
    else:
        # A new, empty repo: the first push starts its branch.
        _git("symbolic-ref", "HEAD", f"refs/heads/{BRANCH}", cwd=state_dir)


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
    _checkout(repo, state_dir)
    return _copy(_files(state_dir / "data"), state_dir / "data", data_dir)


def push(repo: str = STATE_REPO, state_dir: Path = STATE_DIR, data_dir: Path = DATA_DIR) -> int:
    """Mirror data/'s kept files into the private repo and commit.

    A kept file deleted locally is deleted there too. Returns how many
    files the commit changed (0: nothing to commit)."""
    _checkout(repo, state_dir)
    local = _files(data_dir)
    stored = state_dir / "data"
    for path in _files(stored) - local:
        (stored / path).unlink()
        folder = (stored / path).parent
        if folder != stored and not any(folder.iterdir()):
            folder.rmdir()
    _copy(local, data_dir, stored)

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
    return len(changed)
