#!/usr/bin/env python3
"""Exit 1 while a ledger pull request is open.

The cloud routine clones main. A data/ledger-* pull request that is not
merged yet holds the last run's pushes, so main's ledger is behind
CloudKit, and a run from it would push those events a second time. A run
whose ledger never got into an open pull request is caught by its run
mark instead (iwpipe/state.py).
"""
from __future__ import annotations

import sys

import _bootstrap  # noqa: F401

import requests

from iwpipe import github
from iwpipe.term import GREEN, RED, RESET


def main() -> int:
    try:
        open_prs = github.open_ledger_prs()
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
    print(f"{GREEN}no open ledger pull request{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
