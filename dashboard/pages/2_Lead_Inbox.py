import streamlit as st
from dashboard.common import filter_controls, cached_leads

st.title("Lead Inbox")
filters = filter_controls()
rows = cached_leads(tuple(sorted(filters.items())))
display = []
for x in rows:
    budget = "—" if x["budget_max"] is None and x["budget_min"] is None else f"{x['budget_min'] or 0:,}–{x['budget_max'] or '∞'} {x.get('budget_currency') or 'IDR'}"
    display.append({"score": x["lead_score"], "classification": x["lead_class"], "first_seen": x.get("first_seen"), "post age": x.get("post_timestamp"), "area": x["desired_location"], "property": x.get("property_type") or "unknown", "bedrooms": x.get("bedrooms"), "budget": budget, "period": x.get("budget_period") or "unknown", "budget confidence": x.get("budget_confidence") or "low", "match type": ", ".join(x["match_types"]), "property IDs": ", ".join(x["matched_property_ids"]), "status": x.get("status"), "Telegram sent": bool(x.get("telegram_sent"))})
st.dataframe(display, use_container_width=True, hide_index=True)
