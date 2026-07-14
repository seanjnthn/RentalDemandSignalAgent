import json,sqlite3
from difflib import SequenceMatcher
from datetime import datetime,timezone
SCHEMA='''CREATE TABLE IF NOT EXISTS leads (post_id TEXT PRIMARY KEY,source TEXT NOT NULL DEFAULT 'threads',provider TEXT NOT NULL DEFAULT 'apify',source_url TEXT NOT NULL,author_username TEXT NOT NULL,post_timestamp TEXT NOT NULL,fetched_at TEXT NOT NULL,first_seen TEXT,last_seen TEXT,raw_text TEXT,rental_intent TEXT,desired_location TEXT,location_confidence REAL,property_type TEXT,bedrooms INTEGER,budget_min INTEGER,budget_max INTEGER,budget_currency TEXT DEFAULT 'IDR',budget_period TEXT,move_in_date TEXT,rental_duration TEXT,special_requirements TEXT,lead_class TEXT NOT NULL,lead_score INTEGER NOT NULL,score_breakdown TEXT,score_version TEXT,matched_inventory TEXT,status TEXT NOT NULL DEFAULT 'new',notes TEXT,dedup_hash TEXT,alerted_at TEXT);
CREATE INDEX IF NOT EXISTS idx_leads_class ON leads(lead_class);CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);CREATE INDEX IF NOT EXISTS idx_leads_author ON leads(author_username);CREATE INDEX IF NOT EXISTS idx_leads_dedup ON leads(dedup_hash);
CREATE TABLE IF NOT EXISTS authors(username TEXT PRIMARY KEY,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,lead_count INTEGER NOT NULL DEFAULT 1);CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id TEXT NOT NULL REFERENCES leads(post_id),sent_at TEXT NOT NULL,channel TEXT NOT NULL DEFAULT 'telegram',UNIQUE(post_id,channel));CREATE TABLE IF NOT EXISTS status_history(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id TEXT NOT NULL REFERENCES leads(post_id),old_status TEXT,new_status TEXT NOT NULL,changed_at TEXT NOT NULL,note TEXT);CREATE TABLE IF NOT EXISTS inventory(inventory_id TEXT PRIMARY KEY,title TEXT,location TEXT,property_type TEXT,bedrooms INTEGER,price INTEGER,currency TEXT DEFAULT 'IDR',period TEXT DEFAULT 'month',furnished INTEGER,available_from TEXT,notes TEXT);CREATE TABLE IF NOT EXISTS scan_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,started_at TEXT NOT NULL,finished_at TEXT,queries_used INTEGER,posts_fetched INTEGER,new_leads INTEGER,alerts_sent INTEGER);'''
def connect(path):
    c=sqlite3.connect(path);c.row_factory=sqlite3.Row;c.executescript(SCHEMA)
    cols={r[1] for r in c.execute('PRAGMA table_info(leads)')}
    for name, definition in (("provider", "TEXT NOT NULL DEFAULT 'apify'"),("first_seen", "TEXT"),("last_seen", "TEXT"),("notes", "TEXT")):
        if name not in cols: c.execute(f'ALTER TABLE leads ADD COLUMN {name} {definition}')
    c.commit(); return c
def existing(c): return [dict(r) for r in c.execute('SELECT post_id,author_username,dedup_hash,raw_text FROM leads')]
def upsert_lead(c,lead,provider="apify"):
    d=lead.to_dict(); cols=['post_id','source_url','author_username','post_timestamp','fetched_at','raw_text','rental_intent','desired_location','location_confidence','property_type','bedrooms','budget_min','budget_max','budget_currency','budget_period','move_in_date','rental_duration','special_requirements','lead_class','lead_score','score_breakdown','score_version','matched_inventory','status','dedup_hash']
    vals=[d[x] for x in cols]; vals=[json.dumps(x) if isinstance(x,(list,dict)) else x for x in vals]
    now=datetime.now(timezone.utc).isoformat()
    near=c.execute('SELECT post_id,author_username,raw_text,status FROM leads WHERE post_id != ?',(d['post_id'],)).fetchall()
    normalized=' '.join((d.get('raw_text') or '').lower().split())
    for row in near:
        if row['author_username'] == d.get('author_username') and SequenceMatcher(None, normalized, ' '.join((row['raw_text'] or '').lower().split())).ratio() >= .9:
            c.execute("UPDATE leads SET status='duplicate',last_seen=? WHERE post_id=? AND status='new'", (now, row['post_id']))
            c.commit(); return 0
    cols = ['provider','first_seen','last_seen'] + cols
    vals = [provider,now,now] + vals
    cur=c.execute('INSERT OR IGNORE INTO leads('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',vals)
    if cur.rowcount == 0:
        c.execute('UPDATE leads SET last_seen=? WHERE post_id=?', (now, d['post_id']))
    c.commit();return cur.rowcount
def mark_alert(c,post_id): cur=c.execute('INSERT OR IGNORE INTO alerts(post_id,sent_at) VALUES(?,?)',(post_id,datetime.now(timezone.utc).isoformat()));c.commit();return cur.rowcount
def set_status(c,post_id,new):
    row=c.execute('SELECT status FROM leads WHERE post_id=?',(post_id,)).fetchone()
    if not row: raise ValueError('unknown post')
    old=row[0]; allowed={'new':{'reviewed','negotiating','duplicate','rejected'},'reviewed':{'contacted','rejected'},'contacted':{'responded','negotiating','rejected'},'responded':{'viewing_scheduled','rejected'},'viewing_scheduled':{'converted','negotiating','rejected'},'negotiating':{'converted','rejected'},'converted':set(),'rejected':set(),'duplicate':set(),'irrelevant':set()}
    if new not in allowed.get(old,set()): raise ValueError(f'invalid transition {old} -> {new}')
    c.execute('UPDATE leads SET status=? WHERE post_id=?',(new,post_id));c.execute('INSERT INTO status_history(post_id,old_status,new_status,changed_at) VALUES(?,?,?,?)',(post_id,old,new,datetime.now(timezone.utc).isoformat()));c.commit()

def purge_old_leads(c, days):
    cutoff = datetime.now(timezone.utc).timestamp() - int(days) * 86400
    rows = c.execute("SELECT post_id,last_seen FROM leads WHERE status IN ('rejected','duplicate','irrelevant')").fetchall()
    ids=[]
    for row in rows:
        try: old = datetime.fromisoformat((row['last_seen'] or '').replace('Z','+00:00')).timestamp() < cutoff
        except (ValueError, TypeError): old = False
        if old: ids.append(row['post_id'])
    if ids: c.executemany('DELETE FROM leads WHERE post_id=?', [(x,) for x in ids]); c.commit()
    return len(ids)
