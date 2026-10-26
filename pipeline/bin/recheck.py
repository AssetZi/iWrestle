#!/usr/bin/env python3
"""Re-read a collected file against the ledger, without scraping again.

    python bin/recheck.py data/events.flowrestling.20261005.json

Collect sets an event aside as a possible duplicate when its look-alike is
in the ledger. Once a person (or the triage rules) has excluded one of the
pair, the other is free to go out, but only a new collect used to notice.
This redoes just that step: exclusions, corrected names, where each event
already is, and look-alikes. It also sets aside dual meets, a rule that reads
only the name. Listings, assets and miss counts are untouched.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

import collect as collect_cli

from iwpipe import ledger, level, schema
from iwpipe.term import RED, RESET

# What annotate_from_ledger writes; everything else on an event is collect's.
LEDGER_NOTES = ("excluded:", "already in ", "possible duplicate of ", "same day a few km from ")
# A skip any of these explains is not the ledger's doing and stays a skip.
OTHER_SKIPS = ("college-level event", "adult-level event", "cancelled or placeholder listing", "dual meet")


def reset(event) -> None:
    """Put an event back to how normalize left it, as far as the ledger goes."""
    notes = event["review"].get("notes", [])
    set_aside = any(n.startswith(("excluded:", "possible duplicate of ")) for n in notes)
    kept = [n for n in notes if not n.startswith(LEDGER_NOTES)]
    event["review"]["notes"] = kept
    if event["review"]["status"] != schema.STATUS_SKIP or not set_aside:
        return
    if any(n.startswith(OTHER_SKIPS) for n in kept):
        return
    if level.venue_is_tba(event.get("address", "")) and not event.get("location"):
        return
    event["review"]["status"] = schema.STATUS_PENDING


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()

    payload = schema.load(args.file)
    events = payload["events"]
    before = {e["sourceKey"]: e["review"]["status"] for e in events}
    try:
        with ledger.lock():
            for event in events:
                reset(event)
                if "dual meet" not in event["review"]["notes"]:
                    collect_cli.flag_dual(event)
                collect_cli.annotate_from_ledger(event)
    except ledger.LedgerError as error:
        print(f"{RED}{error}{RESET}")
        return 1
    schema.dump(args.file, payload["source"], events)

    freed = sum(
        1 for e in events
        if before[e["sourceKey"]] == schema.STATUS_SKIP and e["review"]["status"] != schema.STATUS_SKIP
    )
    set_aside = sum(
        1 for e in events
        if before[e["sourceKey"]] != schema.STATUS_SKIP and e["review"]["status"] == schema.STATUS_SKIP
    )
    print(f"rechecked {len(events)} events: {freed} no longer set aside, {set_aside} newly set aside")
    return 0


if __name__ == "__main__":
    sys.exit(main())
