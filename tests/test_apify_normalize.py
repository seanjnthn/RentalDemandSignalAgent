from rdsa.apify_provider import ApifyThreadsProvider


def test_normalize_aliases_and_required_fields():
    item = {"id": 7, "text": "cari apartemen BSD", "postUrl": "https://threads.net/@u/post/7", "createdAt": "2026-07-13T00:00:00Z", "userName": "u"}
    assert ApifyThreadsProvider.normalize(item) == {"id": "7", "text": "cari apartemen BSD", "timestamp": item["createdAt"], "username": "u", "permalink": item["postUrl"]}
    assert ApifyThreadsProvider.normalize({"id": "x"}) is None
    assert ApifyThreadsProvider.normalize({"text": "missing id"}) is None


def test_normalize_prefers_canonical_fields():
    item = {"id": "x", "text": "hello", "permalink": "p", "url": "u", "timestamp": "t", "createdAt": "old", "username": "name", "userName": "old-name"}
    result = ApifyThreadsProvider.normalize(item)
    assert result["permalink"] == "p" and result["timestamp"] == "t" and result["username"] == "name"


def test_normalize_converts_epoch_int_timestamp_to_iso():
    # Actor returns timestamp as epoch seconds (int).
    item = {"id": "x", "text": "hi", "timestamp": 1752000000, "username": "u", "url": "https://t/p"}
    r = ApifyThreadsProvider.normalize(item)
    assert r["timestamp"].endswith("+00:00") and "T" in r["timestamp"]


def test_normalize_converts_epoch_ms_timestamp_to_iso():
    item = {"id": "x", "text": "hi", "timestamp": 1752000000000, "username": "u", "url": "https://t/p"}
    r = ApifyThreadsProvider.normalize(item)
    assert r["timestamp"].endswith("+00:00")


def test_normalize_rejects_unparseable_timestamp_gracefully():
    item = {"id": "x", "text": "hi", "timestamp": -1, "username": "u", "url": "https://t/p"}
    r = ApifyThreadsProvider.normalize(item)
    assert isinstance(r["timestamp"], str)  # never an int downstream
