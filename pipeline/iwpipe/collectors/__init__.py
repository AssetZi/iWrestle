"""Registry of source collectors.

A collector's only job is pulling raw text out of a page. Normalization into
the app's exact vocabulary happens once, in bin/collect.py.
"""
from __future__ import annotations

from . import flowrestling, pywrestling, trackwrestling

COLLECTORS = {
    "flowrestling": flowrestling,
    "pywrestling": pywrestling,
    "trackwrestling": trackwrestling,
}
