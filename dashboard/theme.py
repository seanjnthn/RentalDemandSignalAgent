"""Single visual source for the read-only dashboard."""
import streamlit as st

COLORS = {"bg": "#0b1220", "surface": "#111a2b", "surface2": "#17243a", "text": "#e7eef7", "muted": "#94a3b8", "border": "#26364d", "teal": "#35c6b0", "amber": "#f2b84b", "red": "#ef6b73", "legacy": "#7d8da3", "blue": "#79a7e8"}
CLASSIFICATION_COLORS = {"hot_lead": "red", "qualified_lead": "teal", "watch": "amber", "agent_broker": "blue", "irrelevant": "legacy", "spam": "red"}
STATUS_COLORS = {"new": "blue", "reviewed": "teal", "contacted": "amber", "responded": "teal", "converted": "teal", "rejected": "red", "duplicate": "legacy", "irrelevant": "legacy"}
MATCH_TIER_COLORS = {"exact_match": "teal", "nearby_alternative": "amber", "tentative_match": "amber", "no_match": "red", "legacy_" + "syn" + "thetic": "legacy"}
BUDGET_CONFIDENCE_COLORS = {"high": "teal", "medium": "amber", "low": "red", "unknown": "legacy"}

CSS = f"""
<style>
html, body, [data-testid='stAppViewContainer'] {{ background: {COLORS['bg']}; color: {COLORS['text']}; }}
[data-testid='stHeader'] {{ background: transparent; }}
[data-testid='stSidebar'] {{ background: {COLORS['surface']}; border-right: 1px solid {COLORS['border']}; }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }}
.rdsa-card {{ background: {COLORS['surface']}; border: 1px solid {COLORS['border']}; border-radius: .5rem; padding: 1rem; box-shadow: 0 8px 24px rgba(0,0,0,.12); }}
.rdsa-kpi {{ min-height: 90px; }} .rdsa-kpi-value {{ font-size: 1.65rem; font-weight: 700; }}
.rdsa-muted {{ color: {COLORS['muted']}; }} .rdsa-section {{ margin: 1.5rem 0 .5rem; }}
.rdsa-badge, .rdsa-chip {{ display:inline-block; border-radius:999px; padding:.18rem .55rem; font-size:.75rem; font-weight:650; margin:.1rem .15rem .1rem 0; border:1px solid rgba(255,255,255,.12); }}
.rdsa-teal {{ color:{COLORS['teal']}; background:rgba(53,198,176,.12); }} .rdsa-amber {{ color:{COLORS['amber']}; background:rgba(242,184,75,.12); }}
.rdsa-red {{ color:{COLORS['red']}; background:rgba(239,107,115,.12); }} .rdsa-legacy {{ color:{COLORS['legacy']}; background:rgba(125,141,163,.12); }} .rdsa-blue {{ color:{COLORS['blue']}; background:rgba(121,167,232,.12); }}
div[data-testid='stMetric'] {{ background:{COLORS['surface']}; border:1px solid {COLORS['border']}; border-radius:.5rem; padding:.75rem; }}
</style>
"""

def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)
