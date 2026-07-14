"""Validation and adaptation for operator-supplied real inventory."""
import csv
import json
import re
from datetime import date
from pathlib import Path

REQUIRED_COLUMNS = ["property_id", "area", "building", "property_type", "bedrooms",
                    "monthly_price", "furnished", "available_from", "features",
                    "status", "listing_url"]
ALIASES = {"bsd": "BSD", "bsd city": "BSD", "alam sutera": "Alam Sutera",
           "alsut": "Alam Sutera", "gading serpong": "Gading Serpong", "gs": "Gading Serpong",
           "tangerang selatan": "Tangerang Selatan", "tangsel": "Tangerang Selatan"}
PII_RE = re.compile(r"(?:\+62|0\d{8,}|\b\d{8,20}\b|\b(?:rekening|bank|ktp|nik|passport|paspor)\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", re.I)
URL_RE = re.compile(r"^https?://[^\s]+$", re.I)
VALID_STATUSES = {"available", "rented", "reserved", "unavailable", "occupied"}


def _report():
    return {"ok": True, "total_rows": 0, "accepted_rows": 0, "rejected_rows": 0,
            "rejected_reasons": [], "available_by_area": {}, "price_range_by_type": {},
            # Compatibility fields retained without identifiers or source literals.
            "missing": False, "missing_columns": [], "duplicates": [], "excluded_count": 0,
            "errors": [], "rows_read": 0, "rows_loaded": 0}


def _reject(report, row_number, reason, hard=True):
    report["rejected_rows"] += 1
    report["rejected_reasons"].append({"row": row_number, "reason": reason})
    if hard:
        report["ok"] = False


def load_real_inventory(path):
    report = _report()
    path = Path(path)
    if not path.exists():
        report["missing"] = True
        report["ok"] = False
        report["errors"].append({"row": 0, "error": "inventory file is absent"})
        return [], report
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            missing = [c for c in REQUIRED_COLUMNS if c not in fields]
            if missing:
                report["missing_columns"] = missing
                _reject(report, 1, "missing required columns: " + ", ".join(missing))
                return [], report
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        report["ok"] = False
        report["errors"].append({"row": 0, "error": f"unable to read inventory: {type(exc).__name__}"})
        return [], report

    report["total_rows"] = len(rows)
    report["rows_read"] = len(rows)
    seen = set(); out = []
    for number, row in enumerate(rows, 2):
        pid = (row.get("property_id") or "").strip()
        if pid in seen:
            report["duplicates"].append({"row": number, "reason": "duplicate property_id"})
            _reject(report, number, "duplicate property_id")
            continue
        if pid: seen.add(pid)
        errors = []
        if not pid: errors.append("property_id is required")
        try:
            price = int(row.get("monthly_price", ""))
            if price < 0: errors.append("monthly_price must be non-negative")
        except (TypeError, ValueError): price = None; errors.append("monthly_price must be numeric")
        bedrooms_raw = str(row.get("bedrooms", "")).strip()
        try: bedrooms = int(bedrooms_raw)
        except (TypeError, ValueError): bedrooms = None; errors.append("bedrooms must be an integer")
        if bedrooms is not None and (bedrooms < 0 or bedrooms > 20 or str(bedrooms) != bedrooms_raw):
            errors.append("bedrooms must be an integer from 0 to 20")
        furnished_raw = str(row.get("furnished", "")).strip().lower()
        if furnished_raw in {"1", "true", "yes"}: furnished = 1
        elif furnished_raw in {"0", "false", "no"}: furnished = 0
        else: furnished = None; errors.append("furnished must be int/bool")
        status = (row.get("status") or "").strip().lower()
        if status not in VALID_STATUSES:
            errors.append("status is unknown")
        available_from = (row.get("available_from") or "").strip()
        if available_from:
            try: date.fromisoformat(available_from)
            except ValueError: errors.append("available_from must be YYYY-MM-DD or empty")
        url = (row.get("listing_url") or "").strip()
        pii_fields = [f for f in ("features", "building", "listing_url") if PII_RE.search(row.get(f) or "")]
        if pii_fields:
            errors.append("PII-like data rejected")
            report["excluded_count"] += 1
        if not URL_RE.match(url): errors.append("listing_url must be an http(s) URL")
        if errors:
            _reject(report, number, "; ".join(errors))
            continue
        if status != "available":
            report["excluded_count"] += 1
            continue
        area = (row.get("area") or "").strip()
        location = ALIASES.get(area.lower(), area)
        ptype = (row.get("property_type") or "").strip()
        building = (row.get("building") or "").strip()
        out.append({"inventory_id": pid, "title": f"{building} — {ptype}" if ptype else building,
                    "location": location, "property_type": ptype, "bedrooms": bedrooms,
                    "price": price, "furnished": furnished, "available_from": available_from,
                    "notes": row.get("features", "")})
        report["available_by_area"][location] = report["available_by_area"].get(location, 0) + 1
        limits = report["price_range_by_type"].setdefault(ptype, [price, price])
        limits[0] = min(limits[0], price); limits[1] = max(limits[1], price)
    report["accepted_rows"] = len(out)
    report["rows_loaded"] = len(out)
    return out, report


def validate_real_inventory_for_scan(path):
    return load_real_inventory(path)


def validate_real_inventory(path):
    rows, report = validate_real_inventory_for_scan(path)
    report["hard_errors"] = not report.get("ok", False)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return report


if __name__ == "__main__":
    import sys
    raise SystemExit(0 if validate_real_inventory(sys.argv[1] if len(sys.argv) > 1 else "data/inventory_real.csv").get("ok") else 1)
