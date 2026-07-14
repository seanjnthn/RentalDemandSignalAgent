from rdsa.notifier import preview_eligible, format_preview_card
from rdsa.extractor import extract
from rdsa.scorer import score
from rdsa.classifier import classify

def make():
    l=classify(score(extract({"id":"1","text":"cari apartemen BSD 2 kamar 6 jt/bulan secepatnya","timestamp":"2026-07-13T00:00:00Z","username":"real_name","permalink":"https://threads.net/p/1"})))
    l.lead_class="hot_lead"; return l

def test_preview_eligibility_and_sanitization():
    l=make(); l.raw_text += " call 081234567890 or me@example.com"; card=format_preview_card(l)
    assert preview_eligible(l) and "🏠 RENTAL LEAD" in card and "Recommended action" in card
    assert "081234567890" not in card and "me@example.com" not in card and l.source_url in card
    l.lead_class="watch"; assert not preview_eligible(l)

def test_ambiguous_budget_and_empty_inventory_wording():
    l=make(); l.raw_text="cari apartemen BSD budget 900"; l.budget_min=l.budget_max=None; l.budget_confidence="low"; l.matched_inventory=[]
    card=format_preview_card(l, matching_enabled=True)
    assert "Budget: unclear — review original post" in card
    assert "Inventory matches: No suitable unit found" in card
    assert "Inventory matches: Not configured" in format_preview_card(l, matching_enabled=False)
