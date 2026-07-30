import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
from . import config

MAX_CARDS_PER_RUN = 3
WIB = ZoneInfo("Asia/Jakarta")


def redact_token(text):
    value = str(text)
    tokens = [config.TELEGRAM_BOT_TOKEN] if config.TELEGRAM_BOT_TOKEN else []
    for token in tokens:
        value = value.replace(token, "[REDACTED_TOKEN]")
    return re.sub(r"bot\d+:[A-Za-z0-9_-]+", "[REDACTED_TOKEN]", value)


def format_timestamp_wib(utc_iso):
    """Convert a UTC ISO-8601 timestamp to human-readable WIB (Asia/Jakarta).

    Returns a string like '27 Jul 2026 · 21:14 WIB' or 'unavailable' if the
    input is None, empty, or unparseable. Never fabricates a value.
    """
    if not utc_iso:
        return "unavailable"
    try:
        dt = datetime.fromisoformat(str(utc_iso).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local = dt.astimezone(WIB)
        return local.strftime("%d %b %Y · %H:%M WIB")
    except (ValueError, TypeError, OverflowError):
        return "unavailable"


def _get(lead, name, default=None): return lead.get(name, default) if isinstance(lead, dict) else getattr(lead, name, default)
def preview_eligible(lead): return _get(lead, "lead_class") in ("hot_lead", "qualified_lead")


def _safe(value, fallback="not stated"):
    value = str(value or fallback)
    value = re.sub(r"(?:\+62|0\d{8,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", "[redacted]", value)
    return value[:120]


def format_preview_card(lead, matching_enabled=True):
    """Format a lead card for Telegram delivery.

    Timestamps:
      - Posted   → authoritative Threads post timestamp (post_timestamp), in WIB
      - Discovered → RDSA first-seen timestamp (first_seen), in WIB

    Neither timestamp is fabricated. If unavailable, displays 'unavailable'.
    """
    breakdown = _get(lead, "score_breakdown", []) or []
    reasons = [_safe(x.get("reason", "")) for x in breakdown[:3] if isinstance(x, dict) and x.get("reason")]
    matches = _get(lead, "matched_inventory", []) or []
    if not matching_enabled:
        matches_block = "Inventory matches: Not configured"
    else:
        lines = "\n".join(
            f"{i}. {_safe(m.get('property_id', m.get('inventory_id', 'unknown')))}"
            f" - {m.get('match_type', 'exact_match')} - {m.get('score', 0)}"
            + (f" ({_safe(m.get('warnings', [None])[0])})" if m.get('warnings') else "")
            for i, m in enumerate(matches[:3], 1)
        ) or "No suitable unit found"
        matches_block = "Inventory matches:\n" + lines if matches else "Inventory matches: No suitable unit found"

    budget = _get(lead, "budget_max") or _get(lead, "budget_min")
    budget_confidence = _get(lead, "budget_confidence", "low")
    budget = f"{budget:,} IDR" if budget_confidence in ("high", "medium") and isinstance(budget, int) else "unclear — review original post"
    ptype = _get(lead, "property_type") or "unknown"
    beds = _get(lead, "bedrooms")
    property_text = f"{ptype} {beds} bedroom" if beds else str(ptype)
    source = _get(lead, "source_url", "")
    source = _safe(source, "") if re.match(r"^https?://", str(source)) else ""

    # Timestamps (v0.9): authoritative post_timestamp and first_seen in WIB
    posted = format_timestamp_wib(_get(lead, "post_timestamp"))
    discovered = format_timestamp_wib(_get(lead, "first_seen"))

    return (
        f"🏠 RENTAL LEAD — {_get(lead, 'lead_score', 0)}/100\n\n"
        f"Posted: {posted}\n"
        f"Discovered: {discovered}\n"
        f"Area: {_safe(_get(lead, 'desired_location'), 'unknown')}\n"
        f"Property: {_safe(property_text)}\n"
        f"Budget: {budget}\n"
        f"Move-in: {_safe(_get(lead, 'move_in_date'))}\n\n"
        f"Why qualified:\n- {_safe('; '.join(reasons) if reasons else 'qualified by scoring rules')}\n\n"
        f"{matches_block}\n\n"
        f"Recommended action:\nReview the original Threads post and contact manually if appropriate.\n\n{source}"
    )


def format_card(lead):
    return format_preview_card(lead)


def format_completion_summary(stats: dict) -> str:
    """Format a manual-scan completion summary for Telegram.

    Required stats keys (all optional — missing keys render as 'n/a'):
      - status, run_id
      - started_at, finished_at, duration
      - raw_posts, existing_posts, new_posts
      - qualified_count, watch_count, agent_broker_count, eligible_count
      - inventory_matches, sent_cards
      - provider_cost_usd, monthly_usage_usd

    Never exposes token, secret values, or exception traces.
    """
    def _v(key, default="n/a"):
        val = stats.get(key)
        if val is None:
            return default
        return val

    status = _v("status")
    run_id = _v("run_id", "")
    started = format_timestamp_wib(stats.get("started_at"))
    finished = format_timestamp_wib(stats.get("finished_at"))
    duration = _v("duration", "")

    raw = str(_v("raw_posts"))
    existing = str(_v("existing_posts"))
    new = str(_v("new_posts"))
    qualified = str(_v("qualified_count"))
    watch = str(_v("watch_count"))
    agent_broker = str(_v("agent_broker_count"))
    eligible = str(_v("eligible_count"))
    inventory = str(_v("inventory_match_count"))
    sent = str(_v("sent_cards"))

    cost = _v("provider_cost_usd", "")
    monthly = _v("monthly_usage_usd", "")

    lines = [
        "📊 *RDSA MANUAL SCAN COMPLETE*",
        "",
        f"*Status:* {status}",
    ]
    if run_id:
        lines.append(f"*Run ID:* `{run_id}`")

    lines.append("")
    if started != "unavailable" and finished != "unavailable":
        lines.append(f"*Started:* {started}")
        lines.append(f"*Finished:* {finished}")
        if duration:
            lines.append(f"*Duration:* {duration}")

    lines.append("")
    lines.append(f"*Posts scanned:* {raw}")
    lines.append(f"*Existing:* {existing}")
    lines.append(f"*New:* {new}")
    lines.append(f"*Qualified:* {qualified}")
    if watch != "n/a":
        lines.append(f"*Watch:* {watch}")
    if agent_broker != "n/a":
        lines.append(f"*Agent/Broker:* {agent_broker}")
    lines.append(f"*Eligible:* {eligible}")
    if inventory != "n/a":
        lines.append(f"*Inventory matches:* {inventory}")
    lines.append(f"*Lead cards sent:* {sent}")

    if cost and cost != "n/a":
        lines.append("")
        lines.append(f"*Provider cost:* ${cost} USD")
    if monthly and monthly != "n/a":
        lines.append(f"*Monthly usage:* ${monthly} USD")

    return "\n".join(lines)


class TelegramNotifier:
    def __init__(self, token, chat_id, session=None):
        self.token = token
        self.chat_id = chat_id
        self.session = session or requests

    def send(self, text, chat_id=None):
        # The constructor fallback keeps the legacy offline HTTP seam usable;
        # operator commands always pass config.TELEGRAM_ALLOWED_CHAT_ID.
        allowed = config.TELEGRAM_ALLOWED_CHAT_ID or self.chat_id
        target = allowed if chat_id is None else chat_id
        if config.TELEGRAM_ALLOWED_CHAT_ID and str(self.chat_id) != str(config.TELEGRAM_ALLOWED_CHAT_ID):
            raise ValueError("Telegram chat_id is not allowed")
        if chat_id is not None and str(chat_id) != str(allowed):
            raise ValueError("Telegram chat_id is not allowed")
        if not self.token or not allowed:
            raise RuntimeError("Telegram credentials and allowed chat are required")
        try:
            response = self.session.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": allowed, "text": text},
                timeout=30,
            )
            response.raise_for_status()
            message_id = response.json().get("result", {}).get("message_id")
            return message_id if message_id is not None else response.json()
        except Exception as exc:
            raise RuntimeError(redact_token(f"Telegram delivery failed: {exc}")) from None


# ---------------------------------------------------------------------------
# Telegram credentials readiness check (v0.9)
# ---------------------------------------------------------------------------
def telegram_credentials_valid() -> bool:
    """Return True when Telegram bot token and allowed chat ID are both present."""
    return bool(config.TELEGRAM_BOT_TOKEN) and bool(config.TELEGRAM_ALLOWED_CHAT_ID)


def send_lead_cards(notifier, eligible_leads, c, matching_enabled=True, posts_scanned=None, new_leads=None,
                    new_post_ids=None, allow_summary=False):
    """Fail-closed Telegram delivery.

    Atomically claims each post_id via the `delivery_claims` unique constraint
    BEFORE calling Telegram. A lead is only sent when the claim succeeds. If the
    post_id was already claimed/delivered (historical alert, prior claim, or a
    concurrent caller), the claim fails and Telegram is never called.

    Current-run newness: when `new_post_ids` is provided, only leads whose post_id
    was inserted in the current run are eligible. Leads whose `last_seen` was merely
    refreshed (already-existing) are never delivered.

    When zero new eligible leads exist, no lead card is sent. A single concise run
    summary is sent only when `allow_summary=True` (explicit operator request).
    """
    if not config.TELEGRAM_SEND_ENABLED:
        print("Telegram sending disabled (set RDSA_TELEGRAM_SEND_ENABLED=true and pass --confirm-send).")
        return 0
    from .db import claim_delivery, complete_delivery, fail_delivery
    new_set = set(new_post_ids) if new_post_ids is not None else None
    candidates = [x for x in eligible_leads if preview_eligible(x)]
    if new_set is not None:
        candidates = [x for x in candidates if _get(x, "post_id") in new_set]
    leads = sorted(candidates, key=lambda x: _get(x, "lead_score", 0), reverse=True)[:MAX_CARDS_PER_RUN]
    sent = 0
    if not leads:
        if allow_summary:
            n = posts_scanned if posts_scanned is not None else 0
            m = new_leads if new_leads is not None else 0
            try:
                notifier.send(
                    f"RDSA pilot run complete: {n} posts scanned, {m} new leads, "
                    f"0 eligible for alert. No action needed."
                )
            except Exception as exc:
                print(f"{redact_token(exc)}")
            return 1
        return 0
    for lead in leads:
        post_id = _get(lead, "post_id")
        if not claim_delivery(c, post_id):
            # Already claimed/delivered (historical alert, prior claim, or concurrent caller).
            # Fail closed: do NOT call Telegram.
            continue
        try:
            message_id = notifier.send(format_preview_card(lead, matching_enabled=matching_enabled))
            complete_delivery(c, post_id, message_id)
            sent += 1
        except Exception as exc:
            fail_delivery(c, post_id, redact_token(exc))
            print(f"{redact_token(exc)}")
    return sent
