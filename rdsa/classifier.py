from .scoring_config import (
    BROKER_SIGNALS, RENTAL_CONTEXT_SIGNALS, SPAM_SIGNALS, THIRD_PARTY_DEMAND_SIGNALS,
    GENUINE_SEEKER_CONTROLS, THRESHOLDS, OFFERING_SIGNALS, LISTING_STRUCTURE_SIGNALS,
)
import re as _re


def _detect_third_party_cue(text: str):
    for cue in THIRD_PARTY_DEMAND_SIGNALS:
        if cue in text:
            return cue
    return None


def _detect_offering_cue(text: str):
    for cue in OFFERING_SIGNALS:
        if cue in text:
            return cue
    return None


def _detect_broker_cue(text: str):
    for cue in BROKER_SIGNALS:
        if cue in text:
            return cue
    return None


# Unambiguous supply-side cues: an author ADVERTISING a unit (owner or agent).
STRONG_OFFERING = (
    "jual", "sewakan", "disewakan", "dijual", "buka opsi",
    "saya ada unit", "kami ada unit", "punya unit", "ada unit", "unit available",
    "available for rent", "ready unit", "tersedia unit", "listing available", "open listing",
    "unit kami", "unit owner", "pemilik langsung", "direct owner", "unit disewakan",
    "sewa unit", "jual unit", "unit dijual", "menerima titip", "agent listing", "broker listing",
    "cari penyewa", "cari tenant", "butuh penyewa",
    "dm untuk detail", "silakan hubungi", "wa untuk info", "boleh dm", "boleh hubungi",
    "harga sewa",
)
# Bare offering verbs: strong EXCEPT when the post is a question/discussion with no
# unit/price/contact cue (e.g. "ada yang tahu apartemen yang disewakan?").
BARE_VERBS = ("jual", "sewakan", "disewakan", "dijual")
# "harga sewa" is supply-side only when an explicit amount follows it.
_PRICE_AMOUNT = _re.compile(r"(?:\d[\d.,]*|\b\d|\bjt\b|\bm\b|\bjuta\b|\brb\b|\bk\b)")


def _has_price_amount(text: str):
    i = text.find("harga sewa")
    if i == -1:
        return False
    return bool(_PRICE_AMOUNT.search(text[i + len("harga sewa"):]))


def _unit_price_contact(text: str):
    # True when a non-bare-verb strong cue is present (unit / price-with-amount / contact / agent).
    for s in STRONG_OFFERING:
        if s in BARE_VERBS:
            continue
        if s == "harga sewa":
            if _has_price_amount(text):
                return True
            continue
        if s in text:
            return True
    return False


DISCUSSION_MARKERS = (
    "ada yang tahu", "ada yang tau", "ada info", "rekomendasi", "rekomendasinya", "suggest",
    "sarankan", "dimana ya", "kira-kira", "info apartemen", "info rumah", "share info",
    "siapa tau", "apakah", "mohon info", "ada yang punya rekomendasi", "diskusi", "soal",
    "tentang", "bahas", "ngobrol", "tanya", "pertanyaan",
)


def _seeker_class(lead):
    if lead.rental_intent == "seeking":
        return (
            "hot_lead" if lead.lead_score >= THRESHOLDS["hot"]
            else "qualified_lead" if lead.lead_score >= THRESHOLDS["qualified"]
            else "watch" if lead.lead_score >= THRESHOLDS["watch"]
            else "irrelevant"
        )
    return "irrelevant"


def classify(lead):
    t = lead.raw_text.lower()
    if any(signal in t for signal in SPAM_SIGNALS):
        lead.lead_class = "spam"
        lead.classifier_reason = "spam_signal"
        return lead

    offering_cue = _detect_offering_cue(t) or _detect_broker_cue(t)
    strong = any(s in t for s in STRONG_OFFERING) or any(s in t for s in BROKER_SIGNALS) or _unit_price_contact(t)
    structure_score = sum(1 for s in LISTING_STRUCTURE_SIGNALS if s in t)
    genuine = any(ctrl in t for ctrl in GENUINE_SEEKER_CONTROLS)
    discussion = any(d in t for d in DISCUSSION_MARKERS) or t.rstrip().endswith("?")

    # Supply-side when a strong cue is present, or a soft cue backed by listing structure.
    is_offering = strong or (offering_cue and structure_score >= 3)
    # A question/discussion that mentions only a bare verb (no unit/price/contact) is NOT a listing.
    bare_only = (any(v in t for v in BARE_VERBS) and not _unit_price_contact(t)
                 and not any(s in t for s in STRONG_OFFERING if s not in BARE_VERBS))
    if is_offering and discussion and bare_only:
        lead.lead_class = _seeker_class(lead)
        lead.classifier_reason = f"discussion_not_offering: {offering_cue or 'listing_structure'}"
        return lead
    if is_offering and not genuine:
        lead.lead_class = "agent_broker"
        lead.classifier_reason = f"offering_supply: {offering_cue or 'listing_structure'}"
        return lead
    if is_offering and genuine:
        # Explicit current request is seeking but offering language is present.
        lead.lead_class = _seeker_class(lead)
        lead.classifier_reason = f"ambiguous_offering_seeker: {offering_cue or 'listing_structure'}"
        return lead

    # Third-party-demand: author sourcing/placing on behalf of a client (broker/agent).
    cue = _detect_third_party_cue(t)
    if cue and not genuine:
        lead.lead_class = "agent_broker"
        lead.classifier_reason = f"third_party_demand: {cue}"
        return lead

    if lead.rental_intent == "seeking":
        lead.lead_class = _seeker_class(lead)
        lead.classifier_reason = "genuine_seeker" if lead.lead_class in ("hot_lead", "qualified_lead") else "seeking_low_score"
        return lead

    has_context = any(signal in t for signal in RENTAL_CONTEXT_SIGNALS) and bool(lead.desired_location or lead.property_type != "unknown")
    if lead.rental_intent == "unclear" and has_context and lead.lead_score >= THRESHOLDS["watch"]:
        lead.lead_class = "watch"
        lead.classifier_reason = "unclear_with_context"
        return lead

    lead.lead_class = "irrelevant"
    lead.classifier_reason = "no_rental_signal"
    return lead
