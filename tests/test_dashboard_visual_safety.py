from pathlib import Path


def test_dashboard_source_has_no_live_delivery_or_provider_paths():
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("dashboard").rglob("*.py"))
    for forbidden in ("apify_provider", "TelegramNotifier", "requests", "send_lead_cards", "plotly"):
        assert forbidden not in source.lower()


def test_dashboard_source_does_not_render_credentials_or_private_author_fields():
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("dashboard").rglob("*.py"))
    for forbidden in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_CHAT_ID", "APIFY_API_TOKEN", "author_username"):
        assert forbidden not in source


def test_dashboard_source_has_no_synthetic_inventory_fallback():
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("dashboard").rglob("*.py"))
    assert "synthetic" not in source.lower()
