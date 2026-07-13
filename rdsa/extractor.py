import re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

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
    def to_dict(self): return asdict(self)

def _amount(number, suffix=""):
    n = float(number.replace(".", "").replace(",", "."))
    if suffix.lower() in ("jt", "juta", "m"): n *= 1_000_000
    elif suffix.lower() in ("rb", "ribu", "k"): n *= 1_000
    return int(n)

def extract(post, now=None):
    text = post.get("text", ""); low = text.lower()
    seeking = bool(re.search(r"\b(butuh|cari(?!\s+info\b)|pengen cari|looking for|apartment needed|mau cari|sewa)\b", low)) or bool(re.search(r"\bneed\s+(?:an?\s+)?(?:apartment|house|home|kontrakan)\b", low)) or ("info" in low and re.search(r"\b(?:kontrakan|apartemen|apartment|rumah|kost)\b", low) and not re.search(r"\bcari\s+info\b", low))
    offering = bool(re.search(r"\b(disewakan|for rent|tersedia|unit terbatas|harga terbaik|wa admin|contact us)\b", low))
    intent = "offering" if offering else "seeking" if seeking else "unclear"
    location = next((label for label, aliases in LOCATIONS if any(a in low for a in aliases)), None)
    confidence = 1.0 if location else 0.0
    if location == "Serpong" or location == "Tangerang": confidence = .7
    ptype = "unknown"
    for kind, words in (("apartment", ("apartemen", "apartment")), ("house", ("rumah", "house")), ("kontrakan", ("kontrakan",)), ("kost", ("kost", "kos"))):
        if any(w in low for w in words): ptype = kind; break
    bedroom = None
    m = re.search(r"\b(\d+)\s*(?:br|bedroom|kamar(?: tidur)?)\b", low)
    if m: bedroom = int(m.group(1))
    period = "unknown"
    if re.search(r"(?:/|per\s*)(bln|bulan|month)|monthly", low): period = "month"
    elif re.search(r"(?:/|per\s*)tahun|year|annual", low): period = "year"
    elif re.search(r"(?:/|per\s*)quarter", low): period = "quarter"
    elif re.search(r"(?:/|per\s*)6\s*bulan|half.year", low): period = "half_year"
    amounts = []
    for m in re.finditer(r"(?:rp\s*)?(\d+(?:[.,]\d+)?)\s*(jt|juta|m|rb|ribu|k)?", low):
        raw = m.group(1); suffix = m.group(2) or ""
        following=low[m.end():m.end()+12]
        if suffix or ("budget" in low[m.start()-15:m.start()+30] and not re.match(r"\s*(?:br|bedroom|kamar|tahun|year|bulan|month)",following)) or "million" in low[m.start():m.end()+15]: amounts.append(_amount(raw, suffix if suffix else ""))
    if "million" in low and amounts and amounts[0] < 1000: amounts[0] *= 1_000_000
    # Explicit plain-million English budgets (e.g. 6 million/month).
    if not amounts:
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*million", low): amounts.append(int(float(m.group(1))*1_000_000))
    bmin = bmax = None
    if amounts:
        bmin, bmax = (min(amounts), max(amounts))
        if len(amounts) == 1: bmin = None
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
    return Lead(str(post["id"]), post.get("permalink", ""), post.get("username", ""), post.get("timestamp", ""), fetched, text, intent, location, confidence, ptype, bedroom, bmin, bmax, "IDR", period, move, dur, req)
