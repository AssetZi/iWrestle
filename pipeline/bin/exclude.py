#!/usr/bin/env python3
"""Take an event out of the directory, for good.

    python bin/exclude.py "Hurst Invitational" --reason "college open"
    python bin/exclude.py flowrestling:hurst-invitational:2026-11-01 --reason "college open"
    python bin/exclude.py --list
    python bin/exclude.py --undo flowrestling:hurst-invitational:2026-11-01

The argument is a source key or a piece of the event's name; a name that
matches more than one event is listed instead of guessed. The event is
deleted from every environment it was pushed to, and every future collect
skips it. --undo lets it back in on the next run.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys

import _bootstrap  # noqa: F401

import requests

from iwpipe import cktool, ckws, exclusions, ledger
from iwpipe.config import DATA_DIR
from iwpipe.term import BOLD, DIM, GREEN, RED, RESET, YELLOW


def newest_events():
    seen = {}
    for path in sorted(glob.glob(str(DATA_DIR / "events.*.json"))):
        for event in json.load(open(path)).get("events", []):
            seen[event["sourceKey"]] = event
    return seen


def resolve(query: str, events):
    if query in events:
        return [events[query]]
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

    hits = resolve(args.query, newest_events())
    if not hits:
        print(f"{RED}no event matches{RESET} {args.query!r}")
        return 1
    if len(hits) > 1:
        print(f"{YELLOW}{len(hits)} events match; use the exact key:{RESET}")
        for e in hits[:20]:
            print(f"  {e['sourceKey']:<60} {e.get('date', '')[:10]}  {e.get('name', '')[:40]}")
        return 1

    event = hits[0]
    key = event["sourceKey"]
    exclusions.add(key, args.reason, event.get("name", ""))
    print(f"{BOLD}excluded{RESET} {key}  ({args.reason})")

    status = 0
    try:
        with ledger.lock():
            for environment in ("development", "production"):
                entry = ledger.get(key, environment)
                if not entry:
                    continue
                try:
                    cktool.require_client(environment).delete_record(entry["recordName"])
                except (cktool.NoWriteAccess, ckws.CKWSError, requests.RequestException) as error:
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
