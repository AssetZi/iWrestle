#!/usr/bin/env python3
"""Can each environment be reached with its server-to-server key?"""
import sys

import _bootstrap  # noqa: F401

from iwpipe import cktool, ckws


def main() -> int:
    worst = 0
    for environment in ("development", "production"):
        client = cktool.rest_client(environment)
        if client is None:
            print(f"{environment}: no key configured")
            continue
        try:
            client.ping()
            print(f"{environment}: OK")
        except ckws.CKWSError as error:
            reason = str(error).split("reason")[-1].strip(' :"}\n') if "reason" in str(error) else str(error)[:120]
            print(f"{environment}: FAILED ({reason})")
            worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
