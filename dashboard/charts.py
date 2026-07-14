"""Altair chart builders for the dashboard.

Charts accept repository-shaped dictionaries and remain renderable when their
input is empty. The dashboard uses the Altair renderer supplied by Streamlit.
"""
from collections import Counter

import altair as alt
import pandas as pd

from dashboard.formatters import label
from dashboard.theme import COLORS


def _empty(title: str, message: str = "No data available for this view.") -> alt.Chart:
    frame = pd.DataFrame({"label": [message], "value": [0]})
    return (
        alt.Chart(frame)
        .mark_text(size=14, color=COLORS["muted"])
        .encode(text=alt.Text("label:N"))
        .properties(title=f"{title} · {message}", height=220)
    )


def _bars(values, title: str, color: str = "teal") -> alt.Chart:
    counts = Counter(str(v or "Unknown") for v in values)
    if not counts:
        return _empty(title)
    frame = pd.DataFrame({"label": [label(k) for k in counts], "value": list(counts.values())})
    chart = alt.Chart(frame).mark_bar(color=COLORS[color]).encode(
        x=alt.X("value:Q", title="Leads"),
        y=alt.Y("label:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("label:N", title="Category"), alt.Tooltip("value:Q", title="Count")],
    )
    return chart.properties(title=title, height=220).interactive()


def _runs(runs, fields, title: str, colors=None) -> alt.Chart:
    if not runs:
        return _empty(title, "No pilot runs recorded.")
    rows = []
    for run in runs:
        for name, key in fields:
            rows.append({"run": run.get("run"), "series": name, "value": run.get(key) or 0})
    frame = pd.DataFrame(rows)
    chart = alt.Chart(frame).mark_line(point=True).encode(
        x=alt.X("run:Q", title="Run"), y=alt.Y("value:Q", title=None),
        color=alt.Color("series:N", scale=alt.Scale(range=colors or [COLORS["teal"]])),
        tooltip=["run:Q", "series:N", "value:Q"],
    )
    return chart.properties(title=title, height=220).interactive()


def lead_funnel(overview):
    frame = pd.DataFrame({"stage": ["All leads", "Hot + qualified", "Telegram delivered"], "value": [overview.get("total", 0), overview.get("hot", 0) + overview.get("qualified", 0), overview.get("telegram_delivered", 0)]})
    return alt.Chart(frame).mark_bar().encode(x=alt.X("value:Q", title="Leads"), y=alt.Y("stage:N", sort="-x", title=None), color=alt.Color("stage:N", legend=None, scale=alt.Scale(range=[COLORS["blue"], COLORS["teal"], COLORS["amber"]])), tooltip=["stage:N", "value:Q"]).properties(title="Lead funnel", height=220).interactive()


def classification_distribution(leads): return _bars([x.get("lead_class") for x in leads], "Classification distribution")
def match_tier_distribution(leads): return _bars([m.get("match_type") for x in leads for m in x.get("matches", []) if not m.get("is_legacy")], "Active match tiers")
def location_distribution(leads): return _bars([x.get("desired_location") for x in leads], "Lead locations", "blue")
def budget_confidence_distribution(leads): return _bars([x.get("budget_confidence") for x in leads], "Budget confidence", "amber")
def cost_trend(runs): return _runs(runs, [("Cost", "apify_cost")], "Cost per run", [COLORS["amber"]])
def eligible_delivered_trend(runs): return _runs(runs, [("Eligible", "eligible"), ("Delivered", "delivered")], "Eligible vs delivered", [COLORS["teal"], COLORS["blue"]])
def classification_by_run(runs): return _runs(runs, [("New leads", "new")], "New leads by run", [COLORS["teal"]])
def tiers_by_run(runs): return _runs(runs, [("New leads", "new")], "Match tiers by run", [COLORS["amber"]])
def cost_per_eligible(runs):
    values = [{"run": r.get("run"), "value": (r.get("apify_cost") or 0) / (r.get("eligible") or 1)} for r in runs]
    if not values: return _empty("Cost per eligible lead", "No pilot runs recorded.")
    return alt.Chart(pd.DataFrame(values)).mark_line(point=True, color=COLORS["amber"]).encode(x=alt.X("run:Q", title="Run"), y=alt.Y("value:Q", title="USD"), tooltip=["run:Q", alt.Tooltip("value:Q", format=".3f")]).properties(title="Cost per eligible lead", height=220).interactive()
def cost_per_delivered(runs):
    values = [{"run": r.get("run"), "value": (r.get("apify_cost") or 0) / (r.get("delivered") or 1)} for r in runs]
    if not values: return _empty("Cost per delivered lead", "No pilot runs recorded.")
    return alt.Chart(pd.DataFrame(values)).mark_line(point=True, color=COLORS["blue"]).encode(x=alt.X("run:Q", title="Run"), y=alt.Y("value:Q", title="USD"), tooltip=["run:Q", alt.Tooltip("value:Q", format=".3f")]).properties(title="Cost per delivered lead", height=220).interactive()


def raw_normalized_new_funnel(runs):
    if not runs:
        return _empty("Raw → normalized → new", "No pilot runs recorded.")
    run = runs[-1]
    frame = pd.DataFrame({"stage": ["Raw", "Normalized", "New"], "value": [run.get("raw") or 0, run.get("normalized") or 0, run.get("new") or 0]})
    return alt.Chart(frame).mark_bar(color=COLORS["teal"]).encode(x=alt.X("value:Q", title="Records"), y=alt.Y("stage:N", sort="-x", title=None), tooltip=["stage:N", "value:Q"]).properties(title="Raw → normalized → new", height=220).interactive()


def cumulative_cost(runs):
    if not runs:
        return _empty("Cumulative cost", "No pilot runs recorded.")
    total = 0.0
    rows = []
    for run in runs:
        total += float(run.get("apify_cost") or 0)
        rows.append({"run": run.get("run"), "value": total})
    return alt.Chart(pd.DataFrame(rows)).mark_line(point=True, color=COLORS["amber"]).encode(x=alt.X("run:Q", title="Run"), y=alt.Y("value:Q", title="USD"), tooltip=["run:Q", alt.Tooltip("value:Q", format=".3f")]).properties(title="Cumulative cost", height=220).interactive()
