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

BOLD, DIM, GREEN, YELLOW, RED, RESET = (
    "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"
)


def prepare(event):
    """Fields file, asset paths and content hash for one event."""
    folder = event_asset_dir(event["sourceKey"])
    fields = cktool.build_fields(event)
    fields_path = folder / "fields.json"
    fields_path.write_text(json.dumps(fields, indent=2) + "\n")
    logo = Path(event["logo"])
    flyer = Path(event["flyer"]["path"])
    return fields_path, logo, flyer, cktool.content_hash(fields, logo, flyer)


def push_one(event, environment, *, dry_run, replace_record=None):
    """Create one record (deleting the previous one when replacing).

    Returns (record name, content hash). cktool has no update, so a changed
    event is deleted and created again under a new record name.
    """
    fields_path, logo, flyer, digest = prepare(event)
    if dry_run:
        verb = "replace" if replace_record else "create"
        print(f"    would {verb} via cktool")
        print(f"      --fields-file {fields_path}")
        print(f"      --asset-files LOGO={logo} FLYER={flyer}")
        return None, digest

    # Create first, delete second: a failed create must never leave the
    # event missing from the database.
    response = cktool.create_record(fields_path, logo, flyer, environment)
    name = response.get("recordName") or response.get("record", {}).get("recordName", "")
    if replace_record:
        try:
            cktool.delete_record(replace_record, environment)
        except cktool.CKToolError as error:
            print(f"    {YELLOW}old record {replace_record[:8]} not deleted: {str(error).splitlines()[-1][:80]}{RESET}")
    return name, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--key", help="push only this sourceKey")
    parser.add_argument(
        "--force", action="store_true", help="push even if the ledger has it"
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="re-push events already in this environment whose content changed",
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
        existing = ledger.get(event["sourceKey"], environment)
        if existing and not args.force:
            if not args.replace:
                print(f"{YELLOW}skip{RESET} {event['name'][:50]}: already in ledger")
                continue
            _, _, _, digest = prepare(event)
            if digest == existing.get("contentHash"):
                print(f"{DIM}same{RESET} {event['name'][:50]}: unchanged since push")
                continue
            event["_replace"] = existing["recordName"]
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
    failed = 0
    for event in queue:
        replacing = event.pop("_replace", None)
        verb = "replace" if replacing else "push"
        print(f"{BOLD}{verb}{RESET} {event['date'][:10]}  {event['name'][:50]}")
        try:
            record_name, digest = push_one(
                event, environment, dry_run=args.dry_run, replace_record=replacing
            )
        except cktool.CKToolError as error:
            print(f"  {RED}failed{RESET}: {error}")
            failed += 1
            continue
        if args.dry_run:
            continue
        ledger.record(
            event["sourceKey"], environment, record_name, event["name"],
            day=event["date"][:10], location=event.get("location"),
            content_hash=digest,
        )
        pushed += 1
        print(f"  {GREEN}{'replaced' if replacing else 'created'}{RESET} {record_name}")

    if args.dry_run:
        print(f"\ndry run: {len(queue)} events would be pushed to {environment}")
    else:
        print(f"\npushed {pushed}/{len(queue)} to {environment}" + (f", {failed} failed" if failed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
