from app_review_demo import run_search


def test_live_disabled_makes_no_client_call(monkeypatch):
    monkeypatch.setenv("THREADS_LIVE_ENABLED", "false")
    class NoCall:
        def search(self, *args, **kwargs):
            raise AssertionError("Threads API must not be called")
    monkeypatch.setattr("app_review_demo.ThreadsClient", lambda *a, **k: NoCall())
    outcome = run_search(mode="Live", limit=10, token="not-used")
    assert outcome["status"] == "disabled"
    assert "Live mode disabled" in outcome["message"]

