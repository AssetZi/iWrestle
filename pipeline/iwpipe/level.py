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
OPEN_FAMILY = re.compile(r"\b(open|invitational|invite|duals?|classic|dual meet)\b", re.I)
YOUTH_MARKER = re.compile(
    r"\b(youth|kids?|elementary|k-?\d+|novice|bantam|tots?|pee\s*wee|middle school|"
    r"junior high|jr\.? high|high school|hs|jv|varsity|scholastic|interscholastic|takedown|girls?|"
    # State high school associations (NCHSAA, GHSA), youth associations
    # (CVYWA), and Tournament of Champions qualifiers are youth wrestling
    # even when they meet at a college.
    r"\w*hsaa?|\w*ywa|tocq?)\b|\b\d{1,2}u\b",
    re.I,
)


ADULT_MARKER = re.compile(r"\b(mens?|men's|womens?|women's|adult|masters|veterans?|seniors? open|olympic|world team)\b", re.I)


def classify_level(name: str, venue: str = "", description: str = "") -> str | None:
    """"college" or "adult" for events that are not youth wrestling, else None."""
    name = name or ""
    blob = " ".join(filter(None, [name, venue, description]))
    if YOUTH_MARKER.search(blob):
        return None
    if COLLEGE_NAME.search(name):
        return "college"
    if ADULT_MARKER.search(name):
        return "adult"
    if COLLEGE_VENUE.search(f"{name} {venue}") and OPEN_FAMILY.search(name):
        return "college"
    return None


# Organizers who cannot remove a listing rename it: "Bobcat JV-Delete",
# "Delete Delete Delete", "STP Hold - Please Set Invisible", "RS Dual Test".
PLACEHOLDER = re.compile(
    r"^\s*(cancel+ed|postponed|no|tba|tbd|test|placeholder)\b|\b(cancel+ed|postponed)\b"
    r"|\bdelete\b|\bset invisible\b|\btest\s*$",
    re.I,
)
TBA_ADDRESS = re.compile(r"\btba\b|\btbd\b", re.I)
# A dual meet is one team against another: "Alta @ Bountiful", "Air Force
# vs Army", "Wilson Area Hs vs. Salisbury Twp Hs". Brock keeps them out of the
# directory (2026-10-26), and on 2026-11-02 made the rule the name alone: any
# "@" or any "vs" is a dual, whatever else the name says. That takes listings
# like "@ West Iredell" and "IGHSAU 1A Reg. 1 @" (a host never named) along
# with it. A dual tournament ("Tobin Duals", "PIAA Interscholastic Duals")
# has neither and stays.
DUAL = re.compile(r"@|\bvs\.?\b", re.I)


def is_placeholder(name: str) -> bool:
    """A listing that is not an event: cancelled, postponed, a bare "NO"/"TBA",
    or one its organizer has marked for deletion."""
    return bool(PLACEHOLDER.search(name or ""))


def is_dual(name: str) -> bool:
    """One team against another: an "@" or a "vs" anywhere in the name."""
    return bool(DUAL.search(name or ""))


def venue_is_tba(address: str) -> bool:
    """The event is real but its venue is still "TBA"; worth a look, not a skip."""
    return bool(TBA_ADDRESS.search(address or ""))
