"""The eval set itself must stay well formed; scoring is pure and tested here.
The live run is `make enrich-eval`."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import enrich_eval  # noqa: E402

from iwpipe.enrich import BannerExtraction, ContactOut  # noqa: E402


def test_every_case_has_its_files_and_verified_answers():
    found = enrich_eval.cases()
    assert len(found) >= 8
    for case in found:
        assert (case / "banner.jpg").exists(), case
        event = json.loads((case / "event.json").read_text())
        assert event["contact"]["email"].endswith("example.com"), "the baseline must not carry the answer"
        expected = json.loads((case / "expected.json").read_text())
        assert set(expected) <= {"email", "ageGroups", "flyerMatchesEvent", "registrationUrl"}


def test_scoring_counts_only_verified_fields():
    expected = {"email": "jane@club.org", "ageGroups": ["Youth"], "flyerMatchesEvent": True, "registrationUrl": "https://www.wrestlereg.com/x"}
    perfect = BannerExtraction(contact=ContactOut(email="Jane@Club.org"), divisions=["Youth 6-12"],
                               flyerMatchesEvent=True, registrationUrl="wrestlereg.com/other",
                               confidence="high", evidence="")
    assert enrich_eval.score(perfect, expected) == (4, 4, [])
    off = BannerExtraction(contact=ContactOut(email=None), divisions=["Open"], flyerMatchesEvent=False,
                           registrationUrl=None, confidence="low", evidence="")
    points, possible, wrong = enrich_eval.score(off, expected)
    assert (points, possible) == (0, 4) and len(wrong) == 4
    # Nothing expected, nothing scored.
    assert enrich_eval.score(off, {}) == (0, 0, [])
