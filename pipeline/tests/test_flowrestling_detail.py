"""The event-hub record is where Flo keeps the organizer contact."""
import json
from pathlib import Path

from iwpipe.collectors import flowrestling
from iwpipe.schema import blank_event

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "flowrestling-event-hub.json"


def test_contact_address_and_site_come_from_the_detail():
    detail = json.loads(FIXTURE.read_text())["data"]
    event = blank_event("flowrestling")
    flowrestling.apply_detail(event, detail)
    assert event["contact"]["email"] == "btcwrestlingusa@gmail.com"
    assert event["contact"]["lastName"] == "(Organizer)"
    assert event["address"] == "Monroeville Convention Center, 209 Mall Plaza Boulevard, Monroeville, PA 15146"
    assert event["organizerWebsite"] == "https://breakthechainswrestling.com"


def test_a_person_name_is_split():
    event = blank_event("flowrestling")
    flowrestling.apply_detail(event, {"eventContact": {"name": "Jane Coach", "email": "j@c.org"}})
    assert (event["contact"]["firstName"], event["contact"]["lastName"]) == ("Jane", "Coach")


def test_scraped_values_win_over_the_detail():
    event = blank_event("flowrestling")
    event["contact"]["email"] = "scraped@x.org"
    flowrestling.apply_detail(event, {"eventContact": {"name": "X", "email": "detail@x.org"}})
    assert event["contact"]["email"] == "scraped@x.org"


def test_detail_url_is_beside_schedule_not_under_it():
    assert flowrestling.detail_url("14479196") == "https://prod-web-api.flowrestling.org/api/event-hub/14479196"


def test_role_names_stay_in_organizer_form():
    event = blank_event("flowrestling")
    flowrestling.apply_detail(event, {"eventContact": {"name": "Tournament Director", "email": "t@d.org"}})
    assert event["contact"]["lastName"] == "(Organizer)"


def test_detail_supplies_coordinates_and_state_when_the_listing_lacks_them():
    detail = json.loads(FIXTURE.read_text())["data"]
    event = blank_event("flowrestling")
    flowrestling.apply_detail(event, detail)
    assert event["location"] == {"latitude": 40.4326759, "longitude": -79.7911664}
    assert event["region"] == "PA"
