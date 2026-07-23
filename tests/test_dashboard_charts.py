from altair import Chart
import pytest

from dashboard.charts import (
    RDSA_ALTAIR_THEME,
    _finite_domain,
    budget_confidence_distribution,
    classification_distribution,
    classification_by_run,
    cost_trend,
    cumulative_cost,
    eligible_delivered_trend,
    lead_funnel,
    raw_normalized_new_funnel,
    valid_count,
)


def _records(chart):
    spec = chart.to_dict()
    rows = []
    rows.extend(spec.get("data", {}).get("values", []))
    for values in spec.get("datasets", {}).values():
        rows.extend(values)
    return rows


def test_dashboard_charts_are_altair_charts():
    charts = [lead_funnel({"total": 3, "hot": 1, "qualified": 1, "telegram_delivered": 1}), classification_distribution([]), budget_confidence_distribution([]), raw_normalized_new_funnel([]), cumulative_cost([])]
    assert all(isinstance(chart, Chart) for chart in charts)


def test_lead_funnel_has_expected_encodings():
    spec = lead_funnel({"total": 3, "hot": 1, "qualified": 1, "telegram_delivered": 1}).to_dict()
    assert spec["encoding"]["x"]["field"] == "value"
    assert spec["encoding"]["y"]["field"] == "stage"


def test_empty_chart_has_informative_title():
    spec = raw_normalized_new_funnel([]).to_dict()
    assert "No pilot runs" in spec["title"]
    assert spec["usermeta"]["rdsa_empty_state"] is True


def test_count_validation_rejects_fractional_negative_and_nonfinite_values():
    assert valid_count(0) == 0
    assert valid_count(2.0) == 2
    assert valid_count(0.7) is None
    assert valid_count(-1) is None
    assert valid_count(float("inf")) is None
    assert valid_count(float("nan")) is None
    assert valid_count(True) is None


def test_fractional_count_is_withheld_without_zero_fallback():
    chart = raw_normalized_new_funnel(
        [{"run": 10, "raw": 8, "normalized": 5, "new": 0.7}]
    )
    records = _records(chart)
    assert {row["stage"] for row in records} == {"Raw", "Normalized"}
    assert all(row["value"] in {8, 5} for row in records)


def test_missing_run_counts_are_gaps_but_recorded_zero_is_retained():
    chart = eligible_delivered_trend(
        [{"run": 1, "eligible": None, "delivered": 0},
         {"run": 2, "eligible": 3, "delivered": float("inf")}]
    )
    records = _records(chart)
    assert records == [
        {"run": 1, "series": "Delivered", "value": 0},
        {"run": 2, "series": "Eligible", "value": 3},
    ]


def test_invalid_numeric_series_returns_explicit_empty_chart():
    spec = cost_trend([{"run": 1, "apify_cost": float("inf")}]).to_dict()
    assert spec["usermeta"]["rdsa_empty_state"] is True
    assert "infinity" not in str(spec).lower()
    assert "nan" not in str(spec).lower()


def test_all_charts_use_the_standardized_accessible_theme():
    spec = classification_distribution([{"lead_class": "hot_lead"}]).to_dict()
    assert spec["config"]["background"] == "transparent"
    assert spec["config"]["axis"]["labelColor"] == RDSA_ALTAIR_THEME["config"]["axis"]["labelColor"]
    assert spec["config"]["view"]["stroke"] == RDSA_ALTAIR_THEME["config"]["view"]["stroke"]
    assert spec["encoding"]["x"]["axis"]["format"] == "d"
    tooltip_titles = {item["title"] for item in spec["encoding"]["tooltip"]}
    assert tooltip_titles == {"Category", "Count"}


def test_funnel_disables_implicit_stacking_that_creates_empty_extent_fields():
    spec = lead_funnel(
        {"total": 12, "hot": 2, "qualified": 3, "telegram_delivered": 1}
    ).to_dict()

    assert spec["encoding"]["x"]["stack"] is None


def test_valid_charts_pin_finite_quantitative_domains_for_streamlit_bootstrap():
    charts = [
        classification_distribution([{"lead_class": "hot_lead"}]),
        lead_funnel(
            {"total": 12, "hot": 2, "qualified": 3, "telegram_delivered": 1}
        ),
        classification_by_run([{"run": 1, "new": 2}, {"run": 2, "new": 3}]),
    ]

    for chart in charts:
        spec = chart.to_dict()
        for channel in ("x", "y"):
            encoding = spec.get("encoding", {}).get(channel, {})
            if encoding.get("type") != "quantitative":
                continue
            domain = encoding.get("scale", {}).get("domain")
            assert domain is not None
            assert len(domain) == 2
            assert all(value not in (float("inf"), float("-inf")) for value in domain)


@pytest.mark.parametrize(
    "values",
    [[], [None], [True], ["2"], [float("nan")], [float("inf")]],
)
def test_finite_domain_rejects_empty_or_nonfinite_nonnumeric_values(values):
    with pytest.raises(ValueError, match="Chart domains require"):
        _finite_domain(values)


def test_finite_domain_handles_zero_single_equal_positive_and_decimal_ranges():
    assert _finite_domain([0]) == [0.0, 1.0]
    assert _finite_domain([7], include_zero=False) == [6.5, 7.5]
    assert _finite_domain([4, 4], include_zero=False) == [3.5, 4.5]
    assert _finite_domain([2, 7]) == [0.0, 7.0]
    assert _finite_domain([0.125, 1.75]) == [0.0, 1.75]


def test_zero_only_and_one_point_run_domains_are_non_degenerate_without_new_rows():
    chart = classification_by_run([{"run": 4, "new": 0}])
    spec = chart.to_dict()

    assert _records(chart) == [{"run": 4, "series": "New leads", "value": 0}]
    assert spec["encoding"]["x"]["scale"]["domain"] == [3.5, 4.5]
    assert spec["encoding"]["y"]["scale"]["domain"] == [0.0, 1.0]


def test_count_and_cost_domains_keep_their_own_values_formats_and_maxima():
    count_spec = eligible_delivered_trend(
        [{"run": 1, "eligible": 2, "delivered": 7}]
    ).to_dict()
    cost_chart = cost_trend([{"run": 1, "apify_cost": 1.75}])
    cost_spec = cost_chart.to_dict()

    assert count_spec["encoding"]["y"]["scale"]["domain"] == [0.0, 7.0]
    assert count_spec["encoding"]["y"]["axis"]["format"] == "d"
    assert cost_spec["encoding"]["y"]["scale"]["domain"] == [0.0, 1.75]
    assert cost_spec["encoding"]["y"]["axis"]["format"] == ".3f"
    assert _records(cost_chart) == [{"run": 1, "series": "Cost", "value": 1.75}]
