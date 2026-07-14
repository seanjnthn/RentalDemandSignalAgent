from types import SimpleNamespace

from rdsa import config
from rdsa.cli import process_raw
from rdsa.db import connect, normalize_matched_inventory, upsert_lead
from rdsa.extractor import extract
from rdsa.matcher import match
from rdsa.notifier import format_preview_card, send_lead_cards


def lead(**changes):
    values = dict(lead_class="qualified_lead", desired_location="BSD", property_type="apartment",
                  bedrooms=1, budget_min=2_000_000, budget_max=4_000_000,
                  budget_period="month", budget_confidence="high")
    values.update(changes)
    return SimpleNamespace(**values)


def unit(area="Gading Serpong", ptype="apartment", bedrooms=1, price=3_000_000):
    return {"inventory_id": "APT-1", "title": "Unit", "location": area,
            "property_type": ptype, "bedrooms": bedrooms, "price": price,
            "period": "month"}


def test_canonical_areas_keep_bsd_distinct_and_nearby_is_explicit():
    assert config.canonical_area("BSD City") == "BSD"
    assert config.canonical_area("gading serpong") == "Gading Serpong"
    assert config.canonical_area("BSD") != config.canonical_area("GS")
    assert match(lead(), [unit()])[0]["match_type"] == "nearby_alternative"


def test_unknown_location_and_budget_period_are_not_exact():
    unknown = match(lead(desired_location=None), [unit()])[0]
    assert unknown["match_type"] == "tentative_match"
    assert "Location must be confirmed before recommending a unit." in unknown["warnings"]
    period = match(lead(budget_period="unknown"), [unit()])[0]
    assert period["match_type"] != "exact_match"


def test_exact_conflict_and_exact_match():
    assert match(lead(), [unit(area="BSD")])[0]["match_type"] == "exact_match"
    assert match(lead(), [unit(area="Alam Sutera")])[0]["match_type"] == "no_match"


def test_structured_persistence_and_legacy_null_normalization(tmp_path):
    c = connect(str(tmp_path / "db.sqlite"))
    l = extract({"id": "p", "text": "cari apartemen BSD 1BR 3jt/bulan"})
    l.lead_class = "qualified_lead"
    l.matched_inventory = match(lead(), [unit(area="BSD")])
    assert upsert_lead(c, l) == 1
    stored = c.execute("select matched_inventory from leads where post_id='p'").fetchone()[0]
    assert '"property_id": "APT-1"' in stored and "null" not in stored
    assert normalize_matched_inventory("[null]") == []
    assert normalize_matched_inventory("[None]") == []


def test_target_metrics_use_extracted_canonical_area():
    args = SimpleNamespace(pilot=False, dry_run=True)
    result = process_raw([{"id": "a", "text": "cari apartemen BSD 1BR 3jt/bulan"},
                          {"id": "b", "text": "cari rumah Tangerang Selatan 2BR 3jt/bulan"}],
                         "synthetic", args, None, inventory_mode="none")
    assert result["target_location"] == 2 == result["extracted_target_area_leads"]


def test_card_contains_tier_and_nearby_confirmation():
    l = lead(matched_inventory=[match(lead(), [unit()])[0]], score_breakdown=[])
    card = format_preview_card(l)
    assert "nearby_alternative" in card
    assert "Nearby alternative" in card or "confirm area flexibility" in card


def test_alert_rows_unchanged_by_lead_persistence(tmp_path):
    c = connect(str(tmp_path / "db.sqlite"))
    c.execute("insert into alerts(post_id,sent_at,message_id) values('old','now','17')")
    c.commit()
    before = [tuple(row) for row in c.execute("select post_id,message_id from alerts")]
    l = extract({"id": "new", "text": "cari apartemen BSD 1BR 3jt/bulan"})
    l.lead_class = "qualified_lead"
    l.matched_inventory = match(lead(), [unit(area="BSD")])
    upsert_lead(c, l)
    assert [tuple(row) for row in c.execute("select post_id,message_id from alerts")] == before


def test_single_send_path_renders_card_once(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(config, "TELEGRAM_SEND_ENABLED", True)
    class Fake:
        def send(self, text):
            print(text)
            return 99
    c = connect(str(tmp_path / "db.sqlite"))
    l = lead(post_id="one", lead_score=90, matched_inventory=[])
    upsert = SimpleNamespace(to_dict=lambda: {"post_id": "one", "source_url": "", "author_username": "u",
        "post_timestamp": "", "fetched_at": "", "raw_text": "", "rental_intent": "seeking",
        "desired_location": "BSD", "location_confidence": 1, "property_type": "apartment", "bedrooms": 1,
        "budget_min": 3_000_000, "budget_max": 3_000_000, "budget_currency": "IDR", "budget_period": "month",
        "budget_confidence": "high", "budget_note": "", "budget_raw": "", "move_in_date": None,
        "rental_duration": None, "special_requirements": [], "lead_class": "qualified_lead", "lead_score": 90,
        "score_breakdown": [], "score_version": "v1", "matched_inventory": [], "status": "new", "dedup_hash": "x"})
    upsert_lead(c, upsert)
    send_lead_cards(Fake(), [l], c)
    assert capsys.readouterr().out.count("RENTAL LEAD") == 1
