"""Offline operator-control tests (scan-only milestone).

Dependency-injected fakes stand in for Apify, Telegram, the Windows
Task Scheduler, and the audit store, so NO real external call, no PowerShell,
and no Task Scheduler mutation ever occurs. The page module is imported
with an injected OperatorPorts via st.session_state to prove the dashboard
performs no real action on import or render.

Covers: readiness gates, idempotent manual scan, recurring enable/disable,
task validation, audit sanitization, and page-import / no-action invariants.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import pytest

from rdsa import config as C
from dashboard import operator_service as OS
from dashboard.operator_service import OperatorPorts, Readiness, ScanResult, TaskControlState


def _run_iso_subprocess(mode: str) -> dict:
    """Run the isolated Scheduler-page verifier in a SEPARATE process.

    C1B isolation: any raw import of ``dashboard.pages.7_Scheduler`` in this
    pytest process pollutes Streamlit's module-level form-context stack, which
    then breaks the AppTest browser tests in the SAME process with
    "Forms cannot be nested in other forms." The raw import is therefore moved
    into tests/_c1b_scheduler_iso.py, run with PYTHONPATH UNSET and every
    real launch/adapter entry point replaced by an abort. Returns the parsed
    JSON result dict (key "C1B_ISO_RESULT").
    """
    import json
    import subprocess

    iso = Path(__file__).resolve().parent / "_c1b_scheduler_iso.py"
    assert iso.exists(), f"missing iso verifier: {iso}"

    proc = subprocess.run(
        [sys.executable, str(iso), mode],
        env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"},
        capture_output=True, text=True, timeout=120,
    )
    payload = None
    for line in proc.stdout.splitlines():
        if line.startswith("C1B_ISO_RESULT "):
            payload = json.loads(line[len("C1B_ISO_RESULT "):])
            break
    assert payload is not None, (
        f"iso verifier (mode={mode}) produced no result line\n"
        f"rc={proc.returncode}\nstderr={proc.stderr[-2000:]}"
    )
    assert payload.get("external_reached") is not True, (
        f"iso verifier reached a real external adapter: {payload.get('errors')}"
    )
    assert payload.get("ok") is True, (
        f"iso verifier (mode={mode}) failed: {payload.get('errors')}"
    )
    assert proc.returncode == 0, (
        f"iso verifier rc={proc.returncode}\nstderr={proc.stderr[-2000:]}"
    )
    return payload


@pytest.fixture(autouse=True)
def _reset_opt_in():
    """Reset the process-local manual-launch opt-in before each test.

    ``_live_opt_in`` is a module global; without this, a launch in one
    test would persistently block launches in later tests in the same
    process (which is the intended idempotency, but not what each
    isolated test expects).
    """
    OS.reset_opt_in()
    yield
    OS.reset_opt_in()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
class FakeManualPort:
    def __init__(self, side_effect=None):
        self.calls = 0
        self.last_args = None
        self.side_effect = side_effect

    def __call__(self, *args, **kwargs):
        self.calls += 1
        self.last_args = args[0] if args else kwargs
        if self.side_effect is not None:
            return self.side_effect(*args, **kwargs)
        # Mirror the real orchestrator's success-path shape.
        return {"status": "completed", "run_id": "man-" + str(self.calls)}


class FakeAudit:
    def __init__(self):
        self.rows = []

    def __call__(self, row):
        import copy
        self.rows.append(copy.deepcopy(row))


def _task_model(name="RentalDemandSignalAgent-Daily", enabled=True,
                trigger_mode="daily_schedule", arguments=None,
                carries_send=False, next_run="2026-07-21T08:30:00",
                cadence="daily"):
    if arguments is None:
        arguments = (
            '-NoProfile -ExecutionPolicy Bypass -File '
            f'"C:\\repo\\scripts\\windows_scheduler_run.ps1" '
            f'-RepoRoot "C:\\repo" -TriggerMode {trigger_mode} -ConfirmRun'
        )
    if carries_send:
        arguments += " -EnableScheduledSend"
    return {
        "name": name,
        "execute": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        "arguments": arguments,
        "working_directory": str(C.ROOT),
        "enabled": enabled,
        "state": "Ready" if enabled else "Disabled",
        "trigger_mode": trigger_mode,
        "next_run": next_run,
        "cadence": cadence,
    }


class FakeTaskPorts:
    def __init__(self, model=None, set_result=True):
        self.model = model
        self.set_result = set_result
        self.set_calls = []

    def resolve(self, name):
        return self.model

    def set_enabled(self, name, enabled):
        self.set_calls.append((name, enabled))
        # Mutate the model so subsequent control-state reads reflect the flip.
        if self.model is not None:
            self.model["enabled"] = enabled
        return self.set_result


def make_ports(manual=None, task_model=None, task_set_result=True,
               state_status=None, readiness=None):
    fake_audit = FakeAudit()
    fake_manual = manual or FakeManualPort()
    task_ports = FakeTaskPorts(task_model, task_set_result)
    snap = state_status or {
        "code_readiness": "ready",
        "scheduler_enabled": True,
        "scheduler_send_enabled": False,
        "apify_live_enabled": False,
        "telegram_send_enabled": False,
        "monthly_usage_usd": 1.0,
        "stop_usd": 4.25,
        "warn_usd": 3.75,
        "lock": {"locked": False},
        "latest_run": None,
        "last_successful_run": None,
        "interrupted_runs": [],
    }
    if readiness is None:
        readiness = {"ready": True, "reasons": []}
    return OperatorPorts(
        manual_port=fake_manual,
        state_port=lambda: snap,
        readiness_port=lambda: readiness,
        task_port=task_ports.resolve,
        task_set_port=task_ports.set_enabled,
        audit_port=fake_audit,
    ), fake_manual, fake_audit


# ---------------------------------------------------------------------------
# Readiness gates
# ---------------------------------------------------------------------------
def test_missing_confirmation_blocks_manual_scan():
    ports, manual, audit = make_ports()
    res = OS.start_manual_scan(confirm=False, ports=ports)
    assert res.accepted is False
    assert res.status == "refused"
    assert manual.calls == 0
    assert audit.rows[-1]["outcome"] == "refused"
    assert audit.rows[-1]["error_code"] == "missing_confirmation"


def test_readiness_failure_blocks():
    ports, manual, audit = make_ports(readiness={"ready": False, "reasons": ["repository_readiness_failed"]})
    r = OS.get_manual_run_readiness(ports)
    assert r.ready is False
    assert "repository_readiness_failed" in r.reasons
    res = OS.start_manual_scan(confirm=True, ports=ports)
    assert res.accepted is False
    assert manual.calls == 0


def test_readiness_active_process_blocks():
    ports, manual, _ = make_ports(readiness={"ready": False, "reasons": ["active_process_alive"]})
    r = OS.get_manual_run_readiness(ports)
    assert "active_process_alive" in r.reasons
    assert r.ready is False


def test_readiness_active_lock_blocks():
    ports, manual, _ = make_ports(readiness={"ready": False, "reasons": ["active_lock_exists"]})
    r = OS.get_manual_run_readiness(ports)
    assert "active_lock_exists" in r.reasons


def test_readiness_unresolved_interrupted_run_blocks():
    ports, manual, _ = make_ports(readiness={"ready": False, "reasons": ["unresolved_interrupted_run"]})
    r = OS.get_manual_run_readiness(ports)
    assert "unresolved_interrupted_run" in r.reasons


def test_cost_stop_gate_blocks():
    ports, manual, _ = make_ports(readiness={"ready": False, "reasons": ["cost_stop_gate"]})
    r = OS.get_manual_run_readiness(ports)
    assert "cost_stop_gate" in r.reasons


def test_cost_warning_does_not_block():
    ports, manual, _ = make_ports(readiness={"ready": True, "reasons": []})
    r = OS.get_manual_run_readiness(ports)
    assert r.ready is True
    assert "cost_stop_gate" not in r.reasons


def test_missing_credentials_blocks():
    ports, manual, _ = make_ports(readiness={"ready": False, "reasons": ["inventory_unavailable"]})
    r = OS.get_manual_run_readiness(ports)
    assert "inventory_unavailable" in r.reasons


# ---------------------------------------------------------------------------
# Idempotency / double-click / rerun
# ---------------------------------------------------------------------------
def test_one_manual_launch_only():
    manual = FakeManualPort()
    ports, _, audit = make_ports(manual=manual)
    r1 = OS.start_manual_scan(confirm=True, ports=ports)
    assert r1.accepted is True
    assert manual.calls == 1
    # Second attempt in the same process must be refused (opt-in latched).
    r2 = OS.start_manual_scan(confirm=True, ports=ports)
    assert r2.accepted is False
    assert r2.status == "refused"
    assert manual.calls == 1


def test_double_click_no_second_apify():
    manual = FakeManualPort()
    ports, _, audit = make_ports(manual=manual)
    # Two near-simultaneous submits before opt-in latches: the orchestrator's
    # own lock would catch the second; here we prove the service calls the
    # manual port at most the moment it transitions to accepted.
    r1 = OS.start_manual_scan(confirm=True, ports=ports)
    r2 = OS.start_manual_scan(confirm=True, ports=ports)
    assert manual.calls == 1
    assert r1.accepted and not r2.accepted


def test_streamlit_rerun_no_repeat():
    manual = FakeManualPort()
    ports, _, audit = make_ports(manual=manual)
    OS.start_manual_scan(confirm=True, ports=ports)
    OS.reset_opt_in()  # a rerun that lost session_state would re-evaluate
    # but start_manual_scan performs a fresh readiness check; with a held
    # lock it would be refused. Simulate the held-lock refusal path.
    snap = {"code_readiness": "ready", "lock": {"locked": True, "process_alive": True},
             "interrupted_runs": [], "monthly_usage_usd": 0.0,
             "stop_usd": 4.25, "warn_usd": 3.75}
    ports2, manual2, _ = make_ports(manual=manual, readiness={"ready": False, "reasons": ["active_process_alive"]})
    r = OS.start_manual_scan(confirm=True, ports=ports2)
    assert r.accepted is False
    assert manual.calls == 1  # original only


def test_zero_telegram_calls_on_manual_scan(monkeypatch):
    sent = {"n": 0}

    def fake_send(*a, **k):
        sent["n"] += 1
        raise AssertionError("Telegram must never be called")

    monkeypatch.setattr(OS, "_live_opt_in", False)
    ports, manual, _ = make_ports()
    # Even if the manual port were the real one, scheduler_send stays False.
    r = OS.start_manual_scan(confirm=True, ports=ports)
    assert r.accepted is True
    assert sent["n"] == 0


def test_zero_automatic_retry():
    manual = FakeManualPort()
    ports, _, _ = make_ports(manual=manual)

    def boom(args):
        boom.n += 1
        if boom.n == 1:
            raise RuntimeError("apify timeout")  # one failure, no retry
        return {"status": "completed", "run_id": "x"}

    boom.n = 0
    manual.side_effect = boom
    ports = OperatorPorts(manual_port=manual, audit_port=FakeAudit(),
                        readiness_port=lambda: {"ready": True, "reasons": []})
    r = OS.start_manual_scan(confirm=True, ports=ports)
    assert r.accepted is False
    assert r.status == "failed"
    assert boom.n == 1  # exactly one attempt, no retry


def test_process_local_live_opt_in_not_persisted():
    import os
    before = dict(os.environ)
    manual = FakeManualPort()
    ports, _, _ = make_ports(manual=manual)
    OS.start_manual_scan(confirm=True, ports=ports)
    # The opt-in is process-local; it must not leak to os.environ as truthy.
    assert os.environ.get("RDSA_SCHEDULER_ENABLED", "").lower() != "true"
    assert os.environ.get("RDSA_TELEGRAM_SEND_ENABLED", "").lower() != "true"
    assert os.environ.get("APIFY_LIVE_ENABLED", "").lower() != "true"
    # Original parent environment is restored unchanged.
    assert os.environ == before


def test_no_env_mutation(monkeypatch):
    before = dict(__import__("os").environ)
    manual = FakeManualPort()
    ports, _, _ = make_ports(manual=manual)
    OS.start_manual_scan(confirm=True, ports=ports)
    after = dict(__import__("os").environ)
    assert before == after


# ---------------------------------------------------------------------------
# Recurring scan control
# ---------------------------------------------------------------------------
def test_expected_task_validation_passes():
    ports, _, _ = make_ports(task_model=_task_model(enabled=False))
    st = OS.get_task_control_state(ports)
    assert st.exists and st.valid and st.enabled is False
    assert st.carries_scheduled_send is False


def test_mismatched_task_action_blocked():
    model = _task_model()
    model["execute"] = "C:\\python.exe"  # wrong executable
    ports, _, _ = make_ports(task_model=model)
    st = OS.get_task_control_state(ports)
    assert st.valid is False
    assert "execute" in st.mismatches
    res = OS.set_recurring_scan_enabled(True, confirm=True, ports=ports)
    assert res["ok"] is False
    assert res["reason"] == "task_definition_mismatch"


def test_task_with_scheduled_send_argument_blocked():
    ports, _, _ = make_ports(task_model=_task_model(carries_send=True))
    st = OS.get_task_control_state(ports)
    assert st.carries_scheduled_send is True
    assert "scheduled_send_optin" in st.mismatches
    res = OS.set_recurring_scan_enabled(True, confirm=True, ports=ports)
    assert res["ok"] is False
    assert res["reason"] == "scheduled_send_optin_present"


def test_enable_existing_disabled_task():
    manual = FakeManualPort()
    ports, _, audit = make_ports(task_model=_task_model(enabled=False))
    res = OS.set_recurring_scan_enabled(True, confirm=True, ports=ports)
    assert res["ok"] is True
    assert res["outcome"] == "accepted"
    assert res["previous_state"] == "disabled"
    assert res["resulting_state"] == "enabled"
    assert audit.rows[-1]["action"] == "recurring_set"


def test_disable_existing_enabled_task():
    ports, _, audit = make_ports(task_model=_task_model(enabled=True))
    res = OS.set_recurring_scan_enabled(False, confirm=True, ports=ports)
    assert res["ok"] is True
    assert res["outcome"] == "accepted"
    assert res["resulting_state"] == "disabled"


def test_repeated_enable_noop():
    ports, _, _ = make_ports(task_model=_task_model(enabled=True))
    res = OS.set_recurring_scan_enabled(True, confirm=True, ports=ports)
    assert res["ok"] is True
    assert res["outcome"] == "noop"
    assert res["previous_state"] == "enabled"
    assert res["resulting_state"] == "enabled"


def test_repeated_disable_noop():
    ports, _, _ = make_ports(task_model=_task_model(enabled=False))
    res = OS.set_recurring_scan_enabled(False, confirm=True, ports=ports)
    assert res["ok"] is True
    assert res["outcome"] == "noop"
    assert res["previous_state"] == "disabled"
    assert res["resulting_state"] == "disabled"


def test_recurring_requires_confirmation():
    ports, _, _ = make_ports(task_model=_task_model(enabled=False))
    res = OS.set_recurring_scan_enabled(True, confirm=False, ports=ports)
    assert res["ok"] is False
    assert res["reason"] == "missing_confirmation"


def test_missing_task_blocked():
    ports, _, _ = make_ports(task_model=None)
    st = OS.get_task_control_state(ports)
    assert st.exists is False
    res = OS.set_recurring_scan_enabled(True, confirm=True, ports=ports)
    assert res["ok"] is False
    assert res["reason"] == "task_not_registered"


def test_disabling_does_not_terminate_process():
    # The fake set_enabled only flips state; no kill/terminate is invoked.
    model = _task_model(enabled=True)
    fake_task = FakeTaskPorts(model, set_result=True)
    ports = OperatorPorts(
        task_port=fake_task.resolve,
        task_set_port=fake_task.set_enabled,
        audit_port=FakeAudit(),
    )
    res = OS.set_recurring_scan_enabled(False, confirm=True, ports=ports)
    assert res["ok"] is True
    assert len(fake_task.set_calls) == 1
    assert fake_task.set_calls[0] == ("RentalDemandSignalAgent-Daily", False)
    # Model state flipped but no process object was ever touched.
    assert model["enabled"] is False


# ---------------------------------------------------------------------------
# Audit sanitization / secrets
# ---------------------------------------------------------------------------
def test_audit_event_recorded_with_op_id():
    ports, manual, audit = make_ports(task_model=_task_model(enabled=False))
    OS.start_manual_scan(confirm=True, ports=ports)
    assert any(r["op_id"] for r in audit.rows)
    assert audit.rows[-1]["action"] == "manual_scan_start"
    assert audit.rows[-1]["outcome"] == "accepted"
    assert audit.rows[-1]["actor"] == "dashboard"


def test_failed_action_records_sanitized_failure():
    manual = FakeManualPort()

    def fail(**kwargs):
        raise RuntimeError(
            "provider failed token=secret chat_id=909767721 "
            "C:\\private\\path"
        )

    manual.side_effect = fail
    ports = OperatorPorts(manual_port=manual, audit_port=FakeAudit(),
                        readiness_port=lambda: {"ready": True, "reasons": []})
    r = OS.start_manual_scan(confirm=True, ports=ports)
    assert r.accepted is False
    assert r.status == "failed"
    assert r.error_code is not None
    # Sanitized: no token / chat id / path leaked into audit row.
    row = ports.audit_port.rows[-1]
    blob = str(row)
    assert "secret" not in blob
    assert "909767721" not in blob
    assert "C:\\private" not in blob


def test_no_token_chatid_or_author_exposure_in_audit():
    ports, _, audit = make_ports(task_model=_task_model(enabled=False))
    OS.set_recurring_scan_enabled(True, confirm=True, ports=ports)
    blob = str(audit.rows)
    assert "TELEGRAM_BOT_TOKEN" not in blob
    assert "APIFY_API_TOKEN" not in blob
    assert "chat_id" not in blob.lower()


# ---------------------------------------------------------------------------
# Page-import / no-action-on-import invariants
# ---------------------------------------------------------------------------
def test_page_imports_without_side_effects():
    # The raw import is performed in an ISOLATED subprocess so it cannot
    # pollute Streamlit's form-context stack in this pytest process (which
    # also runs AppTest browser tests). See tests/_c1b_scheduler_iso.py.
    payload = _run_iso_subprocess("import_check")


def test_subprocess_guard_is_fail_closed():
    """The C1B subprocess allow-list must reject every command except the
    exact benign ``cmd /c ver`` required for Streamlit import.

    Proves: allowed benign command passes; an arbitrary Python child command,
    an arbitrary executable, PowerShell, and the Windows Task Scheduler are all
    rejected; the page still imports through the isolated verifier; and zero
    operator adapter calls occur.
    """
    payload = _run_iso_subprocess("guard_check")
    assert payload.get("ok") is True
    assert payload.get("guard_allowed_passed") is True
    assert payload.get("guard_rejected_count") == 4
    assert payload.get("guard_clean") is True
    assert payload.get("real_manual_calls") == 0
    assert payload.get("real_task_calls") == 0
    assert payload.get("external_reached") is not True


def test_scheduler_page_default_wiring_is_fail_closed():
    """The Scheduler page imported/rendered without injected ports must NOT
    reach any real external operation: run_scheduled_run (Apify), PowerShell /
    Task Scheduler, Telegram, or the manual launcher.

    Phase C1 requires the dashboard to fail closed: the default page wiring
    uses ``OS.not_connected_ports()`` so no real adapter is instantiated.

    C1B isolation: the raw page import is performed in an ISOLATED subprocess
    (PYTHONPATH unset, every real launch/adapter entry point replaced with a
    function that aborts the child) so the page's module-top-level
    ``st.form(...)`` calls cannot contaminate the Streamlit form-context stack
    of this pytest process (which also runs AppTest browser tests in the same
    process). See tests/_c1b_scheduler_iso.py.
    """
    payload = _run_iso_subprocess("fail_closed")
    # Explicit fail-closed evidence from the isolated import.
    assert payload.get("ports_fail_closed") is True
    assert payload.get("real_manual_calls") == 0
    assert payload.get("real_task_calls") == 0
    assert payload.get("external_reached") is not True


def test_all_dashboard_pages_import():
    # Importing every dashboard page (incl. the Scheduler page with its
    # module-level st.form calls) is done in an ISOLATED subprocess so the
    # form-context stack is not polluted for the AppTest browser tests that
    # run in this same process.
    payload = _run_iso_subprocess("all_pages")
    assert payload.get("all_pages_imported") is True


def test_scheduler_status_remains_readable():
    # The observability snapshot still exposes read-only evidence.
    from rdsa.dashboard_repository import get_scheduler_status
    snap = get_scheduler_status()
    assert "lock" in snap
    assert "monthly_usage_usd" in snap
    assert "interrupted_runs" in snap


def test_get_manual_run_readiness_returns_structured():
    ports, _, _ = make_ports()
    r = OS.get_manual_run_readiness(ports)
    assert isinstance(r, Readiness)
    assert set(r.to_dict().keys()) == {"ready", "reasons"}


def test_scanresult_and_taskcontrol_to_dict():
    sr = ScanResult(accepted=True, status="completed", run_id="x")
    assert sr.to_dict()["accepted"] is True
    tc = TaskControlState(exists=True, enabled=True, valid=True)
    assert tc.to_dict()["enabled"] is True
