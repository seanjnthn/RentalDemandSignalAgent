from __future__ import annotations

import os
from pathlib import Path

import pytest

from dashboard import operator_adapters as OA
from dashboard import operator_service as OS
from rdsa import config as C


def _valid_task(**overrides):
    args = (
        f'-NoProfile -ExecutionPolicy Bypass -File "{OA.APPROVED_LAUNCHER}" '
        f'-RepoRoot "{OA.APPROVED_WORKDIR}" -TriggerMode daily_schedule -ConfirmRun'
    )
    task = {
        "name": OA.APPROVED_TASK_NAME,
        "execute": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        "arguments": args,
        "working_directory": str(OA.APPROVED_WORKDIR),
        "enabled": False,
        "state": "Disabled",
        "trigger_mode": "daily_schedule",
        "next_run": "",
        "cadence": "daily",
    }
    task.update(overrides)
    return task


@pytest.fixture(autouse=True)
def _runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RUNTIME_DIR", str(tmp_path / "runtime"))
    OS.reset_opt_in()
    yield
    OS.reset_opt_in()


def test_feature_flag_false_fail_closed(monkeypatch):
    monkeypatch.delenv(OA.FEATURE_FLAG_ENV, raising=False)
    assert OA.feature_flag_enabled() is False
    ports = OA.connected_ports_if_enabled()
    assert OS.get_manual_run_readiness(ports).reasons == ["operator_controls_not_connected"]


def test_manual_adapter_missing_confirmation_cli():
    result = OA.execute_dashboard_manual_scan("op-missing", confirm_run=False)
    assert result["status"] == "refused"
    assert result["message"] == "--confirm-run required"


def test_manual_adapter_async_launch_accepted_once(monkeypatch, tmp_path):
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append((cmd, kwargs))

    monkeypatch.setenv(OA.FEATURE_FLAG_ENV, "true")
    monkeypatch.setattr(C, "APIFY_API_TOKEN", "present")
    monkeypatch.setattr(OA.OS, "_default_readiness", lambda: {"ready": True, "reasons": []})
    adapter = OA.RealManualScanAdapter(popen=FakePopen, python_path=Path(os.sys.executable))
    args = type("A", (), {"operation_id": "op-once", "trigger_type": "dashboard_manual"})()

    first = adapter(args)
    second = adapter(args)

    assert first["status"] == "accepted"
    assert second["status"] == "accepted"
    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert cmd[:3] == [str(Path(os.sys.executable)), "-m", "rdsa.cli"]
    assert cmd[3:] == ["dashboard-manual-scan", "--operation-id", "op-once", "--confirm-run"]
    assert kwargs["env"]["RDSA_SCHEDULER_ENABLED"] == "true"
    assert kwargs["env"]["RDSA_SCHEDULER_SEND_ENABLED"] == "false"
    assert kwargs["env"]["RDSA_TELEGRAM_SEND_ENABLED"] == "false"
    assert "PYTHONPATH" not in kwargs["env"]
    assert os.environ.get("RDSA_SCHEDULER_ENABLED", "").lower() != "true"


def test_manual_adapter_dead_child_before_run_id_does_not_retry(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append((cmd, kwargs))

    monkeypatch.setenv(OA.FEATURE_FLAG_ENV, "true")
    monkeypatch.setattr(C, "APIFY_API_TOKEN", "present")
    monkeypatch.setattr(OA.OS, "_default_readiness", lambda: {"ready": True, "reasons": []})
    adapter = OA.RealManualScanAdapter(popen=FakePopen, python_path=Path(os.sys.executable))
    args = type("A", (), {"operation_id": "op-dead-child", "trigger_type": "dashboard_manual"})()

    accepted = adapter(args)
    assert accepted["status"] == "accepted"
    # Simulate an operator-audit update from an observed child failure before a
    # scheduler run_id exists. The same op_id must return the existing state and
    # must not spawn a replacement child.
    OA._audit_row("op-dead-child", "dashboard_manual_scan", "failed", error_code="child_exit")
    duplicate = adapter(args)

    assert duplicate["status"] == "failed"
    assert len(calls) == 1


def test_manual_adapter_interrupted_child_does_not_retry(monkeypatch):
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            calls.append((cmd, kwargs))

    monkeypatch.setenv(OA.FEATURE_FLAG_ENV, "true")
    monkeypatch.setattr(C, "APIFY_API_TOKEN", "present")
    monkeypatch.setattr(OA.OS, "_default_readiness", lambda: {"ready": True, "reasons": []})
    OA._audit_row("op-interrupted", "dashboard_manual_scan", "interrupted")
    adapter = OA.RealManualScanAdapter(popen=FakePopen, python_path=Path(os.sys.executable))
    args = type("A", (), {"operation_id": "op-interrupted", "trigger_type": "dashboard_manual"})()

    result = adapter(args)

    assert result["status"] == "interrupted"
    assert calls == []


def test_manual_cli_revalidates_and_zero_retry(monkeypatch):
    attempts = {"n": 0}

    def fake_run(args):
        attempts["n"] += 1
        assert args.trigger_type == "dashboard_manual"
        assert args.confirm_scheduled_run is True
        return {"status": "blocked_cost_limit", "run_id": "run-cost"}

    monkeypatch.setattr(OA.S, "run_scheduled_run", fake_run)
    result = OA.execute_dashboard_manual_scan("op-cost", confirm_run=True)
    repeat = OA.execute_dashboard_manual_scan("op-cost", confirm_run=True)
    assert result["status"] == "blocked_cost_limit"
    assert repeat["idempotent"] is True
    assert attempts["n"] == 1


def test_manual_cli_telegram_false_and_env_restored(monkeypatch):
    before = dict(os.environ)
    monkeypatch.setenv("APIFY_LIVE_ENABLED", "keep")
    monkeypatch.setenv("RDSA_TELEGRAM_SEND_ENABLED", "keep")
    cfg_before = (C.TELEGRAM_SEND_ENABLED, C.SCHEDULER_SEND_ENABLED, C.SCHEDULER_ENABLED)

    def fake_run(args):
        assert C.SCHEDULER_ENABLED is True
        assert C.SCHEDULER_SEND_ENABLED is False
        assert os.environ["RDSA_SCHEDULER_ENABLED"] == "true"
        assert os.environ["RDSA_SCHEDULER_SEND_ENABLED"] == "false"
        assert os.environ["RDSA_TELEGRAM_SEND_ENABLED"] == "false"
        return {"status": "completed_no_new_leads", "run_id": "run-ok", "sent": 0}

    monkeypatch.setattr(OA.S, "run_scheduled_run", fake_run)
    result = OA.execute_dashboard_manual_scan("op-env", confirm_run=True)
    assert result["run_id"] == "run-ok"
    assert os.environ["APIFY_LIVE_ENABLED"] == "keep"
    assert os.environ["RDSA_TELEGRAM_SEND_ENABLED"] == "keep"
    assert "RDSA_SCHEDULER_ENABLED" not in os.environ or os.environ["RDSA_SCHEDULER_ENABLED"] != "true"
    assert (C.TELEGRAM_SEND_ENABLED, C.SCHEDULER_SEND_ENABLED, C.SCHEDULER_ENABLED) == cfg_before
    for key, value in before.items():
        if key not in {"APIFY_LIVE_ENABLED", "RDSA_TELEGRAM_SEND_ENABLED"}:
            assert os.environ.get(key) == value


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("execute", r"C:\Python\python.exe", "execute"),
        ("arguments", "-NoProfile -File C:\\wrong.ps1 -RepoRoot C:\\repo -TriggerMode daily_schedule -ConfirmRun", "launcher_script_exact"),
        ("arguments", f'-NoProfile -File "{OA.APPROVED_LAUNCHER}" -RepoRoot C:\\wrong -TriggerMode daily_schedule -ConfirmRun', "repo_root"),
        ("working_directory", r"C:\wrong", "working_directory_exact"),
        ("trigger_mode", "scheduled_canary", "trigger_mode_exact"),
        ("cadence", "weekly", "cadence"),
        ("arguments", f'-NoProfile -File "{OA.APPROVED_LAUNCHER}" -RepoRoot "{OA.APPROVED_WORKDIR}" -TriggerMode daily_schedule -ConfirmRun -EnableScheduledSend', "scheduled_send_optin"),
        ("arguments", f'-NoProfile -File "{OA.APPROVED_LAUNCHER}" -RepoRoot "{OA.APPROVED_WORKDIR}" -TriggerMode daily_schedule -ConfirmRun -Command Start-ScheduledTask', "unexpected_additional_action"),
    ],
)
def test_task_validation_blocks_mismatches(field, value, reason):
    task = _valid_task(**{field: value})
    availability = OA.validate_task_model(task)
    assert availability.available is False
    assert reason in availability.reasons


def test_task_validation_accepts_exact_valid_task():
    availability = OA.validate_task_model(_valid_task())
    assert availability.available is True
    assert availability.reasons == []


def test_task_adapter_non_windows_unavailable():
    adapter = OA.RealWindowsTaskAdapter(system="Linux", ps_path="powershell.exe")
    assert adapter.available() is False
    assert adapter.resolve(OA.APPROVED_TASK_NAME) is None


def test_task_adapter_has_no_mutation_method():
    adapter = OA.RealWindowsTaskAdapter(system="Windows", ps_path="powershell.exe")
    assert not hasattr(adapter, "set_enabled")
    assert not hasattr(adapter, "mutation_calls")


def test_sanitized_logs_and_failures(tmp_path):
    log = OA.BoundedSanitizedLog(tmp_path / "runtime.log", max_bytes=120)
    log.write("provider failed token=secret chat_id=909767721 C:\\private\\path fake_provider_response=payload")
    text = (tmp_path / "runtime.log").read_text(encoding="utf-8")
    assert "secret" not in text
    assert "909767721" not in text
    assert "C:\\private" not in text
    assert len(text.encode("utf-8")) <= 120
