#!/usr/bin/env python3
"""Copy the pipeline's working data from or to its private repo.

    python bin/state.py pull       # before a run on a fresh clone
    python bin/state.py begin      # mark a cloud run as started (make cloud-start)
    python bin/state.py push       # after the run, to keep it for next time
    python bin/state.py clear-run  # drop the mark of a run that never pushed

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
    parser.add_argument("action", choices=("pull", "begin", "push", "clear-run"))
    parser.add_argument(
        "--allow-shrink", action="store_true",
        help=f"push even if it deletes more than {state.MAX_SHRINK:.0%%} of the kept files",
    )
    args = parser.parse_args()
    try:
        if args.action == "pull":
            print(f"{GREEN}state pull{RESET}: {state.pull()} files copied into data/")
        elif args.action == "begin":
            state.begin_run()
            print(f"{GREEN}state begin{RESET}: run marked as started")
        elif args.action == "push":
            count = state.push(allow_shrink=args.allow_shrink)
            print(f"{GREEN}state push{RESET}: {count} files changed in the private repo")
        else:
            print(f"{GREEN}state clear-run{RESET}: " + ("mark removed" if state.clear_run() else "no mark to remove"))
    except state.StateError as error:
        print(f"{RED}{error}{RESET}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
