from .scoring_config import (BROKER_SIGNALS, RENTAL_CONTEXT_SIGNALS, SPAM_SIGNALS, THIRD_PARTY_DEMAND_SIGNALS,
                             GENUINE_SEEKER_CONTROLS, THRESHOLDS)


def _detect_third_party_cue(text: str):
    for cue in THIRD_PARTY_DEMAND_SIGNALS:
        if cue in text:
            return cue
    return None


def classify(lead):
    t = lead.raw_text.lower()
    has_context = any(signal in t for signal in RENTAL_CONTEXT_SIGNALS) and bool(lead.desired_location or lead.property_type != "unknown")
    if any(signal in t for signal in SPAM_SIGNALS):
        lead.lead_class = "spam"
        lead.classifier_reason = "spam_signal"
    elif lead.rental_intent == "offering" or any(signal in t for signal in BROKER_SIGNALS):
        lead.lead_class = "agent_broker"
        lead.classifier_reason = "offering_or_broker_signal"
    else:
        # Third-party-demand detection: an author sourcing/placing on behalf of a client
        # (broker/agent) must be classified agent_broker even when intent/location/type/budget
        # are explicit. Genuine first-person seekers (e.g. "untuk saya sendiri") stay eligible.
        cue = _detect_third_party_cue(t)
        genuine = any(ctrl in t for ctrl in GENUINE_SEEKER_CONTROLS)
        if cue and not genuine:
            lead.lead_class = "agent_broker"
            lead.classifier_reason = f"third_party_demand: {cue}"
        elif lead.rental_intent == "seeking":
            lead.lead_class = "hot_lead" if lead.lead_score >= THRESHOLDS["hot"] else "qualified_lead" if lead.lead_score >= THRESHOLDS["qualified"] else "watch" if lead.lead_score >= THRESHOLDS["watch"] else "irrelevant"
            lead.classifier_reason = "genuine_seeker" if lead.lead_class in ("hot_lead", "qualified_lead") else "seeking_low_score"
        elif lead.rental_intent == "unclear" and has_context and lead.lead_score >= THRESHOLDS["watch"]:
            lead.lead_class = "watch"
            lead.classifier_reason = "unclear_with_context"
        else:
            lead.lead_class = "irrelevant"
            lead.classifier_reason = "no_rental_signal"
    return lead
