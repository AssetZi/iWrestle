"""Is this a college-level event?

Neither Flo nor Trackwrestling exposes a competition level, so it is
inferred: a university venue plus a name in the open/invitational family
and no youth marker anywhere. iWrestle lists youth wrestling; college
opens become "Open" and are skipped unless INCLUDE_COLLEGE is set.
"""
from __future__ import annotations

import re

COLLEGE_VENUE = re.compile(r"\b(university|college|collegiate|ncaa|naia|njcaa)\b", re.I)
COLLEGE_NAME = re.compile(r"\b(college open|collegiate|ncaa|naia|njcaa|university open)\b", re.I)
OPEN_FAMILY = re.compile(r"\b(open|invitational|duals?|classic|dual meet)\b", re.I)
YOUTH_MARKER = re.compile(
    r"\b(youth|kids?|elementary|k-?\d+|novice|bantam|tots?|pee\s*wee|middle school|"
    r"junior high|jr\.? high|high school|hs|jv|varsity|scholastic|takedown|girls?)\b|\b\d{1,2}u\b",
    re.I,
)


def classify_level(name: str, venue: str = "", description: str = "") -> str | None:
    """"college" for a college-level event, else None."""
    name = name or ""
    blob = " ".join(filter(None, [name, venue, description]))
    if YOUTH_MARKER.search(blob):
        return None
    if COLLEGE_NAME.search(name):
        return "college"
    if COLLEGE_VENUE.search(f"{name} {venue}") and OPEN_FAMILY.search(name):
        return "college"
    return None
