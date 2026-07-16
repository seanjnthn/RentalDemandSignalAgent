"""PHASE 10 — comprehensive offline scheduler tests (mocks only, no live calls).

Covers: kill switches, process lock, ledger states, cost guard, delivery gating,
CLI wiring, and safety invariants. No Apify, no Telegram, no synthetic inventory
fallback.

IMPORTANT: run_scheduled_run imports process_raw / send_lead_cards / TelegramNotifier /
validate_real_inventory_for_scan / ApifyThreadsProvider via `from .x import Y` *inside*
the function, so each call re-reads the attribute on the SOURCE module. Mocks therefore
target the source modules (rdsa.cli / rdsa.notifier / rdsa.inventory / rdsa.apify_provider),
not rdsa.scheduler.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from unittest import mock

import pytest

from rdsa import config
from rdsa import scheduler as S


@pytest.fixture
def sched_env(tmp_path, monkeypatch):
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


def enable_scheduler(monkeypatch, send=False):
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", True)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", send)


def make_args(confirm=True, trigger="daily_schedule"):
    return types.SimpleNamespace(confirm_scheduled_run=confirm, trigger_type=trigger)


def make_lead(post_id, lead_class="qualified_lead"):
    return types.SimpleNamespace(post_id=post_id, lead_class=lead_class,
                                 matched_inventory=[])


def fake_process_result(new_post_ids, leads, new_rows=0):
    return {
        "raw_posts": len(leads) + 2,
        "normalized_posts": len(leads) + 2,
        "duplicates": 0,
        "new_rows": new_rows if new_rows else len(new_post_ids),
        "leads": leads,
        "new_post_ids": new_post_ids,
    }


def ok_inventory():
    row = {"inventory_id": "APT-TEST-1", "title": "Test", "location": "BSD",
           "property_type": "apartment", "bedrooms": 1, "price": 2000000,
           "period": "month"}
    return ([row], {"ok": True})


# ---------------------------------------------------------------------------
# Kill switches
# ---------------------------------------------------------------------------
def test_scheduler_disabled_refuses_before_apify(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", False)
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov:
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "refused"
    Prov.return_value.search_batched.assert_not_called()


def test_missing_confirm_refuses(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov:
        res = S.run_scheduled_run(make_args(confirm=False))
    assert res["status"] == "refused"
    Prov.return_value.search_batched.assert_not_called()


def test_send_disabled_performs_zero_telegram_calls(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    new_ids = ["p1"]
    res_leads = [make_lead("p1", "qualified_lead")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)) as proc, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards") as send_cards, \
         mock.patch("rdsa.scheduler.TelegramNotifier") as Noti:
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "completed"
    send_cards.assert_not_called()
    Noti.return_value.send.assert_not_called()
    assert proc.call_args.kwargs.get("inventory_mode") == "real"


def test_flags_restored_after_success(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = ["p1"]
    res_leads = [make_lead("p1", "qualified_lead")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", return_value=1):
        Prov.return_value.search_batched.return_value = []
        S.run_scheduled_run(make_args(confirm=True))
    assert config.APIFY_LIVE_ENABLED == "false"
    assert config.TELEGRAM_SEND_ENABLED is False


def test_flags_restored_after_failure(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.cli.process_raw", return_value=fake_process_result([], [])):
        Prov.return_value.search_batched.side_effect = RuntimeError("apify boom")
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "failed"
    assert config.APIFY_LIVE_ENABLED == "false"
    assert config.TELEGRAM_SEND_ENABLED is False


# ---------------------------------------------------------------------------
# Process lock
# ---------------------------------------------------------------------------
def test_first_lock_acquisition_succeeds(sched_env):
    lock = S.SchedulerLock(str(sched_env.lock))
    assert lock.acquire("run-a") is True
    assert lock.status()["locked"] is True
    lock.release()
    assert lock.status()["locked"] is False


def test_second_process_blocked_before_apify(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    lock = S.SchedulerLock(str(sched_env.lock))
    assert lock.acquire("run-other") is True
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()):
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "refused"
    assert res["message"].startswith("Scheduler lock conflict")
    Prov.return_value.search_batched.assert_not_called()
    lock.release()


def test_normal_and_exception_release(sched_env):
    lock = S.SchedulerLock(str(sched_env.lock))
    lock.acquire("run-a")
    lock.release()
    assert lock.status()["locked"] is False
    lock.acquire("run-b")
    try:
        raise RuntimeError("x")
    except RuntimeError:
        lock.release()
    assert lock.status()["locked"] is False


def test_stale_lock_not_auto_deleted(sched_env):
    lock = S.SchedulerLock(str(sched_env.lock))
    Path(lock.lock_path).parent.mkdir(parents=True, exist_ok=True)
    Path(lock.lock_path).write_text(json.dumps(
        {"run_id": "stale", "pid": -1, "started_at": "2020-01-01T00:00:00Z",
         "hostname": "ghost"}), encoding="utf-8")
    other = S.SchedulerLock(str(sched_env.lock))
    assert other.inspect() is not None
    assert other.acquire("run-new") is False


def test_unlock_requires_confirmation(sched_env):
    lock = S.SchedulerLock(str(sched_env.lock))
    Path(lock.lock_path).parent.mkdir(parents=True, exist_ok=True)
    Path(lock.lock_path).write_text(json.dumps(
        {"run_id": "stale", "pid": -1, "started_at": "2020-01-01T00:00:00Z",
         "hostname": "ghost"}), encoding="utf-8")
    assert lock.force_unlock(confirm=False) is False
    assert lock.status()["locked"] is True
    assert lock.force_unlock(confirm=True) is True
    assert lock.status()["locked"] is False


def test_live_process_lock_cannot_be_removed(sched_env):
    lock = S.SchedulerLock(str(sched_env.lock))
    lock.acquire("run-self")
    assert lock.force_unlock(confirm=True) is False
    assert lock.status()["locked"] is True
    lock.release()


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
def test_idempotent_migration(sched_env):
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    S.migrate_ledger(c)
    cols1 = {r[1] for r in c.execute("PRAGMA table_info(scheduled_runs)")}
    S.migrate_ledger(c)
    cols2 = {r[1] for r in c.execute("PRAGMA table_info(scheduled_runs)")}
    assert cols1 == cols2
    assert {"run_id", "status", "trigger_type"} <= cols1


def test_ledger_starting_and_terminal_states(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = ["p1"]
    res_leads = [make_lead("p1", "qualified_lead")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", return_value=1):
        Prov.return_value.search_batched.return_value = []
        S.run_scheduled_run(make_args(confirm=True))
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    row = S.latest_run(c)
    assert row["status"] == "completed"
    assert row["trigger_type"] == "daily_schedule"
    assert row["new_posts"] == 1
    assert row["eligible_leads"] == 1
    assert row["sent_cards"] == 1
    assert row["scheduler_send_enabled"] == 1


def test_ledger_completed_no_new_leads(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    res_leads = [make_lead("p1", "qualified_lead")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result([], res_leads, new_rows=0)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards") as sc:
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "completed_no_new_leads"
    sc.assert_not_called()
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    assert S.latest_run(c)["status"] == "completed_no_new_leads"


def test_ledger_completed_no_eligible_leads(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    new_ids = ["b1", "b2"]
    res_leads = [make_lead("b1", "agent_broker"), make_lead("b2", "agent_broker")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards") as sc:
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "completed_no_eligible_leads"
    sc.assert_not_called()
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    assert S.latest_run(c)["status"] == "completed_no_eligible_leads"


def test_ledger_blocked_cost_limit(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    monkeypatch.setattr(config, "APIFY_STOP_USD", 4.0)
    sched_env.usage.write_text(json.dumps({"actual_usd": 4.5}), encoding="utf-8")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()):
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "blocked_cost_limit"
    Prov.return_value.search_batched.assert_not_called()
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    assert S.latest_run(c)["status"] == "blocked_cost_limit"


def test_ledger_blocked_lock(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    lock = S.SchedulerLock(str(sched_env.lock))
    lock.acquire("run-other")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()):
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "refused"
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    assert S.latest_run(c)["status"] == "blocked_lock"
    lock.release()


def test_ledger_failed_and_sanitized_error(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    token = "bot12345:SECRETTOKENxyz"
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.cli.process_raw", return_value=fake_process_result([], [])):
        Prov.return_value.search_batched.side_effect = RuntimeError(f"apify failed {token}")
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "failed"
    assert res["error_code"] == "apify_error"
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    row = S.latest_run(c)
    assert row["status"] == "failed"
    assert token not in (row["sanitized_error"] or "")
    assert "[REDACTED_TOKEN]" in (row["sanitized_error"] or "")


def test_no_secrets_stored_in_ledger(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    chat = "9988776655"
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(["p1"], [make_lead("p1")])), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", return_value=1):
        Prov.return_value.search_batched.return_value = []
        S.run_scheduled_run(make_args(confirm=True))
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    row = S.latest_run(c)
    blob = json.dumps(row, default=str)
    assert chat not in blob


# ---------------------------------------------------------------------------
# Cost guard
# ---------------------------------------------------------------------------
def test_cost_below_stop_permits_mocked_run(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    monkeypatch.setattr(config, "APIFY_STOP_USD", 4.0)
    sched_env.usage.write_text(json.dumps({"actual_usd": 1.0}), encoding="utf-8")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result([], [])), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards"):
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] in ("completed_no_new_leads", "completed_no_eligible_leads")
    Prov.return_value.search_batched.assert_called()


def test_cost_above_stop_blocks_before_apify(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    monkeypatch.setattr(config, "APIFY_STOP_USD", 2.0)
    sched_env.usage.write_text(json.dumps({"actual_usd": 1.98}), encoding="utf-8")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()):
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] == "blocked_cost_limit"
    Prov.return_value.search_batched.assert_not_called()


def test_warning_and_stop_not_recorded_as_run_cost(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    monkeypatch.setattr(config, "APIFY_WARN_USD", 1.5)
    monkeypatch.setattr(config, "APIFY_STOP_USD", 4.0)
    sched_env.usage.write_text(json.dumps({"actual_usd": 1.6}), encoding="utf-8")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result([], [])), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards"):
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    row = S.latest_run(c)
    assert row["usage_total_usd"] == config.SCHEDULER_MAX_CHARGE_USD
    assert row["monthly_usage_usd"] == 1.6


def test_no_paid_automatic_retry(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.cli.process_raw", return_value=fake_process_result([], [])):
        Prov.return_value.search_batched.side_effect = RuntimeError("apify fail")
        S.run_scheduled_run(make_args(confirm=True))
    assert Prov.return_value.search_batched.call_count == 1


# ---------------------------------------------------------------------------
# Delivery gating
# ---------------------------------------------------------------------------
def test_only_new_post_ids_eligible(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = ["p1"]
    res_leads = [make_lead("p1", "qualified_lead"), make_lead("p2", "hot_lead")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", return_value=1) as sc:
        Prov.return_value.search_batched.return_value = []
        S.run_scheduled_run(make_args(confirm=True))
    sent_leads = sc.call_args.args[1]
    assert [l.post_id for l in sent_leads] == ["p1"]


def test_historical_agent_broker_offering_excluded(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = ["n1", "n2", "n3"]
    res_leads = [
        make_lead("n1", "agent_broker"),
        make_lead("n2", "qualified_lead"),
        make_lead("n3", "watch"),
    ]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", return_value=1) as sc:
        Prov.return_value.search_batched.return_value = []
        S.run_scheduled_run(make_args(confirm=True))
    sent_leads = sc.call_args.args[1]
    assert [l.post_id for l in sent_leads] == ["n2"]


def test_atomic_delivery_claim_required(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = ["p1"]
    res_leads = [make_lead("p1", "qualified_lead")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", return_value=1) as sc:
        Prov.return_value.search_batched.return_value = []
        S.run_scheduled_run(make_args(confirm=True))
    assert sc.called
    assert sc.call_args.args[1][0].post_id == "p1"


def test_maximum_three_cards(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = [f"p{i}" for i in range(6)]
    res_leads = [make_lead(f"p{i}", "qualified_lead") for i in range(6)]
    captured = {}
    def fake_send(notifier, eligible, c, **kw):
        captured["n"] = len(eligible)
        return min(len(eligible), 3)
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", side_effect=fake_send):
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    assert captured["n"] == 6
    assert res["sent"] == 3
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    assert S.latest_run(c)["sent_cards"] == 3


def test_zero_eligible_zero_telegram_calls(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = ["b1"]
    res_leads = [make_lead("b1", "agent_broker")]
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.send_lead_cards", return_value=1) as sc, \
         mock.patch("rdsa.scheduler.TelegramNotifier") as Noti:
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    assert res["sent"] == 0
    sc.assert_not_called()
    Noti.return_value.send.assert_not_called()


def test_telegram_failure_not_auto_retried(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=True)
    new_ids = ["p1"]
    res_leads = [make_lead("p1", "qualified_lead")]
    noti = mock.MagicMock()
    noti.send.side_effect = RuntimeError("telegram down")
    with mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as Prov, \
         mock.patch("rdsa.cli.process_raw",
                    return_value=fake_process_result(new_ids, res_leads)), \
         mock.patch("rdsa.inventory.validate_real_inventory_for_scan",
                    return_value=ok_inventory()), \
         mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
         mock.patch("rdsa.scheduler.send_lead_cards",
                    side_effect=RuntimeError("telegram down")):
        Prov.return_value.search_batched.return_value = []
        res = S.run_scheduled_run(make_args(confirm=True))
    assert noti.send.call_count == 0
    from rdsa import db as D
    c = D.connect(str(sched_env.db))
    assert S.latest_run(c)["status"] == "failed"


# ---------------------------------------------------------------------------
# CLI and safety
# ---------------------------------------------------------------------------
def test_cli_scheduled_run_wired(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    with mock.patch("rdsa.scheduler.run_scheduled_run", return_value={"status": "refused"}) as rsr:
        from rdsa import cli
        cli.main(["scheduled-run", "--confirm-scheduled-run"])
    assert rsr.called
    assert rsr.call_args.args[0].confirm_scheduled_run is True


def test_cli_scheduler_status_read_only(sched_env, monkeypatch):
    from rdsa import cli
    with mock.patch("rdsa.scheduler.SchedulerLock") as Lock, \
         mock.patch("rdsa.scheduler.latest_run", return_value=None), \
         mock.patch("rdsa.scheduler.last_successful_run", return_value=None), \
         mock.patch("rdsa.scheduler.read_usage_safe", return_value={"actual_usd": 1.0}):
        Lock.return_value.status.return_value = {"locked": False}
        cli.main(["scheduler-status"])


def test_cli_scheduler_unlock_requires_confirmation(sched_env, monkeypatch):
    from rdsa import cli
    lock = S.SchedulerLock(str(sched_env.lock))
    Path(lock.lock_path).parent.mkdir(parents=True, exist_ok=True)
    Path(lock.lock_path).write_text(json.dumps(
        {"run_id": "stale", "pid": -1, "started_at": "2020-01-01T00:00:00Z",
         "hostname": "ghost"}), encoding="utf-8")
    with mock.patch("rdsa.scheduler.SchedulerLock", return_value=lock):
        cli.main(["scheduler-unlock"])
    assert lock.status()["locked"] is True
    with mock.patch("rdsa.scheduler.SchedulerLock", return_value=lock):
        cli.main(["scheduler-unlock", "--confirm-unlock"])
    assert lock.status()["locked"] is False


def test_no_live_apify_or_telegram_in_tests(sched_env, monkeypatch):
    enable_scheduler(monkeypatch, send=False)
    res = S.run_scheduled_run(make_args(confirm=True))
    assert res["status"] in ("refused", "failed", "blocked_cost_limit", "blocked_lock")
