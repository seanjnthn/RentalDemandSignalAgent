from pathlib import Path

from rdsa.dashboard_repository import sanitize


def test_dashboard_code_has_no_send_or_provider_call_path():
    source = "\n".join(p.read_text(encoding="utf-8") for p in Path("dashboard").rglob("*.py"))
    assert "send_lead_cards" not in source
    assert "TelegramNotifier" not in source
    assert "ApifyThreadsProvider" not in source
    assert "requests." not in source
    assert "synthetic" not in source.lower()


def test_credentials_and_private_identifiers_are_not_rendered_by_dashboard_code():
    source = "\n".join(p.read_text(encoding="utf-8") for p in Path("dashboard").rglob("*.py"))
    for secret_name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_CHAT_ID", "APIFY_API_TOKEN"):
        assert secret_name not in source
    assert "author_username" not in source
    assert "internal row" not in source.lower()


def test_phone_and_email_sanitization():
    output = sanitize("Call +628123456789 or 081234567890, email owner@example.com")
    assert "+628123456789" not in output
    assert "081234567890" not in output
    assert "owner@example.com" not in output
