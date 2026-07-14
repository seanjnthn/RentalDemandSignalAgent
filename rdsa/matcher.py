import csv

from .config import NEARBY_AREA_MAP, canonical_area


def load_inventory(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [{**r, "bedrooms": int(r["bedrooms"]), "price": int(r["price"]),
                 "furnished": int(r["furnished"])} for r in csv.DictReader(f)]


def _value(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _price_range(lead):
    low, high = _value(lead, "budget_min"), _value(lead, "budget_max")
    return low, high


def _candidate(lead, item):
    reasons, warnings, conflicts = [], [], []
    lead_area = canonical_area(_value(lead, "desired_location"))
    item_area = canonical_area(item.get("location"))
    if not lead_area:
        warnings.append("Location must be confirmed before recommending a unit.")
    elif lead_area == item_area:
        reasons.append("area aligned")
    elif item_area in NEARBY_AREA_MAP.get(lead_area, []):
        reasons.append("area nearby")
        warnings.append("Nearby alternative — confirm area flexibility.")
    else:
        conflicts.append("area conflict")
        warnings.append(f"lead area {lead_area}, inventory area {item_area or 'unknown'}")

    ptype = _value(lead, "property_type", "unknown")
    if not ptype or ptype == "unknown":
        warnings.append("Property type must be confirmed.")
    elif ptype == item.get("property_type"):
        reasons.append("property type aligned")
    else:
        conflicts.append("property type conflict")

    bedrooms = _value(lead, "bedrooms")
    if bedrooms is None:
        if item.get("bedrooms") is None:
            warnings.append("Bedrooms must be confirmed.")
    elif item.get("bedrooms") is None:
        warnings.append("Bedrooms must be confirmed.")
    elif item["bedrooms"] >= bedrooms:
        reasons.append("bedrooms aligned")
    else:
        conflicts.append("bedroom requirement conflict")

    budget_min, budget_max = _price_range(lead)
    period = _value(lead, "budget_period", "unknown") or "unknown"
    confidence = _value(lead, "budget_confidence", "low") or "low"
    has_budget = budget_min is not None or budget_max is not None
    budget_uncertain = has_budget and (period == "unknown" or confidence != "high")
    if has_budget and period == "unknown":
        warnings.append("Budget period must be confirmed.")
    elif has_budget:
        inventory_period = item.get("period", "month") or "month"
        # Extractor stores yearly budgets in monthly-normalized fields. Explicit
        # periods therefore permit a safe comparison to monthly inventory.
        inv_price = item.get("price")
        if period == "year" and inventory_period == "year":
            inv_price = inv_price * 12
        if period == inventory_period or (period == "year" and inventory_period == "month"):
            # A single parsed budget amount is a ceiling in the lead language;
            # do not reject cheaper units because it is also stored in min.
            compatible = budget_max is None or inv_price <= budget_max
        else:
            compatible = False
        if compatible:
            reasons.append("budget aligned")
        else:
            conflicts.append("budget conflict")

    if conflicts:
        match_type = "no_match"
    elif not lead_area or not reasons or not ptype or ptype == "unknown" or (bedrooms is None and item.get("bedrooms") is None):
        match_type = "tentative_match"
    elif lead_area != item_area:
        match_type = "nearby_alternative"
    elif budget_uncertain:
        match_type = "tentative_match"
    else:
        match_type = "exact_match"
    score = len(reasons) * 20 - len(conflicts) * 40
    if match_type == "exact_match": score += 40
    elif match_type == "nearby_alternative": score += 25
    elif match_type == "tentative_match": score += 5
    result = {"property_id": item.get("inventory_id", item.get("property_id")), "match_type": match_type,
              "score": score, "reasons": reasons, "warnings": warnings}
    # Compatibility fields for existing preview/tests; the five fields above
    # are the stable matching-quality contract.
    legacy_reasons = list(reasons)
    legacy_reasons += [{"area aligned": "location", "area nearby": "location",
                        "property type aligned": "property type", "bedrooms aligned": "bedrooms",
                        "budget aligned": "budget"}.get(reason, reason) for reason in reasons]
    result.update({"inventory_id": result["property_id"], "match_reasons": legacy_reasons,
                   "title": item.get("title"), "location": item.get("location"),
                   "property_type": item.get("property_type"), "bedrooms": item.get("bedrooms"),
                   "price": item.get("price")})
    return result


def match(lead, inventory, limit=3):
    if _value(lead, "lead_class") not in ("hot_lead", "qualified_lead"):
        return []
    candidates = [_candidate(lead, item) for item in inventory]
    # Prefer actionable candidates, but retain conflict explanations when
    # everything conflicts so the card can explain why no unit qualified.
    candidates.sort(key=lambda x: (x["match_type"] == "no_match", -x["score"]))
    viable = [candidate for candidate in candidates if candidate["match_type"] != "no_match"]
    return (viable or candidates)[:limit]
