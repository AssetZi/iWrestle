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

from iwpipe import cktool, ckws, ledger, schema
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


def push_one(event, environment, *, dry_run, replace_record=None, client=None):
    """Create one record (deleting the previous one when replacing).

    Returns (record name, content hash). Neither backend can update a
    record, so a changed event is created again and the old one removed.
    """
    fields_path, logo, flyer, digest = prepare(event)
    if dry_run:
        verb = "replace" if replace_record else "create"
        print(f"    would {verb} via {cktool.backend_name(environment)}")
        print(f"      fields {fields_path}")
        print(f"      assets LOGO={logo} FLYER={flyer}")
        return None, digest

    # Create first, delete second: a failed create must never leave the
    # event missing from the database.
    if client is not None:
        fields = json.loads(fields_path.read_text())
        name = cktool.create_record_rest(client, fields, logo, flyer)
    else:
        response = cktool.create_record(fields_path, logo, flyer, environment)
        name = response.get("recordName") or response.get("record", {}).get("recordName", "")

    if replace_record:
        try:
            if client is not None:
                client.delete_record(replace_record)
            else:
                cktool.delete_record(replace_record, environment)
        except (cktool.CKToolError, ckws.CKWSError) as error:
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
    parser.add_argument(
        "--yes", action="store_true",
        help="skip the production prompt; only for a caller that already confirmed",
    )
    args = parser.parse_args()

    environment = cktool.PRODUCTION if args.production else cktool.DEVELOPMENT
    client = cktool.rest_client(environment)
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
        elif args.replace and event.get("movedFrom"):
            # The date changed at the source: same event, new key. Create
            # the new record and take down the one for the old date.
            old = ledger.get(event["movedFrom"], environment)
            if old:
                event["_replace"] = old["recordName"]
                event["_forget"] = event["movedFrom"]
        queue.append(event)

    # Listings absent from the source for MISS_LIMIT runs are cancelled.
    removals = ledger.due_for_removal(payload["source"], environment) if args.replace else []

    if not queue and not removals:
        print("nothing to push")
        return 0

    print(f"{DIM}via {cktool.backend_name(environment)}{RESET}")

    if args.production and not args.dry_run:
        print(f"\n{RED}{BOLD}  PRODUCTION  {RESET}")
        print(f"About to create {len(queue)} Event records visible to every")
        print("iWrestle user on the App Store. This cannot be undone in bulk.\n")
        for event in queue[:40]:
            print(f"  {event['date'][:10]}  {event['name']}")
        if len(queue) > 40:
            print(f"  ... and {len(queue) - 40} more")
        if removals:
            print(f"\nAnd delete {len(removals)} records whose listing is gone from the source:")
            for entry in removals[:40]:
                print(f"  {entry['date']}  {entry['name']}")
        if args.yes:
            print(f"\n{YELLOW}--yes given, not asking.{RESET}")
        elif input("\nType y to continue: ").strip().lower() != "y":
            print("aborted")
            return 1

    pushed = 0
    failed = 0
    moved = 0
    for event in queue:
        replacing = event.pop("_replace", None)
        forget = event.pop("_forget", None)
        verb = "move" if forget else "replace" if replacing else "push"
        print(f"{BOLD}{verb}{RESET} {event['date'][:10]}  {event['name'][:50]}")
        try:
            record_name, digest = push_one(
                event, environment, dry_run=args.dry_run,
                replace_record=replacing, client=client,
            )
        except (cktool.CKToolError, ckws.CKWSError) as error:
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
        if forget:
            ledger.forget(forget, environment)
            moved += 1
        pushed += 1
        print(f"  {GREEN}{'moved' if forget else 'replaced' if replacing else 'created'}{RESET} {record_name}")

    removed = 0
    for entry in removals:
        print(f"{BOLD}remove{RESET} {entry['date']}  {entry['name'][:50]}  (gone from source {entry['missCount']} runs)")
        if args.dry_run:
            print(f"    would delete {entry['recordName'][:8]} via {cktool.backend_name(environment)}")
            continue
        try:
            if client is not None:
                client.delete_record(entry["recordName"])
            else:
                cktool.delete_record(entry["recordName"], environment)
        except (cktool.CKToolError, ckws.CKWSError) as error:
            print(f"  {RED}failed{RESET}: {error}")
            failed += 1
            continue
        ledger.forget(entry["sourceKey"], environment)
        removed += 1
        print(f"  {GREEN}removed{RESET} {entry['recordName']}")

    extras = ""
    if moved:
        extras += f", {moved} moved"
    if removals:
        extras += f", {len(removals) if args.dry_run else removed} removed"
    if failed:
        extras += f", {failed} failed"
    if args.dry_run:
        print(f"\ndry run: {len(queue)} events would be pushed to {environment}{extras}")
    else:
        print(f"\npushed {pushed}/{len(queue)} to {environment}{extras}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
