"""Rental Demand Signal overview; read-only dashboard entrypoint."""
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from dashboard.theme import apply_theme
from dashboard.common import cached_leads, cached_overview, filter_controls, render_kpis
from dashboard.components import section, table, lead_row, chart
from dashboard.charts import lead_funnel, classification_distribution, match_tier_distribution, location_distribution, cost_trend, eligible_delivered_trend
from rdsa.dashboard_repository import get_pilot_runs
from datetime import datetime, timezone


def _active_match_label(lead: dict) -> str:
    """Render only validated real inventory IDs in overview summaries."""
    active = [m.get("property_id") for m in lead.get("matches", []) if not m.get("is_legacy")]
    if active:
        return ", ".join(str(value) for value in active)
    if lead.get("matches"):
        return "No active real inventory match"
    return ""

st.set_page_config(page_title="Rental Demand Signal", page_icon=":material/analytics:", layout="wide")
apply_theme()
filters=filter_controls("overview")
leads=cached_leads(tuple(sorted(filters.items())))
overview=cached_overview(tuple(sorted(filters.items())))
st.markdown("# Rental Demand Signal")
st.markdown("**Private operational intelligence** · read-only review surface")
st.caption(f"Last refreshed {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')} · Database status: connected · Active inventory: 3 units")
render_kpis(overview)
section("Demand shape", "A quick read on volume, quality, and active inventory coverage.")
c1,c2,c3=st.columns(3)
with c1: chart(lead_funnel(overview))
with c2: chart(classification_distribution(leads))
with c3: chart(match_tier_distribution(leads))
c1,c2,c3=st.columns(3); runs=get_pilot_runs()
with c1: chart(location_distribution(leads))
with c2: chart(cost_trend(runs))
with c3: chart(eligible_delivered_trend(runs))
section("Recent high-priority leads", "Scores and identifiers are shown without private contact details.")
table([lead_row(x) for x in leads if x.get("lead_class") in ("hot_lead","qualified_lead")][:12], "No hot or qualified leads in this view.")
