import csv
from rdsa.inventory import REQUIRED_COLUMNS, load_real_inventory, validate_real_inventory, validate_real_inventory_for_scan

def write_csv(path, rows, columns=REQUIRED_COLUMNS):
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=columns, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def row(pid="P1", area="BSD City", status="available", **kw):
    return {"property_id":pid,"area":area,"building":"Synthetic Building","property_type":"apartment","bedrooms":"2","monthly_price":"7000000","furnished":"true","available_from":"2026-08-01","features":"SYNTHETIC ONLY","status":status,"listing_url":"https://example.invalid/P1",**kw}

def test_aliases_and_unavailable(tmp_path):
    p=tmp_path/"inventory.csv"; write_csv(p,[row("1","BSD City"),row("2","Alsut"),row("3","GS"),row("4","Tangsel"),row("5",status="rented")])
    rows, report=load_real_inventory(p)
    assert [r["location"] for r in rows] == ["BSD","Alam Sutera","Gading Serpong","Tangerang Selatan"]
    assert report["excluded_count"] == 1

def test_duplicate_and_pii_are_rejected(tmp_path):
    p=tmp_path/"inventory.csv"; write_csv(p,[row("1"),row("1"),row("2",features="Call 081234567890")])
    rows, report=load_real_inventory(p)
    assert len(rows)==1 and report["duplicates"] and report["excluded_count"]==1

def test_missing_columns_is_reported_and_missing_file_is_empty(tmp_path):
    p=tmp_path/"bad.csv"; write_csv(p,[row()],REQUIRED_COLUMNS[:-1])
    report=validate_real_inventory(p); assert report["hard_errors"]
    assert load_real_inventory(tmp_path/"absent.csv")[0] == []

def test_invalid_fields_are_rejected_and_report_is_sanitized(tmp_path):
    p=tmp_path/"invalid.csv"
    write_csv(p, [row("ok", area="BSD City", **{"monthly_price":"7000000"}),
                  row("bad-price", monthly_price="nope"), row("bad-bed", bedrooms="21"),
                  row("bad-date", available_from="07/01/2026"), row("bad-status", status="listed")])
    rows, report=validate_real_inventory_for_scan(p)
    assert not report["ok"] and len(rows) == 1
    assert report["available_by_area"] == {"BSD": 1}
    assert report["price_range_by_type"] == {"apartment": [7000000, 7000000]}
    assert report["rejected_rows"] == 4
    assert all(set(reason) == {"row", "reason"} for reason in report["rejected_reasons"])
    assert "bad-price" not in str(report) and "nope" not in str(report)
