"""Overview page retained for Streamlit's legacy pages directory."""
import streamlit as st
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dashboard.theme import apply_theme
from dashboard.common import cached_leads, cached_overview, filter_controls, render_kpis
from dashboard.components import chart, lead_row, section, table
from dashboard.charts import classification_distribution, lead_funnel, location_distribution, match_tier_distribution

st.set_page_config(page_title="Overview · Rental Demand Signal", page_icon=":material/analytics:", layout="wide")
apply_theme()
filters = filter_controls("overview_page")
leads = cached_leads(tuple(sorted(filters.items())))
overview = cached_overview(tuple(sorted(filters.items())))
st.markdown("# Rental Demand Signal")
st.caption("Private operational intelligence · read-only review surface")
render_kpis(overview)
section("Demand shape", "A compact view of lead quality, active coverage, and target locations.")
c1, c2, c3, c4 = st.columns(4)
with c1: chart(lead_funnel(overview))
with c2: chart(classification_distribution(leads))
with c3: chart(match_tier_distribution(leads))
with c4: chart(location_distribution(leads))
section("Recent high-priority leads")
table([lead_row(lead) for lead in leads if lead.get("lead_class") in ("hot_lead", "qualified_lead")][:12], "No hot or qualified leads in this view.")
