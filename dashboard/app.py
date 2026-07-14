"""Read-only-by-default Streamlit entrypoint."""
import streamlit as st
from dashboard.common import cached_leads, cached_overview, filter_controls, render_kpis

st.set_page_config(page_title="Rental Demand Signal", page_icon="🏠", layout="wide")

st.title("Rental Demand Signal")
st.caption("Local operational review · read-only by default")
filters = filter_controls()
render_kpis(cached_overview(tuple(sorted(filters.items()))))
st.subheader("Lead snapshot")
rows = cached_leads(tuple(sorted(filters.items())))
st.dataframe([{"score": x["lead_score"], "classification": x["lead_class"], "area": x["desired_location"], "property": x["property_type"], "status": x["status"], "matches": ", ".join(x["matched_property_ids"])} for x in rows[:25]], use_container_width=True, hide_index=True)
