"""Scheduler observability page (read-only).

Shows scheduler code readiness, lock status, latest scheduled run, cost posture,
and current flags. Intentionally provides NO run-now / enable / send / unlock /
task-install controls, and exposes NO tokens, chat IDs, .env values, or
Windows usernames.
"""
import streamlit as st

from dashboard.theme import apply_theme
from rdsa.dashboard_repository import get_scheduler_status

st.set_page_config(page_title="Scheduler · Rental Demand Signal", page_icon=":material/schedule:", layout="wide")
apply_theme()

st.markdown("# Scheduler")
st.caption("Read-only observability · safe daily scheduler foundation (v0.7)")

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
st.caption("This page is read-only. To activate a real schedule, an operator must "
           "install a Windows Scheduled Task out-of-band and enable the scheduler kill "
           "switches. No run, enable, send, or unlock controls are exposed here.")
