from dashboard.components import badge, lead_row, score_bar
from dashboard.formatters import budget, legacy_label
from dashboard.theme import MATCH_TIER_COLORS


def test_badges_use_semantic_tones():
    assert "rdsa-teal" in badge("exact_match", MATCH_TIER_COLORS)
    assert "rdsa-amber" in badge("nearby_alternative", MATCH_TIER_COLORS)
    assert "rdsa-legacy" in badge("legacy_synthetic", MATCH_TIER_COLORS)


def test_score_bar_is_bounded():
    assert "width:100%" in score_bar(150)
    assert "width:0%" in score_bar("invalid")


def test_budget_formatter_handles_range_and_period():
    assert "IDR" in budget({"budget_min": 5_000_000, "budget_max": 7_000_000})


def test_legacy_label_is_explicitly_inactive():
    assert "not an active inventory recommendation" in legacy_label()


def test_lead_row_excludes_private_source_fields():
    row = lead_row({"post_id": "p1", "raw_text": "email@example.com", "lead_score": 90, "lead_class": "hot_lead", "desired_location": "BSD", "property_type": "apartment", "status": "new"})
    assert "raw_text" not in row and "email@example.com" not in repr(row)
