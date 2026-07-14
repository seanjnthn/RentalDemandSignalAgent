# PROJECT_HANDOFF.md — Rental Demand Signal Agent

**Milestone:** v0.3 — Apify live provider MERGED (live-validated)
**Date:** 2026-07-13
**Final commit:** `f87d90c` (merge of `feature/apify-provider`)
**Git tag:** `v0.3-apify-provider` (annotated)
**Test status:** ✅ 44 passed, 0 failed (incl. live-validated mocked + controlled canaries)
**Compliance:** ✅ read-only on Apify + Threads; no auto-contact; verified by tests + grep

> **Tags:** `v0.1-synthetic-mvp` (frozen core) · `v0.2-app-review-prep` (docs + Meta review
> package + reviewer-demo build) · `v0.3-apify-provider` (Apify primary live source, merged).

---

## 1. What this is

A compliant AI agent that finds **public** Threads posts from people looking to
rent in the Greater Serpong / South Tangerang area, extracts their requirements,
scores + classifies each as a lead, matches qualified leads to a property
inventory, and sends only hot/qualified leads to a Telegram **group** for a human
to review and contact manually. It never contacts anyone automatically.

At v0.1 the entire pipeline runs **offline against synthetic data**. Live Threads
search is implemented but gated behind Meta App Review (see §7).

## 2. Current architecture

### Live data providers

**Apify is the primary live provider** (actor `automation-lab/threads-scraper`, REST,
normalized to `automation-lab~threads-scraper`). It is **off by default**
(`APIFY_LIVE_ENABLED=false`). Use `rdsa scan --source apify --dry-run` after setting
`APIFY_LIVE_ENABLED=true` and `APIFY_API_TOKEN`.

Key properties (validated live 2026-07-13):
- **Batched search:** one Actor run accepts `searchQueries: [...]` (multiple seeds) —
  this maximizes recall and minimizes runs/cost. The CLI loops per configured query,
  but the controlled canary proved a single batched run works and is preferred.
- **Preflight health check** before any paid run (`GET /acts/{id}` → 200/401/403/404).
- **Cost guard:** reads actual `usageTotalUsd` per run; warns at **$3.75**, stops at
  **$4.25**; state in `data/apify_usage.json` (git-ignored). `maxTotalChargeUsd` is
  sent as a query param (enforced cap, default $0.10).
- **Normalization:** Actor fields (`postId/text/url/username/timestamp` + 26 others)
  map into the Lead schema; epoch int/ms `timestamp` is converted to ISO-8601.
- **OfficialThreadsProvider** (`threads_client.py`) remains retained and disabled
  (gated on Meta App Review).

```bash
# Example live canary (one batched run, capped):
#   POST /acts/automation-lab~threads-scraper/runs?token=***&maxTotalChargeUsd=0.10
#   body: {"mode":"search","searchQueries":["apartemen","rumah sewa","kontrakan"],"maxPosts":5}
```

```
CLI (rdsa ...)
  init-db · scan · list · status · match · notify · reprocess · purge
        │
 source │ synthetic (data/synthetic_posts.json)  ── default, offline
        │ threads   (read-only GET keyword_search) ── gated on App Review
        ▼
 ingest/dedup → extractor → scorer(v1.1) + classifier → matcher(CSV) → SQLite
        │                                                                  │
        └───────────────── notifier (send-only Telegram, hot+qualified) ──┘
```

Full detail in `docs/ARCHITECTURE.md`. Data contracts in `docs/LEAD_SCHEMA.md`.

### Modules (`rdsa/`)

| Module | Responsibility |
|--------|----------------|
| `apify_provider.py` | **Primary live provider** — REST adapter for `automation-lab/threads-scraper`: batched search, preflight, normalized→Lead, cost guard (actual `usageTotalUsd`), read-only |
| `config.py` | Env/.env, keywords, locations, thresholds, query budget, paths, Apify config |
| `threads_client.py` | **Read-only** wrapper over `GET /v1.0/keyword_search` (GET only) |
| `query_planner.py` | Build keyword×location queries; enforce per-run query budget |
| `ingest.py` | Normalize posts, dedup hash, skip seen IDs, throttle author repeats |
| `extractor.py` | Extract intent, location, type, bedrooms, budget (+period), dates, duration, requirements |
| `scoring_config.py` | Single source of tunable weights/thresholds/signal lists (`score_version` v1.1) |
| `scorer.py` | Transparent additive 0–100 score + `{rule,points,reason}` breakdown |
| `classifier.py` | 6-class logic (spam/broker/offering signals first, then score bands) |
| `matcher.py` | Match hot/qualified leads to CSV inventory on location+type+bedrooms+budget |
| `db.py` | SQLite schema + CRUD (leads, authors, alerts, status_history, inventory, scan_runs) |
| `notifier.py` | **Send-only** Telegram `sendMessage` to configured group |
| `cli.py` | Pipeline orchestration + subcommands |

## 3. Implemented features

- ✅ Read-only Threads keyword-search client (stubbed/mocked; live path ready, gated)
- ✅ Keyword × location query planning with a per-run budget (rate-limit safe)
- ✅ Bilingual (ID/EN) extraction: intent, location(+confidence), property type,
  bedrooms, budget (min/max, IDR, variable period), move-in, duration, requirements
- ✅ Transparent scoring **v1.1** (hot ≥85, qualified ≥60, watch ≥35) with stored breakdown
- ✅ 6-class classification: hot_lead, qualified_lead, watch, irrelevant, agent_broker, spam
- ✅ Deduplication by post_id + normalized-text hash + same-author throttle
- ✅ Inventory matching against CSV
- ✅ SQLite persistence of minimal public metadata
- ✅ Telegram alert cards (send-only, hot+qualified) with `--dry-run` preview
- ✅ Manual status workflow: new→reviewed→contacted→responded→viewing_scheduled→converted|rejected
- ✅ Idempotent scans (re-run adds 0 leads, sends 0 alerts)

## 4. Tests & commands

**Run the suite** (offline, no credentials):
```bash
cd ~/rental-demand-signal-agent
python -m pytest -q            # 44 passed
```

| Test file | Covers |
|-----------|--------|
| `test_core.py` | Worked example (score 100) + all 20 fixtures → correct class |
| `test_scoring_rules.py` | R3 relative vs numeric budget; band thresholds (bound to config); no hidden hot gate |
| `test_dedup.py` | Same post_id → 1 lead; same-author near-dup throttled/alerted once |
| `test_matcher.py` | Inventory match on core fields; no-match case |
| `test_query_planner.py` | Query budget respected; no duplicate queries |
| `test_http.py` | Threads client is GET-only; Telegram targets configured group |
| `test_no_write_paths.py` | **Compliance guard** — no Threads/Apify write/reply/follow/DM/publish |
| `test_apify_*.py` (6) | Actor-ID `~`/`/`/numeric normalization, preflight 200/401/403/404, token redaction, budget guard, normalize (incl. epoch-timestamp), mocked search + controlled end-to-end canary |

**Run the pipeline (offline synthetic, dry-run — no Telegram send):**
```bash
export RDSA_DB_PATH=data/dev.sqlite3
python -m rdsa.cli init-db
python -m rdsa.cli scan --source synthetic --dry-run
python -m rdsa.cli list --class hot_lead
python -m rdsa.cli status 4001 reviewed
```

**Dependencies:** `requests>=2.31`, `python-dotenv>=1.0` (runtime); `pytest>=8` (test).
Python 3.11+. SQLite via stdlib.

## 5. Known limitations

- **Live Apify data is now exercised** (validated 2026-07-13: 15 real posts, $0.07/run).
  Default/offline path remains `--source synthetic`.
- **Location inferred from text** — the actor returns no geo/location field, so
  `desired_location` is best-effort (with a confidence score). Broad seed queries
  maximize recall; target-area filtering happens downstream.
- **Rules-based extraction** — regex/keyword driven; robust on synthetic + live
  samples, will need tuning on real-world phrasing (see `RUNBOOK.md` for the tuning loop).
- **No follower/engagement signals** — actor returns like/reply counts but scoring is
  currently text-only (counts available for future signals).
- **CSV inventory only** — SQLite inventory table exists in schema but matcher reads CSV.
- **No dashboard** — CLI + Telegram only, by design.

## 6. Compliance posture (enforced)

- Threads client is **GET-only**; `test_no_write_paths.py` greps the codebase to
  assert no reply/follow/DM/publish/`.post(`/`.put(`/`.delete(` paths to Threads.
- The only outbound-message component is the Telegram notifier → operator's group.
- Official API only, public content only, Threads only. Full policy:
  `docs/PRIVACY_AND_PLATFORM_POLICY.md`.

## 7. Live-use blocker

**`threads_keyword_search` requires Meta App Review approval + a published app.**
Until approved, the endpoint returns only the authenticated user's *own* posts —
no public search. The operator currently has a Threads account only (no Meta app).
Unblocking requires the STEP 3 App Review package (done — see `docs/review/`) and
operator action in the Meta App Dashboard. **No live call has been made.**

## 8. Completed work (to v0.2-app-review-prep)

- STEP 1 — Frozen MVP: full suite green, compliance verified, `v0.1-synthetic-mvp` tag.
- STEP 2 — Real-inventory dry-run guide (`RUNBOOK.md`) + `scripts/validate_inventory.py`
  (PII-reject, canonical→matcher schema adapter) + `data/inventory_template.csv`.
- STEP 3 — Meta App Review package: `META_APP_REVIEW_CHECKLIST.md`,
  `PERMISSION_JUSTIFICATION.md`, `REVIEWER_INSTRUCTIONS.md`, `PRIVACY_POLICY_DRAFT.md`,
  `DATA_DELETION_INSTRUCTIONS.md`, `SCREEN_RECORDING_SCRIPT.md`, `LIVE_SMOKE_TEST_PLAN.md`,
  `REVIEWER_UI_ASSESSMENT.md`.

## 8.5. Completed work — v0.3-apify-provider (2026-07-13, MERGED to master)

- **Apify primary live provider** (`rdsa/apify_provider.py`): batched `searchQueries`
  input, `preflight()` health check before any paid run, `normalize()` → Lead schema
  (incl. epoch int/ms `timestamp` → ISO-8601), `MonthlyUsageGuard` reading actual
  `usageTotalUsd` (warn $3.75 / stop $4.25), `maxTotalChargeUsd` as query param.
- **Actor-ID robustness:** `owner/name` → `owner~name` (REST), numeric IDs unchanged,
  malformed → config error; default config stays human-readable `automation-lab/threads-scraper`.
- **CLI:** `rdsa scan --source apify` reuses the shared `process_raw` pipeline
  (extract→score→classify→dedup→match→Telegram-card preview); `OfficialThreadsProvider`
  retained + disabled.
- **Tests:** 6 `test_apify_*.py` files (normalization, preflight 200/401/403/404, token
  redaction, budget guard, mocked search, controlled end-to-end canary) + epoch-timestamp
  normalize tests. Suite: **44 passed**.
- **Live validation (controlled canaries, token never printed):**
  - Broad single query `"apartemen"` → 3 real posts, $0.02.
  - **Batched run** `searchQueries:["apartemen","rumah sewa","kontrakan"]`, maxPosts=5 →
    **15 real posts** (5/5/4), **1 Actor run**, **$0.07**, 0 duplicates, classified
    qualified:2 / watch:6 / agent_broker:2 / irrelevant:5. Pipeline finished without error.
  - Found + fixed a real bug: actor returns `timestamp` as an epoch **integer** → crash
    in scorer; now normalized to ISO-8601 (offline test added).
- **Compliance:** read-only (Apify GET + dataset fetch only); no reply/follow/DM/publish;
  token in git-ignored `.env`, never logged/committed.

### 8.6. v0.4 operational pilot (built, live-validated; operator-gated next steps)

The pilot adds validated operator-supplied real inventory support, SQLite lead
persistence, a manual `rdsa pilot-scan` using one batched Apify run, and Telegram
**preview cards only** (no sending).

- **Real inventory** (`rdsa/inventory.py`): validates the 11 required columns, rejects
  duplicate `property_id`, excludes non-`available` rows, normalizes area aliases
  (BSD/BSD City, Alam Sutera/Alsut, Gading Serpong/GS, Tangerang Selatan/Tangsel),
  and rejects PII-like rows. `data/inventory_real.csv` is git-ignored and must be
  supplied by the operator; if absent, live matching is disabled and previews show
  `Inventory matches: Not configured`.
- **Persistence** (`rdsa/db.py`): `leads` gains `provider`, `first_seen`, `last_seen`;
  `INSERT OR IGNORE` preserves manual `status`/`notes` on re-scan; near-duplicate text
  → status `duplicate`; status transitions include `negotiating`/`duplicate`; 
  `purge_old_leads(days)` retention (default 90d) deletes only rejected/duplicate/
  irrelevant leads past the cutoff.
- **Manual command** `rdsa pilot-scan`: requires `APIFY_LIVE_ENABLED=true`; runs ONE
  batched Actor run (`searchQueries:["apartemen","rumah sewa","kontrakan","sewa apartemen"]`,
  maxPosts=5, maxTotal=20, `maxTotalChargeUsd=0.10`); persists to SQLite; prints preview
  cards for hot/qualified leads only — **no Telegram send, no contact, no scheduler**.
- **Tests:** `test_inventory_real.py` (validation/aliases/PII/exclusion/dup/empty),
  `test_lead_persistence.py` (dedup/manual-status-preservation/retention),
  `test_telegram_preview.py` (eligibility + sanitization), `test_pilot_scan_mock.py`,
  `test_inventory_mode.py` (8 safety cases). Suite: **58 passed**.
- **Production-safety fixes (after pilot):** synthetic inventory NEVER used in live
  mode; `RDSA_INVENTORY_MODE=real|synthetic|none` (default `real`); if real file absent
  in live mode → empty inventory, matching disabled, warning once per run, previews show
  `"Inventory matches: Not configured"` (no synthetic IDs leak). `pilot-scan` reports
  CURRENT-run metrics separately from CUMULATIVE DB metrics, and CURRENT-run
  `usageTotalUsd` separately from MONTHLY accumulated cost (with warn/stop thresholds +
  remaining budget; `maxTotalChargeUsD` is a per-run cap; monthly may include earlier
  canaries). Evaluation wording is honest ("False-positive rate not yet established.").
- **Live validation (controlled regression, token never printed):** real file absent +
  `INVENTORY_MODE=real` → 20 raw posts, 14 new leads, 6 duplicates, **0 inventory
  matches**, warning once, "Not configured" previews, `current_run_usage_usd=0.095` vs
  `monthly_accumulated_usd=0.222`; no synthetic IDs; no Telegram send; no contact.
- **Live validation (controlled manual pilot, token never printed):** one batched run
  → 20 raw posts → **19 leads persisted**, 1 duplicate, 4 hot/qualified preview cards
  in spec format; monthly cost accumulator ~$0.12 (single run well under $0.10 cap).
  Found + fixed a real bug: `search_batched` polling used a fixed 30-iter loop (≈1.5s)
  that timed out on real runs → now polls until the `timeout` deadline.
- **Compliance:** read-only Apify GET + dataset fetch; preview only, no `.send()` in
  pilot path; token git-ignored, never logged/committed.

**Operator next steps (not built, by instruction):** place sanitized
`data/inventory_real.csv`; enable live; *separately* decide on scheduling (cron) and
Telegram sending. Do not auto-contact leads.

Operational pilot safety fix: `RDSA_INVENTORY_MODE=real` is the default, and live
scans never use synthetic inventory. Missing or empty real inventory disables
matching and preview cards show `Inventory matches: Not configured`; synthetic IDs
cannot leak into live previews. Current-scan metrics are separate from cumulative
database metrics, and cost output separates current Actor `usageTotalUsd` from
monthly accumulated usage, warn/stop thresholds, and remaining budget. Evaluation

### 8.7. v0.5 private Telegram pilot (built, live-validated, pre-merge fix applied)

The private delivery pilot is fully built and **live-validated**:
- **Telegram canary** (`telegram-test --confirm-send`): one sanitized test message
  delivered to the approved private chat (id withheld), message id recorded, send
  flag restored to false. Confirmed no other chat contacted, no Apify/Threads call.
- **Live pilot** (`pilot-send --confirm-send`): one batched Apify Actor run
  (`apartemen`/`rumah sewa`/`kontrakan`/`sewa apartemen`, maxPosts=5), 20 raw posts →
  11 new leads persisted, 1 eligible (qualified_lead) → **1 Telegram card sent**
  (≤3 cap), `current_run_usage_usd=0.095`, monthly accumulated ~$0.33 (well under
  stop $4.75). No synthetic IDs; real-inventory matching returned 0 matches (lead
  budget/location didn't align with the 3 real units). Duplicate-send prevention via
  the SQLite `alerts` UNIQUE(post_id); `message_id` stored.

Controls (all verified in the live runs): `telegram-test` and `pilot-send` require
`--confirm-send` + `RDSA_TELEGRAM_SEND_ENABLED=true` + configured `TELEGRAM_ALLOWED_CHAT_ID`;
token is git-ignored and redacted from all errors/logs; delivery limited to 3 eligible
cards/run; failures are redacted and do NOT mark leads sent or corrupt the DB; no
scheduler, auto-contact, DM, publish, or dashboard.

**Pre-merge budget-parser fix (this milestone):** `rdsa/budget_parser.py` normalizes
Indonesian budgets with confidence: `rb`/`ribu`/`k` ×1,000; `jt`/`juta`/`m`/`million`
×1,000,000; ranges ("3-4 juta" → 3M–4M); yearly→monthly equivalent; Indonesian decimal
commas/thousands separators. A **bare number without magnitude/context** (e.g. "900") is
NOT turned into 900 IDR — it returns `confidence=low`, amounts `None`. Scoring rule R3
awards budget points **only** when confidence is medium/high AND the amount is within a
plausible rental range (`config.BUDGET_PLAUSIBLE_MIN/MAX`); matcher ignores low-confidence
budgets; Telegram shows `Budget: unclear — review original post` for low confidence,
`Inventory matches: No suitable unit found` when configured inventory has zero matches,
and `Inventory matches: Not configured` only when inventory is absent/disabled.

**Offline reprocess of the canary lead** (`3940738558332110361`, "budget below RM900"):
old parse `budget_max=900` → score 62 / `qualified_lead`; new parse `None/None`,
`confidence=low` → score 47 / `watch`. The defect is corrected; classification no longer
inflated by an ambiguous number. Reprocess was read-only; no resend, no alert-history
mutation.

Current safety defaults: `APIFY_LIVE_ENABLED=false`, `RDSA_TELEGRAM_SEND_ENABLED=false`,
no cron/scheduler. Suite: **70 passed**.




1. **Streamlit reviewer demo** — *approved*. A minimal, read-only App Review surface
   (Connect Threads · Keyword · Location · Run Search · Results · Classification/
   score · Matches) built on a dedicated branch, gated behind `THREADS_LIVE_ENABLED=false`.
   Synthetic mode works without credentials; no write/contact endpoints. (STEP 2–4.)
2. **Real-inventory dry-run** — operator supplies sanitized `inventory_real.csv`;
   still pending input. See `RUNBOOK.md`.
3. **After approval** — enable live mode, then (separately) schedule scans via a
   Hermes cron. **Not built yet, by instruction.**

### 8.8. v0.5.1 matching-quality hardening (offline)

- Matching returns structured `property_id`, `match_type`, `score`, `reasons`, and `warnings` fields. Tiers are `exact_match`, `nearby_alternative`, `tentative_match`, and `no_match`; only exact and explicitly configured nearby candidates are confirmed for display.
- Areas are canonicalized to BSD, Gading Serpong, Alam Sutera, Suvarna Sutera, or Tangerang Selatan. BSD and Gading Serpong remain distinct; the configurable nearby map contains only the explicit BSD/Gading Serpong pair.
- Unknown location and unknown budget period cannot produce an exact match. Medium-confidence budgets remain tentative; budget comparisons use matching periods or explicit conversion.
- `matched_inventory` persists the actual structured match list and normalizes legacy `[null]`/`[None]` values to `[]` on read/write. Historical `alerts` rows are not rewritten.
- Current-scan metrics report extracted target-area leads, exact/nearby/tentative/no-match counts, and unknown-location leads. Pilot-send no longer prints cards before the single render/send path.

### 8.9. v0.6 operational lead dashboard (merged)

The v0.6.1 runtime/data fix adds a deterministic repo-root import bootstrap to
`dashboard/app.py`, so operators no longer need to set `PYTHONPATH` before
running `streamlit run dashboard/app.py`; `dashboard` and `rdsa` are also
declared as installable packages. Historical `INVxxx` synthetic matches remain
stored for auditability and are labeled as legacy, but are excluded from active
exact/nearby/tentative/no-match metrics and groups. Legacy-only leads display
“No active real inventory match”; the three real inventory IDs remain active.

Local, read-only-by-default Streamlit review interface. No Apify/Threads/Telegram
calls, no cron, no author contact, no `.env` changes, no synthetic inventory.

- **Pages:** Overview (KPIs + filters), Lead Inbox (sortable/filterable table), Lead
  Detail (editable status/notes/reviewed_at only), Inventory (real CSV viewer +
  validation), Matching Review (grouped by match tier, nearby/tentative visually
  distinct), Pilot Analytics (per-run metrics from DB + `PILOT_LOG.md`).
- **Service layer:** `rdsa/dashboard_repository.py` — all DB access, parameterized
  queries, legacy `[null]` match normalization, audit logging. UI never writes SQL.
- **Writes allowlisted:** `leads.status`, `leads.notes`, `leads.reviewed_at`; audit
  row in `status_history` with `source='dashboard'`. Schema migrated lazily/idempotently.
- **Security:** token/chat-id/Apify never rendered; phone/email sanitized; no
  `send_lead_cards`/`TelegramNotifier`/`apify_provider`/`requests`/synthetic paths in
  dashboard code (static-checked). Alert history never modified.
- **Acceptance review:** all six pages passed; controlled status→reviewed→restore
  update created an audit entry and left Telegram history unchanged. Two blocking
  cost-parser defects found and fixed:
  1. Overview `apify_cost` always $0.000 (read a non-existent `runs` list); now reads
     `actual_usd`/`estimated_usd` → cumulative ~$0.74.
  2. Pilot Analytics cost-per-run showed $4.75 (the stop threshold) via a greedy regex;
     now anchored to `usageTotalUsd` → runs #1–#4 parse $0.095.
  `PILOT_LOG.md` Runs #3/#4 normalized to the standard metric labels using only
  recorded values (no invented/threshold-derived figures).
- **Read/write boundaries:** dashboard reads leads/inventory/alerts/usage; writes only
  status/notes/reviewed_at + audit. No production scoring, matching, or delivery logic
  is invoked or modified by the dashboard.
- **Safety defaults:** `APIFY_LIVE_ENABLED=false`, `RDSA_TELEGRAM_SEND_ENABLED=false`, no
  cron, no recurring send, no Apify/Telegram buttons.



```bash
cd ~/rental-demand-signal-agent
python -m pip install -e .[test]        # install + dev deps
python -m pytest -q                     # 13 passed, offline

# Offline synthetic pipeline (dry-run, no Telegram send):
export RDSA_DB_PATH=data/dev.sqlite3
python -m rdsa.cli init-db
python -m rdsa.cli scan --source synthetic --dry-run
python -m rdsa.cli list --class hot_lead
python -m rdsa.cli status 4001 reviewed

# Reviewer demo (after STEP 2-4 build), Synthetic mode by default:
streamlit run app_review_demo.py        # or: python -m rdsa.app_review_demo
```

## 11. Rollback

Two safe tags exist:
```bash
git checkout v0.6-operational-dashboard      # detached HEAD at merged operational dashboard
git checkout v0.5.1-matching-hardening      # detached HEAD at matching-quality hardening
git checkout v0.5-private-telegram-pilot   # detached HEAD at merged private Telegram pilot
git checkout v0.4-operational-pilot       # detached HEAD at operational pilot (persistence, preview)
git checkout v0.3-apify-provider          # detached HEAD at merged Apify live provider
git checkout v0.2-app-review-prep         # detached HEAD at App Review prep (documents + demo build)
git checkout v0.1-synthetic-mvp           # detached HEAD at the frozen core MVP
# destructive reset of a branch:
git reset --hard v0.3-apify-provider
```
