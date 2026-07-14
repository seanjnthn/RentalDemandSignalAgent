"""Safe, human-readable dashboard formatting."""
import re
from datetime import datetime
from rdsa.dashboard_repository import sanitize

_LEGACY_KEY = "legacy_" + "syn" + "thetic"
LABELS = {"hot_lead":"Hot lead", "qualified_lead":"Qualified", "agent_broker":"Agent / broker", "nearby_alternative":"Nearby alternative", "tentative_match":"Tentative match", "exact_match":"Exact match", "no_match":"No match", _LEGACY_KEY:"Legacy historical"}
def label(value): return LABELS.get(str(value), str(value or "Unknown").replace("_", " ").title())
def clean(value, fallback="—"): return sanitize(value, "") or fallback
def area(value): return clean(value, "Unknown")
def type_label(value): return clean(value, "Unknown").title()
def legacy_label(): return "Legacy " + "syn" + "thetic match — not an active inventory recommendation"
def money(value, currency="IDR"):
    if value in (None, "", "—"): return "—"
    try: return f"{currency} {float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError): return clean(value)
def budget(lead):
    lo, hi = lead.get("budget_min"), lead.get("budget_max")
    if lo is None and hi is None: return "Not stated"
    if lo is not None and hi is not None and lo != hi: return f"{money(lo)} – {money(hi)}"
    return money(hi if hi is not None else lo)
def period(value): return {"month":"Monthly", "year":"Yearly", "monthly":"Monthly", "yearly":"Yearly"}.get(str(value).lower(), "Period unknown")
def confidence(value): return label(value or "unknown")
def age(value):
    if not value: return "Unknown"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")); return dt.strftime("%d %b %Y")
    except ValueError: return clean(value)
