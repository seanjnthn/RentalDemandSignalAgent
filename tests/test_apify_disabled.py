import pytest
from rdsa.apify_provider import ApifyError, ApifyThreadsProvider


def test_disabled_apify_makes_no_http_call(monkeypatch):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "false")
    class NoCall:
        def __getattr__(self, name): raise AssertionError(f"unexpected HTTP method: {name}")
    with pytest.raises(ApifyError, match="disabled"):
        ApifyThreadsProvider(token="not-used", session=NoCall()).search(["query"])
