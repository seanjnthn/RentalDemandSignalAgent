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
