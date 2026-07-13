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
