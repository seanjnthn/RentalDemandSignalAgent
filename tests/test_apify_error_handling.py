import pytest
import requests
from rdsa.apify_provider import ApifyError, ApifyQuotaError, ApifyThreadsProvider


class Response:
    def __init__(self, status, payload=None): self.status_code = status; self.payload = payload or {}
    def json(self): return self.payload


def test_malformed_dataset_is_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    class S:
        def post(self, *a, **k): return Response(200, {"data": {"id": "r"}})
        def get(self, url, **kwargs):
            if "dataset" in url: return Response(200, {"not": "a list"})
            return Response(200, {"data": {"status": "SUCCEEDED"}})
    p = ApifyThreadsProvider(token="t", session=S()); p.usage = p.usage.__class__(tmp_path / "u.json")
    assert p.search(["q"]) == []


def test_429_is_quota_after_retries(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    class S:
        def post(self, *a, **k): return Response(429, {"error": "quota exceeded"})
    with pytest.raises(ApifyQuotaError): ApifyThreadsProvider(token="t", session=S()).search(["q"])


def test_5xx_retries_then_errors(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    class S:
        def __init__(self): self.calls = 0
        def post(self, *a, **k): self.calls += 1; return Response(503)
    s = S()
    with pytest.raises(ApifyError): ApifyThreadsProvider(token="t", session=s).search(["q"])
    assert s.calls == 3


def test_timeout_is_clear_error(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    class S:
        def post(self, *a, **k): raise requests.Timeout("slow")
    with pytest.raises(ApifyError, match="timed out"): ApifyThreadsProvider(token="t", session=S()).search(["q"])
