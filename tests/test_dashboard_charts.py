from altair import Chart

from dashboard.charts import (
    budget_confidence_distribution,
    classification_distribution,
    cumulative_cost,
    lead_funnel,
    raw_normalized_new_funnel,
)


def test_dashboard_charts_are_altair_charts():
    charts = [lead_funnel({"total": 3, "hot": 1, "qualified": 1, "telegram_delivered": 1}), classification_distribution([]), budget_confidence_distribution([]), raw_normalized_new_funnel([]), cumulative_cost([])]
    assert all(isinstance(chart, Chart) for chart in charts)


def test_lead_funnel_has_expected_encodings():
    spec = lead_funnel({"total": 3, "hot": 1, "qualified": 1, "telegram_delivered": 1}).to_dict()
    assert spec["encoding"]["x"]["field"] == "value"
    assert spec["encoding"]["y"]["field"] == "stage"


def test_empty_chart_has_informative_title():
    assert "No pilot runs" in raw_normalized_new_funnel([]).to_dict()["title"]
