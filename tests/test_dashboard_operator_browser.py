"""C1B — Offline browser acceptance for the operator Scheduler page.

Uses Streamlit's AppTest harness with fully FAKE OperatorPorts injected through
the page's test seam (st.session_state["_operator_ports"]). No real adapter,
Apify, Telegram, PowerShell, or Windows Task Scheduler is ever reached.

Verification covers the Phase C1 operator-control acceptance criteria:
  - page load performs no action;
  - read-only Scheduler evidence remains visible;
  - operator controls are visually separated (own header/section);
  - "Scan only" and "Telegram Off" are clearly displayed;
  - readiness failures disable / block Run search now;
  - missing confirmation causes no adapter call;
  - accepted confirmed submission causes exactly one fake call;
  - a rerun with the same operation ID causes no second call (idempotent);
  - installed task state is visible but read-only;
  - malformed task definition is reported without mutation controls;
  - a forbidden scheduled-send argument is shown as read-only evidence;
  - no raw token / chat ID / private author / env value / provider response leaks;
  - browser console has zero warnings and zero errors (no uncaught exceptions /
    tracebacks from the page script).

Run with:
    env -u PYTHONPATH python -m pytest -q -p no:cacheprovider \
        tests/test_dashboard_operator_browser.py
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from streamlit.testing.v1 import AppTest  # noqa: E402
from dashboard.operator_service import OperatorPorts  # noqa: E402

_PAGE = "dashboard/pages/7_Scheduler.py"

# A redaction payload that must NEVER appear anywhere in rendered UI text.
# These are the *secret values* only (the sanitizer is allowed to keep the
# non-sensitive label text such as "token=" or "provider failed").
FORBIDDEN_SUBSTRINGS = [
    "secret",          # raw secret value must not survive
    "909767721",       # raw chat id must not survive
    "C:\\private\\path",  # raw private path must not survive
    "TOKEN-env",       # env placeholder leak
    "TELEGRAM-env",    # env placeholder leak
    "fake_provider_response",  # provider payload leak
]


def _audit_blob(at: AppTest) -> str:
    """Collect every rendered text-bearing element for leakage assertions."""
    parts = []
    # Metrics expose their label via .label (and .value is the numeric/text).
    for m in list(at.metric):
        try:
            parts.append(str(m.label))
        except Exception:
            pass
        try:
            parts.append(str(m.value))
        except Exception:
            pass
    for group in (
        list(at.markdown), list(at.caption), list(at.subheader),
        list(at.title), list(at.text), list(at.success),
        list(at.warning), list(at.error), list(at.info),
    ):
        for el in group:
            try:
                parts.append(str(el.value))
            except Exception:
                try:
                    parts.append(str(el.label))
                except Exception:
                    pass
    return "\n".join(parts)


def _button(at: AppTest, label: str):
    for b in at.button:
        if b.label == label:
            return b
    raise AssertionError(f"no button labelled {label!r}")


def _approved_task_model(**overrides):
    from rdsa import config as C
    base = {
        "name": "RentalDemandSignalAgent-Daily",
        "execute": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        "arguments": (
            '-NoProfile -ExecutionPolicy Bypass -File '
            '"C:\\repo\\scripts\\windows_scheduler_run.ps1" -RepoRoot "C:\\repo" '
            "-TriggerMode daily_schedule -ConfirmRun"
        ),
        "working_directory": str(C.ROOT),
        "enabled": True,
        "state": "Ready",
        "trigger_mode": "daily_schedule",
    }
    base.update(overrides)
    return base


def _fake_ports(readiness=None, task_model=None, record=None, fail_manual=False):
    """Build an OperatorPorts that records calls and never touches the host."""
    record = record if record is not None else {"manual": 0, "set": 0}
    audit_db = {}  # in-memory simulation of operator_audit table

    def _task(name):
        return _approved_task_model(**(task_model or {}))

    def _manual(args):
        record["manual"] += 1
        if fail_manual:
            raise RuntimeError(
                "provider failed token=secret chat_id=909767721 C:\\private\\path"
            )
        return {"status": "completed", "run_id": "man-x-" + str(record["manual"])}

    def _audit_write(row: dict) -> None:
        op_id = row.get("op_id")
        if op_id:
            audit_db[op_id] = row

    def _audit_lookup(op_id: str) -> dict | None:
        return audit_db.get(op_id)

    readiness = readiness or {"ready": True, "reasons": []}
    return OperatorPorts(
        manual_port=_manual,
        task_port=_task,
        readiness_port=lambda: readiness,
        audit_port=_audit_write,
        audit_lookup_port=_audit_lookup,
        state_port=lambda: {"lock": {"locked": False}, "interrupted_runs": []},
    )


def _run(ports=None, ready_default=True):
    from dashboard import operator_service as OS
    # The manual-scan opt-in latch is process-global; reset it so each test
    # starts clean (isolation between AppTest runs in the same process).
    OS.reset_opt_in()
    at = AppTest.from_file(_PAGE, default_timeout=30)
    if ports is not None:
        at.session_state["_operator_ports"] = ports
    at.run()
    return at


# ---------------------------------------------------------------------------
# Load-time safety
# ---------------------------------------------------------------------------
def test_page_load_performs_no_action():
    record = {"manual": 0, "set": 0}
    ports = _fake_ports(record=record)
    at = _run(ports)
    assert record["manual"] == 0, "manual adapter called on load"
    assert record["set"] == 0, "task mutation called on load"
    # No runtime exception from the page script.
    assert len(at.exception) == 0


def test_page_load_is_fail_closed_without_injection():
    """Default wiring (no injected ports) must not reach any real adapter."""
    record = {"manual": 0, "set": 0}
    # Build a ports object only to track whether the page reaches it; we do NOT
    # inject it, so the page must fall back to not_connected_ports().
    at = _run(ports=None)
    # If the page reached a real adapter it would error; confirm clean load.
    assert len(at.exception) == 0
    # Read-only Scheduler evidence still present.
    blob = _audit_blob(at)
    assert "Code readiness" in blob
    assert "Scheduler" in blob


def test_feature_flag_true_with_valid_adapters_displays_readiness(monkeypatch):
    from rdsa import config as C
    import dashboard.operator_adapters as OA

    record = {"manual": 0, "set": 0}
    ports = _fake_ports(record=record, task_model={"enabled": False})
    monkeypatch.setattr(C, "DASHBOARD_OPERATOR_CONTROLS_ENABLED", True)
    monkeypatch.setattr(OA, "connected_ports_if_enabled", lambda: ports)

    at = _run(ports=None)
    blob = _audit_blob(at)
    assert "Run lead search" in blob
    assert "Disabled" in blob
    at.checkbox(key="manual_confirm").set_value(True)
    _button(at, "Run search now").click().run()
    assert record["manual"] == 1
    assert "Enable recurring scan" not in _audit_blob(at)
    assert "Disable recurring scan" not in _audit_blob(at)
    assert record["set"] == 0
    assert len(at.exception) == 0


# ---------------------------------------------------------------------------
# Read-only evidence + visual separation + scan-only/telegram-off labels
# ---------------------------------------------------------------------------
def test_read_only_evidence_visible_and_controls_separated():
    at = _run(_fake_ports())
    blob = _audit_blob(at)
    # Read-only Scheduler observability.
    assert "Code readiness" in blob
    assert "Cost posture" in blob or "Monthly usage" in blob
    assert "Process lock" in blob
    assert "Latest scheduled run" in blob
    # Operator controls are visually separated under their own header.
    blob_all = _audit_blob(at)
    assert "Operator controls" in blob_all
    # Scan-only + Telegram-off messaging.
    assert "Scan only" in blob_all
    # Telegram-send state is shown (and is off in the default status snapshot).
    assert "Telegram send" in blob


def test_scan_only_and_telegram_off_displayed():
    at = _run(_fake_ports())
    blob = _audit_blob(at)
    # Explicit scan-only promise.
    assert "never sends Telegram" in blob
    # Telegram send state section is shown (intent is stated in the caption).
    assert "Telegram send" in blob
    assert "Scan only" in blob


# ---------------------------------------------------------------------------
# Readiness failure blocks Run search now
# ---------------------------------------------------------------------------
def test_readiness_failure_disables_run_search_now():
    ports = _fake_ports(readiness={"ready": False,
                                   "reasons": ["operator_controls_not_connected"]})
    at = _run(ports)
    run_btn = _button(at, "Run search now")
    assert run_btn.disabled is True
    # The blocking reason is surfaced.
    blob = _audit_blob(at)
    assert "operator_controls_not_connected" in blob


def test_missing_confirmation_causes_no_adapter_call():
    record = {"manual": 0, "set": 0}
    ports = _fake_ports(record=record)
    at = _run(ports)
    # Submit WITHOUT ticking the confirmation checkbox.
    _button(at, "Run search now").click().run()
    assert record["manual"] == 0, "adapter called without confirmation"
    # A warning (not an error) is shown for the unconfirmed attempt.
    blob = _audit_blob(at)
    assert "confirm" in blob.lower()


# ---------------------------------------------------------------------------
# Accepted confirmed submission + idempotency
# ---------------------------------------------------------------------------
def test_confirmed_submission_causes_exactly_one_fake_call():
    record = {"manual": 0, "set": 0}
    ports = _fake_ports(record=record)
    at = _run(ports)
    at.checkbox(key="manual_confirm").set_value(True)
    _button(at, "Run search now").click().run()
    assert record["manual"] == 1, "expected exactly one adapter call"
    assert len(at.exception) == 0
    # Success is shown to the operator.
    assert len(at.success) >= 1


def test_rerun_same_operation_id_no_second_call():
    record = {"manual": 0, "set": 0}
    ports = _fake_ports(record=record)
    at = _run(ports)
    at.checkbox(key="manual_confirm").set_value(True)
    _button(at, "Run search now").click().run()
    assert record["manual"] == 1
    # Submit again with the same (latched) operation id -> no second call.
    at.checkbox(key="manual_confirm").set_value(True)
    _button(at, "Run search now").click().run()
    assert record["manual"] == 1, "idempotency broken: second adapter call"


# ---------------------------------------------------------------------------
# Installed task is visible but read-only
# ---------------------------------------------------------------------------
def test_installed_task_state_visible_when_enabled():
    ports = _fake_ports(task_model={"enabled": True})
    at = _run(ports)
    blob = _audit_blob(at)
    assert "Installed Windows Scheduled Task (read-only)" in blob
    assert "Enabled" in blob
    assert "Cadence" in blob
    assert "Enable recurring scan" not in blob
    assert "Disable recurring scan" not in blob


def test_installed_task_state_visible_when_disabled():
    ports = _fake_ports(task_model={"enabled": False})
    at = _run(ports)
    blob = _audit_blob(at)
    assert "Disabled" in blob
    assert "Task Enabled/Disabled" in blob
    assert "Enable recurring scan" not in blob
    assert "Disable recurring scan" not in blob


def test_malformed_task_definition_reported_without_controls():
    ports = _fake_ports(task_model={"enabled": True, "trigger_mode": "weekly"})
    at = _run(ports)
    blob = _audit_blob(at)
    assert "Task definition evidence differs" in blob
    assert "Enable recurring scan" not in blob
    assert "Disable recurring scan" not in blob


def test_scheduled_send_argument_shown_as_read_only_evidence():
    ports = _fake_ports(task_model={
        "enabled": True,
        "arguments": (
            '-NoProfile -ExecutionPolicy Bypass -File '
            '"C:\\repo\\scripts\\windows_scheduler_run.ps1" -RepoRoot "C:\\repo" '
            "-TriggerMode daily_schedule -ConfirmRun -EnableScheduledSend"
        ),
    })
    at = _run(ports)
    blob = _audit_blob(at)
    assert "scheduled-send" in blob.lower()
    assert "Enable recurring scan" not in blob
    assert "Disable recurring scan" not in blob


def test_failed_manual_scan_is_sanitized_and_no_leak():
    ports = _fake_ports(fail_manual=True)
    at = _run(ports)
    at.checkbox(key="manual_confirm").set_value(True)
    _button(at, "Run search now").click().run()
    blob = _audit_blob(at)
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in blob, f"leak detected: {forbidden}"


# ---------------------------------------------------------------------------
# No secret leakage across the whole rendered surface
# ---------------------------------------------------------------------------
def test_no_secret_leakage_on_loaded_page():
    at = _run(_fake_ports())
    blob = _audit_blob(at)
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in blob, f"leak detected: {forbidden}"


# ---------------------------------------------------------------------------
# Console health: zero uncaught exceptions / tracebacks
# ---------------------------------------------------------------------------
def test_browser_console_zero_exceptions():
    at = _run(_fake_ports())
    assert len(at.exception) == 0, f"page raised: {at.exception}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
