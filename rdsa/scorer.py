import re
from datetime import datetime, timezone
from .scoring_config import RELATIVE_BUDGET_SIGNALS, SCORE_VERSION, SPAM_SIGNALS

def score(lead, now=None):
    t=lead.raw_text.lower(); b=[]
    def add(rule,points,reason):
        if points: b.append({"rule":rule,"points":points,"reason":reason})
    add("R1",25 if lead.rental_intent=="seeking" and re.search(r"butuh|cari|looking for|needed|need|sewa",t) else 10 if lead.rental_intent=="seeking" else 0,"explicit seeking intent")
    add("R2",20 if lead.desired_location in ("BSD","Alam Sutera","Gading Serpong","Tangerang Selatan") else 10 if lead.desired_location in ("Serpong","Tangerang") else 0,"target location")
    relative_budget = any(signal in t for signal in RELATIVE_BUDGET_SIGNALS)
    add("R3",7 if relative_budget else 15 if lead.budget_max is not None else 0,"budget stated")
    add("R4",10 if lead.property_type!="unknown" else 5 if "tempat tinggal" in t else 0,"property type")
    add("R5",8 if lead.bedrooms is not None else 0,"bedrooms specified")
    add("R6",12 if re.search(r"secepatnya|asap|bulan ini|akhir bulan",t) else 6 if re.search(r"bulan depan|next month",t) else 2 if re.search(r"tahun depan|someday|move[- ]?in\s+flexible|flexible\s+move[- ]?in",t) else 0,"move-in urgency")
    add("R7",5 if lead.rental_duration else 0,"duration stated")
    add("R8",5 if len(lead.special_requirements)>=2 else 2 if lead.special_requirements else 0,"requirements richness")
    try:
        age=(now or datetime.now(timezone.utc))-datetime.fromisoformat(lead.post_timestamp.replace("Z","+00:00")); freshness=10 if age.total_seconds()<=86400 else 6 if age.total_seconds()<=259200 else 3 if age.total_seconds()<=604800 else 0
    except (ValueError,TypeError): freshness=0
    add("R9",freshness,"post freshness")
    if lead.rental_intent=="offering": add("P3",-30,"offering post")
    if any(signal in t for signal in SPAM_SIGNALS): add("P2",-40,"spam signal")
    lead.score_breakdown=b; lead.lead_score=max(0,min(100,sum(x["points"] for x in b))); lead.score_version=SCORE_VERSION; return lead
