#!/usr/bin/env python3
"""The human gate before anything reaches the live public database.

    python bin/review.py data/events.pywrestling.20260904.json
    python bin/review.py <file> --approve-all
    python bin/review.py <file> --open

Prints one line per event with the flags collect raised, then lets you set
review.status by hand. Only "approved" events are ever pushed.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from iwpipe import schema

BOLD, DIM, GREEN, YELLOW, RED, CYAN, RESET = (
    "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m"
)


def status_color(status: str, blocked: bool) -> str:
    if blocked:
        return RED
    return {"approved": GREEN, "skip": DIM}.get(status, YELLOW)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--approve-all",
        action="store_true",
        help="approve every complete, not-yet-pushed event",
    )
    parser.add_argument("--open", action="store_true", help="open in $EDITOR")
    args = parser.parse_args()

    payload = schema.load(args.file)
    events = payload["events"]

    print(f"\n{BOLD}{args.file}{RESET}  ({payload['source']}, {len(events)} events)\n")
    for index, event in enumerate(events):
        problems = schema.validate(event)
        status = event["review"]["status"]
        color = status_color(status, bool(problems))
        when = (event.get("date") or "----------")[:10]
        print(
            f"{color}{index:>3}  {status:<9}{RESET} {when}  "
            f"{event.get('eventType','?'):<10} {event.get('name','')[:44]:<44} "
            f"{DIM}{', '.join(event.get('ageGroups', []))}{RESET}"
        )
        for text in event["review"].get("notes", []):
            marker = RED if text in problems else CYAN if text.startswith("AI:") else DIM
            print(f"      {marker}- {text}{RESET}")

    if args.approve_all:
        changed = 0
        for event in events:
            if event["review"]["status"] == schema.STATUS_PENDING and not schema.validate(event):
                event["review"]["status"] = schema.STATUS_APPROVED
                changed += 1
        schema.dump(args.file, payload["source"], events)
        print(f"\n{GREEN}approved {changed} events{RESET}")

    if args.open:
        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(args.file)])

    approved = sum(1 for e in events if e["review"]["status"] == schema.STATUS_APPROVED)
    blocked = sum(1 for e in events if schema.validate(e))
    ai_sourced = sum(
        1 for e in events
        if any(n.startswith("AI: ") and " from banner" in n for n in e["review"].get("notes", []))
    )
    print(
        f"\n{approved} approved, {blocked} incomplete, "
        f"{len(events) - approved - blocked} pending; "
        f"{ai_sourced} events with AI-sourced fields"
    )
    if approved:
        print(f"next: python bin/push.py {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
