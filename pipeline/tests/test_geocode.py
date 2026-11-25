import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import summary as summary_cli  # noqa: E402

from iwpipe import geocode  # noqa: E402
from iwpipe.http import make_session  # noqa: E402

HIT = [{"lat": "41.2148", "lon": "-79.3853", "type": "building", "display_name": "Tippin Gym"}]


class FakeResponse:
    def __init__(self, payload=None, text=""):
        self._payload, self.text = payload, text

    def json(self):
        if self._payload is None:
            raise requests.exceptions.JSONDecodeError("Expecting value", self.text, 1)
        return self._payload


@pytest.fixture
def calls(monkeypatch, tmp_path):
    """Route geocode's requests to a queue of canned answers; record each call."""
    monkeypatch.setattr(geocode, "GEOCACHE_PATH", tmp_path / "geocache.json")
    monkeypatch.setattr(geocode, "_unavailable", False, raising=False)

    class Calls(list):
        """Each request's keyword arguments; `answers` is what comes back, in order."""

    made = Calls()
    answers = []

    def fake_get(session, url, **kwargs):
        made.append(kwargs)
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(geocode, "get", fake_get)
    made.answers = answers
    return made


def test_the_geocoder_is_asked_under_the_pipelines_own_name(calls):
    """Nominatim's usage policy refuses clients that pose as a browser."""
    calls.answers.append(FakeResponse(HIT))
    assert geocode.lookup(None, "Tippin Gym, Clarion, PA")["latitude"] == 41.2148
    headers = calls[0]["headers"]
    assert "Mozilla" not in headers["User-Agent"]
    assert headers["User-Agent"].startswith("iWrestle-events-pipeline/")
    assert headers["Accept"] == "application/json"


def test_the_browser_headers_do_not_ride_along_on_the_wire():
    """What the shared session actually sends once geocode's headers are merged in."""
    session = make_session()
    sent = session.prepare_request(
        requests.Request("GET", geocode.ENDPOINT, headers=geocode.HEADERS)
    ).headers
    assert sent["User-Agent"].startswith("iWrestle-events-pipeline/")
    assert sent["Accept"] == "application/json"
    assert "Upgrade-Insecure-Requests" not in sent


def test_a_reply_that_is_not_json_leaves_the_event_unlocated(calls, capsys):
    """The 2026-11-23 run: a block page came back and collect died on it."""
    calls.answers.append(FakeResponse(None, text="\n<html>Access blocked</html>"))
    assert geocode.lookup(None, "Tippin Gym, Clarion, PA") is None
    assert "geocoder unavailable" in capsys.readouterr().out


@pytest.mark.parametrize("reply", [
    {"error": "Access blocked"},          # an error object instead of results
    [{"display_name": "no coordinates"}],  # a result without lat/lon
    ["not a result"],
])
def test_a_reply_that_is_not_results_leaves_the_event_unlocated(calls, reply):
    calls.answers.append(FakeResponse(reply))
    assert geocode.lookup(None, "Tippin Gym, Clarion, PA") is None
    assert geocode._load_cache() == {}


def test_retries_running_out_leaves_the_event_unlocated(calls):
    calls.answers.append(RuntimeError("GET https://nominatim.example failed after retries: None"))
    assert geocode.lookup(None, "Tippin Gym, Clarion, PA") is None
    assert geocode._load_cache() == {}


@pytest.mark.parametrize("answer", [
    FakeResponse(None, text="\n<html>Access blocked</html>"),
    FakeResponse({"error": "Access blocked"}),
    requests.HTTPError("403 Client Error: Forbidden"),
])
def test_the_routine_summary_reports_the_outage(calls, capsys, answer):
    """Collect no longer stops, so this line is the only sign of a blocked geocoder."""
    calls.answers.append(answer)
    geocode.lookup(None, "Tippin Gym, Clarion, PA")
    line = capsys.readouterr().out.strip()
    _, trouble = summary_cli.summarize("== pywrestling\n" + line + "\n")
    assert trouble == [f"pywrestling: {line}"] or trouble == [line], trouble


def test_a_refusal_is_not_cached_as_a_miss(calls):
    """A cached None would hide the event on every later run too."""
    calls.answers.append(requests.HTTPError("403 Client Error: Forbidden"))
    assert geocode.lookup(None, "Tippin Gym, Clarion, PA") is None
    assert geocode._load_cache() == {}


def test_after_a_refusal_the_run_stops_asking_but_still_reads_the_cache(calls, capsys):
    calls.answers.append(FakeResponse(HIT))
    geocode.lookup(None, "Tippin Gym, Clarion, PA")
    calls.answers.append(requests.HTTPError("403 Client Error: Forbidden"))
    assert geocode.lookup(None, "1 Elsewhere Rd, Erie, PA") is None
    assert geocode.lookup(None, "2 Elsewhere Rd, Erie, PA") is None
    assert len(calls) == 2   # the third address never went out
    assert geocode.lookup(None, "Tippin Gym, Clarion, PA")["longitude"] == -79.3853
    assert capsys.readouterr().out.count("geocoder unavailable") == 1


def test_an_address_nominatim_does_not_know_is_still_cached_as_a_miss(calls):
    calls.answers.extend([FakeResponse([]), FakeResponse([])])
    assert geocode.lookup(None, "Nowhere Gym, Clarion") is None
    assert geocode._load_cache() == {"nowhere gym, clarion": None}
