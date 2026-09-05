"""Merge rules are the safety of the AI step: scraped values always win."""
from iwpipe import enrich
from iwpipe.enrich import BannerExtraction, ContactOut, LogoBBox

DEFAULT = "support@example.com"


def base_event(**overrides):
    event = {
        "sourceKey": "pywrestling:x:2026-10-17",
        "name": "Interstate Classic",
        "date": "2026-10-17T16:00:00Z",
        "address": "Venue, 1 Main St, Clarion, PA 16214",
        "organizer": "Clarion Wrestling Club",
        "ageGroups": ["Youth", "Jr High", "High School"],
        "registration": "",
        "contact": {"firstName": "Clarion Wrestling Club", "lastName": "(Organizer)",
                    "email": DEFAULT, "phone": ""},
        "review": {"status": "pending", "notes": [
            "organizer used as contact name",
            "placeholder contact email: set a real DEFAULT_CONTACT_EMAIL in .env",
            "no divisions found, defaulted",
        ]},
    }
    event.update(overrides)
    return event


def extraction(**overrides):
    fields = dict(
        contact=ContactOut(name="Jane Coach", email="jane@club.org", phone="(814) 555-0100"),
        organizerWebsite="clarionwrestling.com",
        divisions=["Tots", "Bantam", "Jr High", "Girls K-12"],
        startTime="9:00 AM",
        weighInTime="7:30 AM",
        entryFee="$25",
        registrationUrl="https://form.jotform.com/1",
        logoBBox=LogoBBox(x=0.1, y=0.1, w=0.3, h=0.6),
        confidence="high",
        evidence="All text legible.",
    )
    fields.update(overrides)
    return BannerExtraction(**fields)


def test_fills_defaulted_and_empty_fields_with_notes(monkeypatch):
    monkeypatch.setattr(enrich, "DEFAULT_CONTACT_EMAIL", DEFAULT)
    event = base_event()
    filled = enrich.merge(event, extraction())
    contact = event["contact"]
    assert contact["email"] == "jane@club.org"
    assert contact["phone"] == "814-555-0100"
    assert (contact["firstName"], contact["lastName"]) == ("Jane", "Coach")
    assert event["registration"] == "https://form.jotform.com/1"
    assert event["organizerWebsite"] == "https://clarionwrestling.com"
    assert event["details"] == {"startTime": "9:00 AM", "weighInTime": "7:30 AM", "entryFee": "$25"}
    assert event["logoBBox"]["w"] == 0.3
    notes = event["review"]["notes"]
    for field in ("email", "phone", "contact name", "registration", "organizer website"):
        assert any(n.startswith(f"AI: {field}") for n in notes), field
    assert "placeholder contact email: set a real DEFAULT_CONTACT_EMAIL in .env" not in notes
    assert set(filled) >= {"email", "phone", "contactName", "registration"}


def test_scraped_values_are_never_overwritten(monkeypatch):
    monkeypatch.setattr(enrich, "DEFAULT_CONTACT_EMAIL", DEFAULT)
    event = base_event(registration="https://trackwrestling.com/reg")
    event["contact"] = {"firstName": "Bob", "lastName": "Real", "email": "bob@real.org", "phone": "111-222-3333"}
    event["review"]["notes"] = []
    enrich.merge(event, extraction())
    assert event["contact"]["email"] == "bob@real.org"
    assert event["contact"]["phone"] == "111-222-3333"
    assert event["contact"]["firstName"] == "Bob"
    assert event["registration"] == "https://trackwrestling.com/reg"


def test_divisions_replace_only_a_defaulted_set():
    defaulted = base_event()
    enrich.merge(defaulted, extraction())
    assert defaulted["ageGroups"] == ["Novice", "Jr High", "Open"]
    assert "no divisions found, defaulted" not in defaulted["review"]["notes"]

    from_icons = base_event()
    from_icons["review"]["notes"].remove("no divisions found, defaulted")
    enrich.merge(from_icons, extraction())
    assert from_icons["ageGroups"] == ["Youth", "Jr High", "High School"]
    assert any(n.startswith("AI: banner lists") for n in from_icons["review"]["notes"])


def test_nulls_change_nothing_but_still_record_the_pass():
    event = base_event()
    before = {k: v for k, v in event.items() if k != "review"}
    empty = extraction(
        contact=ContactOut(), organizerWebsite=None, divisions=[], startTime=None,
        weighInTime=None, entryFee=None, registrationUrl=None, logoBBox=None,
        confidence="low", evidence="Banner is a blurry photo.",
    )
    filled = enrich.merge(event, empty)
    assert filled == []
    after = {k: v for k, v in event.items() if k not in ("review", "details")}
    assert after == before
    assert "AI: low confidence, verify" in event["review"]["notes"]


def test_bad_phone_numbers_are_dropped():
    event = base_event()
    enrich.merge(event, extraction(contact=ContactOut(phone="call the club")))
    assert event["contact"]["phone"] == ""


def test_cache_key_changes_with_prompt_version(monkeypatch):
    event = base_event()
    first = enrich.cache_key(event, "abc")
    monkeypatch.setattr(enrich, "PROMPT_VERSION", enrich.PROMPT_VERSION + 1)
    assert enrich.cache_key(event, "abc") != first


def test_message_carries_image_first_then_context():
    event = base_event(detailText="See you there.")
    messages = enrich.build_messages(event, b"\xff\xd8fake")
    content = messages[0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"]["media_type"] == "image/jpeg"
    assert "Interstate Classic" in content[1]["text"]
    assert "See you there." in content[1]["text"]
    assert '"contactEmailIsDefault": true' in content[1]["text"]


def test_usage_totals_price_cached_tokens_cheaply():
    class Usage:
        input_tokens = 1000
        cache_read_input_tokens = 10000
        output_tokens = 200

    totals = enrich.usage_totals([Usage()])
    assert totals["input"] == 1000 and totals["cached"] == 10000
    assert totals["dollars"] == round((1000 + 1000) / 1e6 * 5 + 200 / 1e6 * 25, 4)
