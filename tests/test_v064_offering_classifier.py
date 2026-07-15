"""v0.6.4 offering / supply-side classifier hardening tests.

All offline: no Apify, no Telegram. Exercises the existing rdsa.classifier pipeline
with short contextual posts (tempfile-free; reuses module-level helpers).
"""
import pytest
from rdsa.extractor import extract
from rdsa.scorer import score
from rdsa.classifier import classify
from rdsa.notifier import preview_eligible


def _lead(text, pid="x"):
    l = extract({"id": pid, "text": text, "timestamp": "2026-07-15T06:00:00+00:00"})
    classify(score(l))
    return l


# ---------------- Supply-side / offering ----------------
SUPPLY = [
    "disewakan apartemen BSD",
    "saya ada unit untuk disewakan",
    "unit available 1BR",
    "direct owner",
    "harga sewa 35 juta/tahun",
    "DM untuk detail",
    "fasilitas lengkap harga 5jt/bulan ready unit hubungi wa",
    "ada unit BSD, siapa yang cari?",
]


@pytest.mark.parametrize("txt", SUPPLY)
def test_supply_side_is_agent_broker_and_ineligible(txt):
    l = _lead(txt, pid="s1")
    assert l.lead_class == "agent_broker", f"{txt!r} -> {l.lead_class}"
    assert not preview_eligible(l)
    assert l.classifier_reason.startswith("offering_supply:")


def test_offering_cue_recorded():
    l = _lead("saya ada unit untuk disewakan", pid="s2")
    assert "offering_supply" in l.classifier_reason


# ---------------- Agent third-party sourcing ----------------
AGENT = [
    "client saya cari unit",
    "mencarikan unit untuk tenant",
    "broker mencari unit",
    "menerima titip sewa",
]


@pytest.mark.parametrize("txt", AGENT)
def test_agent_third_party_is_agent_broker(txt):
    l = _lead(txt, pid="a1")
    assert l.lead_class == "agent_broker"
    assert not preview_eligible(l)


# ---------------- Genuine seekers stay eligible ----------------
SEEKERS = [
    "saya cari apartemen untuk tinggal",
    "saya dan keluarga butuh rumah sewa",
    "butuh kontrakan dekat kantor",
]


@pytest.mark.parametrize("txt", SEEKERS)
def test_genuine_seekers_not_agent_broker(txt):
    l = _lead(txt, pid="g1")
    assert l.lead_class != "agent_broker"
    # at minimum must not be classified as a supply/agent post
    assert "offering_supply" not in (l.classifier_reason or "")


def test_ambiguous_discussion_not_offering():
    # A question mentioning "disewakan" is discussion, not a listing.
    l = _lead("ada yang tahu apartemen yang disewakan?", pid="g2")
    assert l.lead_class != "agent_broker"
    assert l.classifier_reason.startswith("discussion_not_offering:")


def test_owner_asking_how_to_find_tenant_is_supply():
    # Owner seeking a tenant = supply-side, not a demand lead.
    l = _lead("punya unit apartemen di BSD, lagi cari penyewa", pid="g3")
    assert l.lead_class == "agent_broker"
    assert not preview_eligible(l)


# ---------------- Ambiguous controls ----------------
def test_rental_price_discussion_not_demand():
    l = _lead("menurut kalian, harga sewa apartemen BSD tahun ini naik banyak?", pid="am1")
    # discussion about prices -> not a hot/qualified demand lead
    assert l.lead_class != "hot_lead"


def test_news_mentioning_disewakan_not_demand():
    l = _lead("berita: banyak unit yang disewakan tapi sepi penyewa tahun ini", pid="am2")
    assert l.lead_class != "hot_lead"
    assert l.lead_class != "qualified_lead"


def test_tenant_describing_existing_rental_not_demand():
    l = _lead("akhirnya saya tinggal di apartemen yang disewakan tahun lalu, nyaman", pid="am3")
    assert l.lead_class != "hot_lead"
    assert l.lead_class != "qualified_lead"


# ---------------- Run #7 post reprocess (offline, no DB write) ----------------
def test_run7_post_becomes_ineligible():
    raw = ("Halo Threads! \n\nAku lagi buka opsi untuk jual / sewakan unit apartment di BSD "
           "(Under Market Price)\n\nAvailable:\n1 Unit SOHO (2 lantai)\n1 Unit Apartment 1 Bedroom")
    l = _lead(raw, pid="3914314253977235827")
    assert l.lead_class == "agent_broker"
    assert l.classifier_reason.startswith("offering_supply:")
    assert not preview_eligible(l)          # would generate zero cards


def test_no_regression_v063_third_party():
    # v0.6.3 controls still hold: third-party sourcing stays agent_broker.
    for txt in ["ada client cari rumah", "saya lagi ada client cari apartemen", "co-broke rumah"]:
        l = _lead(txt, pid="r1")
        assert l.lead_class == "agent_broker"
        assert l.classifier_reason.startswith("third_party_demand:")


def test_no_regression_v063_genuine_controls():
    for txt in ["saya cari apartemen untuk saya sendiri", "saya dan keluarga mencari rumah"]:
        l = _lead(txt, pid="r2")
        assert l.lead_class != "agent_broker"


def test_classification_priority_offering_over_seeking():
    # "Cari penyewa untuk apartemen saya" -> supply, not seeker.
    l = _lead("Cari penyewa untuk apartemen saya di BSD", pid="p1")
    assert l.lead_class == "agent_broker"
    assert l.classifier_reason.startswith("offering_supply:")
