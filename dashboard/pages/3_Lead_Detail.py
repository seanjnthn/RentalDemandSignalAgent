import streamlit as st
import dashboard._bootstrap  # standalone import fix (v0.6.1)
from dashboard.theme import apply_theme
from dashboard.common import cached_leads
from dashboard.components import section, classification_badge, status_badge, match_tier_badge, score_bar, badge
from dashboard.formatters import budget, period, confidence, clean, legacy_label, money
from rdsa.dashboard_repository import get_lead, get_audit, update_lead_status

st.set_page_config(page_title="Lead detail · Rental Demand Signal", page_icon=":material/person_search:", layout="wide")
apply_theme(); st.markdown("# Lead detail")
leads=cached_leads(tuple()); ids=[x.get("post_id") for x in leads]; selected=st.selectbox("Lead", ids) if ids else None
if selected:
    lead=get_lead(selected); section("Lead summary"); cols=st.columns(4)
    facts=[("Classification",classification_badge(lead.get("lead_class"))), ("Score",score_bar(lead.get("lead_score"))), ("Area",clean(lead.get("desired_location"),"Unknown")), ("Status",status_badge(lead.get("status"))), ("Budget",budget(lead)), ("Period",period(lead.get("budget_period"))), ("Confidence",badge(confidence(lead.get("budget_confidence")),{"High":"teal","Medium":"amber","Low":"red","Unknown":"legacy"})), ("First seen",clean(lead.get("first_seen")))]
    for i,(k,v) in enumerate(facts):
        with cols[i%4]: st.markdown(f'<div class="rdsa-card"><div class="rdsa-muted">{k}</div>{v}</div>', unsafe_allow_html=True)
    section("Score explanation"); st.write(lead.get("score_breakdown") or "No component breakdown recorded.")
    section("Source"); st.caption(clean(lead.get("source_url"),"No public URL")); st.text_area("Sanitized source text", clean(lead.get("raw_text"),"No text"), height=160, disabled=True)
    section("Inventory matches")
    if not lead.get("matches"): st.info("No active real inventory match.")
    for match in lead.get("matches",[]):
        with st.container(border=True):
            if match.get("is_legacy"): st.markdown(f'<span class="rdsa-badge rdsa-legacy">Historical / inactive</span> {legacy_label()}', unsafe_allow_html=True)
            else: st.markdown(f"{match_tier_badge(match.get('match_type'))} **{clean(match.get('property_id'))}** · {money(match.get('price'))}", unsafe_allow_html=True)
            st.write({"area":clean(match.get("location"),"Not recorded"),"type":clean(match.get("property_type")),"bedrooms":match.get("bedrooms"),"score":match.get("score"),"reasons":match.get("reasons"),"warnings":match.get("warnings")})
    section("Workflow", "Only status, notes, and review timestamp can be changed.")
    statuses=["new","reviewed","contacted","responded","viewing_scheduled","converted","negotiating","rejected","duplicate","irrelevant"]
    with st.form("review_form"):
        new_status=st.selectbox("Status",statuses,index=statuses.index(lead.get("status")) if lead.get("status") in statuses else 0); notes=st.text_area("Notes",lead.get("notes") or ""); reviewed=st.text_input("Reviewed at (ISO, optional)",lead.get("reviewed_at") or ""); confirm=st.checkbox("Confirm dashboard-only update")
        if st.form_submit_button("Save review"):
            if not confirm: st.error("Confirm before saving.")
            else: update_lead_status(selected,new_status,notes,reviewed_at=reviewed or None); st.success("Saved and audited."); st.cache_data.clear(); st.rerun()
    section("Audit trail"); st.dataframe(get_audit(selected),hide_index=True,width="stretch"); section("Telegram history"); st.dataframe(lead.get("alerts") or [],hide_index=True,width="stretch")
