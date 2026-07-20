"""Phase 2B Signal Desk Overview presentation contracts."""

from pathlib import Path
import os
import subprocess
import sys

from dashboard.overview import (
    PRIMARY_KPI_DEFINITIONS,
    build_primary_kpis,
    classification_groups,
    data_state,
    independent_volume_values,
    inventory_has_active_rows,
    match_quality_summary,
    operational_health,
    overview_excerpt,
    priority_queue,
    system_statuses,
)
from dashboard.charts import overview_distribution_chart, overview_volume_chart
from dashboard.components import branded_page_header
from dashboard.theme import COLORS


def test_overview_has_exactly_six_primary_kpi_definitions():
    assert [item["label"] for item in PRIMARY_KPI_DEFINITIONS] == [
        "Review backlog",
        "High-signal leads",
        "Qualified leads",
        "Target-area leads",
        "Active real matches",
        "Delivered leads",
    ]
    assert len(PRIMARY_KPI_DEFINITIONS) == 6


def test_overview_header_renders_without_streamlit_heading_anchor(monkeypatch):
    markdown_rendered = []
    html_rendered = []
    monkeypatch.setattr(
        "dashboard.components.st.markdown",
        lambda body, **_: markdown_rendered.append(body),
    )
    monkeypatch.setattr("dashboard.components.st.html", html_rendered.append)
    body = branded_page_header(
        "Rental Demand Signal",
        "Demand intelligence and underwriting review workspace",
        anchorless=True,
    )
    assert "<h1" not in body
    assert '<div class="rdsa-page-title">Rental Demand Signal</div>' in body
    assert html_rendered == [body]
    assert markdown_rendered == []


def test_primary_kpis_preserve_zero_and_withhold_missing_values():
    cards = build_primary_kpis(
        {
            "new": 0,
            "hot": None,
            "qualified": 2,
            "total": 5,
            "unknown_location": 5,
            "exact_match": 0,
            "nearby_alternative": 0,
            "tentative_match": 0,
            "telegram_delivered": None,
        }
    )
    values = {card["key"]: card["value"] for card in cards}
    assert values == {
        "review_backlog": 0,
        "high_signal": None,
        "qualified": 2,
        "target_area": 0,
        "active_real_matches": 0,
        "delivered": None,
    }


def test_fractional_counts_are_withheld_in_kpis_and_volume_stages():
    overview = {
        "new": 1.5,
        "hot": 2,
        "qualified": 3,
        "total": 8.25,
        "unknown_location": 1,
        "exact_match": 1,
        "nearby_alternative": 0.5,
        "tentative_match": 0,
        "telegram_delivered": 0,
    }
    values = {card["key"]: card["value"] for card in build_primary_kpis(overview)}
    assert values["review_backlog"] is None
    assert values["target_area"] is None
    assert values["active_real_matches"] is None
    stages = independent_volume_values(overview)
    assert "Stored leads" not in stages
    assert "Active matches" not in stages
    assert stages["Delivered"] == 0


def test_match_quality_uses_active_real_inventory_and_excludes_legacy():
    summary = match_quality_summary(
        [
            {
                "matches": [
                    {"property_id": "REAL-1", "match_type": "exact_match", "is_legacy": False},
                    {"property_id": "INV001", "match_type": "legacy_synthetic", "is_legacy": True},
                ]
            },
            {"matches": []},
            {
                "matches": [
                    {"property_id": "INV002", "match_type": "legacy_synthetic", "is_legacy": True}
                ]
            },
        ]
    )
    assert summary["active"] == {"Exact": 1, "Nearby": 0, "Tentative": 0, "No match": 2}
    assert summary["legacy_count"] == 2
    assert "INV001" not in repr(summary)
    assert "INV002" not in repr(summary)


def test_active_match_claims_are_withheld_when_real_inventory_is_unavailable():
    overview = {
        "new": 1,
        "hot": 1,
        "qualified": 0,
        "total": 1,
        "unknown_location": 0,
        "exact_match": 1,
        "nearby_alternative": 0,
        "tentative_match": 0,
        "telegram_delivered": 0,
    }
    leads = [
        {
            "post_id": "p1",
            "status": "new",
            "lead_class": "hot_lead",
            "lead_score": 90,
            "raw_text": "Need BSD apartment",
            "desired_location": "BSD",
            "budget_confidence": "high",
            "matches": [
                {"property_id": "REAL-1", "match_type": "exact_match", "is_legacy": False}
            ],
        }
    ]
    invalid_inventory = {"rows": [], "report": {"ok": False}}
    assert inventory_has_active_rows(invalid_inventory) is False
    cards = build_primary_kpis(overview, active_inventory_available=False)
    assert next(card for card in cards if card["key"] == "active_real_matches")["value"] is None
    assert "Active real matches" not in independent_volume_values(
        overview, active_inventory_available=False
    )
    summary = match_quality_summary(leads, active_inventory_available=False)
    assert summary["active"] == {}
    assert summary["available"] is False
    queue = priority_queue(leads, active_inventory_available=False)
    assert queue[0]["match_tier"] == "Withheld"
    assert queue[0]["review_reason"] == "Active inventory unavailable"


def test_overview_excerpt_redacts_formatted_phones_and_handles():
    excerpt = overview_excerpt(
        "Contact +62 812-3456-7890, 0812 3456 7890, Telegram @private_handle or owner@example.com"
    )
    assert "812-3456-7890" not in excerpt
    assert "0812 3456 7890" not in excerpt
    assert "@private_handle" not in excerpt
    assert "owner@example.com" not in excerpt
    assert excerpt.count("[redacted]") >= 4


def test_priority_queue_preserves_repository_score_order_and_display_allowlist():
    leads = [
        {
            "post_id": "p-high",
            "status": "new",
            "lead_class": "hot_lead",
            "lead_score": 95,
            "raw_text": "Need BSD unit, contact owner@example.com",
            "desired_location": "BSD",
            "budget_min": 5_000_000,
            "budget_max": 7_000_000,
            "budget_period": "month",
            "budget_confidence": "high",
            "matches": [{"property_id": "REAL-1", "match_type": "exact_match", "is_legacy": False}],
            "author_username": "private-author",
        },
        {
            "post_id": "p-next",
            "status": "new",
            "lead_class": "qualified_lead",
            "lead_score": 82,
            "raw_text": "Apartment wanted",
            "desired_location": "Unknown",
            "budget_confidence": "unknown",
            "matches": [{"property_id": "INV999", "match_type": "legacy_synthetic", "is_legacy": True}],
        },
        {"post_id": "p-skip", "status": "new", "lead_class": "irrelevant", "lead_score": 99},
    ]
    queue = priority_queue(leads)
    assert [row["lead_ref"] for row in queue] == ["p-high", "p-next"]
    assert list(queue[0]) == [
        "lead_ref",
        "excerpt",
        "classification",
        "score",
        "target_area",
        "budget",
        "budget_evidence",
        "match_tier",
        "review_reason",
        "review_state",
    ]
    rendered = repr(queue)
    assert "owner@example.com" not in rendered
    assert "private-author" not in rendered
    assert "INV999" not in rendered


def test_priority_queue_demotes_uncertain_budget_to_secondary_evidence():
    leads = [
        {
            "post_id": "p-low",
            "status": "new",
            "lead_class": "hot_lead",
            "lead_score": 95,
            "raw_text": "Need BSD apartment",
            "desired_location": "BSD",
            "budget_min": 5_000_000,
            "budget_max": 7_000_000,
            "budget_period": "month",
            "budget_confidence": "low",
            "matches": [],
        },
        {
            "post_id": "p-high",
            "status": "new",
            "lead_class": "qualified_lead",
            "lead_score": 90,
            "raw_text": "Need Alam Sutera apartment",
            "desired_location": "Alam Sutera",
            "budget_min": 8_000_000,
            "budget_max": 10_000_000,
            "budget_period": "month",
            "budget_confidence": "high",
            "matches": [],
        },
    ]
    uncertain, confident = priority_queue(leads)
    assert uncertain["review_reason"] == "Budget needs confirmation"
    assert uncertain["budget"] == "Budget needs confirmation"
    assert uncertain["budget_evidence"] == "IDR 5.000.000 – IDR 7.000.000"
    assert confident["budget"] == "IDR 8.000.000 – IDR 10.000.000"
    assert confident["budget_evidence"] is None


def test_high_signal_uses_informational_blue_not_error_red():
    high_signal = next(item for item in PRIMARY_KPI_DEFINITIONS if item["key"] == "high_signal")
    assert high_signal["tone"] == "blue"
    assert high_signal["tone"] != "red"


def test_disabled_scheduler_and_telegram_are_muted_not_critical():
    items = system_statuses(
        database_available=True,
        inventory={"rows": [], "report": {"ok": True}},
        scheduler={
            "code_readiness": "ready",
            "scheduler_enabled": False,
            "telegram_send_enabled": False,
            "lock": {"locked": False},
            "interrupted_runs": [],
            "latest_run": None,
        },
    )
    by_label = {item["label"]: item for item in items}
    assert by_label["Scheduler"]["tone"] == "legacy"
    assert by_label["Telegram delivery"]["tone"] == "legacy"
    assert by_label["Scheduler"]["value"] == "Disabled"
    assert by_label["Telegram delivery"]["value"] == "Disabled"


def test_unresolved_interruption_is_blocking_but_reconciled_is_historical():
    base = {
        "code_readiness": "ready",
        "scheduler_enabled": False,
        "telegram_send_enabled": False,
        "lock": {"locked": False},
        "latest_run": {"status": "interrupted"},
    }
    unresolved = {**base, "interrupted_runs": [{"reconciliation": "required"}]}
    resolved = {**base, "interrupted_runs": [{"reconciliation": "completed"}]}

    unresolved_item = {item["label"]: item for item in system_statuses(True, {}, unresolved)}["Scheduler"]
    resolved_item = {item["label"]: item for item in system_statuses(True, {}, resolved)}["Scheduler"]
    assert unresolved_item["tone"] == "red"
    assert unresolved_item["value"] == "Interruption unresolved"
    assert resolved_item["tone"] == "legacy"
    assert resolved_item["value"] == "Disabled"
    assert operational_health(resolved)["interruption"] == "Historical · reconciled"


def test_scheduler_distinguishes_live_and_stale_locks_and_blocked_runs():
    base = {
        "code_readiness": "ready",
        "scheduler_enabled": True,
        "telegram_send_enabled": False,
        "interrupted_runs": [],
    }
    live = {
        **base,
        "lock": {"locked": True, "process_alive": True},
        "latest_run": {"status": "running"},
    }
    stale = {
        **base,
        "lock": {"locked": True, "process_alive": False},
        "latest_run": {"status": "running"},
    }
    blocked = {
        **base,
        "lock": {"locked": False},
        "latest_run": {"status": "blocked_cost_limit"},
    }
    live_item = {item["label"]: item for item in system_statuses(True, {}, live)}["Scheduler"]
    stale_item = {item["label"]: item for item in system_statuses(True, {}, stale)}["Scheduler"]
    blocked_item = {item["label"]: item for item in system_statuses(True, {}, blocked)}["Scheduler"]
    assert live_item == {"label": "Scheduler", "value": "Running", "tone": "teal"}
    assert stale_item["tone"] == "red"
    assert stale_item["value"] == "Stale lock"
    assert blocked_item["tone"] == "red"
    assert blocked_item["value"] == "Cost limit blocked run"


def test_current_run_cost_and_monthly_cumulative_usage_remain_separate():
    health = operational_health(
        {
            "latest_run": {"usage_total_usd": 0.125, "status": "completed"},
            "last_successful_run": {"finished_at": "2026-07-17T06:42:00Z"},
            "monthly_usage_usd": 1.205,
            "warn_usd": 4.0,
            "stop_usd": 4.75,
            "lock": {"locked": False},
            "interrupted_runs": [],
            "telegram_send_enabled": False,
        }
    )
    assert health["current_run_cost_usd"] is None
    assert health["current_run_cost_note"] == "Not recorded with reliable per-run provenance"
    assert health["monthly_usage_usd"] == 1.205


def test_classification_groups_are_transparent_stored_field_rollups():
    groups = classification_groups(
        [
            {"lead_class": "hot_lead"},
            {"lead_class": "qualified_lead"},
            {"lead_class": "watch"},
            {"lead_class": "agent_broker"},
            {"lead_class": "irrelevant"},
            {"lead_class": "spam"},
            {"lead_class": None},
        ]
    )
    assert groups == {
        "Genuine seeker": 2,
        "Agent / offering": 1,
        "Irrelevant": 2,
        "Review required": 2,
    }


def test_classification_chart_uses_concise_labels_and_full_tooltip_definitions():
    groups = classification_groups(
        [
            {"lead_class": "hot_lead"},
            {"lead_class": "agent_broker"},
            {"lead_class": "irrelevant"},
            {"lead_class": None},
        ]
    )
    assert "Agent / offering" in groups
    assert all("broker or offering" not in category for category in groups)

    spec = overview_distribution_chart(
        groups,
        "Classification distribution",
        record_count=4,
    ).to_dict()
    tooltip_fields = [item["field"] for item in spec["encoding"]["tooltip"]]
    assert tooltip_fields == ["category", "definition", "value"]


def test_empty_and_limited_data_states_are_explicit():
    assert data_state(0) == "empty"
    assert data_state(1) == "limited"
    assert data_state(2) == "limited"
    assert data_state(3) == "ready"


def test_overview_volume_chart_has_truthful_title_and_finite_domain():
    spec = overview_volume_chart(
        {"Stored leads": 4, "High signal": 0, "Qualified": 1, "Delivered": 0}
    ).to_dict()
    assert spec["title"] == "Independent recorded volumes"
    assert spec["encoding"]["x"]["field"] == "value"
    assert spec["encoding"]["x"]["title"] == "Recorded count"
    assert spec["encoding"]["x"]["scale"]["domain"] == [0.0, 4.0]
    assert spec["encoding"]["x"]["stack"] is None


def test_overview_volume_chart_uses_concise_active_match_label_with_definition():
    values = independent_volume_values(
        {
            "total": 4,
            "hot": 1,
            "qualified": 1,
            "exact_match": 1,
            "nearby_alternative": 1,
            "tentative_match": 0,
            "telegram_delivered": 0,
        }
    )
    assert "Active matches" in values
    assert "Active real matches" not in values
    spec = overview_volume_chart(values).to_dict()
    assert [item["field"] for item in spec["encoding"]["tooltip"]] == [
        "stage",
        "definition",
        "value",
    ]


def test_overview_distribution_withholds_small_samples_as_limited_data():
    limited = overview_distribution_chart(
        {"Genuine seeker": 1, "Review required": 1},
        "Classification distribution",
        record_count=2,
    ).to_dict()
    assert limited["usermeta"]["rdsa_empty_state"] is True
    assert "Limited data" in limited["title"]

    ready = overview_distribution_chart(
        {"Exact": 0, "Nearby": 1, "Tentative": 0, "No match": 2},
        "Match-quality distribution",
        record_count=3,
    ).to_dict()
    assert ready["title"] == "Match-quality distribution"
    assert ready["encoding"]["x"]["scale"]["domain"] == [0.0, 2.0]


def test_overview_distributions_use_semantic_category_colors():
    classification = overview_distribution_chart(
        {
            "Genuine seeker": 4,
            "Review required": 3,
            "Agent / offering": 2,
            "Irrelevant": 1,
        },
        "Classification distribution",
        record_count=10,
    ).to_dict()
    classification_scale = classification["encoding"]["color"]["scale"]
    assert dict(zip(classification_scale["domain"], classification_scale["range"])) == {
        "Genuine seeker": COLORS["teal"],
        "Review required": COLORS["amber"],
        "Agent / offering": COLORS["blue"],
        "Irrelevant": COLORS["muted"],
    }

    match_quality = overview_distribution_chart(
        {"Exact": 4, "Nearby": 3, "Tentative": 2, "No match": 1},
        "Match-quality distribution",
        record_count=10,
    ).to_dict()
    match_scale = match_quality["encoding"]["color"]["scale"]
    match_colors = dict(zip(match_scale["domain"], match_scale["range"]))
    assert match_colors == {
        "Exact": COLORS["teal"],
        "Nearby": COLORS["blue"],
        "Tentative": COLORS["amber"],
        "No match": COLORS["muted"],
    }
    assert match_colors["No match"] != COLORS["teal"]


def test_overview_source_has_no_business_engine_or_secret_access():
    source = Path("dashboard/overview.py").read_text(encoding="utf-8")
    assert "get_overview" in source
    assert "get_leads" in source
    assert "get_inventory" in source
    assert "get_scheduler_status" in source
    for forbidden in (
        "sqlite3",
        "SELECT ",
        "classifier",
        "extractor",
        "matching.py",
        "TelegramNotifier",
        "ApifyThreadsProvider",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_CHAT_ID",
        "APIFY_API_TOKEN",
        "author_username",
    ):
        assert forbidden not in source


def test_overview_page_imports_with_pythonpath_unset():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy; runpy.run_path(r'dashboard/pages/1_Overview.py', run_name='__main__')",
        ],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
