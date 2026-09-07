from iwpipe import schema


def complete_event():
    event = schema.blank_event("pywrestling")
    event.update(
        name="Interstate Classic",
        eventType="tournament",
        date="2026-10-17T16:00:00Z",
        address="Venue, 1 Main St, Clarion, PA 16214",
        location={"latitude": 41.2, "longitude": -79.4},
        ageGroups=["Youth", "Jr High"],
        logo="/tmp/logo.png",
    )
    event["flyer"] = {"url": None, "path": "/tmp/flyer.pdf"}
    event["contact"] = {
        "firstName": "A", "lastName": "B", "email": "a@b.com", "phone": "1",
    }
    return event


def test_complete_event_validates():
    assert schema.validate(complete_event()) == []


def test_missing_assets_are_caught():
    """The app drops records without both assets, so the pipeline must too."""
    event = complete_event()
    event["logo"] = None
    event["flyer"]["path"] = None
    problems = schema.validate(event)
    assert "missing logo" in problems
    assert "missing flyer" in problems


def test_name_and_email_are_required():
    for field in ("firstName", "lastName", "email"):
        event = complete_event()
        event["contact"][field] = ""
        assert f"missing contact.{field}" in schema.validate(event)


def test_phone_is_optional():
    """The app hides an empty phone row; only email must be reachable."""
    event = complete_event()
    event["contact"]["phone"] = ""
    assert schema.validate(event) == []


def test_bad_vocabulary_is_rejected():
    event = complete_event()
    event["eventType"] = "Tournament"
    event["ageGroups"] = ["Middle School"]
    problems = schema.validate(event)
    assert any("eventType" in p for p in problems)
    assert any("ageGroup" in p for p in problems)


def test_source_key_is_stable():
    key = schema.source_key("pywrestling", "Interstate Classic", "2026-10-17T16:00:00Z")
    assert key == "pywrestling:interstate-classic:2026-10-17"


def test_only_approved_complete_events_are_pushable():
    event = complete_event()
    assert not schema.is_pushable(event)
    event["review"]["status"] = schema.STATUS_APPROVED
    assert schema.is_pushable(event)


def test_out_of_range_coordinates_do_not_validate():
    event = complete_event()
    event["location"] = {"latitude": -106.2, "longitude": 31.8}
    assert "coordinates out of range" in schema.validate(event)
