# Rental Demand Signal Agent (MVP)

Finds **public** Threads posts from people actively looking to rent in the
Greater Serpong / South Tangerang area, extracts their requirements, scores and
classifies each as a lead, matches qualified leads to your property inventory,
and sends only the good leads to **Telegram for a human to review and contact
manually**.

> **Compliance first.** Official Threads API only. Public content only.
> Read-only on Threads — the agent never replies, comments, follows, DMs, or
> contacts anyone. See `docs/PRIVACY_AND_PLATFORM_POLICY.md`.

## Status

📋 **Planning complete — awaiting operator approval before implementation.**
This repo currently contains planning docs + test fixtures only. Code is built
by Codex, task-by-task, after approval.

## Documents

| Doc | Purpose |
|-----|---------|
| [`docs/PRODUCT_REQUIREMENTS.md`](docs/PRODUCT_REQUIREMENTS.md) | Scope, requirements, success criteria |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Components, data flow, storage |
| [`docs/LEAD_SCHEMA.md`](docs/LEAD_SCHEMA.md) | Lead object + SQLite DDL |
| [`docs/SCORING_RULES.md`](docs/SCORING_RULES.md) | Transparent 0–100 scoring (v1.0) |
| [`docs/PRIVACY_AND_PLATFORM_POLICY.md`](docs/PRIVACY_AND_PLATFORM_POLICY.md) | Hard compliance boundaries |
| [`docs/CREDENTIALS_AND_PERMISSIONS.md`](docs/CREDENTIALS_AND_PERMISSIONS.md) | API facts, tokens, scopes |
| [`docs/VERTICAL_SLICE.md`](docs/VERTICAL_SLICE.md) | Smallest end-to-end slice |
| [`docs/TASKS.md`](docs/TASKS.md) | Phased, TDD task breakdown for Codex |

## Test fixtures

- `data/synthetic_posts.json` — 20 labeled synthetic Threads posts (all 6 classes).
- `data/inventory.csv` — sample property inventory for matching.

## Key facts (verified against official Threads docs, Jul 2026)

- Endpoint: `GET https://graph.threads.net/v1.0/keyword_search`
- Scopes: `threads_basic` + `threads_keyword_search` (**App Review required** for
  public results; pre-approval it searches only your own posts).
- Rate limit: **2,200 queries / rolling 24h per user**.
- API returns **no location/geo/follower data** — location is inferred from text.

## Monitored keywords × locations

**Keywords:** cari apartemen · butuh apartemen · sewa apartemen · cari kontrakan ·
cari rumah sewa · looking for apartment · apartment needed
**Locations:** BSD · Alam Sutera · Gading Serpong · Tangerang Selatan

## Roles

- **Human** — approves leads, contacts people manually, manages inventory, updates status.
- **Hermes** — plans, orchestrates, schedules scans, analyzes/reviews leads & Codex output.
- **Codex** — builds connector, DB, scoring, matcher, notifier, tests, docs.
# Rental Demand Signal Agent

An offline-first, read-only Threads demand-signal MVP. It extracts public rental intent, scores and classifies it with transparent v1.0 rules, matches local inventory, stores minimal data in SQLite, and sends review cards only to the operator's Telegram group.

## Setup

```bash
python -m pip install -e ".[test]"
copy .env.example .env       # Windows
rdsa init-db
```

Run the complete offline vertical slice:

```bash
rdsa scan --source synthetic --dry-run
rdsa list --class hot_lead
rdsa status 4001 reviewed
pytest
```

## App Review Demo

Install and launch the human-triggered Streamlit review surface:

```bash
pip install -e .[test]
streamlit run app_review_demo.py
```

Synthetic mode reads `data/synthetic_posts.json` and needs no credentials or
network access. Live mode is off unless `THREADS_LIVE_ENABLED=true` and
`THREADS_APP_ID`, `THREADS_APP_SECRET`, and `THREADS_REDIRECT_URI` are set.
The demo is read-only on Threads and never automatically contacts authors.

The live Threads source is intentionally stubbed: it requires the official API, approved keyword-search permission, and credentials. The only Threads operation implemented is the official keyword-search GET. Telegram is send-only to the configured operator group; outreach to leads remains manual.

## Apify live provider

Apify is the primary live provider and uses the read-only `automation-lab/threads-scraper` actor for public Threads posts. Live is off by default. Set `APIFY_API_TOKEN` and `APIFY_LIVE_ENABLED=true` (optionally `APIFY_ACTOR_ID`) to enable it. Limits are `APIFY_MAX_TOTAL=20` and `APIFY_MAX_PER_QUERY=5`; approved queries are in `rdsa/config.py`.

Preview with `rdsa scan --source apify --dry-run`. The monthly guard stores estimated cost in `data/apify_usage.json`, warns at $4.00, and refuses new runs at $4.75. The Apify path only prints cards for manual review and never sends Telegram. The existing `OfficialThreadsProvider` in `rdsa/threads_client.py` is retained unchanged but disabled.

Status transitions are `new -> reviewed -> contacted -> responded -> viewing_scheduled -> converted`, with `rejected` available from any active state. See `docs/RUNBOOK.md` for operating notes.
