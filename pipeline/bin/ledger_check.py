#!/usr/bin/env python3
"""Exit 1 when main's ledger may be behind CloudKit.

The cloud routine clones main. Its ledger is behind when a data/ledger-*
pull request is not merged yet, or when the last run's ledger never got
into one; the copy kept by `make state-push` shows the second. A run from
a stale ledger would push those events a second time. Run it after
`make state-pull`.
"""
from __future__ import annotations

import os
import sys

import _bootstrap  # noqa: F401

import requests

from iwpipe import state
from iwpipe.term import GREEN, RED, RESET

LEDGER_BRANCH_PREFIX = "data/ledger-"
# Named here, not read from origin: a cloud clone's origin can be a local
# proxy URL.
GITHUB_REPO = os.getenv("GITHUB_REPO", "AssetZi/iWrestle")


def open_ledger_prs(slug: str) -> list[dict]:
    headers = {"Accept": "application/vnd.github+json"}
    # Anonymous calls share a 60-an-hour limit per IP, which a cloud
    # machine's shared address can use up. Any token that can read this
    # public repo will do.
    token = os.getenv("PIPELINE_STATE_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
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
        open_prs = open_ledger_prs(GITHUB_REPO)
    except (requests.RequestException, ValueError) as error:
        # Not knowing is not the same as none being open.
        print(f"{RED}could not check for open ledger pull requests{RESET}: {str(error)[:200]}")
        return 1
    if open_prs:
        print(f"{RED}a ledger pull request is still open{RESET}; main's ledger is behind CloudKit.")
        for pr in open_prs:
            print(f"  #{pr['number']} {pr['head']['ref']}: {pr['html_url']}")
        print("Merge it, then run again. Nothing was collected or pushed.")
        return 1
    lost = state.ledger_differences()
    if lost:
        print(
            f"{RED}{len(lost)} development events the last run recorded are not in main's "
            f"ledger{RESET}, so its ledger never reached main and this run would create them again:"
        )
        for key in lost[:10]:
            print(f"  {key}")
        print(
            "That run's pushed.json is in pipeline/.state/ledger/. Copy its development "
            "entries into main's (keep main's production entries) on a data/ledger-<date> "
            "branch cut from origin/main and open its pull request; once that is merged, "
            "run again. Nothing was collected or pushed."
        )
        return 1
    print(f"{GREEN}main's ledger is current{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
