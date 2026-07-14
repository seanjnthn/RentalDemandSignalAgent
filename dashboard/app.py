"""Read-only-by-default Streamlit entrypoint."""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from dashboard.common import cached_leads, cached_overview, filter_controls, render_kpis

st.set_page_config(page_title="Rental Demand Signal", page_icon="🏠", layout="wide")

st.title("Rental Demand Signal")
st.caption("Local operational review · read-only by default")
filters = filter_controls()
render_kpis(cached_overview(tuple(sorted(filters.items()))))
st.subheader("Lead snapshot")
rows = cached_leads(tuple(sorted(filters.items())))
def _active_match_label(lead: dict) -> str:
    active = [m["property_id"] for m in lead.get("matches", []) if not m.get("is_legacy")]
    if active:
        return ", ".join(active)
    if lead.get("matches"):
        return "No active real inventory match"
    return ""
st.dataframe([{"score": x["lead_score"], "classification": x["lead_class"], "area": x["desired_location"], "property": x["property_type"], "status": x["status"], "matches": _active_match_label(x)} for x in rows[:25]], use_container_width=True, hide_index=True)
