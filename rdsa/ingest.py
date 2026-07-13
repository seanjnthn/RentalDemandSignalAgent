import hashlib,re
from difflib import SequenceMatcher
def dedup_hash(text): return hashlib.sha256(re.sub(r"\W+"," ",text.lower()).strip().encode()).hexdigest()
def is_duplicate(lead,existing):
    lead.dedup_hash=dedup_hash(lead.raw_text)
    normalized=re.sub(r"\W+"," ",lead.raw_text.lower()).strip()
    return any(x.get("post_id")==lead.post_id or x.get("dedup_hash")==lead.dedup_hash or (x.get("author_username")==lead.author_username and SequenceMatcher(None,normalized,re.sub(r"\W+"," ",x.get("raw_text","").lower()).strip()).ratio()>=.9) for x in existing)
