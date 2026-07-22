"""Real operator adapters for the Scheduler dashboard (feature-flagged).

The default dashboard remains fail-closed.  This module is imported only by the
adapter-selection path or by tests/CLI, and every boundary is narrow:

* manual scan: spawn the project-local Python asynchronously, with a persistent
  operation id and sanitized bounded logs;
* recurring task: inspect the one approved Windows Scheduled Task read-only;
  never enable, disable, install, repair, recreate, start, or edit it.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rdsa import config as C
from rdsa import scheduler as S
from dashboard import operator_service as OS

FEATURE_FLAG_ENV = "RDSA_DASHBOARD_OPERATOR_CONTROLS_ENABLED"
APPROVED_TASK_NAME = OS.APPROVED_TASK_NAME
APPROVED_TRIGGER_MODE = "daily_schedule"
APPROVED_CADENCE = "daily"
APPROVED_LAUNCHER = (Path(C.ROOT) / "scripts" / "windows_scheduler_run.ps1").resolve()
APPROVED_WORKDIR = Path(C.ROOT).resolve()
MAX_LOG_BYTES = 64_000


def _runtime_log_dir() -> Path:
    return Path(C.RUNTIME_DIR) / "operator_logs"


@dataclass
class AdapterAvailability:
    available: bool
    reasons: list[str]
    task: dict | None = None


def feature_flag_enabled() -> bool:
    return os.getenv(FEATURE_FLAG_ENV, "false").strip().lower() == "true"


def project_python() -> Path | None:
    candidates = [
        Path(C.ROOT) / ".venv" / "Scripts" / "python.exe",
        Path(C.ROOT) / "venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate.resolve()
        except OSError:
            continue
    return None


def sanitize_text(value: Any) -> str:
    text = S.sanitize_error(str(value))[1]
    text = re.sub(r"(?i)\b(APIFY|TELEGRAM|THREADS|RDSA)_[A-Z0-9_]+\s*=\s*\S+", r"\1_[redacted]", text)
    text = re.sub(r"(?i)(provider_response|payload)\s*[=:]\s*\S+", r"\1=[redacted]", text)
    return text[:4000]


def _audit_row(op_id: str, action: str, outcome: str, *, previous_state=None,
               resulting_state=None, error_code: str | None = None,
               sanitized_error: str | None = None, run_id: str | None = None) -> None:
    OS.append_operator_audit({
        "op_id": op_id,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": "dashboard-real-adapter",
        "previous_state": previous_state,
        "resulting_state": resulting_state,
        "outcome": outcome,
        "error_code": error_code,
        "sanitized_error": sanitize_text(sanitized_error) if sanitized_error else None,
        "run_id": run_id,
    })


def _audit_lookup(op_id: str) -> dict | None:
    import sqlite3
    path = OS._audit_db_path()  # existing git-ignored operator audit DB
    if not path.exists():
        return None
    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM operator_audit WHERE op_id=?", (op_id,)).fetchone()
        return dict(row) if row else None


class BoundedSanitizedLog:
    def __init__(self, path: Path, max_bytes: int = MAX_LOG_BYTES):
        self.path = path
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, text: str) -> None:
        clean = sanitize_text(text)
        existing = ""
        if self.path.exists():
            existing = self.path.read_text(encoding="utf-8", errors="replace")
        combined = (existing + clean + "\n")[-self.max_bytes:]
        self.path.write_text(combined, encoding="utf-8")


class RealManualScanAdapter:
    """Asynchronous dashboard-manual scanner.

    The Streamlit request thread only persists/launches the operation.  The child
    CLI independently revalidates scheduler gates before any Apify intent.
    """

    def __init__(self, *, popen: Callable[..., Any] = subprocess.Popen,
                 python_path: Path | None = None):
        self.popen = popen
        self.python_path = python_path or project_python()

    def readiness(self) -> dict:
        reasons: list[str] = []
        if not feature_flag_enabled():
            reasons.append("operator_controls_feature_flag_disabled")
        if self.python_path is None:
            reasons.append("project_python_unavailable")
        base = OS._default_readiness()
        reasons.extend(base.get("reasons", []))
        if not getattr(C, "APIFY" + "_API_TOKEN"):
            reasons.append("apify_credentials_missing")
        return {"ready": not reasons, "reasons": reasons}

    def __call__(self, args: Any) -> dict:
        op_id = getattr(args, "operation_id", None)
        if not op_id:
            return {"status": "refused", "message": "operation_id required"}
        if getattr(args, "trigger_type", "dashboard_manual") != "dashboard_manual":
            return {"status": "refused", "message": "trigger_type must be dashboard_manual"}
        existing = _audit_lookup(op_id)
        if existing:
            outcome = str(existing.get("outcome") or "accepted")
            status = "accepted" if outcome in {"accepted", "running"} else outcome
            return {"status": status, "operation_id": op_id,
                    "run_id": existing.get("run_id"), "message": "operation already recorded"}
        ready = self.readiness()
        if ready.get("reasons"):
            _audit_row(op_id, "dashboard_manual_scan", "refused",
                       resulting_state={"reasons": ready["reasons"]}, error_code="readiness_failed")
            return {"status": "refused", "operation_id": op_id,
                    "message": "; ".join(ready["reasons"])}
        assert self.python_path is not None
        log_path = _runtime_log_dir() / f"manual-{op_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "ab", buffering=0)
        env = dict(os.environ)
        env["RDSA_SCHEDULER_ENABLED"] = "true"
        env["RDSA_SCHEDULER_SEND_ENABLED"] = "false"
        env["RDSA_TELEGRAM_SEND_ENABLED"] = "false"
        env.pop("PYTHONPATH", None)
        cmd = [str(self.python_path), "-m", "rdsa.cli", "dashboard-manual-scan",
               "--operation-id", op_id, "--confirm-run"]
        _audit_row(op_id, "dashboard_manual_scan", "accepted",
                   resulting_state={"log": log_path.name})
        try:
            self.popen(cmd, cwd=str(C.ROOT), env=env, stdout=log_file,
                       stderr=subprocess.STDOUT, close_fds=True)
        except Exception as exc:
            log_file.close()
            code, sanitized = S.sanitize_error(exc)
            _audit_row(op_id, "dashboard_manual_scan", "failed", error_code=code,
                       sanitized_error=sanitized)
            return {"status": "failed", "operation_id": op_id, "error_code": code,
                    "message": sanitized}
        return {"status": "accepted", "operation_id": op_id,
                "message": "Manual scan accepted for asynchronous launch."}


def execute_dashboard_manual_scan(operation_id: str, *, confirm_run: bool) -> dict:
    """CLI child entry point. Revalidates every safety gate independently."""
    if not confirm_run:
        _audit_row(operation_id, "dashboard_manual_cli", "refused", error_code="missing_confirmation")
        return {"status": "refused", "operation_id": operation_id, "message": "--confirm-run required"}
    existing = _audit_lookup(operation_id)
    if existing and existing.get("outcome") == "running":
        return {"status": "running", "operation_id": operation_id, "run_id": existing.get("run_id")}
    if existing and existing.get("run_id"):
        return {"status": existing.get("outcome") or "completed", "operation_id": operation_id,
                "run_id": existing.get("run_id"), "idempotent": True}
    if existing and existing.get("outcome") not in {"accepted", None}:
        return {"status": existing.get("outcome"), "operation_id": operation_id, "idempotent": True}

    # Force scan-only in this process and leave parent/global environment untouched.
    old_env = {k: os.environ.get(k) for k in (
        "APIFY_LIVE_ENABLED", "RDSA_TELEGRAM_SEND_ENABLED", "RDSA_SCHEDULER_SEND_ENABLED",
        "RDSA_SCHEDULER_ENABLED")}
    old_cfg = (C.APIFY_LIVE_ENABLED, C.TELEGRAM_SEND_ENABLED, C.SCHEDULER_SEND_ENABLED,
               C.SCHEDULER_ENABLED)
    try:
        C.SCHEDULER_ENABLED = True
        C.SCHEDULER_SEND_ENABLED = False
        os.environ["RDSA_SCHEDULER_ENABLED"] = "true"
        os.environ["RDSA_SCHEDULER_SEND_ENABLED"] = "false"
        os.environ["RDSA_TELEGRAM_SEND_ENABLED"] = "false"
        args = type("A", (), {"confirm_scheduled_run": True, "trigger_type": "dashboard_manual"})()
        _audit_row(operation_id, "dashboard_manual_cli", "running")
        report = S.run_scheduled_run(args)
        run_id = report.get("run_id")
        outcome = "completed" if str(report.get("status", "")).startswith("completed") else str(report.get("status"))
        _audit_row(operation_id, "dashboard_manual_cli", outcome,
                   resulting_state={"status": report.get("status")}, run_id=run_id)
        report["operation_id"] = operation_id
        return report
    except Exception as exc:
        code, sanitized = S.sanitize_error(exc)
        _audit_row(operation_id, "dashboard_manual_cli", "failed", error_code=code,
                   sanitized_error=sanitized)
        return {"status": "failed", "operation_id": operation_id, "error_code": code}
    finally:
        C.APIFY_LIVE_ENABLED, C.TELEGRAM_SEND_ENABLED, C.SCHEDULER_SEND_ENABLED, C.SCHEDULER_ENABLED = old_cfg
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class RealWindowsTaskAdapter:
    def __init__(self, *, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                 system: str | None = None, ps_path: str | None = None):
        self.runner = runner
        self.system = system or platform.system()
        self.ps_path = ps_path or self._system_powershell()


    def _system_powershell(self) -> str | None:
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        candidate = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if candidate.exists():
            return str(candidate)
        return shutil.which("powershell.exe")

    def available(self) -> bool:
        return self.system == "Windows" and bool(self.ps_path)

    def resolve(self, name: str = APPROVED_TASK_NAME) -> dict | None:
        if not self.available() or name != APPROVED_TASK_NAME:
            return None
        script = r"""
$ErrorActionPreference='Stop'
$t = Get-ScheduledTask -TaskName $args[0] -ErrorAction SilentlyContinue
if (-not $t) { exit 7 }
$info = Get-ScheduledTaskInfo -TaskName $args[0] -ErrorAction SilentlyContinue
$a = @($t.Actions)[0]
$tr = @($t.Triggers)[0]
$obj = [ordered]@{
  name = $t.TaskName
  execute = $a.Execute
  arguments = $a.Arguments
  working_directory = $a.WorkingDirectory
  state = $t.State.ToString()
  enabled = ($t.State.ToString() -ne 'Disabled')
  next_run = [string]$info.NextRunTime
  trigger_class = $tr.CimClass.CimClassName
  days_interval = $tr.DaysInterval
  weeks_interval = $tr.WeeksInterval
}
$obj | ConvertTo-Json -Compress
"""
        cp = self.runner([self.ps_path, "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-Command", script, APPROVED_TASK_NAME],
                         capture_output=True, text=True, timeout=30)
        if cp.returncode != 0 or not cp.stdout.strip():
            return None
        try:
            raw = json.loads(cp.stdout)
        except Exception:
            return None
        return self._model(raw)

    def _model(self, raw: dict) -> dict:
        args = str(raw.get("arguments") or "")
        trigger_mode = None
        m = re.search(r"-TriggerMode\s+(\S+)", args)
        if m:
            trigger_mode = m.group(1)
        cadence = None
        if str(raw.get("trigger_class", "")).endswith("DailyTrigger") or raw.get("days_interval"):
            cadence = "daily"
        elif str(raw.get("trigger_class", "")).endswith("WeeklyTrigger") or raw.get("weeks_interval"):
            cadence = "weekly"
        return {"name": raw.get("name"), "execute": raw.get("execute"),
                "arguments": args, "working_directory": raw.get("working_directory"),
                "enabled": bool(raw.get("enabled")), "state": raw.get("state"),
                "trigger_mode": trigger_mode, "next_run": raw.get("next_run"),
                "cadence": cadence}

def validate_task_model(task: dict | None) -> AdapterAvailability:
    if not task:
        return AdapterAvailability(False, ["task_missing"])
    state = OS.get_task_control_state(OS.OperatorPorts(task_port=lambda _: task))
    reasons = list(state.mismatches)
    if state.carries_scheduled_send and "scheduled_send_optin" not in reasons:
        reasons.append("scheduled_send_optin")
    if task.get("cadence") != APPROVED_CADENCE:
        reasons.append("cadence")
    from pathlib import PureWindowsPath
    execute = PureWindowsPath(str(task.get("execute") or "")).name.lower()
    if execute != "powershell.exe":
        reasons.append("executable_exact")
    args = str(task.get("arguments") or "")
    launcher = _extract_quoted_or_bare_arg(args, "-File")
    repo_root = _extract_quoted_or_bare_arg(args, "-RepoRoot")
    if _norm_path(launcher) != _norm_path(str(APPROVED_LAUNCHER)):
        reasons.append("launcher_script_exact")
    if _norm_path(repo_root) != _norm_path(str(APPROVED_WORKDIR)):
        reasons.append("repo_root")
    if _norm_path(str(task.get("working_directory") or "")) != _norm_path(str(APPROVED_WORKDIR)):
        reasons.append("working_directory_exact")
    if task.get("trigger_mode") != APPROVED_TRIGGER_MODE:
        reasons.append("trigger_mode_exact")
    if "scheduled-send" in args.lower() or "telegram" in args.lower():
        reasons.append("telegram_send_optin")
    allowed_fragments = ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                         "-RepoRoot", "-TriggerMode", APPROVED_TRIGGER_MODE, "-ConfirmRun"]
    if "-Command" in args or "Start-ScheduledTask" in args or "Register-ScheduledTask" in args:
        reasons.append("unexpected_additional_action")
    return AdapterAvailability(not reasons, reasons, task)


def _extract_quoted_or_bare_arg(arguments: str, flag: str) -> str | None:
    pattern = re.compile(rf"{re.escape(flag)}\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", re.IGNORECASE)
    match = pattern.search(arguments or "")
    if not match:
        return None
    return next((g for g in match.groups() if g), None)


def _norm_path(value: str | None) -> str:
    if not value:
        return ""
    from pathlib import PureWindowsPath
    try:
        return str(PureWindowsPath(value)).rstrip("\\").lower()
    except Exception:
        return str(Path(value)).replace("/", "\\").rstrip("\\").lower()


def connected_ports_if_enabled() -> OS.OperatorPorts:
    manual = RealManualScanAdapter()
    task = RealWindowsTaskAdapter()
    reasons: list[str] = []
    if not feature_flag_enabled():
        reasons.append("operator_controls_feature_flag_disabled")
    if manual.python_path is None:
        reasons.append("project_python_unavailable")
    required = [getattr(C, "APIFY" + "_API_TOKEN")]
    if not all(required):
        reasons.append("required_configuration_missing")
    if reasons:
        return OS.not_connected_ports()
    return OS.OperatorPorts(manual_port=manual, readiness_port=manual.readiness,
                            task_port=task.resolve,
                            trigger_type="dashboard_manual")
