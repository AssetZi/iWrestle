#!/usr/bin/env python3
"""Write approved events into CloudKit with cktool.

    python bin/push.py data/events.pywrestling.20260904.json --dry-run
    python bin/push.py data/events.pywrestling.20260904.json
    python bin/push.py data/events.pywrestling.20260904.json --production

Development is the default because debug builds from Xcode read that
environment; production is what the App Store build reads and requires an
explicit flag plus a typed confirmation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from iwpipe import cktool, ledger, schema
from iwpipe.assets import event_asset_dir

BOLD, GREEN, YELLOW, RED, RESET = (
    "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"
)


def push_one(event, environment, *, dry_run):
    """Create one record; returns its CloudKit record name."""
    folder = event_asset_dir(event["sourceKey"])
    fields_path = folder / "fields.json"
    logo = Path(event["logo"])
    flyer = Path(event["flyer"]["path"])

    fields_path.write_text(
        json.dumps(cktool.build_fields(event), indent=2) + "\n"
    )
    if dry_run:
        print("    would run cktool create-record")
        print(f"      --fields-file {fields_path}")
        print(f"      --asset-files LOGO={logo} FLYER={flyer}")
        return None

    response = cktool.create_record(fields_path, logo, flyer, environment)
    return (
        response.get("recordName")
        or response.get("record", {}).get("recordName", "")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--key", help="push only this sourceKey")
    parser.add_argument(
        "--force", action="store_true", help="push even if the ledger has it"
    )
    args = parser.parse_args()

    environment = cktool.PRODUCTION if args.production else cktool.DEVELOPMENT
    payload = schema.load(args.file)

    queue = []
    for event in payload["events"]:
        if args.key and event["sourceKey"] != args.key:
            continue
        if event["review"]["status"] != schema.STATUS_APPROVED:
            continue
        problems = schema.validate(event)
        if problems:
            print(f"{RED}skip{RESET} {event['name'][:50]}: {problems[0]}")
            continue
        if not args.force and ledger.contains(event["sourceKey"], environment):
            print(f"{YELLOW}skip{RESET} {event['name'][:50]}: already in ledger")
            continue
        queue.append(event)

    if not queue:
        print("nothing to push")
        return 0

    if args.production and not args.dry_run:
        print(f"\n{RED}{BOLD}  PRODUCTION  {RESET}")
        print(f"About to create {len(queue)} Event records visible to every")
        print("iWrestle user on the App Store. This cannot be undone in bulk.\n")
        for event in queue:
            print(f"  {event['date'][:10]}  {event['name']}")
        if input("\nType y to continue: ").strip().lower() != "y":
            print("aborted")
            return 1

    pushed = 0
    for event in queue:
        print(f"{BOLD}push{RESET} {event['date'][:10]}  {event['name'][:50]}")
        try:
            record_name = push_one(event, environment, dry_run=args.dry_run)
        except cktool.CKToolError as error:
            print(f"  {RED}failed{RESET}: {error}")
            break
        if args.dry_run:
            continue
        ledger.record(event["sourceKey"], environment, record_name, event["name"])
        pushed += 1
        print(f"  {GREEN}created{RESET} {record_name}")

    if args.dry_run:
        print(f"\ndry run: {len(queue)} events would be pushed to {environment}")
    else:
        print(f"\npushed {pushed}/{len(queue)} to {environment}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
