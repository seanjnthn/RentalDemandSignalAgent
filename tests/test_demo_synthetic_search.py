from app_review_demo import run_search


def test_synthetic_search_processes_results_without_network():
    outcome = run_search(mode="Synthetic", limit=10)
    assert outcome["status"] == "ok"
    assert outcome["results"]
    assert all(item["lead"].lead_class and item["lead"].lead_score >= 0 and item["lead"].score_breakdown is not None for item in outcome["results"])

