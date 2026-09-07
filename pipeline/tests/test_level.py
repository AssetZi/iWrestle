from iwpipe.level import classify_level


def test_college_open_at_a_university():
    assert classify_level("Hurst Invitational", "Mercyhurst University") == "college"
    assert classify_level("Clarion Open", "Clarion University") == "college"
    assert classify_level("NCAA Regional Duals", "") == "college"


def test_youth_events_at_a_university_stay():
    assert classify_level("Falcon Frenzy Takedown Tournament", "Messiah University") is None
    assert classify_level("Harold Winshel Memorial Round Robin", "Bucks County Community College",
                          "BANTAM 8 and under, HIGH SCHOOL 18 and under") is None


def test_high_school_gym_is_not_college():
    assert classify_level("Trinity Belt Brawl", "Trinity High School") is None
    assert classify_level("Lebanon Wrestling Tournament", "Lebanon High School") is None


def test_adult_opens_are_not_youth():
    assert classify_level("2026 Griffin Open Mens", "Lamar Dixon Expo Center") == "adult"
    assert classify_level("Yukon Boys Open", "Yukon High School") is None


def test_placeholders():
    from iwpipe.level import is_placeholder

    assert is_placeholder("CANCELLED 2026 MWP Vision Quest")
    assert is_placeholder("NO")
    assert not is_placeholder("IHSA 1A Regional 4")
    assert not is_placeholder("Northwest Bigfoot Battle")
    assert not is_placeholder("Takedown in the Den")


def test_tba_venue_is_a_note_not_a_skip():
    from iwpipe.level import venue_is_tba

    assert venue_is_tba("TBA, TBA, TBA, IL TBA")
    assert not venue_is_tba("Elizabethtown Area High School, 600 East High Street, Elizabethtown, PA 17022")


def test_invite_counts_like_invitational():
    assert classify_level("Millikin Invite", "Millikin University") == "college"
