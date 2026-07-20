"""Canonical v0.8 Signal Desk Overview page."""

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st

from dashboard.overview import render_signal_desk
from dashboard.theme import apply_theme


st.set_page_config(
    page_title="Overview · Rental Demand Signal",
    page_icon=":material/analytics:",
    layout="wide",
)
apply_theme()
render_signal_desk()
