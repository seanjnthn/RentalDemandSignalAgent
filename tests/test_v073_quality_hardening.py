"""v0.7.3 scheduler quality hardening — targeted offline tests.

Covers the four fixes:
  1. genuine-seeker classifier precedence (family/school demand overrides an
     ambiguous offering-form word, but strong listings stay agent_broker);
  2. rent-aware budget extraction (area/IPL/deposit separated from rent);
  3. classifier_reason persistence through to_dict()/SQLite;
  4. scheduled-run => lead provenance (scheduled_run_leads).

No Apify, no Telegram, no Windows task, no full synthetic scan.
"""
import json
import pytest
from rdsa.extractor import extract
from rdsa.scorer import score
from rdsa.classifier import classify
from rdsa.budget_parser import parse_budget
from rdsa import db as D


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SEEKER_POST = (
    "Kakak2 warga thread dom Tangerang khususnya daerah :\n"
    "Poris\nCipondoh\nPerumnas Karawaci\nSangiang\nKota Bumi\n"
    "(Di utamakan Poris, Cipondoh & sekitarnya)\n"
    "Aku minta tolong kalau ada info rumah kecil yg mau dikontrakin, bisa akses mobil & "
    "ada parkiran mobilnya (yg harga sewanya gak terlalu mehol), tolong di spill siapa tau kita cocok\n"
    "Udh lumayan lama nyari kontrakan tapi blm nemu, alesan mau pindah krn anakku sebentar lagi "
    "sekolah & niatnya mau di sekolahin di daerah (Poris)"
)


def _lead(text, pid="x"):
    l = extract({"id": pid, "text": text, "timestamp": "2026-07-15T06:00:00+00:00"})
    classify(score(l))
    return l


# ---------------------------------------------------------------------------
# Fix 1 — genuine-seeker classifier precedence
# ---------------------------------------------------------------------------
def test_family_school_seeker_becomes_genuine_demand():
    l = _lead(SEEKER_POST, pid="3829775294010720778")
    assert l.lead_class != "agent_broker"
    assert l.classifier_reason.startswith("genuine_seeker")
    assert l.rental_intent == "seeking"


def test_actual_disewakan_listing_stays_agent_broker():
    for txt in [
        "disewakan apartemen BSD 2 kamar 5 jt/bulan",
        "DISEWAKAN APARTEMENT DI GADING SERPONG harga sewa 25 juta/tahun",
        "disewakan rumah uk. 3 x 12mtr harga Rp. 1.300.000/bln",
        "saya ada unit untuk disewakan, fasilitas lengkap",
    ]:
        l = _lead(txt, pid="lst")
        assert l.lead_class == "agent_broker", f"{txt!r} -> {l.lead_class}"
        assert l.classifier_reason.startswith("offering_supply")


def test_ambiguous_dikontrakkan_family_context():
    # "dikontrakin" is an offering-form word, but first-person household demand + no
    # strong listing proof must override it to a genuine seeker.
    l = _lead("rumah kecil yg mau dikontrakin buat anak saya sekolah, lama nyari", pid="dk")
    assert l.lead_class != "agent_broker"
    assert l.classifier_reason.startswith("genuine_seeker")


def test_ambiguous_offering_with_strong_proof_stays_listing():
    # Even with a household-sounding phrase, a real listing (unit/price/facilities) wins.
    l = _lead("anak saya butuh sekolah, disewakan unit ada fasilitas harga 3jt/bulan", pid="sp")
    assert l.lead_class == "agent_broker"


def test_classifier_reason_persists_on_lead_and_dict():
    l = _lead(SEEKER_POST, pid="3829775294010720778")
    assert l.classifier_reason and l.classifier_reason.startswith("genuine_seeker")
    assert "classifier_reason" in l.to_dict()
    assert l.to_dict()["classifier_reason"] == l.classifier_reason


# ---------------------------------------------------------------------------
# Fix 2 — rent-aware budget extraction
# ---------------------------------------------------------------------------
LISTING_23M_IPL_RENT = (
    "*DISEWAKAN APARTEMENT DI GADING SERPONG*\n"
    "-Luas kamarnya : 23m\n"
    "-IPL per bulan : 285rb\n"
    "-Harga sewa per tahun : 25 juta (Nego)\n"
    "#sewa #apartemen"
)


def test_23m_ipl_285rb_rent_25juta_selects_only_rent():
    b = parse_budget(LISTING_23M_IPL_RENT)
    assert b.role == "rent"
    # rent must be 25,000,000 yearly, NOT 23m and NOT 285rb
    assert b.min_amount == b.max_amount == 25_000_000
    assert b.period == "year"
    assert b.original_yearly == 25_000_000
    assert b.monthly_min == 25_000_000 // 12
    # IPL is captured as a separate (non-rent) charge
    ipl = [c for c in b.candidates if c["role"] == "ipl"]
    assert ipl and ipl[0]["amount"] == 285_000
    # 23m is area, never money
    assert b.area_text and "23m" in b.area_text
    rent_amounts = [c["amount"] for c in b.candidates if c["role"] == "rent"]
    assert 23_000_000 not in rent_amounts
    assert 285_000 not in rent_amounts


def test_rp_1_300_000_per_bln_parses_monthly():
    text = "harga : Rp. 1.300.000/bln"
    b = parse_budget(text)
    assert b.role == "rent"
    assert b.min_amount == b.max_amount == 1_300_000
    assert b.period == "month"
    assert b.monthly_min == b.monthly_max == 1_300_000
    assert b.confidence in ("high", "medium")
    assert b.area_text is None


def test_dimensions_are_not_monetary():
    for text in ["Luas kamarnya : 23m", "uk. 3 x 12mtr", "kamar 4x5m"]:
        b = parse_budget(text)
        assert b.role != "rent" or b.rent_figure is None
        assert b.area_text is not None


def test_ipl_does_not_replace_rent():
    text = "IPL per bulan : 285rb\nHarga sewa per tahun : 25 juta"
    b = parse_budget(text)
    assert b.role == "rent"
    assert b.rent_figure == 25_000_000
    assert b.min_amount == 25_000_000


def test_deposit_and_service_charge_controls():
    b = parse_budget("deposit 2 juta, service charge 150rb/bulan, harga sewa 10 juta/tahun")
    assert b.role == "rent"
    assert b.rent_figure == 10_000_000
    roles = {c["role"] for c in b.candidates}
    assert "deposit" in roles
    assert "ipl" in roles  # service charge mapped to ipl role


# ---------------------------------------------------------------------------
# Fix 3 — classifier_reason persists through SQLite (manual + pilot + scheduled)
# ---------------------------------------------------------------------------
def test_classifier_reason_written_to_sqlite(tmp_path):
    c = D.connect(str(tmp_path / "db.sqlite"))
    l = _lead(SEEKER_POST, pid="3829775294010720778")
    assert D.upsert_lead(c, l, "apify") == 1
    row = c.execute("SELECT classifier_reason, lead_class FROM leads WHERE post_id=?",
                    ("3829775294010720778",)).fetchone()
    assert row["classifier_reason"] == l.classifier_reason
    assert row["classifier_reason"].startswith("genuine_seeker")


def test_existing_meaningful_reason_not_overwritten(tmp_path):
    c = D.connect(str(tmp_path / "db.sqlite"))
    l = _lead(SEEKER_POST, pid="x1")
    D.upsert_lead(c, l, "apify")
    # Re-insert the same lead (e.g. re-fetched): UPSERT refreshes last_seen only and
    # must NOT clobber the previously stored classifier_reason with NULL.
    D.upsert_lead(c, l, "apify")
    row = c.execute("SELECT classifier_reason FROM leads WHERE post_id='x1'").fetchone()
    assert row["classifier_reason"] == l.classifier_reason


# ---------------------------------------------------------------------------
# Fix 4 — scheduled-run lead provenance
# ---------------------------------------------------------------------------
def test_provenance_migration_idempotent(tmp_path):
    c = D.connect(str(tmp_path / "db.sqlite"))
    D.migrate_provenance(c)
    cols1 = {r[1] for r in c.execute("PRAGMA table_info(scheduled_run_leads)")}
    D.migrate_provenance(c)
    cols2 = {r[1] for r in c.execute("PRAGMA table_info(scheduled_run_leads)")}
    assert cols1 == cols2
    assert {"run_id", "post_id", "inserted_this_run", "classification",
            "eligible", "created_at"} <= cols1


def test_run_to_post_association(tmp_path):
    c = D.connect(str(tmp_path / "db.sqlite"))
    D.associate_run_leads(c, "run-1", [
        {"post_id": "p1", "inserted_this_run": True, "classification": "qualified_lead", "eligible": True},
        {"post_id": "p2", "inserted_this_run": False, "classification": "agent_broker", "eligible": False},
    ])
    rows = D.leads_for_run(c, "run-1")
    assert {(r["post_id"], r["inserted_this_run"], r["classification"], r["eligible"])
            for r in rows} == {
        ("p1", 1, "qualified_lead", 1), ("p2", 0, "agent_broker", 0)}


def test_duplicate_association_prevented(tmp_path):
    c = D.connect(str(tmp_path / "db.sqlite"))
    n1 = D.associate_run_leads(c, "run-2", [
        {"post_id": "p1", "inserted_this_run": True, "classification": "hot_lead", "eligible": True},
    ])
    n2 = D.associate_run_leads(c, "run-2", [
        {"post_id": "p1", "inserted_this_run": True, "classification": "hot_lead", "eligible": True},
    ])
    assert n1 == 1 and n2 == 0  # INSERT OR IGNORE -> second insert is a no-op
    assert len(D.leads_for_run(c, "run-2")) == 1


def test_new_post_ids_recoverable_by_run(tmp_path):
    c = D.connect(str(tmp_path / "db.sqlite"))
    D.associate_run_leads(c, "run-3", [
        {"post_id": "p1", "inserted_this_run": True, "classification": "hot_lead", "eligible": True},
        {"post_id": "p2", "inserted_this_run": False, "classification": "agent_broker", "eligible": False},
        {"post_id": "p3", "inserted_this_run": True, "classification": "qualified_lead", "eligible": True},
    ])
    assert D.new_post_ids_for_run(c, "run-3") == ["p1", "p3"]


def test_historical_tables_unchanged_by_migration(tmp_path):
    c = D.connect(str(tmp_path / "db.sqlite"))
    c.execute("INSERT INTO scheduled_runs(run_id, trigger_type, started_at, status) "
              "VALUES('old-run','daily_schedule','2026-01-01T00:00:00Z','completed')")
    c.commit()
    before = c.execute("SELECT COUNT(*) FROM scheduled_runs").fetchone()[0]
    D.migrate_provenance(c)
    after = c.execute("SELECT COUNT(*) FROM scheduled_runs").fetchone()[0]
    assert before == after == 1


def test_scheduler_records_lead_provenance(tmp_path, monkeypatch):
    """A mocked scheduled run populates scheduled_run_leads for every processed lead."""
    from rdsa import config, scheduler as S
    db = tmp_path / "rdsa_test.sqlite3"
    lock = tmp_path / "scheduler.lock"
    usage = tmp_path / "apify_usage.json"
    usage.write_text(json.dumps({"month": "2026-07", "actual_usd": 1.0,
                                 "estimated_usd": 1.0, "runs": 0}), encoding="utf-8")
    real_csv = tmp_path / "inventory_real.csv"
    real_csv.write_text("inventory_id,title,location,property_type,bedrooms,price,period\n",
                        encoding="utf-8")
    monkeypatch.setattr(config, "DB_PATH", str(db))
    monkeypatch.setattr(config, "LOCK_PATH", str(lock))
    monkeypatch.setattr(config, "RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(config, "APIFY_USAGE_PATH", str(usage))
    monkeypatch.setattr(config, "INVENTORY_REAL_CSV", str(real_csv))
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", True)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)
    monkeypatch.setattr(config, "APIFY_LIVE_ENABLED", "false")
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)

    from unittest import mock
    new_ids = ["n1", "n2"]
    leads = [mock.Mock(post_id="n1", lead_class="qualified_lead"),
             mock.Mock(post_id="n2", lead_class="agent_broker")]
    fake = {"raw_posts": 4, "normalized_posts": 4, "duplicates": 0,
            "new_rows": 2, "leads": leads, "new_post_ids": new_ids}

    def fake_process(raw, source, args, c, inventory_mode=None):
        return fake

    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw", side_effect=fake_process), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=([{"inventory_id": "APT-TEST-1", "title": "T",
                                    "location": "BSD", "property_type": "apartment",
                                    "bedrooms": 1, "price": 2000000, "period": "month"}],
                                   {"ok": True})):
        Prov.return_value.search_batched.return_value = []
        S.run_scheduled_run(mock.Mock(confirm_scheduled_run=True, trigger_type="scheduled_canary"))

    c = D.connect(str(db))
    rows = D.leads_for_run(c, S.latest_run(c)["run_id"])
    assert {r["post_id"] for r in rows} == {"n1", "n2"}
    by_pid = {r["post_id"]: r for r in rows}
    assert by_pid["n1"]["inserted_this_run"] == 1 and by_pid["n1"]["classification"] == "qualified_lead"
    assert by_pid["n2"]["inserted_this_run"] == 1 and by_pid["n2"]["classification"] == "agent_broker"
