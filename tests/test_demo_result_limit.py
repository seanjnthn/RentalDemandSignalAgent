from app_review_demo import MAX_RESULTS, run_search


def test_result_limit_is_capped_and_respected():
    assert len(run_search(mode="Synthetic", limit=3)["results"]) <= 3
    assert len(run_search(mode="Synthetic", limit=99)["results"]) <= MAX_RESULTS

