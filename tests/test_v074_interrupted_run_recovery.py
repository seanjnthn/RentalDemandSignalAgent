"""v0.7.4 — Interrupted run recovery (offline; mocks only, no live calls).

Covers detection, fail-closed gating, explicit reconciliation, dashboard
observability, and data-integrity invariants. No Apify, no Telegram, no
synthetic inventory fallback, no Windows task, no historical mutation.

Key design points reflected in tests:
- interruption is inferred ONLY from (dead PID + no active lock + past grace),
  never from age alone and never for a run whose process/lock is active;
- the explicit terminal status is `interrupted` and is never auto-retried or
  treated as completed;
- reconciliation requires explicit confirmation, verifies PID dead + no active
  lock, records finished_at + interrupted + sanitized reason, never touches
  leads/alerts/delivery_claims/cost data, never calls Apify/Telegram, is
  idempotent, and refuses completed/active records;
- the scheduler-status dashboard surface stays read-only.
"""
from __future__ import annotations

import json
import os
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest

from rdsa import config
from rdsa import scheduler as S
from rdsa import db as D


DEAD_PID = 999999  # almost certainly not running


@pytest.fixture
def env(tmp_path, monkeypatch):
    db = tmp_path / "rdsa_test.sqlite3"
    lock = tmp_path / "scheduler.lock"
    usage = tmp_path / "apify_usage.json"
    usage.write_text(json.dumps({"month": "2026-07", "actual_usd": 1.0,
                                 "estimated_usd": 1.0, "runs": 0}), encoding="utf-8")
    real_csv = tmp_path / "inventory_real.csv"
    real_csv.write_text("inventory_id,title,location,property_type,bedrooms,price,period\n", encoding="utf-8")
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


def connect(env):
    return D.connect(str(env.db))


def insert_run(env, run_id, status, process_id=DEAD_PID, started_at=None,
               current_phase="starting", heartbeat_at=None):
    c = connect(env)
    if started_at is None:
        started_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    if heartbeat_at is None:
        heartbeat_at = started_at
    c.execute(
        "INSERT OR REPLACE INTO scheduled_runs("
        "run_id, trigger_type, started_at, status, process_id, current_phase, heartbeat_at) "
        "VALUES(?, 'daily_schedule', ?, ?, ?, ?, ?)",
        (run_id, started_at, status, process_id, current_phase, heartbeat_at),
    )
    c.commit()
    c.close()


# ---------------------------------------------------------------------------
# Idempotent migration
# ---------------------------------------------------------------------------
def test_idempotent_migration_adds_progress_columns(env):
    c = connect(env)
    S.migrate_ledger(c)
    cols1 = {r[1] for r in c.execute("PRAGMA table_info(scheduled_runs)")}
    S.migrate_ledger(c)
    cols2 = {r[1] for r in c.execute("PRAGMA table_info(scheduled_runs)")}
    assert cols1 == cols2
    assert {"current_phase", "heartbeat_at", "interruption_reason"} <= cols1


def test_record_run_start_sets_starting_phase(env):
    c = connect(env)
    S.record_run_start(c, "run-x", "daily_schedule", DEAD_PID, False)
    row = S.latest_run(c)
    assert row["status"] == "starting"
    assert row["current_phase"] == "starting"
    assert row["heartbeat_at"]
    assert row["process_id"] == DEAD_PID


def test_update_run_progress_is_idempotent(env):
    c = connect(env)
    S.record_run_start(c, "run-x", "daily_schedule", DEAD_PID, False)
    S.update_run_progress(c, "run-x", "preflight")
    S.update_run_progress(c, "run-x", "actor_started")
    row = S.latest_run(c)
    assert row["current_phase"] == "actor_started"
    assert row["heartbeat_at"]
    # progress updates never set finished_at
    assert row["finished_at"] is None


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def test_dead_pid_no_lock_elapsed_grace_is_candidate(env):
    insert_run(env, "run-dead", "starting", process_id=DEAD_PID,
               started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    c = connect(env)
    cand = S.detect_interrupted_runs(c, lock=S.SchedulerLock(str(env.lock)),
                                     grace_seconds=3600)
    assert [r["run_id"] for r in cand] == ["run-dead"]


def test_live_pid_not_reconciled(env):
    insert_run(env, "run-live", "starting", process_id=os.getpid(),
               started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    c = connect(env)
    cand = S.detect_interrupted_runs(c, lock=S.SchedulerLock(str(env.lock)),
                                     grace_seconds=3600)
    assert cand == []


def test_active_lock_not_reconciled(env):
    # Acquire a real lock (pid = this process, alive) for run-lock.
    lock = S.SchedulerLock(str(env.lock))
    assert lock.acquire("run-lock")
    try:
        insert_run(env, "run-lock", "starting", process_id=DEAD_PID,
                   started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
        c = connect(env)
        cand = S.detect_interrupted_runs(c, lock=lock, grace_seconds=3600)
        assert cand == []
    finally:
        lock.release()


def test_age_alone_insufficient(env):
    # Dead pid + no lock BUT started within grace window → not a candidate.
    insert_run(env, "run-recent", "starting", process_id=DEAD_PID,
               started_at=datetime.now(timezone.utc).isoformat())
    c = connect(env)
    cand = S.detect_interrupted_runs(c, lock=S.SchedulerLock(str(env.lock)),
                                     grace_seconds=3600)
    assert cand == []


def test_terminal_status_never_candidate(env):
    for st in ("completed", "failed", "blocked_lock", "refused", "interrupted"):
        insert_run(env, f"run-{st}", st, process_id=DEAD_PID,
                   started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    c = connect(env)
    cand = S.detect_interrupted_runs(c, lock=S.SchedulerLock(str(env.lock)),
                                     grace_seconds=3600)
    assert cand == []


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------
def seed_historical_data(env):
    """Seed leads/alerts/delivery_claims/cost that must remain untouched."""
    c = connect(env)
    c.execute(
        "INSERT INTO leads(post_id,source,source_url,author_username,post_timestamp,"
        "fetched_at,raw_text,lead_class,lead_score,status) "
        "VALUES('lead-1','threads','https://x','u','2026-07-01T00:00:00+00:00',"
        "'2026-07-01T00:00:00+00:00','need apartment','hot_lead',90,'new')")
    c.execute("INSERT INTO alerts(post_id,sent_at,channel) VALUES('lead-1','2026-07-01T00:00:00+00:00','telegram')")
    c.execute("INSERT INTO delivery_claims(post_id,channel,status,claimed_at,sent_at) "
              "VALUES('lead-1','telegram','sent','2026-07-01T00:00:00+00:00','2026-07-01T00:00:00+00:00')")
    c.commit(); c.close()
    env.usage.write_text(json.dumps({"actual_usd": 2.5, "estimated_usd": 2.5, "runs": 3}), encoding="utf-8")


def counts(env):
    c = connect(env)
    leads = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    alerts = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    claims = c.execute("SELECT COUNT(*) FROM delivery_claims").fetchone()[0]
    usage = json.loads(Path(env.usage).read_text(encoding="utf-8"))
    c.close()
    return {"leads": leads, "alerts": alerts, "claims": claims, "usage": usage}


def test_missing_confirmation_refuses(env):
    insert_run(env, "run-x", "starting")
    c = connect(env)
    res = S.reconcile_run(c, "run-x", confirm=False)
    assert res["reconciled"] is False
    assert res["reason_refused"] == "missing_confirmation"
    assert S.latest_run(c)["status"] == "starting"


def test_explicit_reconciliation_terminal_interrupted(env):
    seed_historical_data(env)
    before = counts(env)
    insert_run(env, "run-x", "starting", current_phase="actor_started")
    c = connect(env)
    res = S.reconcile_run(c, "run-x", confirm=True)
    assert res["reconciled"] is True
    assert res["status"] == "interrupted"
    assert res["finished_at"]
    assert res["interruption_reason"]
    row = c.execute("SELECT status,finished_at,interruption_reason FROM scheduled_runs WHERE run_id=?",
                    ("run-x",)).fetchone()
    assert row["status"] == "interrupted"
    assert row["finished_at"]
    assert row["interruption_reason"]
    # historical data untouched
    assert counts(env) == before


def test_reconciliation_does_not_call_apify_or_telegram(env):
    insert_run(env, "run-x", "starting")
    c = connect(env)
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.scheduler.TelegramNotifier") as Noti, \
         mock.patch("rdsa.scheduler.send_lead_cards") as send_cards:
        S.reconcile_run(c, "run-x", confirm=True)
    Prov.assert_not_called()
    Noti.assert_not_called()
    send_cards.assert_not_called()


def test_second_reconciliation_no_mutation(env):
    insert_run(env, "run-x", "starting")
    c = connect(env)
    first = S.reconcile_run(c, "run-x", confirm=True)
    finished_first = first["finished_at"]
    second = S.reconcile_run(c, "run-x", confirm=True)
    assert second["reconciled"] is False
    assert second["already_terminal"] is True
    assert second["idempotent"] is True
    # finished_at unchanged by the second (no-op) call
    row = c.execute("SELECT finished_at FROM scheduled_runs WHERE run_id=?", ("run-x",)).fetchone()
    assert row["finished_at"] == finished_first


def test_completed_run_refused(env):
    insert_run(env, "run-done", "completed")
    c = connect(env)
    res = S.reconcile_run(c, "run-done", confirm=True)
    assert res["reconciled"] is False
    assert res["already_terminal"] is True
    assert S.latest_run(c)["status"] == "completed"


def test_reconcile_active_process_refused(env):
    insert_run(env, "run-live", "starting", process_id=os.getpid())
    c = connect(env)
    res = S.reconcile_run(c, "run-live", confirm=True)
    assert res["reconciled"] is False
    assert res["reason_refused"] == "process_alive"


def test_reconcile_active_lock_refused(env):
    lock = S.SchedulerLock(str(env.lock))
    assert lock.acquire("run-lock")
    try:
        insert_run(env, "run-lock", "starting", process_id=DEAD_PID,
                   started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
        c = connect(env)
        res = S.reconcile_run(c, "run-lock", confirm=True, lock=lock)
        assert res["reconciled"] is False
        assert res["reason_refused"] == "active_lock"
    finally:
        lock.release()


def test_reconcile_sanitizes_reason(env):
    insert_run(env, "run-x", "starting")
    c = connect(env)
    res = S.reconcile_run(c, "run-x", confirm=True,
                          reason="token bot123:SECRET and C:\\Users\\x path")
    assert res["reconciled"] is True
    assert "bot123:SECRET" not in res["interruption_reason"]
    assert "[REDACTED_TOKEN]" in res["interruption_reason"]


# ---------------------------------------------------------------------------
# Fail-closed: new scheduled run blocked while unresolved run exists
# ---------------------------------------------------------------------------
def test_new_scheduled_run_blocked_while_unresolved(env, monkeypatch):
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", True)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)
    # Insert an interruption candidate (dead pid, no lock, old).
    insert_run(env, "run-stuck", "starting", process_id=DEAD_PID,
               started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    args = types.SimpleNamespace(confirm_scheduled_run=True, trigger_type="daily_schedule")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov:
        res = S.run_scheduled_run(args)
    assert res["status"] == "refused"
    assert "run-stuck" in res["message"]
    Prov.return_value.search_batched.assert_not_called()


def test_no_live_calls_when_blocked_by_interruption(env, monkeypatch):
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", True)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)
    insert_run(env, "run-stuck", "starting", process_id=DEAD_PID,
               started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    args = types.SimpleNamespace(confirm_scheduled_run=True, trigger_type="daily_schedule")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.scheduler.TelegramNotifier") as Noti:
        S.run_scheduled_run(args)
    Prov.assert_not_called()
    Noti.assert_not_called()


# ---------------------------------------------------------------------------
# Dashboard observability (read-only)
# ---------------------------------------------------------------------------
def test_dashboard_shows_required_interrupted(env):
    insert_run(env, "run-stuck", "starting", current_phase="actor_started",
               started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    from rdsa.dashboard_repository import get_scheduler_status
    status = get_scheduler_status(str(env.db))
    assert status["code_readiness"] == "ready"
    recs = status["interrupted_runs"]
    assert len(recs) == 1
    r = recs[0]
    assert r["run_id"] == "run-stuck"
    assert r["current_phase"] == "actor_started"
    assert r["heartbeat_at"]
    assert r["reconciliation"] == "required"
    assert r["interruption_reason"] is None


def test_dashboard_shows_completed_interrupted(env):
    insert_run(env, "run-done", "interrupted",
               started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    c = connect(env)
    c.execute("UPDATE scheduled_runs SET interruption_reason=?, finished_at=? WHERE run_id=?",
              ("Process terminated by OS while status=starting; last known phase=starting.",
               datetime.now(timezone.utc).isoformat(), "run-done"))
    c.commit(); c.close()
    from rdsa.dashboard_repository import get_scheduler_status
    recs = get_scheduler_status(str(env.db))["interrupted_runs"]
    assert len(recs) == 1
    assert recs[0]["reconciliation"] == "completed"
    assert "Process terminated" in (recs[0]["interruption_reason"] or "")


def test_scheduler_status_remains_read_only(env):
    insert_run(env, "run-stuck", "starting",
               started_at=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat())
    from rdsa.dashboard_repository import get_scheduler_status
    # Multiple reads must not mutate the ledger.
    get_scheduler_status(str(env.db))
    get_scheduler_status(str(env.db))
    c = connect(env)
    row = c.execute("SELECT status FROM scheduled_runs WHERE run_id=?", ("run-stuck",)).fetchone()
    assert row["status"] == "starting"


def test_cli_scheduler_reconcile_wired(env, monkeypatch):
    insert_run(env, "run-x", "starting")
    from rdsa import cli
    with mock.patch("rdsa.scheduler.reconcile_run",
                    return_value={"reconciled": True}) as rec:
        cli.main(["scheduler-reconcile", "--run-id", "run-x", "--confirm-reconcile"])
    assert rec.called
    # Signature: reconcile_run(c, run_id, *, confirm, lock, reason)
    assert rec.call_args.args[1] == "run-x"
    assert rec.call_args.kwargs.get("confirm") is True


def test_cli_scheduler_reconcile_refuses_without_confirm(env, monkeypatch):
    insert_run(env, "run-x", "starting")
    from rdsa import cli
    with mock.patch("rdsa.scheduler.reconcile_run",
                    return_value={"reconciled": False}) as rec:
        cli.main(["scheduler-reconcile", "--run-id", "run-x"])
    assert rec.called
    assert rec.call_args.kwargs.get("confirm") is False


def test_reconcile_works_on_prepatch_schema_missing_columns(env):
    """Production DBs predating v0.7.4 have scheduled_runs WITHOUT the new
    progress columns. reconcile_run must idempotently ensure columns exist and
    still record the interrupted terminal state (no row-data mutation of other
    tables)."""
    c = connect(env)
    c.execute("DROP TABLE IF EXISTS scheduled_runs")
    c.execute(
        "CREATE TABLE scheduled_runs("
        "run_id TEXT PRIMARY KEY, trigger_type TEXT NOT NULL, started_at TEXT NOT NULL, "
        "finished_at TEXT, status TEXT NOT NULL, process_id INTEGER)")
    c.execute("INSERT INTO scheduled_runs(run_id, trigger_type, started_at, status, process_id) "
              "VALUES('run-old', 'daily_schedule', ?, 'starting', ?)",
              ((datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(), DEAD_PID))
    c.commit()
    res = S.reconcile_run(c, "run-old", confirm=True)
    assert res["reconciled"] is True
    cols = {r[1] for r in c.execute("PRAGMA table_info(scheduled_runs)")}
    assert {"current_phase", "heartbeat_at", "interruption_reason"} <= cols
    row = c.execute("SELECT status, interruption_reason, finished_at FROM scheduled_runs "
                    "WHERE run_id='run-old'").fetchone()
    assert row["status"] == "interrupted"
    assert row["finished_at"]


def test_detect_interrupted_schema_agnostic(env):
    """detect_interrupted_runs must work on a pre-patch schema (no progress
    columns) and still flag a dead-pid / no-lock / past-grace run."""
    c = connect(env)
    c.execute("DROP TABLE IF EXISTS scheduled_runs")
    c.execute(
        "CREATE TABLE scheduled_runs("
        "run_id TEXT PRIMARY KEY, trigger_type TEXT NOT NULL, started_at TEXT NOT NULL, "
        "finished_at TEXT, status TEXT NOT NULL, process_id INTEGER)")
    c.execute("INSERT INTO scheduled_runs(run_id, trigger_type, started_at, status, process_id) "
              "VALUES('run-old', 'daily_schedule', ?, 'starting', ?)",
              ((datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(), DEAD_PID))
    c.commit()
    cand = S.detect_interrupted_runs(c, lock=S.SchedulerLock(str(env.lock)),
                                     grace_seconds=3600)
    assert [r["run_id"] for r in cand] == ["run-old"]
    # The new progress columns are read via .get() and tolerated when absent.
    assert cand[0].get("current_phase") is None
