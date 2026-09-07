#!/usr/bin/env python3
"""Write approved events into CloudKit.

    python bin/push.py data/events.pywrestling.20260904.json --dry-run
    python bin/push.py data/events.pywrestling.20260904.json
    python bin/push.py data/events.pywrestling.20260904.json --production

Development is the default because debug builds from Xcode read that
environment; production is what the App Store build reads and requires an
explicit flag plus a typed confirmation.

Order of operations for one changed event, and why:

    create new record  →  delete old record  →  write ledger entry

A failed create must never leave the event missing from the database, so
the old record is only deleted once the new one exists. The ledger is
written last so a crash between the two leaves an extra record (which
reconcile finds) rather than a missing one.

Removals are capped per run: a broken scrape or a classifier regression
would otherwise take real events down in bulk. Exit status is 1 whenever
something did not happen (a failed create, a blocked removal, a locked
ledger), so the routine can say so.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

import requests

from iwpipe import cktool, ckws, ledger, schema
from iwpipe.assets import event_asset_dir
from iwpipe.term import BOLD, DIM, GREEN, RED, RESET, YELLOW

# Removals (gone from the source, retired, excluded) allowed in one run:
# this share of the source's entries in the environment, but never fewer
# than the minimum, so a small source can still lose a handful.
REMOVAL_CAP_FRACTION = 0.10
REMOVAL_CAP_MIN = 5
# Re-pushing more than this many existing events in one run means the
# content hash changed for a reason other than the events changing (a
# template change, a cache wipe). It is allowed, but not by accident.
REPLACE_WARN = 50


def digest(event):
    """(fields, logo, flyer, content hash) without writing anything."""
    fields = cktool.build_fields(event)
    logo = Path(event["logo"])
    flyer = Path(event["flyer"]["path"])
    return fields, logo, flyer, cktool.content_hash(fields, logo, flyer)


def prepare(event):
    """Write the fields file next to the assets; returns (path, logo, flyer, hash)."""
    fields, logo, flyer, content_hash = digest(event)
    folder = event_asset_dir(event["sourceKey"])
    fields_path = folder / "fields.json"
    fields_path.write_text(json.dumps(fields, indent=2) + "\n")
    return fields_path, logo, flyer, content_hash


def push_one(event, environment, client, *, dry_run, replace_record=None):
    """Create one record (deleting the previous one when replacing).

    Returns (record name, content hash).
    """
    fields_path, logo, flyer, content_hash = prepare(event)
    if dry_run:
        verb = "replace" if replace_record else "create"
        print(f"    would {verb} via {cktool.backend_name(environment)}")
        print(f"      fields {fields_path}")
        print(f"      assets LOGO={logo} FLYER={flyer}")
        return None, content_hash

    fields = json.loads(fields_path.read_text())
    name = cktool.create_record(client, fields, logo, flyer)

    if replace_record:
        try:
            client.delete_record(replace_record)
        except (ckws.CKWSError, requests.RequestException) as error:
            print(f"    {YELLOW}old record {replace_record[:8]} not deleted: {str(error).splitlines()[-1][:80]}{RESET}")
    return name, content_hash


RETIRE_NOTES = ("excluded:", "college-level event", "adult-level event")


def retired(events, environment, already, *, record=True):
    """Ledger entries for pushed events this file now sets aside for good.

    A reclassification has to hold for RETIRE_LIMIT runs running before
    the record comes down; an exclusion is a person's call and counts at
    once. With record=False (dry run) nothing is counted, only reported.
    """
    found = []
    for event in events:
        if event["review"]["status"] != schema.STATUS_SKIP or event["sourceKey"] in already:
            continue
        notes = event["review"].get("notes", [])
        reason = next((n for n in notes if n.startswith(RETIRE_NOTES)), None)
        if not reason:
            continue
        entry = ledger.get(event["sourceKey"], environment)
        if not entry:
            continue
        if record:
            count = ledger.mark_retiring(event["sourceKey"], environment, reason)
        else:
            count = ledger.RETIRE_LIMIT if reason.startswith("excluded:") else entry.get("retireCount", 0) + 1
        if count >= ledger.RETIRE_LIMIT:
            found.append({**entry, "missCount": 0, "reason": reason})
        else:
            print(f"{DIM}retiring{RESET} {event['name'][:50]}: {reason} ({count}/{ledger.RETIRE_LIMIT} runs)")
    return found


def removal_cap(source, environment):
    entries = sum(
        1 for v in ledger.load().values()
        if v["environment"] == environment and v["sourceKey"].startswith(f"{source}:")
    )
    return max(REMOVAL_CAP_MIN, int(REMOVAL_CAP_FRACTION * entries))


def confirm(prompt, *, yes):
    if yes:
        print(f"\n{YELLOW}--yes given, not asking.{RESET}")
        return True
    if not sys.stdin.isatty():
        print(f"\n{RED}not a terminal and no --yes; stopping.{RESET}")
        return False
    return input(f"\n{prompt} ").strip().lower() == "y"


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
        help="skip the confirmations; only for a caller that already confirmed",
    )
    parser.add_argument(
        "--max-removals", type=int, default=None,
        help="allow this many removals this run (default: 10%% of the source, at least 5)",
    )
    args = parser.parse_args()

    environment = cktool.PRODUCTION if args.production else cktool.DEVELOPMENT
    try:
        client = cktool.require_client(environment)
    except cktool.NoWriteAccess as error:
        print(f"{RED}{error}{RESET}")
        return 1

    try:
        with ledger.lock():
            return _run(args, environment, client)
    except ledger.LedgerError as error:
        print(f"{RED}{error}{RESET}")
        return 1


def _run(args, environment, client) -> int:
    payload = schema.load(args.file)
    source = payload["source"]

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
            if digest(event)[3] == existing.get("contentHash"):
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
    removals = ledger.due_for_removal(source, environment) if args.replace else []
    # And a pushed event that this file now sets aside for good (excluded by
    # hand, or reclassified as college or adult) comes down as well.
    if args.replace:
        removals += retired(
            payload["events"], environment, {r["sourceKey"] for r in removals},
            record=not args.dry_run,
        )
    # Anything this file approves again is no longer on its way out, whether
    # or not its content changed.
    approved = {e["sourceKey"] for e in payload["events"] if e["review"]["status"] == schema.STATUS_APPROVED}
    if not args.dry_run and approved:
        ledger.clear_retiring(approved, environment)

    blocked = 0
    cap = args.max_removals if args.max_removals is not None else removal_cap(source, environment)
    if len(removals) > cap:
        print(
            f"{RED}{BOLD}{len(removals)} removals wanted, cap is {cap}{RESET}: none removed. "
            f"A broken scrape or a classifier change, most likely. Check them with "
            f"make review ARGS=\"--flagged\"; to allow it, push again with --max-removals {len(removals)}."
        )
        for entry in removals[:20]:
            print(f"  {entry['date']}  {entry['name'][:50]}  ({entry.get('reason') or 'gone from source'})")
        blocked = len(removals)
        removals = []

    if not queue and not removals:
        print("nothing to push" if not blocked else "nothing pushed")
        return 1 if blocked else 0

    print(f"{DIM}via {cktool.backend_name(environment)}{RESET}")

    replacing = sum(1 for e in queue if e.get("_replace") and not e.get("_forget"))
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
        if not confirm("Type y to continue:", yes=args.yes):
            print("aborted")
            return 1
    elif replacing > REPLACE_WARN and not args.dry_run:
        print(
            f"\n{YELLOW}{BOLD}{replacing} existing events would be re-pushed{RESET} (more than {REPLACE_WARN}). "
            "Unless that many listings really changed, the content hash moved for another reason "
            "(rendered assets deleted, a template change). Each replace is a delete and a create."
        )
        if not confirm("Type y to re-push them all:", yes=args.yes):
            print("aborted")
            return 1

    pushed = 0
    failed = 0
    moved = 0
    for event in queue:
        replacing_record = event.pop("_replace", None)
        forget = event.pop("_forget", None)
        verb = "move" if forget else "replace" if replacing_record else "push"
        print(f"{BOLD}{verb}{RESET} {event['date'][:10]}  {event['name'][:50]}")
        try:
            record_name, content_hash = push_one(
                event, environment, client, dry_run=args.dry_run,
                replace_record=replacing_record,
            )
        except (ckws.CKWSError, requests.RequestException) as error:
            print(f"  {RED}failed{RESET}: {str(error)[:200]}")
            failed += 1
            continue
        if args.dry_run:
            continue
        ledger.record(
            event["sourceKey"], environment, record_name, event["name"],
            day=event["date"][:10], location=event.get("location"),
            content_hash=content_hash,
        )
        if forget:
            ledger.forget(forget, environment)
            moved += 1
        pushed += 1
        print(f"  {GREEN}{'moved' if forget else 'replaced' if replacing_record else 'created'}{RESET} {record_name}")

    removed = 0
    for entry in removals:
        why = entry.get("reason") or f"gone from source {entry['missCount']} runs"
        print(f"{BOLD}remove{RESET} {entry['date']}  {entry['name'][:50]}  ({why})")
        if args.dry_run:
            print(f"    would delete {entry['recordName'][:8]} via {cktool.backend_name(environment)}")
            continue
        try:
            client.delete_record(entry["recordName"])
        except (ckws.CKWSError, requests.RequestException) as error:
            print(f"  {RED}failed{RESET}: {str(error)[:200]}")
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
    if blocked:
        extras += f", {blocked} removals blocked by the cap"
    if args.dry_run:
        print(f"\ndry run: {len(queue)} events would be pushed to {environment}{extras}")
    else:
        print(f"\npushed {pushed}/{len(queue)} to {environment}{extras}")
    return 1 if (failed or blocked) else 0


if __name__ == "__main__":
    sys.exit(main())
