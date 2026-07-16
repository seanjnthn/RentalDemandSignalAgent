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
from .notifier import preview_eligible, send_lead_cards, TelegramNotifier, redact_token


# ---------------------------------------------------------------------------
# Error sanitization
# ---------------------------------------------------------------------------
def sanitize_error(exc: BaseException | str) -> tuple[str, str]:
    """Return (error_code, sanitized_error) with no secrets, paths, or raw tokens.

    error_code is a coarse, stable identifier (e.g. "apify_error", "telegram_failure",
    "cost_limit", "lock_conflict"). sanitized_error is a short human string with tokens,
    absolute paths, and Windows usernames stripped.
    """
    text = redact_token(str(exc))
    # strip absolute paths (Windows and POSIX)
    text = redact_token(text)
    text = _strip_paths(text)
    text = _strip_usernames(text)
    lowered = str(exc).lower()
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
        if len(part) > 3 and (part[1:3] == ":\\" or part.startswith("/") or "\\" in part and part[1:2] == ":"):
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
    c.commit()


def record_run_start(c, run_id: str, trigger_type: str, process_id: int, scheduler_send_enabled: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    c.execute(
        """INSERT OR REPLACE INTO scheduled_runs(
            run_id, trigger_type, started_at, status, scheduler_send_enabled, process_id)
            VALUES(?,?,?, 'starting', ?, ?)""",
        (run_id, trigger_type, now, int(bool(scheduler_send_enabled)), process_id),
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

    c = D.connect(config.DB_PATH)
    migrate_ledger(c)
    lock = SchedulerLock()
    started = False
    live_restored = False

    def _restore_flags():
        nonlocal live_restored
        config.APIFY_LIVE_ENABLED = "false"
        config.TELEGRAM_SEND_ENABLED = False
        os.environ.pop("APIFY_LIVE_ENABLED", None)
        os.environ.pop("RDSA_TELEGRAM_SEND_ENABLED", None)
        live_restored = True

    try:
        # ---- gate 2: acquire process lock ----
        if not lock.acquire(run_id):
            record_run_start(c, run_id, trigger_type, os.getpid(), scheduler_send)
            update_run(c, run_id, status="blocked_lock")
            st = lock.status()
            return _refuse(f"Scheduler lock conflict: another run is active (pid={st.get('pid')}). Aborting before Apify.")
        started = True
        record_run_start(c, run_id, trigger_type, os.getpid(), scheduler_send)

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
        argv = type("A", (), {"pilot": True, "dry_run": True, "summary": False, "confirm_send": False})()
        result = process_raw(raw, "apify", argv, c, inventory_mode="real")
        c.commit()

        new_post_ids = result.get("new_post_ids", [])
        eligible = [l for l in result["leads"]
                   if l.post_id in set(new_post_ids)
                   and preview_eligible(l)
                   and l.lead_class != "agent_broker"]

        claimed = 0
        sent = 0
        if scheduler_send and eligible:
            notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_ALLOWED_CHAT_ID)
            sent = send_lead_cards(
                notifier, eligible, c, matching_enabled=True,
                posts_scanned=result["raw_posts"], new_leads=result["new_rows"],
                new_post_ids=new_post_ids, allow_summary=False,
            )
            claimed = sent

        # ---- ledger completion ----
        usage_after = _read_usage()
        if not eligible:
            status = "completed_no_eligible_leads" if result["new_rows"] else "completed_no_new_leads"
        else:
            status = "completed"
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
