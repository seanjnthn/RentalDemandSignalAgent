"""Reusable, sanitized presentation components for the Streamlit dashboard."""

from __future__ import annotations

import csv
import html
import io
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import streamlit as st

from dashboard.formatters import budget, clean, format_value, label, period
from dashboard.theme import (
    BUDGET_CONFIDENCE_COLORS,
    CLASSIFICATION_COLORS,
    MATCH_TIER_COLORS,
    STATUS_COLORS,
)


_ALLOWED_TONES = {"teal", "amber", "red", "blue", "legacy"}


def _safe(value: Any, fallback: str = "Not recorded") -> str:
    return html.escape(clean(value, fallback), quote=True)


def _tone(value: Any, fallback: str = "legacy") -> str:
    candidate = str(value or "").lower()
    return candidate if candidate in _ALLOWED_TONES else fallback


def badge(value: Any, colors: Mapping[str, str], fallback: str = "legacy") -> str:
    tone = _tone(colors.get(str(value)), fallback)
    return f'<span class="rdsa-badge rdsa-{tone}">{_safe(label(value))}</span>'


def classification_badge(value: Any) -> str:
    return badge(value, CLASSIFICATION_COLORS)


def status_badge(value: Any) -> str:
    return badge(value, STATUS_COLORS)


def match_tier_badge(value: Any) -> str:
    return badge(value, MATCH_TIER_COLORS)


def confidence_badge(value: Any) -> str:
    return badge(value or "unknown", BUDGET_CONFIDENCE_COLORS)


def budget_confidence_badge(value: Any) -> str:
    return confidence_badge(value)


def area_chip(value: Any) -> str:
    return f'<span class="rdsa-chip rdsa-blue">{_safe(value, "Unknown")}</span>'


def branded_page_header(
    title: Any,
    description: Any,
    *,
    meta: Any = None,
    eyebrow: str = "Rental Demand Signal",
    anchorless: bool = False,
) -> str:
    meta_html = f'<div class="rdsa-muted">{_safe(meta)}</div>' if meta else ""
    title_html = (
        f'<div class="rdsa-page-title">{_safe(title)}</div>'
        if anchorless
        else f'<h1>{_safe(title)}</h1>'
    )
    body = (
        '<header class="rdsa-page-header">'
        '<div>'
        f'<div class="rdsa-eyebrow">{_safe(eyebrow)}</div>'
        f"{title_html}"
        f'<div class="rdsa-muted">{_safe(description)}</div>'
        "</div>"
        f"{meta_html}"
        "</header>"
    )
    if anchorless:
        st.html(body)
    else:
        st.markdown(body, unsafe_allow_html=True)
    return body


def system_status_strip(items: Iterable[Mapping[str, Any]]) -> str:
    rendered = []
    for item in list(items)[:4]:
        tone = _tone(item.get("tone"))
        rendered.append(
            '<span class="rdsa-status-item">'
            f'<span class="rdsa-badge rdsa-{tone}">{_safe(item.get("label"))}</span>'
            f'<span>{_safe(item.get("value"))}</span>'
            "</span>"
        )
    body = f'<div class="rdsa-status-strip" role="status">{"".join(rendered)}</div>'
    st.markdown(body, unsafe_allow_html=True)
    return body


def score_bar(score: Any) -> str:
    try:
        value = max(0.0, min(100.0, float(score)))
    except (TypeError, ValueError):
        value = 0.0
    return (
        '<div class="rdsa-score" role="img" '
        f'aria-label="Score {value:.0f} out of 100"><span>{value:.0f}</span>'
        f'<div><i style="width:{value:.0f}%"></i></div></div>'
    )


def section_header(title: Any, caption: Any = None) -> str:
    extra = f'<div class="rdsa-muted">{_safe(caption)}</div>' if caption else ""
    body = f'<section class="rdsa-section"><h2>{_safe(title)}</h2>{extra}</section>'
    st.markdown(body, unsafe_allow_html=True)
    return body


def section(title: Any, caption: Any = None) -> str:
    return section_header(title, caption)


def kpi_card(
    label_text: Any,
    value: Any,
    caption: Any = None,
    *,
    tone: str = "legacy",
    compact: bool = False,
) -> str:
    detail = f'<small class="rdsa-muted">{_safe(caption)}</small>' if caption else ""
    compact_class = " rdsa-kpi--compact" if compact else ""
    body = (
        f'<div class="rdsa-card rdsa-kpi{compact_class}" role="group">'
        f'<div class="rdsa-kpi-label"><span class="rdsa-badge rdsa-{_tone(tone)}">'
        f'{_safe(label_text)}</span></div>'
        f'<div class="rdsa-kpi-value">{_safe(format_value(value))}</div>'
        f"{detail}</div>"
    )
    st.markdown(body, unsafe_allow_html=True)
    return body


def empty_state(title: Any, message: Any) -> str:
    body = (
        '<div class="rdsa-state" role="status">'
        f'<strong>{_safe(title)}</strong><div class="rdsa-muted">{_safe(message)}</div>'
        "</div>"
    )
    st.markdown(body, unsafe_allow_html=True)
    return body


def state_message(kind: str, title: Any, message: Any) -> str:
    safe_title, safe_message = clean(title, "Attention"), clean(message, "")
    text = f"{safe_title} — {safe_message}" if safe_message else safe_title
    renderer = st.error if kind == "error" else st.warning if kind == "warning" else st.info
    renderer(text)
    return text


def warning_state(title: Any, message: Any) -> str:
    return state_message("warning", title, message)


def error_state(title: Any, message: Any) -> str:
    return state_message("error", title, message)


def metadata_row(items: Sequence[tuple[Any, Any]]) -> str:
    cells = "".join(
        '<span class="rdsa-status-item">'
        f'<span class="rdsa-meta-key">{_safe(key)}</span><span>{_safe(value)}</span>'
        "</span>"
        for key, value in items
    )
    body = f'<div class="rdsa-metadata-row">{cells}</div>'
    st.markdown(body, unsafe_allow_html=True)
    return body


def comparison_row(
    criterion: Any,
    lead_value: Any,
    inventory_value: Any,
    result: Any,
    *,
    tone: str = "legacy",
) -> str:
    body = (
        '<div class="rdsa-comparison-row" role="row">'
        f'<strong role="cell">{_safe(criterion)}</strong>'
        f'<span role="cell">{_safe(lead_value)}</span>'
        f'<span role="cell">{_safe(inventory_value)}</span>'
        f'<span class="rdsa-comparison-result rdsa-{_tone(tone)}" role="cell">{_safe(result)}</span>'
        "</div>"
    )
    st.markdown(body, unsafe_allow_html=True)
    return body


def callout(kind: str, message: Any) -> None:
    getattr(st, kind, st.info)(clean(message, ""))


def table(rows: Sequence[Mapping[str, Any]], empty: str = "No records match these filters.", height: int = 420) -> None:
    if not rows:
        st.info(empty, icon=":material/info:")
        return
    st.dataframe(rows, hide_index=True, height=height, width="stretch")


def export_csv(rows: Sequence[Mapping[str, Any]], label_text: str = "Download filtered CSV", key: str = "csv") -> None:
    if not rows:
        return
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    st.download_button(
        label_text,
        buffer.getvalue().encode("utf-8"),
        "rental-demand-leads.csv",
        "text/csv",
        key=key,
    )


def chart(fig: Any) -> None:
    st.altair_chart(fig, width="stretch")


def lead_row(lead: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "Lead": clean(lead.get("post_id")),
        "Score": lead.get("lead_score", 0),
        "Classification": label(lead.get("lead_class")),
        "Area": clean(lead.get("desired_location"), "Unknown"),
        "Type": clean(lead.get("property_type"), "Unknown"),
        "Budget": budget(dict(lead)),
        "Period": period(lead.get("budget_period")),
        "Status": label(lead.get("status")),
        "Telegram": "Delivered" if lead.get("telegram_sent") else "Not sent",
        "Match": ", ".join(label(item) for item in lead.get("match_types", [])) or "No active match",
    }