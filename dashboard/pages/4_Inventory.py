import streamlit as st
from rdsa.dashboard_repository import get_inventory

st.title("Inventory")
data = get_inventory(); report = data["report"]
if report.get("missing"): st.warning("Real inventory file is missing. No fallback inventory is loaded.")
elif not report.get("ok"): st.warning("Inventory validation failed; no invalid rows are shown.")
st.info(f"Validation: {'valid' if report.get('ok') else 'invalid'} · available rows loaded: {len(data['rows'])}")
st.write("Available count by area", report.get("available_by_area", {}))
rows = []
for x in data["rows"]:
    rows.append({"property_id": x["inventory_id"], "area": x["location"], "building": x["title"], "property_type": x["property_type"], "bedrooms": x["bedrooms"], "monthly equivalent": x["price"], "annual asking": x.get("annual_asking"), "furnished": bool(x["furnished"]), "features": x.get("notes"), "availability": x.get("available_from"), "listing_url": x.get("listing_url", "")})
st.dataframe(rows, use_container_width=True, hide_index=True)
