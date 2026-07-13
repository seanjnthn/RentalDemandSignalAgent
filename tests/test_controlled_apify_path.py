from types import SimpleNamespace
from rdsa import config
from rdsa.apify_provider import ApifyThreadsProvider
from rdsa.cli import process_raw


class Response:
    status_code = 200
    def __init__(self, payload): self.payload = payload
    def json(self): return self.payload


class FakeSession:
    def __init__(self): self.runs = 0; self.by_run = {}
    def post(self, url, **kwargs):
        self.runs += 1; rid = f"mock-{self.runs}"
        self.by_run[rid] = [{"id": f"{rid}-1", "text": "cari apartemen BSD 2 kamar 6 jt/bulan secepatnya", "username": "public_renter", "timestamp": "2026-07-13T00:00:00Z", "permalink": "https://threads.net/@public_renter/post/1"}, {"id": "duplicate", "text": "cari apartemen BSD 2 kamar 6 jt/bulan", "username": "public_renter", "timestamp": "2026-07-13T00:00:00Z", "permalink": "https://threads.net/@public_renter/post/duplicate"}, {"id": f"{rid}-spam", "text": "harga terbaik hubungi wa admin apartemen BSD", "username": "agent", "timestamp": "2026-07-13T00:00:00Z", "permalink": "https://threads.net/@agent/post/spam"}]
        return Response({"data": {"id": rid}})
    def get(self, url, **kwargs):
        if "/actor-runs/" not in url:
            # Preflight GET /acts/{id} — return a 200 meta response.
            return Response({"data": {"id": "meta", "status": "SUCCEEDED"}})
        rid = url.split("/actor-runs/")[1].split("/")[0]
        if "dataset" in url: return Response(self.by_run[rid])
        return Response({"data": {"status": "SUCCEEDED", "computeUnits": 0.1}})


def test_controlled_apify_end_to_end_report(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    session = FakeSession(); provider = ApifyThreadsProvider(token="mock", session=session)
    provider.usage = provider.usage.__class__(tmp_path / "usage.json")
    queries = config.APIFY_QUERIES
    posts = provider.search(queries, max_posts_per_query=5, max_total=20)
    result = process_raw(posts, "apify", SimpleNamespace(dry_run=True), None)
    print("Controlled Apify report: actor execution success (mocked)")
    print(f"result count: {len(posts)}; runs/queries: {session.runs}/{len(queries)}; estimated run cost: ${provider.usage.total_usd:.2f}")
    print(f"relevant (hot+qualified): {sum(result['classes'].get(k, 0) for k in ('hot_lead','qualified_lead'))}; duplicates dropped: {result['duplicates']}; broker/spam: {result['classes'].get('agent_broker', 0) + result['classes'].get('spam', 0)}")
    print("available fields: id, text, timestamp, username, permalink; freshness: mocked current-day timestamps")
    print("limitations: public text only, rules-based extraction, no author contact, no Telegram")
    assert session.runs == 4 and len(posts) == 12 and result["duplicates"] >= 1
    output = capsys.readouterr().out
    print(output, end="")
    assert "Controlled Apify report" in output
