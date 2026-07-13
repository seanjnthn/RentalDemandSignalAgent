# ARCHITECTURE.md — Rental Demand Signal Agent (MVP)

**Last updated:** 2026-07-13

---

## 1. Design principles

- **Compliance by construction.** The Threads client is *read-only*: it exposes
  only `keyword_search` GET calls. No write/reply/follow methods exist in the
  codebase.
- **Small, boring, testable.** One Python package, one CLI, SQLite, no server.
- **Deterministic core, offline-testable.** Extraction, scoring, dedup, and
  matching are pure functions over post dicts — runnable against synthetic data
  with zero network access.
- **Every alert is explainable.** The score breakdown travels with the lead.

## 2. High-level flow

```
                    ┌─────────────────────────────────────────────┐
                    │              CLI  (rdsa ...)                  │
                    │  scan · reprocess · match · notify · status  │
                    └───────────────┬─────────────────────────────┘
                                    │
   ┌──────────────┐   posts   ┌─────▼──────┐  raw   ┌──────────────┐
   │ Threads      │──────────▶│  Ingest /  │───────▶│  Extractor   │
   │ Keyword      │  (public) │  Dedup     │        │ (rules/NLP)  │
   │ Search API   │           └─────┬──────┘        └──────┬───────┘
   └──────────────┘                 │ new only             │ fields
        (read-only)                 │                      ▼
                                    │              ┌──────────────┐
                                    │              │  Classifier  │
                                    │              │  + Scorer    │
                                    │              └──────┬───────┘
                                    │                     │ lead + score
                                    ▼                     ▼
                            ┌───────────────┐     ┌──────────────┐
                            │   SQLite DB   │◀────│  Inventory   │
                            │ leads,authors,│     │  Matcher     │
                            │ alerts,status │     │ (CSV/SQLite) │
                            └───────┬───────┘     └──────────────┘
                                    │ hot + qualified only
                                    ▼
                            ┌───────────────┐
                            │   Telegram    │  (send-only, human review)
                            │   Notifier    │
                            └───────────────┘
```

## 3. Components

| # | Component | File (proposed) | Responsibility |
|---|-----------|-----------------|----------------|
| 1 | **Config** | `rdsa/config.py` | Load env/`.env`, keyword list, locations, thresholds, Telegram target. |
| 2 | **Threads client** | `rdsa/threads_client.py` | Read-only wrapper over `GET /v1.0/keyword_search`. Handles pagination, rate-limit budget, retries. **No write methods.** |
| 3 | **Query planner** | `rdsa/query_planner.py` | Build the keyword × location query set; enforce a per-run query budget. |
| 4 | **Ingest + dedup** | `rdsa/ingest.py` | Normalize posts, hash for dedup, drop already-seen post IDs / recent author repeats. |
| 5 | **Extractor** | `rdsa/extractor.py` | Pull structured fields from `text` (intent, location, type, bedrooms, budget, dates, duration, requirements). Rules-first, pluggable LLM later. |
| 6 | **Classifier** | `rdsa/classifier.py` | Assign one of the 6 classes from signals. |
| 7 | **Scorer** | `rdsa/scorer.py` | 0–100 transparent score + breakdown (see `SCORING_RULES.md`). |
| 8 | **Inventory matcher** | `rdsa/matcher.py` | Load CSV/SQLite inventory; match on location, type, bedrooms, budget. |
| 9 | **Storage** | `rdsa/db.py` | SQLite schema + CRUD for leads, authors, alerts, status history. |
| 10 | **Notifier** | `rdsa/notifier.py` | Send-only Telegram Bot API `sendMessage`. Formats the review card. |
| 11 | **CLI / orchestrator** | `rdsa/cli.py` | Wire the pipeline; subcommands. |

## 4. Data flow contracts

- **Threads post (raw):** `{id, text, media_type, permalink, timestamp, username,
  has_replies, is_quote_post, is_reply}` — exactly the fields the API returns.
- **Lead (extracted):** see `LEAD_SCHEMA.md`.
- **Score:** `{score: int, band: str, breakdown: [{rule, points, reason}], version}`.
- **Match:** `{inventory_id, address, type, bedrooms, price, match_reasons, score}`.

## 5. Pipeline stages (idempotent)

1. `plan_queries()` → list of `(q, location, since, until)`.
2. `fetch()` → raw posts (respecting query budget).
3. `dedup()` → drop known `post_id`s and recent same-author repeats.
4. `extract()` → structured fields + per-field confidence.
5. `classify()` + `score()` → class + 0–100 + breakdown.
6. `persist()` → upsert into SQLite (status defaults to `new`).
7. `match()` → attach inventory matches for hot/qualified.
8. `notify()` → send hot/qualified not-yet-alerted leads to Telegram; mark alerted.

## 6. Storage (SQLite) — logical tables

- `leads` — one row per unique post; extracted fields, class, score, status, timestamps.
- `authors` — username → first_seen, last_seen, lead_count (for author-level dedup/throttle).
- `alerts` — which leads were sent to Telegram and when (idempotency guard).
- `status_history` — append-only log of manual status transitions.
- `inventory` — optional; if using SQLite instead of CSV.
- `scan_runs` — audit: run time, queries used, posts fetched, new leads, alerts sent.

See `LEAD_SCHEMA.md` for column-level detail.

## 7. External interfaces

| Interface | Direction | Auth | Notes |
|-----------|-----------|------|-------|
| Threads Keyword Search API | **read-only** | Threads user access token (OAuth2, long-lived) | `graph.threads.net/v1.0/keyword_search` |
| Telegram Bot API | **send-only** | Bot token | `sendMessage` to one configured chat_id |
| Inventory | read | local file | CSV first, SQLite optional |

## 8. Tech stack

- Python 3.11+, `requests` (or `httpx`), `python-dotenv`, `pydantic` (optional for
  schema), `pytest` for tests. SQLite via stdlib `sqlite3`. No web framework.

## 9. Scheduling

- MVP: run `rdsa scan` manually or via a Hermes cron job (e.g. every few hours),
  sized to stay far under the 2,200/24h query budget. No always-on service.

## 10. Compliance guardrails (enforced in code)

- The Threads client module contains **only** GET/search functions.
- A unit test greps the codebase to assert no `reply`, `repost`, `follow`, `like`,
  `POST` to Threads publish endpoints exist.
- Only `permalink` (public URL) + `username` + public text fields are stored.
- Telegram notifier is the only outbound-message component, and it targets the
  operator's own chat — never a Threads user.
