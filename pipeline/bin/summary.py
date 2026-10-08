#!/usr/bin/env python3
"""The few lines of a routine log a person needs.

    python bin/summary.py                      # the newest log in data/logs
    python bin/summary.py data/logs/routine.20261005.log

A routine log runs to tens of thousands of lines (one or two per event).
This prints, per source, what was collected and pushed, and every line
that means something stopped or was held back.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import _bootstrap  # noqa: F401

from iwpipe.config import DATA_DIR

LOG_DIR = DATA_DIR / "logs"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
HEADING = re.compile(r"^== (\w+)")
KEEP = re.compile(
    r"^(collected |wrote |rechecked |enriched |tokens: |pushed |nothing (to push|pushed)|development: |production: "
    r"|\d+ pushed listings gone from |\d+ not created by this pipeline)"
)
# Lines that mean something stopped, was skipped, or was held back.
TROUBLE = re.compile(
    r"scrape looks partial|removals wanted, cap is|would be re-pushed|blocked \(HTTP|ANTHROPIC_API_KEY"
    r"|is held by another run|not a terminal|nothing collected|Error\b|^make: \*\*\*|did not answer"
)
ACTION = re.compile(r"^  (created|replaced|moved|removed) ")


def summarize(text: str) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    trouble: list[str] = []
    source = ""
    actions: Counter[str] = Counter()

    def close() -> None:
        if actions:
            lines.append("  " + ", ".join(f"{actions[k]} {k}" for k in ("created", "replaced", "moved", "removed") if actions[k]))
        actions.clear()

    in_traceback = False
    for raw in text.splitlines():
        line = ANSI.sub("", raw).rstrip()
        heading = HEADING.match(line)
        if heading:
            close()
            source = heading.group(1)
            lines.append(line)
            continue
        if line.startswith("Traceback"):
            in_traceback = True
            continue
        if in_traceback:
            # The last line of a traceback is the error; the rest is noise.
            if line and not line.startswith(" "):
                in_traceback = False
                trouble.append(f"{source}: {line[:200]}")
            continue
        action = ACTION.match(line)
        if action:
            actions[action.group(1)] += 1
        elif TROUBLE.search(line):
            trouble.append(f"{source}: {line[:300]}")
        elif KEEP.match(line):
            lines.append("  " + line[:200])
            if line.startswith(("pushed ", "nothing ")):
                close()
    close()
    return lines, trouble


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, nargs="?")
    args = parser.parse_args()

    log = args.log
    if log is None:
        logs = sorted(LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime)
        if not logs:
            print(f"no logs in {LOG_DIR}")
            return 1
        log = logs[-1]
    lines, trouble = summarize(log.read_text(errors="replace"))
    print(f"{log.name}")
    print("\n".join(lines))
    print(f"\nneeds a look ({len(trouble)}):" if trouble else "\nneeds a look: nothing")
    for line in trouble:
        print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
