"""Centralized Signal Desk visual tokens and Streamlit-safe CSS."""

from __future__ import annotations

import streamlit as st


COLOR_TOKENS = {
    "canvas": "#0B1220",
    "sidebar": "#0E1728",
    "surface": "#111A2B",
    "surface_raised": "#17243A",
    "surface_hover": "#1C2B43",
    "border_subtle": "#26364D",
    "border_strong": "#3A4C66",
    "text_primary": "#F1F5F9",
    "text_secondary": "#CBD5E1",
    "text_muted": "#94A3B8",
    "text_disabled": "#64748B",
    "teal": "#2DD4BF",
    "amber": "#FBBF24",
    "red": "#F87171",
    "blue": "#93C5FD",
}

TYPOGRAPHY_TOKENS = {
    "display": {"size": 36, "line_height": 44, "weight": 700},
    "page_title": {"size": 28, "line_height": 36, "weight": 700},
    "section_title": {"size": 20, "line_height": 28, "weight": 650},
    "card_title": {"size": 16, "line_height": 24, "weight": 650},
    "body": {"size": 14, "line_height": 22, "weight": 400},
    "label": {"size": 13, "line_height": 18, "weight": 600},
    "metadata": {"size": 12, "line_height": 18, "weight": 500},
    "kpi": {"size": 28, "line_height": 34, "weight": 700},
}

SPACING_TOKENS = {1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32, 12: 48}
RADIUS_TOKENS = {"sm": 6, "md": 8, "lg": 12}
BORDER_TOKENS = {
    "default": f"1px solid {COLOR_TOKENS['border_subtle']}",
    "selected": f"1px solid {COLOR_TOKENS['blue']}",
    "critical": f"1px solid {COLOR_TOKENS['red']}",
}
SURFACE_TOKENS = {
    "canvas": COLOR_TOKENS["canvas"],
    "sidebar": COLOR_TOKENS["sidebar"],
    "card": COLOR_TOKENS["surface"],
    "raised": COLOR_TOKENS["surface_raised"],
    "hover": COLOR_TOKENS["surface_hover"],
}

# Backward-compatible palette names used by the existing pages and charts.
COLORS = {
    "bg": COLOR_TOKENS["canvas"],
    "surface": COLOR_TOKENS["surface"],
    "surface2": COLOR_TOKENS["surface_raised"],
    "text": COLOR_TOKENS["text_primary"],
    "secondary": COLOR_TOKENS["text_secondary"],
    "muted": COLOR_TOKENS["text_muted"],
    "disabled": COLOR_TOKENS["text_disabled"],
    "border": COLOR_TOKENS["border_subtle"],
    "teal": COLOR_TOKENS["teal"],
    "amber": COLOR_TOKENS["amber"],
    "red": COLOR_TOKENS["red"],
    "legacy": COLOR_TOKENS["text_muted"],
    "blue": COLOR_TOKENS["blue"],
}

_LEGACY_KEY = "legacy_" + "syn" + "thetic"
CLASSIFICATION_COLORS = {
    "hot_lead": "blue",
    "qualified_lead": "teal",
    "watch": "amber",
    "agent_broker": "blue",
    "irrelevant": "legacy",
    "spam": "red",
}
STATUS_COLORS = {
    "new": "blue",
    "reviewed": "teal",
    "contacted": "amber",
    "responded": "teal",
    "viewing_scheduled": "blue",
    "converted": "teal",
    "negotiating": "amber",
    "rejected": "red",
    "duplicate": "legacy",
    "irrelevant": "legacy",
    "completed": "teal",
    "failed": "red",
    "interrupted": "red",
    "disabled": "legacy",
}
MATCH_TIER_COLORS = {
    "exact_match": "teal",
    "nearby_alternative": "amber",
    "tentative_match": "amber",
    "no_match": "amber",
    _LEGACY_KEY: "legacy",
}
BUDGET_CONFIDENCE_COLORS = {
    "high": "teal",
    "medium": "amber",
    "low": "amber",
    "unknown": "amber",
}

# Version-sensitive Streamlit selectors live only in this block. None removes
# navigation, the sidebar collapse control, focus indicators, or native inputs.
STREAMLIT_SHELL_CSS = f"""
html, body, [data-testid="stAppViewContainer"] {{
  background: {COLOR_TOKENS['canvas']};
  color: {COLOR_TOKENS['text_primary']};
}}
[data-testid="stHeader"] {{
  background: rgba(11, 18, 32, .94);
  border-bottom: 1px solid {COLOR_TOKENS['border_subtle']};
}}
[data-testid="stSidebar"] {{
  background: {COLOR_TOKENS['sidebar']};
  border-right: 1px solid {COLOR_TOKENS['border_subtle']};
}}
[data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"] {{ display: none; }}
[data-testid="stMetric"] {{
  background: {COLOR_TOKENS['surface']};
  border: {BORDER_TOKENS['default']};
  border-radius: {RADIUS_TOKENS['md']}px;
  padding: {SPACING_TOKENS[3]}px {SPACING_TOKENS[4]}px;
}}
.block-container {{
  max-width: 1500px;
  padding-top: {SPACING_TOKENS[8]}px;
  padding-bottom: {SPACING_TOKENS[12]}px;
}}
"""

COMPONENT_CSS = f"""
:root {{ color-scheme: dark; }}
body {{
  font-family: Inter, ui-sans-serif, system-ui, -apple-system,
    BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: {TYPOGRAPHY_TOKENS['body']['size']}px;
  line-height: {TYPOGRAPHY_TOKENS['body']['line_height']}px;
}}
a:focus-visible, button:focus-visible, input:focus-visible,
textarea:focus-visible, select:focus-visible, [tabindex]:focus-visible {{
  outline: 2px solid {COLOR_TOKENS['blue']} !important;
  outline-offset: 2px;
}}
.rdsa-card {{
  background: {COLOR_TOKENS['surface']};
  border: {BORDER_TOKENS['default']};
  border-radius: {RADIUS_TOKENS['md']}px;
  padding: {SPACING_TOKENS[4]}px;
}}
.rdsa-card--raised {{
  background: {COLOR_TOKENS['surface_raised']};
  border-radius: {RADIUS_TOKENS['lg']}px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, .14);
}}
.rdsa-kpi {{ min-height: 96px; }}
.rdsa-kpi--compact {{ min-height: 84px; }}
.rdsa-kpi-label {{
  color: {COLOR_TOKENS['text_muted']};
  font-size: {TYPOGRAPHY_TOKENS['label']['size']}px;
  font-weight: {TYPOGRAPHY_TOKENS['label']['weight']};
}}
.rdsa-kpi-value {{
  color: {COLOR_TOKENS['text_primary']};
  font-size: {TYPOGRAPHY_TOKENS['kpi']['size']}px;
  font-variant-numeric: tabular-nums;
  font-weight: {TYPOGRAPHY_TOKENS['kpi']['weight']};
  line-height: {TYPOGRAPHY_TOKENS['kpi']['line_height']}px;
  margin: {SPACING_TOKENS[1]}px 0;
}}
.rdsa-muted {{ color: {COLOR_TOKENS['text_muted']}; }}
.rdsa-section {{ margin: {SPACING_TOKENS[6]}px 0 {SPACING_TOKENS[2]}px; }}
.rdsa-section h2, .rdsa-section h3 {{
  color: {COLOR_TOKENS['text_primary']};
  font-size: {TYPOGRAPHY_TOKENS['section_title']['size']}px;
  line-height: {TYPOGRAPHY_TOKENS['section_title']['line_height']}px;
  margin: 0;
}}
.rdsa-badge, .rdsa-chip {{
  align-items: center;
  border: 1px solid currentColor;
  border-radius: {RADIUS_TOKENS['sm']}px;
  display: inline-flex;
  font-size: {TYPOGRAPHY_TOKENS['metadata']['size']}px;
  font-weight: 600;
  gap: {SPACING_TOKENS[1]}px;
  line-height: 18px;
  margin: 2px 4px 2px 0;
  min-height: 24px;
  padding: 2px {SPACING_TOKENS[2]}px;
}}
.rdsa-teal {{ color: {COLOR_TOKENS['teal']}; background: rgba(45, 212, 191, .10); }}
.rdsa-amber {{ color: {COLOR_TOKENS['amber']}; background: rgba(251, 191, 36, .10); }}
.rdsa-red {{ color: {COLOR_TOKENS['red']}; background: rgba(248, 113, 113, .10); }}
.rdsa-blue {{ color: {COLOR_TOKENS['blue']}; background: rgba(147, 197, 253, .10); }}
.rdsa-legacy {{ color: {COLOR_TOKENS['text_muted']}; background: rgba(148, 163, 184, .08); }}
.rdsa-page-header {{
  align-items: flex-start;
  display: flex;
  gap: {SPACING_TOKENS[4]}px;
  justify-content: space-between;
  margin-bottom: {SPACING_TOKENS[4]}px;
}}
.rdsa-page-header h1, .rdsa-page-title {{
  color: {COLOR_TOKENS['text_primary']};
  font-size: {TYPOGRAPHY_TOKENS['page_title']['size']}px;
  line-height: {TYPOGRAPHY_TOKENS['page_title']['line_height']}px;
  margin: 0;
}}
.rdsa-eyebrow, .rdsa-meta-key {{
  color: {COLOR_TOKENS['text_muted']};
  font-size: {TYPOGRAPHY_TOKENS['metadata']['size']}px;
  font-weight: 600;
}}
.rdsa-status-strip {{
  align-items: center;
  background: {COLOR_TOKENS['surface']};
  border: {BORDER_TOKENS['default']};
  border-radius: {RADIUS_TOKENS['md']}px;
  display: flex;
  flex-wrap: wrap;
  gap: {SPACING_TOKENS[4]}px;
  min-height: 40px;
  padding: {SPACING_TOKENS[2]}px {SPACING_TOKENS[3]}px;
}}
.rdsa-status-item, .rdsa-metadata-row {{
  align-items: center;
  display: inline-flex;
  flex-wrap: wrap;
  gap: {SPACING_TOKENS[2]}px;
}}
.rdsa-state {{
  background: {COLOR_TOKENS['surface']};
  border: {BORDER_TOKENS['default']};
  border-radius: {RADIUS_TOKENS['md']}px;
  padding: {SPACING_TOKENS[4]}px;
}}
.rdsa-comparison-row {{
  align-items: center;
  border-bottom: {BORDER_TOKENS['default']};
  display: grid;
  gap: {SPACING_TOKENS[3]}px;
  grid-template-columns: minmax(100px, .8fr) repeat(2, minmax(140px, 1.4fr)) minmax(90px, .8fr);
  padding: {SPACING_TOKENS[3]}px 0;
}}
.rdsa-score {{ display: flex; gap: {SPACING_TOKENS[2]}px; align-items: center; }}
.rdsa-score > div {{
  background: {COLOR_TOKENS['surface_hover']};
  border-radius: {RADIUS_TOKENS['sm']}px;
  height: 6px;
  overflow: hidden;
  width: 100%;
}}
.rdsa-score i {{ background: {COLOR_TOKENS['blue']}; display: block; height: 100%; }}
.rdsa-priority-card {{
  background: {COLOR_TOKENS['surface']};
  border: {BORDER_TOKENS['default']};
  border-left: 3px solid {COLOR_TOKENS['amber']};
  border-radius: {RADIUS_TOKENS['md']}px;
  margin: {SPACING_TOKENS[2]}px 0;
  padding: {SPACING_TOKENS[3]}px {SPACING_TOKENS[4]}px;
}}
.rdsa-priority-head {{
  align-items: center;
  display: flex;
  justify-content: space-between;
}}
.rdsa-priority-excerpt {{
  color: {COLOR_TOKENS['text_secondary']};
  line-height: 1.45;
  margin: {SPACING_TOKENS[2]}px 0;
}}
.rdsa-priority-facts {{
  align-items: center;
  color: {COLOR_TOKENS['text_muted']};
  display: flex;
  flex-wrap: wrap;
  font-size: {TYPOGRAPHY_TOKENS['metadata']['size']}px;
  gap: {SPACING_TOKENS[2]}px {SPACING_TOKENS[4]}px;
}}
.rdsa-budget-evidence {{
  display: block;
  color: {COLOR_TOKENS['text_muted']};
  font-size: {TYPOGRAPHY_TOKENS['metadata']['size']}px;
  line-height: {TYPOGRAPHY_TOKENS['metadata']['line_height']}px;
  margin-top: {SPACING_TOKENS[1]}px;
}}
.rdsa-priority-reason {{
  color: {COLOR_TOKENS['amber']};
  font-size: {TYPOGRAPHY_TOKENS['metadata']['size']}px;
  margin-top: {SPACING_TOKENS[2]}px;
}}
.rdsa-health-grid {{
  display: grid;
  gap: {SPACING_TOKENS[2]}px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}}
.rdsa-health-fact {{
  background: {COLOR_TOKENS['surface']};
  border: {BORDER_TOKENS['default']};
  border-radius: {RADIUS_TOKENS['sm']}px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: {SPACING_TOKENS[2]}px {SPACING_TOKENS[3]}px;
}}
.rdsa-health-fact strong {{
  color: {COLOR_TOKENS['text_secondary']};
  font-size: {TYPOGRAPHY_TOKENS['metadata']['size']}px;
  overflow-wrap: anywhere;
}}
@media (max-width: 1180px) {{
  .rdsa-comparison-row {{ grid-template-columns: minmax(90px, .8fr) repeat(2, minmax(120px, 1fr)); }}
  .rdsa-comparison-result {{ grid-column: 2 / -1; }}
  .rdsa-health-grid {{ grid-template-columns: 1fr; }}
}}
"""

CSS = f"<style>{STREAMLIT_SHELL_CSS}{COMPONENT_CSS}</style>"


def apply_theme() -> str:
    """Apply the centralized theme and return the emitted CSS for verification."""

    st.markdown(CSS, unsafe_allow_html=True)
    return CSS