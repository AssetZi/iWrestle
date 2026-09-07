#!/usr/bin/env python3
"""Compare CloudKit against the local ledger, and undo mistakes.

    python bin/reconcile.py
    python bin/reconcile.py --production
    python bin/reconcile.py --delete-key pywrestling:some-event:2026-10-17
"""
from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401

from iwpipe import cktool, ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--delete-key", help="delete the record this key created")
    args = parser.parse_args()

    environment = cktool.PRODUCTION if args.production else cktool.DEVELOPMENT

    try:
        client = cktool.require_client(environment)
    except cktool.NoWriteAccess as error:
        print(error)
        return 1

    if args.delete_key:
        try:
            with ledger.lock():
                entry = ledger.get(args.delete_key, environment)
                if not entry:
                    print(f"no ledger entry for {args.delete_key} in {environment}")
                    return 1
                client.delete_record(entry["recordName"])
                ledger.forget(args.delete_key, environment)
        except ledger.LedgerError as error:
            print(error)
            return 1
        print(f"deleted {entry['recordName']} ({entry['name']})")
        return 0

    records = client.query_records("Event", ["name", "date"], max_records=10000)
    entries = {
        key: value
        for key, value in ledger.load().items()
        if value["environment"] == environment
    }
    known = {value["recordName"] for value in entries.values()}
    unknown = [r for r in records if r.get("recordName") not in known]

    print(f"{environment}: {len(records)} records in CloudKit, {len(entries)} in ledger")
    if unknown:
        print(f"\n{len(unknown)} not created by this pipeline (app entries, most likely):")
        for record in unknown[:20]:
            fields = record.get("fields", {})
            name = fields.get("name", {}).get("value", "?")
            print(f"  {record.get('recordName','?')[:16]}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
