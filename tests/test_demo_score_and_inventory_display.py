from app_review_demo import run_search


def test_known_synthetic_post_has_expected_score_class_and_match():
    outcome = run_search(keyword="Butuh apartemen 2BR", mode="Synthetic", limit=10)
    item = next(item for item in outcome["results"] if item["post"]["id"] == "4001")
    lead = item["lead"]
    assert lead.lead_class == "hot_lead"
    assert lead.lead_score == 100
    assert lead.matched_inventory
    assert all("inventory_id" in match for match in lead.matched_inventory)
