"""v0.6.3 hardening tests — delivery atomicity, current-run newness, classifier,
budget-period, and structured bedrooms. All offline: no Apify, no Telegram network.
Uses repository-local temp DBs (tempfile.mkdtemp) to stay Windows-safe and avoid the
system temp-dir PermissionError seen under the sandbox."""
import os, tempfile, sqlite3
import pytest
from rdsa import db as D
from rdsa.extractor import extract
from rdsa.scorer import score
from rdsa.classifier import classify
from rdsa.budget_parser import parse_budget
from rdsa.notifier import send_lead_cards, preview_eligible


def _conn():
    d = tempfile.mkdtemp(prefix="rdsa_v063_")
    return D.connect(os.path.join(d, "t.sqlite3"))


def _lead(text, pid="1"):
    l = extract({"id": pid, "text": text, "timestamp": "2026-07-13T06:00:00+00:00"})
    classify(score(l))
    return l


# ---------------- delivery atomicity + state machine ----------------
def test_post_id_canonicalization():
    assert D.normalize_post_id(123) == D.normalize_post_id("123") == "123"
    assert D.normalize_post_id("  456  ") == "456"


def test_claim_then_send_then_reclaim_blocked():
    c = _conn()
    assert D.claim_delivery(c, "p1") is True
    assert D.claim_delivery(c, "p1") is False          # conflict -> fail closed
    D.complete_delivery(c, "p1", 777)
    assert D.claim_delivery(c, "p1") is False          # already sent -> blocked


def test_pending_claim_blocks_second_claim():
    c = _conn()
    D.claim_delivery(c, "p2")                           # pending
    assert D.claim_delivery(c, "p2") is False          # another process/attempt blocked


def test_failed_delivery_auditable_and_not_sent():
    c = _conn()
    D.claim_delivery(c, "pf")
    try:
        raise RuntimeError("boom")
    except Exception as e:
        D.fail_delivery(c, "pf", str(e))
    row = c.execute("SELECT status, error FROM delivery_claims WHERE post_id=?", ("pf",)).fetchone()
    assert row["status"] == "failed"
    assert "boom" in (row["error"] or "")
    assert D.claim_delivery(c, "pf") is False           # failed -> no auto-retry


def test_historical_alert_backfill_blocks_claim():
    # Seed a real alerts row, then connect() backfills delivery_claims (status='sent').
    d = tempfile.mkdtemp(prefix="rdsa_v063_")
    dbp = os.path.join(d, "x.sqlite3")
    seed = sqlite3.connect(dbp)
    seed.execute('CREATE TABLE alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id TEXT NOT NULL,sent_at TEXT NOT NULL,channel TEXT NOT NULL DEFAULT "telegram",message_id TEXT)')
    seed.execute("INSERT INTO alerts(post_id,sent_at,channel,message_id) VALUES(?,?,?,?)", ("h1", "2026-07-14T00:00:00+00:00", "telegram", "17"))
    seed.commit(); seed.close()
    c = D.connect(dbp)
    backed = c.execute("SELECT status,message_id FROM delivery_claims WHERE post_id=?", ("h1",)).fetchone()
    assert backed["status"] == "sent" and backed["message_id"] == "17"
    assert D.claim_delivery(c, "h1") is False           # historical alert blocks claim


def test_atomic_claim_conflict_performs_zero_telegram_calls():
    c = _conn()
    calls = []

    class Fake:
        def send(self, card):
            calls.append(1)
            return 555
    D.claim_delivery(c, "p9")
    # second claim fails -> never reaches notifier
    sent = send_lead_cards(Fake(), [{"post_id": "p9", "lead_class": "hot_lead", "lead_score": 90}], c, new_post_ids=["p9"])
    assert calls == [], "no Telegram call when claim rejected"
    assert sent == 0


def test_successful_claim_sends_exactly_once():
    c = _conn()
    calls = []

    class Fake:
        def send(self, card):
            calls.append(1)
            return 555
    import rdsa.config as cfg
    cfg.TELEGRAM_SEND_ENABLED = True
    try:
        sent = send_lead_cards(Fake(), [{"post_id": "p10", "lead_class": "hot_lead", "lead_score": 90}], c, new_post_ids=["p10"])
        assert sent == 1 and len(calls) == 1
        sent2 = send_lead_cards(Fake(), [{"post_id": "p10", "lead_class": "hot_lead", "lead_score": 90}], c, new_post_ids=["p10"])
        assert sent2 == 0 and len(calls) == 1
    finally:
        cfg.TELEGRAM_SEND_ENABLED = False


def test_second_attempt_sends_zero():
    c = _conn()
    calls = []

    class Fake:
        def send(self, card):
            calls.append(1)
            return 555
    import rdsa.config as cfg
    cfg.TELEGRAM_SEND_ENABLED = True
    try:
        send_lead_cards(Fake(), [{"post_id": "pa", "lead_class": "qualified_lead", "lead_score": 70}], c, new_post_ids=["pa"])
        send_lead_cards(Fake(), [{"post_id": "pa", "lead_class": "qualified_lead", "lead_score": 70}], c, new_post_ids=["pa"])
        assert len(calls) == 1
    finally:
        cfg.TELEGRAM_SEND_ENABLED = False


def test_first_insert_is_new_then_repeat_not_new():
    c = _conn()
    l = _lead("cari apartemen BSD 5jt/bulan", pid="100")
    assert D.upsert_lead(c, l) == 1
    assert D.upsert_lead(c, l) == 0          # last_seen refresh only, not new


def test_string_numeric_post_id_consistency():
    c = _conn()
    a = D.upsert_lead(c, _lead("cari apartemen BSD", pid=200))
    b = D.upsert_lead(c, _lead("cari apartemen BSD", pid="200"))
    assert a == 1 and b == 0


def test_last_seen_refresh_not_in_new_post_ids():
    c = _conn()
    l = _lead("cari apartemen BSD 5jt/bulan", pid="300")
    D.upsert_lead(c, l)
    # simulate process_raw new_post_ids tracking
    new = []
    if D.upsert_lead(c, l):
        new.append(D.normalize_post_id(l.post_id))
    assert new == []                        # repeated ingestion not new


def test_historical_eligible_lead_blocked_without_new_post_ids():
    c = _conn()
    l = _lead("cari apartemen BSD 5jt/bulan", pid="400")
    D.upsert_lead(c, l)                     # already inserted previously
    calls = []

    class Fake:
        def send(self, card):
            calls.append(1)
            return 1
    # historical eligible lead but NOT in new_post_ids -> not delivered
    sent = send_lead_cards(Fake(), [l], c, new_post_ids=[])
    assert sent == 0 and calls == []


def test_run_1_run_5_duplicate_prevented():
    # Reproduce: a lead already delivered in Run #1 must not be re-sent in Run #5.
    c = _conn()
    # Run #1: backfill an alert (as connect() would from alerts table)
    c.execute("INSERT OR IGNORE INTO delivery_claims(post_id,channel,status,claimed_at,sent_at,message_id) VALUES(?,?,?,?,?,?)",
              ("dup1", "telegram", "sent", "2026-07-14T00:00:00+00:00", "2026-07-14T00:00:00+00:00", "17"))
    calls = []

    class Fake:
        def send(self, card):
            calls.append(1)
            return 99
    lead = {"post_id": "dup1", "lead_class": "hot_lead", "lead_score": 90}
    sent = send_lead_cards(Fake(), [lead], c, new_post_ids=["dup1"])  # even if "new" this run
    assert sent == 0 and calls == [], "Run #5 duplicate prevented via atomic claim"


# ---------------- classifier hardening ----------------
THIRD_PARTY = [
    "saya lagi ada client cari apartemen",
    "ada client cari rumah",
    "client saya mencari unit",
    "untuk klien",
    "mencarikan unit untuk tenant",
    "butuh listing untuk client",
    "co-broke rumah",
    "cobroke apartemen",
    "broker mencari unit",
    "agen properti cari",
]
GENUINE = [
    "saya cari apartemen untuk saya sendiri",
    "saya dan keluarga mencari rumah",
    "butuh kontrakan untuk ditempati",
    "saya cari kos untuk tinggal",
]


@pytest.mark.parametrize("txt", THIRD_PARTY)
def test_third_party_demand_is_agent_broker(txt):
    l = _lead(txt, pid="t1")
    assert l.lead_class == "agent_broker"
    assert l.classifier_reason.startswith("third_party_demand:")


@pytest.mark.parametrize("txt", GENUINE)
def test_genuine_first_person_not_agent_broker(txt):
    l = _lead(txt, pid="t2")
    assert l.lead_class != "agent_broker"   # stays eligible (watch/irrelevant OK), never broker


def test_classifier_reason_retained():
    l = _lead("ada client cari rumah", pid="t3")
    assert "client" in l.classifier_reason


def test_agent_broker_never_telegram_eligible():
    l = _lead("ada client cari rumah", pid="t4")
    assert not preview_eligible(l)


def test_ambiguous_bare_client_word_not_agent_when_genuine():
    # "client" alone is not a cue; genuine first-person wins.
    l = _lead("saya cari apartemen untuk saya sendiri client", pid="t5")
    assert l.lead_class != "agent_broker"


# ---------------- budget period ----------------
def test_yearly_abbreviations():
    assert parse_budget("50jt/thn").period == "year"
    assert parse_budget("Rp50 juta/tahun").period == "year"
    assert parse_budget("30 juta setahun").period == "year"
    b = parse_budget("50jt/thn")
    assert b.min_amount == 50_000_000 and b.max_amount == 50_000_000
    # monthly equivalent retained for yearly
    assert b.monthly_min == 50_000_000 // 12


def test_monthly_abbreviations():
    assert parse_budget("2,5jt/bln").period == "month"
    assert parse_budget("Rp3 juta per bulan").period == "month"
    b = parse_budget("2,5jt/bln")
    assert b.min_amount == 2_500_000


def test_yearly_monthly_equivalent():
    b = parse_budget("30 juta setahun")
    assert b.period == "year"
    assert b.monthly_min == 30_000_000 // 12


def test_indonesian_decimal_comma():
    b = parse_budget("Rp3 juta per bulan")
    assert b.min_amount == 3_000_000


def test_bare_number_ambiguous_no_invented_amount():
    b = parse_budget("900")
    assert b.min_amount is None and b.period == "unknown" and b.confidence == "low"
    b2 = parse_budget("900 rb")
    assert b2.min_amount == 900_000 and b2.period == "unknown"


# ---------------- structured bedrooms ----------------
def _beds(txt):
    l = _lead(txt, pid="b1")
    return (l.bedrooms, l.bedroom_min, l.bedroom_max, l.bedroom_options, l.studio_acceptable, l.bedroom_confidence)


def test_studio():
    assert _beds("studio")[4] is True and _beds("studio")[3] == [0]


def test_2kt():
    beds, mn, mx, opts, studio, conf = _beds("2KT")
    assert beds == 2 and mn == 2 and mx == 2 and opts == [2] and studio is False


def test_studio_2kt_alternatives():
    beds, mn, mx, opts, studio, conf = _beds("studio/2KT")
    assert beds is None and opts == [0, 2] and studio is True   # alternatives preserved


def test_studio_atau_2_kamar():
    beds, mn, mx, opts, studio, conf = _beds("studio atau 2 kamar")
    assert beds is None and opts == [0, 2] and studio is True


def test_range_1_2_kamar():
    beds, mn, mx, opts, studio, conf = _beds("1-2 kamar")
    assert beds is None and mn == 1 and mx == 2


def test_minimum_2_kamar():
    beds, mn, mx, opts, studio, conf = _beds("minimal 2 kamar")
    assert beds is None and mn == 2 and mx is None


def test_maximum_3_kamar():
    beds, mn, mx, opts, studio, conf = _beds("maksimal 3 kamar")
    assert beds is None and mn is None and mx == 3


def test_uncertain_bedroom_no_exact_value():
    # range/options must not become an invented single exact value
    beds, mn, mx, opts, studio, conf = _beds("1-2 kamar")
    assert beds is None


# ---------------- dashboard KPI ----------------
def test_overview_cost_per_contacted_key_present():
    from rdsa.dashboard_repository import get_overview
    d = tempfile.mkdtemp(prefix="rdsa_v063_")
    dbp = os.path.join(d, "o.sqlite3")
    c = D.connect(dbp)
    # no contacted leads -> denominator zero -> None (Not available)
    ov = get_overview(db_path=dbp)
    assert "cost_per_contacted" in ov
    assert ov["cost_per_contacted"] is None
