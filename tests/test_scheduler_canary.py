"""PHASE 11 — offline canary simulation (mocks only, no live calls).

Runs the REAL scheduled-run pipeline (process_raw -> extract -> score ->
classify -> dedup -> DB insert -> delivery gating) against three synthetic
Apify posts. Only the Apify provider and TelegramNotifier are mocked, so the
canary exercises the genuine classifier, dedup, ledger, and fail-closed
delivery path — not a re-stubbed process_raw.

Simulations:
  1. New qualified demand lead + new offering + historical duplicate.
  2. Re-run the same input -> zero new, zero duplicate delivery.
  3. Projected monthly cost above stop threshold -> blocked_cost_limit.
  4. Apify/provider failure after run starts -> sanitized failed, no retry.
  5. Telegram failure after lead persistence + claim -> lead kept, not sent.

No Apify network call, no Telegram network call, no Windows task change.
"""
from __future__ import annotations

import json
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from rdsa import config
from rdsa import scheduler as S


# ---------------------------------------------------------------------------
# Synthetic Apify input (shape matches apify_provider.ApifyThreadsProvider.normalize)
# ---------------------------------------------------------------------------
NOW = datetime.now(timezone.utc).isoformat()

CANARY_DEMAND_ID = "demand-1"
CANARY_OFFER_ID = "offer-1"
CANARY_DUP_ID = "dup-1"

DEMAND_TEXT = (
    "Butuh apartemen BSD 2 kamar, budget 5jt/bulan, furnished, aman, "
    "sewa 1 tahun, pindah bulan ini."
)
OFFER_TEXT = (
    "Disewakan apartemen BSD 2 kamar, harga 5jt/bulan, furnished, "
    "silahkan hubungi wa untuk info."
)
DUP_TEXT = "Postingan historis duplikat yang sudah tercatat di database."


def make_posts():
    return [
        {"id": CANARY_DEMAND_ID, "text": DEMAND_TEXT, "timestamp": NOW,
         "username": "seeker1", "permalink": "https://threads.net/@seeker1/1"},
        {"id": CANARY_OFFER_ID, "text": OFFER_TEXT, "timestamp": NOW,
         "username": "owner1", "permalink": "https://threads.net/@owner1/1"},
        {"id": CANARY_DUP_ID, "text": DUP_TEXT, "timestamp": NOW,
         "username": "dupuser", "permalink": "https://threads.net/@dupuser/1"},
    ]


VALID_INVENTORY_CSV = (
    "property_id,area,building,property_type,bedrooms,monthly_price,furnished,"
    "available_from,features,status,listing_url\n"
    "APT-TEST-1,BSD,The Breeze,apartment,2,5000000,1,2026-08-01,"
    "\"furnished,carport\",available,https://example.com/listing/apt1\n"
)


@pytest.fixture
def canary_env(tmp_path, monkeypatch):
    db = tmp_path / "rdsa_canary.sqlite3"
    lock = tmp_path / "scheduler.lock"
    usage = tmp_path / "apify_usage.json"
    usage.write_text(json.dumps({"month": "2026-07", "actual_usd": 1.0,
                                 "estimated_usd": 1.0, "runs": 0}), encoding="utf-8")
    real_csv = tmp_path / "inventory_real.csv"
    real_csv.write_text(VALID_INVENTORY_CSV, encoding="utf-8")
    monkeypatch.setattr(config, "DB_PATH", str(db))
    monkeypatch.setattr(config, "LOCK_PATH", str(lock))
    monkeypatch.setattr(config, "RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(config, "APIFY_USAGE_PATH", str(usage))
    monkeypatch.setattr(config, "INVENTORY_REAL_CSV", str(real_csv))
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", False)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)
    monkeypatch.setattr(config, "APIFY_LIVE_ENABLED", "false")
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)
    yield types.SimpleNamespace(db=db, lock=lock, usage=usage, real_csv=real_csv)
    monkeypatch.setattr(config, "APIFY_LIVE_ENABLED", "false")
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)


def enable_scheduler(monkeypatch, send=False):
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", True)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", send)


def make_args(confirm=True, trigger="daily_schedule"):
    return types.SimpleNamespace(confirm_scheduled_run=confirm, trigger_type=trigger)


def seed_historical_duplicate(monkeypatch):
    """Pre-insert the historical duplicate lead so the canary dup post is excluded."""
    from rdsa import db as D
    c = D.connect(config.DB_PATH)
    c.execute(
        "INSERT INTO leads(post_id, source, provider, source_url, author_username, "
        "post_timestamp, fetched_at, raw_text, lead_class, lead_score, status, dedup_hash) "
        "VALUES (?, 'apify', 'apify', '', 'dupuser', '', '', ?, 'qualified_lead', 0, 'new', 'seedhash')",
        (CANARY_DUP_ID, DUP_TEXT),
    )
    c.commit()
    c.close()


def latest_row():
    from rdsa import db as D
    c = D.connect(config.DB_PATH)
    row = S.latest_run(c)
    c.close()
    return row


def delivery_claims():
    from rdsa import db as D
    c = D.connect(config.DB_PATH)
    rows = [dict(r) for r in c.execute("SELECT post_id, status FROM delivery_claims")]
    c.close()
    return rows


# ===========================================================================
# Simulation 1 — new qualified demand lead + offering + historical duplicate
# ===========================================================================
def test_canary_simulation_1_new_demand_offering_duplicate(canary_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    seed_historical_duplicate(monkeypatch)
    posts = make_posts()
    noti = mock.MagicMock()
    noti.send.return_value = 12345  # successful Telegram send returns message id
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti):
        Prov.return_value.search_batched.return_value = posts
        res = S.run_scheduled_run(make_args(confirm=True))

    assert res["status"] == "completed"
    # genuine new demand lead + new offering inserted; historical dup excluded.
    # (run_scheduled_run returns the NEW-ROW COUNT, not the id list.)
    assert res["new_posts"] == 2           # demand + offering inserted; dup excluded
    assert res["eligible"] == 1            # only the qualified demand lead
    assert res["sent"] == 1                # exactly one delivery claim succeeds
    assert noti.send.call_count == 1       # exactly one Telegram send

    # delivery claim recorded as sent (exactly one)
    claims = delivery_claims()
    sent = [c for c in claims if c["status"] == "sent"]
    assert len(sent) == 1
    assert sent[0]["post_id"] == CANARY_DEMAND_ID

    # ledger reached a completed terminal state
    row = latest_row()
    assert row["status"] == "completed"
    assert row["new_posts"] == 2
    assert row["eligible_leads"] == 1
    assert row["sent_cards"] == 1

    # flags restored to false
    assert config.APIFY_LIVE_ENABLED == "false"
    assert config.TELEGRAM_SEND_ENABLED is False
    # lock released
    assert S.SchedulerLock(str(canary_env.lock)).status()["locked"] is False


# ===========================================================================
# Simulation 2 — re-run the same input -> zero new, zero duplicate delivery
# ===========================================================================
def test_canary_simulation_2_rerun_idempotent(canary_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    seed_historical_duplicate(monkeypatch)
    posts = make_posts()
    noti = mock.MagicMock()
    noti.send.return_value = 12345
    sends_before = 0
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti):
        Prov.return_value.search_batched.return_value = posts
        # First run: populates demand + offering, sends one card.
        first = S.run_scheduled_run(make_args(confirm=True))
        sends_before = noti.send.call_count
        # Second run: same input again.
        second = S.run_scheduled_run(make_args(confirm=True))

    # Exactly one Telegram send across BOTH runs (no duplicate delivery).
    assert sends_before == 1
    assert noti.send.call_count == 1

    # Second run: zero newly inserted eligible leads, zero Telegram calls.
    assert second["new_posts"] == 0
    assert second["eligible"] == 0
    assert second["sent"] == 0

    # Terminal ledger state on re-run is a no-new-leads / no-eligible state.
    assert second["status"] in ("completed_no_new_leads", "completed_no_eligible_leads")
    row = latest_row()
    assert row["status"] in ("completed_no_new_leads", "completed_no_eligible_leads")

    # Zero duplicate delivery: still exactly one sent claim from the first run.
    claims = delivery_claims()
    assert len([c for c in claims if c["status"] == "sent"]) == 1

    # flags restored, lock released
    assert config.APIFY_LIVE_ENABLED == "false"
    assert config.TELEGRAM_SEND_ENABLED is False
    assert S.SchedulerLock(str(canary_env.lock)).status()["locked"] is False


# ===========================================================================
# Simulation 3 — projected monthly cost above stop threshold
# ===========================================================================
def test_canary_simulation_3_cost_limit_blocks_before_apify(canary_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    monkeypatch.setattr(config, "APIFY_STOP_USD", 1.0)
    canary_env.usage.write_text(json.dumps({"actual_usd": 1.0}), encoding="utf-8")
    posts = make_posts()
    noti = mock.MagicMock()
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti):
        Prov.return_value.search_batched.return_value = posts
        res = S.run_scheduled_run(make_args(confirm=True))

    # zero Apify calls, zero Telegram calls
    assert Prov.return_value.search_batched.call_count == 0
    assert noti.send.call_count == 0

    # ledger status blocked_cost_limit
    assert res["status"] == "blocked_cost_limit"
    row = latest_row()
    assert row["status"] == "blocked_cost_limit"
    assert row["error_code"] == "cost_limit"

    # lock released, flags restored
    assert S.SchedulerLock(str(canary_env.lock)).status()["locked"] is False
    assert config.APIFY_LIVE_ENABLED == "false"
    assert config.TELEGRAM_SEND_ENABLED is False


# ===========================================================================
# Simulation 4 — Apify/provider failure after the run starts
# ===========================================================================
def test_canary_simulation_4_apify_failure_no_retry(canary_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    token = "bot12345:SECRETAPRILKEY"
    noti = mock.MagicMock()
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti):
        Prov.return_value.search_batched.side_effect = RuntimeError(f"apify actor failed {token}")
        res = S.run_scheduled_run(make_args(confirm=True))

    # no automatic retry: exactly one Apify attempt
    assert Prov.return_value.search_batched.call_count == 1
    # zero Telegram calls
    assert noti.send.call_count == 0

    # ledger records a sanitized failed state (no credentials stored)
    assert res["status"] == "failed"
    assert res["error_code"] == "apify_error"
    row = latest_row()
    assert row["status"] == "failed"
    assert token not in (row["sanitized_error"] or "")
    assert "[redacted]" in (row["sanitized_error"] or "")
    # No credential-like material leaked into the ledger blob. The genuine
    # secret is gone; only the redaction PLACEHOLDER (which literally contains
    # the word "token") remains, which is expected and safe.
    blob = json.dumps(row, default=str).lower()
    assert "secretaprilkey" not in blob
    assert "bot12345" not in blob
    assert "[redacted]" in blob

    # lock released, flags restored
    assert S.SchedulerLock(str(canary_env.lock)).status()["locked"] is False
    assert config.APIFY_LIVE_ENABLED == "false"
    assert config.TELEGRAM_SEND_ENABLED is False


# ===========================================================================
# Simulation 5 — Telegram failure after lead persistence + claim
# ===========================================================================
def test_canary_simulation_5_telegram_failure_after_claim(canary_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    # Only the genuine demand lead so the run reaches delivery.
    posts = [p for p in make_posts() if p["id"] == CANARY_DEMAND_ID]
    noti = mock.MagicMock()
    noti.send.side_effect = RuntimeError("telegram down")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti):
        Prov.return_value.search_batched.return_value = posts
        res = S.run_scheduled_run(make_args(confirm=True))

    # Telegram called exactly once, no automatic retry.
    assert noti.send.call_count == 1

    # Lead persistence remains valid: demand lead is in the DB.
    from rdsa import db as D
    c = D.connect(config.DB_PATH)
    persisted = c.execute("SELECT post_id, status FROM leads WHERE post_id=?",
                          (CANARY_DEMAND_ID,)).fetchone()
    c.close()
    assert persisted is not None
    assert persisted["post_id"] == CANARY_DEMAND_ID

    # Delivery is NOT marked sent; failure remains auditable.
    claims = delivery_claims()
    assert len(claims) == 1
    assert claims[0]["post_id"] == CANARY_DEMAND_ID
    assert claims[0]["status"] == "failed"

    # Run still completed (the RUN succeeded; only delivery failed).
    assert res["status"] == "completed"
    assert res["sent"] == 0

    # lock released, flags restored
    assert S.SchedulerLock(str(canary_env.lock)).status()["locked"] is False
    assert config.APIFY_LIVE_ENABLED == "false"
    assert config.TELEGRAM_SEND_ENABLED is False
