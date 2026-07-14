from types import SimpleNamespace

import pytest

from rdsa import config
from rdsa.cli import main
from rdsa.db import already_sent, connect, mark_alert
from rdsa.notifier import TelegramNotifier, format_preview_card, redact_token, send_lead_cards


def lead(post_id, score=80, klass="hot_lead"):
    return SimpleNamespace(post_id=post_id, lead_class=klass, lead_score=score,
                           score_breakdown=[], matched_inventory=[], desired_location="BSD",
                           property_type="apartment", bedrooms=2, budget_max=7000000,
                           move_in_date="", post_timestamp="2026-07-13T00:00:00Z", source_url="https://threads.net/p/" + post_id)


class FakeNotifier:
    def __init__(self, failure=False): self.calls=[]; self.failure=failure
    def send(self, text):
        self.calls.append(text)
        if self.failure: raise RuntimeError("[REDACTED_TOKEN] network failure")
        return len(self.calls)


def test_disabled_delivery_returns_without_send(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)
    n=FakeNotifier()
    assert send_lead_cards(n, [lead("x")], connect(":memory:")) == 0
    assert not n.calls


def test_allowed_chat_enforcement(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "123")
    with pytest.raises(ValueError): TelegramNotifier("bad", "999").send("x")


def test_confirmation_is_required(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
    monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "123")
    monkeypatch.setattr(TelegramNotifier, "send", lambda *a, **k: (_ for _ in ()).throw(AssertionError("sent")))
    main(["telegram-test"])


def test_max_three_and_dedup(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
    c=connect(":memory:"); n=FakeNotifier()
    assert send_lead_cards(n, [lead(str(i), i) for i in range(5)], c) == 3
    assert len(n.calls) == 3
    mark_alert(c, "4", 99)
    n.calls.clear(); send_lead_cards(n, [lead("4", 100)], c)
    assert not n.calls and already_sent(c, "4")


def test_redaction_and_card_sanitization():
    assert "bot123:ABC" not in redact_token("https://x/bot123:ABC/secret")
    l=lead("x"); l.score_breakdown=[{"reason":"call 081234567890 or me@example.com"}]
    card=format_preview_card(l)
    assert "081234567890" not in card and "me@example.com" not in card


def test_no_eligible_sends_one_summary(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
    n=FakeNotifier(); send_lead_cards(n, [lead("x", klass="watch")], connect(":memory:"), posts_scanned=2, new_leads=1)
    assert len(n.calls) == 1 and "run complete" in n.calls[0]
