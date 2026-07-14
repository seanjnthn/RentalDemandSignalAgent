import streamlit as st
from rdsa.dashboard_repository import get_matching_groups

st.title("Matching Review")
groups = get_matching_groups()
styles = {"exact_match": "🟢", "nearby_alternative": "🟠", "tentative_match": "🟡", "no_match": "🔴"}
for kind in ("exact_match", "nearby_alternative", "tentative_match", "no_match"):
    st.subheader(f"{styles[kind]} {kind.replace('_', ' ').title()} ({len(groups[kind])})")
    for item in groups[kind]:
        lead, match = item["lead"], item["match"]
        with st.expander(f"{lead['post_id']} · {lead['desired_location']} → {match['property_id']} · score {match['score']}"):
            st.write({"lead area": lead["desired_location"], "inventory area": match.get("location") or "not in stored match", "reasons": match["reasons"], "warnings": match["warnings"], "budget compatibility": "see reasons/warnings", "bedroom compatibility": "see reasons/warnings", "confirmation needed": bool(match["warnings"]) or kind != "exact_match"})
