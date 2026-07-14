import streamlit as st
from rdsa.dashboard_repository import get_leads, get_overview

@st.cache_data(ttl=60)
def cached_overview(filters): return get_overview(dict(filters))
@st.cache_data(ttl=60)
def cached_leads(filters): return get_leads(dict(filters))

def filter_controls(prefix="global"):
    with st.sidebar:
        st.markdown("### Review controls")
        date_range=st.date_input("First seen", value=(), key=f"{prefix}_dates")
        classification=st.selectbox("Classification", ["All","hot_lead","qualified_lead","watch","agent_broker","irrelevant","spam"], key=f"{prefix}_class")
        status=st.selectbox("Status", ["All","new","reviewed","contacted","responded","viewing_scheduled","converted","negotiating","rejected","duplicate","irrelevant"], key=f"{prefix}_status")
        area=st.text_input("Canonical area", key=f"{prefix}_area")
        property_type=st.text_input("Property type", key=f"{prefix}_type")
        match_type=st.selectbox("Match tier", ["All","exact_match","nearby_alternative","tentative_match","no_match"], key=f"{prefix}_match")
        if st.button("Refresh data", key=f"{prefix}_refresh"): st.cache_data.clear(); st.rerun()
        st.caption("Read-only operational surface")
        st.markdown('<span class="rdsa-badge rdsa-amber">Apify disabled</span> <span class="rdsa-badge rdsa-legacy">Telegram disabled</span>', unsafe_allow_html=True)
    result={"classification":classification,"status":status,"area":area,"property_type":property_type,"match_type":match_type}
    if len(date_range)==2: result.update(date_from=date_range[0].isoformat(),date_to=date_range[1].isoformat())
    return result

def render_kpis(data):
    from dashboard.components import kpi_card
    fields=[("Total leads","total"),("Hot","hot"),("Qualified","qualified"),("Target area","target_area"),("Active real matches","active_matches"),("Telegram delivered","telegram_delivered"),("Cumulative cost", "apify_cost"),("Cost / useful lead","cost_per_qualified")]
    cols=st.columns(4)
    for i,(name,key) in enumerate(fields):
        value=data.get(key)
        if key in ("apify_cost","cost_per_qualified"): value="—" if value is None else f"${value:.3f}"
        if key=="target_area": value=data.get("target_area", data.get("total",0)-data.get("unknown_location",0))
        if key=="active_matches": value=sum(data.get(k,0) for k in ("exact_match","nearby_alternative","tentative_match"))
        with cols[i%4]: kpi_card(name,value)
