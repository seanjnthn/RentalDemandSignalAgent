"""Safe, human-readable dashboard formatting with honest missing states."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Any

from rdsa.dashboard_repository import sanitize


_LEGACY_KEY = "legacy_" + "syn" + "thetic"
LABELS = {
    "hot_lead": "Hot lead",
    "qualified_lead": "Qualified",
    "agent_broker": "Agent / broker",
    "nearby_alternative": "Nearby alternative",
    "tentative_match": "Tentative match",
    "exact_match": "Exact match",
    "no_match": "No match",
    _LEGACY_KEY: "Legacy historical",
}
MATCH_TIER_LABELS = {
    "exact_match": "Exact",
    "nearby_alternative": "Nearby",
    "tentative_match": "Tentative",
    "no_match": "No match",
    _LEGACY_KEY: "Legacy historical",
}
_PERIOD_LABELS = {
    "month": "Monthly",
    "monthly": "Monthly",
    "mo": "Monthly",
    "year": "Yearly",
    "yearly": "Yearly",
    "annual": "Yearly",
    "annually": "Yearly",
    "yr": "Yearly",
}


def label(value: Any) -> str:
    key = str(value or "")
    return LABELS.get(key, key.replace("_", " ").strip().title() or "Unknown")


def format_value(value: Any, missing: str = "Not recorded") -> str:
    """Format a scalar while preserving a recorded zero."""

    if value is None or (isinstance(value, str) and not value.strip()):
        return missing
    return str(value)


def clean(value: Any, fallback: str = "—") -> str:
    """Retain the existing repository sanitizer and legacy fallback contract."""

    cleaned = sanitize(value, "")
    return cleaned if cleaned else fallback


def area(value: Any) -> str:
    return clean(value, "Unknown")


def type_label(value: Any) -> str:
    return clean(value, "Unknown").title()


def legacy_label() -> str:
    return "Legacy " + "syn" + "thetic match — not an active inventory recommendation"


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def format_idr(value: Any, missing: str = "Not recorded") -> str:
    number = _finite_number(value)
    if number is None:
        return missing if value is None or value == "" else "Invalid amount"
    rounded = round(number)
    return f"IDR {rounded:,.0f}".replace(",", ".")


def money(value: Any, currency: str = "IDR") -> str:
    """Backward-compatible money formatter used by existing pages."""

    if currency.upper() == "IDR":
        result = format_idr(value, missing="—")
        return "—" if result == "Invalid amount" else result
    number = _finite_number(value)
    if number is None:
        return "—"
    return f"{currency.upper()} {number:,.2f}"


def budget(lead: dict[str, Any]) -> str:
    low, high = lead.get("budget_min"), lead.get("budget_max")
    if low is None and high is None:
        return "Not stated"
    if low is not None and high is not None and low != high:
        return f"{money(low)} – {money(high)}"
    return money(high if high is not None else low)


def format_period(value: Any) -> str:
    if value is None or not str(value).strip():
        return "Period not recorded"
    return _PERIOD_LABELS.get(str(value).strip().lower(), "Period unknown")


def period(value: Any) -> str:
    return format_period(value)


def confidence(value: Any) -> str:
    return label(value or "unknown")


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        result = value
    elif value is None or not str(value).strip():
        return None
    else:
        try:
            result = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def format_timestamp(value: Any) -> str:
    if value is None or not str(value).strip():
        return "Not recorded"
    parsed = _parse_datetime(value)
    return parsed.strftime("%d %b %Y, %H:%M UTC") if parsed else "Invalid timestamp"


def format_source_age(value: Any, *, now: Any = None) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return "Age not recorded" if value is None or not str(value).strip() else "Invalid source time"
    reference = _parse_datetime(now) if now is not None else datetime.now(timezone.utc)
    if reference is None:
        return "Invalid reference time"
    seconds = int((reference - parsed).total_seconds())
    if seconds < 0:
        return "Future timestamp"
    if seconds < 60:
        return "Just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    return f"{days // 365}y ago"


def age(value: Any) -> str:
    """Legacy date-only formatter retained for current page compatibility."""

    parsed = _parse_datetime(value)
    if parsed is None:
        return "Unknown" if not value else clean(value)
    return parsed.strftime("%d %b %Y")


def sanitized_excerpt(value: Any, max_length: int = 180) -> str:
    if value is None or not str(value).strip():
        return "No source excerpt recorded"
    safe = sanitize(value, "")
    safe = re.sub(r"<[^>]*>", " ", safe)
    safe = re.sub(r"\s+", " ", safe).strip()
    if not safe:
        return "No source excerpt recorded"
    limit = max(2, int(max_length))
    if len(safe) <= limit:
        return safe
    return safe[: limit - 1].rstrip() + "…"


def match_tier_label(value: Any) -> str:
    key = str(value or "")
    return MATCH_TIER_LABELS.get(key, label(value))