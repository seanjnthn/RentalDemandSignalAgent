import json
import pytest
from rdsa.apify_provider import ApifyBudgetExceeded, ApifyThreadsProvider, MonthlyUsageGuard


def test_budget_thresholds_and_month_reset(tmp_path):
    path = tmp_path / "usage.json"
    guard = MonthlyUsageGuard(path)
    assert guard.check_budget() == "ok"
    guard._state["estimated_usd"] = 4.00; assert guard.check_budget() == "warn"
    guard._state["estimated_usd"] = 4.75; assert guard.check_budget() == "stop"
    guard._state["month"] = "1900-01"; path.write_text(json.dumps(guard._state), encoding="utf-8")
    assert MonthlyUsageGuard(path).total_usd == 0


def test_search_refuses_at_stop(monkeypatch, tmp_path):
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "true")
    provider = ApifyThreadsProvider(token="not-used", session=object())
    provider.usage = MonthlyUsageGuard(tmp_path / "usage.json")
    provider.usage._state["estimated_usd"] = 4.75
    with pytest.raises(ApifyBudgetExceeded): provider.search(["q"])


def test_cost_report_keeps_run_and_monthly_values_distinct(tmp_path):
    guard = MonthlyUsageGuard(tmp_path / "usage.json", warn_at_usd=1.0, stop_at_usd=2.0)
    guard._state["actual_usd"] = 0.50
    guard._state["estimated_usd"] = 0.50
    guard.last_run_usd = 0.07
    assert guard.last_run_usd == 0.07
    assert guard.actual_usd == 0.50
    assert guard.remaining == 1.50
