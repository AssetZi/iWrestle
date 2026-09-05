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
