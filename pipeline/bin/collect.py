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
import re
import sys
from datetime import date, datetime
from pathlib import Path

import _bootstrap  # noqa: F401

from iwpipe import assets, geocode, ledger, level, mapping, pdftext, schema
from iwpipe.collectors import COLLECTORS
from iwpipe.config import DATA_DIR, DEFAULT_CONTACT_EMAIL, INCLUDE_COLLEGE
from iwpipe.http import make_session


DEFAULT_EMAIL_NOTES = (
    "default contact email",
    "placeholder contact email: set a real DEFAULT_CONTACT_EMAIL in .env",
    "no contact email: set DEFAULT_CONTACT_EMAIL in .env",
)


def _is_default_email(email):
    return not email or email == DEFAULT_CONTACT_EMAIL or email.endswith("example.com")


def _drop_notes(event, texts):
    notes = event.setdefault("review", {}).setdefault("notes", [])
    event["review"]["notes"] = [n for n in notes if n not in texts]


def normalize(event, session, *, source, today, skip_geocode=False, refresh_assets=False,
              site_emails=frozenset()):
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

    # A college or adult open is not youth wrestling: mark it Open and, by
    # default, keep it out of the directory.
    tier = level.classify_level(event.get("name", ""), event.get("venue", ""), event.get("detailText", ""))
    if tier:
        event["ageGroups"] = ["Open"]
        schema.note(event, f"{tier}-level event")
        if not INCLUDE_COLLEGE:
            event["review"]["status"] = schema.STATUS_SKIP

    # Cancelled listings are not events; a "TBA" venue is real but unfinished.
    if level.is_placeholder(event.get("name", "")):
        schema.note(event, "cancelled or placeholder listing")
        event["review"]["status"] = schema.STATUS_SKIP
        skip_geocode = True
    elif level.venue_is_tba(event.get("address", "")):
        schema.note(event, "venue still TBA at the source")
        skip_geocode = True

    if not event.get("ageGroups"):
        schema.note(event, "no divisions found, defaulted")
        event["ageGroups"] = ["Youth", "Jr High", "High School"]

    contact = event.setdefault(
        "contact", {"firstName": "", "lastName": "", "email": "", "phone": ""}
    )
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
        _, _, asset_notes = assets.ensure_assets(session, event, force=refresh_assets)
        for text in asset_notes:
            schema.note(event, text)
        folder = assets.event_asset_dir(event["sourceKey"])
        event["logo"] = str(folder / "logo.png")
        event.setdefault("flyer", {})["path"] = str(folder / "flyer.pdf")

        # A real flyer PDF beats every default: read the contact off it,
        # unless it turns out to be another event's flyer.
        source_pdf = folder / "source-flyer.pdf"
        if source_pdf.exists():
            event["flyerText"] = pdftext.extract_text(source_pdf)
            match = pdftext.pdf_matches_event(event["flyerText"], event)
            event["flyerMatch"] = match
            if match is False:
                source_pdf.unlink()
                event["flyer"]["url"] = None
                event["flyerText"] = ""
                _, _, regen_notes = assets.ensure_assets(session, event, force=True)
                schema.note(event, "flyer PDF names a different event, dropped")
            ignore = set(site_emails) | {e.lower() for e in event.get("ignoreEmails", [])}
            email, phone = pdftext.contacts_from_text(event["flyerText"], ignore)
            if email and _is_default_email(contact.get("email", "")):
                contact["email"] = email
                _drop_notes(event, DEFAULT_EMAIL_NOTES)
                schema.note(event, "email from flyer PDF")
            if phone and not contact.get("phone"):
                contact["phone"] = phone
                schema.note(event, "phone from flyer PDF")

    # "2027 Battle in the Burgh" dated 2026 is a placeholder listing.
    year_in_name = re.search(r"\b(20\d\d)\b", event.get("name", ""))
    if year_in_name and event.get("date") and year_in_name.group(1) != event["date"][:4]:
        schema.note(event, f"name says {year_in_name.group(1)} but date is {event['date'][:4]}, verify")

    # A venue still "TBA" with nothing to place on the map is not listable
    # yet; keep it out of the pending pile so review stays readable.
    if level.venue_is_tba(event.get("address", "")) and not event.get("location"):
        event["review"]["status"] = schema.STATUS_SKIP

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
    parser.add_argument(
        "--refresh-assets", action="store_true",
        help="regenerate logos and flyers even if they exist (after code changes)",
    )
    args = parser.parse_args()

    session = make_session()
    collector = COLLECTORS[args.source]
    site_emails = getattr(collector, "SITE_EMAILS", frozenset())
    extra = {"flo_session": session} if args.source == "trackwrestling" else {}
    raw = collector.collect(
        session, fixture=args.from_fixture, limit=args.limit,
        dump_unparsed=args.dump_unparsed, **extra,
    )
    print(f"collected {len(raw)} raw listings from {args.source}")

    today = date.today()
    events = []
    for item in raw:
        event = normalize(
            item, session, source=args.source, today=today,
            skip_geocode=args.skip_geocode, refresh_assets=args.refresh_assets,
            site_emails=site_emails,
        )
        # Being in one environment's ledger must not block the other: push
        # refuses repeats per environment on its own. Just say where it is.
        for environment in ("development", "production"):
            if ledger.contains(event["sourceKey"], environment):
                schema.note(event, f"already in {environment}")
        if True:
            duplicates = ledger.find_similar(
                event["sourceKey"], schema.slug(event.get("name", "")),
                (event.get("date") or "")[:10], event.get("location"),
            )
            if duplicates:
                event["review"]["status"] = schema.STATUS_SKIP
                schema.note(
                    event, "possible duplicate of " + ", ".join(duplicates)
                )
            else:
                nearby = ledger.find_nearby(
                    event["sourceKey"], (event.get("date") or "")[:10], event.get("location")
                )
                if nearby:
                    schema.note(event, "same day a few km from " + ", ".join(nearby) + ", check for duplicate")
        events.append(event)

    # Two events sharing one registration form is how one of them ends up
    # with the other's flyer; say so where a person will see it.
    by_form: dict[str, list] = {}
    for event in events:
        if event.get("registration"):
            by_form.setdefault(event["registration"], []).append(event)
    for shared in by_form.values():
        if len(shared) > 1:
            for event in shared:
                others = ", ".join(e["name"] for e in shared if e is not event)
                schema.note(event, f"registration form shared with {others}")

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
