import json
import sqlite3

from rdsa.dashboard_repository import (
    get_inventory, get_lead, get_leads, get_matching_groups,
    normalize_matches, sanitize, update_lead_status,
)
from rdsa.db import connect


def seed(path, matched=None):
    c = connect(path)
    c.execute("INSERT INTO leads(post_id,source_url,author_username,post_timestamp,fetched_at,first_seen,last_seen,raw_text,desired_location,property_type,bedrooms,budget_max,budget_currency,budget_period,budget_confidence,lead_class,lead_score,matched_inventory,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("p1", "https://threads.net/p/1", "person", "2026-07-14T00:00:00+00:00", "2026-07-14T00:00:00+00:00", "2026-07-14T00:00:00+00:00", "2026-07-14T00:00:00+00:00", "Need apartment, call 081234567890 or me@example.com", "BSD", "apartment", 2, 8000000, "IDR", "month", "high", "hot_lead", 90, json.dumps(matched or []), "new"))
    c.commit(); c.close()


def test_empty_database_and_lead_loading(tmp_path):
    path = tmp_path / "empty.sqlite3"
    assert get_leads({}, path) == []
    seed(path, [{"property_id": "P-1", "match_type": "exact_match", "score": 90, "reasons": ["area aligned"], "warnings": []}])
    lead = get_lead("p1", path)
    assert lead["desired_location"] == "BSD"
    assert lead["matches"][0]["property_id"] == "P-1"
    assert "[redacted]" in lead["raw_text"]


def test_filters_and_legacy_match_shapes(tmp_path):
    path = tmp_path / "filter.sqlite3"
    seed(path, [{"inventory_id": "APT-GS-MTOWN-1BR-001", "location": "Gading Serpong", "match_reasons": ["budget"]}])
    assert len(get_leads({"classification": "hot_lead", "area": "BSD", "match_type": "nearby_alternative"}, path)) == 1
    assert normalize_matches("[null]") == []
    assert normalize_matches([{ "inventory_id": "A", "location": "BSD", "match_reasons": ["x"] }], "BSD")[0]["match_type"] == "legacy_synthetic"


def test_real_inventory_missing_and_valid(tmp_path):
    missing = get_inventory(tmp_path / "missing.csv")
    assert missing["rows"] == [] and missing["report"]["missing"]
    valid = get_inventory("data/inventory_real.csv")
    assert valid["report"]["ok"] and valid["rows"] and valid["rows"][0]["listing_url"]


def test_status_notes_and_audit_are_parameterized(tmp_path):
    path = tmp_path / "write.sqlite3"; seed(path)
    update_lead_status("p1", "reviewed", "reviewed; safe", db_path=path)
    lead = get_lead("p1", path)
    assert lead["status"] == "reviewed" and "safe" in lead["notes"]
    with sqlite3.connect(path) as c:
        row = c.execute("SELECT source,new_status FROM status_history WHERE post_id=?", ("p1",)).fetchone()
    assert row == ("dashboard", "reviewed")


def test_matching_groups_have_stable_labels(tmp_path):
    path = tmp_path / "groups.sqlite3"; seed(path, [{"property_id": "APT-GS-MTOWN-1BR-001", "match_type": "tentative_match", "score": 1, "reasons": [], "warnings": ["confirm"]}])
    assert get_matching_groups(path)["tentative_match"][0]["match"]["match_type"] == "tentative_match"


def test_scheduler_status_flag_coercion_and_no_secrets(tmp_path, monkeypatch):
    # APIFY_LIVE_ENABLED is a STRING ('false'/'true'); the dashboard must
    # report it consistently with the real live-gating truthy() helper.
    from rdsa.dashboard_repository import get_scheduler_status, _truthy
    import rdsa.config as config
    monkeypatch.setattr(config, "APIFY_LIVE_ENABLED", "false")
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", False)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)
    st = get_scheduler_status(tmp_path / "sched.sqlite3")
    assert st["apify_live_enabled"] is False
    assert st["scheduler_enabled"] is False
    assert st["scheduler_send_enabled"] is False
    assert st["telegram_send_enabled"] is False
    # 'true' string must still read as on (symmetry with gating logic).
    monkeypatch.setattr(config, "APIFY_LIVE_ENABLED", "true")
    assert _truthy(config.APIFY_LIVE_ENABLED) is True
    # Sanitized snapshot exposes neither run id, host, nor tokens.
    blob = json.dumps(st, default=str).lower()
    assert "run_id" not in blob and "hostname" not in blob
    assert "token" not in blob and "chat" not in blob
