#!/usr/bin/env python3
"""Score the enrich prompt against tests/evals/enrich.

    python bin/enrich_eval.py            # every case, live calls to the model
    python bin/enrich_eval.py --limit 2  # a quick check
    python bin/enrich_eval.py --list     # what the set contains, no calls

Each case is one real banner (and flyer PDF, where the organizer posted
one) with the answers a person checked. The prompt is the only part of the
pipeline with no other regression check, so run this after every
PROMPT_VERSION bump. It costs about a dollar for the whole set.

A case scores one point per field that agrees with expected.json: contact
email, mapped age groups, whether the flyer belongs to the event, the
registration link's host. Exit status is 1 when the average falls under
PASS_MARK.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import _bootstrap  # noqa: F401

from iwpipe import enrich, mapping
from iwpipe.config import ANTHROPIC_API_KEY, PIPELINE_ROOT
from iwpipe.term import BOLD, DIM, GREEN, RED, RESET, YELLOW

EVAL_DIR = PIPELINE_ROOT / "tests" / "evals" / "enrich"
PASS_MARK = 0.8
EXIT_UNAVAILABLE = 2


def cases() -> list[Path]:
    return sorted(p for p in EVAL_DIR.iterdir() if (p / "event.json").exists())


def _host(url: str | None) -> str:
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    return urlparse(url).netloc.lower().removeprefix("www.")


def score(extraction: enrich.BannerExtraction, expected: dict) -> tuple[int, int, list[str]]:
    """(points, possible, what was wrong)."""
    points, possible, wrong = 0, 0, []

    if expected.get("email"):
        possible += 1
        got = (extraction.contact.email or "").strip().lower()
        if got == expected["email"].lower():
            points += 1
        else:
            wrong.append(f"email {got or 'none'!r} != {expected['email']!r}")

    if expected.get("ageGroups"):
        possible += 1
        groups, _ = mapping.normalize_age_groups(", ".join(extraction.divisions or []))
        if set(groups) == set(expected["ageGroups"]):
            points += 1
        else:
            wrong.append(f"ageGroups {groups} != {expected['ageGroups']}")

    if expected.get("flyerMatchesEvent") is not None:
        possible += 1
        if extraction.flyerMatchesEvent == expected["flyerMatchesEvent"]:
            points += 1
        else:
            wrong.append(f"flyerMatchesEvent {extraction.flyerMatchesEvent} != {expected['flyerMatchesEvent']}")

    if expected.get("registrationUrl"):
        possible += 1
        if _host(extraction.registrationUrl) == _host(expected["registrationUrl"]):
            points += 1
        else:
            wrong.append(f"registration host {_host(extraction.registrationUrl) or 'none'!r} != {_host(expected['registrationUrl'])!r}")

    return points, possible, wrong


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    found = cases()
    if args.list:
        for case in found:
            expected = json.loads((case / "expected.json").read_text())
            print(f"  {case.name:<40} {'pdf ' if (case / 'flyer.pdf').exists() else '    '} {expected.get('email') or '-'}")
        print(f"{len(found)} cases, prompt v{enrich.PROMPT_VERSION}")
        return 0

    if not ANTHROPIC_API_KEY:
        print(f"{RED}ANTHROPIC_API_KEY is not set in pipeline/.env{RESET}")
        return EXIT_UNAVAILABLE

    import anthropic

    from iwpipe import assets

    client = anthropic.Anthropic()
    usages, total_points, total_possible = [], 0, 0
    print(f"{DIM}prompt v{enrich.PROMPT_VERSION}, model {enrich.ENRICH_MODEL}{RESET}")
    for case in found[: args.limit] if args.limit else found:
        event = json.loads((case / "event.json").read_text())
        expected = json.loads((case / "expected.json").read_text())
        image_bytes = (case / "banner.jpg").read_bytes()
        pdf_bytes = (case / "flyer.pdf").read_bytes() if (case / "flyer.pdf").exists() else None
        page_bytes = None
        if pdf_bytes:
            page = assets.render_pdf_page(case / "flyer.pdf", case / "flyer-page1.png")
            page_bytes = page.read_bytes() if page else None
            (case / "flyer-page1.png").unlink(missing_ok=True)

        extraction, usage = enrich.extract_with_retry(client, event, image_bytes, pdf_bytes, page_bytes)
        usages.append(usage)
        if extraction is None:
            print(f"{RED}refused{RESET}  {case.name}")
            total_possible += 1
            continue
        points, possible, wrong = score(extraction, expected)
        total_points += points
        total_possible += possible
        marker = GREEN if points == possible else YELLOW if points else RED
        print(f"{marker}{points}/{possible}{RESET}  {case.name:<40} {extraction.confidence:<7} {'; '.join(wrong)}")

    if not total_possible:
        print("nothing scored")
        return 1
    ratio = total_points / total_possible
    totals = enrich.usage_totals(usages)
    print(f"\n{BOLD}{total_points}/{total_possible} ({ratio:.0%}){RESET}, pass mark {PASS_MARK:.0%}; about ${totals['dollars']:.2f}")
    return 0 if ratio >= PASS_MARK else 1


if __name__ == "__main__":
    sys.exit(main())
