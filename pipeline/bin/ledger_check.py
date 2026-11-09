#!/usr/bin/env python3
"""Exit 1 while a ledger pull request is open.

The cloud routine clones main. A data/ledger-* pull request that is not
merged yet holds last week's pushes, so main's ledger is behind CloudKit,
and a run from it would push those events a second time.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import _bootstrap  # noqa: F401

import requests

from iwpipe.term import GREEN, RED, RESET

LEDGER_BRANCH_PREFIX = "data/ledger-"


def repo_slug() -> str:
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not match:
        raise ValueError(f"origin is not a GitHub repo: {url}")
    return match.group(1)


def open_ledger_prs(slug: str) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(
        f"https://api.github.com/repos/{slug}/pulls",
        params={"state": "open", "per_page": 100}, headers=headers, timeout=30,
    )
    response.raise_for_status()
    return [pr for pr in response.json() if pr["head"]["ref"].startswith(LEDGER_BRANCH_PREFIX)]


def main() -> int:
    try:
        open_prs = open_ledger_prs(repo_slug())
    except (requests.RequestException, subprocess.CalledProcessError, ValueError) as error:
        # Not knowing is not the same as none being open.
        print(f"{RED}could not check for open ledger pull requests{RESET}: {str(error)[:200]}")
        return 1
    if open_prs:
        print(f"{RED}a ledger pull request is still open{RESET}; main's ledger is behind CloudKit.")
        for pr in open_prs:
            print(f"  #{pr['number']} {pr['head']['ref']}: {pr['html_url']}")
        print("Merge it, then run again. Nothing was collected or pushed.")
        return 1
    print(f"{GREEN}no open ledger pull request{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
