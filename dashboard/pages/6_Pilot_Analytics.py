import streamlit as st
from rdsa.dashboard_repository import get_pilot_runs, get_overview

st.title("Pilot Analytics")
st.caption("Run-log values are manually recorded; database totals are cumulative. Review status is not a false-positive rate.")
st.dataframe(get_pilot_runs(), use_container_width=True, hide_index=True)
st.subheader("Cumulative dashboard totals")
st.json(get_overview())
st.info("False-positive rate is not claimed: it requires a completed manual review denominator.")
