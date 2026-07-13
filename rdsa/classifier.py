def classify(lead):
    t=lead.raw_text.lower()
    if any(x in t for x in ("giveaway","join sekarang","modal 100rb","klik link di bio")): lead.lead_class="spam"
    elif lead.rental_intent=="offering" or any(x in t for x in ("disewakan","for rent","wa admin","many units")): lead.lead_class="agent_broker"
    elif lead.rental_intent=="seeking": lead.lead_class="hot_lead" if lead.lead_score>=75 and (lead.move_in_date is not None or lead.rental_duration is not None) else "qualified_lead" if lead.lead_score>=55 or "info kontrakan" in t else "watch" if lead.lead_score>=35 else "irrelevant"
    elif lead.rental_intent=="unclear" and "no longer" not in t and "need ac" not in t and any(x in t for x in ("apartemen","apartment","kontrakan","sewa")) and lead.lead_score>=10: lead.lead_class="watch"
    else: lead.lead_class="irrelevant"
    return lead
