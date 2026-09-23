from datetime import date

import pytest

from iwpipe.dates import parse_date, parse_time, to_utc_iso

TODAY = date(2026, 9, 4)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Saturday September 5, 2026", date(2026, 9, 5)),
        ("Saturday-Sunday October 17-18, 2026", date(2026, 10, 17)),
        ("Sunday March 7, 2027", date(2027, 3, 7)),
        ("10/17/2026", date(2026, 10, 17)),
        ("Sat, Oct 17", date(2026, 10, 17)),
        ("2026-12-05", date(2026, 12, 5)),
        ("no date here", None),
    ],
)
def test_parse_date(text, expected):
    assert parse_date(text, today=TODAY) == expected


def test_year_is_inferred_forward():
    """A January listing seen in September belongs to next year."""
    assert parse_date("January 3", today=TODAY) == date(2027, 1, 3)


@pytest.mark.parametrize(
    "text,expected",
    [("9:00 AM", (9, 0)), ("10 am", (10, 0)), ("7:30 pm", (19, 30)), ("noon", None)],
)
def test_parse_time(text, expected):
    assert parse_time(text) == expected


def test_default_time_is_noon_eastern():
    """Noon ET keeps the event on its own calendar day in every US zone."""
    assert to_utc_iso("October 17, 2026", today=TODAY) == "2026-10-17T16:00:00Z"


def test_stated_time_wins():
    assert to_utc_iso("March 7, 2027 at 9:00 AM", today=TODAY) == "2027-03-07T14:00:00Z"


def test_utc_source_passes_through():
    assert to_utc_iso("2026-12-05T19:30:00Z") == "2026-12-05T19:30:00Z"
