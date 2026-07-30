"""v0.7 — safe daily scheduler foundation (offline-safe, no live calls in normal use).

Provides:
- cross-platform process lock (atomic file creation, git-ignored runtime dir)
- idempotent scheduled_runs ledger helpers
- cost guard (projected monthly usage vs stop/warning thresholds)
- sanitized error recording
- run_scheduled_run orchestration with all fail-closed gates, timeout, and flag restore

This module NEVER performs a live Apify or Telegram call on import. Live execution
requires explicit in-process flag enablement after preflight (see run_scheduled_run).
"""
from __future__ import annotations

import ctypes
import json
import os
import socket
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .notifier import preview_eligible, send_lead_cards, TelegramNotifier


# ---------------------------------------------------------------------------
# Error sanitization
# ---------------------------------------------------------------------------
def sanitize_error(exc: BaseException | str) -> tuple[str, str]:
    """Return (error_code, sanitized_error) with no secrets, paths, or raw tokens.

    error_code is a coarse, stable identifier (e.g. "apify_error", "telegram_failure",
    "cost_limit", "lock_conflict"). sanitized_error is a short human string with tokens,
    absolute paths, and Windows usernames stripped.

    Redaction is idempotent: re-sanitizing already-sanitized text leaves it intact.
    """
    import re as _re

    text = str(exc)

    # --- Secret / token redaction (idempotent: skips already-[redacted] values) ---
    # Assignment / colon forms: token=..., api_token: ..., "chat_id": ..., etc.
    text = _re.sub(
        r"(?i)\b(token|api_token|bot_token|api_key|secret|password|chat_id)\b"
        r"\s*(?:=|:)\s*([^\s\[\]]+)",
        lambda m: f"{m.group(1)}=[redacted]",
        text,
    )
    # Telegram bot token form: bot12345:[redacted]
    text = _re.sub(
        r"bot\d+:[A-Za-z0-9_.-]+",
        "[redacted]",
        text,
    )
    # JSON-quoted forms: "token": "VALUE" (value may contain punctuation).

    text = _re.sub(
        r'(?i)("(?:token|api_token|bot_token|api_key|secret|password|chat_id)"\s*:\s*)'
        r'("[^"]*")',
        lambda m: f'{m.group(1)}"[redacted]"',
        text,
    )
    # HTTP Authorization header: "Authorization: Bearer [redacted]".
    text = _re.sub(
        r"(?i)\bauthorization\s*(?::|=)\s*bearer\s+([^\s\[\]]+)",
        "Authorization: Bearer [redacted]",
        text,
    )
    # Bare "Bearer <token>" occurrences.
    text = _re.sub(
        r"(?i)\bbearer\s+([A-Za-z0-9._-]{8,})",
        "Bearer [redacted]",
        text,
    )
    # URL query-string tokens: ?token=VALUE or &token=VALUE.
    text = _re.sub(
        r"(?i)([?&]token=)([^\s&\[\]]+)",
        lambda m: f"{m.group(1)}[redacted]",
        text,
    )

    # --- Path redaction (Windows drive paths and POSIX absolute paths) ---
    text = _strip_paths(text)
    text = _strip_usernames(text)

    lowered = text.lower()
    if "cost" in lowered and ("limit" in lowered or "stop" in lowered or "exceed" in lowered):
        code = "cost_limit"
    elif "lock" in lowered or "already running" in lowered:
        code = "lock_conflict"
    elif "apify" in lowered or "actor" in lowered:
        code = "apify_error"
    elif "telegram" in lowered:
        code = "telegram_failure"
    elif "inventory" in lowered:
        code = "invalid_inventory"
    elif "timeout" in lowered:
        code = "timeout"
    elif "database" in lowered or "sqlite" in lowered:
        code = "database_error"
    else:
        code = "failed"
    # keep sanitized error short and token-free
    return code, text[:280]


def _strip_paths(text: str) -> str:
    out = []
    for part in text.split():
        # Windows drive path (C:\...) or POSIX absolute path (/usr/...).
        if len(part) > 2 and (
            (len(part) > 3 and part[1:3] == ":\\")
            or part.startswith("/")
            or (len(part) > 2 and part[1:2] == ":" and "\\" in part)
        ):
            out.append("[path]")
        else:
            out.append(part)
    return " ".join(out)


def _strip_usernames(text: str) -> str:
    # Windows paths often embed the username; [path] already covers them.
    return text


# ---------------------------------------------------------------------------
# Process lock (cross-platform, dependency-free)
# ---------------------------------------------------------------------------
def _pid_alive(pid: int) -> bool:
    """Best-effort cross-platform liveness check. Returns True if the PID is
    verifiably still running; False if dead or unknown."""
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        try:
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except NotImplementedError:
        return False


class SchedulerLock:
    """Atomic-file process lock. Only one scheduled run at a time.

    The lock file stores a JSON payload: run_id, pid, started_at, hostname.
    Stale locks are NEVER auto-deleted merely because they are old; a separate
    explicit unlock (scheduler_unlock --confirm-unlock) is required. A lock whose
    process is verifiably alive is never cleared.
    """

    def __init__(self, lock_path: str | None = None):
        # Resolve at call time so test/operator overrides of config.LOCK_PATH apply.
        self.lock_path = lock_path or config.LOCK_PATH

    def _payload(self, run_id: str) -> dict:
        return {
            "run_id": run_id,
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "hostname": socket.gethostname(),
        }

    def acquire(self, run_id: str) -> bool:
        """Attempt atomic lock creation. Returns True on success, False if held."""
        path = Path(self.lock_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._payload(run_id))
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        except OSError:
            return False
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
        return True

    def release(self) -> None:
        """Remove the lock file if it exists. Safe: does not follow symlinks."""
        try:
            path = Path(self.lock_path)
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass

    def inspect(self) -> dict | None:
        """Read the lock payload, or None if absent."""
        try:
            data = Path(self.lock_path).read_text(encoding="utf-8")
            return json.loads(data)
        except (OSError, ValueError):
            return None

    def status(self) -> dict:
        """Return a dashboard-safe lock status (no secrets, no full path)."""
        payload = self.inspect()
        if not payload:
            return {"locked": False}
        pid = int(payload.get("pid", 0))
        alive = _pid_alive(pid)
        return {
            "locked": True,
            "run_id": payload.get("run_id"),
            "pid": pid,
            "started_at": payload.get("started_at"),
            "hostname": payload.get("hostname"),
            "process_alive": alive,
        }

    def force_unlock(self, *, confirm: bool) -> bool:
        """Manual unlock. Requires explicit confirmation. Never clears a lock whose
        process is verifiably still running (refuses unless confirmed AND dead)."""
        payload = self.inspect()
        if not payload:
            return True  # already unlocked
        if not confirm:
            return False
        pid = int(payload.get("pid", 0))
        if _pid_alive(pid):
            # Never clear a lock whose process is still running.
            return False
        self.release()
        return True


# ---------------------------------------------------------------------------
# Ledger helpers (idempotent; table created by db.connect via SCHEMA)
# ---------------------------------------------------------------------------
def migrate_ledger(c) -> None:
    """Ensure scheduled_runs exists. Idempotent (CREATE TABLE IF NOT EXISTS)."""
    c.execute(
        """CREATE TABLE IF NOT EXISTS scheduled_runs(
            run_id TEXT PRIMARY KEY, trigger_type TEXT NOT NULL, started_at TEXT NOT NULL,
            finished_at TEXT, status TEXT NOT NULL, actor_run_id TEXT, raw_posts INTEGER,
            normalized_posts INTEGER, existing_posts INTEGER, new_posts INTEGER,
            eligible_leads INTEGER, claimed_deliveries INTEGER, sent_cards INTEGER,
            usage_total_usd REAL, monthly_usage_usd REAL, error_code TEXT,
            sanitized_error TEXT, scheduler_send_enabled INTEGER, process_id INTEGER)"""
    )
    # v0.7.4 — idempotent progress/audit columns (ALTER is a no-op if present).
    _ledger_cols = {r[1] for r in c.execute("PRAGMA table_info(scheduled_runs)")}
    for col, definition in (
        ("current_phase", "TEXT"),
        ("heartbeat_at", "TEXT"),
        ("interruption_reason", "TEXT"),
    ):
        if col not in _ledger_cols:
            c.execute(f"ALTER TABLE scheduled_runs ADD COLUMN {col} {definition}")
    c.commit()


def record_run_start(c, run_id: str, trigger_type: str, process_id: int, scheduler_send_enabled: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    c.execute(
        """INSERT OR REPLACE INTO scheduled_runs(
            run_id, trigger_type, started_at, status, scheduler_send_enabled, process_id,
            current_phase, heartbeat_at)
            VALUES(?,?,?, 'starting', ?, ?, 'starting', ?)""",
        (run_id, trigger_type, now, int(bool(scheduler_send_enabled)), process_id, now),
    )
    c.commit()


def update_run_progress(c, run_id: str, phase: str) -> None:
    """Record lifecycle progress (idempotent). Sets current_phase + heartbeat_at.

    Never sets finished_at or any other reconciliation/result field. No secrets
    or provider responses are stored.
    """
    now = datetime.now(timezone.utc).isoformat()
    c.execute(
        "UPDATE scheduled_runs SET current_phase=?, heartbeat_at=? WHERE run_id=?",
        (phase, now, run_id),
    )
    c.commit()


def update_run(c, run_id: str, **fields) -> None:
    if "finished_at" not in fields:
        fields["finished_at"] = datetime.now(timezone.utc).isoformat()
    cols = ", ".join(f"{k}=?" for k in fields)
    vals = list(fields.values())
    vals.append(run_id)
    c.execute(f"UPDATE scheduled_runs SET {cols} WHERE run_id=?", vals)
    c.commit()


def latest_run(c) -> dict | None:
    row = c.execute(
        "SELECT * FROM scheduled_runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def last_successful_run(c) -> dict | None:
    row = c.execute(
        "SELECT * FROM scheduled_runs WHERE status='completed' OR status='completed_no_new_leads' "
        "OR status='completed_no_eligible_leads' ORDER BY finished_at DESC LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def is_terminal_status(status: str) -> bool:
    """A status is terminal if it is resolved or the explicit interrupted state."""
    return status in config.RUN_STATUS_TERMINAL_RESOLVED or status == config.RUN_STATUS_INTERRUPTED


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def detect_interrupted_runs(c, lock: "SchedulerLock | None" = None,
                            grace_seconds: int | None = None) -> list[dict]:
    """Return non-terminal scheduled runs that qualify as interruption candidates.

    A run qualifies ONLY when ALL hold:
      - its status is non-terminal (starting/preflight/.../cleanup); AND
      - its recorded process_id is NOT alive; AND
      - no active scheduler lock belongs to it (lock absent or not its run_id); AND
      - started_at is older than the conservative grace period.

    We NEVER infer interruption from age alone, and we NEVER flag a run whose
    process is alive or whose lock is active. The lock parameter defaults to a
    fresh SchedulerLock() so callers may pass a pre-inspected lock in tests.
    """
    if grace_seconds is None:
        grace_seconds = int(config.SCHEDULER_INTERRUPTION_GRACE_SECONDS)
    lock = lock or SchedulerLock()
    lock_payload = lock.inspect()
    lock_run_id = lock_payload.get("run_id") if lock_payload else None
    lock_pid = int(lock_payload.get("pid", 0)) if lock_payload else 0
    lock_alive = _pid_alive(lock_pid) if lock_pid else False

    now = datetime.now(timezone.utc)
    candidates = []
    rows = c.execute("SELECT * FROM scheduled_runs").fetchall()
    for row in rows:
        r = dict(row)
        status = r.get("status")
        if status not in config.RUN_STATUS_NON_TERMINAL:
            # Terminal/resolved rows are never interruption candidates.
            continue
        pid = int(r.get("process_id") or 0)
        if pid and _pid_alive(pid):
            # Process still running — never treat as interrupted.
            continue
        # Lock belongs to this run and is still active → still running, skip.
        if lock_alive and lock_run_id == r.get("run_id"):
            continue
        started = _parse_iso(r.get("started_at"))
        if started is None:
            # Unparseable timestamp: cannot safely judge age; require explicit review.
            continue
        elapsed = (now - started).total_seconds()
        if elapsed < grace_seconds:
            # Too recent — a normal in-flight run. Never infer from age alone.
            continue
        candidates.append(r)
    return candidates


def reconcile_run(c, run_id: str, *, confirm: bool, lock: "SchedulerLock | None" = None,
                  reason: str | None = None) -> dict:
    """Explicit operator reconciliation of an interrupted scheduled run.

    Requirements enforced:
      - explicit --confirm-reconcile required;
      - verifies the recorded PID is dead;
      - verifies no active matching lock belongs to the run;
      - refuses if the run is already terminal (completed/failed/etc.) or if its
        process is still alive or its lock is active;
      - records finished_at and an explicit `interrupted` terminal status;
      - stores a sanitized reason (no secrets/responses);
      - never touches leads, alerts, delivery_claims, or cost data;
      - never calls Apify or Telegram;
      - is idempotent: a second call on an already-reconciled run reports no-op.

    Returns a dict describing the outcome (never raises on policy refusal).
    """
    lock = lock or SchedulerLock()
    # Idempotently ensure ledger columns exist (production DBs predating this
    # migration have the table but lack current_phase/heartbeat_at/
    # interruption_reason). This is ALTER IF NOT EXISTS only — read-mostly, no
    # mutation of any row data. Never touches leads/alerts/delivery/cost.
    migrate_ledger(c)
    row = c.execute(
        "SELECT * FROM scheduled_runs WHERE run_id=?", (run_id,)
    ).fetchone()
    if row is None:
        return {"reconciled": False, "reason_refused": "unknown_run",
                "message": f"Run {run_id} not found in ledger."}
    r = dict(row)
    status = r.get("status")

    # Idempotency: already terminal → no mutation.
    if is_terminal_status(status):
        return {"reconciled": False, "already_terminal": True,
                "status": status, "idempotent": True,
                "message": f"Run {run_id} is already in terminal state '{status}'; no mutation."}

    if not confirm:
        return {"reconciled": False, "reason_refused": "missing_confirmation",
                "message": "Reconciliation refused: --confirm-reconcile is required."}

    pid = int(r.get("process_id") or 0)
    if pid and _pid_alive(pid):
        return {"reconciled": False, "reason_refused": "process_alive",
                "message": f"Reconciliation refused: process {pid} is still alive."}

    lock_payload = lock.inspect()
    lock_run_id = lock_payload.get("run_id") if lock_payload else None
    lock_pid = int(lock_payload.get("pid", 0)) if lock_payload else 0
    if _pid_alive(lock_pid) and lock_run_id == run_id:
        return {"reconciled": False, "reason_refused": "active_lock",
                "message": f"Reconciliation refused: active scheduler lock for run {run_id}."}

    # Sanitize the operator-supplied / derived reason. Strip secrets/paths.
    if not reason:
        last_phase = r.get("current_phase") or "starting"
        reason = f"Process terminated by OS while status={status}; last known phase={last_phase}."
    sanitized = sanitize_error(reason)[1]
    now = datetime.now(timezone.utc).isoformat()
    c.execute(
        "UPDATE scheduled_runs SET status=?, finished_at=?, interruption_reason=? "
        "WHERE run_id=?",
        (config.RUN_STATUS_INTERRUPTED, now, sanitized, run_id),
    )
    c.commit()
    return {"reconciled": True, "status": config.RUN_STATUS_INTERRUPTED,
            "finished_at": now, "interruption_reason": sanitized,
            "process_id": pid, "idempotent": False}


# ---------------------------------------------------------------------------
# Cost guard
# ---------------------------------------------------------------------------
def projected_monthly_usage(usage: dict, max_run_cost: float) -> float:
    """projected monthly usage = current monthly usage + configured maximum run cost."""
    current = float(usage.get("actual_usd") or usage.get("estimated_usd") or 0.0)
    return current + float(max_run_cost)


def evaluate_cost(usage: dict, max_run_cost: float):
    """Return (projected_usd, blocked, warning). No side effects.

    blocked = projected exceeds stop threshold.
    warning = projected exceeds warning threshold (informational only; never overrides stop).
    """
    projected = projected_monthly_usage(usage, max_run_cost)
    stop = float(config.APIFY_STOP_USD)
    warn = float(config.APIFY_WARN_USD)
    blocked = projected > stop
    warning = projected > warn
    return projected, blocked, warning


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def _refuse(message: str) -> dict:
    print(message)
    return {"status": "refused", "message": message}


def run_scheduled_run(args) -> dict:
    """Execute one scheduled run with all fail-closed gates.

    Refuses (no Apify/Telegram, no paid run) unless:
      - config.SCHEDULER_ENABLED is true, AND
      - args.confirm_scheduled_run is true.
    Live Apify + Telegram are enabled in-process ONLY after preflight passes.
    All process-local flags are restored on completion or error.
    """
    run_id = f"sch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    trigger_type = getattr(args, "trigger_type", "daily_schedule") or "daily_schedule"
    is_manual = trigger_type == "dashboard_manual"
    scheduler_send = config.SCHEDULER_SEND_ENABLED

    # ---- gate 1: kill switches + explicit confirmation ----
    if not config.SCHEDULER_ENABLED:
        return _refuse("Scheduler disabled: set RDSA_SCHEDULER_ENABLED=true to enable scheduled runs.")
    if not getattr(args, "confirm_scheduled_run", False):
        return _refuse("Scheduled run refused: pass --confirm-scheduled-run to execute.")

    from . import db as D
    from .cli import process_raw
    from .apify_provider import ApifyThreadsProvider
    from .inventory import validate_real_inventory_for_scan
    from .db import migrate_provenance, associate_run_leads
    from .db import claim_notification, complete_notification as _complete_notification
    from .notifier import format_completion_summary, telegram_credentials_valid, redact_token, _get

    c = D.connect(config.DB_PATH)
    migrate_ledger(c)
    lock = SchedulerLock()
    started = False
    live_restored = False

    def _restore_flags():
        nonlocal live_restored
        config.APIFY_LIVE_ENABLED = "false"
        config.TELEGRAM_SEND_ENABLED = False
        config.SCHEDULER_SEND_ENABLED = False
        os.environ.pop("APIFY_LIVE_ENABLED", None)
        os.environ.pop("RDSA_TELEGRAM_SEND_ENABLED", None)
        os.environ.pop("RDSA_SCHEDULER_SEND_ENABLED", None)
        live_restored = True

    # ---- gate 0: fail-closed interruption recovery ----
    # Before any Apify/Telegram call (and before acquiring a fresh lock), refuse
    # if there are unresolved non-terminal historical runs. This forces explicit
    # operator reconciliation and prevents auto-retrying an interrupted Actor
    # attempt. We never automatically retry or silently resolve the old run.
    try:
        interrupted = detect_interrupted_runs(c, lock=lock)
    except Exception:
        interrupted = []
    if interrupted:
        run_ids = ", ".join(r["run_id"] for r in interrupted)
        msg = (f"Scheduled run blocked: {len(interrupted)} unresolved non-terminal "
               f"historical run(s) require explicit operator reconciliation "
               f"(run scheduler-reconcile --run-id <RUN_ID> --confirm-reconcile): "
               f"{run_ids}. Refusing before Apify.")
        return _refuse(msg)

    try:
        # ---- gate 2: acquire process lock ----
        if not lock.acquire(run_id):
            record_run_start(c, run_id, trigger_type, os.getpid(), scheduler_send)
            update_run(c, run_id, status="blocked_lock")
            st = lock.status()
            return _refuse(f"Scheduler lock conflict: another run is active (pid={st.get('pid')}). Aborting before Apify.")
        started = True
        record_run_start(c, run_id, trigger_type, os.getpid(), scheduler_send)
        update_run_progress(c, run_id, "preflight")

        # ---- gate 3: inventory validation ----
        rows, inv_report = validate_real_inventory_for_scan(config.INVENTORY_REAL_CSV)
        if not inv_report.get("ok") or not rows:
            update_run(c, run_id, status="failed", error_code="invalid_inventory",
                       sanitized_error="Real inventory missing or invalid.")
            return {"status": "failed", "run_id": run_id, "reason": "invalid_inventory"}

        # ---- gate 4: cost guard (before any Apify request) ----
        usage = _read_usage()
        projected, blocked, warning = evaluate_cost(usage, config.SCHEDULER_MAX_CHARGE_USD)
        if warning:
            print(f"[warn] projected monthly usage {projected:.3f} USD exceeds warning threshold "
                  f"{config.APIFY_WARN_USD} USD (informational; stop threshold {config.APIFY_STOP_USD} USD)")
        if blocked:
            update_run(c, run_id, status="blocked_cost_limit",
                       monthly_usage_usd=float(usage.get("actual_usd", 0)),
                       usage_total_usd=config.SCHEDULER_MAX_CHARGE_USD,
                       error_code="cost_limit",
                       sanitized_error=f"Projected monthly usage {projected:.3f} USD exceeds stop {config.APIFY_STOP_USD} USD.")
            return {"status": "blocked_cost_limit", "run_id": run_id, "projected_usd": projected}

        # ---- enable live execution in-process only (after all preflight) ----
        update_run_progress(c, run_id, "actor_started")
        os.environ["APIFY_LIVE_ENABLED"] = "true"
        config.APIFY_LIVE_ENABLED = "true"
        if scheduler_send:
            os.environ["RDSA_TELEGRAM_SEND_ENABLED"] = "true"
            config.TELEGRAM_SEND_ENABLED = True

        # ---- gate 5: one batched Apify Actor request (no paid retry) ----
        provider = ApifyThreadsProvider()
        raw = provider.search_batched(
            config.SCHEDULER_QUERIES,
            max_posts_per_query=config.SCHEDULER_MAX_PER_QUERY,
            max_total=config.SCHEDULER_MAX_TOTAL,
            max_total_charge_usd=config.SCHEDULER_MAX_CHARGE_USD,
            timeout=config.SCHEDULER_TIMEOUT_SECONDS,
        )
        update_run_progress(c, run_id, "actor_completed")
        argv = type("A", (), {"pilot": True, "dry_run": True, "summary": False, "confirm_send": False})()
        result = process_raw(raw, "apify", argv, c, inventory_mode="real")
        update_run_progress(c, run_id, "persistence")
        c.commit()

        new_post_ids = result.get("new_post_ids", [])
        eligible = [l for l in result["leads"]
                   if l.post_id in set(new_post_ids)
                   and preview_eligible(l)
                   and l.lead_class != "agent_broker"]

        # ---- provenance: link every processed lead to this run (idempotent) ----
        migrate_provenance(c)
        new_set = set(new_post_ids)
        eligible_set = {l.post_id for l in eligible}
        associations = [
            {"post_id": l.post_id, "inserted_this_run": l.post_id in new_set,
             "classification": l.lead_class, "eligible": l.post_id in eligible_set}
            for l in result["leads"]
        ]
        associate_run_leads(c, run_id, associations)

        # Determine terminal status BEFORE delivery (needed by completion summary).
        if not eligible:
            status = "completed_no_eligible_leads" if result["new_rows"] else "completed_no_new_leads"
        else:
            status = "completed"

        claimed = 0
        sent = 0

        # Determine whether Telegram delivery should happen for this run.
        # - Scheduled runs: gated by scheduler_send (RDSA_SCHEDULER_SEND_ENABLED).
        # - Manual dashboard scans: gated by MANUAL_SEND_ENABLED (process-local,
        #   never persists globally).
        should_telegram = (scheduler_send or
                          (is_manual and config.MANUAL_SEND_ENABLED))

        if should_telegram:
            update_run_progress(c, run_id, "delivery")
            notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_ALLOWED_CHAT_ID)

            # 1. Send eligible lead cards first (cards-before-summary order).
            if eligible:
                sent = send_lead_cards(
                    notifier, eligible, c, matching_enabled=True,
                    posts_scanned=result["raw_posts"], new_leads=result["new_rows"],
                    new_post_ids=new_post_ids, allow_summary=False,
                )
                claimed = sent

            # 2. Send completion summary for manual scans (v0.9).
            if is_manual:
                # Compute classification counts for the summary.
                all_leads = result.get("leads", [])
                qualified_count = sum(1 for l in all_leads if _get(l, "lead_class") == "qualified_lead")
                watch_count = sum(1 for l in all_leads if _get(l, "lead_class") == "watch")
                agent_broker_count = sum(1 for l in all_leads if _get(l, "lead_class") == "agent_broker")
                inventory_match_count = sum(
                    1 for l in eligible if _get(l, "matched_inventory", [])
                )
                duration_str = ""
                started_at = None
                finished_at = datetime.now(timezone.utc).isoformat()
                try:
                    ledger = c.execute(
                        "SELECT started_at FROM scheduled_runs WHERE run_id=?",
                        (run_id,)
                    ).fetchone()
                    if ledger:
                        started_at = ledger["started_at"]
                        try:
                            start_dt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
                            end_dt = datetime.fromisoformat(str(finished_at).replace("Z", "+00:00"))
                            secs = int((end_dt - start_dt).total_seconds())
                            if secs >= 60:
                                duration_str = f"{secs // 60}m {secs % 60}s"
                            else:
                                duration_str = f"{secs}s"
                        except (ValueError, TypeError):
                            pass
                except Exception:
                    pass

                stats = {
                    "status": status,
                    "run_id": run_id,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duration": duration_str,
                    "raw_posts": result.get("raw_posts", 0),
                    "existing_posts": result.get("duplicates", 0),
                    "new_posts": result.get("new_rows", 0),
                    "qualified_count": qualified_count,
                    "watch_count": watch_count,
                    "agent_broker_count": agent_broker_count,
                    "eligible_count": len(eligible),
                    "inventory_match_count": inventory_match_count,
                    "sent_cards": sent,
                    "monthly_usage_usd": str(usage.get("actual_usd", "")),
                }
                summary_text = format_completion_summary(stats)

                # Idempotent: claim before sending.
                if claim_notification(c, run_id, "manual_completion"):
                    try:
                        msg_id = notifier.send(summary_text)
                        _complete_notification(c, run_id, msg_id, "manual_completion")
                    except Exception as exc:
                        print(f"{redact_token(exc)}")

        update_run_progress(c, run_id, "cleanup")
        # ---- ledger completion ----
        usage_after = _read_usage()
        last_run_id = getattr(provider, "last_run_id", None)
        # The real provider does not always expose last_run_id; only persist a
        # genuine value (never a mock/test double) into the ledger.
        if last_run_id is None or not isinstance(last_run_id, (str, int)):
            last_run_id = None
        update_run(
            c, run_id,
            status=status,
            actor_run_id=last_run_id,
            raw_posts=result["raw_posts"],
            normalized_posts=result["normalized_posts"],
            existing_posts=result["duplicates"],
            new_posts=result["new_rows"],
            eligible_leads=len(eligible),
            claimed_deliveries=claimed,
            sent_cards=sent,
            usage_total_usd=config.SCHEDULER_MAX_CHARGE_USD,
            monthly_usage_usd=float(usage_after.get("actual_usd", 0)),
        )
        return {"status": status, "run_id": run_id, "new_posts": result["new_rows"],
                "eligible": len(eligible), "sent": sent}

    except Exception as exc:  # fail closed, record, never auto-retry
        code, sanitized = sanitize_error(exc)
        try:
            update_run(c, run_id, status="failed", error_code=code, sanitized_error=sanitized)
        except Exception:
            pass
        print(f"[error] scheduled run failed ({code}): {sanitized}")
        # v0.9: For manual scans, send a sanitized failure notification
        # (best-effort; never replaces the actual scheduler failure state).
        if is_manual and config.MANUAL_SEND_ENABLED:
            try:
                if claim_notification(c, run_id, "manual_failure"):
                    notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN,
                                                config.TELEGRAM_ALLOWED_CHAT_ID)
                    msg = f"⚠️ *RDSA manual scan failed*\n\n*Run ID:* `{run_id}`\n*Error:* {sanitized}"
                    msg_id = notifier.send(msg)
                    _complete_notification(c, run_id, msg_id, "manual_failure")
            except Exception:
                pass
        return {"status": "failed", "run_id": run_id, "error_code": code}
    finally:
        _restore_flags()
        if started:
            lock.release()


def read_usage_safe() -> dict:
    """Read apify_usage.json without raising. Safe for dashboard/CLI status."""
    return _read_usage()


def _read_usage() -> dict:
    try:
        from pathlib import Path
        p = Path(config.APIFY_USAGE_PATH)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"actual_usd": 0.0, "estimated_usd": 0.0}
