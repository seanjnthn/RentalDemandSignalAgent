import streamlit as st
import dashboard._bootstrap  # standalone import fix (v0.6.1)
from dashboard.theme import apply_theme
from dashboard.common import cached_leads
from dashboard.components import section, table, lead_row, export_csv
from dashboard.formatters import clean

st.set_page_config(page_title="Lead inbox · Rental Demand Signal", page_icon=":material/inbox:", layout="wide")
apply_theme(); st.markdown("# Lead inbox"); st.caption("CRM-style triage for sanitized, read-only lead records.")
rows=cached_leads(tuple()); query=st.text_input("Search leads", placeholder="Search ID, area, type, or sanitized text", key="inbox_search")
quick=st.pills("Quick filters", ["All","Hot","Needs review","Unknown area"], default="All")
c1,c2,c3,c4=st.columns(4)
with c1: classes=st.multiselect("Classification", ["hot_lead","qualified_lead","watch","agent_broker","irrelevant","spam"])
with c2: statuses=st.multiselect("Status", ["new","reviewed","contacted","responded","converted","rejected"])
with c3: areas=st.multiselect("Area", sorted({x.get("desired_location") for x in rows if x.get("desired_location")}))
with c4: tiers=st.multiselect("Match tier", ["exact_match","nearby_alternative","tentative_match","no_match"])
f1,f2,f3=st.columns(3)
with f1: property_types=st.multiselect("Property type", sorted({x.get("property_type") for x in rows if x.get("property_type")}))
with f2: confidences=st.multiselect("Budget confidence", ["high","medium","low","unknown"])
with f3: telegram_state=st.selectbox("Telegram state", ["All","Delivered","Not sent"])
if st.button("Reset inbox filters", key="inbox_reset"):
    for key in ("inbox_search",): st.session_state.pop(key, None)
    st.rerun()
def keep(x):
    text=" ".join(str(x.get(k,"")) for k in ("post_id","desired_location","property_type","raw_text")).lower()
    return (not query or query.lower() in text) and (not classes or x.get("lead_class") in classes) and (not statuses or x.get("status") in statuses) and (not areas or x.get("desired_location") in areas) and (not property_types or x.get("property_type") in property_types) and (not confidences or (x.get("budget_confidence") or "unknown") in confidences) and (telegram_state == "All" or (telegram_state == "Delivered") == bool(x.get("telegram_sent"))) and (not tiers or any(t in x.get("match_types",[]) for t in tiers)) and (quick != "Hot" or x.get("lead_class")=="hot_lead") and (quick != "Needs review" or x.get("status")=="new") and (quick != "Unknown area" or x.get("desired_location")=="Unknown")
filtered=[x for x in rows if keep(x)]
section(f"{len(filtered)} leads", "Sort with the table headers; text is sanitized by the repository.")
view=[lead_row(x) for x in filtered[:100]]; table(view); export_csv(view, key="inbox_export")
if filtered:
    selected=st.selectbox("Selected lead preview", [x.get("post_id") for x in filtered])
    lead=next(x for x in filtered if x.get("post_id")==selected)
    with st.container(border=True): st.markdown(f"**{lead.get('post_id')}** · score {lead.get('lead_score',0)}"); st.caption(clean(lead.get("raw_text"), "No source text"))
