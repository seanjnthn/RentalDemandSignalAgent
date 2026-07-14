import requests
import re
from datetime import datetime, timezone

def _get(lead, name, default=None):
    return lead.get(name, default) if isinstance(lead, dict) else getattr(lead, name, default)

def preview_eligible(lead):
    return _get(lead, "lead_class") in ("hot_lead", "qualified_lead")

def _age(value):
    try: seconds=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(str(value).replace("Z","+00:00"))).total_seconds())
    except (ValueError,TypeError): return "unknown"
    if seconds < 3600: return f"{max(1,int(seconds//60))}m ago"
    if seconds < 86400: return f"{int(seconds//3600)}h ago"
    return f"{int(seconds//86400)}d ago"

def _safe(value, fallback="not stated"):
    value=str(value or fallback)
    value=re.sub(r"(?:\+62|0\d{8,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", "[redacted]", value)
    return value[:120]

def format_preview_card(lead, matching_enabled=True):
    breakdown=_get(lead,"score_breakdown",[]) or []
    reasons=[_safe(x.get("reason", "")) for x in breakdown[:3] if isinstance(x,dict) and x.get("reason")]
    matches=_get(lead,"matched_inventory",[]) or []
    if not matching_enabled:
        matches_block = "Inventory matches: Not configured"
    else:
        match_lines = "\n".join(f"{i}. {_safe(m.get('inventory_id','unknown'))} — {m.get('score',0)}" for i,m in enumerate(matches[:3],1)) or "1. none"
        matches_block = f"Inventory matches:\n{match_lines}"
    budget=_get(lead,"budget_max") or _get(lead,"budget_min")
    budget=f"{budget:,} IDR" if isinstance(budget,int) else "not stated"
    ptype=_get(lead,"property_type") or "unknown"; beds=_get(lead,"bedrooms")
    property_text=f"{ptype} {beds} bedroom" if beds else str(ptype)
    source=_get(lead,"source_url","")
    source=_safe(source, "") if re.match(r"^https?://",str(source)) else ""
    return (f"🏠 RENTAL LEAD — {_get(lead,'lead_score',0)}/100\n\n"
            f"Posted: {_age(_get(lead,'post_timestamp'))}\nArea: {_safe(_get(lead,'desired_location'),'unknown')}\n"
            f"Property: {_safe(property_text)}\nBudget: {budget}\nMove-in: {_safe(_get(lead,'move_in_date'))}\n\n"
            f"Why qualified:\n- {_safe('; '.join(reasons) if reasons else 'qualified by scoring rules')}\n\n"
            f"{matches_block}\n\nRecommended action:\n"
            f"Review the original Threads post and contact manually if appropriate.\n\n{source}")
def format_card(lead):
    matches='\n'.join(f"- {m['inventory_id']}: {m['title']} ({m['price']:,} IDR/month)" for m in lead.matched_inventory) or '- No inventory match'; breakdown='; '.join(f"{x['rule']} {x['points']:+d} ({x['reason']})" for x in lead.score_breakdown)
    return f"RENTAL DEMAND — {lead.lead_class}\nScore: {lead.lead_score}/100\n@{lead.author_username}\nLocation: {lead.desired_location or 'unknown'} | Type: {lead.property_type} | Bedrooms: {lead.bedrooms or '-'}\nBudget: {lead.budget_min or '-'}–{lead.budget_max or '-'} IDR/{lead.budget_period}\n{breakdown}\nMatches:\n{matches}\nSource: {lead.source_url}\nStatus: {lead.status} (manual review)"
class TelegramNotifier:
    def __init__(self,token,chat_id,session=None): self.token=token;self.chat_id=chat_id;self.session=session or requests
    def send(self,text):
        if not self.token or not self.chat_id: raise RuntimeError('Telegram credentials are required')
        r=self.session.post(f'https://api.telegram.org/bot{self.token}/sendMessage',json={'chat_id':self.chat_id,'text':text},timeout=30);r.raise_for_status();return r.json()
