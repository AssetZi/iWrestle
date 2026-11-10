#!/usr/bin/env python3
"""Take an event out of the directory, for good.

    python bin/exclude.py "Hurst Invitational" --reason "college open"
    python bin/exclude.py flowrestling:hurst-invitational:2026-11-01 --reason "college open"
    python bin/exclude.py --list
    python bin/exclude.py --undo flowrestling:hurst-invitational:2026-11-01

The argument is a source key or a piece of the event's name; a name that
matches more than one event is listed instead of guessed, and so is a key
the source has since replaced with longer ones. The event is deleted from
every environment it was pushed to (production only where its key is set;
otherwise the next production publish retires it), and every future
collect skips it.
--undo lets it back in on the next run.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import _bootstrap  # noqa: F401

import requests

from iwpipe import cktool, ckws, exclusions, ledger
from iwpipe.config import DATA_DIR
from iwpipe.schema import STATUS_SKIP, base_key
from iwpipe.term import BOLD, DIM, GREEN, RED, RESET, YELLOW

SOURCE_KEY = re.compile(r"^(pywrestling|flowrestling|trackwrestling):[^\s:]+:\d{4}-\d{2}-\d{2}(:\S+)?$")


def newest_events():
    """(every event ever collected by key, the keys in each source's newest file)."""
    seen = {}
    current = {}
    for path in sorted(glob.glob(str(DATA_DIR / "events.*.json"))):
        payload = json.load(open(path))
        events = payload.get("events", [])
        for event in events:
            seen[event["sourceKey"]] = event
        if events:
            current[events[0]["sourceKey"].split(":", 1)[0]] = {e["sourceKey"] for e in events}
    return seen, current


def successors(key: str, current) -> list[str]:
    """Keys in the newest file that took this key's place.

    Two listings sharing a name and a day each get a ":<id>" suffix, so last
    week's bare key no longer names anything the source lists; excluding it
    would be recorded and change nothing.
    """
    listed = current.get(key.split(":", 1)[0], set())
    if key in listed:
        return []
    return sorted(k for k in listed if k != key and base_key(k) == key)


def resolve(query: str, events, current=None):
    if query in events:
        twins = successors(query, current or {})
        return [events[k] for k in twins] if twins else [events[query]]
    if SOURCE_KEY.match(query):
        # A key is exact or it is wrong; never fall back to matching names.
        return [
            {"sourceKey": v["sourceKey"], "name": v["name"], "date": v.get("date", "")}
            for v in ledger.load().values() if v["sourceKey"] == query
        ][:1]
    needle = query.lower()
    hits = [e for e in events.values() if needle in e.get("name", "").lower()]
    if not hits:
        # It may have been pushed from an older file; the ledger remembers.
        hits = [
            {"sourceKey": v["sourceKey"], "name": v["name"], "date": v.get("date", "")}
            for v in ledger.load().values()
            if needle in v.get("name", "").lower()
        ]
        keys = {}
        for h in hits:
            keys.setdefault(h["sourceKey"], h)
        hits = list(keys.values())
    return hits


def mark_in_newest_file(key: str, reason: str) -> None:
    """Note the exclusion on the event in its source's newest collected file.

    A production publish reads that file and retires an event noted
    "excluded:". Collect and recheck add the note too, but an exclusion
    after the run's last recheck would otherwise leave it approved, and the
    publish would keep it live in production, or create it there."""
    source = key.split(":", 1)[0]
    files = glob.glob(str(DATA_DIR / f"events.{source}.*.json"))
    if not files:
        return
    # By modification time, as make promote picks it (`ls -t`).
    newest = max(files, key=os.path.getmtime)
    with open(newest) as handle:
        payload = json.load(handle)
    changed = False
    for event in payload.get("events", []):
        if event.get("sourceKey") != key:
            continue
        review = event.setdefault("review", {})
        notes = review.setdefault("notes", [])
        note = f"excluded: {reason}"
        if review.get("status") != STATUS_SKIP or note not in notes:
            review["status"] = STATUS_SKIP
            if note not in notes:
                notes.append(note)
            changed = True
    if changed:
        # Written aside and moved into place, so an interrupted write
        # cannot truncate this week's file.
        temporary = newest + ".tmp"
        with open(temporary, "w") as handle:
            handle.write(json.dumps(payload, indent=2) + "\n")
        os.replace(temporary, newest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="source key or part of the name")
    parser.add_argument("--reason", default="removed by hand")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--undo", metavar="KEY")
    args = parser.parse_args()

    if args.list:
        entries = exclusions.load()
        for key, entry in sorted(entries.items()):
            print(f"  {key:<60} {entry['reason']}")
        print(f"{len(entries)} excluded")
        return 0

    if args.undo:
        if exclusions.remove(args.undo):
            print(f"{GREEN}un-excluded{RESET} {args.undo}; it can return on the next collect")
            return 0
        print(f"{args.undo} was not excluded")
        return 1

    if not args.query:
        parser.error("give a source key or a name, or --list / --undo")

    events, current = newest_events()
    hits = resolve(args.query, events, current)
    if not hits:
        print(f"{RED}no event matches{RESET} {args.query!r}")
        return 1
    if len(hits) > 1 or hits[0]["sourceKey"] != args.query and SOURCE_KEY.match(args.query):
        print(f"{YELLOW}{len(hits)} events match; use the exact key:{RESET}")
        for e in hits[:20]:
            print(f"  {e['sourceKey']:<60} {e.get('date', '')[:10]}  {e.get('name', '')[:40]}")
        return 1

    event = hits[0]
    key = event["sourceKey"]
    exclusions.add(key, args.reason, event.get("name", ""))
    print(f"{BOLD}excluded{RESET} {key}  ({args.reason})")
    mark_in_newest_file(key, args.reason)

    status = 0
    try:
        with ledger.lock():
            for environment in ("development", "production"):
                entry = ledger.get(key, environment)
                if not entry:
                    continue
                try:
                    client = cktool.require_client(environment)
                except cktool.NoWriteAccess as error:
                    if environment == cktool.PRODUCTION:
                        # The cloud routine has no production key. The
                        # collected file's "excluded:" note makes the next
                        # production publish retire the record.
                        print(
                            f"  {DIM}production: no key here; the next production publish "
                            f"retires record {entry['recordName'][:8]}{RESET}"
                        )
                        continue
                    print(f"  {RED}{environment}: delete failed{RESET}: {str(error)[:120]}")
                    status = 1
                    continue
                try:
                    client.delete_record(entry["recordName"])
                except (ckws.CKWSError, requests.RequestException) as error:
                    print(f"  {RED}{environment}: delete failed{RESET}: {str(error)[:120]}")
                    status = 1
                    continue
                ledger.forget(key, environment)
                print(f"  {GREEN}{environment}{RESET}: record {entry['recordName'][:8]} deleted")
    except ledger.LedgerError as error:
        print(f"{RED}{error}{RESET}")
        return 1
    print(f"{DIM}Every future collect will skip it. Undo with: python bin/exclude.py --undo {key}{RESET}")
    return status


if __name__ == "__main__":
    sys.exit(main())
