import streamlit as st
from dashboard.common import cached_leads
from rdsa.dashboard_repository import get_lead, get_audit, update_lead_status

st.title("Lead Detail")
leads = cached_leads(tuple())
post_id = st.selectbox("Lead", [x["post_id"] for x in leads] if leads else [])
if post_id:
    lead = get_lead(post_id)
    st.caption(f"Public source: {lead.get('source_url') or 'not available'}")
    st.text_area("Sanitized post text", lead.get("raw_text", ""), height=150, disabled=True)
    c1, c2, c3 = st.columns(3); c1.metric("Score", lead["lead_score"]); c2.metric("Classification", lead["lead_class"]); c3.metric("Status", lead["status"])
    st.json({"area": lead["desired_location"], "property_type": lead.get("property_type"), "bedrooms": lead.get("bedrooms"), "budget_min": lead.get("budget_min"), "budget_max": lead.get("budget_max"), "currency": lead.get("budget_currency"), "period": lead.get("budget_period"), "confidence": lead.get("budget_confidence"), "move_in": lead.get("move_in_date"), "duration": lead.get("rental_duration"), "requirements": lead.get("special_requirements")})
    st.subheader("Score breakdown"); st.json(lead.get("score_breakdown", []))
    if lead.get("matches") and not lead.get("match_types"):
        st.info("No active real inventory match")
    st.subheader("Structured matches"); st.json(lead.get("matches", []))
    st.subheader("Telegram delivery metadata"); st.json(lead.get("alerts", []))
    st.write({"first_seen": lead.get("first_seen"), "last_seen": lead.get("last_seen"), "reviewed_at": lead.get("reviewed_at")})
    statuses = ["new", "reviewed", "contacted", "responded", "viewing_scheduled", "converted", "negotiating", "rejected", "duplicate", "irrelevant"]
    with st.form("review"):
        new_status = st.selectbox("Status", statuses, index=statuses.index(lead["status"]) if lead["status"] in statuses else 0)
        notes = st.text_area("Notes", lead.get("notes", "")); reviewed = st.text_input("Reviewed at (ISO, optional)", lead.get("reviewed_at") or "")
        confirm = st.checkbox("Confirm this dashboard-only update")
        if st.form_submit_button("Save review"):
            if not confirm: st.error("Confirm before saving.")
            else:
                update_lead_status(post_id, new_status, notes, reviewed_at=reviewed or None); st.success("Saved and audited."); st.cache_data.clear(); st.rerun()
    st.subheader("Audit history"); st.dataframe(get_audit(post_id), hide_index=True, use_container_width=True)
