from pathlib import Path
def test_threads_code_is_read_only():
    text=Path('rdsa/threads_client.py').read_text(encoding='utf-8').lower()
    assert 'keyword_search' in text
    assert 'graph.threads.net' in text
    assert 'threads.net/bot' not in text
    assert all(x not in text for x in ('.post(','.put(','.delete(','publish','follow','repost','comment','direct message'))

def test_apify_provider_is_public_read_only_adapter():
    text=Path('rdsa/apify_provider.py').read_text(encoding='utf-8').lower()
    assert 'api.apify.com' in text
    assert 'graph.threads.net' not in text
    assert all(x not in text for x in ('reply', 'comment', 'follow', 'publish', 'direct message', 'send dm'))
