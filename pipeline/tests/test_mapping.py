import pytest

from iwpipe.mapping import normalize_age_groups, normalize_event_type
from iwpipe.schema import AGE_GROUPS, EVENT_TYPES


@pytest.mark.parametrize(
    "text,expected",
    [
        ("K-4, K-6, K-8, High School & Girls K-12 Divisions",
         ["Novice", "Youth", "Jr High", "High School", "Open"]),
        ("Youth, Jr High, Varsity", ["Youth", "Jr High", "High School"]),
        ("Novice and Bantam only", ["Novice"]),
        ("Open College Division", ["Open"]),
        ("", []),
    ],
)
def test_age_groups(text, expected):
    groups, _ = normalize_age_groups(text)
    assert groups == expected


def test_age_groups_use_app_vocabulary():
    groups, _ = normalize_age_groups("middle school, varsity, pee wee")
    assert set(groups) <= set(AGE_GROUPS)


def test_order_follows_the_apps_chip_order():
    groups, _ = normalize_age_groups("high school, novice, jr high")
    assert groups == ["Novice", "Jr High", "High School"]


@pytest.mark.parametrize(
    "texts,expected",
    [
        (("Battle in the Burg", "Team Duals Tournament"), "Duals"),
        (("Summer Technique Camp",), "camp"),
        (("Takedown Clinic with Cael",), "clinic"),
        (("Harold Winshel Memorial",), "tournament"),
        (("Warriors Individual Tournament",), "tournament"),
    ],
)
def test_event_type(texts, expected):
    assert normalize_event_type(*texts) == expected
    assert normalize_event_type(*texts) in EVENT_TYPES
