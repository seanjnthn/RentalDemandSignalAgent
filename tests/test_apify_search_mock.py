from rdsa.apify_provider import ApifyThreadsProvider


class Response:
    status_code = 200
    def __init__(self, payload): self.payload = payload
    def json(self): return self.payload


class Session:
    def __init__(self): self.calls = []; self.datasets = {}
    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs)); run_id = f"run-{len(self.datasets)}"
        self.datasets[run_id] = [{"id": f"{run_id}-{i}", "text": "cari apartemen BSD", "url": "https://threads.net/p"} for i in range(10)]
        return Response({"data": {"id": run_id}})
    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if "/dataset/items" in url: return Response(self.datasets[url.split("/actor-runs/")[1].split("/")[0]])
        return Response({"data": {"status": "SUCCEEDED", "computeUnits": 0.1}})


def test_search_polls_and_caps_results(monkeypatch, tmp_path):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    session = Session(); provider = ApifyThreadsProvider(token="test-token", session=session)
    provider.usage = provider.usage.__class__(tmp_path / "usage.json")
    posts = provider.search(["one", "two"], max_posts_per_query=3, max_total=7)
    assert len(posts) == 6 and len(posts) <= 7 and all(set(p) == {"id", "text", "timestamp", "username", "permalink"} for p in posts)
    assert len([c for c in session.calls if c[0] == "POST"]) == 2
    assert all(c[2]["json"]["maxPosts"] == 3 for c in session.calls if c[0] == "POST")


def test_search_batched_single_run_and_polls(monkeypatch, tmp_path):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    session = Session(); provider = ApifyThreadsProvider(token="test-token", session=session)
    provider.usage = provider.usage.__class__(tmp_path / "usage.json")
    posts = provider.search_batched(["apartemen", "rumah sewa"], max_posts_per_query=5, max_total=20, timeout=10)
    # one batched run, not per-query
    post_calls = [c for c in session.calls if c[0] == "POST"]
    assert len(post_calls) == 1
    assert post_calls[0][2]["json"]["searchQueries"] == ["apartemen", "rumah sewa"]
    assert len(posts) == 10 and all(set(p) == {"id", "text", "timestamp", "username", "permalink"} for p in posts)

