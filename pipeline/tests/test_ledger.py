"""Cross-source duplicates: the same gym on the same weekend is the same event."""
from iwpipe import ledger


def _seed(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    ledger.record(
        "pywrestling:harold-winshel-memorial-round-robin:2026-09-12", "development",
        "REC1", "Harold Winshel Memorial Round Robin",
        day="2026-09-12", location={"latitude": 40.2394, "longitude": -74.9658},
    )


def test_same_venue_same_weekend_is_flagged(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    found = ledger.find_similar(
        "flowrestling:11th-annual-harold-winshel-memorial:2026-09-12",
        "11th-annual-harold-winshel-memorial", "2026-09-12",
        {"latitude": 40.2390, "longitude": -74.9672},
    )
    assert found == ["pywrestling:harold-winshel-memorial-round-robin:2026-09-12"]


def test_same_gym_a_month_later_is_a_different_event(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    assert ledger.find_similar(
        "flowrestling:x:2026-10-12", "x", "2026-10-12",
        {"latitude": 40.2390, "longitude": -74.9672},
    ) == []


def test_exact_slug_still_matches_without_a_location(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    assert ledger.find_similar(
        "flowrestling:harold-winshel-memorial-round-robin:2026-09-12",
        "harold-winshel-memorial-round-robin", "2026-09-12", None,
    )


def test_an_event_never_matches_itself(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    assert ledger.find_similar(
        "pywrestling:harold-winshel-memorial-round-robin:2026-09-12",
        "harold-winshel-memorial-round-robin", "2026-09-12",
        {"latitude": 40.2394, "longitude": -74.9658},
    ) == []


def test_sibling_events_from_the_same_source_are_not_duplicates(monkeypatch, tmp_path):
    """West Penn Open and West Penn Duals share a gym and a day on purpose."""
    _seed(monkeypatch, tmp_path)
    assert ledger.find_similar(
        "pywrestling:west-penn-duals:2026-09-12", "west-penn-duals", "2026-09-12",
        {"latitude": 40.2394, "longitude": -74.9658},
    ) == []


def test_a_city_level_geocode_a_few_km_off_is_flagged_not_skipped(monkeypatch, tmp_path):
    _seed(monkeypatch, tmp_path)
    near = {"latitude": 40.2394 + 0.03, "longitude": -74.9658}   # ~3.3 km north
    assert ledger.find_similar("trackwrestling:x:2026-09-12", "x", "2026-09-12", near) == []
    assert ledger.find_nearby("trackwrestling:x:2026-09-12", "2026-09-12", near) == [
        "pywrestling:harold-winshel-memorial-round-robin:2026-09-12"
    ]


# --- Listings that vanished, and dates that moved -----------------------------

def _seed_upcoming(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    ledger.record("pywrestling:a:2026-09-12", "development", "RA", "A", day="2026-09-12")
    ledger.record("pywrestling:b:2026-10-03", "development", "RB", "B", day="2026-10-03")
    ledger.record("pywrestling:old:2026-08-01", "development", "RO", "Old", day="2026-08-01")
    ledger.record("flowrestling:c:2026-10-03", "development", "RC", "C", day="2026-10-03")


def test_a_listing_absent_from_its_source_is_counted_per_run(monkeypatch, tmp_path):
    _seed_upcoming(monkeypatch, tmp_path)
    missing = ledger.mark_misses("pywrestling", {"pywrestling:a:2026-09-12"}, "2026-09-07")
    assert [m["sourceKey"] for m in missing] == ["pywrestling:b:2026-10-03"]
    assert ledger.get("pywrestling:b:2026-10-03", "development")["missCount"] == 1
    # A past event and another source's event are nobody's business here.
    assert "missCount" not in ledger.get("pywrestling:old:2026-08-01", "development")
    assert "missCount" not in ledger.get("flowrestling:c:2026-10-03", "development")
    assert ledger.due_for_removal("pywrestling", "development") == []

    ledger.mark_misses("pywrestling", {"pywrestling:a:2026-09-12"}, "2026-09-14")
    due = ledger.due_for_removal("pywrestling", "development")
    assert [d["sourceKey"] for d in due] == ["pywrestling:b:2026-10-03"]
    assert ledger.due_for_removal("pywrestling", "production") == []


def test_a_listing_that_comes_back_is_forgiven(monkeypatch, tmp_path):
    _seed_upcoming(monkeypatch, tmp_path)
    ledger.mark_misses("pywrestling", set(), "2026-09-07")
    ledger.mark_misses("pywrestling", {"pywrestling:a:2026-09-12", "pywrestling:b:2026-10-03"}, "2026-09-14")
    assert "missCount" not in ledger.get("pywrestling:b:2026-10-03", "development")


def test_an_entry_on_its_way_out_no_longer_blocks_another_source(monkeypatch, tmp_path):
    _seed_upcoming(monkeypatch, tmp_path)
    key = "flowrestling:b:2026-10-03"
    assert ledger.find_similar(key, "b", "2026-10-03", None) == ["pywrestling:b:2026-10-03"]
    ledger.mark_misses("pywrestling", set(), "2026-09-07")
    ledger.mark_misses("pywrestling", set(), "2026-09-14")
    assert ledger.find_similar(key, "b", "2026-10-03", None) == []


def test_a_date_change_is_the_same_event_moved(monkeypatch, tmp_path):
    _seed_upcoming(monkeypatch, tmp_path)
    seen = {"pywrestling:a:2026-09-12", "pywrestling:b:2026-10-10"}
    assert ledger.find_moved("pywrestling", "b", "2026-10-10", seen, "2026-09-07") == ["pywrestling:b:2026-10-03"]
    # Still listed on the old day too: two events, not a move.
    assert ledger.find_moved("pywrestling", "b", "2026-10-10", seen | {"pywrestling:b:2026-10-03"}, "2026-09-07") == []
    # Last season's edition is over; next year's is a new event.
    assert ledger.find_moved("pywrestling", "old", "2027-08-07", seen, "2026-09-07") == []
    # Another source's copy is a duplicate, handled elsewhere.
    assert ledger.find_moved("pywrestling", "c", "2026-10-10", seen, "2026-09-07") == []


# --- The file itself -------------------------------------------------------------

def test_a_corrupt_ledger_is_an_error_not_an_empty_ledger(monkeypatch, tmp_path):
    """Reading {} from a truncated file would re-create every event as a twin."""
    import pytest

    path = tmp_path / "pushed.json"
    monkeypatch.setattr(ledger, "LEDGER_PATH", path)
    path.write_text('{"development:x": {"recordName": "R"')
    with pytest.raises(ledger.LedgerError):
        ledger.load()
    path.write_text("")
    with pytest.raises(ledger.LedgerError):
        ledger.load()


def test_save_replaces_the_file_whole(monkeypatch, tmp_path):
    path = tmp_path / "pushed.json"
    monkeypatch.setattr(ledger, "LEDGER_PATH", path)
    ledger.record("pywrestling:a:2026-09-12", "development", "RA", "A", day="2026-09-12")
    assert not path.with_suffix(".json.tmp").exists()
    assert ledger.get("pywrestling:a:2026-09-12", "development")["recordName"] == "RA"


def test_a_second_writer_is_refused_while_the_ledger_is_held(monkeypatch, tmp_path):
    import pytest

    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    with ledger.lock():
        with pytest.raises(ledger.LedgerLocked):
            with ledger.lock():
                pass
    # Released on exit.
    with ledger.lock():
        pass


# --- Guards against taking real events down ----------------------------------------

def test_a_scrape_far_below_the_ledger_looks_partial(monkeypatch, tmp_path):
    _seed_upcoming(monkeypatch, tmp_path)   # pywrestling has 2 upcoming entries
    assert ledger.looks_partial("pywrestling", 2, "2026-09-07") == (False, 2)
    assert ledger.looks_partial("pywrestling", 1, "2026-09-07") == (True, 2)
    ledger.record("pywrestling:c:2026-10-03", "development", "RC2", "C", day="2026-10-03")
    ledger.record("pywrestling:d:2026-10-03", "development", "RD", "D", day="2026-10-03")
    ledger.record("pywrestling:e:2026-10-03", "development", "RE", "E", day="2026-10-03")
    assert ledger.looks_partial("pywrestling", 2, "2026-09-07") == (True, 5)
    # A source that has never been pushed cannot be partial.
    assert ledger.looks_partial("trackwrestling", 0, "2026-09-07") == (False, 0)


def test_a_reclassification_has_to_hold_for_two_runs(monkeypatch, tmp_path):
    _seed_upcoming(monkeypatch, tmp_path)
    key = "pywrestling:a:2026-09-12"
    assert ledger.mark_retiring(key, "development", "college-level event") == 1
    assert ledger.mark_retiring(key, "development", "college-level event") == 2
    ledger.clear_retiring({key}, "development")
    assert "retireCount" not in ledger.get(key, "development")
    # An exclusion is a person's decision: it counts at once.
    assert ledger.mark_retiring(key, "development", "excluded: college open") >= ledger.RETIRE_LIMIT
    assert ledger.mark_retiring("pywrestling:nope:2026-01-01", "development", "college-level event") == 0


# --- Suffixed keys ------------------------------------------------------------------

def test_a_disambiguated_twin_still_matches_by_name_and_day(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger, "LEDGER_PATH", tmp_path / "pushed.json")
    ledger.record("flowrestling:x-y:2026-11-18:2gPX", "production", "R2", "X Y", day="2026-11-18")
    assert ledger.find_similar("trackwrestling:x-y:2026-11-18", "x-y", "2026-11-18", None) == [
        "flowrestling:x-y:2026-11-18:2gPX"
    ]
    assert ledger.find_moved("flowrestling", "x-y", "2026-11-25", set(), "2026-09-07") == [
        "flowrestling:x-y:2026-11-18:2gPX"
    ]
