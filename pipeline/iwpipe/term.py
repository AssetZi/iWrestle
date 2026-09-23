"""Terminal colors for the CLIs, off when nobody is looking at a terminal.

Honors NO_COLOR (https://no-color.org) and turns itself off when stdout is
a pipe, so captured logs stay grep-able.
"""
from __future__ import annotations

import os
import sys


def _wanted() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


if _wanted():
    BOLD, DIM, GREEN, YELLOW, RED, CYAN, RESET = (
        "\033[1m", "\033[2m", "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m"
    )
else:
    BOLD = DIM = GREEN = YELLOW = RED = CYAN = RESET = ""
