"""Telling a dead connection from one failed request.

A request that fails is an answer about that request. Three in a row that
never reached a server are an answer about the network, and a run that
keeps going only fills the log with the same line.
"""
from __future__ import annotations

import re

import requests

# Consecutive requests that never connected before a run gives up.
GIVE_UP_AFTER = 3


def is_network_error(error: BaseException) -> bool:
    """The request never got an answer (DNS, refused, timed out).

    Looks through `raise ... from`: the CloudKit client reports a failed
    create as its own error with the transport error as the cause.
    """
    seen = 0
    while error is not None and seen < 5:
        if isinstance(error, (requests.ConnectionError, requests.Timeout)):
            return True
        error, seen = error.__cause__, seen + 1
    return False


def brief(error: BaseException) -> str:
    """One short phrase out of a urllib3 error chain."""
    text = str(error)
    host = re.search(r"host='([^']+)'", text)
    if "Failed to resolve" in text or "NameResolutionError" in text:
        why = "DNS lookup failed"
    elif "timed out" in text.lower() or isinstance(error, requests.Timeout):
        why = "timed out"
    else:
        why = "connection failed"
    return f"{why} for {host.group(1)}" if host else why
