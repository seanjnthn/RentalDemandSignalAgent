import streamlit as st
import dashboard._bootstrap  # standalone import fix (v0.6.1)
from dashboard.theme import apply_theme
from dashboard.components import section, match_tier_badge
from dashboard.formatters import clean, budget, period, legacy_label, money
from rdsa.dashboard_repository import get_matching_groups, get_leads

st.set_page_config(page_title="Matching review · Rental Demand Signal", page_icon=":material/compare_arrows:", layout="wide")
apply_theme(); st.markdown("# Matching review"); st.caption("Nearby is never presented as exact; unknown locations stay unconfirmed.")
groups=get_matching_groups(); legacy=[l for l in get_leads({}) if l.get("matches") and not l.get("match_types")]
tab_names=["Exact","Nearby","Tentative","No match","Legacy historical"]; tabs=st.tabs(tab_names); keys=["exact_match","nearby_alternative","tentative_match","no_match"]
for tab,key in zip(tabs,keys):
    with tab:
        section(f"{tab_names[keys.index(key)]} matches", f"{len(groups[key])} active comparisons")
        for item in groups[key]:
            lead,match=item["lead"],item["match"]
            with st.container(border=True):
                st.markdown(f"{match_tier_badge(key)} **{clean(lead.get('post_id'))}** → **{clean(match.get('property_id'))}**",unsafe_allow_html=True)
                a,b=st.columns(2)
                with a: st.markdown("**Lead**"); st.write({"area":clean(lead.get("desired_location"),"Unknown"),"type":clean(lead.get("property_type")),"bedrooms":lead.get("bedrooms"),"budget":budget(lead),"period":period(lead.get("budget_period"))})
                with b: st.markdown("**Inventory**"); st.write({"area":clean(match.get("location"),"Not recorded"),"type":clean(match.get("property_type")),"bedrooms":match.get("bedrooms"),"rent":money(match.get("price")),"availability":"See inventory record"})
                st.write({"match score":match.get("score"),"reasons":match.get("reasons"),"warnings":match.get("warnings"),"confirmation required":key!="exact_match" or bool(match.get("warnings"))})
with tabs[-1]:
    section("Legacy historical matches", "Historical records are muted and excluded from active recommendations.")
    if not legacy: st.info("No historical-only matches.")
    for lead in legacy: st.markdown(f'<span class="rdsa-badge rdsa-legacy">Historical / inactive</span> **{clean(lead.get("post_id"))}** · {legacy_label()}',unsafe_allow_html=True)
