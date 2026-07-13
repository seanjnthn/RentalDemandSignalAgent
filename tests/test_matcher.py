from datetime import datetime, timezone

from rdsa.extractor import extract
from rdsa.matcher import load_inventory, match
from rdsa.scorer import score
from rdsa.classifier import classify


def _scored(text):
    lead = extract({"id": "x", "text": text, "timestamp": "2026-07-13T06:00:00+00:00"}, datetime(2026, 7, 13, 7, tzinfo=timezone.utc))
    return classify(score(lead, datetime(2026, 7, 13, 7, tzinfo=timezone.utc)))


def test_qualified_lead_matches_inventory_on_core_fields():
    lead = _scored("Cari apartemen 2BR di BSD, budget 8jt/bulan")
    matches = match(lead, load_inventory("data/inventory.csv"))
    assert matches and matches[0]["inventory_id"] == "INV001"
    assert {"location", "property type", "bedrooms", "budget"} <= set(matches[0]["match_reasons"])


def test_lead_with_no_viable_inventory_returns_no_matches():
    lead = _scored("Cari apartemen 3BR di BSD, budget 2jt/bulan")
    assert match(lead, load_inventory("data/inventory.csv")) == []
