# PRODUCT_REQUIREMENTS.md — Rental Demand Signal Agent (MVP)

**Status:** Draft for approval
**Owner:** Human (product) · Hermes (PM/orchestrator) · Codex (implementation)
**Last updated:** 2026-07-13

---

## 1. Problem statement

Property agents in the Greater Serpong / South Tangerang area waste hours
manually scrolling social media to find people who are actively looking to
rent. There is no structured, compliant way to surface these "demand signals,"
qualify them, and route the good ones to a human for outreach.

## 2. Goal

Build a small, compliant AI agent that:

1. Finds **public** Threads posts from people **actively looking to rent** a home.
2. Extracts structured rental requirements from each post.
3. Scores and classifies each post as a lead.
4. Matches qualified leads against the operator's own property inventory.
5. Sends only **hot** and **qualified** leads to a Telegram channel for a
   human to review and contact manually.

The agent **surfaces and organizes** demand. It never contacts anyone.

## 3. In scope (MVP)

- **Source:** Threads only, via the official Threads Keyword Search API.
- **Languages:** Indonesian + English keyword sets.
- **Geography:** BSD, Alam Sutera, Gading Serpong, Tangerang Selatan.
- Keyword-based public search, extraction, scoring, classification,
  deduplication, inventory matching, Telegram notification, SQLite storage,
  and a manual status workflow.

## 4. Explicitly out of scope (MVP)

- ❌ Instagram, Facebook, X, TikTok, or any non-Threads source.
- ❌ Any scraping, unofficial API, headless-browser harvesting, or private data.
- ❌ Reading private messages / DMs.
- ❌ Any automated reply, comment, follow, like, repost, quote, or DM.
- ❌ Contacting a lead automatically, ever.
- ❌ A web dashboard or UI (Telegram + SQLite only for now).
- ❌ Storing full post text long-term beyond what's needed for review (see policy).

## 5. Users & roles

| Role | Responsibility |
|------|----------------|
| **Human operator** | Approves leads, contacts people manually, manages inventory CSV, updates lead status. |
| **Hermes** | Plans, orchestrates, schedules scans, analyzes/reviews leads, reviews Codex output. |
| **Codex** | Builds the API connector, DB, scoring engine, matcher, Telegram notifier, tests, docs. |

## 6. MVP workflow (functional requirements)

1. **FR-1 Search** — Query the Threads Keyword Search API for an approved list of
   keyword × location combinations. `search_type=RECENT`, `media_type=TEXT`.
2. **FR-2 Extract** — From each returned post, extract: rental intent, desired
   location, property type, bedrooms, budget, move-in date, rental duration,
   special requirements, source URL, post timestamp. (See `LEAD_SCHEMA.md`.)
3. **FR-3 Classify** — Assign exactly one class: `hot_lead`, `qualified_lead`,
   `watch`, `irrelevant`, `agent_broker`, `spam`.
4. **FR-4 Score** — Compute a transparent 0–100 lead score with a stored,
   human-readable breakdown. (See `SCORING_RULES.md`.)
5. **FR-5 Deduplicate** — Never store or notify the same post twice; collapse
   repeat posts from the same author within a configurable window.
6. **FR-6 Match** — For qualified/hot leads, match requirements against a CSV or
   SQLite inventory and attach up to N matching listings.
7. **FR-7 Notify** — Send only `hot_lead` and `qualified_lead` items to Telegram,
   with score breakdown, extracted fields, matched inventory, and source link.
8. **FR-8 Store** — Persist minimal public lead metadata in SQLite.
9. **FR-9 Status workflow** — Support manual status transitions:
   `new → reviewed → contacted → responded → viewing_scheduled → converted | rejected`.
10. **FR-10 No auto-contact** — The system must have no code path that messages,
    replies to, or follows any Threads user.

## 7. Non-functional requirements

- **NFR-1 Compliance-first:** Only official APIs, only public content. Enforced in
  code and documented in `PRIVACY_AND_PLATFORM_POLICY.md`.
- **NFR-2 Rate-limit safe:** Stay well under the Threads limit of **2,200
  queries / rolling 24h per user** (shared across apps). Budget queries per scan.
- **NFR-3 Transparent scoring:** Every score must be explainable from stored rules.
- **NFR-4 Idempotent scans:** Re-running a scan produces no duplicate leads/alerts.
- **NFR-5 Secrets hygiene:** All tokens via environment / `.env`, never committed.
- **NFR-6 Testable:** Extraction, scoring, dedup, and matching run offline against
  the 20 synthetic posts with no network calls.
- **NFR-7 Small:** Single Python package, stdlib + a few well-known deps, one CLI.

## 8. Success criteria (MVP acceptance)

- Runs end-to-end offline on the 20 synthetic posts and produces correct
  classifications and scores matching `SCORING_RULES.md`.
- With live credentials, one `scan` run fetches public posts, stores leads, and
  posts a correctly formatted alert to a test Telegram channel.
- Zero code paths that write/reply/follow/DM on Threads (verified by review + grep test).
- Deduplication verified: a second scan over identical data adds 0 new leads and
  sends 0 new alerts.

## 9. Key constraints & risks (from API verification)

- ⚠️ **`threads_keyword_search` requires App Review approval.** Until approved,
  the endpoint only searches the authenticated user's **own** posts — so the
  synthetic-data path is the primary dev/test path until approval lands.
- ⚠️ **No location field** is returned by the API. Location must be inferred from
  post text + the search query location term (best-effort, confidence-scored).
- ⚠️ **No follower/engagement/geo data** is returned — scoring relies on text signals.
- ⚠️ Keyword-search results exclude the `owner` field; sensitive keywords return
  empty arrays.

## 10. Open questions for the operator

1. Which Telegram delivery target: a private channel, a group, or a DM to you?
2. Budget currency/threshold assumptions (assume IDR/month unless told otherwise)?
3. Do you already have a Meta app + Threads use case created, or should the
   credential-acquisition steps be part of delivery?
4. Inventory format preference: start with CSV (simplest) and migrate to SQLite?
