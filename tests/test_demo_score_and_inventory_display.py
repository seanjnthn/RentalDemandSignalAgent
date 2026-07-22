from app_review_demo import run_search
from datetime import datetime, timezone


def test_known_synthetic_post_has_expected_score_class_and_match():
    # Freeze time to ensure post freshness remains within scoring windows.
    reference_now = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
    outcome = run_search(keyword="Butuh apartemen 2BR", mode="Synthetic", limit=10, now=reference_now)
    item = next(item for item in outcome["results"] if item["post"]["id"] == "4001")
    lead = item["lead"]
    assert lead.lead_class == "hot_lead"
    assert lead.lead_score == 100
    assert lead.matched_inventory
    assert all("inventory_id" in match for match in lead.matched_inventory)
