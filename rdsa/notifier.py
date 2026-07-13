import requests
def format_card(lead):
    matches='\n'.join(f"- {m['inventory_id']}: {m['title']} ({m['price']:,} IDR/month)" for m in lead.matched_inventory) or '- No inventory match'; breakdown='; '.join(f"{x['rule']} {x['points']:+d} ({x['reason']})" for x in lead.score_breakdown)
    return f"RENTAL DEMAND — {lead.lead_class}\nScore: {lead.lead_score}/100\n@{lead.author_username}\nLocation: {lead.desired_location or 'unknown'} | Type: {lead.property_type} | Bedrooms: {lead.bedrooms or '-'}\nBudget: {lead.budget_min or '-'}–{lead.budget_max or '-'} IDR/{lead.budget_period}\n{breakdown}\nMatches:\n{matches}\nSource: {lead.source_url}\nStatus: {lead.status} (manual review)"
class TelegramNotifier:
    def __init__(self,token,chat_id,session=None): self.token=token;self.chat_id=chat_id;self.session=session or requests
    def send(self,text):
        if not self.token or not self.chat_id: raise RuntimeError('Telegram credentials are required')
        r=self.session.post(f'https://api.telegram.org/bot{self.token}/sendMessage',json={'chat_id':self.chat_id,'text':text},timeout=30);r.raise_for_status();return r.json()
