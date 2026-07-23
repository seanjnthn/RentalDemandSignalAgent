"""Rental Demand Signal read-only Signal Desk entrypoint."""

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from dashboard.overview import render_signal_desk
from dashboard.theme import apply_theme


def _active_match_label(lead: dict) -> str:
    """Retain the legacy test seam while excluding inactive inventory rows."""

    active = [
        match.get("property_id")
        for match in lead.get("matches", [])
        if not match.get("is_legacy")
    ]
    if active:
        return ", ".join(str(value) for value in active)
    return "No active real inventory match" if lead.get("matches") else ""


st.set_page_config(
    page_title="Rental Demand Signal",
    page_icon=":material/analytics:",
    layout="wide",
)
apply_theme()
render_signal_desk()
