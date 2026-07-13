from .scoring_config import BROKER_SIGNALS, RENTAL_CONTEXT_SIGNALS, SPAM_SIGNALS, THRESHOLDS

def classify(lead):
    t=lead.raw_text.lower()
    has_context = any(signal in t for signal in RENTAL_CONTEXT_SIGNALS) and bool(lead.desired_location or lead.property_type != "unknown")
    if any(signal in t for signal in SPAM_SIGNALS): lead.lead_class="spam"
    elif lead.rental_intent=="offering" or any(signal in t for signal in BROKER_SIGNALS): lead.lead_class="agent_broker"
    elif lead.rental_intent=="seeking":
        lead.lead_class="hot_lead" if lead.lead_score>=THRESHOLDS["hot"] else "qualified_lead" if lead.lead_score>=THRESHOLDS["qualified"] else "watch" if lead.lead_score>=THRESHOLDS["watch"] else "irrelevant"
    elif lead.rental_intent=="unclear" and has_context and lead.lead_score>=THRESHOLDS["watch"]: lead.lead_class="watch"
    else: lead.lead_class="irrelevant"
    return lead
