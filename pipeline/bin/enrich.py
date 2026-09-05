#!/usr/bin/env python3
"""Read each event's banner with Claude and fill in what the scraper missed.

    python bin/enrich.py data/events.pywrestling.20260904.json
    python bin/enrich.py <file> --dry-run
    python bin/enrich.py <file> --key pywrestling:takedown-in-the-den:2026-09-19

Only empty or defaulted fields are filled. Every AI-sourced value is marked
with an "AI:" note, and nothing here changes review.status, so the review
gate still decides what gets pushed. Answers are cached per banner, so a
rerun costs nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

import anthropic

from iwpipe import assets, enrich, schema
from iwpipe.config import ANTHROPIC_API_KEY
from iwpipe.http import make_session

BOLD, DIM, GREEN, YELLOW, RED, RESET = (
    "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"
)
EXIT_NO_KEY = 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="list what would be sent")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--key", help="enrich only this sourceKey")
    parser.add_argument("--force", action="store_true", help="ignore the cache")
    parser.add_argument("--no-logo", action="store_true", help="keep existing logos")
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print(f"{RED}ANTHROPIC_API_KEY is not set in pipeline/.env; enrichment skipped.{RESET}")
        return EXIT_NO_KEY

    payload = schema.load(args.file)
    events = payload["events"]
    session = make_session()
    client = None if args.dry_run else anthropic.Anthropic()
    cache = enrich.load_cache()

    counts = {"enriched": 0, "cached": 0, "skipped": 0, "failed": 0}
    usages = []
    contacts_from_ai = 0

    for event in events:
        if args.key and event["sourceKey"] != args.key:
            continue
        if event["review"]["status"] == schema.STATUS_SKIP:
            continue
        if args.limit and counts["enriched"] + counts["cached"] >= args.limit:
            break

        label = f"{event['date'][:10]}  {event['name'][:48]}"
        banner = assets.ensure_banner(session, event)
        if banner is None:
            schema.note(event, "no banner, enrich skipped")
            counts["skipped"] += 1
            print(f"{DIM}skip{RESET} {label}  (no banner)")
            continue

        image_bytes = banner.read_bytes()
        image_hash = enrich.banner_hash(image_bytes)
        key = enrich.cache_key(event, image_hash)

        if args.dry_run:
            state = "cached" if key in cache else "would send"
            print(f"{DIM}{state:<10}{RESET} {label}")
            continue

        extraction = None
        if key in cache and not args.force:
            try:
                extraction = enrich.BannerExtraction.model_validate(cache[key]["extraction"])
                counts["cached"] += 1
            except enrich.ValidationError:
                extraction = None

        if extraction is None:
            try:
                extraction, usage = enrich.extract_with_retry(client, event, image_bytes)
            except anthropic.RateLimitError:
                schema.note(event, "AI: rate limited, try again later")
                counts["failed"] += 1
                print(f"{YELLOW}rate limited{RESET} {label}")
                continue
            except anthropic.APIStatusError as error:
                if error.status_code >= 500:
                    schema.note(event, f"AI: server error {error.status_code}")
                    counts["failed"] += 1
                    print(f"{YELLOW}server error{RESET} {label}")
                    continue
                print(f"{RED}request rejected ({error.status_code}): {error.message}{RESET}")
                schema.dump(args.file, payload["source"], events)
                return 1
            except anthropic.APIConnectionError:
                schema.note(event, "AI: network error")
                counts["failed"] += 1
                print(f"{YELLOW}network error{RESET} {label}")
                continue
            except enrich.ValidationError:
                schema.note(event, "AI: unparseable result")
                counts["failed"] += 1
                print(f"{YELLOW}unparseable{RESET} {label}")
                continue

            usages.append(usage)
            if extraction is None:
                schema.note(event, "AI: declined to read this banner")
                counts["failed"] += 1
                print(f"{YELLOW}declined{RESET} {label}")
                continue
            cache[key] = {"extraction": extraction.model_dump(), "at": event.get("date")}
            enrich.save_cache(cache)
            counts["enriched"] += 1

        if args.no_logo:
            event.pop("logoBBox", None)
        filled = enrich.merge(event, extraction)
        enrich.record_provenance(event, image_hash, extraction)
        if any(f in filled for f in ("email", "phone", "contactName")):
            contacts_from_ai += 1

        # Regenerate the logo (maybe a crop now) and the flyer (new links).
        _, _, asset_notes = assets.ensure_assets(session, event, force=True)
        for text in asset_notes:
            schema.note(event, text)
        for problem in schema.validate(event):
            schema.note(event, problem)

        marker = GREEN if filled else DIM
        print(f"{marker}{extraction.confidence:<7}{RESET} {label}  "
              f"{DIM}{', '.join(filled) or 'nothing new'}{RESET}")

    if args.dry_run:
        return 0

    schema.dump(args.file, payload["source"], events)
    totals = enrich.usage_totals(usages)
    print(
        f"\n{BOLD}enriched {counts['enriched']}, cached {counts['cached']}, "
        f"skipped {counts['skipped']}, failed {counts['failed']}{RESET}; "
        f"{contacts_from_ai} contacts from banners"
    )
    print(
        f"tokens: {totals['input']} in, {totals['cached']} cached, "
        f"{totals['output']} out; about ${totals['dollars']:.2f}"
    )
    print(f"next: python bin/review.py {args.file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
