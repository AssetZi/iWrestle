"""Source vocabulary -> the app's exact raw values.

Age group strings must match AgeGroup in
iWrestle/Views/Components/AgeGroupPicker.swift and event types must match
EventType in iWrestle/Views/Components/EventTypePicker.swift, character for
character, or the app's filters silently exclude the event.
"""
from __future__ import annotations

import re

from .schema import AGE_GROUPS

# Longest phrases first so "jr high" wins before "jr".
AGE_GROUP_TOKENS: list[tuple[str, str]] = [
    # Jr High
    (r"\bjr\.?\s*high\b", "Jr High"),
    (r"\bjunior\s+high\b", "Jr High"),
    (r"\bmiddle\s+school\b", "Jr High"),
    (r"\bms\b", "Jr High"),
    (r"\bk-?8\b", "Jr High"),
    (r"\b7\s*-\s*8\b", "Jr High"),
    (r"\b7th\s*[-/&]\s*8th\b", "Jr High"),
    # High School
    (r"\bhigh\s+school\b", "High School"),
    (r"\bhs\b", "High School"),
    (r"\bvarsity\b", "High School"),
    (r"\bjv\b", "High School"),
    (r"\b9\s*-\s*12\b", "High School"),
    # Novice
    (r"\bnovice\b", "Novice"),
    (r"\btots?\b", "Novice"),
    (r"\bbantam\b", "Novice"),
    (r"\bintermediate\b", "Novice"),
    (r"\bpee\s*wee\b", "Novice"),
    (r"\bk-?4\b", "Novice"),
    (r"\bbeginner\b", "Novice"),
    # Youth
    (r"\byouth\b", "Youth"),
    (r"\belementary\b", "Youth"),
    (r"\bmidget\b", "Youth"),
    (r"\bk-?6\b", "Youth"),
    (r"\bschoolboy\b", "Youth"),
    # Open
    (r"\bopen\b", "Open"),
    (r"\bsenior\b", "Open"),
    (r"\bcollege\b", "Open"),
    (r"\bcollegiate\b", "Open"),
    (r"\badult\b", "Open"),
    (r"\bk-?12\b", "Open"),
]

# Checked in order; the first hit wins.
EVENT_TYPE_TOKENS: list[tuple[str, str]] = [
    (r"\bclinic\b", "clinic"),
    (r"\bcamps?\b", "camp"),
    (r"\bduals?\b", "Duals"),
    (r"\bteam\s+tournament\b", "Duals"),
    (r"\btournament\b", "tournament"),
    (r"\bclassic\b", "tournament"),
    (r"\binvitational\b", "tournament"),
    (r"\bopen\b", "tournament"),
    (r"\bindividual\b", "tournament"),
]


def normalize_age_groups(text: str) -> tuple[list[str], list[str]]:
    """Return (age groups found, tokens that looked like divisions but did not map).

    Order follows AGE_GROUPS so the app's chips read consistently.
    """
    if not text:
        return [], []
    lowered = text.lower()
    found: set[str] = set()
    matched_spans: list[tuple[int, int]] = []

    for pattern, group in AGE_GROUP_TOKENS:
        for match in re.finditer(pattern, lowered):
            found.add(group)
            matched_spans.append(match.span())

    unknown: list[str] = []
    for candidate in re.findall(r"\b(?:k-\d+|\d+u|[a-z]{4,})\b", lowered):
        if candidate in {"school", "grade", "division", "divisions", "boys", "girls"}:
            continue
        if any(
            re.search(pattern, candidate) for pattern, _ in AGE_GROUP_TOKENS
        ):
            continue
        if re.fullmatch(r"k-\d+|\d+u", candidate) and candidate not in unknown:
            unknown.append(candidate)

    ordered = [group for group in AGE_GROUPS if group in found]
    return ordered, unknown


def normalize_event_type(*texts: str) -> str:
    """Classify an event from its name and format text; default to tournament."""
    blob = " ".join(t for t in texts if t).lower()
    for pattern, event_type in EVENT_TYPE_TOKENS:
        if re.search(pattern, blob):
            return event_type
    return "tournament"
