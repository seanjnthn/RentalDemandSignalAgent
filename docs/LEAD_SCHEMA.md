# LEAD_SCHEMA.md — Rental Demand Signal Agent (MVP)

**Last updated:** 2026-07-13

Defines the extracted lead structure and the SQLite storage schema. Only
**public** metadata is stored (see `PRIVACY_AND_PLATFORM_POLICY.md`).

---

## 1. Extracted lead object

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `post_id` | string | API `id` | Primary key; used for dedup. |
| `source` | enum | fixed | Always `"threads"` in MVP. |
| `source_url` | string (URL) | API `permalink` | Public post link. |
| `author_username` | string | API `username` | Public handle (no `@`). |
| `post_timestamp` | ISO-8601 | API `timestamp` | When the post was made. |
| `fetched_at` | ISO-8601 | system | When we retrieved it. |
| `raw_text` | string | API `text` | Public post text (retention limited — see policy). |
| `rental_intent` | enum | extracted | `seeking` / `offering` / `unclear`. Only `seeking` is a lead. |
| `desired_location` | string | extracted | Best-effort from text + query location term. |
| `location_confidence` | float 0–1 | extracted | Because the API returns no geo. |
| `property_type` | enum | extracted | `apartment` / `house` / `kontrakan` / `kost` / `unknown`. |
| `bedrooms` | int / null | extracted | e.g. "2BR", "2 kamar". |
| `budget_min` | int / null | extracted | Numeric, currency in `budget_currency`. |
| `budget_max` | int / null | extracted | Numeric. |
| `budget_currency` | string | extracted | Default `IDR`. |
| `budget_period` | enum | extracted | `month` / `year` / `unknown`. |
| `move_in_date` | date / null | extracted | Parsed or relative ("next month"). |
| `rental_duration` | string / null | extracted | e.g. "12 months", "1 tahun". |
| `special_requirements` | string[] | extracted | e.g. `furnished`, `pet-friendly`, `near MRT`. |
| `lead_class` | enum | classifier | `hot_lead` / `qualified_lead` / `watch` / `irrelevant` / `agent_broker` / `spam`. |
| `lead_score` | int 0–100 | scorer | Transparent score. |
| `score_breakdown` | json | scorer | Array of `{rule, points, reason}`. |
| `score_version` | string | scorer | Rules version used. |
| `matched_inventory` | json | matcher | Array of matched listing refs (hot/qualified only). |
| `status` | enum | manual | `new` / `reviewed` / `contacted` / `responded` / `viewing_scheduled` / `converted` / `rejected`. |
| `dedup_hash` | string | ingest | Hash of normalized text for near-dup detection. |
| `alerted_at` | ISO-8601 / null | notifier | Set when sent to Telegram (idempotency). |

## 2. SQLite schema (DDL)

```sql
CREATE TABLE IF NOT EXISTS leads (
    post_id            TEXT PRIMARY KEY,
    source             TEXT NOT NULL DEFAULT 'threads',
    source_url         TEXT NOT NULL,
    author_username    TEXT NOT NULL,
    post_timestamp     TEXT NOT NULL,
    fetched_at         TEXT NOT NULL,
    raw_text           TEXT,
    rental_intent      TEXT,
    desired_location   TEXT,
    location_confidence REAL,
    property_type      TEXT,
    bedrooms           INTEGER,
    budget_min         INTEGER,
    budget_max         INTEGER,
    budget_currency    TEXT DEFAULT 'IDR',
    budget_period      TEXT,
    move_in_date       TEXT,
    rental_duration    TEXT,
    special_requirements TEXT,          -- JSON array
    lead_class         TEXT NOT NULL,
    lead_score         INTEGER NOT NULL,
    score_breakdown    TEXT,            -- JSON
    score_version      TEXT,
    matched_inventory  TEXT,            -- JSON
    status             TEXT NOT NULL DEFAULT 'new',
    dedup_hash         TEXT,
    alerted_at         TEXT
);

CREATE INDEX IF NOT EXISTS idx_leads_class  ON leads(lead_class);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_author ON leads(author_username);
CREATE INDEX IF NOT EXISTS idx_leads_dedup  ON leads(dedup_hash);

CREATE TABLE IF NOT EXISTS authors (
    username     TEXT PRIMARY KEY,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL,
    lead_count   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id      TEXT NOT NULL REFERENCES leads(post_id),
    sent_at      TEXT NOT NULL,
    channel      TEXT NOT NULL DEFAULT 'telegram',
    UNIQUE(post_id, channel)
);

CREATE TABLE IF NOT EXISTS status_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id      TEXT NOT NULL REFERENCES leads(post_id),
    old_status   TEXT,
    new_status   TEXT NOT NULL,
    changed_at   TEXT NOT NULL,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id TEXT PRIMARY KEY,
    title        TEXT,
    location     TEXT,
    property_type TEXT,
    bedrooms     INTEGER,
    price        INTEGER,
    currency     TEXT DEFAULT 'IDR',
    period       TEXT DEFAULT 'month',
    furnished    INTEGER,               -- 0/1
    available_from TEXT,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS scan_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    queries_used INTEGER,
    posts_fetched INTEGER,
    new_leads    INTEGER,
    alerts_sent  INTEGER
);
```

## 3. Inventory CSV format (MVP default)

`data/inventory.csv`:

```csv
inventory_id,title,location,property_type,bedrooms,price,currency,period,furnished,available_from,notes
INV001,Cozy 2BR @ Green Office Park,BSD,apartment,2,7500000,IDR,month,1,2026-08-01,Near AEON Mall
```

## 4. Status workflow (allowed transitions)

```
new ──▶ reviewed ──▶ contacted ──▶ responded ──▶ viewing_scheduled ──▶ converted
  │          │            │             │                 │
  └──────────┴────────────┴─────────────┴─────────────────┴────────▶ rejected
```

Every transition is appended to `status_history`. The system never sets status
past `new` automatically.
