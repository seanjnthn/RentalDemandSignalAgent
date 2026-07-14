import streamlit as st
from rdsa.dashboard_repository import get_leads, get_overview

@st.cache_data(ttl=60)
def cached_overview(filters): return get_overview(dict(filters))

@st.cache_data(ttl=60)
def cached_leads(filters): return get_leads(dict(filters))

def filter_controls():
    with st.sidebar:
        st.header("Filters")
        date_range = st.date_input("First seen", value=())
        classification = st.selectbox("Classification", ["All", "hot_lead", "qualified_lead", "watch", "agent_broker", "irrelevant", "spam"])
        status = st.selectbox("Status", ["All", "new", "reviewed", "contacted", "responded", "viewing_scheduled", "converted", "negotiating", "rejected", "duplicate", "irrelevant"])
        area = st.text_input("Area (exact canonical value)")
        property_type = st.text_input("Property type")
        match_type = st.selectbox("Match type", ["All", "exact_match", "nearby_alternative", "tentative_match", "no_match"])
        if st.button("Refresh data"): st.cache_data.clear(); st.rerun()
    f = {"classification": classification, "status": status, "area": area, "property_type": property_type, "match_type": match_type}
    if len(date_range) == 2: f.update(date_from=date_range[0].isoformat(), date_to=date_range[1].isoformat())
    return f

def render_kpis(data):
    labels = [("Total leads", "total"), ("New", "new"), ("Hot", "hot"), ("Qualified", "qualified"), ("Watch", "watch"), ("Exact matches", "exact_match"), ("Nearby", "nearby_alternative"), ("Tentative", "tentative_match"), ("No match", "no_match"), ("Unknown location", "unknown_location"), ("Telegram delivered", "telegram_delivered")]
    cols = st.columns(4)
    for i, (label, key) in enumerate(labels): cols[i % 4].metric(label, data[key])
    c1, c2 = st.columns(2); c1.metric("Cumulative Apify cost", f"${data['apify_cost']:.3f}"); c2.metric("Cost per qualified lead", "—" if data["cost_per_qualified"] is None else f"${data['cost_per_qualified']:.3f}")
