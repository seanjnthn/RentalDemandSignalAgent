import streamlit as st
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from dashboard.theme import apply_theme
from dashboard.components import section, table
from dashboard.formatters import money, clean, type_label
from rdsa.dashboard_repository import get_inventory, get_leads

st.set_page_config(page_title="Inventory · Rental Demand Signal", page_icon=":material/apartment:", layout="wide")
apply_theme(); st.markdown("# Active inventory"); st.caption("Only validated real inventory is shown. Historical IDs are never loaded here.")
data=get_inventory(); report=data["report"]
if report.get("missing"): st.warning("Real inventory is missing. No fallback inventory is loaded.")
elif not report.get("ok"): st.warning("Inventory validation failed; invalid rows are withheld.")
else: st.success(f"Validated {len(data['rows'])} active real properties.")
leads=get_leads({}); counts={x["inventory_id"]:sum(1 for l in leads for m in l.get("matches",[]) if not m.get("is_legacy") and m.get("property_id")==x["inventory_id"]) for x in data["rows"]}
section("Property cards")
for row in data["rows"]:
    with st.container(border=True):
        c1,c2,c3=st.columns([2,1,1]); c1.markdown(f"### {clean(row.get('title'))}"); c1.caption(clean(row.get("inventory_id"))); c2.metric("Monthly",money(row.get("price"))); c3.metric("Active matches",counts.get(row.get("inventory_id"),0)); st.write(f"{clean(row.get('location'))} · {type_label(row.get('property_type'))} · {row.get('bedrooms',0)} bedrooms · {'Furnished' if row.get('furnished') else 'Unfurnished'} · available {clean(row.get('available_from'))}")
section("Inventory table")
table([{ "Property ID":r.get("inventory_id"), "Building":r.get("title"), "Area":r.get("location"), "Type":r.get("property_type"), "Bedrooms":r.get("bedrooms"), "Monthly rent":money(r.get("price")), "Annual asking":money(r.get("annual_asking")), "Listing URL":"Available" if r.get("listing_url") else "Missing" } for r in data["rows"]])
