import csv
from rdsa.inventory import REQUIRED_COLUMNS, load_real_inventory, validate_real_inventory

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
