import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from .budget_parser import parse_budget
from .config import canonical_area

LOCATIONS = [("Tangerang Selatan", ("tangerang selatan", "tangsel")), ("Gading Serpong", ("gading serpong",)), ("Alam Sutera", ("alam sutera",)), ("BSD", ("bsd",)), ("Serpong", ("serpong",)), ("Tangerang", ("tangerang",))]

@dataclass
class Lead:
    post_id: str; source_url: str; author_username: str; post_timestamp: str; fetched_at: str; raw_text: str
    rental_intent: str = "unclear"; desired_location: str|None = None; location_confidence: float = 0.0
    property_type: str = "unknown"; bedrooms: int|None = None; budget_min: int|None = None; budget_max: int|None = None
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
    bedroom = None
    m = re.search(r"\b(\d+)\s*(?:br|bedroom|kamar(?: tidur)?)\b", low)
    if m: bedroom = int(m.group(1))
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
    return Lead(str(post["id"]), post.get("permalink", ""), post.get("username", ""), post.get("timestamp", ""), fetched, text, intent, location, confidence, ptype, bedroom, bmin, bmax, budget.currency, period, move, dur, req, budget_confidence=budget.confidence, budget_note=budget.note, budget_raw=budget.raw_text)
