# PROJECT_HANDOFF.md — Rental Demand Signal Agent

**Milestone:** v0.2 — App Review prep (checkpoint; reviewer demo build approved)
**Date:** 2026-07-13
**Final commit:** `e5a7619`
**Git tag:** `v0.2-app-review-prep` (annotated, points at `e5a7619`)
**Test status:** ✅ 13 passed, 0 failed (fully offline)
**Compliance:** ✅ read-only on Threads; no auto-contact; verified by test + codebase grep

> **Note on tags:** `v0.1-synthetic-mvp` (`f2b27d8`) is the frozen core MVP.
> `v0.2-app-review-prep` (`e5a7619`) adds the handoff, real-inventory RUNBOOK, and
> the Meta App Review package. The approved Streamlit **reviewer demo** is built on
> a dedicated branch after this tag (see §8).

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

Apify is the primary live provider and is off by default. Use `rdsa scan --source apify --dry-run` after setting `APIFY_LIVE_ENABLED=true` and `APIFY_API_TOKEN`. The OfficialThreadsProvider remains retained and disabled. The usage guard warns at $4.00 and stops at $4.75, with state in `data/apify_usage.json`.

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
| `config.py` | Env/.env, keywords, locations, thresholds, query budget, paths |
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
python -m pytest -q            # 13 passed
```

| Test file | Covers |
|-----------|--------|
| `test_core.py` | Worked example (score 100) + all 20 fixtures → correct class |
| `test_scoring_rules.py` | R3 relative vs numeric budget; band thresholds (bound to config); no hidden hot gate |
| `test_dedup.py` | Same post_id → 1 lead; same-author near-dup throttled/alerted once |
| `test_matcher.py` | Inventory match on core fields; no-match case |
| `test_query_planner.py` | Query budget respected; no duplicate queries |
| `test_http.py` | Threads client is GET-only; Telegram targets configured group |
| `test_no_write_paths.py` | **Compliance guard** — no Threads write/reply/follow/DM/publish |

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

- **No live data yet** — default and only fully-exercised path is `--source synthetic`.
- **Location inferred from text** — the Threads API returns no geo/location field,
  so `desired_location` is best-effort (with a confidence score).
- **Rules-based extraction** — regex/keyword driven; robust on the synthetic set,
  will need tuning on real-world phrasing (see `RUNBOOK.md` for the tuning loop).
- **No follower/engagement signals** — API doesn't return them; scoring is text-only.
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

## 9. Next milestone (in progress)

1. **Streamlit reviewer demo** — *approved*. A minimal, read-only App Review surface
   (Connect Threads · Keyword · Location · Run Search · Results · Classification/
   score · Matches) built on a dedicated branch, gated behind `THREADS_LIVE_ENABLED=false`.
   Synthetic mode works without credentials; no write/contact endpoints. (STEP 2–4.)
2. **Real-inventory dry-run** — operator supplies sanitized `inventory_real.csv`;
   still pending input. See `RUNBOOK.md`.
3. **After approval** — enable live mode, then (separately) schedule scans via a
   Hermes cron. **Not built yet, by instruction.**

## 10. Run commands

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
git checkout v0.2-app-review-prep      # detached HEAD at App Review prep (documents + demo build)
git checkout v0.1-synthetic-mvp        # detached HEAD at the frozen core MVP
# destructive reset of a branch:
git reset --hard v0.2-app-review-prep
```
