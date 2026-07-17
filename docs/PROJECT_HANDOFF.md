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

### 8.10. v0.6.1 dashboard runtime + legacy-data fix (merged)

Two operator-facing defects from v0.6, fixed on `fix/v061-dashboard-runtime-and-legacy-data`
and merged as `v0.6.1-dashboard-runtime-fix`.

**Defect 1 — dashboard needed `PYTHONPATH` set manually.** Real-browser launch from a
fresh shell raised `ModuleNotFoundError: No module named 'dashboard'` because Streamlit
adds only `dashboard/` to `sys.path`, not the repo root; the package-relative imports
(`from dashboard.common`, `from rdsa...`) therefore failed unless `PYTHONPATH` pointed at
the repo root.

- **Why HTTP 200 alone failed to catch it:** Streamlit's bootstrap itself imports fine
  and the headless server returns HTTP 200 even when the *page script* later fails to
  import its modules — the error surfaces only as a Streamlit error box / traceback in the
  browser, not in the HTTP status. A bare `curl` is therefore insufficient; pages must be
  opened in a real browser (or imported as modules in a `PYTHONPATH`-unset subprocess) to
  detect it.
- **Permanent fix:** `dashboard/app.py` inserts the repo root into `sys.path` before any
  `from dashboard...`/`from rdsa...` import (one deterministic bootstrap; pages inherit the
  process-global path). `dashboard/__init__.py` added; `pyproject.toml` declares
  `[tool.setuptools.packages.find]` (`rdsa*`, `dashboard*`) so `pip install -e .` also works.
  Verified: `streamlit run dashboard/app.py` boots with `PYTHONPATH` unset; all six pages
  import and render without `ModuleNotFoundError`.

**Defect 2 — historical synthetic `INV001`–`INV010` shown as active matches.** 14 leads in
`data/rdsa.sqlite3` carry `matched_inventory` with `INVxxx` IDs from pre-real-inventory runs.
They rendered in the Overview Lead Snapshot and Matching Review as if current recommendations.

- **Treatment:** `normalize_matches` loads the real inventory ID set
  (`APT-GS-MTOWN-1BR-001`, `HSE-SS-FEDORA-2P1-001`, `KSK-BSD-INTERMODA-001`) and marks any
  `property_id` outside it as `is_legacy=True` with note
  "Legacy synthetic match — not an active inventory recommendation", re-typed to
  `legacy_synthetic`. Legacy items are excluded from `get_overview`/`get_matching_groups`
  active totals; Overview's Lead Snapshot now shows only active IDs and "No active real
  inventory match" for legacy-only leads. Lead Detail / Matching Review show the same
  message. **No historical `leads`/`matched_inventory` rows are rewritten and the `alerts`
  (Telegram) table is never touched** — auditability preserved.
- `get_inventory()` still returns only the 3 real rows; no synthetic fallback introduced.

**Test additions (`tests/test_dashboard_runtime_and_legacy.py`, 94 tests total):** fresh
`PYTHONPATH`-unset subprocess import of app + every page; real `streamlit run` boot asserting
HTTP 200 and no traceback/ModuleNotFoundError; legacy marking/exclusion; real-only inventory;
Overview snapshot active-label behavior; no `apify_provider`/`TelegramNotifier`/`requests`/
`send_lead_cards` imports.

**Corrected browser acceptance method:** launch from a fresh terminal with `PYTHONPATH`
unset, open each page in a real browser, confirm visible content + no Streamlit error box
(do not rely on HTTP 200 alone). Kill any prior Streamlit processes first — a stale server
can serve pre-fix code and mask the fix.


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

### 8.10. v0.6.2 dashboard UX & visual design refresh (merged)

UI/UX-only milestone. The 6-page Streamlit dashboard was redesigned into a polished
dark real-estate intelligence surface. **No scoring, matching, budget parsing, delivery,
Apify, Telegram, or database-source logic was changed.**

- **UX objectives:** clear hierarchy, readable typography, consistent spacing, no raw
  default-Streamlit look, no excessive horizontal scroll; accessible dark/light contrast.
- **Design system:** `dashboard/theme.py` single CSS source (dark navy/charcoal; teal =
  confirmed/healthy, amber = tentative/confirm-required, red = error/serious-warning,
  muted gray = legacy/historical); consistent radius/borders/shadows.
- **Pages/components added:** `dashboard/theme.py`, `dashboard/components.py` (KPI card,
  badges, score bar, area chip, table wrapper w/ empty+loading states), `dashboard/formatters.py`
  (sanitize, currency/period, labels, legacy detection), `dashboard/charts.py` (Altair chart
  builders). All six pages rebuilt: branded Overview (header + KPI strip + funnel/distribution/
  cost charts + recent high-priority leads), CRM Lead Inbox (search, quick chips, filters, sort,
  preview, sanitized CSV export), structured Lead Detail (summary / score explanation / source /
  match cards / workflow+audit, read-only Telegram history), Inventory property cards + table
  (real records only), Matching Review tabs (Exact / Nearby / Tentative / No match / Legacy
  historical, side-by-side comparison), Pilot Analytics (per-run + cumulative charts, no
  false-positive rate claimed).
- **Altair decision:** Plotly is **not installed and cannot be installed offline** (no network,
  no local wheel/cache). Charts use Streamlit-bundled **Altair** (`st.altair_chart`) — fully
  interactive (hover/zoom). `plotly` was intentionally kept out of `pyproject.toml`.
- **Standalone page import fix (this release):** the v0.6.1 `sys.path` bootstrap lived only in
  `app.py`; deep-linking a page URL (`/Overview`) ran the page module before that fix was in
  scope and raised `ModuleNotFoundError: No module named 'dashboard'`. Added `dashboard/_bootstrap.py`
  and import it first in all six page files, so every page loads standalone with `PYTHONPATH` unset.
  Verified by direct browser deep-link to all six page URLs (HTTP 200, no traceback).
- **Browser acceptance (fresh server, PYTHONPATH unset):** all six pages render without
  traceback at 1366×768 and 1920×1080; KPIs/charts/tables correct; exact/nearby/tentative/legacy
  visually distinct; no raw `INVxxx` shown as active matches; status-update workflow still requires
  confirmation and still creates an audit entry (verified via controlled update + restore); Telegram
  history and source text unchanged by the update.
- **Security boundaries:** no Apify execution path, no Telegram send path, no scan/send buttons,
  no token / `.env` / private chat-ID shown, no synthetic inventory fallback; repository writes
  remain limited to lead status / notes / reviewed_at / audit. The v0.6.1 import fix is intact
  (and now also per-page). Altair introduces no remote-data/network dependency.

### 8.11. v0.6.3 delivery, newness & classifier hardening (offline, merged)

Offline hardening milestone triggered by Run #5, where an already-alerted lead was re-delivered
to Telegram and an agent/broker "client cari" post was mis-classified as `hot_lead`. No live calls,
no DB wipe, no inventory change.

**Run #5 duplicate — root cause.** Delivery used a non-atomic pattern: a pre-send `SELECT`
(`already_sent`) followed by a post-send `INSERT OR IGNORE` (`mark_alert`). The unique-constraint
"claim" happened only *after* the Telegram network call, so a duplicate send could occur and was
then masked (the `alerts` table stayed at 3 rows despite a reported `sent:1`). The fix makes the
claim atomic and happen *before* the network call.

**Atomic pre-send claim (`rdsa/db.py`).** New `delivery_claims(post_id, channel UNIQUE, status,
claimed_at, sent_at, message_id, error)` table. `connect()` idempotently backfills `delivery_claims`
from historical `alerts` (`status='sent'`) so legacy deliveries block future claims.
`claim_delivery(post_id)` does `INSERT OR IGNORE … ('pending', now)` and returns `rowcount == 1`
(claimed) vs `0` (already claimed/sent/failed → fail closed). `complete_delivery` sets `sent` +
`sent_at` + `message_id`; `fail_delivery` sets `failed` + `error` (auditable, never auto-retries).
**`send_lead_cards` (notifier.py) now claims before sending** — if the claim fails, Telegram is
never called. The old `already_sent → send → mark_alert` sequence is no longer reachable.

**Current-run newness (`cli.py` / `notifier.py`).** `process_raw` returns `new_post_ids` (post_ids
actually INSERTed this run; `upsert_lead` returns its `INSERT OR IGNORE` rowcount, so a
`last_seen`-only refresh is NOT new). Delivery eligibility = `preview_eligible` AND post_id ∈
`new_post_ids`. A lead merely refreshed is never delivered again. When zero new eligible leads
exist, no card is sent; an optional concise run summary is sent only with `--summary`
(`allow_summary`), default off.

**Agent/broker classification (`classifier.py` / `scoring_config.py`).** New
`THIRD_PARTY_DEMAND_SIGNALS` (contextual phrases: `ada client cari`, `client saya mencari`,
`untuk klien`, `mencarikan unit`, `butuh listing`, `titipan client`, `co-broke`/`cobroke`,
`broker`, `agen properti`, `saya lagi ada client cari`, …). Detected *before* ordinary renter
scoring; fires `agent_broker` with `classifier_reason="third_party_demand: <cue>"`, even when
intent/location/type/budget are explicit. `GENUINE_SEEKER_CONTROLS` (`untuk saya sendiri`,
`saya dan keluarga`, `untuk ditempati`, `untuk kami`, `buat saya`) keep first-person seekers
eligible. `agent_broker` is never Telegram-eligible.

**Budget-period parsing (`budget_parser.py`).** Added explicit Indonesian/English forms:
yearly `/thn`, `/tahun`, `per thn`, `per tahun`, `setahun`, `tahunan`, `/yr`, `per year`, `annual`;
monthly `/bln`, `/bulan`, `per bln`, `per bulan`, `sebulan`, `bulanan`, `/mo`, `per month`,
`monthly`. `50jt/thn` → IDR 50,000,000 yearly with monthly equivalent; `2,5jt/bln` → IDR 2,500,000
monthly; bare `900` → low confidence, no invented amount.

**Structured bedrooms (`extractor.py` / `Lead`).** New fields `bedroom_min/max`, `bedroom_options`,
`studio_acceptable`, `bedroom_confidence`, `bedroom_raw`. `parse_bedrooms` preserves alternatives
(`studio/2KT` → options `[0,2]`, studio accepted) and ranges (`1–2 kamar` → min 1 max 2; `minimal`/
`maksimal`); the legacy `bedrooms` is set only for an exact single requirement, never an invented
value. Low-confidence bedroom data cannot produce an exact match.

**Dashboard KPI (`dashboard_repository.py` / `common.py`).** Renamed "Cost / useful lead" to
**"Cost per contacted lead"** = cumulative Apify cost ÷ leads at `contacted` status or beyond
(no `worth_contacting` field exists; used an existing explicit workflow-status denominator rather
than inventing one). Caption clarifies it is not a conversion rate. When the denominator is zero,
the KPI shows **"Not available"** (never 0 or infinity).

**Tests.** `tests/test_v063_hardening.py` (44 tests): canonical post_id, newness/rowcount,
atomic claim conflict → 0 Telegram calls, historical alert backfill blocks claim, failed-delivery
auditability, Run #1/Run #5 duplicate prevented, third-party phrases, genuine-seeker controls,
yearly/monthly parsing, structured bedrooms, KPI denominator + zero-state, and no-live-call safety.
`test_telegram_delivery.py` updated to the new default-no-summary behavior. Full suite: **150 passed**.

**Offline Run #5 reprocess (`3940755375813528375`, read-only).** Old `hot_lead`/90, budget `unknown`,
`bedrooms=1`. Reprocessed: `agent_broker`/82, cue `ada client cari`, budget `year` (monthly eq
4.17M), bedrooms `min=1,max=2,opts=[0,1,2],studio=True`. Not Telegram-eligible. Historical alert
(message_id 17) backfills a `sent` claim → `claim_delivery` returns False → zero Telegram calls.
Historical records were not modified.

### 8.12. v0.6.4 offering / supply-side classifier hardening (offline, merged)

Follow-up to Run #7, where post `3914314253977235827` (an owner **offering** "buka opsi untuk
jual / sewakan unit apartment di BSD") was misclassified `qualified_lead`/72 and Telegram-delivered
(message ID 25), then rejected on manual review. No live calls, no DB wipe, no inventory change.

**Defect.** The classifier caught third-party *sourcing* (`THIRD_PARTY_DEMAND_SIGNALS`) but had no
supply-side / offering detection for an **owner advertising their own unit**. An offering post with
no "client" cue fell through to the `seeking` branch → `qualified_lead`.

**Fix (`rdsa/classifier.py` + `rdsa/scoring_config.py`).**
- `OFFERING_SIGNALS`: contextual offering phrases (`disewakan`, `saya ada unit`, `unit available`,
  `direct owner`, `harga sewa`, `dm untuk detail`, `menerima titip`, `agent/broker listing`,
  `buka opsi`, `under market price`, …).
- `LISTING_STRUCTURE_SIGNALS`: specs + price + facility + availability + contact + listing-URL +
  marketing language; several co-occurring ⇒ listing even without an explicit verb.
- `STRONG_OFFERING` (classifier-local) now includes `harga sewa` so an asking price triggers supply
  classification (the price-amount guard in `_unit_price_contact` stays).
- `classify` detects offering/supply-side **before** demand: `is_offering = strong or
  (offering_cue and structure_score ≥ 3)`. Supply-side with no genuine-seeker control ⇒
  `agent_broker` (reason `offering_supply: <cue>`); with a genuine control ⇒ ambiguous (kept
  eligible, reason `ambiguous_offering_seeker`). Discussion/questions that mention only a bare verb
  (e.g. "ada yang tahu apartemen yang disewakan?") are NOT listings.
- `BROKER_SIGNALS` (English `for rent`, `contact us`, `many units`, `wa admin`) re-fed into the
  offering/agent detection so English listings (synthetic post `4013`) stay `agent_broker` — this
  was a regression risk when the old `BROKER_SIGNALS` branch was replaced.

**Priority:** supply-side > third-party sourcing > genuine seeker. Agent/broker posts (both
sourcing and offering) are never Telegram-eligible. No new `supply_listing` class was introduced —
`agent_broker` is reused to avoid schema/dashboard changes.

**Tests.** `tests/test_v064_offering_classifier.py` (25 tests): supply-side phrases, agent
third-party, genuine seekers, ambiguous/discussion controls, the Run #7 post reprocess, and no
regression to v0.6.3 third-party controls. Full suite: **175 passed** (150 + 25).

**Offline reprocess (`3914314253977235827`, read-only).** Old `qualified_lead`/72 (eligible, was
delivered) → new `agent_broker`/~40 (reason `offering_supply: sewakan`), Telegram-ineligible, zero
cards. Historical delivery claim (message ID 25) and `alerts`/`delivery_claims` rows unchanged.

### 8.13. v0.7 daily scheduler foundation (built, offline-validated, merged)

Safe, **read-only-by-default** daily-scheduler foundation. It ships the scheduler
engine, CLI controls, a read-only dashboard page, and Windows Task Scheduler scripts
— but **does NOT activate any schedule and installs no Windows task**.

**Defaults (all OFF — nothing runs or sends automatically):**
- `RDSA_SCHEDULER_ENABLED=false` (the run refuses unless explicitly `true`)
- `RDSA_SCHEDULER_SEND_ENABLED=false` (delivery suppressed even when a run executes)
- `APIFY_LIVE_ENABLED=false` (no live Apify; gated behind preflight + in-process flag)
- `RDSA_TELEGRAM_SEND_ENABLED=false` (no Telegram send)
- A scheduled run additionally requires the explicit `--confirm-scheduled-run` flag;
  without it the CLI refuses.

**What is built (`rdsa/scheduler.py` + `rdsa/cli.py`):**
- `run_scheduled_run(trigger_type, send_enabled_override)`: acquires the process lock,
  records a run-ledger row (`scheduled_runs` table), validates inventory, checks the
  projected-cost hard stop, runs the real `process_raw` pipeline (extract→score→classify
  →dedup→persist→atomic delivery claim), sends ≤3 cards only when sending is enabled,
  then **restores flags and releases the lock** on completion **or** error.
- **Process-lock behavior:** a `scheduler_lock` row blocks concurrent runs
  (`blocked_lock`); a normal run releases its lock on completion/error. Stale locks are
  **not** auto-deleted — inspect with `scheduler-status`, clear only explicitly via
  `scheduler-unlock --confirm-unlock` and never while a process is alive.
- **Run-ledger behavior:** every run writes a row with status
  `completed` / `completed_no_new_leads` / `completed_no_eligible_leads` /
  `blocked_cost_limit` / `blocked_lock` / `failed` (with `error_code` +
  redacted `sanitized_error`). Historical `leads`/`alerts`/`delivery_claims` are never
  modified by a run.
- **Projected-cost hard stop:** projected monthly usage = current monthly + configured
  max run cost; the run aborts **before Apify** if projected exceeds `APIFY_STOP_USD`.
  Warning threshold logs only.
- **No automatic paid retry:** an Apify/provider failure records a `failed`/`apify_error`
  ledger row and returns — no retry loop.
- **No automatic Telegram retry:** a Telegram failure leaves the lead persisted and the
  delivery claim marked `failed` (auditable); `send_lead_cards` already claimed before
  the network call, so no duplicate send and no retry.

**CLI:** `scheduler-status` (read-only), `scheduler-unlock --confirm-unlock`
(confirm-gated), `scheduled-run --confirm-scheduled-run` (refuses unless scheduler
enabled + confirmed).

**Dashboard:** `dashboard/pages/7_Scheduler.py` is **read-only observability** — shows
code readiness, the four flags, cost posture, process lock, latest/last-successful run.
**No run / install / unlock / send / enable buttons** are exposed.

**Windows Task Scheduler scripts (`scripts/`):** `windows_scheduler_preview.ps1`
(no-op preview), `_install.ps1` (`-ConfirmInstall`, **Disabled by default**, `-Enable`
opt-in), `_disable.ps1` (`-ConfirmDisable`), `_remove.ps1` (`-ConfirmRemove`),
`_status.ps1`. All pass only `--confirm-scheduled-run` in the task action — **no token,
chat-id, or secret is embedded**; the task name `RentalDemandSignalAgent-Daily` is
consistent across all five. These are operator-run out-of-band; **v0.7 ships none of
them installed.**

**Manual activation procedure (operator, post-release):**
1. Set `RDSA_SCHEDULER_ENABLED=true` in `.env` (add `RDSA_SCHEDULER_SEND_ENABLED=true`
   only when delivery is wanted).
2. Preview, then install Disabled: `pwsh scripts/windows_scheduler_install.ps1
   -ConfirmInstall -TriggerMode Daily -At "08:30"`.
3. Enable only after a successful canary review (`-Enable`).
4. Verify with `windows_scheduler_status.ps1`.

**Windows process cleanup note (Streamlit review/demo):**
Stopping the parent shell/wrapper may not stop the child `python -m
streamlit.web.bootstrap` process. Operators should verify the listening port
(`Get-NetTCPConnection -LocalPort <port>`) and terminate the actual child process
(`taskkill /PID <pid> /F`) when necessary.

**Tests:** PHASE 10 `tests/test_scheduler.py` (33), PHASE 11 `tests/test_scheduler_canary.py`
(5, mocks-only offline canaries), plus a `dashboard_repository` flag-coercion regression
test. Full suite: **214 passed** (PYTHONPATH unset). Two PHASE 12 blocking defects found
and fixed: `windows_scheduler_preview.ps1` parse error; dashboard `Apify live` flag showed
`"on"` because `bool("false")` is `True` (now uses the truthy helper, consistent with the
live-gating logic).

**Rollback tag:** `v0.7-daily-scheduler-foundation`.

### 8.14. v0.7.2 Windows canary launcher (merged, offline-validated)

The Windows canary launcher hardening is merged and tagged as
`v0.7.2-windows-canary-launcher`. It changes only the Windows launcher path; scheduler
business logic is unchanged.

**Trigger mapping:** PowerShell-facing `ScheduledCanary` maps to CLI
`scheduled_canary`; PowerShell-facing `Daily` maps to CLI `daily_schedule`. Preview and
install print both the user-facing mode and mapped CLI value.

**Task action:** preview/install generate an absolute `powershell.exe` action invoking
the absolute `scripts/windows_scheduler_run.ps1` launcher. The action passes the mapped
CLI trigger and `-ConfirmRun`; it does not store a bare Python executable, token, chat
ID, `.env` value, or other secret.

**Process-local safety:** the launcher resolves `<RepoRoot>\\.venv\\Scripts\\python.exe`
and sets `RDSA_SCHEDULER_ENABLED=true` only in the launcher/child process. Scheduled
sending defaults to `false`; `-EnableScheduledSend` is the separate explicit opt-in.
Prior process values are restored in `finally`; `.env`, user-scope environment, and
machine-scope environment are not modified.

The existing installed `RentalDemandSignalAgent-Daily` task remains disabled and keeps
its old action until it is separately reinstalled or updated. This release did not
update, enable, or run that task.

With both scheduler flags false, the direct `scheduled-run` CLI path safely refuses
before lock/ledger work, makes zero Apify or Telegram calls, performs no database
mutation, and currently exits `0` with the Scheduler disabled refusal.

**Verification:** targeted launcher tests: **19 passed, 1 expected environmental skip**;
full suite: **233 passed, 1 expected environmental skip**; all four PowerShell scripts
parse successfully. No live Apify or Telegram calls were made.

**Rollback tag:** `v0.7.1-windows-launcher-hardening`.

### 8.15. v0.7.3 scheduler quality hardening (offline; merged via fix/v073-scheduler-quality-hardening)

Source fixes for four defects surfaced by the Run #9 ScheduledCanary (`sch-20260717T020147Z-6a5956e5`,
4 new leads). Offline-verified against the production DB (read-only reprocess); no Apify/Telegram, no
historical record mutation, no DB wipe.

**A. Genuine-seeker classifier precedence.** A first-person family/school seeker was misclassified
`agent_broker` because `STRONG_OFFERING` matched the bare substring `harga sewa` (no amount). Fix:
`GENUINE_SEEKER_HOUSEHOLD` (anak/sekolah/lama nyari/rumah kecil context) recognises genuine demand;
`STRONG_LISTING_SIGNALS` + `_has_strong_listing_proof()` define real listing proof (bare `harga sewa`
without an amount is **not** proof); when `rental_intent != "offering"` and there is no strong proof, an
ambiguous offering-form word is overridden to a seeker (`genuine_seeker_override` / `_low_score`). A real
listing with strong proof still stays `agent_broker`. `dikontrakkan`/`dikontrakin` added to `STRONG_OFFERING`.

**B. Rent-aware budget extraction.** `23m` was read as IDR 23M; `IPL 285rb` was folded into the rent;
`25 juta/tahun` was not separated from monthly. `budget_parser.py` rewritten to be role-aware: per-line
label detection (area / IPL / deposit / rent / service); dimension/area exclusion (`23m`, `12mtr`,
`3 x 5m` near `luas`/`uk.`/`kamar` are never money); IPL/service/deposit tagged as **separate** non-rent
charges; explicit `a-b <unit>` range matcher; primary rent selected by period (yearly stored natively).
New `BudgetResult` fields: `role`, `rent_figure`, `area_text`, `candidates`, `normalized_note`.

**C. `classifier_reason` persistence.** The value was computed but dropped (the `Lead` dataclass lacked
the field, so `to_dict`/`asdict` omitted it and the SQLite INSERT used a fixed column list). Added
`classifier_reason: str | None = None` to `Lead`; `to_dict` serialises it; `upsert_lead` writes it. The
UPSERT refreshes only `last_seen` on conflict, so a meaningful existing reason is never clobbered with `NULL`.

**D. Scheduled-run → lead provenance.** Leads could only be linked to a run via timestamp reconstruction
of `last_seen`. New `scheduled_run_leads(run_id, post_id, inserted_this_run, classification, eligible,
created_at, PRIMARY KEY(run_id, post_id))`, created idempotently on `connect()` and via `migrate_provenance`.
`associate_run_leads(c, run_id, associations)` records **every** processed lead (new + already-existing)
per run; composite PK makes it idempotent (`INSERT OR IGNORE`). `leads_for_run` / `new_post_ids_for_run`
recover the exact association with no timestamp reconstruction. No secrets or raw text stored.

**Offline reprocess (read-only):**
- `3829775294010720778`: `agent_broker`/`NULL` → **`watch`** / `genuine_seeker_override: harga sewa`
- `3941710706454887314`: budget `23M–285k / month` → budget **`25,000,000 / year`** (23m→area, IPL excluded)
- `3934246864783171346`: budget `NULL` → **`1,300,000 / month`** (`Rp.` parsed, high)
- `3933861953134938990`: reason `NULL` → reason persisted

**Tests:** `tests/test_v073_quality_hardening.py` (classifier precedence, budget roles, `classifier_reason`
persistence, provenance). Full suite **251 passed, 1 skipped** (symlink-privilege `test_venv_python_preferred`,
environment-bound). `git diff --check` clean.

**Rollback tag:** `v0.7.3-scheduler-quality-hardening` (annotated, points at the `--no-ff` merge of
`fix/v073-scheduler-quality-hardening` into `main`).

### 8.16. v0.7.4 interrupted-run recovery (offline; merged via fix/v074-interrupted-run-recovery)

Triggered by Run #10 (`sch-20260717T042351Z-a0dbee12`), which was terminated by the OS at
`status=starting`. The child process was gone, no lock row existed at the time, yet the ledger row had
**no terminal state** — an orphaned `starting` row. No Apify/Telegram, no historical record mutation,
no DB wipe, no retry of Run #10.

**Orphaned `starting`-ledger risk.** A scheduled run that dies OS-side between `INSERT` and its
terminal `UPDATE` leaves a non-terminal row with no completed/failed status. Prior detection had no
way to distinguish "still running" from "died mid-run," so such a row would silently block nothing and
never be resolved — and a naive age-only check could wrongly flag a healthy in-flight run.

**Explicit terminal status.** New auditable `interrupted` status (`config.RUN_STATUS_INTERRUPTED`).
It is terminal (in `is_terminal_status`) and is never treated as `completed`, never eligible for
automatic retry. Non-terminal set: `starting, preflight, actor_started, actor_completed, persistence,
delivery, cleanup`.

**Progress metadata (idempotent).** New ledger columns `current_phase`, `heartbeat_at`,
`interruption_reason` (added via `migrate_ledger` ALTER-if-not-exists, and tolerated when absent on
pre-patch production schemas). `update_run_progress()` writes `current_phase` + `heartbeat_at` at every
major stage of `run_scheduled_run` (`starting → preflight → actor_started → actor_completed →
persistence → delivery → cleanup`) without touching `finished_at` or any secret/provider response.

**Interruption-candidate rules (`detect_interrupted_runs`).** A run qualifies as an interruption
candidate **only if ALL hold**:
1. status ∈ non-terminal set;
2. recorded `process_id` is **not** alive (`_pid_alive` false);
3. **no active matching lock** belongs to it (lock absent, or the lock's run_id ≠ this run, or the
   lock's PID is dead → stale, not active);
4. started_at is **older than the conservative grace period** (`RDSA_SCHEDULER_INTERRUPTION_GRACE_SECONDS`,
   default 3600).

We **never** infer interruption from age alone, and **never** flag a run whose process is alive or whose
lock is active. Terminal/resolved rows (`completed`, `failed`, `blocked_*`, `refused`, `interrupted`)
are never candidates.

**Fail-closed gate (gate 0 in `run_scheduled_run`).** Before any Apify call **and before** acquiring a
fresh lock, if `detect_interrupted_runs` returns any candidate, the run refuses with an explicit
message naming the unresolved run(s) and the `scheduler-reconcile` command. This forces operator
reconciliation and prevents auto-retrying an interrupted Actor attempt. No Apify/Telegram is called.

**Explicit reconciliation command.**
```bash
python -m rdsa.cli scheduler-reconcile --run-id <RUN_ID> --confirm-reconcile
```
Requirements enforced by `reconcile_run`:
- explicit `--confirm-reconcile` required (missing → refusal, no mutation);
- verifies the recorded PID is dead (`_pid_alive` false);
- verifies no active matching lock belongs to the run;
- refuses if already terminal (`completed`/`failed`/`interrupted` → idempotent no-op) or if process
  alive/lock active;
- records `finished_at` + `interrupted` terminal status + a **sanitized** reason (token/path-stripped);
- **never** touches `leads`/`alerts`/`delivery_claims`/cost data;
- **never** calls Apify or Telegram;
- **idempotent** — a second call on an already-reconciled run reports no mutation.

**No automatic retry.** The interrupted Actor attempt is never re-attempted automatically; recovery is a
manual, confirmed operator action only.

**Scheduler blocking while unresolved runs exist.** A new scheduled run is blocked before Apify until all
non-terminal historical runs are explicitly reconciled (or otherwise resolved).

**Dashboard read-only observability.** `dashboard_repository.get_interrupted_runs()` returns, for each
interrupted/qualifying run: `run_id`, `status`, `current_phase`, `heartbeat_at`, `started_at`,
`reconciliation` (`required` or `completed`), and a sanitized `interruption_reason`. The Scheduler page
(`dashboard/pages/7_Scheduler.py`) renders this as a new read-only panel. **No reconcile / run / enable /
unlock / send button is exposed** — reconciliation remains an explicit CLI operator action only.

**Run #10 status.** During v0.7.4 inspection it was `status=starting`, `current_phase=None`
(recorded before this patch), `heartbeat_at=None`, `process_id=27332` (**dead**), with a stale
`runtime/scheduler.lock` referencing this run_id but whose PID is dead → treated as a stale (not
active) lock. As of inspection the run was ~105 min old (past the 1-hour grace) so it **qualified** as
an interruption candidate. Reconciliation would change only `status → interrupted`, `finished_at →
<now>`, `interruption_reason → <sanitized>`; leads (127), alerts (3), delivery_claims (7) untouched.
**Run #10 was subsequently reconciled out-of-band** via the explicit confirmed command
`python -m rdsa.cli scheduler-reconcile --run-id sch-20260717T042351Z-a0dbee12 --confirm-reconcile` →
`status=interrupted`, `finished_at=2026-07-17T06:20:42.405249+00:00`, `idempotent=false`, **no retry,
no Apify/Telegram call**, only the `scheduled_runs` terminal fields changed. **Run #10 is now CLOSED**
as `interrupted` (see `docs/PILOT_LOG.md`).

**Tests.** `tests/test_v074_interrupted_run_recovery.py` (25): dead-PID/no-lock/past-grace candidate;
live-PID refusal; active-lock refusal; age-alone insufficient; missing-confirmation refusal; explicit
reconciliation → `interrupted`; second reconciliation no-mutation; completed-run refusal; active
process/lock refusal; reconciliation never calls Apify/Telegram; historical leads/alerts/claims/costs
unchanged; reason sanitized; new scheduled run blocked while unresolved; dashboard required/completed
display; read-only `scheduler-status`; idempotent migration; pre-patch-schema (missing columns)
compatibility. `tests/test_dashboard_repository.py` hardened to isolate the lock. Full suite
**276 passed, 1 skipped** (env-bound symlink test). `git diff --check` clean.

**Rollback tag:** `v0.7.4-interrupted-run-recovery` (annotated, points at the `--no-ff` merge of
`fix/v074-interrupted-run-recovery` into `main`).

## 11. Rollback

Safe tags exist:
```bash
git checkout v0.6.4-offering-classifier-hardening   # detached HEAD at merged offering/supply hardening
git checkout v0.7-daily-scheduler-foundation   # detached HEAD at merged v0.7 scheduler foundation
git checkout v0.7.1-windows-launcher-hardening # detached HEAD at v0.7.1 launcher hardening
git checkout v0.7.3-scheduler-quality-hardening # detached HEAD at merged v0.7.3 scheduler quality hardening
git checkout v0.7.4-interrupted-run-recovery # detached HEAD at merged v0.7.4 interrupted-run recovery
git checkout v0.6.3-delivery-classifier-hardening   # detached HEAD at merged hardening
git checkout v0.6.2-dashboard-ux-refresh      # detached HEAD at merged UX/visual refresh
git checkout v0.6.1-dashboard-runtime-fix     # detached HEAD at merged runtime + legacy-data fix

git checkout v0.5.1-matching-hardening      # detached HEAD at matching-quality hardening
git checkout v0.5-private-telegram-pilot   # detached HEAD at merged private Telegram pilot
git checkout v0.4-operational-pilot       # detached HEAD at operational pilot (persistence, preview)
git checkout v0.3-apify-provider          # detached HEAD at merged Apify live provider
git checkout v0.2-app-review-prep         # detached HEAD at App Review prep (documents + demo build)
git checkout v0.1-synthetic-mvp           # detached HEAD at the frozen core MVP
# destructive reset of a branch:
git reset --hard v0.3-apify-provider
```
