import re
from datetime import datetime, timezone
import requests
from . import config

MAX_CARDS_PER_RUN = 3

def redact_token(text):
    value = str(text)
    tokens = [config.TELEGRAM_BOT_TOKEN] if config.TELEGRAM_BOT_TOKEN else []
    for token in tokens:
        value = value.replace(token, "[REDACTED_TOKEN]")
    return re.sub(r"bot\d+:[A-Za-z0-9_-]+", "[REDACTED_TOKEN]", value)

def _get(lead, name, default=None): return lead.get(name, default) if isinstance(lead, dict) else getattr(lead, name, default)
def preview_eligible(lead): return _get(lead, "lead_class") in ("hot_lead", "qualified_lead")
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
    if not matching_enabled: matches_block="Inventory matches: Not configured"
    else:
        lines="\n".join(f"{i}. {_safe(m.get('inventory_id','unknown'))} — {m.get('score',0)}" for i,m in enumerate(matches[:3],1)) or "No suitable unit found"
        matches_block="Inventory matches: No suitable unit found" if not matches else f"Inventory matches:\n{lines}"
    budget=_get(lead,"budget_max") or _get(lead,"budget_min")
    budget_confidence=_get(lead,"budget_confidence","low")
    budget=f"{budget:,} IDR" if budget_confidence in ("high","medium") and isinstance(budget,int) else "unclear — review original post"
    ptype=_get(lead,"property_type") or "unknown"; beds=_get(lead,"bedrooms"); property_text=f"{ptype} {beds} bedroom" if beds else str(ptype)
    source=_get(lead,"source_url",""); source=_safe(source, "") if re.match(r"^https?://",str(source)) else ""
    return (f"🏠 RENTAL LEAD — {_get(lead,'lead_score',0)}/100\n\nPosted: {_age(_get(lead,'post_timestamp'))}\nArea: {_safe(_get(lead,'desired_location'),'unknown')}\n"
            f"Property: {_safe(property_text)}\nBudget: {budget}\nMove-in: {_safe(_get(lead,'move_in_date'))}\n\nWhy qualified:\n- {_safe('; '.join(reasons) if reasons else 'qualified by scoring rules')}\n\n"
            f"{matches_block}\n\nRecommended action:\nReview the original Threads post and contact manually if appropriate.\n\n{source}")
def format_card(lead):
    return format_preview_card(lead)

class TelegramNotifier:
    def __init__(self, token, chat_id, session=None): self.token=token; self.chat_id=chat_id; self.session=session or requests
    def send(self, text, chat_id=None):
        # The constructor fallback keeps the legacy offline HTTP seam usable;
        # operator commands always pass config.TELEGRAM_ALLOWED_CHAT_ID.
        allowed=config.TELEGRAM_ALLOWED_CHAT_ID or self.chat_id
        target=allowed if chat_id is None else chat_id
        if config.TELEGRAM_ALLOWED_CHAT_ID and str(self.chat_id) != str(config.TELEGRAM_ALLOWED_CHAT_ID):
            raise ValueError("Telegram chat_id is not allowed")
        if chat_id is not None and str(chat_id) != str(allowed): raise ValueError("Telegram chat_id is not allowed")
        if not self.token or not allowed: raise RuntimeError("Telegram credentials and allowed chat are required")
        try:
            response=self.session.post(f"https://api.telegram.org/bot{self.token}/sendMessage", json={"chat_id":allowed,"text":text}, timeout=30)
            response.raise_for_status()
            message_id=response.json().get("result", {}).get("message_id")
            return message_id if message_id is not None else response.json()
        except Exception as exc:
            raise RuntimeError(redact_token(f"Telegram delivery failed: {exc}")) from None

def send_lead_cards(notifier, eligible_leads, c, matching_enabled=True, posts_scanned=None, new_leads=None):
    if not config.TELEGRAM_SEND_ENABLED:
        print("Telegram sending disabled (set RDSA_TELEGRAM_SEND_ENABLED=true and pass --confirm-send).")
        return 0
    leads=sorted((x for x in eligible_leads if preview_eligible(x)), key=lambda x: _get(x,"lead_score",0), reverse=True)[:MAX_CARDS_PER_RUN]
    sent=0
    if not leads:
        n=posts_scanned if posts_scanned is not None else 0; m=new_leads if new_leads is not None else 0
        try: notifier.send(f"RDSA pilot run complete: {n} posts scanned, {m} new leads, 0 eligible for alert. No action needed.")
        except Exception as exc: print(f"{redact_token(exc)}")
        return 1
    from .db import already_sent, mark_alert
    for lead in leads:
        post_id=_get(lead,"post_id")
        if already_sent(c, post_id): continue
        try:
            message_id=notifier.send(format_preview_card(lead, matching_enabled=matching_enabled))
            mark_alert(c, post_id, message_id)
            sent += 1
        except Exception as exc:
            print(f"{redact_token(exc)}")
    return sent
