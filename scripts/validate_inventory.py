#!/usr/bin/env python3
"""Validate + adapt a real (sanitized) inventory CSV for the RDSA dry-run.

Canonical operator schema (required columns):
    property_id, area, building, property_type, bedrooms, monthly_price,
    furnished, available_from, features, status, listing_url

This script:
  1. Confirms all required columns are present.
  2. Rejects the file if any forbidden PII column is present.
  3. Validates row-level types/values.
  4. Emits a matcher-compatible CSV (the frozen matcher's schema) so the
     v0.1 pipeline runs unchanged.

It does NOT modify the frozen MVP. It reads the operator's file and writes an
adapted copy. Usage:

    python scripts/validate_inventory.py data/inventory_real.csv data/inventory.csv

Exit code 0 = valid + adapted; non-zero = validation failed (nothing written).
"""
import csv
import sys

REQUIRED = ["property_id", "area", "building", "property_type", "bedrooms",
            "monthly_price", "furnished", "available_from", "features",
            "status", "listing_url"]

# Any of these column names (case-insensitive, substring) => hard reject.
FORBIDDEN_PII = ["phone", "whatsapp", "wa_number", "owner_name", "owner",
                 "ktp", "nik", "id_card", "passport", "tenant", "email",
                 "bank", "account", "npwp", "salary", "income", "financial"]

VALID_TYPES = {"apartment", "house", "kontrakan", "kost"}
VALID_STATUS = {"available", "reserved", "unavailable", "rented"}


def fail(msg):
    print(f"❌ VALIDATION FAILED: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        fail("usage: validate_inventory.py <input_real.csv> <output_adapted.csv>")
    src, dst = sys.argv[1], sys.argv[2]

    try:
        with open(src, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        fail(f"input file not found: {src}")

    if not rows:
        fail("input file has no data rows")

    cols = list(rows[0].keys())
    lower = {c.lower().strip() for c in cols}

    # 1. Forbidden PII columns
    hits = [c for c in cols if any(bad in c.lower() for bad in FORBIDDEN_PII)]
    if hits:
        fail(f"forbidden PII columns present (remove them): {hits}")

    # 2. Required columns
    missing = [c for c in REQUIRED if c not in lower]
    if missing:
        fail(f"missing required columns: {missing}")

    # 3. Row validation
    seen_ids = set()
    adapted = []
    warnings = []
    for n, r in enumerate(rows, start=2):  # header is line 1
        r = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        pid = r["property_id"]
        if not pid:
            fail(f"line {n}: empty property_id")
        if pid in seen_ids:
            fail(f"line {n}: duplicate property_id {pid!r}")
        seen_ids.add(pid)
        try:
            bedrooms = int(r["bedrooms"])
            price = int(r["monthly_price"])
        except (ValueError, KeyError):
            fail(f"line {n} ({pid}): bedrooms and monthly_price must be integers")
        furn = r["furnished"].lower()
        if furn in ("1", "true", "yes", "furnished"):
            furnished = 1
        elif furn in ("0", "false", "no", "unfurnished", ""):
            furnished = 0
        else:
            fail(f"line {n} ({pid}): furnished must be 0/1/true/false, got {r['furnished']!r}")
        ptype = r["property_type"].lower()
        if ptype not in VALID_TYPES:
            warnings.append(f"line {n} ({pid}): property_type {ptype!r} not in {VALID_TYPES} (will not match)")
        status = r["status"].lower()
        if status and status not in VALID_STATUS:
            warnings.append(f"line {n} ({pid}): status {status!r} unrecognized")

        # Map canonical -> frozen matcher schema.
        # location = area (matcher matches on this); building+features -> title/notes context.
        title = r["building"] or pid
        if r["features"]:
            title = f"{title} — {r['features']}"
        adapted.append({
            "inventory_id": pid,
            "title": title,
            "location": r["area"],
            "property_type": ptype,
            "bedrooms": bedrooms,
            "price": price,
            "currency": "IDR",
            "period": "month",
            "furnished": furnished,
            "available_from": r["available_from"],
            "notes": f"{r['features']} | status={r['status']} | {r['listing_url']}",
        })

    # Only 'available' (or blank) listings are offered to leads.
    offerable = [a for a, r in zip(adapted, rows)
                 if r.get("status", "").strip().lower() in ("", "available")]

    fieldnames = ["inventory_id", "title", "location", "property_type", "bedrooms",
                  "price", "currency", "period", "furnished", "available_from", "notes"]
    with open(dst, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(offerable)

    print(f"✅ VALID: {len(rows)} rows read, {len(offerable)} available listings written to {dst}")
    print(f"   unique property_ids: {len(seen_ids)}")
    if len(offerable) < len(adapted):
        print(f"   note: {len(adapted) - len(offerable)} non-available listings excluded from matching")
    for w_ in warnings:
        print(f"   ⚠️  {w_}")


if __name__ == "__main__":
    main()
