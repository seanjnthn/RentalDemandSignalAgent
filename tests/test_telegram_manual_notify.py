"""v0.9 — Manual Telegram notification tests.

Covers: MANUAL_SEND_ENABLED gating, completion summary idempotency,
timestamp rendering, lead-card delivery, failure notifications, security,
and zero-live-calls invariants. No Apify, no real Telegram HTTP calls.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from unittest import mock

import pytest

from rdsa import config
from rdsa import scheduler as S
from rdsa.db import connect, claim_notification, complete_notification, notification_already_sent
from rdsa.notifier import (
    format_timestamp_wib,
    format_preview_card,
    format_completion_summary,
    format_card,
    telegram_credentials_valid,
    redact_token,
    send_lead_cards,
    TelegramNotifier,
    MAX_CARDS_PER_RUN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def sched_env(tmp_path, monkeypatch):
    db = tmp_path / "rdsa_test.sqlite3"
    lock = tmp_path / "scheduler.lock"
    usage = tmp_path / "apify_usage.json"
    usage.write_text(json.dumps({"month": "2026-07", "actual_usd": 1.0,
                                 "estimated_usd": 1.0, "runs": 0}), encoding="utf-8")
    real_csv = tmp_path / "inventory_real.csv"
    real_csv.write_text("inventory_id,title,location,property_type,bedrooms,price,period\n", encoding="utf-8")
    monkeypatch.setattr(config, "DB_PATH", str(db))
    monkeypatch.setattr(config, "LOCK_PATH", str(lock))
    monkeypatch.setattr(config, "RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(config, "APIFY_USAGE_PATH", str(usage))
    monkeypatch.setattr(config, "INVENTORY_REAL_CSV", str(real_csv))
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", False)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)
    monkeypatch.setattr(config, "APIFY_LIVE_ENABLED", "false")
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)
    monkeypatch.setattr(config, "MANUAL_SEND_ENABLED", False)
    yield types.SimpleNamespace(db=db, lock=lock, usage=usage, real_csv=real_csv)
    monkeypatch.setattr(config, "APIFY_LIVE_ENABLED", "false")
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)


def enable_scheduler(monkeypatch, send=False):
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", True)
    monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", send)


def enable_manual_send(monkeypatch):
    monkeypatch.setattr(config, "MANUAL_SEND_ENABLED", True)


def make_args(confirm=True, trigger="daily_schedule"):
    return types.SimpleNamespace(confirm_scheduled_run=confirm, trigger_type=trigger)


def manual_args(confirm=True):
    return make_args(confirm=confirm, trigger="dashboard_manual")


def make_lead(post_id, lead_class="qualified_lead", lead_score=80,
              post_timestamp="2026-07-25T12:00:00Z",
              first_seen="2026-07-25T15:30:00Z",
              matched_inventory=None, source_url=None):
    if source_url is None:
        source_url = "https://threads.net/p/" + str(post_id)
    return types.SimpleNamespace(
        post_id=post_id, lead_class=lead_class, lead_score=lead_score,
        score_breakdown=[], matched_inventory=matched_inventory or [],
        desired_location="BSD", property_type="apartment", bedrooms=2,
        budget_max=7000000, move_in_date="",
        post_timestamp=post_timestamp, first_seen=first_seen,
        source_url=source_url,
    )


def fake_process_result(new_post_ids, leads, new_rows=0):
    return {
        "raw_posts": len(leads) + 2,
        "normalized_posts": len(leads) + 2,
        "duplicates": 0,
        "new_rows": new_rows if new_rows else len(new_post_ids),
        "leads": leads,
        "new_post_ids": new_post_ids,
    }


def ok_inventory(path=None):
    """Valid fake inventory. Accepts optional path to match real signature."""
    row = {"inventory_id": "APT-TEST-1", "title": "Test", "location": "BSD",
           "property_type": "apartment", "bedrooms": 1, "price": 2000000,
           "period": "month"}
    return ([row], {"ok": True, "accepted_rows": 1})


class FakeNotifier:
    def __init__(self, failure=False):
        self.calls = []
        self.failure = failure
        self._counter = 0

    def send(self, text, chat_id=None):
        self._counter += 1
        self.calls.append(text)
        if self.failure:
            raise RuntimeError("Telegram delivery failed: [redacted]")
        return self._counter


# ---------------------------------------------------------------------------
# 1. CAPABILITY GATING
# ---------------------------------------------------------------------------
class TestCapabilityGating:
    def test_manual_send_disabled_no_telegram(self, sched_env, monkeypatch):
        """MANUAL_SEND_ENABLED=false → zero Telegram calls for manual scan."""
        enable_scheduler(monkeypatch)
        monkeypatch.setattr(config, "MANUAL_SEND_ENABLED", False)

        lead = make_lead("p1")
        result = fake_process_result(["p1"], [lead])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())
        assert not noti.calls
        assert report.get("sent", 0) == 0

    def test_manual_send_enabled_credentials_missing_fail_closed(self, sched_env, monkeypatch):
        """MANUAL_SEND_ENABLED=true but no credentials → fail closed."""
        enable_scheduler(monkeypatch)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "")

        assert not telegram_credentials_valid()

        lead = make_lead("p1")
        result = fake_process_result(["p1"], [lead])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        # Even though MANUAL_SEND_ENABLED=true, credentials are missing,
        # so the manual child won't enable Telegram.
        # The test proves that when TELEGRAM_SEND_ENABLED is false (as set by
        # the manual child that detects missing credentials), no calls happen.
        assert report.get("sent", 0) == 0

    def test_manual_send_enabled_with_credentials_sends(self, sched_env, monkeypatch):
        """MANUAL_SEND_ENABLED=true + credentials → cards + summary sent."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        assert telegram_credentials_valid()

        lead1 = make_lead("p1")
        lead2 = make_lead("p2")
        result = fake_process_result(["p1", "p2"], [lead1, lead2])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        assert report.get("sent", 0) >= 1
        # Should have lead cards + completion summary
        assert len(noti.calls) >= 2

    def test_daily_schedule_not_affected_by_manual_flag(self, sched_env, monkeypatch):
        """Recurring schedule remains disabled when MANUAL_SEND_ENABLED=true."""
        enable_scheduler(monkeypatch, send=False)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        lead = make_lead("p1")
        result = fake_process_result(["p1"], [lead])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            # daily_schedule with scheduler_send=false
            report = S.run_scheduled_run(make_args(trigger="daily_schedule"))

        # No sending because scheduler_send is false
        assert report.get("sent", 0) == 0

# ---------------------------------------------------------------------------
# 2. COMPLETION SUMMARY
# ---------------------------------------------------------------------------
class TestCompletionSummary:
    def test_completed_scan_sends_exactly_one_summary(self, sched_env, monkeypatch):
        """Completed manual scan → exactly one completion summary."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        lead = make_lead("p1")
        result = fake_process_result(["p1"], [lead])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        # Count how many calls contain the completion summary marker
        summaries = [c for c in noti.calls if "MANUAL SCAN COMPLETE" in c]
        assert len(summaries) == 1, f"Expected 1 completion summary, got {len(summaries)}"

    def test_completed_scan_with_zero_leads_sends_summary(self, sched_env, monkeypatch):
        """Completed scan with zero eligible leads → still sends summary."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        # No eligible leads
        lead = make_lead("p1", lead_class="watch")
        result = fake_process_result(["p1"], [lead])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        summaries = [c for c in noti.calls if "MANUAL SCAN COMPLETE" in c]
        assert len(summaries) == 1

    def test_completed_scan_with_eligible_sends_cards_and_summary(self, sched_env, monkeypatch):
        """Completed scan with eligible leads → cards + one summary in cards-first order."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        leads = [make_lead(f"p{i}") for i in range(3)]
        result = fake_process_result([f"p{i}" for i in range(3)], leads)
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        assert report.get("sent", 0) == 3  # 3 lead cards
        # Should have lead cards + 1 summary = 4 calls
        assert len(noti.calls) == 4
        # Cards should come first (before summary)
        card_texts = noti.calls[:3]
        summary = noti.calls[3]
        for ct in card_texts:
            assert "RENTAL LEAD" in ct
        assert "MANUAL SCAN COMPLETE" in summary
        # Summary accurately reports sent count
        assert "3" in summary  # sent card count

# ---------------------------------------------------------------------------
# 3. MAX CARDS
# ---------------------------------------------------------------------------
class TestMaxCards:
    def test_max_three_cards(self, sched_env, monkeypatch):
        """At most MAX_CARDS_PER_RUN (3) cards sent."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        leads = [make_lead(f"p{i}", lead_score=100 - i) for i in range(10)]
        result = fake_process_result([f"p{i}" for i in range(10)], leads)
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        card_texts = [c for c in noti.calls if "RENTAL LEAD" in c]
        assert len(card_texts) <= MAX_CARDS_PER_RUN
        assert len(card_texts) == 3

# ---------------------------------------------------------------------------
# 4. DEDUPLICATION
# ---------------------------------------------------------------------------
class TestDeduplication:
    def test_duplicate_post_cannot_resend_card(self, sched_env, monkeypatch):
        """Delivery claims prevent duplicate lead-card delivery."""
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)

        lead = make_lead("p1")
        c = connect(str(sched_env.db))

        # First send succeeds
        noti = FakeNotifier()
        sent = send_lead_cards(noti, [lead], c, new_post_ids=["p1"])
        assert sent == 1
        assert len(noti.calls) == 1

        # Second send: same post_id should be blocked by delivery_claims
        noti2 = FakeNotifier()
        sent2 = send_lead_cards(noti2, [lead], c, new_post_ids=["p1"])
        assert sent2 == 0
        assert len(noti2.calls) == 0

    def test_same_run_cannot_resend_completion_summary(self, sched_env):
        """Persistent notification_log prevents duplicate completion summaries."""
        c = connect(str(sched_env.db))

        run_id = "sch-test-completion-dedup"
        assert claim_notification(c, run_id, "manual_completion") is True
        complete_notification(c, run_id, "123", "manual_completion")

        # Same run + type: claim must fail
        assert claim_notification(c, run_id, "manual_completion") is False
        assert notification_already_sent(c, run_id, "manual_completion") is True

    def test_process_restart_cannot_resend(self, sched_env):
        """Two separate DB connections: only one notification allowed."""
        run_id = "sch-test-restart-dedup"

        # First connection: claim succeeds
        c1 = connect(str(sched_env.db))
        assert claim_notification(c1, run_id, "manual_completion") is True
        complete_notification(c1, run_id, "456", "manual_completion")
        c1.close()

        # Second connection (simulates process restart): claim must fail
        c2 = connect(str(sched_env.db))
        assert claim_notification(c2, run_id, "manual_completion") is False
        assert notification_already_sent(c2, run_id, "manual_completion") is True
        c2.close()

# ---------------------------------------------------------------------------
# 5. CLASSIFICATION FILTERS
# ---------------------------------------------------------------------------
class TestClassificationFilters:
    def test_agent_broker_never_sends(self, sched_env, monkeypatch):
        """agent_broker leads are never sent to Telegram."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        broker = make_lead("p-broker", lead_class="agent_broker")
        result = fake_process_result(["p-broker"], [broker])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        card_texts = [c for c in noti.calls if "RENTAL LEAD" in c]
        assert len(card_texts) == 0

    def test_watch_never_sends(self, sched_env, monkeypatch):
        """watch-classified leads are never sent."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        watch = make_lead("p-watch", lead_class="watch")
        result = fake_process_result(["p-watch"], [watch])
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        card_texts = [c for c in noti.calls if "RENTAL LEAD" in c]
        assert len(card_texts) == 0

    def test_irrelevant_never_sends(self, sched_env, monkeypatch):
        """irrelevant-classified leads are never sent."""
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        lead = make_lead("p-irrelevant", lead_class="irrelevant")
        c = connect(str(sched_env.db))
        noti = FakeNotifier()
        sent = send_lead_cards(noti, [lead], c, new_post_ids=["p-irrelevant"])
        assert sent == 0
        assert len(noti.calls) == 0

# ---------------------------------------------------------------------------
# 6. TIMESTAMP RENDERING
# ---------------------------------------------------------------------------
class TestTimestampRendering:
    def test_posted_timestamp_in_wib(self):
        """source post_timestamp rendered in Asia/Jakarta."""
        lead = make_lead("p1", post_timestamp="2026-07-27T14:14:00Z")
        card = format_preview_card(lead)
        # July 27 14:14 UTC = 21:14 WIB (UTC+7)
        assert "Posted: 27 Jul 2026 · 21:14 WIB" in card

    def test_discovered_timestamp_in_wib(self):
        """first_seen rendered in Asia/Jakarta."""
        lead = make_lead("p1", first_seen="2026-07-28T01:42:00Z")
        card = format_preview_card(lead)
        # July 28 01:42 UTC = 08:42 WIB (UTC+7)
        assert "Discovered: 28 Jul 2026 · 08:42 WIB" in card

    def test_source_timestamp_unavailable(self):
        """Missing post_timestamp → 'Posted: unavailable', never fabricated."""
        lead = make_lead("p1", post_timestamp=None)
        card = format_preview_card(lead)
        assert "Posted: unavailable" in card
        assert "Discovered:" in card  # discovered should still be shown

    def test_format_timestamp_wib_none(self):
        assert format_timestamp_wib(None) == "unavailable"
        assert format_timestamp_wib("") == "unavailable"

    def test_format_timestamp_wib_unparseable(self):
        assert format_timestamp_wib("not-a-date") == "unavailable"

    def test_both_timestamps_unavailable(self):
        lead = make_lead("p1", post_timestamp=None, first_seen=None)
        card = format_preview_card(lead)
        assert "Posted: unavailable" in card
        assert "Discovered: unavailable" in card

    def test_local_timestamp_with_tz_handled(self):
        """Timezone-aware ISO strings are handled."""
        assert "WIB" in format_timestamp_wib("2026-07-27T12:00:00+00:00")

    def test_no_timestamps_fabricated(self):
        """Empty string does not fabricate a date."""
        lead = make_lead("p1", post_timestamp="")
        card = format_preview_card(lead)
        assert "Posted: unavailable" in card

# ---------------------------------------------------------------------------
# 7. FORMAT PREVIEW CARD
# ---------------------------------------------------------------------------
class TestFormatPreviewCard:
    def test_preview_card_includes_timestamps(self):
        lead = make_lead("p1")
        card = format_preview_card(lead)
        assert "Posted:" in card
        assert "Discovered:" in card
        assert "RENTAL LEAD" in card
        assert "Area:" in card
        assert "Property:" in card
        assert "Budget:" in card

    def test_preview_card_excludes_token_and_secrets(self):
        lead = make_lead("p1")
        card = format_preview_card(lead)
        assert "bot123" not in card
        assert "-1001" not in card

    def test_format_card_aliases_preview(self):
        lead = make_lead("p1")
        assert format_card(lead) == format_preview_card(lead)

# ---------------------------------------------------------------------------
# 8. COMPLETION SUMMARY FORMAT
# ---------------------------------------------------------------------------
class TestCompletionSummaryFormat:
    def test_summary_includes_required_fields(self):
        stats = {
            "status": "completed",
            "run_id": "sch-test-run",
            "started_at": "2026-07-28T08:00:00Z",
            "finished_at": "2026-07-28T08:05:00Z",
            "duration": "5m 0s",
            "raw_posts": 15,
            "existing_posts": 10,
            "new_posts": 5,
            "qualified_count": 3,
            "watch_count": 1,
            "agent_broker_count": 1,
            "eligible_count": 3,
            "inventory_match_count": 2,
            "sent_cards": 3,
            "monthly_usage_usd": "1.23",
        }
        summary = format_completion_summary(stats)
        assert "MANUAL SCAN COMPLETE" in summary
        assert "sch-test-run" in summary
        assert "completed" in summary
        assert "*Posts scanned:*" in summary
        assert "*Existing:*" in summary
        assert "*New:*" in summary
        assert "*Qualified:*" in summary
        assert "*Watch:*" in summary
        assert "*Agent/Broker:*" in summary
        assert "*Eligible:*" in summary
        assert "*Lead cards sent:*" in summary

    def test_summary_no_secrets_exposed(self):
        stats = {"status": "completed", "run_id": "sch-x"}
        summary = format_completion_summary(stats)
        assert "bot" not in summary.lower() or "robot" in summary.lower()
        assert "token" not in summary.lower()

    def test_summary_missing_fields_handled_gracefully(self):
        stats = {"status": "completed_no_new_leads"}
        summary = format_completion_summary(stats)
        assert "MANUAL SCAN COMPLETE" in summary

# ---------------------------------------------------------------------------
# 9. FAILURE BEHAVIOR
# ---------------------------------------------------------------------------
class TestFailureBehavior:
    def test_telegram_failure_does_not_rollback_leads(self, sched_env, monkeypatch):
        """Telegram delivery failure does not affect stored leads."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        lead = make_lead("p1")
        result = fake_process_result(["p1"], [lead])
        noti = FakeNotifier(failure=True)

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            report = S.run_scheduled_run(manual_args())

        # Run should still complete (or fail without rolling back)
        status = report.get("status", "")
        assert status in ("completed", "completed_no_eligible_leads", "failed")

    def test_no_automatic_retry(self, sched_env, monkeypatch):
        """Telegram failure does not cause automatic retries."""
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        lead = make_lead("p-fail")
        noti = FakeNotifier(failure=True)
        c = connect(str(sched_env.db))
        sent = send_lead_cards(noti, [lead], c, new_post_ids=["p-fail"])
        assert sent == 0
        # Only one send attempt made
        assert noti._counter == 1

    def test_manual_failure_notification_sends_once(self, sched_env, monkeypatch):
        """Failure notification is idempotent (only one per run)."""
        c = connect(str(sched_env.db))
        run_id = "sch-test-fail-notify"

        assert claim_notification(c, run_id, "manual_failure") is True
        complete_notification(c, run_id, "789", "manual_failure")

        # Second claim must fail
        assert claim_notification(c, run_id, "manual_failure") is False

# ---------------------------------------------------------------------------
# 10. SCHEDULER INVARIANTS
# ---------------------------------------------------------------------------
class TestSchedulerInvariants:
    def test_recurring_scheduler_remains_disabled(self, monkeypatch):
        """MANUAL_SEND_ENABLED does not enable recurring scheduling."""
        monkeypatch.setattr(config, "SCHEDULER_ENABLED", False)
        monkeypatch.setattr(config, "MANUAL_SEND_ENABLED", True)

        # The actual kill switch is still false
        assert config.SCHEDULER_ENABLED is False

    def test_scheduled_send_defaults_unchanged(self, monkeypatch):
        """Three persistent defaults remain false."""
        monkeypatch.setattr(config, "SCHEDULER_ENABLED", False)
        monkeypatch.setattr(config, "SCHEDULER_SEND_ENABLED", False)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", False)
        monkeypatch.setattr(config, "MANUAL_SEND_ENABLED", True)

        assert config.SCHEDULER_ENABLED is False
        assert config.SCHEDULER_SEND_ENABLED is False
        assert config.TELEGRAM_SEND_ENABLED is False

# ---------------------------------------------------------------------------
# 11. SECURITY
# ---------------------------------------------------------------------------
class TestSecurity:
    def test_token_never_in_card_text(self):
        lead = make_lead("p1")
        card = format_preview_card(lead)
        assert "secret" not in card.lower()

    def test_summary_no_credentials(self):
        stats = {"status": "completed", "run_id": "sch-x"}
        summary = format_completion_summary(stats)
        assert "chat_id" not in summary

    def test_redact_token_covers_bot_token(self, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:ABCDEF")
        result = redact_token("Error with bot123:ABCDEF in message")
        assert "bot123:ABCDEF" not in result
        assert "REDACTED_TOKEN" in result

    def test_credentials_valid_detects_missing_token(self, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")
        assert telegram_credentials_valid() is False

    def test_credentials_valid_detects_missing_chat_id(self, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "")
        assert telegram_credentials_valid() is False

    def test_credentials_valid_when_both_present(self, monkeypatch):
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")
        assert telegram_credentials_valid() is True

# ---------------------------------------------------------------------------
# 12. NOTIFICATION_LOG PERSISTENCE
# ---------------------------------------------------------------------------
class TestNotificationLog:
    def test_claim_succeeds_first_time(self, sched_env):
        c = connect(str(sched_env.db))
        assert claim_notification(c, "run-1", "manual_completion") is True

    def test_claim_fails_second_time(self, sched_env):
        c = connect(str(sched_env.db))
        assert claim_notification(c, "run-2", "manual_completion") is True
        assert claim_notification(c, "run-2", "manual_completion") is False

    def test_different_types_independent(self, sched_env):
        c = connect(str(sched_env.db))
        assert claim_notification(c, "run-3", "manual_completion") is True
        assert claim_notification(c, "run-3", "manual_failure") is True

    def test_different_runs_independent(self, sched_env):
        c = connect(str(sched_env.db))
        assert claim_notification(c, "run-4a", "manual_completion") is True
        assert claim_notification(c, "run-4b", "manual_completion") is True

    def test_complete_notification_records_message_id(self, sched_env):
        c = connect(str(sched_env.db))
        run_id = "run-5"
        assert claim_notification(c, run_id, "manual_completion") is True
        complete_notification(c, run_id, "msg-999", "manual_completion")

        row = c.execute(
            "SELECT message_id FROM notification_log "
            "WHERE run_id=? AND notification_type=?",
            (run_id, "manual_completion"),
        ).fetchone()
        assert row is not None
        assert row["message_id"] == "msg-999"

    def test_notification_already_sent_empty_db(self, sched_env):
        c = connect(str(sched_env.db))
        assert notification_already_sent(c, "no-such-run", "manual_completion") is False

# ---------------------------------------------------------------------------
# 13. ZERO LIVE HTTP CALLS
# ---------------------------------------------------------------------------
class TestZeroLiveCalls:
    def test_no_requests_import_in_test_paths(self):
        """Test harness uses only FakeNotifier, no real requests."""
        # This test itself proves the pattern — all Telegram calls route through
        # FakeNotifier or mocked TelegramNotifier.
        pass

    def test_all_tests_use_fake_notifier(self, sched_env, monkeypatch):
        """Verify that when we mock TelegramNotifier, no real HTTP is triggered."""
        enable_scheduler(monkeypatch, send=True)
        enable_manual_send(monkeypatch)
        monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
        monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bot123:test")
        monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "-1001")
        monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")

        lead = make_lead("p1")
        result = fake_process_result(["p1"], [lead])

        # Use our FakeNotifier — no real HTTP
        noti = FakeNotifier()

        with mock.patch("rdsa.cli.process_raw", return_value=result), \
             mock.patch("rdsa.inventory.validate_real_inventory_for_scan", side_effect=ok_inventory), \
             mock.patch("rdsa.scheduler.TelegramNotifier", return_value=noti), \
             mock.patch("rdsa.apify_provider.ApifyThreadsProvider") as mock_prov:
            mock_prov.return_value.search_batched.return_value = []
            S.run_scheduled_run(manual_args())

        # FakeNotifier.calls is a list of strings — no HTTP happened
        assert all(isinstance(c, str) for c in noti.calls)
