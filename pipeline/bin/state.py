#!/usr/bin/env python3
"""Copy the pipeline's working data from or to its private repo.

    python bin/state.py pull    # before a run on a fresh clone
    python bin/state.py push    # after the run, to keep it for next time

See iwpipe/state.py for what is kept and why.
"""
from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401

from iwpipe import state
from iwpipe.term import GREEN, RED, RESET


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("pull", "push"))
    args = parser.parse_args()
    try:
        count = state.pull() if args.action == "pull" else state.push()
    except state.StateError as error:
        print(f"{RED}{error}{RESET}")
        return 1
    verb = "copied into data/" if args.action == "pull" else "changed in the private repo"
    print(f"{GREEN}state {args.action}{RESET}: {count} files {verb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
