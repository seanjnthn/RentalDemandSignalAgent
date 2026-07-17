import json,sqlite3
from difflib import SequenceMatcher
from datetime import datetime,timezone


def normalize_post_id(pid) -> str:
    return str(pid).strip()

def normalize_matched_inventory(value):
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return []
    if not isinstance(value, list) or any(item is None or not isinstance(item, dict) for item in value):
        return []
    return value
SCHEMA='''CREATE TABLE IF NOT EXISTS leads (post_id TEXT PRIMARY KEY,source TEXT NOT NULL DEFAULT 'threads',provider TEXT NOT NULL DEFAULT 'apify',source_url TEXT NOT NULL,author_username TEXT NOT NULL,post_timestamp TEXT NOT NULL,fetched_at TEXT NOT NULL,first_seen TEXT,last_seen TEXT,raw_text TEXT,rental_intent TEXT,desired_location TEXT,location_confidence REAL,property_type TEXT,bedrooms INTEGER,bedroom_min INTEGER,bedroom_max INTEGER,bedroom_options TEXT,studio_acceptable INTEGER,bedroom_confidence TEXT,bedroom_raw TEXT,budget_min INTEGER,budget_max INTEGER,budget_currency TEXT DEFAULT 'IDR',budget_period TEXT,budget_confidence TEXT,budget_note TEXT,budget_raw TEXT,move_in_date TEXT,rental_duration TEXT,special_requirements TEXT,lead_class TEXT NOT NULL,classifier_reason TEXT,lead_score INTEGER NOT NULL,score_breakdown TEXT,score_version TEXT,matched_inventory TEXT,status TEXT NOT NULL DEFAULT 'new',notes TEXT,dedup_hash TEXT,alerted_at TEXT);
CREATE INDEX IF NOT EXISTS idx_leads_class ON leads(lead_class);CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);CREATE INDEX IF NOT EXISTS idx_leads_author ON leads(author_username);CREATE INDEX IF NOT EXISTS idx_leads_dedup ON leads(dedup_hash);
CREATE TABLE IF NOT EXISTS authors(username TEXT PRIMARY KEY,first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,lead_count INTEGER NOT NULL DEFAULT 1);CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id TEXT NOT NULL REFERENCES leads(post_id),sent_at TEXT NOT NULL,channel TEXT NOT NULL DEFAULT 'telegram',UNIQUE(post_id,channel));CREATE TABLE IF NOT EXISTS delivery_claims(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id TEXT NOT NULL,channel TEXT NOT NULL DEFAULT 'telegram',status TEXT NOT NULL,claimed_at TEXT NOT NULL,sent_at TEXT,message_id TEXT,error TEXT,UNIQUE(post_id,channel));CREATE TABLE IF NOT EXISTS status_history(id INTEGER PRIMARY KEY AUTOINCREMENT,post_id TEXT NOT NULL REFERENCES leads(post_id),old_status TEXT,new_status TEXT NOT NULL,changed_at TEXT NOT NULL,note TEXT);CREATE TABLE IF NOT EXISTS inventory(inventory_id TEXT PRIMARY KEY,title TEXT,location TEXT,property_type TEXT,bedrooms INTEGER,price INTEGER,currency TEXT DEFAULT 'IDR',period TEXT DEFAULT 'month',furnished INTEGER,available_from TEXT,notes TEXT);CREATE TABLE IF NOT EXISTS scan_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,started_at TEXT NOT NULL,finished_at TEXT,queries_used INTEGER,posts_fetched INTEGER,new_leads INTEGER,alerts_sent INTEGER);
CREATE TABLE IF NOT EXISTS scheduled_runs(
  run_id TEXT PRIMARY KEY,
  trigger_type TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  actor_run_id TEXT,
  raw_posts INTEGER,
  normalized_posts INTEGER,
  existing_posts INTEGER,
  new_posts INTEGER,
  eligible_leads INTEGER,
  claimed_deliveries INTEGER,
  sent_cards INTEGER,
  usage_total_usd REAL,
  monthly_usage_usd REAL,
  error_code TEXT,
  sanitized_error TEXT,
  scheduler_send_enabled INTEGER,
  process_id INTEGER,
  current_phase TEXT,
  heartbeat_at TEXT,
  interruption_reason TEXT
);
CREATE TABLE IF NOT EXISTS scheduled_run_leads(
  run_id TEXT NOT NULL REFERENCES scheduled_runs(run_id),
  post_id TEXT NOT NULL,
  inserted_this_run INTEGER NOT NULL DEFAULT 0,
  classification TEXT,
  eligible INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, post_id)
);'''
def connect(path):
    c=sqlite3.connect(path);c.row_factory=sqlite3.Row;c.executescript(SCHEMA)
    cols={r[1] for r in c.execute('PRAGMA table_info(leads)')}
    for name, definition in (("provider", "TEXT NOT NULL DEFAULT 'apify'"),("first_seen", "TEXT"),("last_seen", "TEXT"),("notes", "TEXT"),("budget_confidence", "TEXT"),("budget_note", "TEXT"),("budget_raw", "TEXT"),("classifier_reason", "TEXT"),("bedroom_min", "INTEGER"),("bedroom_max", "INTEGER"),("bedroom_options", "TEXT"),("studio_acceptable", "INTEGER"),("bedroom_confidence", "TEXT"),("bedroom_raw", "TEXT")):
        if name not in cols: c.execute(f'ALTER TABLE leads ADD COLUMN {name} {definition}')
    alert_cols={r[1] for r in c.execute('PRAGMA table_info(alerts)')}
    if 'message_id' not in alert_cols: c.execute('ALTER TABLE alerts ADD COLUMN message_id TEXT')
    c.execute("""INSERT OR IGNORE INTO delivery_claims(post_id,channel,status,claimed_at,sent_at,message_id)
                 SELECT TRIM(CAST(post_id AS TEXT)),channel,'sent',sent_at,sent_at,message_id FROM alerts""")
    c.commit(); return c
def existing(c):
    rows=[dict(r) for r in c.execute('SELECT post_id,author_username,dedup_hash,raw_text FROM leads')]
    for row in rows: row['post_id']=normalize_post_id(row['post_id'])
    return rows
def read_matched_inventory(c, post_id):
    row = c.execute('SELECT matched_inventory FROM leads WHERE post_id=?', (normalize_post_id(post_id),)).fetchone()
    return normalize_matched_inventory(row[0] if row else None)

def upsert_lead(c,lead,provider="apify"):
    d=lead.to_dict(); d['post_id']=normalize_post_id(d['post_id']); d['matched_inventory']=normalize_matched_inventory(d.get('matched_inventory')); cols=['post_id','source_url','author_username','post_timestamp','fetched_at','raw_text','rental_intent','desired_location','location_confidence','property_type','bedrooms','bedroom_min','bedroom_max','bedroom_options','studio_acceptable','bedroom_confidence','bedroom_raw','budget_min','budget_max','budget_currency','budget_period','budget_confidence','budget_note','budget_raw','move_in_date','rental_duration','special_requirements','lead_class','classifier_reason','lead_score','score_breakdown','score_version','matched_inventory','status','dedup_hash']
    vals=[d.get(x) for x in cols]; vals=[json.dumps(x) if isinstance(x,(list,dict)) else x for x in vals]
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
def already_sent(c, post_id):
    return c.execute("SELECT 1 FROM alerts WHERE post_id=? AND channel='telegram' LIMIT 1", (normalize_post_id(post_id),)).fetchone() is not None
def mark_alert(c,post_id,message_id=None):
    cur=c.execute('INSERT OR IGNORE INTO alerts(post_id,sent_at,message_id) VALUES(?,?,?)',(normalize_post_id(post_id),datetime.now(timezone.utc).isoformat(),message_id));c.commit();return cur.rowcount

def claim_delivery(c, post_id, channel='telegram') -> bool:
    cur=c.execute("INSERT OR IGNORE INTO delivery_claims(post_id,channel,status,claimed_at) VALUES(?,?,'pending',?)",(normalize_post_id(post_id),channel,datetime.now(timezone.utc).isoformat()))
    c.commit();return cur.rowcount == 1

def complete_delivery(c, post_id, message_id, channel='telegram'):
    c.execute("UPDATE delivery_claims SET status='sent',sent_at=?,message_id=?,error=NULL WHERE post_id=? AND channel=?",(datetime.now(timezone.utc).isoformat(),message_id,normalize_post_id(post_id),channel));c.commit()

def fail_delivery(c, post_id, error, channel='telegram'):
    c.execute("UPDATE delivery_claims SET status='failed',error=? WHERE post_id=? AND channel=?",(str(error),normalize_post_id(post_id),channel));c.commit()
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

# ---------------------------------------------------------------------------
# Scheduled-run => lead provenance (v0.7.3)
# ---------------------------------------------------------------------------
def migrate_provenance(c) -> None:
    """Create scheduled_run_leads idempotently. Safe to call repeatedly."""
    c.execute(
        """CREATE TABLE IF NOT EXISTS scheduled_run_leads(
            run_id TEXT NOT NULL REFERENCES scheduled_runs(run_id),
            post_id TEXT NOT NULL,
            inserted_this_run INTEGER NOT NULL DEFAULT 0,
            classification TEXT,
            eligible INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            PRIMARY KEY (run_id, post_id))"""
    )
    c.commit()


def associate_run_leads(c, run_id: str, associations: list[dict]) -> int:
    """Record every processed lead for a scheduled run (new + already-existing).

    `associations` is a list of dicts with keys: post_id, inserted_this_run (bool),
    classification (str), eligible (bool). The composite PK (run_id, post_id) makes
    this idempotent: re-associating the same post for the same run is a no-op.
    Returns the number of NEW rows inserted. No secrets or raw text are stored.
    """
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        (run_id, normalize_post_id(a["post_id"]), int(bool(a.get("inserted_this_run", 0))),
         a.get("classification"), int(bool(a.get("eligible", 0))), now)
        for a in associations
    ]
    before = c.total_changes
    c.executemany(
        "INSERT OR IGNORE INTO scheduled_run_leads"
        "(run_id, post_id, inserted_this_run, classification, eligible, created_at)"
        " VALUES(?,?,?,?,?,?)", rows
    )
    inserted = c.total_changes - before
    c.commit()
    return inserted


def leads_for_run(c, run_id: str) -> list[dict]:
    """Exact, no-timestamp-reconstruction lead association for a run."""
    return [dict(r) for r in c.execute(
        "SELECT post_id, inserted_this_run, classification, eligible, created_at "
        "FROM scheduled_run_leads WHERE run_id=? ORDER BY post_id", (run_id,))]


def new_post_ids_for_run(c, run_id: str) -> list[str]:
    return [r["post_id"] for r in c.execute(
        "SELECT post_id FROM scheduled_run_leads WHERE run_id=? AND inserted_this_run=1",
        (run_id,)).fetchall()]
