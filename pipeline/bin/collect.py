#!/usr/bin/env python3
"""Scrape one source into a normalized, reviewable JSON file.

    python bin/collect.py --source pywrestling
    python bin/collect.py --source pywrestling --from-fixture fixtures/py.html

Collectors only extract raw text. Everything that must match the app exactly
(age groups, event type, timestamps, coordinates, assets) is normalized here,
in one place.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

import _bootstrap  # noqa: F401

from iwpipe import assets, geocode, ledger, mapping, schema
from iwpipe.collectors import COLLECTORS
from iwpipe.config import DATA_DIR
from iwpipe.http import make_session


def normalize(event, session, *, source, today, skip_geocode=False):
    """Raw collector output -> a pushable event, flagging anything doubtful."""
    event.setdefault("source", source)

    event["eventType"] = mapping.normalize_event_type(
        event.get("name", ""), event.get("formatText", ""), event.get("rawText", "")
    )

    if not event.get("date"):
        from iwpipe.dates import to_utc_iso

        event["date"] = to_utc_iso(
            event.get("dateText", ""), event.get("timeText"), today=today
        )
    if not event.get("date"):
        schema.note(event, f"unparsed date: {event.get('dateText', '')!r}")

    groups, unknown = mapping.normalize_age_groups(
        " ".join(filter(None, [event.get("divisionsText", ""), event.get("name", "")]))
    )
    if groups:
        event["ageGroups"] = groups
    if unknown:
        schema.note(event, "unmapped division tokens: " + ", ".join(unknown))
    if not event.get("ageGroups"):
        schema.note(event, "no divisions found, defaulted")
        event["ageGroups"] = ["Youth", "Jr High", "High School"]

    contact = event.setdefault(
        "contact", {"firstName": "", "lastName": "", "email": "", "phone": ""}
    )
    from iwpipe.config import DEFAULT_CONTACT_EMAIL, DEFAULT_CONTACT_PHONE

    if not contact.get("firstName"):
        organizer = event.get("organizer") or event.get("name", "Event")
        contact["firstName"] = organizer[:60]
        contact["lastName"] = "(Organizer)"
        schema.note(event, "organizer used as contact name")
    if not contact.get("email"):
        contact["email"] = DEFAULT_CONTACT_EMAIL
        if not DEFAULT_CONTACT_EMAIL:
            schema.note(event, "no contact email: set DEFAULT_CONTACT_EMAIL in .env")
        elif DEFAULT_CONTACT_EMAIL.endswith("example.com"):
            schema.note(
                event,
                "placeholder contact email: set a real DEFAULT_CONTACT_EMAIL in .env",
            )
        else:
            schema.note(event, "default contact email")
    if not contact.get("phone"):
        contact["phone"] = DEFAULT_CONTACT_PHONE
        schema.note(event, "default contact phone")

    event["sourceKey"] = schema.source_key(
        source, event.get("name", ""), event.get("date") or ""
    )

    if not skip_geocode and not event.get("location") and event.get("address"):
        hit = geocode.lookup(session, event["address"])
        if hit:
            event["location"] = {
                "latitude": hit["latitude"],
                "longitude": hit["longitude"],
            }
            if hit.get("confidence") == "city":
                schema.note(event, "city-level geocode, verify address")
        else:
            schema.note(event, "geocode failed")

    if event.get("date") and event.get("name"):
        _, _, asset_notes = assets.ensure_assets(session, event)
        for text in asset_notes:
            schema.note(event, text)
        folder = assets.event_asset_dir(event["sourceKey"])
        event["logo"] = str(folder / "logo.png")
        event.setdefault("flyer", {})["path"] = str(folder / "flyer.pdf")

    for problem in schema.validate(event):
        schema.note(event, problem)

    return event


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=sorted(COLLECTORS))
    parser.add_argument("--from-fixture", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--skip-geocode", action="store_true")
    parser.add_argument("--dump-unparsed", action="store_true")
    args = parser.parse_args()

    session = make_session()
    collector = COLLECTORS[args.source]
    raw = collector.collect(
        session, fixture=args.from_fixture, limit=args.limit,
        dump_unparsed=args.dump_unparsed,
    )
    print(f"collected {len(raw)} raw listings from {args.source}")

    today = date.today()
    events = []
    for item in raw:
        event = normalize(
            item, session, source=args.source, today=today,
            skip_geocode=args.skip_geocode,
        )
        if ledger.contains(event["sourceKey"], "production") or ledger.contains(
            event["sourceKey"], "development"
        ):
            event["review"]["status"] = schema.STATUS_SKIP
            schema.note(event, "already pushed")
        else:
            duplicates = [
                key
                for key in ledger.find_cross_source(
                    schema.slug(event.get("name", "")), (event.get("date") or "")[:10]
                )
                if key != event["sourceKey"]
            ]
            if duplicates:
                event["review"]["status"] = schema.STATUS_SKIP
                schema.note(
                    event, "possible duplicate of " + ", ".join(duplicates)
                )
        events.append(event)

    out = args.out or DATA_DIR / (
        f"events.{args.source}.{datetime.now().strftime('%Y%m%d')}.json"
    )
    schema.dump(out, args.source, events)

    ready = sum(1 for e in events if not schema.validate(e))
    print(f"wrote {out} ({ready}/{len(events)} complete)")
    print("next: python bin/review.py", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
