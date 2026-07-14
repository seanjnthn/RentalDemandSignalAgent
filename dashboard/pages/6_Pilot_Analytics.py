import streamlit as st
from dashboard.theme import apply_theme
from dashboard.components import section, chart, table
from dashboard.charts import raw_normalized_new_funnel, classification_by_run, eligible_delivered_trend, budget_confidence_distribution, tiers_by_run, cost_trend, cumulative_cost
from dashboard.common import cached_leads
from rdsa.dashboard_repository import get_pilot_runs

st.set_page_config(page_title="Pilot analytics · Rental Demand Signal", page_icon=":material/query_stats:", layout="wide")
apply_theme(); st.markdown("# Pilot analytics"); st.caption("Run-log values are manually recorded; database totals are cumulative. No definitive false-positive rate is claimed without a sufficient review denominator.")
runs=get_pilot_runs(); leads=cached_leads(tuple()); section("Per-run quality")
c1,c2,c3=st.columns(3)
with c1: chart(raw_normalized_new_funnel(runs))
with c2: chart(classification_by_run(runs))
with c3: chart(eligible_delivered_trend(runs))
c1,c2,c3=st.columns(3)
with c1: chart(budget_confidence_distribution(leads))
with c2: chart(tiers_by_run(runs))
with c3: chart(cost_trend(runs))
section("Cumulative view"); c1,c2=st.columns(2)
with c1: chart(cumulative_cost(runs))
with c2: table([{"Run":r.get("run"),"Raw":r.get("raw"),"Normalized":r.get("normalized"),"New":r.get("new"),"Unknown location":r.get("unknown_location"),"Cost":r.get("apify_cost")} for r in runs],"No pilot runs recorded.")
section("Review boundary"); st.info("Manual review quality is intentionally reported as a boundary, not a computed false-positive rate. The dashboard does not infer quality from delivery or classification alone.")
