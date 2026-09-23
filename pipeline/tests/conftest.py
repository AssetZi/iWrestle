import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def _no_network_pauses(monkeypatch):
    """The Flo collector pauses between live detail requests; tests never make any."""
    from iwpipe.collectors import flowrestling

    monkeypatch.setattr(flowrestling, "DETAIL_PAUSE_SECONDS", 0)
