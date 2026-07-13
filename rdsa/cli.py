import argparse,json
from pathlib import Path
from . import config
from .extractor import extract
from .scorer import score
from .classifier import classify
from .ingest import is_duplicate
from .matcher import load_inventory,match
from .db import connect,existing,upsert_lead,mark_alert,set_status
from .notifier import format_card,TelegramNotifier
from .threads_client import ThreadsClient
from .apify_provider import ApifyThreadsProvider, apify_live_enabled
def posts_from_file(): return json.loads(Path(config.ROOT/'data/synthetic_posts.json').read_text(encoding='utf-8'))['posts']
def process_raw(raw_posts, source, args, c):
    inv=load_inventory(config.INVENTORY_CSV); old=existing(c) if c is not None else []
    new=alerts=duplicates=0; classes={}
    for item in raw_posts:
        post=item.get('post', item) if isinstance(item, dict) else item
        lead=score(extract(post)); classify(lead)
        if is_duplicate(lead,old): duplicates+=1; continue
        if lead.lead_class in ('hot_lead','qualified_lead'): lead.matched_inventory=match(lead,inv)
        if c is not None:
            upsert_lead(c,lead)
        old.append({'post_id':lead.post_id,'author_username':lead.author_username,'dedup_hash':lead.dedup_hash,'raw_text':lead.raw_text}); new+=1
        classes[lead.lead_class]=classes.get(lead.lead_class,0)+1
        if lead.lead_class in ('hot_lead','qualified_lead'):
            print(format_card(lead)); print()
            if source != 'apify' and not args.dry_run and c is not None:
                if mark_alert(c,lead.post_id): TelegramNotifier(config.TELEGRAM_BOT_TOKEN,config.TELEGRAM_CHAT_ID).send(format_card(lead)); alerts+=1
    return {'new':new,'alerts':alerts,'duplicates':duplicates,'classes':classes}

def run_scan(args):
    c=connect(config.DB_PATH)
    if args.source=='synthetic': raw=posts_from_file()
    elif args.source=='threads':
        raise RuntimeError('live Threads source is intentionally stubbed until credentials and approval are configured')
    else:
        if not apify_live_enabled(): raise RuntimeError('Apify live disabled; set APIFY_LIVE_ENABLED=true to enable it')
        raw=ApifyThreadsProvider().search(config.APIFY_QUERIES, config.APIFY_MAX_PER_QUERY, max_total=config.APIFY_MAX_TOTAL)
    result=process_raw(raw,args.source,args,c)
    print(f"Scan complete: {result['new']} new leads, {result['alerts']} new alerts")
def main(argv=None):
    p=argparse.ArgumentParser(prog='rdsa'); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('init-db'); s=sub.add_parser('scan');s.add_argument('--source',choices=['synthetic','threads','apify'],default='synthetic');s.add_argument('--dry-run',action='store_true')
    l=sub.add_parser('list');l.add_argument('--class',dest='klass'); st=sub.add_parser('status');st.add_argument('post_id');st.add_argument('new_status');sub.add_parser('match');sub.add_parser('notify');sub.add_parser('reprocess');sub.add_parser('purge')
    a=p.parse_args(argv); c=connect(config.DB_PATH)
    if a.cmd=='init-db': print(f'Database initialized: {config.DB_PATH}')
    elif a.cmd=='scan': run_scan(a)
    elif a.cmd=='list':
        q='SELECT post_id,lead_class,lead_score,status,author_username FROM leads'; rows=c.execute(q+(' WHERE lead_class=?' if a.klass else ''),((a.klass,) if a.klass else ())).fetchall(); [print(dict(r)) for r in rows]
    elif a.cmd=='status': set_status(c,a.post_id,a.new_status); print('Status updated')
    elif a.cmd=='purge': c.execute('DELETE FROM leads');c.execute('DELETE FROM alerts');c.commit();print('Purged leads and alerts')
if __name__=='__main__': main()
