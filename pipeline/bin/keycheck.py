#!/usr/bin/env python3
"""Can each environment be reached with its server-to-server key?

A check that hangs is as bad as one that fails: the routine waits on it.
So each ping gets a deadline, and a connection that never answers, or
answers with a network error rather than a CloudKit one, is a FAILED
line, not a traceback and not a wait.
"""
import sys
import threading

import _bootstrap  # noqa: F401

import requests

from iwpipe import cktool, ckws

PING_DEADLINE_SECONDS = 30


def ping_with_deadline(client, deadline: float) -> str | None:
    """None when the key is accepted, else why not."""
    outcome: dict[str, str | None] = {}

    def run() -> None:
        try:
            client.ping()
            outcome["error"] = None
        except ckws.CKWSError as error:
            text = str(error)
            outcome["error"] = text.split("reason")[-1].strip(' :"}\n') if "reason" in text else text[:120]
        except requests.RequestException as error:
            outcome["error"] = f"network: {str(error)[:120]}"

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(deadline)
    if worker.is_alive():
        return f"no answer in {deadline:g}s"
    return outcome.get("error")


def main() -> int:
    worst = 0
    for environment in ("development", "production"):
        client = cktool.rest_client(environment)
        if client is None:
            print(f"{environment}: no key configured")
            continue
        reason = ping_with_deadline(client, PING_DEADLINE_SECONDS)
        if reason is None:
            print(f"{environment}: OK")
        else:
            print(f"{environment}: FAILED ({reason})")
            worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
