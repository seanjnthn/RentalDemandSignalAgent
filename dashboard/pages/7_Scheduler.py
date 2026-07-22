"""Scheduler observability + scan-only operator controls page.

The upper Scheduler status area remains STRICTLY READ-ONLY (unchanged
observability: code readiness, lock, ledger, cost, interruption recovery).

The 'Operator controls' section adds one scan-only, confirmation-gated
Streamlit form:
  - Run lead search now (reuses the existing scheduler pipeline)

The page never imports subprocess, PowerShell, or Windows APIs directly.
All side effects go through dashboard.operator_service, whose ports are
dependency-injected (tests inject fakes; no real Apify / Telegram /
Task Scheduler call is made on import or on render).
"""
import sys
import uuid
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from dashboard import operator_service as OS
from dashboard.theme import apply_theme
from dashboard.operator_service import OperatorPorts
from rdsa import config as C
from rdsa.dashboard_repository import get_scheduler_status


# Test seam: a test may set st.session_state["_operator_ports"] to inject
# fake/connected ports so the page performs no real external call.
#
# Phase C1 fail-closed wiring: without an explicitly injected OperatorPorts,
# the page defaults to NOT_CONNECTED ports so it can never reach a real manual
# run, PowerShell, the Windows Task Scheduler, Apify, or Telegram on import or
# render. A real (connected) adapter is reachable only after an operator
# explicitly injects one in a later phase.
def _ports() -> OperatorPorts:
    injected = st.session_state.get("_operator_ports")
    if isinstance(injected, OperatorPorts):
        return injected
    if getattr(C, "DASHBOARD_OPERATOR_CONTROLS_ENABLED", False):
        try:
            from dashboard.operator_adapters import connected_ports_if_enabled
            return connected_ports_if_enabled()
        except Exception:
            return OS.not_connected_ports()
    return OS.not_connected_ports()


st.set_page_config(page_title="Scheduler · Rental Demand Signal", page_icon=":material/schedule:", layout="wide")
apply_theme()

st.markdown("# Scheduler")
st.caption("Read-only observability · safe daily scheduler foundation (v0.7)")


# ===========================================================================
# READ-ONLY STATUS AREA (unchanged)
# ===========================================================================
status = get_scheduler_status()

s1, s2, s3, s4 = st.columns(4)
s1.metric("Code readiness", status.get("code_readiness", "unknown"))
s2.metric("Scheduler enabled", "yes" if status.get("scheduler_enabled") else "no")
s3.metric("Scheduled sending", "yes" if status.get("scheduler_send_enabled") else "no")
s4.metric("Process lock", "held" if status.get("lock", {}).get("locked") else "free")

st.divider()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Current flags")
    f1, f2, f3, f4 = st.columns(4)
    f1.write("**Apify live**"); f1.badge("on" if status.get("apify_live_enabled") else "off")
    f2.write("**Telegram send**"); f2.badge("on" if status.get("telegram_send_enabled") else "off")
    f3.write("**Scheduler enabled**"); f3.badge("on" if status.get("scheduler_enabled") else "off")
    f4.write("**Scheduled send**"); f4.badge("on" if status.get("scheduler_send_enabled") else "off")

with c2:
    st.subheader("Cost posture")
    usage = status.get("monthly_usage_usd", 0.0)
    stop = status.get("stop_usd", 0.0)
    warn = status.get("warn_usd", 0.0)
    st.metric("Monthly usage (USD)", f"{usage:.3f}")
    st.metric("Stop threshold (USD)", f"{stop:.3f}")
    st.metric("Warning threshold (USD)", f"{warn:.3f}")
    remaining = max(0.0, stop - usage)
    st.progress(min(1.0, usage / stop) if stop else 0.0, text=f"Remaining to stop: ${remaining:.3f}")

st.divider()

st.subheader("Process lock")
lock = status.get("lock", {})
if lock.get("locked"):
    st.warning(f"Lock held · run_id={lock.get('run_id')} · pid={lock.get('pid')} · "
               f"alive={lock.get('process_alive')} · started={lock.get('started_at')}")
else:
    st.success("No active scheduler lock.")

st.subheader("Latest scheduled run")
latest = status.get("latest_run")
if not latest:
    st.info("No scheduled runs recorded yet.")
else:
    cols = st.columns(4)
    cols[0].metric("Status", latest.get("status"))
    cols[1].metric("Raw / New", f"{latest.get('raw_posts')} / {latest.get('new_posts')}")
    cols[2].metric("Eligible", latest.get("eligible_leads"))
    cols[3].metric("Sent cards", latest.get("sent_cards"))
    if latest.get("sanitized_error"):
        st.error(f"Error [{latest.get('error_code')}]: {latest.get('sanitized_error')}")
    st.caption(f"Trigger: {latest.get('trigger_type')} · "
               f"started {latest.get('started_at')} · finished {latest.get('finished_at')}")

st.subheader("Last successful run")
last_ok = status.get("last_successful_run")
if not last_ok:
    st.info("No successful scheduled run recorded yet.")
else:
    st.write(f"Status **{last_ok.get('status')}** · "
             f"new {last_ok.get('new_posts')} · sent {last_ok.get('sent_cards')} · "
             f"finished {last_ok.get('finished_at')}")

st.divider()

st.subheader("Interrupted runs (read-only)")
interrupted = status.get("interrupted_runs") or []
if not interrupted:
    st.success("No interrupted or unresolved scheduled runs detected.")
else:
    for rec in interrupted:
        rid = rec.get("run_id")
        phase = rec.get("current_phase")
        hb = rec.get("heartbeat_at")
        state = rec.get("reconciliation")  # "required" or "completed"
        reason = rec.get("interruption_reason")
        if state == "completed":
            st.warning(f"⚠ Run **{rid}** · status={rec.get('status')} · "
                       f"last phase={phase} · heartbeat={hb} · "
                       f"**reconciliation completed**"
                       + (f" · reason: {reason}" if reason else ""))
        else:
            st.error(f"⛔ Run **{rid}** · status={rec.get('status')} · "
                     f"last phase={phase} · heartbeat={hb} · "
                     f"**manual reconciliation REQUIRED** (run the CLI "
                     f"`scheduler-reconcile --run-id {rid} --confirm-reconcile` "
                     f"out-of-band). No reconcile control is exposed here.")
    st.caption("This section is strictly read-only. Manual reconciliation is an "
               "explicit, confirmed CLI operator action and is never triggered "
               "from the dashboard.")

st.divider()
st.caption("This page is read-only. To activate a real schedule, an operator must "
           "install a Windows Scheduled Task out-of-band and enable the scheduler kill "
           "switches. No run, enable, send, or unlock controls are exposed here.")


# ===========================================================================
# Small render helpers (no side effects beyond st.* display)
# Defined before first use so a form-submit rerun can call them.
# ===========================================================================
def _render_scan_result(result: "OS.ScanResult") -> None:
    d = result.to_dict()
    if d.get("accepted"):
        st.session_state["_last_scan_run_id"] = d.get("run_id")
        st.session_state["_manual_operation_accepted"] = True
        st.success(d.get("message") or "Manual search accepted.")
    elif d.get("status") == "failed":
        st.error(f"[{d.get('error_code')}] {d.get('message')}")
    else:
        st.warning(d.get("message") or "Manual search was not started.")


# ===========================================================================
# OPERATOR CONTROLS (manual scan only, confirmation-gated, visually separate)
# ===========================================================================
st.divider()
st.markdown("### Operator controls")
st.caption("Scan-only. Every action requires an explicit confirmation. "
           "Telegram delivery is Off. Recurring enable/disable controls are deferred.")


# ---- Manual lead search ------------------------------------------------------
with st.container(border=True):
    st.subheader("Run lead search")
    st.caption("Mode: **Scan only** — discovers and stores leads; never sends Telegram.")

    ports = _ports()
    readiness = OS.get_manual_run_readiness(ports)
    ready = readiness.ready
    task = OS.get_task_control_state(ports)

    # Cost / usage readouts (read-only evidence).
    projected = float(status.get("monthly_usage_usd", 0.0)) + float(C.SCHEDULER_MAX_CHARGE_USD)
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Monthly usage (USD)", f"{status.get('monthly_usage_usd', 0.0):.3f}")
    m2.metric("Projected maximum cost (USD)", f"{projected:.3f}")
    m3.metric("Warn threshold (USD)", f"{status.get('warn_usd', 0.0):.3f}")
    m4.metric("Stop threshold (USD)", f"{status.get('stop_usd', 0.0):.3f}")
    unresolved = any(r.get("reconciliation") == "required" for r in (status.get("interrupted_runs") or []))
    m5.metric("Lock state", "held" if status.get("lock", {}).get("locked") else "free")
    m6.metric("Unresolved-run state", "yes" if unresolved else "no")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Mode", "Scan only")
    r2.metric("Telegram delivery", "Off")
    r3.metric("Credentials/configuration readiness", "ready" if ready else "blocked")
    r4.metric("Installed task state", "Enabled" if task.enabled else ("Disabled" if task.exists else "Not registered"))

    if not ready:
        st.warning("Manual search is disabled: " + "; ".join(readiness.reasons))

    with st.form("manual_search_form"):
        st.session_state.setdefault("_manual_operation_id", uuid.uuid4().hex[:12])
        st.checkbox("I confirm a manual scan now (scan only, no delivery).",
                    value=False, key="manual_confirm")
        submitted = st.form_submit_button(
            "Run search now",
            type="primary",
            disabled=(not ready) or bool(st.session_state.get("_manual_operation_accepted")),
        )
        if submitted:
            confirm = bool(st.session_state.get("manual_confirm", False))
            result = OS.start_manual_scan(
                confirm=confirm,
                operation_id=st.session_state.get("_manual_operation_id"),
                ports=ports,
            )
            _render_scan_result(result)

    # Read-only poll of the last accepted run, when one exists.
    if st.session_state.get("_last_scan_run_id"):
        st.caption(f"Last accepted run: {st.session_state['_last_scan_run_id']} "
                   "— poll its status on the Scheduler read-only area above.")


with st.container(border=True):
    st.subheader("Installed Windows Scheduled Task (read-only)")
    st.caption("Recurring schedule controls are deferred. The dashboard only displays the installed task state; it never enables, disables, starts, recreates, repairs, or modifies the task.")
    task = OS.get_task_control_state(ports)
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Task name", task.name)
    if task.exists:
        t2.metric("Task Enabled/Disabled", "Enabled" if task.enabled else "Disabled")
        t3.metric("Cadence", task.cadence or "unknown")
        t4.metric("Next run", task.next_run or "n/a")
    else:
        t2.metric("Task Enabled/Disabled", "Not registered")
        t3.metric("Cadence", "n/a")
        t4.metric("Next run", "n/a")
    if task.exists and not task.valid:
        st.warning("Task definition evidence differs from the approved read-only model: " + "; ".join(task.mismatches))
    if task.carries_scheduled_send:
        st.error("Task evidence carries a scheduled-send opt-in. This dashboard still exposes no task mutation control.")
