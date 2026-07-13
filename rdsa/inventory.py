"""Validation and adaptation for operator-supplied real inventory."""
import csv
import json
import re
from pathlib import Path

REQUIRED_COLUMNS = ["property_id", "area", "building", "property_type", "bedrooms",
                    "monthly_price", "furnished", "available_from", "features",
                    "status", "listing_url"]
ALIASES = {"bsd": "BSD", "bsd city": "BSD", "alam sutera": "Alam Sutera",
           "alsut": "Alam Sutera", "gading serpong": "Gading Serpong", "gs": "Gading Serpong",
           "tangerang selatan": "Tangerang Selatan", "tangsel": "Tangerang Selatan"}
PII_RE = re.compile(r"(?:\+62|0\d{8,}|\b\d{8,20}\b|\b(?:rekening|bank|ktp|nik|passport|paspor)\b)", re.I)

def load_real_inventory(path):
    report = {"path": str(path), "errors": [], "missing_columns": [], "duplicates": [], "excluded_count": 0,
              "unknown_areas": [], "rows_read": 0, "rows_loaded": 0}
    path = Path(path)
    if not path.exists():
        report["missing"] = True
        return [], report
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            missing = [c for c in REQUIRED_COLUMNS if c not in fields]
            if missing:
                report["missing_columns"] = missing
                report["errors"].append({"row": 1, "error": "missing required columns", "columns": missing})
                return [], report
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        report["errors"].append({"row": 0, "error": str(exc)})
        return [], report
    seen = set(); out = []
    for number, row in enumerate(rows, 2):
        report["rows_read"] += 1
        pid = (row.get("property_id") or "").strip()
        if pid in seen or (pid and any(x["property_id"] == pid for x in report.get("duplicates", []))):
            report["duplicates"].append({"property_id": pid, "row": number})
            continue
        if pid: seen.add(pid)
        errors = []
        if not pid: errors.append("property_id is required")
        try: bedrooms = int(row.get("bedrooms", ""))
        except (TypeError, ValueError): errors.append("bedrooms must be an integer"); bedrooms = None
        try: price = int(row.get("monthly_price", ""))
        except (TypeError, ValueError): errors.append("monthly_price must be an integer"); price = None
        furnished_raw = str(row.get("furnished", "")).strip().lower()
        if furnished_raw in {"1", "true", "yes"}: furnished = 1
        elif furnished_raw in {"0", "false", "no"}: furnished = 0
        else: errors.append("furnished must be int/bool"); furnished = None
        status = (row.get("status") or "").strip().lower()
        if status != "available":
            report["excluded_count"] += 1
            continue
        pii_fields = [f for f in ("features", "building", "listing_url") if PII_RE.search(row.get(f) or "")]
        if pii_fields:
            report["excluded_count"] += 1
            report["errors"].append({"row": number, "property_id": pid, "error": "PII-like data rejected", "fields": pii_fields})
            continue
        if errors:
            report["errors"].append({"row": number, "property_id": pid, "error": "; ".join(errors)})
            continue
        area = (row.get("area") or "").strip()
        location = ALIASES.get(area.lower(), area)
        if area and area.lower() not in ALIASES and area not in report["unknown_areas"]:
            report["unknown_areas"].append(area)
        ptype = (row.get("property_type") or "").strip()
        building = (row.get("building") or "").strip()
        out.append({"inventory_id": pid, "title": f"{building} — {ptype}" if ptype else building,
                    "location": location, "property_type": ptype, "bedrooms": bedrooms,
                    "price": price, "furnished": furnished, "available_from": row.get("available_from", ""),
                    "notes": row.get("features", "")})
    report["rows_loaded"] = len(out)
    return out, report

def validate_real_inventory(path):
    rows, report = load_real_inventory(path)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    report["hard_errors"] = bool(report["errors"] and any("missing required" in str(e) for e in report["errors"])) or bool(report["duplicates"])
    return report

if __name__ == "__main__":
    import sys
    raise SystemExit(1 if validate_real_inventory(sys.argv[1] if len(sys.argv) > 1 else "data/inventory_real.csv")["hard_errors"] else 0)
