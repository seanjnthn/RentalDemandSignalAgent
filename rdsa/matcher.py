import csv
def load_inventory(path):
    with open(path,newline="",encoding="utf-8") as f: return [{**r,"bedrooms":int(r["bedrooms"]),"price":int(r["price"]),"furnished":int(r["furnished"])} for r in csv.DictReader(f)]
def match(lead,inventory,limit=3):
    if lead.lead_class not in ("hot_lead","qualified_lead"): return []
    out=[]
    for i in inventory:
        reasons=[]
        if lead.desired_location and i["location"].lower()==lead.desired_location.lower(): reasons.append("location")
        if lead.property_type=="unknown" or i["property_type"]==lead.property_type: reasons.append("property type")
        if lead.bedrooms is None or i["bedrooms"]>=lead.bedrooms: reasons.append("bedrooms")
        budget_known = getattr(lead, "budget_confidence", "low") in ("high", "medium")
        if budget_known and (lead.budget_max is None or i["price"] <= lead.budget_max): reasons.append("budget")
        if len(reasons)>=3: out.append({"inventory_id":i["inventory_id"],"title":i["title"],"location":i["location"],"property_type":i["property_type"],"bedrooms":i["bedrooms"],"price":i["price"],"match_reasons":reasons,"score":len(reasons)})
    return sorted(out,key=lambda x:x["score"],reverse=True)[:limit]
