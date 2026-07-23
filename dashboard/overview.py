"""Pure presentation contracts for the v0.8 Signal Desk Overview."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import html
import math
import re
from typing import Any

from dashboard.charts import valid_count, valid_number
from dashboard.formatters import budget, label, match_tier_label, sanitized_excerpt
from rdsa.dashboard_repository import (
    get_inventory,
    get_leads,
    get_overview,
    get_scheduler_status,
)


PRIMARY_KPI_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "review_backlog",
        "label": "Review backlog",
        "tone": "amber",
        "definition": "Stored leads in the new review state.",
    },
    {
        "key": "high_signal",
        "label": "High-signal leads",
        "tone": "blue",
        "definition": "Stored leads classified as high signal.",
    },
    {
        "key": "qualified",
        "label": "Qualified leads",
        "tone": "teal",
        "definition": "Stored leads classified as qualified.",
    },
    {
        "key": "target_area",
        "label": "Target-area leads",
        "tone": "teal",
        "definition": "Stored leads with a recorded canonical target area.",
    },
    {
        "key": "active_real_matches",
        "label": "Active real matches",
        "tone": "teal",
        "definition": "Exact, nearby, or tentative matches to validated real inventory.",
    },
    {
        "key": "delivered",
        "label": "Delivered leads",
        "tone": "legacy",
        "definition": "Recorded immutable Telegram delivery rows.",
    },
)

_ACTIVE_MATCH_TYPES = (
    "exact_match",
    "nearby_alternative",
    "tentative_match",
)
_ACTIONABLE_CLASSES = {"hot_lead", "qualified_lead", "watch"}


def _sum_counts(*values: Any) -> int | None:
    counts = [valid_count(value) for value in values]
    return sum(counts) if all(value is not None for value in counts) else None


def inventory_has_active_rows(inventory: Mapping[str, Any]) -> bool:
    """Confirm that the existing inventory contract has validated real rows."""

    report = inventory.get("report")
    rows = inventory.get("rows")
    return bool(
        isinstance(report, Mapping)
        and report.get("ok") is True
        and isinstance(rows, list)
        and rows
    )


def build_primary_kpis(
    overview: Mapping[str, Any],
    *,
    active_inventory_available: bool = True,
) -> list[dict[str, Any]]:
    """Build the exact six cards without coercing missing or malformed counts."""

    total = valid_count(overview.get("total"))
    unknown = valid_count(overview.get("unknown_location"))
    target_area = (
        total - unknown
        if total is not None and unknown is not None and unknown <= total
        else None
    )
    values = {
        "review_backlog": valid_count(overview.get("new")),
        "high_signal": valid_count(overview.get("hot")),
        "qualified": valid_count(overview.get("qualified")),
        "target_area": target_area,
        "active_real_matches": (
            _sum_counts(
                overview.get("exact_match"),
                overview.get("nearby_alternative"),
                overview.get("tentative_match"),
            )
            if active_inventory_available
            else None
        ),
        "delivered": valid_count(overview.get("telegram_delivered")),
    }
    return [
        {**definition, "value": values[definition["key"]]}
        for definition in PRIMARY_KPI_DEFINITIONS
    ]


def independent_volume_values(
    overview: Mapping[str, Any],
    *,
    active_inventory_available: bool = True,
) -> dict[str, int]:
    """Return independent recorded volumes; these are not conversion stages."""

    candidates = (
        ("Stored leads", valid_count(overview.get("total"))),
        ("High signal", valid_count(overview.get("hot"))),
        ("Qualified", valid_count(overview.get("qualified"))),
        (
            "Active matches",
            (
                _sum_counts(
                    overview.get("exact_match"),
                    overview.get("nearby_alternative"),
                    overview.get("tentative_match"),
                )
                if active_inventory_available
                else None
            ),
        ),
        ("Delivered", valid_count(overview.get("telegram_delivered"))),
    )
    return {name: value for name, value in candidates if value is not None}


def classification_groups(leads: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Group stored classes transparently without re-running classification."""

    classes = Counter(lead.get("lead_class") for lead in leads)
    known_total = sum(classes.values())
    genuine = classes["hot_lead"] + classes["qualified_lead"]
    offering = classes["agent_broker"]
    irrelevant = classes["irrelevant"] + classes["spam"]
    review = classes["watch"] + max(
        0,
        known_total - genuine - offering - irrelevant - classes["watch"],
    )
    return {
        "Genuine seeker": genuine,
        "Agent / offering": offering,
        "Irrelevant": irrelevant,
        "Review required": review,
    }


def match_quality_summary(
    leads: Sequence[Mapping[str, Any]],
    *,
    active_inventory_available: bool = True,
) -> dict[str, Any]:
    """Count only active real match rows and keep legacy as historical metadata."""

    counts = {"Exact": 0, "Nearby": 0, "Tentative": 0, "No match": 0}
    labels = {
        "exact_match": "Exact",
        "nearby_alternative": "Nearby",
        "tentative_match": "Tentative",
    }
    legacy_count = 0
    for lead in leads:
        active = []
        for match in lead.get("matches", []) or []:
            if not isinstance(match, Mapping):
                continue
            if match.get("is_legacy"):
                legacy_count += 1
                continue
            match_type = match.get("match_type")
            if match_type in _ACTIVE_MATCH_TYPES:
                active.append(match_type)
        if active_inventory_available and active:
            for match_type in active:
                counts[labels[match_type]] += 1
        elif active_inventory_available:
            counts["No match"] += 1
    return {
        "active": counts if active_inventory_available else {},
        "legacy_count": legacy_count,
        "available": active_inventory_available,
    }


def overview_excerpt(value: Any, max_length: int = 180) -> str:
    """Apply stricter presentation redaction before rendering source excerpts."""

    text = str(value or "")
    phone = r"(?<!\d)(?:\+?62|0)[\s().-]*(?:\d[\s().-]*){8,13}(?!\d)"
    text = re.sub(phone, "[redacted]", text)
    text = re.sub(r"(?<!\w)@[A-Za-z0-9_]{3,}", "[redacted]", text)
    return sanitized_excerpt(text, max_length=max_length)


def _review_reason(lead: Mapping[str, Any], active_types: Sequence[str]) -> str:
    area = str(lead.get("desired_location") or "").strip().lower()
    if area in {"", "unknown"}:
        return "Target area not recorded"
    if str(lead.get("budget_confidence") or "unknown").lower() in {"low", "unknown"}:
        return "Budget needs confirmation"
    if "tentative_match" in active_types:
        return "Tentative match needs review"
    if "nearby_alternative" in active_types:
        return "Nearby alternative needs review"
    if not active_types:
        return "No active real match"
    return "Awaiting first review"


def priority_queue(
    leads: Sequence[Mapping[str, Any]],
    limit: int = 5,
    *,
    active_inventory_available: bool = True,
) -> list[dict[str, Any]]:
    """Preserve get_leads score/recency order and expose only display-safe fields."""

    rows: list[dict[str, Any]] = []
    for lead in leads:
        if (
            lead.get("status") != "new"
            or lead.get("lead_class") not in _ACTIONABLE_CLASSES
        ):
            continue
        active_types = [
            str(match.get("match_type"))
            for match in lead.get("matches", []) or []
            if isinstance(match, Mapping)
            and not match.get("is_legacy")
            and match.get("match_type") in _ACTIVE_MATCH_TYPES
        ]
        best_tier = (
            next(
                (tier for tier in _ACTIVE_MATCH_TYPES if tier in active_types),
                "no_match",
            )
            if active_inventory_available
            else None
        )
        stored_reason = str(lead.get("review_reason") or "").strip()
        review_reason = (
            overview_excerpt(stored_reason, max_length=100)
            if stored_reason
            else _review_reason(lead, active_types)
            if active_inventory_available
            else "Active inventory unavailable"
        )
        formatted_budget = budget(dict(lead))
        budget_confidence = str(
            lead.get("budget_confidence") or "unknown"
        ).strip().lower()
        budget_needs_confirmation = budget_confidence in {"low", "unknown"} or (
            "budget" in stored_reason.lower()
            and any(
                marker in stored_reason.lower()
                for marker in ("confirm", "uncertain", "low confidence")
            )
        )
        rows.append(
            {
                "lead_ref": str(lead.get("post_id") or "Not recorded"),
                "excerpt": overview_excerpt(lead.get("raw_text"), max_length=180),
                "classification": label(lead.get("lead_class")),
                "score": valid_count(lead.get("lead_score")),
                "target_area": str(lead.get("desired_location") or "Unknown"),
                "budget": (
                    "Budget needs confirmation"
                    if budget_needs_confirmation
                    else formatted_budget
                ),
                "budget_evidence": (
                    formatted_budget
                    if budget_needs_confirmation and formatted_budget != "Not recorded"
                    else None
                ),
                "match_tier": match_tier_label(best_tier) if best_tier else "Withheld",
                "review_reason": review_reason,
                "review_state": label(lead.get("status")),
            }
        )
        if len(rows) >= max(0, int(limit)):
            break
    return rows


def system_statuses(
    database_available: bool,
    inventory: Mapping[str, Any],
    scheduler: Mapping[str, Any],
) -> tuple[dict[str, str], ...]:
    """Map observability facts to the four approved semantic states."""

    database = {
        "label": "Database",
        "value": "Connected" if database_available else "Unavailable",
        "tone": "teal" if database_available else "red",
    }

    report = inventory.get("report")
    rows = inventory.get("rows")
    if not isinstance(report, Mapping) or not isinstance(rows, list):
        inventory_item = {
            "label": "Real inventory",
            "value": "Unavailable",
            "tone": "legacy",
        }
    elif not report.get("ok"):
        inventory_item = {
            "label": "Real inventory",
            "value": "Validation failed",
            "tone": "red",
        }
    elif not rows:
        inventory_item = {
            "label": "Real inventory",
            "value": "No active rows",
            "tone": "amber",
        }
    else:
        inventory_item = {
            "label": "Real inventory",
            "value": f"{len(rows)} active",
            "tone": "teal",
        }

    interruptions = scheduler.get("interrupted_runs") or []
    unresolved = any(
        isinstance(item, Mapping) and item.get("reconciliation") == "required"
        for item in interruptions
    )
    reconciled = any(
        isinstance(item, Mapping) and item.get("reconciliation") == "completed"
        for item in interruptions
    )
    lock = scheduler.get("lock") or {}
    locked = bool(lock.get("locked"))
    process_alive = lock.get("process_alive") is True
    latest_status = str(
        (scheduler.get("latest_run") or {}).get("status") or ""
    ).lower()
    if unresolved:
        scheduler_item = {
            "label": "Scheduler",
            "value": "Interruption unresolved",
            "tone": "red",
        }
    elif locked and not process_alive:
        scheduler_item = {
            "label": "Scheduler",
            "value": "Stale lock",
            "tone": "red",
        }
    elif latest_status == "blocked_cost_limit":
        scheduler_item = {
            "label": "Scheduler",
            "value": "Cost limit blocked run",
            "tone": "red",
        }
    elif latest_status == "blocked_lock":
        scheduler_item = {
            "label": "Scheduler",
            "value": "Lock blocked run",
            "tone": "red",
        }
    elif latest_status in {"failed", "error"} or (
        latest_status == "interrupted" and not reconciled
    ):
        scheduler_item = {
            "label": "Scheduler",
            "value": "Latest run failed",
            "tone": "red",
        }
    elif locked and process_alive:
        scheduler_item = {
            "label": "Scheduler",
            "value": "Running",
            "tone": "teal",
        }
    elif scheduler.get("scheduler_enabled") is False:
        scheduler_item = {
            "label": "Scheduler",
            "value": "Disabled",
            "tone": "legacy",
        }
    elif scheduler.get("scheduler_enabled") is True:
        scheduler_item = {
            "label": "Scheduler",
            "value": "Enabled · read-only",
            "tone": "teal",
        }
    else:
        scheduler_item = {
            "label": "Scheduler",
            "value": "Unavailable",
            "tone": "legacy",
        }

    telegram_enabled = scheduler.get("telegram_send_enabled")
    if telegram_enabled is True:
        telegram = {
            "label": "Telegram delivery",
            "value": "Enabled",
            "tone": "teal",
        }
    elif telegram_enabled is False:
        telegram = {
            "label": "Telegram delivery",
            "value": "Disabled",
            "tone": "legacy",
        }
    else:
        telegram = {
            "label": "Telegram delivery",
            "value": "Unavailable",
            "tone": "legacy",
        }
    return database, inventory_item, scheduler_item, telegram


def _finite_measure(value: Any) -> float | None:
    number = valid_number(value)
    return number if number is not None and math.isfinite(number) else None


def operational_health(scheduler: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten scheduler observability into sanitized display fields only."""

    latest_value = scheduler.get("latest_run")
    latest = latest_value if isinstance(latest_value, Mapping) else {}
    last_ok_value = scheduler.get("last_successful_run")
    last_ok = last_ok_value if isinstance(last_ok_value, Mapping) else {}
    interruptions = scheduler.get("interrupted_runs") or []
    unresolved = any(
        isinstance(item, Mapping) and item.get("reconciliation") == "required"
        for item in interruptions
    )
    historical = any(
        isinstance(item, Mapping) and item.get("reconciliation") == "completed"
        for item in interruptions
    )
    interruption = (
        "Blocking · reconciliation required"
        if unresolved
        else "Historical · reconciled"
        if historical
        else "None recorded"
    )
    lock = scheduler.get("lock") or {}
    locked = bool(lock.get("locked"))
    process_alive = lock.get("process_alive") is True
    lock_state = (
        "Running"
        if locked and process_alive
        else "Stale · attention required"
        if locked
        else "Free"
    )
    return {
        "latest_run_status": label(latest.get("status")),
        "latest_run_at": latest.get("finished_at") or latest.get("started_at"),
        "last_successful_at": last_ok.get("finished_at") or last_ok.get("started_at"),
        "interruption": interruption,
        "lock": lock_state,
        "current_run_cost_usd": None,
        "current_run_cost_note": "Not recorded with reliable per-run provenance",
        "monthly_usage_usd": _finite_measure(scheduler.get("monthly_usage_usd")),
        "warn_usd": _finite_measure(scheduler.get("warn_usd")),
        "stop_usd": _finite_measure(scheduler.get("stop_usd")),
        "telegram": (
            "Enabled"
            if scheduler.get("telegram_send_enabled") is True
            else "Disabled"
            if scheduler.get("telegram_send_enabled") is False
            else "Unavailable"
        ),
    }


def data_state(record_count: Any, minimum: int = 3) -> str:
    count = valid_count(record_count)
    if count in (None, 0):
        return "empty"
    return "limited" if count < minimum else "ready"


def load_overview_snapshot() -> dict[str, Any]:
    """Read the four existing contracts independently for graceful degradation."""

    database_available = True
    try:
        overview = get_overview({})
        leads = get_leads({})
    except Exception:
        overview, leads, database_available = {}, [], False
    try:
        inventory = get_inventory()
    except Exception:
        inventory = {}
    try:
        scheduler = get_scheduler_status()
    except Exception:
        scheduler = {}
    return {
        "database_available": database_available,
        "overview": overview,
        "leads": leads,
        "inventory": inventory,
        "scheduler": scheduler,
    }


def _usd(value: Any) -> str:
    number = _finite_measure(value)
    return f"USD {number:,.3f}" if number is not None else "Not recorded"


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else "Not recorded"), quote=True)


def _render_priority_card(row: Mapping[str, Any]) -> None:
    import streamlit as st

    score = row.get("score")
    score_text = str(score) if score is not None else "Not recorded"
    tier = str(row.get("match_tier") or "No match")
    tier_tone = "teal" if tier == "Exact" else "amber"
    budget_evidence = row.get("budget_evidence")
    budget_html = f'<b>Budget</b> {_safe(row.get("budget"))}'
    if budget_evidence:
        budget_html += (
            '<small class="rdsa-budget-evidence">'
            f'Parsed evidence · {_safe(budget_evidence)}'
            "</small>"
        )
    body = (
        '<article class="rdsa-priority-card">'
        '<div class="rdsa-priority-head">'
        f'<span class="rdsa-badge rdsa-blue">{_safe(row.get("classification"))}</span>'
        f'<strong>Score {_safe(score_text)}</strong>'
        "</div>"
        f'<p class="rdsa-priority-excerpt">{_safe(row.get("excerpt"))}</p>'
        '<div class="rdsa-priority-facts">'
        f'<span><b>Area</b> {_safe(row.get("target_area"))}</span>'
        f"<span>{budget_html}</span>"
        f'<span class="rdsa-badge rdsa-{tier_tone}">{_safe(tier)}</span>'
        f'<span class="rdsa-badge rdsa-blue">{_safe(row.get("review_state"))}</span>'
        "</div>"
        f'<div class="rdsa-priority-reason">Review reason · {_safe(row.get("review_reason"))}</div>'
        "</article>"
    )
    st.markdown(body, unsafe_allow_html=True)


def _render_operational_health(health: Mapping[str, Any]) -> None:
    import streamlit as st

    from dashboard.formatters import format_timestamp

    facts = (
        ("Latest scheduler run", health.get("latest_run_status")),
        ("Latest run timestamp", format_timestamp(health.get("latest_run_at"))),
        ("Last successful run", format_timestamp(health.get("last_successful_at"))),
        ("Interruption", health.get("interruption")),
        ("Lock", health.get("lock")),
        ("Telegram send state", health.get("telegram")),
    )
    body = '<div class="rdsa-health-grid">' + "".join(
        '<div class="rdsa-health-fact">'
        f'<span class="rdsa-meta-key">{_safe(name)}</span>'
        f'<strong>{_safe(value)}</strong>'
        "</div>"
        for name, value in facts
    ) + "</div>"
    st.markdown(body, unsafe_allow_html=True)

    current, monthly = st.columns(2, gap="small")
    with current:
        st.markdown("**Current-run cost**")
        st.caption(_usd(health.get("current_run_cost_usd")))
        st.caption(str(health.get("current_run_cost_note") or ""))
    with monthly:
        st.markdown("**Monthly cumulative usage**")
        st.caption(_usd(health.get("monthly_usage_usd")))

    usage = _finite_measure(health.get("monthly_usage_usd"))
    warn = _finite_measure(health.get("warn_usd"))
    stop = _finite_measure(health.get("stop_usd"))
    if usage is not None and stop not in (None, 0):
        st.progress(
            min(usage / stop, 1.0),
            text=f"Monthly usage {_usd(usage)} of {_usd(stop)} stop threshold",
        )
    else:
        st.caption("Monthly cost threshold posture · Not recorded")
    st.caption(f"Warn threshold {_usd(warn)} · Stop threshold {_usd(stop)}")


def render_signal_desk() -> None:
    """Render the professional read-only Overview from existing repository facts."""

    import streamlit as st

    from dashboard.charts import (
        overview_distribution_chart,
        overview_volume_chart,
    )
    from dashboard.components import (
        branded_page_header,
        chart,
        empty_state,
        kpi_card,
        section_header,
        system_status_strip,
    )
    from dashboard.formatters import format_timestamp, format_value

    snapshot = load_overview_snapshot()
    overview = snapshot["overview"]
    leads = snapshot["leads"]
    inventory = snapshot["inventory"]
    scheduler = snapshot["scheduler"]
    active_inventory_available = inventory_has_active_rows(inventory)
    refreshed = format_timestamp(datetime.now(timezone.utc))

    branded_page_header(
        "Rental Demand Signal",
        "Demand intelligence and underwriting review workspace",
        meta=f"Last refreshed {refreshed}",
        eyebrow="Signal Desk",
        anchorless=True,
    )
    system_status_strip(
        system_statuses(
            snapshot["database_available"],
            inventory,
            scheduler,
        )
    )

    kpis = build_primary_kpis(
        overview,
        active_inventory_available=active_inventory_available,
    )
    for offset in (0, 3):
        columns = st.columns(3, gap="small")
        for column, item in zip(columns, kpis[offset : offset + 3]):
            with column:
                kpi_card(
                    item["label"],
                    item["value"],
                    "Action required" if item["key"] == "review_backlog" else None,
                    tone=item["tone"],
                    compact=item["key"] != "review_backlog",
                )

    queue_rows = priority_queue(
        leads,
        limit=5,
        active_inventory_available=active_inventory_available,
    )
    classification = classification_groups(leads)
    match_summary = match_quality_summary(
        leads,
        active_inventory_available=active_inventory_available,
    )
    health = operational_health(scheduler)

    main, supporting = st.columns([1.65, 1], gap="large")
    with main:
        section_header(
            "Priority review queue",
            "Highest-scoring actionable records in the repository's score and recency order.",
        )
        st.page_link(
            "pages/2_Lead_Inbox.py",
            label="Open Lead Inbox",
            icon=":material/inbox:",
        )
        if queue_rows:
            for row in queue_rows:
                _render_priority_card(row)
        else:
            empty_state(
                "No priority records",
                "No new high-signal, qualified, or watch records are available for review.",
            )

        section_header(
            "Independent recorded volumes",
            "These values are independent recorded volumes, not sequential conversion stages.",
        )
        chart(
            overview_volume_chart(
                independent_volume_values(
                    overview,
                    active_inventory_available=active_inventory_available,
                )
            )
        )

    with supporting:
        section_header(
            "Demand composition",
            "Stored classifications and active real-inventory match quality.",
        )
        chart(
            overview_distribution_chart(
                classification,
                "Classification distribution",
                record_count=len(leads),
            )
        )
        if active_inventory_available:
            chart(
                overview_distribution_chart(
                    match_summary["active"],
                    "Match-quality distribution",
                    record_count=len(leads),
                )
            )
        else:
            empty_state(
                "Match quality unavailable",
                "Real inventory is unavailable or failed validation; active match claims are withheld.",
            )
        section_header("Operational health")
        _render_operational_health(health)

    section_header(
        "Definitions and evidence",
        "Secondary context is disclosed on demand to keep the operational brief focused.",
    )
    with st.expander("KPI definitions"):
        for item in PRIMARY_KPI_DEFINITIONS:
            st.markdown(f"**{item['label']}** — {item['definition']}")
    with st.expander("Data-quality limitations"):
        st.markdown(
            "- Missing values remain **Not recorded**; recorded zero remains zero.\n"
            "- Fractional, negative, boolean, and non-finite counts are withheld.\n"
            "- Distributions with fewer than three records render a limited-data state.\n"
            "- Volumes are not conversion rates and no false-positive rate is inferred.\n"
            "- Active match claims use only validated real inventory."
        )
    with st.expander("Historical and legacy match counts"):
        st.markdown(
            f"Historical legacy match rows: **{format_value(match_summary['legacy_count'])}**"
        )
        st.caption(
            "Historical rows are muted and excluded from active recommendations and KPI totals."
        )
    with st.expander("Technical scheduler details"):
        st.markdown(f"**Latest run state:** {format_value(health['latest_run_status'])}")
        st.markdown(f"**Interruption posture:** {format_value(health['interruption'])}")
        st.markdown(f"**Lock state:** {format_value(health['lock'])}")
        st.caption("Read-only observability; no run, unlock, reconcile, or send control is exposed.")
    with st.expander("Raw run ledger references"):
        st.caption(
            "Sanitized run summaries are available on Pilot Analytics and Scheduler. Raw dictionaries and ledger payloads are not rendered here."
        )
        st.page_link(
            "pages/6_Pilot_Analytics.py",
            label="Open Pilot Analytics",
            icon=":material/monitoring:",
        )
        st.page_link(
            "pages/7_Scheduler.py",
            label="Open Scheduler",
            icon=":material/schedule:",
        )
