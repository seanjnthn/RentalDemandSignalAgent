"""Truthful, presentation-only Altair charts for the dashboard.

All numeric inputs are validated before a quantitative encoding is built.
Missing values remain gaps, malformed values are withheld, and an input with no
valid records becomes a text-only empty state instead of an invalid domain.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from numbers import Real
from typing import Any

import altair as alt
import pandas as pd

from dashboard.formatters import label
from dashboard.theme import COLORS


RDSA_ALTAIR_THEME = {
    "config": {
        # Altair 6 rejects null here; the CSS color keyword keeps the card visible.
        "background": "transparent",
        "font": "Inter, ui-sans-serif, system-ui, sans-serif",
        "axis": {
            "domainColor": COLORS["border"],
            "gridColor": COLORS["border"],
            "gridOpacity": 0.38,
            "labelColor": COLORS["muted"],
            "labelFontSize": 12,
            "tickColor": COLORS["border"],
            "titleColor": COLORS["secondary"],
            "titleFontSize": 12,
        },
        "legend": {
            "labelColor": COLORS["muted"],
            "labelFontSize": 12,
            "orient": "top",
            "titleColor": COLORS["secondary"],
        },
        "title": {
            "anchor": "start",
            "color": COLORS["text"],
            "fontSize": 16,
            "fontWeight": 600,
            "offset": 14,
        },
        "view": {"stroke": COLORS["border"], "strokeOpacity": 0.65},
    }
}

OVERVIEW_DISTRIBUTION_COLORS = {
    "Genuine seeker": "teal",
    "Review required": "amber",
    "Agent / offering": "blue",
    "Irrelevant": "muted",
    "Exact": "teal",
    "Nearby": "blue",
    "Tentative": "amber",
    "No match": "muted",
}

OVERVIEW_DISTRIBUTION_DEFINITIONS = {
    "Genuine seeker": "Stored leads classified as high-signal or qualified seekers.",
    "Review required": "Stored watch, unknown, or unrecognized classifications requiring review.",
    "Agent / offering": "Stored agent, broker, or property-offering classifications.",
    "Irrelevant": "Stored irrelevant or spam classifications.",
    "Exact": "Active exact matches to validated real inventory.",
    "Nearby": "Active nearby alternatives from validated real inventory.",
    "Tentative": "Active tentative matches requiring review.",
    "No match": "Leads with no active match to validated real inventory.",
}

OVERVIEW_VOLUME_DEFINITIONS = {
    "Stored leads": "All stored leads in the current repository snapshot.",
    "High signal": "Stored leads classified as high signal.",
    "Qualified": "Stored leads classified as qualified.",
    "Active matches": "Active exact, nearby, or tentative matches to validated real inventory.",
    "Delivered": "Recorded immutable Telegram delivery rows.",
}


def valid_count(value: Any) -> int | None:
    """Return a non-negative integer count or withhold the value."""

    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0 or not number.is_integer():
        return None
    return int(number)


def valid_number(value: Any) -> float | None:
    """Return a finite non-negative measure suitable for a chart domain."""

    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _finite_domain(values: Iterable[int | float], *, include_zero: bool = True) -> list[float]:
    """Return a finite, non-degenerate domain before Streamlit attaches chart data."""

    numbers: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise ValueError("Chart domains require finite numeric values.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Chart domains require finite numeric values.")
        numbers.append(number)
    if not numbers:
        raise ValueError("Chart domains require at least one value.")
    low = min(numbers)
    high = max(numbers)
    if include_zero:
        low = min(0.0, low)
        high = max(0.0, high)
    if low == high:
        if low == 0:
            high = 1.0
        else:
            low -= 0.5
            high += 0.5
    return [low, high]


def _styled(chart: alt.Chart) -> alt.Chart:
    return chart.configure(**RDSA_ALTAIR_THEME["config"])


def _empty(title: str, message: str = "No data available for this view.") -> alt.Chart:
    frame = pd.DataFrame({"message": [message]})
    chart = (
        alt.Chart(frame)
        .mark_text(size=14, color=COLORS["muted"], align="center")
        .encode(text=alt.Text("message:N"))
        .properties(
            title=f"{title} · {message}",
            height=220,
            usermeta={"rdsa_empty_state": True},
        )
    )
    return _styled(chart)


def _bars(values: Iterable[Any], title: str, color: str = "teal") -> alt.Chart:
    counts = Counter(str(value or "Unknown") for value in values)
    if not counts:
        return _empty(title)
    frame = pd.DataFrame(
        {"label": [label(key) for key in counts], "value": list(counts.values())}
    )
    chart = (
        alt.Chart(frame)
        .mark_bar(color=COLORS[color], cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "value:Q",
                title="Leads",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(domain=_finite_domain(counts.values())),
            ),
            y=alt.Y("label:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("label:N", title="Category"),
                alt.Tooltip("value:Q", title="Count", format="d"),
            ],
        )
        .properties(title=title, height=220)
    )
    return _styled(chart)


def overview_volume_chart(values: Mapping[str, Any]) -> alt.Chart:
    """Plot explicitly independent recorded volumes, never a conversion funnel."""

    rows = [
        {
            "stage": name,
            "definition": OVERVIEW_VOLUME_DEFINITIONS.get(
                name, "Independent recorded repository volume."
            ),
            "value": count,
        }
        for name, raw in values.items()
        if (count := valid_count(raw)) is not None
    ]
    if not rows:
        return _empty(
            "Independent recorded volumes",
            "No valid recorded counts available.",
        )
    stage_order = [row["stage"] for row in rows]
    chart = (
        alt.Chart(pd.DataFrame(rows))
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "value:Q",
                title="Recorded count",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(
                    domain=_finite_domain(row["value"] for row in rows)
                ),
                stack=None,
            ),
            y=alt.Y("stage:N", sort=stage_order, title=None),
            color=alt.Color(
                "stage:N",
                legend=None,
                scale=alt.Scale(
                    domain=stage_order,
                    range=[
                        COLORS["blue"],
                        COLORS["teal"],
                        COLORS["teal"],
                        COLORS["amber"],
                        COLORS["muted"],
                    ][: len(stage_order)],
                ),
            ),
            tooltip=[
                alt.Tooltip("stage:N", title="Recorded volume"),
                alt.Tooltip("definition:N", title="Definition"),
                alt.Tooltip("value:Q", title="Count", format="d"),
            ],
        )
        .properties(title="Independent recorded volumes", height=220)
    )
    return _styled(chart)


def overview_distribution_chart(
    values: Mapping[str, Any],
    title: str,
    *,
    record_count: Any,
    minimum_records: int = 3,
) -> alt.Chart:
    """Render a finite distribution or an explicit empty/limited-data state."""

    count = valid_count(record_count)
    if count in (None, 0):
        return _empty(title, "No records available.")
    if count < minimum_records:
        return _empty(title, f"Limited data · {count} records recorded.")
    rows = [
        {
            "category": name,
            "definition": OVERVIEW_DISTRIBUTION_DEFINITIONS.get(
                name, "Recorded repository category."
            ),
            "value": value,
        }
        for name, raw in values.items()
        if (value := valid_count(raw)) is not None
    ]
    if not rows:
        return _empty(title, "No valid recorded counts available.")
    category_order = [row["category"] for row in rows]
    chart = (
        alt.Chart(pd.DataFrame(rows))
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "value:Q",
                title="Recorded count",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(
                    domain=_finite_domain(row["value"] for row in rows)
                ),
                stack=None,
            ),
            y=alt.Y("category:N", sort="-x", title=None),
            color=alt.Color(
                "category:N",
                legend=None,
                scale=alt.Scale(
                    domain=category_order,
                    range=[
                        COLORS[OVERVIEW_DISTRIBUTION_COLORS.get(category, "muted")]
                        for category in category_order
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("definition:N", title="Definition"),
                alt.Tooltip("value:Q", title="Count", format="d"),
            ],
        )
        .properties(title=title, height=220)
    )
    return _styled(chart)


def _runs(
    runs: Sequence[dict[str, Any]],
    fields: Sequence[tuple[str, str]],
    title: str,
    colors: Sequence[str] | None = None,
    *,
    value_kind: str = "count",
    y_title: str | None = None,
) -> alt.Chart:
    if not runs:
        return _empty(title, "No pilot runs recorded.")
    validator = valid_count if value_kind == "count" else valid_number
    rows: list[dict[str, Any]] = []
    for run in runs:
        run_number = valid_count(run.get("run"))
        if run_number is None:
            continue
        for name, key in fields:
            value = validator(run.get(key))
            if value is not None:
                rows.append({"run": run_number, "series": name, "value": value})
    if not rows:
        return _empty(title, "No valid values recorded.")
    value_format = "d" if value_kind == "count" else ".3f"
    frame = pd.DataFrame(rows)
    run_domain = _finite_domain((row["run"] for row in rows), include_zero=False)
    value_domain = _finite_domain(row["value"] for row in rows)
    chart = (
        alt.Chart(frame)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=55), strokeWidth=2)
        .encode(
            x=alt.X(
                "run:Q",
                title="Run",
                axis=alt.Axis(format="d", tickMinStep=1),
                scale=alt.Scale(domain=run_domain),
            ),
            y=alt.Y(
                "value:Q",
                title=y_title,
                axis=alt.Axis(format=value_format),
                scale=alt.Scale(domain=value_domain, zero=True),
            ),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(range=list(colors or [COLORS["teal"]])),
            ),
            tooltip=[
                alt.Tooltip("run:Q", title="Run", format="d"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title="Value", format=value_format),
            ],
        )
        .properties(title=title, height=220)
    )
    return _styled(chart)


def lead_funnel(overview: dict[str, Any]) -> alt.Chart:
    rows: list[dict[str, Any]] = []
    total = valid_count(overview.get("total"))
    hot = valid_count(overview.get("hot"))
    qualified = valid_count(overview.get("qualified"))
    delivered = valid_count(overview.get("telegram_delivered"))
    if total is not None:
        rows.append({"stage": "All leads", "value": total})
    if hot is not None and qualified is not None:
        rows.append({"stage": "Hot + qualified", "value": hot + qualified})
    if delivered is not None:
        rows.append({"stage": "Telegram delivered", "value": delivered})
    if not rows:
        return _empty("Lead volume", "No valid lead counts recorded.")
    frame = pd.DataFrame(rows)
    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "value:Q",
                title="Leads",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(domain=_finite_domain(row["value"] for row in rows)),
                stack=None,
            ),
            y=alt.Y("stage:N", sort="-x", title=None),
            color=alt.Color(
                "stage:N",
                legend=None,
                scale=alt.Scale(
                    domain=["All leads", "Hot + qualified", "Telegram delivered"],
                    range=[COLORS["blue"], COLORS["teal"], COLORS["amber"]],
                ),
            ),
            tooltip=[
                alt.Tooltip("stage:N", title="Stage"),
                alt.Tooltip("value:Q", title="Leads", format="d"),
            ],
        )
        .properties(title="Lead volume", height=220)
    )
    return _styled(chart)


def classification_distribution(leads: Sequence[dict[str, Any]]) -> alt.Chart:
    return _bars(
        [item.get("lead_class") for item in leads], "Classification distribution"
    )


def match_tier_distribution(leads: Sequence[dict[str, Any]]) -> alt.Chart:
    return _bars(
        [
            match.get("match_type")
            for lead in leads
            for match in lead.get("matches", [])
            if not match.get("is_legacy")
        ],
        "Active match tiers",
    )


def location_distribution(leads: Sequence[dict[str, Any]]) -> alt.Chart:
    return _bars([item.get("desired_location") for item in leads], "Lead locations", "blue")


def budget_confidence_distribution(leads: Sequence[dict[str, Any]]) -> alt.Chart:
    return _bars(
        [item.get("budget_confidence") for item in leads],
        "Budget confidence",
        "amber",
    )


def cost_trend(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    return _runs(
        runs,
        [("Cost", "apify_cost")],
        "Cost per run",
        [COLORS["amber"]],
        value_kind="number",
        y_title="USD",
    )


def eligible_delivered_trend(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    return _runs(
        runs,
        [("Eligible", "eligible"), ("Delivered", "delivered")],
        "Eligible vs delivered",
        [COLORS["teal"], COLORS["blue"]],
        y_title="Leads",
    )


def classification_by_run(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    return _runs(
        runs,
        [("New leads", "new")],
        "New leads by run",
        [COLORS["teal"]],
        y_title="Leads",
    )


def tiers_by_run(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    # The current run contract records new-lead count, not per-tier history.
    return _runs(
        runs,
        [("New leads", "new")],
        "New leads by run",
        [COLORS["amber"]],
        y_title="Leads",
    )


def _cost_per(
    runs: Sequence[dict[str, Any]], denominator_key: str, title: str, color: str
) -> alt.Chart:
    rows = []
    for run in runs:
        run_number = valid_count(run.get("run"))
        cost = valid_number(run.get("apify_cost"))
        denominator = valid_count(run.get(denominator_key))
        if run_number is None or cost is None or denominator in (None, 0):
            continue
        rows.append({"run": run_number, "value": cost / denominator})
    if not rows:
        return _empty(title, "No valid nonzero denominator recorded.")
    run_domain = _finite_domain((row["run"] for row in rows), include_zero=False)
    value_domain = _finite_domain(row["value"] for row in rows)
    chart = (
        alt.Chart(pd.DataFrame(rows))
        .mark_line(point=True, color=COLORS[color], strokeWidth=2)
        .encode(
            x=alt.X(
                "run:Q",
                title="Run",
                axis=alt.Axis(format="d", tickMinStep=1),
                scale=alt.Scale(domain=run_domain),
            ),
            y=alt.Y(
                "value:Q",
                title="USD",
                axis=alt.Axis(format=".3f"),
                scale=alt.Scale(domain=value_domain),
            ),
            tooltip=[
                alt.Tooltip("run:Q", title="Run", format="d"),
                alt.Tooltip("value:Q", title="USD per lead", format=".3f"),
            ],
        )
        .properties(title=title, height=220)
    )
    return _styled(chart)


def cost_per_eligible(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    return _cost_per(runs, "eligible", "Cost per eligible lead", "amber")


def cost_per_delivered(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    return _cost_per(runs, "delivered", "Cost per delivered lead", "blue")


def raw_normalized_new_funnel(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    if not runs:
        return _empty("Raw → normalized → new", "No pilot runs recorded.")
    run = runs[-1]
    rows = []
    for stage, key in (("Raw", "raw"), ("Normalized", "normalized"), ("New", "new")):
        value = valid_count(run.get(key))
        if value is not None:
            rows.append({"stage": stage, "value": value})
    if not rows:
        return _empty("Raw → normalized → new", "No valid counts recorded.")
    chart = (
        alt.Chart(pd.DataFrame(rows))
        .mark_bar(color=COLORS["teal"], cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "value:Q",
                title="Records",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(domain=_finite_domain(row["value"] for row in rows)),
            ),
            y=alt.Y("stage:N", sort=["Raw", "Normalized", "New"], title=None),
            tooltip=[
                alt.Tooltip("stage:N", title="Stage"),
                alt.Tooltip("value:Q", title="Records", format="d"),
            ],
        )
        .properties(title="Raw → normalized → new", height=220)
    )
    return _styled(chart)


def cumulative_cost(runs: Sequence[dict[str, Any]]) -> alt.Chart:
    if not runs:
        return _empty("Cumulative cost", "No pilot runs recorded.")
    total = 0.0
    rows = []
    for run in runs:
        run_number = valid_count(run.get("run"))
        cost = valid_number(run.get("apify_cost"))
        if run_number is None or cost is None:
            continue
        total += cost
        rows.append({"run": run_number, "value": total})
    if not rows:
        return _empty("Cumulative cost", "No valid cost values recorded.")
    run_domain = _finite_domain((row["run"] for row in rows), include_zero=False)
    value_domain = _finite_domain(row["value"] for row in rows)
    chart = (
        alt.Chart(pd.DataFrame(rows))
        .mark_line(point=True, color=COLORS["amber"], strokeWidth=2)
        .encode(
            x=alt.X(
                "run:Q",
                title="Run",
                axis=alt.Axis(format="d", tickMinStep=1),
                scale=alt.Scale(domain=run_domain),
            ),
            y=alt.Y(
                "value:Q",
                title="USD",
                axis=alt.Axis(format=".3f"),
                scale=alt.Scale(domain=value_domain),
            ),
            tooltip=[
                alt.Tooltip("run:Q", title="Run", format="d"),
                alt.Tooltip("value:Q", title="Cumulative USD", format=".3f"),
            ],
        )
        .properties(title="Cumulative cost", height=220)
    )
    return _styled(chart)