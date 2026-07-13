import pytest
from rdsa.apify_provider import (
    ApifyError,
    ApifyConfigError,
    ApifyThreadsProvider,
)


class Resp:
    def __init__(self, status_code=200, json=None):
        self.status_code = status_code
        self._json = json if json is not None else {}
    def json(self):
        return self._json


class FakeSession:
    """Records calls; returns a fixed status for every GET/POST."""
    def __init__(self, get_status=200, post_status=201):
        self.calls = []
        self.get_status = get_status
        self.post_status = post_status
    def get(self, url, **kwargs):
        self.calls.append(("get", url))
        return Resp(self.get_status)
    def post(self, url, **kwargs):
        self.calls.append(("post", url))
        return Resp(self.post_status, {"data": {"id": "run-1", "status": "SUCCEEDED", "usageTotalUsd": 0.001}})


def test_normalize_slash_to_tilde():
    assert ApifyThreadsProvider.normalize_actor_id("automation-lab/threads-scraper") == "automation-lab~threads-scraper"


def test_normalize_tilde_unchanged():
    assert ApifyThreadsProvider.normalize_actor_id("automation-lab~threads-scraper") == "automation-lab~threads-scraper"


def test_normalize_numeric_unchanged():
    assert ApifyThreadsProvider.normalize_actor_id("123456") == "123456"
    assert ApifyThreadsProvider.normalize_actor_id("123456~789") == "123456~789"


def test_normalize_malformed_raises():
    for bad in ["", "owner/", "/name", "justname"]:
        with pytest.raises(ApifyConfigError):
            ApifyThreadsProvider.normalize_actor_id(bad)


def test_search_uses_normalized_id_in_url(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    sess = FakeSession(get_status=200, post_status=201)
    # run status poll returns SUCCEEDED with no dataset items
    class S2(FakeSession):
        def __init__(self):
            super().__init__()
        def get(self, url, **kwargs):
            self.calls.append(("get", url))
            if "dataset" in url:
                return Resp(200, [])
            return Resp(200, {"data": {"id": "run-1", "status": "SUCCEEDED", "usageTotalUsd": 0.001}})
    provider = ApifyThreadsProvider(token="x", actor_id="automation-lab/threads-scraper", session=S2())
    # preflight GET hits /acts/automation-lab~threads-scraper
    provider.search(["cari apartemen BSD"], max_posts_per_query=1, max_total=1)
    preflight = [u for m, u in provider.session.calls if m == "get" and "/runs" not in u and "/dataset" not in u]
    assert preflight and "automation-lab~threads-scraper" in preflight[0]
    assert "automation-lab/threads-scraper" not in preflight[0]


def test_preflight_200_ok(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    sess = FakeSession(get_status=200)
    provider = ApifyThreadsProvider(token="x", actor_id="automation-lab/threads-scraper", session=sess)
    assert provider.preflight() == 200
    # preflight must NOT start a run
    assert all("runs" not in u for _, u in sess.calls)


def test_preflight_401_403(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    for status in (401, 403):
        sess = FakeSession(get_status=status)
        provider = ApifyThreadsProvider(token="x", actor_id="automation-lab/threads-scraper", session=sess)
        with pytest.raises(ApifyError, match="authentication|access"):
            provider.preflight()


def test_preflight_404(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    sess = FakeSession(get_status=404)
    provider = ApifyThreadsProvider(token="x", actor_id="automation-lab/threads-scraper", session=sess)
    with pytest.raises(ApifyError, match="404|not found"):
        provider.preflight()


def test_preflight_other_error(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    sess = FakeSession(get_status=500)
    provider = ApifyThreadsProvider(token="x", actor_id="automation-lab/threads-scraper", session=sess)
    with pytest.raises(ApifyError):
        provider.preflight()


def test_token_redaction():
    redacted = ApifyThreadsProvider.redact("https://api.apify.com/v2/acts/x/runs?token=SECRET123&foo=bar")
    assert "SECRET123" not in redacted
    assert "token=***" in redacted
    assert "foo=bar" in redacted
