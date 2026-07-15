import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from .budget_parser import parse_budget
from .config import canonical_area

LOCATIONS = [("Tangerang Selatan", ("tangerang selatan", "tangsel")), ("Gading Serpong", ("gading serpong",)), ("Alam Sutera", ("alam sutera",)), ("BSD", ("bsd",)), ("Serpong", ("serpong",)), ("Tangerang", ("tangerang",))]

_BEDROOM_WORD = r"(?:br|bedroom|bed|kamar(?:\s*tidur)?|kt)"
_RANGE = r"(\d+)\s*[-–]\s*(\d+)"
_STUDIO = r"studio"


def parse_bedrooms(text: str):
    """Return structured bedroom requirements without inventing a single value.

    Produces: bedroom_min, bedroom_max, bedroom_options (list of acceptable counts,
    where 0 means studio), studio_acceptable, bedroom_confidence, bedroom_raw.
    The legacy single `bedrooms` field should be set to the exact value only when
    min == max (so exact inventory matching still works); otherwise None.
    """
    low = (text or "").lower()
    raw = ""
    studio = bool(re.search(rf"\b{_STUDIO}\b", low))
    options = []
    if studio:
        options.append(0)
    min_v = max_v = None
    confidence = "low"
    # explicit single: "2BR", "2 kamar", "2KT", "1 bedroom"
    single = re.findall(rf"\b(\d+)\s*{_BEDROOM_WORD}\b", low)
    # range: "1-2 kamar", "minimal 2 kamar", "maksimal 3 kamar"
    rng = re.search(rf"minimal\s+(\d+)\s*{_BEDROOM_WORD}", low)
    rng_max = re.search(rf"maksimal\s+(\d+)\s*{_BEDROOM_WORD}", low)
    rng_pair = re.search(rf"{_RANGE}\s*{_BEDROOM_WORD}", low)
    if rng_pair:
        min_v, max_v = int(rng_pair.group(1)), int(rng_pair.group(2))
        raw = rng_pair.group(0).strip()
        confidence = "high"
    elif rng:
        min_v = int(rng.group(1)); max_v = None
        raw = rng.group(0).strip(); confidence = "medium"
    elif rng_max:
        min_v = None; max_v = int(rng_max.group(1))
        raw = rng_max.group(0).strip(); confidence = "medium"
    elif single:
        nums = sorted({int(x) for x in single})
        if len(nums) == 1:
            min_v = max_v = nums[0]; confidence = "high"
        else:
            min_v, max_v = nums[0], nums[-1]; confidence = "medium"
        raw = ", ".join(str(n) for n in nums)
        options.extend(nums)
    # "studio atau 2KT" / "studio/2KT" => options include both studio and the numeric
    if studio and single:
        for n in sorted({int(x) for x in single}):
            if n not in options:
                options.append(n)
        raw = raw or "studio"
        confidence = confidence or "medium"
    elif studio and not single:
        raw = "studio"; confidence = "medium"
    options = sorted(set(options))
    # exact single only when a single value is specified and no range/options ambiguity
    exact = min_v if (min_v is not None and min_v == max_v and not (studio and len(options) > 1)) else None
    return {
        "bedroom_min": min_v,
        "bedroom_max": max_v,
        "bedroom_options": options,
        "studio_acceptable": studio,
        "bedroom_confidence": confidence,
        "bedroom_raw": raw,
        "bedrooms": exact,
    }


@dataclass
class Lead:
    post_id: str; source_url: str; author_username: str; post_timestamp: str; fetched_at: str; raw_text: str
    rental_intent: str = "unclear"; desired_location: str|None = None; location_confidence: float = 0.0
    property_type: str = "unknown"; bedrooms: int|None = None
    bedroom_min: int|None = None; bedroom_max: int|None = None; bedroom_options: list = field(default_factory=list)
    studio_acceptable: bool = False; bedroom_confidence: str = "low"; bedroom_raw: str = ""
    budget_min: int|None = None; budget_max: int|None = None
    budget_currency: str = "IDR"; budget_period: str = "unknown"; move_in_date: str|None = None
    rental_duration: str|None = None; special_requirements: list = field(default_factory=list)
    lead_class: str = "irrelevant"; lead_score: int = 0; score_breakdown: list = field(default_factory=list)
    score_version: str = "v1.0"; matched_inventory: list = field(default_factory=list); status: str = "new"; dedup_hash: str = ""
    alerted_at: str|None = None
    budget_confidence: str = "low"; budget_note: str = ""; budget_raw: str = ""
    def to_dict(self): return asdict(self)

def extract(post, now=None):
    text = post.get("text", ""); low = text.lower()
    seeking = bool(re.search(r"\b(butuh|cari(?!\s+info\b)|pengen cari|looking for|apartment needed|mau cari|sewa)\b", low)) or bool(re.search(r"\bneed\s+(?:an?\s+)?(?:apartment|house|home|kontrakan)\b", low)) or ("info" in low and re.search(r"\b(?:kontrakan|apartemen|apartment|rumah|kost)\b", low) and not re.search(r"\bcari\s+info\b", low))
    offering = bool(re.search(r"\b(disewakan|for rent|tersedia|unit terbatas|harga terbaik|wa admin|contact us)\b", low))
    intent = "offering" if offering else "seeking" if seeking else "unclear"
    detected_location = next((label for label, aliases in LOCATIONS if any(a in low for a in aliases)), None)
    location = canonical_area(detected_location) or detected_location
    confidence = 1.0 if location else 0.0
    if location == "Serpong" or location == "Tangerang": confidence = .7
    ptype = "unknown"
    for kind, words in (("apartment", ("apartemen", "apartment")), ("house", ("rumah", "house")), ("kontrakan", ("kontrakan",)), ("kost", ("kost", "kos"))):
        if any(w in low for w in words): ptype = kind; break
    bedroom = parse_bedrooms(text)
    budget = parse_budget(text)
    period = budget.period
    bmin = budget.monthly_min if period == "year" else budget.min_amount
    bmax = budget.monthly_max if period == "year" else budget.max_amount
    if budget.confidence not in ("high", "medium"): bmin = bmax = None
    dur = None
    m = re.search(r"(?:sewa|rent(?:al)?)\s*(\d+\s*(?:tahun|year|months?|bulan))", low)
    if m: dur = m.group(1)
    req = []
    for token, label in (("furnished", "furnished"), ("carport", "carport"), ("pet friendly", "pet-friendly"), ("pet-friendly", "pet-friendly"), ("near aeon", "near AEON"), ("bersih", "clean"), ("aman", "safe")):
        if token in low and label not in req: req.append(label)
    if re.search(r"secepatnya|asap|bulan ini|akhir bulan", low): move = "within 30 days"
    elif re.search(r"bulan depan|next month", low): move = "next month"
    else: move = None
    fetched = (now or datetime.now(timezone.utc)).isoformat()
    return Lead(str(post["id"]), post.get("permalink", ""), post.get("username", ""), post.get("timestamp", ""), fetched, text, intent, location, confidence, ptype, bedroom["bedrooms"],
               bedroom_min=bedroom["bedroom_min"], bedroom_max=bedroom["bedroom_max"], bedroom_options=bedroom["bedroom_options"],
               studio_acceptable=bedroom["studio_acceptable"], bedroom_confidence=bedroom["bedroom_confidence"], bedroom_raw=bedroom["bedroom_raw"],
               budget_min=bmin, budget_max=bmax, budget_currency=budget.currency, budget_period=period, move_in_date=move, rental_duration=dur, special_requirements=req,
               budget_confidence=budget.confidence, budget_note=budget.note, budget_raw=budget.raw_text)
