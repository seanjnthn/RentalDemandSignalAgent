import argparse,json
from collections import Counter
from pathlib import Path
from . import config
from .extractor import extract
from .scorer import score
from .classifier import classify
from .ingest import is_duplicate
from .matcher import load_inventory,match
from .inventory import load_real_inventory, validate_real_inventory_for_scan
from .db import connect,existing,upsert_lead,mark_alert,set_status
from .notifier import format_card,format_preview_card,preview_eligible,TelegramNotifier,send_lead_cards
from .threads_client import ThreadsClient
from .apify_provider import ApifyThreadsProvider, apify_live_enabled
def posts_from_file(): return json.loads(Path(config.ROOT/'data/synthetic_posts.json').read_text(encoding='utf-8'))['posts']
VALID_INVENTORY_MODES = {"real", "synthetic", "none"}

def _inventory_for_scan(source, inventory_mode):
    requested = inventory_mode or config.INVENTORY_MODE
    if requested not in VALID_INVENTORY_MODES:
        raise ValueError(f"Invalid RDSA_INVENTORY_MODE {requested!r}; expected real, synthetic, or none")
    # Offline fixture scans retain their explicit sample inventory behavior. A
    # live/Apify scan never falls through to this branch.
    if inventory_mode is None and source == "synthetic":
        requested = "synthetic"
    if requested == "none":
        return [], False
    if requested == "synthetic":
        if source != "synthetic" and inventory_mode != "synthetic":
            raise ValueError("Synthetic inventory is only permitted for synthetic scans or explicit test mode")
        return load_inventory(config.INVENTORY_CSV), True
    rows, report = load_real_inventory(config.INVENTORY_REAL_CSV)
    if report.get("missing") or not rows:
        return [], False
    return rows, True

def process_raw(raw_posts, source, args, c, inventory_mode=None):
    pilot=getattr(args,"pilot",False)
    inv, matching_enabled = _inventory_for_scan(source, inventory_mode)
    if not matching_enabled and (inventory_mode or config.INVENTORY_MODE) == "real":
        print("Real inventory is not configured. Lead discovery will continue, but inventory matching is disabled.")
    old=existing(c) if c is not None else []
    new=alerts=duplicates=preview_count=normalized_posts=inventory_matches=0; classes={}; target_location=0; run_leads=[]
    target_areas = {loc[0] for loc in config.LOCATIONS}
    for item in raw_posts:
        post=item.get('post', item) if isinstance(item, dict) else item
        normalized_posts += 1
        lead=score(extract(post)); classify(lead)
        if is_duplicate(lead,old): duplicates+=1; continue
        if lead.desired_location in target_areas: target_location += 1
        if lead.lead_class in ('hot_lead','qualified_lead') and matching_enabled:
            lead.matched_inventory=match(lead,inv)
            inventory_matches += len(lead.matched_inventory)
        if c is not None:
            upsert_lead(c,lead,source)
        old.append({'post_id':lead.post_id,'author_username':lead.author_username,'dedup_hash':lead.dedup_hash,'raw_text':lead.raw_text}); new+=1
        run_leads.append(lead)
        classes[lead.lead_class]=classes.get(lead.lead_class,0)+1
        if lead.lead_class in ('hot_lead','qualified_lead'):
            preview_count += 1
            print(format_preview_card(lead, matching_enabled=matching_enabled) if pilot else format_card(lead)); print()
            if not pilot and source != 'apify' and not args.dry_run and c is not None:
                if mark_alert(c,lead.post_id): TelegramNotifier(config.TELEGRAM_BOT_TOKEN,config.TELEGRAM_CHAT_ID).send(format_card(lead)); alerts+=1
    return {'raw_posts': len(raw_posts), 'normalized_posts': normalized_posts,
            'duplicates': duplicates, 'new_rows': new, 'classifications': classes,
            'target_location': target_location, 'inventory_matches': inventory_matches,
            'leads': run_leads,
            'preview_count': preview_count, 'matching_enabled': matching_enabled,
            # Compatibility for callers of the original per-scan result.
            'new': new, 'alerts': alerts, 'classes': classes}

def _cumulative_report(c):
    rows = c.execute("SELECT lead_class,status,COUNT(*) AS n FROM leads GROUP BY lead_class,status").fetchall()
    classifications = Counter(); statuses = Counter()
    for row in rows:
        classifications[row["lead_class"]] += row["n"]
        statuses[row["status"]] += row["n"]
    return {"total_rows": sum(statuses.values()), "classifications": dict(classifications), "statuses": dict(statuses)}

def _evaluation_report(c):
    statuses = Counter(row[0] for row in c.execute("SELECT status FROM leads"))
    manually_reviewed = sum(n for status, n in statuses.items() if status != "new")
    return {"manually_reviewed": manually_reviewed, "confirmed_relevant": 0,
            "confirmed_false_positive": statuses.get("rejected", 0), "unreviewed": statuses.get("new", 0),
            "false_positive_rate_note": "False-positive rate not yet established." if not manually_reviewed else None}

def run_scan(args):
    c=connect(config.DB_PATH)
    if args.source=='synthetic': raw=posts_from_file()
    elif args.source=='threads':
        raise RuntimeError('live Threads source is intentionally stubbed until credentials and approval are configured')
    else:
        if not apify_live_enabled(): raise RuntimeError('Apify live disabled; set APIFY_LIVE_ENABLED=true to enable it')
        raw=ApifyThreadsProvider().search(config.APIFY_QUERIES, config.APIFY_MAX_PER_QUERY, max_total=config.APIFY_MAX_TOTAL)
    result=process_raw(raw,args.source,args,c)
    print(f"Scan complete: {result['new_rows']} new leads, {result['alerts']} new alerts")

def run_pilot_scan(args):
    if not apify_live_enabled():
        print('Pilot scan disabled: set APIFY_LIVE_ENABLED=true to enable Apify live access')
        return {'current': {}, 'cumulative': {}, 'cost': {}}
    c=connect(config.DB_PATH)
    provider=ApifyThreadsProvider()
    raw=provider.search_batched(config.PILOT_QUERIES, max_posts_per_query=5,
        max_total=config.APIFY_MAX_TOTAL, max_total_charge_usd=config.PILOT_MAX_TOTAL_CHARGE_USD)
    args.pilot=True; args.dry_run=True
    result=process_raw(raw,"apify",args,c)
    cumulative = _cumulative_report(c)
    evaluation = _evaluation_report(c)
    guard = provider.usage
    cost = {"current_run_usage_usd": getattr(provider, "last_run_usd", None),
            "monthly_accumulated_usd": guard.accumulated_usd,
            "warn_usd": guard.warn_usd, "stop_usd": guard.stop_usd,
            "remaining_usd": guard.remaining,
            "estimated_usd": guard.estimated_usd, "actual_usd": guard.actual_usd,
            "note": "maxTotalChargeUsD is a per-run cap; monthly accumulation may include earlier canary runs."}
    current_keys = ("raw_posts", "normalized_posts", "duplicates", "new_rows", "classifications",
                    "target_location", "inventory_matches", "preview_count")
    report = {"current": {key: result[key] for key in current_keys}, "cumulative": cumulative,
              "cost": cost, "evaluation": evaluation}
    print(f"Pilot scan complete: {result['new_rows']} new leads, {result['duplicates']} duplicates (preview only)")
    if evaluation["false_positive_rate_note"]:
        print(evaluation["false_positive_rate_note"])
    print(json.dumps({"cost": cost}, indent=2))
    return report

def _send_guard(args):
    if not getattr(args, "confirm_send", False):
        print("Sending requires --confirm-send; no message was sent.")
        return False
    if not config.TELEGRAM_SEND_ENABLED:
        print("Telegram sending disabled (set RDSA_TELEGRAM_SEND_ENABLED=true and pass --confirm-send).")
        return False
    return True

def run_telegram_test(args):
    if not _send_guard(args): return None
    test_msg = ("RDSA Telegram delivery test OK. This is a private, read-only rental-demand signal agent. "
                "No lead data is included in this test message.")
    TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_ALLOWED_CHAT_ID).send(test_msg)
    print("Telegram test message sent.")
    return {"delivery": "sent"}

def run_pilot_send(args):
    if not _send_guard(args): return None
    rows, inventory_report = validate_real_inventory_for_scan(config.INVENTORY_REAL_CSV)
    if not inventory_report.get("ok"):
        print(json.dumps(inventory_report, indent=2, ensure_ascii=False, sort_keys=True))
        print("Stopping before live scan.")
        return {"delivery": "stopped", "inventory": inventory_report}
    if not apify_live_enabled():
        print('Pilot send disabled: set APIFY_LIVE_ENABLED=true to enable Apify live access')
        return {"delivery": "stopped", "inventory": inventory_report}
    c=connect(config.DB_PATH); provider=ApifyThreadsProvider()
    raw=provider.search_batched(config.PILOT_QUERIES, max_posts_per_query=5, max_total=20, max_total_charge_usd=0.10)
    args.pilot=True; args.dry_run=True
    result=process_raw(raw, "apify", args, c, inventory_mode="real")
    eligible=[lead for lead in result["leads"] if preview_eligible(lead)]
    for lead in eligible: print(format_preview_card(lead, matching_enabled=True)); print()
    delivered=send_lead_cards(TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_ALLOWED_CHAT_ID), eligible, c,
                              matching_enabled=True, posts_scanned=result["raw_posts"], new_leads=result["new_rows"])
    cumulative=_cumulative_report(c); evaluation=_evaluation_report(c); guard=provider.usage
    cost={"current_run_usage_usd":getattr(provider,"last_run_usd",None),"monthly_accumulated_usd":guard.accumulated_usd,
          "warn_usd":guard.warn_usd,"stop_usd":guard.stop_usd,"remaining_usd":guard.remaining,
          "estimated_usd":guard.estimated_usd,"actual_usd":guard.actual_usd}
    report={"current":{k:result[k] for k in ("raw_posts","normalized_posts","duplicates","new_rows","classifications","target_location","inventory_matches","preview_count")},
            "cumulative":cumulative,"cost":cost,"evaluation":evaluation,"delivery":{"sent":delivered,"max_cards":3}}
    print(json.dumps({"delivery":report["delivery"],"cost":cost}, indent=2))
    return report
def main(argv=None):
    p=argparse.ArgumentParser(prog='rdsa'); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('init-db'); s=sub.add_parser('scan');s.add_argument('--source',choices=['synthetic','threads','apify'],default='synthetic');s.add_argument('--dry-run',action='store_true')
    sub.add_parser('pilot-scan')
    t=sub.add_parser('telegram-test'); t.add_argument('--confirm-send',action='store_true')
    ps=sub.add_parser('pilot-send'); ps.add_argument('--confirm-send',action='store_true')
    l=sub.add_parser('list');l.add_argument('--class',dest='klass'); st=sub.add_parser('status');st.add_argument('post_id');st.add_argument('new_status');sub.add_parser('match');sub.add_parser('notify');sub.add_parser('reprocess');sub.add_parser('purge')
    a=p.parse_args(argv); c=connect(config.DB_PATH)
    if a.cmd=='init-db': print(f'Database initialized: {config.DB_PATH}')
    elif a.cmd=='scan': run_scan(a)
    elif a.cmd=='pilot-scan': run_pilot_scan(a)
    elif a.cmd=='telegram-test': run_telegram_test(a)
    elif a.cmd=='pilot-send': run_pilot_send(a)
    elif a.cmd=='list':
        q='SELECT post_id,lead_class,lead_score,status,author_username FROM leads'; rows=c.execute(q+(' WHERE lead_class=?' if a.klass else ''),((a.klass,) if a.klass else ())).fetchall(); [print(dict(r)) for r in rows]
    elif a.cmd=='status': set_status(c,a.post_id,a.new_status); print('Status updated')
    elif a.cmd=='purge': c.execute('DELETE FROM leads');c.execute('DELETE FROM alerts');c.commit();print('Purged leads and alerts')
if __name__=='__main__': main()
