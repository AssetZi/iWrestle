#!/usr/bin/env python3
"""Apply Brock's standing rules to the events the pipeline flagged.

Run from the pipeline directory with its virtualenv:

    .venv/bin/python ../.claude/skills/iwrestle-events/scripts/triage.py report
    .venv/bin/python ../.claude/skills/iwrestle-events/scripts/triage.py plan
    .venv/bin/python ../.claude/skills/iwrestle-events/scripts/triage.py apply

report  prints the per-source numbers the weekly report needs (--brief: counts only).
plan    prints what the rules would exclude or rename and what still needs Brock.
apply   runs bin/exclude.py for every event in the plan (deletes it from
        CloudKit wherever it was pushed and keeps it out of future collects)
        and records corrected names. Its last line says whether anything
        changed; if so, `make recheck` pushes the result without scraping.

The rules, as Brock gave them on 2026-09-22 and 2026-10-05, apply only to
events the collect step flagged for a decision:
  1. an invitational is removed;
  2. a college event is removed;
  3. two look-alike listings on the same date, whether or not the names
     match: keep the one with the most information (real contact email,
     phone, flyer, registration link, map location, divisions), remove the
     other. A tie goes to the approved one, then the one already pushed,
     then pywrestling for its flyer;
  4. two listings on different dates: keep both;
  5. a listing whose name says it is cancelled is removed;
  6. two listings on the same date sharing one registration form: keep one,
     by the same measure as rule 3;
  7. a moved date is accepted;
  8. a year in the name that disagrees with the date: the event is kept and
     its name corrected to the year of its date (data/renamed.json).
Anything the rules cannot settle (a flyer for another event, a low-confidence
AI read) is listed under "remains" for Brock.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys
from datetime import date

# The skill lives in <repo>/.claude/skills/iwrestle-events/scripts; the
# pipeline is its sibling at <repo>/pipeline. IWRESTLE_PIPELINE overrides.
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
PIPELINE = os.environ.get("IWRESTLE_PIPELINE") or os.path.join(_REPO, "pipeline")
if not os.path.isdir(os.path.join(PIPELINE, "iwpipe")):
    PIPELINE = "/Users/brock/Developer/iWrestle/pipeline"
sys.path.insert(0, PIPELINE)
sys.path.insert(0, os.path.join(PIPELINE, "bin"))
import _bootstrap  # noqa: E402,F401  (loads .env)

from iwpipe import exclusions, ledger, level, renames, schema  # noqa: E402

SOURCES = ("pywrestling", "flowrestling", "trackwrestling")

DECISION = (
    "possible duplicate of", "same day a few km", "registration form shared with",
    "flyer PDF names a different event", "moved from", "AI: low confidence",
    "AI: attached flyer is for another event",
)
CONTACT_NOTES = ("AI: email", "AI: phone", "AI: contact name", "email from flyer PDF")
SKIP_REASONS = ("college-level event", "adult-level event", "excluded:", "cancelled or placeholder listing")

INVITATIONAL = re.compile(r"\b(invitational|invite)\b", re.I)
CANCELLED = re.compile(r"\bcancel", re.I)
KEY = re.compile(r"(?:flowrestling|trackwrestling|pywrestling):[^,\s]+")
DUAL = re.compile(r"^[^@]+ @ [^@]+$")
# Colleges whose dual meets Flo lists among youth events. A name on this list
# on either side of an "@" is a college dual. Add to it when a new one shows
# up under "remains"; a miss is only a line for Brock, a wrong hit deletes
# an event, so keep entries unambiguous (no "Central", no city names).
COLLEGES = (
    "augustana", "elmhurst", "millikin", "aurora", "ill. wesleyan", "illinois wesleyan",
    "north central (il)", "carthage", "eureka", "blackburn", "westminster (mo)",
    "avila", "ottawa university", "friends university", "gannon", "ashland",
    "ursinus", "east stroudsburg", "mcdaniel", "chatham", "penn st.-altoona",
    "penn st.- altoona", "ithaca", "buffalo st.", "william penn", "baker university",
    "community college", "otero college", "edinboro", "davidson", "american",
    "concordia wisconsin", "elmira", "john carroll", "messiah", "muhlenberg",
    "lycoming", "king's (pa)", "wilkes", "delaware valley", "york (pa)",
    "stevens", "nyu", "hunter", "rit", "cortland", "oneonta", "brockport",
    "oswego", "alfred st.", "springfield", "wpi", "coast guard", "roger williams",
    "johnson & wales", "trinity (ct)", "wesleyan (ct)", "williams", "castleton",
    "norwich", "plymouth st.", "rhode island college", "bridgewater st.",
    "western new england", "utica", "keystone", "centenary (nj)", "morrisville st.",
    "wabash", "manchester", "mount st. joseph", "adrian", "olivet", "trine",
    "alma", "heidelberg", "baldwin wallace", "ohio northern", "john carroll",
    "wilmington (oh)", "otterbein", "mount union", "capital", "wartburg", "coe",
    "luther", "loras", "cornell college", "simpson", "central (ia)", "dubuque",
    "nebraska wesleyan", "buena vista", "concordia (wi)", "lakeland", "wisconsin-",
    "uw-", "st. john's (mn)", "augsburg", "st. olaf", "concordia-moorhead",
    "waldorf", "grand view", "morningside", "doane", "york (ne)", "midland",
    "hastings", "briar cliff", "northwestern (ia)", "dakota wesleyan", "jamestown",
    "dickinson st.", "montana st.-northern", "southern oregon", "menlo", "simpson (ca)",
    "embry-riddle", "arizona christian", "ottawa (az)", "benedictine", "grand canyon",
    # Division I names that never belong to a high school.
    "air force", "navy", "oklahoma st.", "iowa st.", "ohio st.", "michigan st.",
    "arizona st.", "nc state", "n.c. state", "lehigh", "cornell", "princeton",
    "harvard", "columbia", "rutgers", "purdue", "northwestern", "stanford",
    "cal poly", "oregon st.", "boise st.", "utah valley", "north dakota st.",
    "south dakota st.", "virginia tech", "west virginia", "bucknell", "binghamton",
    "hofstra", "sacred heart", "kent st.", "cleveland st.", "campbell",
    "appalachian st.", "chattanooga", "gardner-webb", "presbyterian", "the citadel",
    "george mason", "drexel", "rider", "franklin & marshall", "cal baptist",
    "little rock", "csu bakersfield", "northern colorado", "northern iowa",
    "south dakota st", "wyoming @", "@ wyoming",
)
COLLEGE_VENUE = re.compile(r"\b(university|college|collegiate|ncaa|naia|njcaa)\b", re.I)


# --- Loading -------------------------------------------------------------------

def newest_file(source: str, day: str | None) -> str | None:
    if day:
        path = os.path.join(PIPELINE, "data", f"events.{source}.{day}.json")
        if os.path.exists(path):
            return path
    files = sorted(glob.glob(os.path.join(PIPELINE, "data", f"events.{source}.*.json")))
    return files[-1] if files else None


# Which file each source was read from, for the stale check below.
FILES: dict[str, str] = {}


def file_day(source: str) -> str:
    return os.path.basename(FILES[source]).split(".")[-2]


def stale_sources() -> dict[str, str]:
    """Sources whose newest file is older than another source's.

    A source that failed to collect leaves last week's file as its newest;
    its numbers are last week's and its events may no longer be listed.
    """
    days = {source: file_day(source) for source in FILES}
    newest = max(days.values(), default="")
    missing = {source: "never collected" for source in SOURCES if source not in FILES}
    return {**missing, **{source: day for source, day in days.items() if day < newest}}


def warn_stale() -> None:
    for source, day in stale_sources().items():
        print(f"!! {source}: STALE, not collected this run (newest file: {day}); its numbers and plan lines are from that file")


def load_all(day: str | None) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    events: dict[str, dict] = {}
    by_source: dict[str, list[dict]] = {}
    for source in SOURCES:
        path = newest_file(source, day)
        if not path:
            continue
        FILES[source] = path
        rows = json.load(open(path))["events"]
        by_source[source] = rows
        for event in rows:
            events[event["sourceKey"]] = event
    return events, by_source


def notes(event: dict) -> list[str]:
    return event.get("review", {}).get("notes", [])


def flagged(event: dict) -> list[str]:
    return [n for n in notes(event) if n.startswith(DECISION) or "name says" in n]


def pushed_to(key: str) -> list[str]:
    return [env for env in ("development", "production") if ledger.get(key, env)]


def short(key: str) -> str:
    return "".join(env[0] for env in pushed_to(key)) or "-"


# --- Rules ---------------------------------------------------------------------

def is_invitational(event: dict) -> bool:
    return bool(INVITATIONAL.search(event.get("name", "")))


def is_college(event: dict) -> bool:
    name = event.get("name", "") or ""
    venue = event.get("venue") or ""
    address = event.get("address") or ""
    if level.YOUTH_MARKER.search(f"{name} {venue}"):
        return False
    if level.classify_level(name, venue) == "college":
        return True
    if DUAL.match(name):
        lowered = name.lower()
        if any(college in lowered for college in COLLEGES):
            return True
        if COLLEGE_VENUE.search(f"{venue} {address}"):
            return True
    if "Open" in event.get("ageGroups", []) and COLLEGE_VENUE.search(f"{venue} {address}"):
        return True
    return False


def norm(name: str) -> set[str]:
    text = name.lower()
    text = re.sub(r"\b(20\d\d|2\d/2\d|\d+(st|nd|rd|th)|annual|an|tournament|tourn|the|of|at|day \d)\b", " ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return set(text.split())


def same_event(a: dict, b: dict) -> bool:
    x, y = norm(a.get("name", "")), norm(b.get("name", ""))
    if not x or not y:
        return False
    return len(x & y) / len(x | y) >= 0.5 or x <= y or y <= x


def info_score(event: dict) -> int:
    """How much a listing tells a family: one point per thing it carries."""
    contact = event.get("contact") or {}
    email = contact.get("email", "")
    flyer = event.get("flyer") or {}
    return sum((
        bool(email) and not schema.is_default_email(email),
        bool(contact.get("phone")),
        bool(flyer.get("url") if isinstance(flyer, dict) else flyer),
        bool(event.get("registration")),
        bool(event.get("location")),
        bool(event.get("divisionsText")),
    ))


def keep_score(key: str, event: dict) -> int:
    score = 100 * info_score(event)
    email = (event.get("contact") or {}).get("email", "")
    if email and not schema.is_default_email(email):
        score += 4
    if event.get("review", {}).get("status") == "approved":
        score += 3
    score += len(pushed_to(key))
    score += {"pywrestling": 2, "flowrestling": 1, "trackwrestling": 0}[key.split(":")[0]]
    if len(key.split(":")) == 3:
        score += 1
    return score


YEAR = re.compile(r"\b20\d\d\b")


def corrected_name(event: dict) -> str | None:
    """The name with its year brought into line with the date, if it is off."""
    name, year = event.get("name", ""), event.get("date", "")[:4]
    found = YEAR.findall(name)
    if not year or len(found) != 1 or found[0] == year:
        return None  # two years in a name ("2026-2027 Kickoff") is not ours to guess
    return YEAR.sub(year, name)


def build_plan(events: dict[str, dict], ignore_excluded: bool = False):
    excluded = {} if ignore_excluded else exclusions.load()
    plan: dict[str, str] = {}
    renamed: dict[str, str] = {}
    remains: dict[str, list[str]] = collections.defaultdict(list)

    def drop(key: str, reason: str) -> None:
        if key not in excluded and key not in plan:
            plan[key] = reason

    candidates = {k: e for k, e in events.items() if k not in excluded and flagged(e)}

    for key, event in candidates.items():
        if is_invitational(event):
            drop(key, "invitational")
        elif is_college(event):
            drop(key, "college event")
        elif CANCELLED.search(event.get("name", "")):
            drop(key, "cancelled listing")

    seen: set[tuple[str, str]] = set()
    for key, event in candidates.items():
        if key in plan:
            continue
        for note in notes(event):
            if not note.startswith(("possible duplicate of", "same day a few km")):
                continue
            for other_key in KEY.findall(note):
                other = events.get(other_key)
                if other is None or other_key in excluded or other_key in plan:
                    continue  # not collected today: it retires on its own
                pair = tuple(sorted((key, other_key)))
                if pair in seen:
                    continue
                seen.add(pair)
                if event.get("date", "")[:10] != other.get("date", "")[:10]:
                    continue  # different dates: both stay
                keep, lose = (key, other_key) if keep_score(key, event) >= keep_score(other_key, other) else (other_key, key)
                drop(lose, f"same-date duplicate of {keep}")

    # One registration form on two listings of one day is one event listed twice.
    by_form: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for key, event in events.items():
        if event.get("registration") and key not in excluded and key not in plan:
            by_form[(event["registration"], event.get("date", "")[:10])].append(key)
    for keys in by_form.values():
        if len(keys) < 2 or not any(k in candidates for k in keys):
            continue
        keep = max(keys, key=lambda k: keep_score(k, events[k]))
        for key in keys:
            if key != keep:
                drop(key, f"same-date duplicate of {keep} (shared registration form)")

    known = renames.load()
    for key, event in candidates.items():
        if key in plan:
            continue
        for note in flagged(event):
            if note.startswith(("possible duplicate of", "same day a few km", "registration form shared with", "moved from")):
                continue  # settled above, or accepted as it stands
            if "name says" in note:
                name = corrected_name(event)
                if name and key not in known:
                    renamed[key] = name
                elif not name and event.get("date", "")[:4] not in YEAR.findall(event.get("name", "")):
                    remains[key].append(note)  # "2026-2027 Team Duals" dated 2027 is a season, and fine
                continue
            remains[key].append(note)
    return plan, renamed, remains


# --- Commands ------------------------------------------------------------------

def cmd_report(events, by_source, args) -> int:
    excluded = exclusions.load()
    warn_stale()
    stale = stale_sources()
    for source, rows in by_source.items():
        status = collections.Counter(e["review"]["status"] for e in rows)
        invalid = sum(1 for e in rows if schema.validate(e))
        reasons = collections.Counter()
        contacts, decisions, low = [], [], []
        for e in rows:
            when, name = e.get("date", "")[:10], e.get("name", "")
            for n in notes(e):
                if e["review"]["status"] == "skip":
                    for r in SKIP_REASONS:
                        if n.startswith(r):
                            reasons[r.rstrip(":")] += 1
                # Contacts are worth a look once: only for events not yet in production.
                if n.startswith(CONTACT_NOTES) and "already in production" not in notes(e):
                    c = e.get("contact") or {}
                    who = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                    contacts.append(f"{when}  {name}  |  {who}  {c.get('email', '')}  {c.get('phone', '')}")
                if n.startswith(("AI: low confidence", "AI: attached flyer is for another event")):
                    low.append(f"{when}  {name}  |  {n}")
            if e["sourceKey"] not in excluded and flagged(e):
                decisions.append(f"{when}  {name}  |  " + "; ".join(flagged(e))[:160])
        dups = sum(1 for e in rows if e["review"]["status"] == "skip" and any(n.startswith("possible duplicate") for n in notes(e)))
        print(f"\n== {source}: {len(rows)} events" + (f"  (STALE: file from {stale[source]})" if source in stale else ""))
        print(f"  status: " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())) + f"; {invalid} fail validate")
        print("  skipped as: " + (", ".join(f"{k} {v}" for k, v in reasons.items()) or "none") + f"; possible duplicate {dups}")
        if args.brief:
            print(f"  new contacts from AI/flyer {len(set(contacts))}; low confidence / wrong flyer {len(low)}")
            for line in low:
                print("    " + line)
            continue
        print(f"  contacts from AI/flyer ({len(contacts)}):")
        for line in sorted(set(contacts)):
            print("    " + line)
        print(f"  need a decision ({len(decisions)}):")
        shown = decisions if args.all else decisions[:15]
        for line in shown:
            print("    " + line)
        if len(decisions) > len(shown):
            print(f"    ... and {len(decisions) - len(shown)} more (--all lists them)")
        print(f"  low confidence / wrong flyer ({len(low)}):")
        for line in low:
            print("    " + line)
    approved_inv = sum(
        1 for e in events.values()
        if e["review"]["status"] == "approved" and e["sourceKey"] not in excluded and is_invitational(e) and not flagged(e)
    )
    print(f"\napproved invitationals not flagged (kept; Brock has not ruled on these): {approved_inv}")
    return 0


def print_plan(events, plan, renamed, remains) -> None:
    warn_stale()
    print(f"== would exclude {len(plan)}")
    by_reason = collections.Counter(r.split(" of ")[0] for r in plan.values())
    print("  " + ", ".join(f"{k} {v}" for k, v in by_reason.items()))
    for key, reason in plan.items():
        e = events[key]
        live = "  IN PRODUCTION" if "production" in pushed_to(key) else ""
        print(f"  {e.get('date', '')[:10]}  {e.get('name', '')[:50]:<50}  {e['review']['status']:<8} {short(key):<2}  {key}  <- {reason}{live}")
    print(f"== would rename {len(renamed)}")
    for key, name in renamed.items():
        print(f"  {events[key].get('date', '')[:10]}  {events[key].get('name', '')[:50]}  ->  {name[:50]}")
    print(f"== remains for Brock {len(remains)}")
    for key, lines in remains.items():
        e = events[key]
        print(f"  {e.get('date', '')[:10]}  {e.get('name', '')[:50]:<50}  {e['review']['status']:<8} {short(key):<2}  {key}")
        for line in lines:
            print(f"      - {line[:170]}")


def cmd_plan(events, by_source, args) -> int:
    plan, renamed, remains = build_plan(events, ignore_excluded=args.ignore_excluded)
    print_plan(events, plan, renamed, remains)
    return 0


def cmd_apply(events, by_source, args) -> int:
    plan, renamed, remains = build_plan(events)
    print_plan(events, plan, renamed, remains)
    if renamed:
        names = {**renames.load(), **renamed}
        renames.RENAMED_PATH.write_text(json.dumps(names, indent=2, sort_keys=True) + "\n")
        print(f"== renamed {len(renamed)} (data/renamed.json)")
    if not plan:
        print("nothing to exclude")
        print("== changed: run make recheck" if renamed else "== unchanged")
        return 0
    python = os.path.join(PIPELINE, ".venv", "bin", "python")
    failed = 0
    print(f"== excluding {len(plan)}")
    for key, reason in plan.items():
        result = subprocess.run(
            [python, "bin/exclude.py", key, "--reason", reason],
            cwd=PIPELINE, capture_output=True, text=True,
        )
        deleted = re.findall(r"(development|production): record \w+ deleted", result.stdout)
        state = "OK  " if result.returncode == 0 else "FAIL"
        detail = ", ".join(d.split(":")[0] for d in deleted) or "not pushed"
        if result.returncode != 0:
            detail = (result.stdout + result.stderr).strip().replace("\n", " | ")[:200]
            failed += 1
        print(f"  {state} {key}  ({detail})")
    print(f"== excluded {len(plan) - failed}, failed {failed}")
    print("== changed: run make recheck")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("report", "plan", "apply"))
    parser.add_argument("--date", default=date.today().strftime("%Y%m%d"), help="YYYYMMDD of the collected files (default today; falls back to the newest)")
    parser.add_argument("--brief", action="store_true", help="report only: counts, no lists")
    parser.add_argument("--all", action="store_true", help="report only: list every event needing a decision, not the first 15")
    parser.add_argument("--ignore-excluded", action="store_true", help="plan only: pretend excluded.json is empty (to test the rules)")
    args = parser.parse_args()
    events, by_source = load_all(args.date)
    if not events:
        print("no collected files found")
        return 1
    return {"report": cmd_report, "plan": cmd_plan, "apply": cmd_apply}[args.command](events, by_source, args)


if __name__ == "__main__":
    sys.exit(main())
