"""keycheck answers in bounded time, whatever the network does."""
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import keycheck  # noqa: E402

from iwpipe import ckws  # noqa: E402


class _Client:
    def __init__(self, behaviour):
        self.behaviour = behaviour

    def ping(self):
        if self.behaviour == "hang":
            time.sleep(5)
        elif self.behaviour == "reset":
            raise requests.ConnectionError("Connection reset by peer")
        elif self.behaviour == "rejected":
            raise ckws.CKWSError('records/query failed (401): {"reason": "AUTHENTICATION_FAILED"}')
        return 1


def test_an_accepted_key_is_ok():
    assert keycheck.ping_with_deadline(_Client("ok"), 1) is None


def test_a_hanging_ping_fails_at_the_deadline():
    started = time.monotonic()
    assert keycheck.ping_with_deadline(_Client("hang"), 0.2) == "no answer in 0.2s"
    assert time.monotonic() - started < 2


def test_a_network_error_is_a_failure_not_a_traceback():
    assert keycheck.ping_with_deadline(_Client("reset"), 1).startswith("network: ")


def test_a_rejected_key_names_the_reason():
    assert keycheck.ping_with_deadline(_Client("rejected"), 1) == "AUTHENTICATION_FAILED"
