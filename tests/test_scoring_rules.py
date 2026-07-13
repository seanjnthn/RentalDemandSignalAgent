from datetime import datetime, timezone

from rdsa.classifier import classify
from rdsa.extractor import extract
from rdsa.scorer import score

NOW = datetime(2026, 7, 13, 7, tzinfo=timezone.utc)


def _score(text):
    lead = extract({"id": "x", "text": text, "timestamp": "2026-07-13T06:00:00+00:00"}, NOW)
    return score(lead, NOW)


def test_relative_budget_is_seven_and_numeric_budget_is_fifteen():
    assert next(x["points"] for x in _score("Looking for apartment in BSD, budget under 10 million/month").score_breakdown if x["rule"] == "R3") == 7
    assert next(x["points"] for x in _score("Looking for apartment in BSD, budget 8jt/bulan").score_breakdown if x["rule"] == "R3") == 15


def test_score_bands_follow_spec_thresholds():
    for value, expected in ((75, "hot_lead"), (55, "qualified_lead"), (35, "watch"), (34, "irrelevant")):
        lead = _score("Looking for apartment in BSD")
        lead.lead_score = value
        assert classify(lead).lead_class == expected


def test_high_scoring_seeker_without_move_in_or_duration_is_hot():
    lead = _score("Looking for apartment in BSD, budget 8jt/bulan, 2BR")
    lead.move_in_date = lead.rental_duration = None
    lead.lead_score = 75
    assert classify(lead).lead_class == "hot_lead"
