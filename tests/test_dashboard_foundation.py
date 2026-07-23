"""Phase 2A contracts for the shared dashboard visual foundation."""

from pathlib import Path

from dashboard.components import (
    branded_page_header,
    classification_badge,
    comparison_row,
    confidence_badge,
    empty_state,
    kpi_card,
    match_tier_badge,
    metadata_row,
    status_badge,
    system_status_strip,
)
from dashboard.formatters import (
    format_idr,
    format_period,
    format_source_age,
    format_timestamp,
    format_value,
    match_tier_label,
    sanitized_excerpt,
)
from dashboard.theme import (
    BORDER_TOKENS,
    COLOR_TOKENS,
    COMPONENT_CSS,
    RADIUS_TOKENS,
    SPACING_TOKENS,
    STREAMLIT_SHELL_CSS,
    SURFACE_TOKENS,
    TYPOGRAPHY_TOKENS,
)


def test_theme_tokens_are_complete_and_restrained():
    assert {
        "canvas",
        "sidebar",
        "surface",
        "surface_raised",
        "surface_hover",
        "border_subtle",
        "border_strong",
        "text_primary",
        "text_secondary",
        "text_muted",
        "text_disabled",
        "teal",
        "amber",
        "red",
        "blue",
    } <= COLOR_TOKENS.keys()
    assert {"display", "page_title", "section_title", "body", "label", "metadata", "kpi"} <= TYPOGRAPHY_TOKENS.keys()
    assert {1, 2, 3, 4, 6, 8, 12} <= SPACING_TOKENS.keys()
    assert {"sm", "md", "lg"} <= RADIUS_TOKENS.keys()
    assert {"default", "selected", "critical"} <= BORDER_TOKENS.keys()
    assert {"canvas", "sidebar", "card", "raised", "hover"} <= SURFACE_TOKENS.keys()
    combined = (STREAMLIT_SHELL_CSS + COMPONENT_CSS).lower()
    assert "gradient" not in combined
    assert "glow" not in combined
    assert "@keyframes" not in combined


def test_streamlit_testid_selectors_are_isolated_to_shell_css():
    assert "data-testid" in STREAMLIT_SHELL_CSS
    assert "data-testid" not in COMPONENT_CSS
    assert 'data-testid="stAppDeployButton"' in STREAMLIT_SHELL_CSS
    assert 'data-testid="stMainMenu"' in STREAMLIT_SHELL_CSS
    assert "stSidebarCollapseButton" not in STREAMLIT_SHELL_CSS


def test_focus_ring_only_applies_to_focused_interactive_elements():
    assert "a:focus-visible, button:focus-visible" in COMPONENT_CSS
    assert "a, button, input" not in COMPONENT_CSS


def test_semantic_badges_follow_the_design_language():
    assert "rdsa-blue" in classification_badge("hot_lead")
    assert "rdsa-teal" in classification_badge("qualified_lead")
    assert "rdsa-red" in status_badge("rejected")
    assert "rdsa-teal" in match_tier_badge("exact_match")
    assert "rdsa-amber" in match_tier_badge("no_match")
    assert "rdsa-amber" in confidence_badge("unknown")
    assert "rdsa-legacy" in match_tier_badge("legacy_synthetic")


def test_shared_component_html_is_semantic_sanitized_and_backward_compatible(monkeypatch):
    rendered = []
    monkeypatch.setattr("dashboard.components.st.markdown", lambda body, **_: rendered.append(body))

    header = branded_page_header("Lead <Inbox>", "Review & triage", meta="Read-only")
    strip = system_status_strip([
        {"label": "Database", "value": "Connected", "tone": "teal"},
        {"label": "Scheduler", "value": "Disabled", "tone": "legacy"},
    ])
    card = kpi_card("Needs review", 0, "Recorded count", tone="amber")
    empty = empty_state("No leads", "No records match <these> filters.")
    meta = metadata_row([("Source", "Threads"), ("Age", "12m")])
    row = comparison_row("Area", "BSD", "Gading Serpong", "Nearby", tone="amber")

    assert "<Inbox>" not in header and "&lt;Inbox&gt;" in header
    assert 'role="status"' in strip
    assert ">0<" in card
    assert 'role="status"' in empty and "&lt;these&gt;" in empty
    assert "Source" in meta and "Threads" in meta
    assert "Nearby" in row and "rdsa-amber" in row
    assert rendered


def test_currency_period_and_missing_value_formatting():
    assert format_idr(1_250_000) == "IDR 1.250.000"
    assert format_idr(0) == "IDR 0"
    assert format_idr(None) == "Not recorded"
    assert format_period("month") == "Monthly"
    assert format_period("annual") == "Yearly"
    assert format_period(None) == "Period not recorded"
    assert format_value(0) == "0"
    assert format_value(None) == "Not recorded"
    assert format_value("") == "Not recorded"


def test_timestamp_and_source_age_are_utc_and_honest():
    assert format_timestamp("2026-07-17T06:42:00Z") == "17 Jul 2026, 06:42 UTC"
    assert format_timestamp(None) == "Not recorded"
    assert format_timestamp("not-a-date") == "Invalid timestamp"
    assert format_source_age("2026-07-17T06:30:00Z", now="2026-07-17T06:42:00Z") == "12m ago"
    assert format_source_age(None, now="2026-07-17T06:42:00Z") == "Age not recorded"


def test_sanitized_excerpt_removes_contacts_markup_and_excess_length():
    source = "<b>Owner</b> owner@example.com 081234567890 " + ("apartment " * 50)
    excerpt = sanitized_excerpt(source, max_length=90)
    assert "owner@example.com" not in excerpt
    assert "081234567890" not in excerpt
    assert "<b>" not in excerpt
    assert len(excerpt) <= 90
    assert excerpt.endswith("…")
    assert sanitized_excerpt(None) == "No source excerpt recorded"


def test_match_tier_labels_are_exact_and_legacy_is_explicit():
    assert match_tier_label("exact_match") == "Exact"
    assert match_tier_label("nearby_alternative") == "Nearby"
    assert match_tier_label("tentative_match") == "Tentative"
    assert match_tier_label("no_match") == "No match"
    assert match_tier_label("legacy_synthetic") == "Legacy historical"


def test_shared_foundation_source_contains_no_credentials_or_private_fields():
    source = "\n".join(
        (Path("dashboard") / name).read_text(encoding="utf-8")
        for name in ("theme.py", "components.py", "formatters.py", "charts.py")
    )
    forbidden = (
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_CHAT_ID",
        "APIFY_API_TOKEN",
        "author_username",
    )
    assert all(value not in source for value in forbidden)


def test_every_page_preserves_the_repository_root_import_bootstrap():
    for page in sorted((Path("dashboard") / "pages").glob("*.py")):
        source = page.read_text(encoding="utf-8")
        dashboard_import = source.find("from dashboard.")
        bootstrap = source.find("sys.path.insert(0, _ROOT)")
        assert bootstrap >= 0, f"{page.name} is missing the permanent root bootstrap"
        assert '_ROOT = str(Path(__file__).resolve().parents[2])' in source, (
            f"{page.name} bootstrap must point to the repository root"
        )
        assert dashboard_import < 0 or bootstrap < dashboard_import, (
            f"{page.name} imports dashboard before the root bootstrap"
        )
