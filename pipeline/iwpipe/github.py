"""The GitHub API calls the pipeline makes: the app repo's open ledger
pull requests, and whether the private data repo is private."""
from __future__ import annotations

import os
import shutil
import subprocess

import requests

# The app repo. Named here, not read from origin: a cloud clone's origin can
# be a local proxy URL.
APP_REPO = os.getenv("IWRESTLE_GITHUB_REPO", "AssetZi/iWrestle")
LEDGER_BRANCH_PREFIX = "data/ledger-"


def token() -> str:
    """PIPELINE_STATE_TOKEN in the cloud. On the Mac, where that is unset,
    the gh login (`gh auth token`, read into memory, never printed)."""
    for name in ("PIPELINE_STATE_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        if os.getenv(name):
            return os.environ[name]
    if shutil.which("gh"):
        result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    return ""


def headers() -> dict[str, str]:
    """Authenticated when a token is found. Anonymous calls share a
    60-an-hour limit per IP, which a cloud machine's shared address can
    use up."""
    result = {"Accept": "application/vnd.github+json"}
    found = token()
    if found:
        result["Authorization"] = f"Bearer {found}"
    return result


def open_ledger_prs(repo: str = APP_REPO) -> list[dict]:
    """Open pull requests from data/ledger-* branches. Raises
    requests.RequestException when GitHub can't be asked."""
    response = requests.get(
        f"https://api.github.com/repos/{repo}/pulls",
        params={"state": "open", "per_page": 100}, headers=headers(), timeout=30,
    )
    response.raise_for_status()
    return [pr for pr in response.json() if pr["head"]["ref"].startswith(LEDGER_BRANCH_PREFIX)]
