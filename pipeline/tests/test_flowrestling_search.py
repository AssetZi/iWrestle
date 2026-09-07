"""National enumeration over the search endpoint, with a stubbed session."""
import json
from datetime import datetime, timedelta, timezone

from iwpipe.collectors import flowrestling


def _item(i, days=10, name=None):
    start = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT16:00:00.000Z")
    return {"id": f"id{i}", "name": name or f"Event {i}", "startTime": start,
            "url": f"https://www.flowrestling.org/nextgen/events/{1000+i}/information",
            "location": {"venueName": "Gym", "city": "Erie", "region": "PA",
                         "coordinates": {"latitude": 42.1, "longitude": -80.0}}}


class Response:
    def __init__(self, payload, status=200):
        self._payload = payload; self.status_code = status
        self.headers = {"Content-Type": "application/json"}
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload


class Session:
    """Two queries; 'a' has 150 matches over two pages, 'e' overlaps."""
    def __init__(self):
        self.calls = []
    def post(self, url, headers=None, json=None, timeout=None):
        self.calls.append(json)
        q, off = json["query"], json.get("offset", 0)
        pool = {"a": [_item(i) for i in range(150)], "e": [_item(i) for i in range(100, 160)]}.get(q, [])
        page = pool[off: off + 100]
        return Response({"data": [{"date": "x", "events": page}], "meta": {"total": len(pool), "hasMore": off + 100 < len(pool)}})
    def get(self, url, headers=None, timeout=None):
        core = url.rsplit("/", 1)[-1]
        return Response({"data": {"eventContact": {"name": "Jane Coach", "email": f"c{core}@x.org"},
                                  "location": {"name": "Gym", "address": {"line1": "1 Main St", "city": "Erie", "state": "PA", "zipCode": "16501"}}}})


def test_enumeration_pages_by_offset_and_unions_by_id():
    session = Session()
    events = flowrestling.enumerate_all(session, queries=["a", "e"])
    assert len(events) == 160
    offsets = [(c["query"], c["offset"]) for c in session.calls]
    assert offsets == [("a", 0), ("a", 100), ("e", 0)]


def test_window_drops_past_and_far_future(monkeypatch):
    monkeypatch.setattr(flowrestling, "enumerate_all", lambda s, queries=None: [_item(1, days=-5), _item(2, days=30), _item(3, days=900)])
    monkeypatch.setattr(flowrestling, "_load_detail_cache", lambda: {})
    monkeypatch.setattr(flowrestling, "_save_detail_cache", lambda cache: None)
    events = flowrestling.collect(Session())
    assert [e["name"] for e in events] == ["Event 2"]
    assert events[0]["contact"]["email"] == "c1002@x.org"
    assert events[0]["sourceUrl"].endswith("/events/1002/information")


def test_detail_cache_is_reused_until_it_ages(monkeypatch):
    session = Session()
    cache = {}
    flowrestling.fetch_detail(session, "1002", cache)
    flowrestling.fetch_detail(session, "1002", cache)
    assert "1002" in cache and cache["1002"]["data"]["eventContact"]["email"] == "c1002@x.org"
    cache["1002"]["fetchedAt"] = "2020-01-01T00:00:00+00:00"
    flowrestling.fetch_detail(session, "1002", cache)
    assert cache["1002"]["fetchedAt"].startswith(str(datetime.now(timezone.utc).year))


def test_search_by_name_matches_on_words_and_day():
    session = Session()
    monkey_pool = [_item(1, days=10, name="Hurst Invitational")]
    session.post = lambda url, headers=None, json=None, timeout=None: Response({"data": [{"date": "x", "events": monkey_pool}], "meta": {"total": 1}})
    day = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
    assert flowrestling.search_by_name(session, "Hurst Invitational", day)["id"] == "id1"
    assert flowrestling.search_by_name(session, "Hurst Invitational", "2020-01-01") is None
    assert flowrestling.search_by_name(session, "Totally Different Event", day) is None


def test_swapped_coordinates_are_put_right_and_garbage_is_dropped():
    from iwpipe.collectors.flowrestling import _coordinates

    assert _coordinates({"latitude": -106.258236, "longitude": 31.793335}) == {
        "latitude": 31.793335, "longitude": -106.258236,
    }
    assert _coordinates({"latitude": 40.1, "longitude": -79.4}) == {"latitude": 40.1, "longitude": -79.4}
    assert _coordinates({"latitude": 500, "longitude": 500}) is None
    assert _coordinates(None) is None
