"""Reusable, presentation-only Streamlit components."""
import csv
import io

import streamlit as st

from dashboard.formatters import budget, clean, label, period
from dashboard.theme import BUDGET_CONFIDENCE_COLORS, CLASSIFICATION_COLORS, MATCH_TIER_COLORS, STATUS_COLORS


def badge(value, colors, fallback="legacy"):
    tone = colors.get(str(value), fallback)
    return f'<span class="rdsa-badge rdsa-{tone}">{clean(label(value))}</span>'


def classification_badge(value): return badge(value, CLASSIFICATION_COLORS)
def status_badge(value): return badge(value, STATUS_COLORS)
def match_tier_badge(value): return badge(value, MATCH_TIER_COLORS)
def budget_confidence_badge(value): return badge(value, BUDGET_CONFIDENCE_COLORS)
def area_chip(value): return f'<span class="rdsa-chip rdsa-blue">{clean(value, "Unknown")}</span>'


def score_bar(score):
    try: value = max(0, min(100, float(score)))
    except (TypeError, ValueError): value = 0
    return f'<div class="rdsa-score"><span>{value:.0f}</span><div><i style="width:{value:.0f}%"></i></div></div>'


def section(title, caption=None):
    extra = f'<div class="rdsa-muted">{clean(caption)}</div>' if caption else ""
    st.markdown(f'<div class="rdsa-section"><h3>{clean(title)}</h3>{extra}</div>', unsafe_allow_html=True)


def kpi_card(label_text, value, caption=None):
    detail = f'<small class="rdsa-muted">{clean(caption)}</small>' if caption else ""
    st.markdown(f'<div class="rdsa-card rdsa-kpi"><div class="rdsa-muted">{clean(label_text)}</div><div class="rdsa-kpi-value">{clean(value, "0")}</div>{detail}</div>', unsafe_allow_html=True)


def callout(kind, message):
    getattr(st, kind, st.info)(message)


def table(rows, empty="No records match these filters.", height=420):
    if not rows:
        st.info(empty, icon=":material/info:")
        return
    st.dataframe(rows, hide_index=True, height=height, width="stretch")


def export_csv(rows, label_text="Download filtered CSV", key="csv"):
    if not rows: return
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), extrasaction="ignore")
    writer.writeheader(); writer.writerows(rows)
    st.download_button(label_text, buffer.getvalue().encode("utf-8"), "rental-demand-leads.csv", "text/csv", key=key)


def chart(fig): st.altair_chart(fig, width="stretch")


def lead_row(lead):
    return {"Lead": clean(lead.get("post_id")), "Score": lead.get("lead_score", 0), "Classification": label(lead.get("lead_class")), "Area": clean(lead.get("desired_location"), "Unknown"), "Type": clean(lead.get("property_type"), "Unknown"), "Budget": budget(lead), "Period": period(lead.get("budget_period")), "Status": label(lead.get("status")), "Telegram": "Delivered" if lead.get("telegram_sent") else "Not sent", "Match": ", ".join(label(x) for x in lead.get("match_types", [])) or "No active match"}
