import json
from datetime import datetime, timezone

from rdsa.db import connect, mark_alert, upsert_lead
from rdsa.extractor import extract
from rdsa.ingest import is_duplicate
from rdsa.scorer import score
from rdsa.classifier import classify


def _lead(item):
    lead = score(extract(item["post"], datetime(2026, 7, 13, 7, tzinfo=timezone.utc)), datetime(2026, 7, 13, 7, tzinfo=timezone.utc))
    return classify(lead)


def test_same_post_id_is_stored_once(tmp_path):
    item = json.load(open("data/synthetic_posts.json", encoding="utf-8"))["posts"][0]
    lead = _lead(item)
    db = connect(str(tmp_path / "rdsa.sqlite3"))
    assert upsert_lead(db, lead) == 1
    assert upsert_lead(db, lead) == 0
    assert db.execute("select count(*) from leads").fetchone()[0] == 1


def test_same_author_near_duplicate_is_throttled_and_alerted_once():
    posts = json.load(open("data/synthetic_posts.json", encoding="utf-8"))["posts"]
    first, duplicate = (_lead(posts[i]) for i in (0, 18))
    assert not is_duplicate(first, [])
    assert is_duplicate(duplicate, [first.to_dict()])
    db = connect(":memory:")
    upsert_lead(db, first)
    assert mark_alert(db, first.post_id) == 1
    assert is_duplicate(duplicate, [{"post_id": first.post_id, "author_username": first.author_username, "dedup_hash": first.dedup_hash, "raw_text": first.raw_text}])
    assert db.execute("select count(*) from alerts").fetchone()[0] == 1
