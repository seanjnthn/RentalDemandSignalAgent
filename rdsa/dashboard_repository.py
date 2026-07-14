"""Read-mostly service layer for the local operational dashboard.

This module deliberately imports only the database and real-inventory helpers. It
does not import config, notifier, providers, or network clients.
"""
from __future__ import annotations

import json
import csv
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import db
from .config import canonical_area
from .inventory import load_real_inventory, validate_real_inventory_for_scan

MATCH_TYPES = ("exact_match", "nearby_alternative", "tentative_match", "no_match")
CLASSIFICATIONS = ("hot_lead", "qualified_lead", "watch", "agent_broker", "irrelevant", "spam")
DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "rdsa.sqlite3"
DEFAULT_INVENTORY = Path(__file__).resolve().parent.parent / "data" / "inventory_real.csv"


def _conn(path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    return db.connect(str(path))


def _json(value: Any, fallback: Any) -> Any:
    if value in (None, "", "null", "[null]", "[None]"):
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        result = json.loads(value)
        return result if result is not None else fallback
    except (TypeError, ValueError):
        return fallback


def sanitize(value: Any, fallback: str = "") -> str:
    text = str(value or fallback)
    text = re.sub(r"(?:\+62|0\d{8,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", "[redacted]", text)
    return text[:4000]


def normalize_matches(value: Any, lead_area: str | None = None) -> list[dict[str, Any]]:
    """Normalize both persisted match shapes without inventing identifiers."""
    raw = _json(value, [])
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        property_id = item.get("property_id", item.get("inventory_id"))
        if property_id in (None, ""):
            continue
        legacy = "property_id" not in item and "match_type" not in item
        reasons = item.get("reasons", item.get("match_reasons", [])) or []
        if not isinstance(reasons, list):
            reasons = [str(reasons)]
        warnings = item.get("warnings", []) or []
        if not isinstance(warnings, list):
            warnings = [str(warnings)]
        match_type = item.get("match_type")
        if match_type not in MATCH_TYPES:
            inventory_area = item.get("location")
            match_type = "nearby_alternative" if legacy and lead_area and inventory_area and canonical_area(lead_area) != canonical_area(inventory_area) else "exact_match"
        result.append({
            "property_id": str(property_id), "match_type": match_type,
            "score": item.get("score", 0), "reasons": reasons, "warnings": warnings,
            "title": item.get("title"), "location": item.get("location"),
            "property_type": item.get("property_type"), "bedrooms": item.get("bedrooms"),
            "price": item.get("price"),
        })
    return result


def _decorate(row: sqlite3.Row) -> dict[str, Any]:
    lead = dict(row)
    lead["desired_location"] = canonical_area(lead.get("desired_location")) or "Unknown"
    lead["raw_text"] = sanitize(lead.get("raw_text"), "")
    lead["notes"] = sanitize(lead.get("notes"), "")
    lead["score_breakdown"] = _json(lead.get("score_breakdown"), [])
    lead["special_requirements"] = _json(lead.get("special_requirements"), lead.get("special_requirements") or "")
    lead["matches"] = normalize_matches(lead.get("matched_inventory"), lead.get("desired_location"))
    lead["match_types"] = sorted({m["match_type"] for m in lead["matches"]}) or ["no_match"]
    lead["matched_property_ids"] = [m["property_id"] for m in lead["matches"]]
    return lead


def _where(filters: dict[str, Any] | None = None) -> tuple[str, list[Any]]:
    f = filters or {}; clauses, params = [], []
    if f.get("date_from"): clauses.append("COALESCE(first_seen, fetched_at) >= ?"); params.append(str(f["date_from"]))
    if f.get("date_to"): clauses.append("COALESCE(first_seen, fetched_at) < ?"); params.append(str(f["date_to"]) + "T23:59:59.999999")
    for key, column in (("classification", "lead_class"), ("status", "status"), ("area", "desired_location"), ("property_type", "property_type")):
        value = f.get(key)
        if value and value not in ("All", "all"):
            clauses.append(f"{column} = ?"); params.append(value)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def get_leads(filters: dict[str, Any] | None = None, db_path: str | Path = DEFAULT_DB) -> list[dict[str, Any]]:
    where, params = _where(filters)
    with _conn(db_path) as c:
        rows = c.execute("SELECT l.*, EXISTS(SELECT 1 FROM alerts a WHERE a.post_id=l.post_id AND a.channel='telegram') AS telegram_sent FROM leads l" + where + " ORDER BY lead_score DESC, COALESCE(first_seen, fetched_at) DESC", params).fetchall()
        leads = [_decorate(r) for r in rows]
    match_type = (filters or {}).get("match_type")
    return [x for x in leads if not match_type or match_type in ("All", "all") or match_type in x["match_types"]]


def get_lead(post_id: str, db_path: str | Path = DEFAULT_DB) -> dict[str, Any] | None:
    with _conn(db_path) as c:
        row = c.execute("SELECT l.*, EXISTS(SELECT 1 FROM alerts a WHERE a.post_id=l.post_id AND a.channel='telegram') AS telegram_sent FROM leads l WHERE l.post_id=?", (post_id,)).fetchone()
        if not row: return None
        lead = _decorate(row)
        lead["alerts"] = [dict(a) for a in c.execute("SELECT sent_at, message_id, channel FROM alerts WHERE post_id=? ORDER BY sent_at", (post_id,)).fetchall()]
        return lead


def get_overview(filters: dict[str, Any] | None = None, db_path: str | Path = DEFAULT_DB) -> dict[str, Any]:
    leads = get_leads(filters, db_path)
    counts = Counter(x.get("lead_class") for x in leads)
    statuses = Counter(x.get("status") for x in leads)
    matches = Counter(m["match_type"] for x in leads for m in x["matches"])
    with _conn(db_path) as c:
        delivered = c.execute("SELECT COUNT(*) FROM alerts WHERE channel='telegram'").fetchone()[0]
    usage_path = Path(db_path).parent / "apify_usage.json"
    try:
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
        if isinstance(usage, dict): usage = usage.get("runs", usage.get("usage", []))
        cost = sum(float(x.get("usageTotalUsd", 0) or 0) for x in usage if isinstance(x, dict))
    except (OSError, ValueError, TypeError): cost = 0.0
    qualified = counts["hot_lead"] + counts["qualified_lead"]
    return {"total": len(leads), "new": statuses["new"], "hot": counts["hot_lead"], "qualified": counts["qualified_lead"], "watch": counts["watch"], "exact_match": matches["exact_match"], "nearby_alternative": matches["nearby_alternative"], "tentative_match": matches["tentative_match"], "no_match": matches["no_match"], "unknown_location": sum(x["desired_location"] == "Unknown" for x in leads), "telegram_delivered": delivered, "apify_cost": cost, "cost_per_qualified": cost / qualified if qualified else None}


def get_inventory(path: str | Path = DEFAULT_INVENTORY) -> dict[str, Any]:
    rows, report = validate_real_inventory_for_scan(path)
    # The validator intentionally adapts to the matcher shape. Reattach only
    # public CSV display fields, never hidden or synthetic inventory records.
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            public = {r.get("property_id"): r for r in csv.DictReader(handle)}
        for row in rows:
            original = public.get(row["inventory_id"], {})
            row["listing_url"] = original.get("listing_url", "")
            text = original.get("features", "")
            annual = re.search(r"annual[^\d]*(?:Rp\s*)?([\d.,]+)", text, re.I)
            row["annual_asking"] = annual.group(1) if annual else None
    except (OSError, UnicodeError, csv.Error):
        pass
    return {"rows": rows, "report": report}


def get_matching_groups(db_path: str | Path = DEFAULT_DB) -> dict[str, list[dict[str, Any]]]:
    groups = {key: [] for key in MATCH_TYPES}
    for lead in get_leads({}, db_path):
        for match in lead["matches"]:
            groups[match["match_type"]].append({"lead": lead, "match": match})
    return groups


def update_lead_status(post_id: str, new_status: str, notes: str | None = None, user: str = "dashboard", reviewed_at: str | None = None, db_path: str | Path = DEFAULT_DB) -> None:
    if new_status not in {"new", "reviewed", "contacted", "responded", "viewing_scheduled", "converted", "negotiating", "rejected", "duplicate", "irrelevant"}: raise ValueError("invalid status")
    now = datetime.now(timezone.utc).isoformat()
    with _conn(db_path) as c:
        c.execute("ALTER TABLE leads ADD COLUMN reviewed_at TEXT") if "reviewed_at" not in {r[1] for r in c.execute("PRAGMA table_info(leads)")} else None
        if "source" not in {r[1] for r in c.execute("PRAGMA table_info(status_history)")}: c.execute("ALTER TABLE status_history ADD COLUMN source TEXT")
        row = c.execute("SELECT status FROM leads WHERE post_id=?", (post_id,)).fetchone()
        if not row: raise ValueError("unknown post")
        c.execute("UPDATE leads SET status=?, notes=?, reviewed_at=? WHERE post_id=?", (new_status, sanitize(notes), reviewed_at or now, post_id))
        c.execute("INSERT INTO status_history(post_id,old_status,new_status,changed_at,note,source) VALUES(?,?,?,?,?,?)", (post_id, row[0], new_status, now, sanitize(notes), "dashboard"))
        c.commit()


def get_audit(post_id: str, db_path: str | Path = DEFAULT_DB) -> list[dict[str, Any]]:
    with _conn(db_path) as c:
        columns = {r[1] for r in c.execute("PRAGMA table_info(status_history)")}
        source = "source" if "source" in columns else "NULL AS source"
        return [dict(r) for r in c.execute(f"SELECT old_status,new_status,changed_at,note,{source} FROM status_history WHERE post_id=? ORDER BY changed_at DESC", (post_id,)).fetchall()]


def get_pilot_runs(log_path: str | Path | None = None, db_path: str | Path = DEFAULT_DB) -> list[dict[str, Any]]:
    path = Path(log_path or Path(__file__).resolve().parent.parent / "docs" / "PILOT_LOG.md")
    try: text = path.read_text(encoding="utf-8")
    except OSError: return []
    runs = []
    for section in re.split(r"(?m)^## Run #", text)[1:]:
        number = re.match(r"(\d+)", section)
        if not number: continue
        def metric(label: str) -> Any:
            m = re.search("(?:" + label + r")[^\d]*(\d+(?:\.\d+)?)", section, re.I); return float(m.group(1)) if m and "." in m.group(1) else int(m.group(1)) if m else None
        runs.append({"run": int(number.group(1)), "raw": metric(r"Raw posts|Raw"), "normalized": metric(r"Normalized"), "duplicates": metric(r"Duplicates|Dup"), "new": metric(r"New leads|New"), "unknown_location": metric(r"unknown-location leads|unknown location"), "apify_cost": metric(r"usageTotalUsd|Current.*\$"), "text": section[:1000]})
    return runs
