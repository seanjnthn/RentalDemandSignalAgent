"""Testable operator-control abstraction for the Signal Desk Scheduler page.

Scan-only milestone. Exposes narrow, dependency-injected methods so the
Streamlit page never imports subprocess / PowerShell / Windows APIs directly
and so tests can inject fakes for Apify, Telegram, Task Scheduler, and
the audit store.

The manual scan **reuses** ``rdsa.scheduler.run_scheduled_run`` verbatim
(trigger_type="dashboard_manual", confirm_scheduled_run=True); every
fail-closed gate (lock, cost, inventory, interruption recovery, single
batched Apify request, no paid retry, Telegram off) is inherited, and the
run stays traceable through the existing ``scheduled_runs`` ledger.

No .env mutation. No scheduled Telegram-send toggle. No task (re)creation.
"""
from __future__ import annotations

import json
import types
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rdsa import dashboard_repository as DR
from rdsa import config as C
from rdsa import scheduler as S


# Approved Windows task definition (single source of truth mirrors scripts/*.ps1).
APPROVED_TASK_NAME = "RentalDemandSignalAgent-Daily"
APPROVED_LAUNCHER = "scripts\\windows_scheduler_run.ps1"
APPROVED_EXECUTABLE_SUFFIX = "powershell.exe"
APPROVED_TRIGGER_MODES = ("daily_schedule", "scheduled_canary")
# A recurring scan must NEVER carry a scheduled-send opt-in.
FORBIDDEN_TASK_ARG_FRAGMENTS = ("-EnableScheduledSend",)


# ---------------------------------------------------------------------------
# Ports (dependency injection)
# ---------------------------------------------------------------------------
@dataclass
class OperatorPorts:
    """Injectable boundaries. Defaults wire to the real rdsa implementation."""
    # run_scheduled_run(args) -> dict ; real Apify/Telegram only after preflight.
    manual_port: Callable[[Any], dict] = field(
        default_factory=lambda: S.run_scheduled_run
    )
    # get_scheduler_status(db_path) -> dict
    state_port: Callable[[Any], dict] = field(
        default_factory=lambda: DR.get_scheduler_status
    )
    # resolve_task(name) -> TaskModel | None  (real or fake)
    task_port: Callable[[str], Any] = field(
        default_factory=lambda: resolve_windows_task
    )

    # readiness_port() -> dict with keys {ready:bool, reasons:list[str]}
    # default combines state_port + inventory + repo checks.
    readiness_port: Callable[[], dict] = field(
        default_factory=lambda: _default_readiness
    )
    # audit_append(row) -> None
    audit_port: Callable[[dict], None] = field(
        default_factory=lambda: append_operator_audit
    )
    # trigger_type passed to the manual run.
    trigger_type: str = "dashboard_manual"


@dataclass
class Readiness:
    ready: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ready": self.ready, "reasons": list(self.reasons)}


@dataclass
class ScanResult:
    accepted: bool
    status: str
    operation_id: str | None = None
    run_id: str | None = None
    message: str = ""
    error_code: str | None = None

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "operation_id": self.operation_id,
            "run_id": self.run_id,
            "message": self.message,
            "error_code": self.error_code,
        }


@dataclass
class TaskControlState:
    exists: bool
    enabled: bool | None = None
    valid: bool = False
    mismatches: list[str] = field(default_factory=list)
    carries_scheduled_send: bool = False
    name: str = APPROVED_TASK_NAME
    next_run: str | None = None
    cadence: str | None = None

    def to_dict(self) -> dict:
        return {
            "exists": self.exists,
            "enabled": self.enabled,
            "valid": self.valid,
            "mismatches": list(self.mismatches),
            "carries_scheduled_send": self.carries_scheduled_send,
            "name": self.name,
            "next_run": self.next_run,
            "cadence": self.cadence,
        }


# ---------------------------------------------------------------------------
# Fail-closed default wiring (Phase C1)
# ---------------------------------------------------------------------------
def not_connected_ports() -> "OperatorPorts":
    """Fail-closed default ports for the Phase C1 dashboard.

    The Scheduler page must NOT default to a real manual-run or to a real
    Windows Task Scheduler adapter. On import or render, without an
    explicitly injected ``OperatorPorts``, the page uses this object so it
    can never reach ``run_scheduled_run``, PowerShell, the Task Scheduler,
    Apify, or Telegram.

    The real adapter may exist behind ``OperatorPorts`` (it is wired through
    the dataclass ``default_factory``), but it is only reachable when an
    operator explicitly injects a *connected* ports object — a later phase.
    Until then, readiness reports a clear ``operator_controls_not_connected``
    state and the task resolver returns "not registered" without touching the
    host.
    """
    def _not_connected_readiness() -> dict:
        return {"ready": False, "reasons": ["operator_controls_not_connected"]}

    def _not_connected_task(name: str):
        # No real Task Scheduler lookup; report the task as unregistered.
        return None


    def _not_connected_manual(args):
        # Defensive: start_manual_scan is guarded by the page and by the
        # readiness gate, so this should never run. Fail closed if it does.
        raise RuntimeError("operator controls not connected")

    def _not_connected_audit(row: dict) -> None:
        return None

    return OperatorPorts(
        manual_port=_not_connected_manual,
        state_port=lambda: {"code_readiness": "unknown"},
        readiness_port=_not_connected_readiness,
        task_port=_not_connected_task,
        audit_port=_not_connected_audit,
    )


# ---------------------------------------------------------------------------
# Process-local opt-in (never persisted)
# ---------------------------------------------------------------------------
_live_opt_in = False


def reset_opt_in() -> None:
    """Test seam: clear the process-local manual-launch opt-in."""
    global _live_opt_in
    _live_opt_in = False


def _set_opt_in(value: bool) -> None:
    global _live_opt_in
    _live_opt_in = bool(value)


# ---------------------------------------------------------------------------
# Manual scan
# ---------------------------------------------------------------------------
def get_manual_run_readiness(ports: OperatorPorts | None = None) -> Readiness:
    """Return why the manual search button must be disabled, if at all.

    The verdict is produced by the injected ``readiness_port`` so tests
    can force either outcome without touching the filesystem. The default
    port (``_default_readiness``) combines the scheduler status snapshot
    with the real inventory / repository availability checks.
    """
    ports = ports or OperatorPorts()
    if _live_opt_in:
        return Readiness(ready=False, reasons=["manual_launch_accepted"])
    try:
        verdict = ports.readiness_port()
    except Exception:
        return Readiness(ready=False, reasons=["scheduler_status_unavailable"])
    reasons = list(verdict.get("reasons", [])) or []
    return Readiness(ready=not reasons, reasons=reasons)


def _default_readiness() -> dict:
    """Real readiness: scheduler status + inventory + repository checks."""
    from rdsa.dashboard_repository import get_scheduler_status

    reasons: list[str] = []
    try:
        status = get_scheduler_status()
    except Exception:
        return {"ready": False, "reasons": ["scheduler_status_unavailable"]}

    if status.get("code_readiness") in (None, "unknown"):
        reasons.append("repository_readiness_failed")

    lock = status.get("lock") or {}
    if lock.get("locked"):
        if lock.get("process_alive"):
            reasons.append("active_process_alive")
        else:
            reasons.append("active_lock_exists")

    interrupted = status.get("interrupted_runs") or []
    if any(r.get("reconciliation") == "required" for r in interrupted):
        reasons.append("unresolved_interrupted_run")

    usage = float(status.get("monthly_usage_usd") or 0.0)
    stop = float(status.get("stop_usd") or 0.0)
    projected = usage + float(C.SCHEDULER_MAX_CHARGE_USD)
    if projected > stop:
        reasons.append("cost_stop_gate")

    if not _inventory_available():
        reasons.append("inventory_unavailable")
    if not _repo_resolvable():
        reasons.append("repository_unavailable")

    return {"ready": not reasons, "reasons": reasons}


def _inventory_available() -> bool:
    try:
        from rdsa.inventory import validate_real_inventory_for_scan
        _, report = validate_real_inventory_for_scan(C.INVENTORY_REAL_CSV)
        return bool(report.get("ok")) and bool(report.get("accepted_rows"))
    except Exception:
        return False


def _repo_resolvable() -> bool:
    try:
        return bool(Path(C.ROOT).exists())
    except Exception:
        return False


def start_manual_scan(
    *,
    confirm: bool,
    live_opt_in: bool = False,
    operation_id: str | None = None,
    ports: OperatorPorts | None = None,
) -> ScanResult:
    """Run one manual scan reusing the existing scheduler pipeline.

    Requirements enforced:
      - explicit ``confirm`` required;
      - must not be called after an opt-in already accepted this process;
      - reuses run_scheduled_run with trigger_type="dashboard_manual";
      - at most one Apify request, no paid retry, Telegram off;
      - returns control without waiting indefinitely (run_scheduled_run returns
        a dict; we surface run_id and poll read-only ledger status separately);
      - never fabricates success.

    On acceptance, sets the process-local opt-in so readiness reports
    ``manual_launch_accepted`` for the remainder of the process (idempotency
    against Streamlit reruns / double-clicks).
    """
    ports = ports or OperatorPorts()
    op_id = operation_id or uuid.uuid4().hex[:8]

    if not confirm:
        _audit(ports, op_id, "manual_scan_start", {},
                {"accepted": False}, "refused", "missing_confirmation")
        return ScanResult(accepted=False, status="refused", operation_id=op_id,
                          message="Confirmation required to run a manual search.")

    if _live_opt_in:
        return ScanResult(accepted=False, status="refused", operation_id=op_id,
                          message="A manual launch was already accepted this session.")

    # Re-check readiness at execution time (fail-closed).
    readiness = get_manual_run_readiness(ports)
    if not readiness.ready:
        _audit(ports, op_id, "manual_scan_start", {},
                {"accepted": False, "reasons": readiness.reasons},
                "refused", "readiness_failed")
        return ScanResult(
            accepted=False, status="refused",
            operation_id=op_id,
            message="Readiness gate not met: " + "; ".join(readiness.reasons),
        )

    args = types.SimpleNamespace(
        confirm_scheduled_run=True,
        trigger_type=ports.trigger_type,
        operation_id=op_id,
    )
    try:
        report = ports.manual_port(args)
    except Exception as exc:  # fail closed; record sanitized failure.
        code, sanitized = S.sanitize_error(exc)
        _audit(ports, op_id, "manual_scan_start", {},
                {"accepted": False}, "failed", code,
                sanitized_error=sanitized)
        return ScanResult(accepted=False, status="failed", operation_id=op_id,
                          error_code=code, message=sanitized)

    status = str(report.get("status"))
    run_id = report.get("run_id")
    if not run_id:
        run_id = report.get("operation_id")
    if status in ("refused", "blocked_cost_limit", "blocked_lock", "failed"):
        _audit(ports, op_id, "manual_scan_start", {},
                {"accepted": False, "run_id": run_id, "status": status},
                "refused", status)
        return ScanResult(accepted=False, status=status, operation_id=op_id, run_id=run_id,
                          message=str(report.get("message", status)))
    # Accepted: lock the opt-in for the remainder of this process.
    _set_opt_in(True)
    _audit(ports, op_id, "manual_scan_start", {},
            {"accepted": True, "run_id": run_id, "status": status},
            "accepted", run_id=run_id)
    return ScanResult(
        accepted=True, status=status, operation_id=op_id, run_id=run_id,
        message=f"Manual search accepted. run_id={run_id}",
    )


# ---------------------------------------------------------------------------
# Installed Windows Scheduled Task (read-only evidence only)
# ---------------------------------------------------------------------------
def get_task_control_state(ports: OperatorPorts | None = None) -> TaskControlState:
    ports = ports or OperatorPorts()
    task = ports.task_port(APPROVED_TASK_NAME)
    if task is None:
        return TaskControlState(exists=False, valid=False,
                               name=APPROVED_TASK_NAME)
    mismatches: list[str] = []
    if task.get("name") != APPROVED_TASK_NAME:
        mismatches.append("task_name")
    exe = (task.get("execute") or "").replace("/", "\\").lower()
    if not exe.endswith(APPROVED_EXECUTABLE_SUFFIX):
        mismatches.append("execute")
    if APPROVED_LAUNCHER.lower() not in (task.get("arguments") or "").lower().replace("/", "\\"):
        mismatches.append("launcher_script")
    if str(task.get("working_directory") or "").replace("/", "\\").rstrip("\\").lower() \
            != str(C.ROOT).replace("/", "\\").rstrip("\\").lower():
        mismatches.append("working_directory")
    if task.get("trigger_mode") not in APPROVED_TRIGGER_MODES:
        mismatches.append("trigger_mode")
    carries_send = any(
        frag.lower() in (task.get("arguments") or "").lower()
        for frag in FORBIDDEN_TASK_ARG_FRAGMENTS
    )
    if carries_send:
        mismatches.append("scheduled_send_optin")
    return TaskControlState(
        exists=True,
        enabled=bool(task.get("enabled")),
        valid=not mismatches,
        mismatches=mismatches,
        carries_scheduled_send=carries_send,
        name=APPROVED_TASK_NAME,
        next_run=task.get("next_run"),
        cadence=task.get("cadence"),
    )


# ---------------------------------------------------------------------------
# Audit (operator_audit table in the runtime DB; git-ignored)
# ---------------------------------------------------------------------------
def _audit_db_path() -> Path:
    return Path(C.RUNTIME_DIR) / "operator_audit.sqlite3"


def append_operator_audit(row: dict) -> None:
    """Persist one sanitized operator-action row. No secrets are stored."""
    import sqlite3

    path = _audit_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operator_audit(
                op_id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                previous_state TEXT,
                resulting_state TEXT,
                outcome TEXT NOT NULL,
                error_code TEXT,
                sanitized_error TEXT,
                run_id TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO operator_audit(
                op_id, action, timestamp, actor, previous_state,
                resulting_state, outcome, error_code, sanitized_error, run_id
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row.get("op_id"),
                row.get("action"),
                row.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                row.get("actor", "dashboard"),
                _json_safe(row.get("previous_state")),
                _json_safe(row.get("resulting_state")),
                row.get("outcome"),
                row.get("error_code"),
                row.get("sanitized_error"),
                row.get("run_id"),
            ),
        )
        conn.commit()


def _json_safe(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value[:4000]
    try:
        return json.dumps(value, default=str)[:4000]
    except (TypeError, ValueError):
        return str(value)[:4000]


def _scrub(text: str) -> str:
    """Extra sanitization for operator-audit error text.

    ``rdsa.scheduler.sanitize_error`` already strips phones, emails, and
    absolute paths. We additionally redact high-signal secret assignment
    patterns (token=, chat_id=, api_key=, bot_token=) and Windows
    ``C:\\Users\\<user>`` paths so no credential or private author leaks
    into the audit ledger.
    """
    import re as _re
    out = S.sanitize_error(text)[1]
    out = _re.sub(r"(?i)(token|chat_id|api_key|bot_token)\s*[=:]\s*\S+", r"\1=[redacted]", out)
    out = _re.sub(r"C:\\Users\\[^\\s]+", "[user-path]", out)
    return out[:4000]


def _audit(
    ports: OperatorPorts,
    op_id: str,
    action: str,
    previous_state: Any,
    resulting_state: Any,
    outcome: str,
    error_code: str | None = None,
    *,
    sanitized_error: str | None = None,
    run_id: str | None = None,
) -> None:
    ports.audit_port({
        "op_id": op_id,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": "dashboard",
        "previous_state": previous_state,
        "resulting_state": resulting_state,
        "outcome": outcome,
        "error_code": error_code,
        "sanitized_error": _scrub(sanitized_error) if sanitized_error else None,
        "run_id": run_id,
    })


# ---------------------------------------------------------------------------
# Real Windows task resolver (default port; the page may inject a fake).
# Skipped automatically where PowerShell/Task Scheduler is unavailable.
# ---------------------------------------------------------------------------
def resolve_windows_task(name: str) -> dict | None:
    """Resolve the registered scheduled task via PowerShell (Windows only).

    Returns a sanitized model or None. Refuses to import subprocess when the
    host lacks PowerShell. The dashboard page calls this only through the
    injected ``task_port``; tests inject fakes.
    """
    import shutil
    import subprocess

    ps = shutil.which("powershell") or shutil.which("pwsh")
    if ps is None:
        return None
    script = (
        "$t = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
        "if (-not $t) { exit 7 } "
        "$a = $t.Actions[0]; "
        "$info = Get-ScheduledTaskInfo -TaskName '%s' -ErrorAction SilentlyContinue; "
        "[Console]::Out.Write(($a.Execute + '|||' + $a.Arguments + '|||' + "
        "$t.TaskPath + '|||' + $t.State + '|||' + "
        "([string]$info.NextRunTime)))"
    ) % (name, name)
    try:
        cp = subprocess.run(
            [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return None
    if cp.returncode != 0 or not cp.stdout.strip():
        return None
    parts = cp.stdout.strip().split("|||")
    if len(parts) < 4:
        return None
    execute, arguments, task_path, state = parts[0], parts[1], parts[2], parts[3]
    next_run = parts[4] if len(parts) > 4 else None
    trigger_mode = None
    m = __import__("re").search(r"-TriggerMode\s+(\S+)", arguments)
    if m:
        trigger_mode = m.group(1)
    return {
        "name": name,
        "execute": execute,
        "arguments": arguments,
        "task_path": task_path,
        "enabled": state != "Disabled",
        "state": state,
        "trigger_mode": trigger_mode,
        "next_run": next_run,
        "cadence": "daily" if trigger_mode == "daily_schedule" else (
            "weekly" if trigger_mode == "scheduled_canary" else None),
    }
