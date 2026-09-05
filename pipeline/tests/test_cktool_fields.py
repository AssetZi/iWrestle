"""The fields file must mirror createEvent in CloudKitEventCRUD.swift."""
from iwpipe import cktool
from iwpipe.config import ADMIN_RECORD_NAME

EVENT = {
    "name": "Interstate Classic",
    "eventType": "Duals",
    "date": "2026-10-17T16:00:00Z",
    "location": {"latitude": 41.2, "longitude": -79.4},
    "address": "Venue, 1 Main St, Clarion, PA 16214",
    "ageGroups": ["Youth", "Jr High"],
    "registration": "",
    "contact": {
        "firstName": "A", "lastName": "B", "email": "a@b.com", "phone": "1",
    },
}

# Event.Field in iWrestle/Models/Event.swift, minus the unused `photo` key.
REQUIRED_KEYS = {
    "userID", "eventType", "name", "date", "location", "address", "ageGroups",
    "logo", "flyer", "eventContactFirstName", "eventContactLastName",
    "eventContactEmail", "eventContactPhone",
}


def test_every_required_field_is_written():
    assert REQUIRED_KEYS <= set(cktool.build_fields(EVENT))


def test_empty_registration_is_omitted():
    """createEvent only sets registration when it is non-empty."""
    assert "registration" not in cktool.build_fields(EVENT)
    with_registration = dict(EVENT, registration="https://x.co")
    assert cktool.build_fields(with_registration)["registration"]["value"] == "https://x.co"


def test_ownership_points_at_the_admin_record():
    """Without this the event never appears under Settings -> My events."""
    value = cktool.build_fields(EVENT)["userID"]["value"]
    assert ADMIN_RECORD_NAME in str(value)


def test_assets_reference_the_upload_keys():
    fields = cktool.build_fields(EVENT)
    assert fields["logo"] == {"type": "assetType", "value": "LOGO"}
    assert fields["flyer"] == {"type": "assetType", "value": "FLYER"}


def test_age_groups_use_the_list_type():
    fields = cktool.build_fields(EVENT)
    assert fields["ageGroups"]["type"] == "stringListType"
    assert fields["ageGroups"]["value"] == ["Youth", "Jr High"]




def test_location_and_reference_use_the_confirmed_shapes():
    """Both were verified against the development database on the first push."""
    fields = cktool.build_fields(EVENT)
    assert fields["location"]["value"] == {"latitude": 41.2, "longitude": -79.4}
    assert fields["userID"]["value"]["action"] == "NONE"
