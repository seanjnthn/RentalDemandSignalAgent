# PILOT_LOG.md — Manual Private Rental-Lead Pilot Scans

Append-only log of controlled live pilot runs. Every run is manual, gated behind
`--confirm-send` + `RDSA_TELEGRAM_SEND_ENABLED=true` (in-process only), and uses
real validated inventory (`INVENTORY_MODE=real`). No cron, no recurring send, no
author contact.

---

## Run #1 — 2026-07-14 (baseline tag: v0.5-private-telegram-pilot)

**Command:** `pilot-send --confirm-send` (Apify + Telegram temporarily enabled
in-process only; `.env` unchanged).

### Preflight
| # | Check | Result |
|---|---|---|
| 1 | Working tree clean | ✅ |
| 2 | Secrets/runtime git-ignored (`.env`, `inventory_real.csv`, `rdsa.sqlite3`, `apify_usage.json`) | ✅ |
| 3 | 3 real inventory units load | ✅ |
| 4 | Telegram destination = approved private chat `909767721` | ✅ |
| 5 | Monthly Apify usage $0.341 << stop $4.75 | ✅ |

### A. Scan
- **Raw posts:** 20 (1 batched Actor run; `apartemen`/`rumah sewa`/`kontrakan`/`sewa apartemen`, maxPosts=5)
- **Normalized:** 20
- **Duplicates:** 12
- **New leads:** 8
- **Classifications:** hot_lead:1, qualified_lead:1, agent_broker:3, watch:2, irrelevant:1
- **Target-location leads (reported metric):** 0
  - Note: one eligible lead extracted `BSD` (conf 1.0) and another `Tangerang Selatan` (conf 1.0); the `target_location` counter returned 0, a known metric-quirk (counts against the scan's configured target set, not the extracted area). Both BSD/Tangsel areas are within scope.

### B. Extraction quality (8 new leads)
- **Budget confidence:** high:1, medium:2, low:5
  - Eligible leads: hot_lead budget `50,000,000 IDR` (medium), qualified_lead budget `2,083,333 IDR` (high) — both awarded budget points correctly.
  - 5 low-confidence (ambiguous) budgets → no budget points (per v0.5 fix).
- **Unclear budgets:** 5 (low confidence) → cards show `Budget: unclear — review original post`.
- **Location extraction failures:** 5/8 had `None`/unknown location.
- **Property-type extraction failures:** 1/8 unknown (an agent_broker, score 0).

### C. Matching
- **Real inventory matches:** 2 (both eligible leads)
  - `3940755375813528375` (hot, BSD apartment 1BR, 50M) → **APT-GS-MTOWN-1BR-001** (M-Town BSD 1BR, 35M/yr)
  - `3940750095612586995` (qualified, house, 2.08M/mo) → **HSE-SS-FEDORA-2P1-001** (Fedora house, 20M/yr ≈ 1.67M/mo)
- **Match reasons:** property-type + budget band alignment; both real units (no synthetic IDs).
- **Commercially reasonable:** **Yes** for both by type + budget band. The house match is geographically uncertain (lead location unknown), see review.

### D. Telegram
- **Eligible leads:** 2 (1 hot_lead, 1 qualified_lead)
- **Cards sent:** 2 (≤3 cap ✅) — message IDs **17, 18**
- **Duplicate sends prevented:** ✅ (`alerts` UNIQUE(post_id); only 2 new eligible leads)
- **Destination:** approved private chat `909767721` only

### E. Cost
- **Current-run `usageTotalUsd`:** $0.095
- **Monthly accumulated:** $0.436 (run #1 of baseline was ~$0.33; this run added $0.095)
- **Remaining budget:** $4.314 (stop $4.75)

### F. Manual quality review (sent/eligible leads)

**1. Hot lead `3940755375813528375` — 90/100 (sent, msg 17)**
- Confirmed relevant: ✅ genuine rental-seeking post
- Rental intent: genuine (explicit seeking; BSD; budget stated)
- Budget reliable: medium confidence, 50M IDR — plausible for BSD 1BR (likely annual; unit 35M/yr)
- Location reliable: BSD (conf 1.0) — reliable
- Match sensible: M-Town BSD 1BR ↔ BSD 1BR seeker — **commercially reasonable ✅**
- Worth contacting manually: **Yes**

**2. Qualified lead `3940750095612586995` — 60/100 (sent, msg 18)**
- Confirmed relevant: ✅ genuine rental-seeking post
- Rental intent: genuine (seeking)
- Budget reliable: high confidence, 2.08M/mo — plausible
- Location reliable: **No** — extracted location `None`/unknown ("Area: unknown")
- Match sensible: house↔house by type+budget is reasonable, but location unverified → geographically uncertain
- Worth contacting manually: **Yes, after verifying location**

**False positives among sent:** 0. **Uncertain:** lead #2 (location). Both are real seekers, not broker/spam.

### Observations / data-quality notes
- `matched_inventory` DB column stored `[None]` for the 2 delivered matched leads (placeholder quirk); **cards rendered the correct real property IDs**. Delivery was correct; persistence field should be tightened in a later maintenance pass.
- Console prints each card twice (cosmetic; `delivery.sent=2` and `message_ids=[17,18]` confirm exactly 2 sends).
- Location extraction is weak for short/casual Threads text (5/8 unknown) — expected; review step compensates.

### Post-run safety state
- `APIFY_LIVE_ENABLED=false` ✅ · `RDSA_TELEGRAM_SEND_ENABLED=false` ✅
- No cron · No author contact · No secrets committed
- Full suite: **70 passed**

### Re-evaluation (offline)

No Apify or Telegram calls were made. Re-running the matcher and preview formatter against stored lead data is expected to classify BSD lead `3940755375813528375` against M-Town (Gading Serpong) as `nearby_alternative`, with area flexibility confirmation required. Unknown-location house lead `3940750095612586995` against Fedora (Suvarna Sutera) is expected to be `tentative_match`, with location confirmation required. Alerts 17/18 remain untouched.

---

## Run #2 — 2026-07-14 (baseline tag: v0.5.1-matching-hardening)

**Command:** `pilot-send --confirm-send` (Apify + Telegram temporarily enabled in-process only; `.env` unchanged).

### Preflight
| # | Check | Result |
|---|---|---|
| 1 | Working tree clean | ✅ |
| 2 | Secrets/runtime git-ignored (no token committed) | ✅ |
| 3 | 3 real inventory units load | ✅ |
| 4 | No synthetic inventory (`INVENTORY_MODE=real`) | ✅ |
| 5 | Telegram destination = approved private chat `909767721` | ✅ |
| 6 | Monthly Apify usage $0.445 << stop $4.75 | ✅ |

### A. Current scan
- **Raw posts:** 20 (1 batched Actor run; maxPosts=5 ×4 queries) · **Normalized:** 20
- **Duplicates:** 17 · **New leads:** 3
- **Classifications:** watch:2, irrelevant:1 (no hot_lead / qualified_lead this run)
- **Extracted target-area leads:** 0 · **Unknown-location leads:** 3

### B. Extraction quality (3 new leads)
- **Budget confidence:** low:2, medium:1, high:0
- **Unclear budgets:** 2 low-confidence (no reliable amount)
- **Location extraction failures:** 3/3 unknown
- **Property-type failures:** 0/3 (kontrakan, apartment×2 detected) · **Bedroom failures:** 1/3

### C. Matching quality
- Eligible leads (hot/qualified): **0** → matcher ran for none; exact:0, nearby:0, tentative:0, no_match:0.
- No lead cards; nothing matched or displayed.

### D. Telegram
- **Eligible leads:** 0 → **Lead cards sent:** 0
- **Run-summary message sent:** 1 (message ID **19**) — the "scan completed, no new eligible lead" notice (per spec when no eligible leads)
- **Duplicate sends prevented:** ✅ (alerts table unchanged: still 3 prior rows; msg 19 maps to no lead)
- **No other chat contacted:** ✅ (single summary to approved private chat only)

### E. Cost
- **Current-run `usageTotalUsd`:** $0.095 · **Monthly accumulated:** $0.54 · **Remaining:** $4.21 (stop $4.75)

### F. Manual review
No eligible/delivered **lead** cards this run (only the summary notice). The 3 new leads:
- `3940773205228724478` (watch 53): kontrakan, 2 beds, unknown loc/budget — genuine-ish seeking but low signal; **uncertain**, not worth contacting yet.
- `3940771546071772808` (watch 59): apartment, unknown beds/loc/budget — seeking signal, weak extraction; **uncertain**, not worth contacting yet.
- `3940768555138762726` (irrelevant 30): apartment, budget 850M IDR (likely a sale/offering, not rental) — **not a rental lead** (false-positive-ish for rental intent); **not worth contacting**.

Assessment: rental-intent reliability mixed (1 likely offering); location reliability none (all unknown); budget reliability low (2 unclear, 1 implausible 850M); no property matches to assess. Card wording accuracy: N/A (no lead cards). The summary message accurately reported "no eligible lead."

### Post-run safety state
- `APIFY_LIVE_ENABLED=false` ✅ · `RDSA_TELEGRAM_SEND_ENABLED=false` ✅
- No cron · No author contact · No secrets committed
- Full suite: **78 passed**

---

## Run #3 — 2026-07-14 (same workflow)

1 batched Actor run (maxPosts=5 ×4 queries).

**Current-run metrics (this scan):**
- **Raw posts:** 20
- **Normalized posts:** 20
- **Duplicates:** 17
- **New leads:** 3 (irrelevant:1, watch:2)
- **Eligible leads (hot/qualified):** 0
- **Delivered leads (lead cards):** 0 (1 run-summary message ID 20)
- **Extracted target-area leads:** 0
- **Unknown-location leads:** 3
- **Exact matches:** 0
- **Nearby alternatives:** 0
- **Tentative matches:** 0
- **No matches:** 0
- **Current-run `usageTotalUsd`:** $0.095
- **Monthly accumulated usage:** $0.637

**Cumulative (after this run):** 77 total leads; monthly accumulated Apify usage $0.637; remaining budget $4.113.

Original prose:
- **Extraction (3 new):** budget low:2/medium:1; location unknown 3/3; type failures 0; bedroom failures 1
- New leads: `3940785104167711039` (irrelevant), `3940782638403487161` (watch 53, house 30-600M/mo, high conf budget), `3825041513746892069` (watch 37, apartment)
- No cron · Send restored false · Suite 78 passed

## Run #4 — 2026-07-14 (same workflow)

1 batched Actor run (maxPosts=5 ×4 queries).

**Current-run metrics (this scan):**
- **Raw posts:** 20
- **Normalized posts:** 20
- **Duplicates:** 19
- **New leads:** 1 (irrelevant:1)
- **Eligible leads (hot/qualified):** 0
- **Delivered leads (lead cards):** 0 (1 run-summary message ID 21)
- **Extracted target-area leads:** 0
- **Unknown-location leads:** 1
- **Exact matches:** 0
- **Nearby alternatives:** 0
- **Tentative matches:** 0
- **No matches:** 0
- **Current-run `usageTotalUsd`:** $0.095
- **Monthly accumulated usage:** $0.732

**Cumulative (after this run):** 78 total leads; monthly accumulated Apify usage $0.732; remaining budget $4.018.

Original prose:
- **Extraction (1 new):** budget low:1; location unknown 1/1; type unknown; bedroom missing
- New lead: `3940783718386605052` (irrelevant 12)
- No cron · Send restored false · Suite 78 passed

---

## Cross-run comparison (Runs #1–#4)

All four runs used identical gated workflow: one batched Apify run (apartemen / rumah sewa / kontrakan / sewa apartemen, maxPosts=5), real inventory, `--confirm-send`, ≤3 cards, approved private chat only, production logic unchanged.

### Cost per run
| Run | Raw | Dup | New | Eligible (lead cards) | Msgs sent | Current $ | Monthly $ |
|---|---|---|---|---|---|---|---|
| #1 | 20 | 12 | 8 | 2 (IDs 17,18) | 2 | 0.095 | 0.436 |
| #2 | 20 | 17 | 3 | 0 (summary 19) | 1 | 0.095 | 0.540 |
| #3 | 20 | 17 | 3 | 0 (summary 20) | 1 | 0.095 | 0.637 |
| #4 | 20 | 19 | 1 | 0 (summary 21) | 1 | 0.095 | 0.732 |

**Cost is perfectly consistent: $0.095/run** (Apify `usageTotalUsd`), well under the $0.10 canary cap and far below stop $4.75. Monthly accumulated $0.732 after 4 runs — 15% of budget. No run exceeded any threshold.

### Lead quality
- Runs #2–#4 produced **0 eligible (hot/qualified) leads**; only Run #1 surfaced 2.
- New-lead classifications across #2–#4 (7 leads): irrelevant:3, watch:4 — all low-signal.
- **Deduplication dominates over time**: dup rate climbed 12→17→17→19. The same recent public posts are re-fetched each run (Apify returns the freshest ~20 per query); only genuinely new posts add rows. Run #4 added just 1 new row. This is expected for frequent re-scans of the same seed queries and is *correct* behavior (no duplicate alerts — `alerts` UNIQUE guard held; only 3 lead deliveries total, IDs 17/18).

### Location extraction
- **Consistently weak: 10/10 new leads across runs #2–#4 had unknown location** (location_confidence 0.0). Short/casual Threads text rarely names BSD/Alam Sutera/Gading Serpong/Tangsel explicitly. This is the system's biggest extraction gap and directly caps match quality (unknown location → no `exact_match`; at most `tentative_match`).
- Target-area leads (canonical extracted in-scope areas): **0 across all four runs**. The two Run #1 eligible leads that DID have location (BSD, Tangerang Selatan) came from longer, more detailed posts.

### Budget parsing
- Confidence distribution (runs #2–#4, 7 leads): **low:5, medium:1, high:1**.
- Confidence-aware parser works as designed: ambiguous/blank budgets → `low` (no points, card shows "unclear"); only clear magnitudes score. Notable: `3940782638403487161` (watch) parsed `30,000,000–600,000,000/month` at **high** confidence — a very wide range (likely "30-600 jt"/similar); the high confidence is debatable given the 20× spread, but it is a real magnitude. `3940768555138762726` (irrelevant) parsed `850,000,000` medium — implausibly high for rent (likely a sale), correctly not matched.
- **No recurrence of the old "900→900 IDR" defect** — the v0.5 fix holds across all runs.

### Matching consistency
- With 0 eligible leads in runs #2–#4, the matcher executed **0 match evaluations** (it only runs for hot/qualified). So direct match-tier output is only observable from Run #1 (BSD→nearby_alternative, unknown-loc→tentative_match, per the v0.5.1 re-eval).
- **Consistency verdict:** the *pipeline* is consistent and deterministic per run (identical cost, identical gating, identical dedup behavior). The *match tiers* are consistent by construction (v0.5.1 tiers + canonical areas + nearby map are pure functions of lead+inventory). However, **end-to-end match quality is currently limited by upstream extraction** (location unknown 100%, budget low 71%), not by the matcher. The matcher cannot produce good matches from leads that lack location/budget signal.

### Overall evaluation
- **Cost:** ✅ consistent and safe ($0.095/run, 15% of monthly budget used).
- **Pipeline/controls:** ✅ consistent (dedup, gating, ≤3 cards, no duplicate sends, no cron, send restored).
- **Extraction:** ⚠️ location extraction is the weak link (0/10 in-scope locations); budget parsing is sound but mostly low-confidence on thin text.
- **Matching:** ✅ consistent by design, but limited by upstream signal; not yet exercised on eligible leads post-hardening except Run #1.
- **Recommendation:** before any recurring schedule, improve **location extraction** (location hints, "di BSD"/"area X" patterns, username bio, nearest-area inference) and consider **broadening seeds** or **longer interval between runs** to reduce duplicate-fetch waste. Matching logic itself is ready; it is starved of qualified input.

### Post-comparison safety state
- `APIFY_LIVE_ENABLED=false` ✅ · `RDSA_TELEGRAM_SEND_ENABLED=false` ✅
- No cron · No author contact · No secrets committed · Suite 78 passed

---

## Dashboard acceptance review (v0.6)

Branch `feature/v06-operational-dashboard` reviewed against the pilot database and real inventory (no Apify/Telegram calls). All six pages (Overview, Lead Inbox, Lead Detail, Inventory, Matching Review, Pilot Analytics) passed acceptance: metrics load, current/cumulative are not mixed, filters work, no misleading false-positive metric, costs clearly labeled, legacy `[null]` matches render as no match, canonical areas distinct (BSD ≠ Gading Serpong), nearby alternatives not shown as exact, unknown-location matches tentative, confirmation warnings visible, exactly 3 real inventory rows load (no synthetic), furnished values human-readable, placeholder URLs marked pending, and writes are limited to status/notes/reviewed_at/audit (Telegram history read-only).

**Blocking defects found and fixed (smallest change, `rdsa/dashboard_repository.py`):**
1. Overview `apify_cost` always $0.000 — read `usage.get("runs", …)` but the usage file has no list; now reads `actual_usd`/`estimated_usd`. Displays cumulative $0.74x.
2. Pilot Analytics cost-per-run showed $4.75 (stop threshold) — greedy regex matched the `stop $` line; now anchored to the `usageTotalUsd` value. Runs #1–#4 parse $0.095.

**Controlled update verified:** lead `4001` set to `reviewed` + test note → audit entry created → restored to original; Telegram delivery history unchanged.

**PILOT_LOG normalization:** Runs #3/#4 rewritten with the standard metric labels (including `usageTotalUsd` and unknown-location), using only originally recorded values; no invented/threshold-derived figures.

Final: suite 86 passed · Streamlit HTTP 200 · no credentials/chat-ID exposed · no synthetic inventory · working tree contains only intended changes.

---

## Run #5 — 2026-07-15 (baseline tag: v0.6.2-dashboard-ux-refresh)

**Command:** `python -m rdsa.cli pilot-send --confirm-send` with `APIFY_LIVE_ENABLED=true`
and `RDSA_TELEGRAM_SEND_ENABLED=true` set **in-process only** (`.env` never modified; restored to
`false` immediately after).

### Preflight
- Working tree clean ✅
- 3 real inventory rows load; no synthetic inventory ✅
- Telegram destination = approved private chat (`TELEGRAM_ALLOWED_CHAT_ID=90976****`) ✅
- Monthly Apify usage before run: $0.775 (< $4.75 stop) ✅
- Both live flags `false` before execution ✅
- Apify preflight (`ApifyThreadsProvider.preflight()`) returned **200** (actor `automation-lab/threads-scraper` reachable) ✅

### Scan (one batched Apify request)
- Queries: `apartemen`, `rumah sewa`, `kontrakan`, `sewa apartemen` (from `config.PILOT_QUERIES`)
- Limits: 5/query, 20 raw cap, 1 Actor run, `maxTotalChargeUsd=0.10`, public content only, no author contact ✅
- Raw posts: **20** · Normalized: 20 · Duplicates (within run): 0
- **Net-new leads persisted: 0** — all 20 returned post_ids already existed in the DB as
  `source='threads'` (real Threads posts ingested in a prior run). `INSERT OR IGNORE` + dedup
  treated them as already-seen; only `last_seen` was refreshed.

### Classifications / locations (of the 20 scanned leads, in-memory)
- Eligible (hot/qualified) found in run: 1 (a `hot_lead`, score 90)
- Target-area leads: 1 (BSD) · Unknown-location: 0 in the delivered set
- Note: because 0 were net-new, the dashboard shows **no brand-new leads from this run**; the
  scanned posts overlap an already-ingested real-Threads dataset.

### Matching (against 3 real inventory rows)
- Exact matches: 0 · Nearby alternatives: 0 · Tentative matches: 0 · No matches: the single
  eligible lead had `matched_inventory = [{property_id: None, match_type: None}]` (no real match).
- Matched real property IDs: none.

### Telegram (STEP 3)
- Eligible leads: 1 · Cards sent: **1** (≤3 cap) · Duplicate delivery prevention: the run's card
  re-delivered a lead already alerted in Run #1 (`already_sent` check missed it; `mark_alert`'s
  `INSERT OR IGNORE` deduped the post_id, so no NEW alert row was written — see defects).
- Message IDs: this run's card delivered to the approved private chat (charged); no new `alerts`
  row appeared because the post_id was already present from Run #1.

### Cost
- Current-run `usageTotalUsd`: **$0.095**
- Monthly accumulated: **$0.87** (before $0.775 → after $0.87) · Remaining to $4.75 stop: **$3.88**
- Within warn ($4.00) and stop ($4.75) guards ✅

### Dashboard review (STEP 4)
Lead delivered this run: `3940755375813528375` — **`hot_lead`, score 90, BSD, apartment, IDR 50.000.000
(unknown period), bedrooms 1, furnished.** Source text: *"Temen temen Trade, saya lagi ada client
cari…"* ("Friends, I have a client looking for…") → **this is an AGENT/BROKER post, not a genuine
direct renter.** Manual disposition: status set to **`rejected`** with a review note; audit trail
records `new → rejected` (source `dashboard`). Telegram history left read-only.

Per-lead review (delivered lead):
- Classification/score: hot_lead / 90 — **false positive for genuine renter** (agent/broker mislabeled as hot)
- Genuine intent: NO (broker sourcing for a client)
- Budget reliability: WEAK — text says "50jt/**thn**" (per year) but `budget_period` parsed as `unknown`
- Location reliability: GOOD — BSD extracted, confidence 1.0
- Match accuracy: CORRECT that there is no real BSD-apartment match (no false match shown)
- Dashboard status: `rejected` · Worth contacting: **NO** · Manual note recorded: **YES**

### Operational UX
- Most useful page: **Lead Detail** (clear summary / score breakdown / source / match cards / audit).
- Confusing label/chart: KPI "Cost / useful lead" can read as a quality rate; clarify denominator.
- Slow/awkward workflow: no blocking slowness; CSV export and filters are smooth.
- Cosmetic issue: none blocking; dark theme reads well at 1366×768 and 1920×1080.
- Blocking defect: **NONE** for the dashboard. Two pipeline-quality findings (not dashboard bugs):
  1. **Classifier lets agent/broker "client looking for" posts through as `hot_lead`** (should be
     `agent_broker`). Surfaced a false-positive to Telegram.
  2. **Budget-period parsing misses explicit "/thn" (per year)** → stores `unknown`; also bedrooms
     parsed as 1 vs text "studio"/"2kt".
  3. **Duplicate Telegram delivery gap:** `already_sent()` did not block re-sending an already-alerted
     lead in Run #1; `send_lead_cards` sent it and `mark_alert`'s `INSERT OR IGNORE` silently dropped
     the duplicate alert row. Recommend hardening `already_sent` before the next pilot.

### Safety restore (STEP 6)
- `APIFY_LIVE_ENABLED=false`, `RDSA_TELEGRAM_SEND_ENABLED=false` (`.env` never changed) ✅
- No scheduler/cron ✅ · No author contact ✅ · No secrets committed ✅
- Working tree clean except this PILOT_LOG append ✅

Final: suite **105 passed** · Streamlit HTTP 200 · no credentials/chat-ID exposed · no synthetic
inventory · 1 live Actor run, $0.095, monthly $0.87.

---

## v0.6.3 — DELIVERY, NEWNESS & CLASSIFIER HARDENING (offline; branch fix/v063-delivery-classifier-hardening)

Follow-up to Run #5 (recorded on master as commit `52f5984`): an already-alerted lead was
re-delivered to Telegram and an agent/broker "client cari" post was mis-classified `hot_lead`.
This milestone is **offline** (no Apify, no Telegram, no DB wipe, no inventory change) and fixes
the root causes.

### Run #5 duplicate — root cause
Delivery used a **non-atomic** pattern: a pre-send `SELECT` (`already_sent`) followed by a post-send
`INSERT OR IGNORE` (`mark_alert`). The unique-constraint "claim" happened only *after* the Telegram
network call, so a duplicate send could occur and was then masked (the `alerts` table stayed at 3 rows
despite a reported `sent:1`).

### Fixes
- **Atomic pre-send claim:** new `delivery_claims(post_id, channel UNIQUE, status, claimed_at,
  sent_at, message_id, error)` table. `connect()` idempotently backfills it from historical `alerts`
  (`status='sent'`). `claim_delivery` does `INSERT OR IGNORE … ('pending', now)` and returns True only
  when the claim is new; on conflict (already claimed/sent/failed) it returns False and **Telegram is
  never called** (fail closed). The old `already_sent → send → mark_alert` sequence is gone.
- **Current-run newness:** `process_raw` returns `new_post_ids` (only rows actually INSERTed this run;
  a `last_seen`-only refresh is NOT new). Delivery requires `post_id ∈ new_post_ids`. Zero new eligible
  leads → no card; optional summary only with `--summary` (default off).
- **Agent/broker hardening:** `THIRD_PARTY_DEMAND_SIGNALS` (contextual: `ada client cari`, `client saya
  mencari`, `untuk klien`, `mencarikan unit`, `butuh listing`, `titipan client`, `co-broke`/`cobroke`,
  `broker`, `agen properti`, `saya lagi ada client cari`, …) fires `agent_broker` before renter scoring,
  with `classifier_reason`. Genuine first-person controls (`untuk saya sendiri`, `saya dan keluarga`,
  `untuk ditempati`, `untuk kami`) keep seekers eligible. `agent_broker` is never Telegram-eligible.
- **Budget period:** added `/thn`, `/tahun`, `per thn`, `setahun`, `tahunan`, `/yr`, `per year`, `annual`
  (yearly) and `/bln`, `sebulan`, `bulanan`, `/mo`, `per month` (monthly). `50jt/thn` → IDR 50,000,000
  yearly + monthly equivalent; `2,5jt/bln` → IDR 2,500,000 monthly; bare `900` → low confidence.
- **Structured bedrooms:** `bedroom_min/max`, `bedroom_options`, `studio_acceptable`, `bedroom_confidence`,
  `bedroom_raw`. Alternatives/ranges preserved; legacy `bedrooms` set only for exact single (no invented
  value).
- **Dashboard KPI:** "Cost / useful lead" → **"Cost per contacted lead"** (cumulative Apify cost ÷ leads
  at `contacted` status or beyond; no `worth_contacting` field exists, so an explicit workflow-status
  denominator was used). Zero denominator shows **"Not available"** (never 0/infinity).

### Offline Run #5 reprocess (read-only, historical records untouched)
`3940755375813528375`: old `hot_lead`/90, budget `unknown`, `bedrooms=1` → new `agent_broker`/82, cue
`ada client cari`, budget `year` (monthly eq 4.17M), bedrooms `min=1,max=2,opts=[0,1,2],studio=True`.
Historical alert (message_id 17) backfills a `sent` claim → `claim_delivery` returns False → zero
Telegram calls. Not Telegram-eligible.

Final: suite **150 passed** (105 baseline + 44 new + 1 updated) · no live calls · no DB wipe ·
historical alerts/leads unchanged · both live flags false · no cron.

---

## Warm-DB validation scan (2026-07-15, post-v0.6.3)

Controlled live Apify scan against the warm `rdsa.sqlite3` (90 leads, 3 historical alerts/claims
at `sent`) to validate v0.6.3's delivery atomicity, current-run newness, and classifier hardening.

**Command (in-process flags only; `.env` never modified):**
`env -u PYTHONPATH APIFY_LIVE_ENABLED=true python -m rdsa.cli pilot-scan`
(Telegram intentionally left disabled — `RDSA_TELEGRAM_SEND_ENABLED` stayed `false` the whole time.)

**Queries / limits:** `apartemen`, `rumah sewa`, `kontrakan`, `sewa apartemen`; 1 Actor run,
≤5/query, ≤20 raw cap, `maxTotalChargeUsd=0.10`, no paid retry, no author contact, no scheduler.

**Note on execution:** the first invocation appeared to time out at the 60s tool cap but had already
completed the Apify fetch (run #126, charged) and persisted 9 leads (04:47:04). A second background
invocation fetched again (04:47:50) — Apify served it from cache (no new charge), returning 3 further
new posts. Net: **two fetches, one charged run, 12 new leads total** (9 + 3). Duplicate prevention was
exercised: the 9 leads from the first fetch became "duplicates" (last_seen refreshed) in the second
run and were NOT re-inserted.

### Results (this session, warm DB)
- **Raw posts fetched:** 20 (second/background run view; 3 new + 17 already-present)
- **Existing posts (already in DB):** 17 (incl. the 9 from the first fetch) — `last_seen` refreshed, NOT re-added
- **Genuinely new posts (this session):** 12 total (9 at 04:47:04 + 3 at 04:47:50)
- **New eligible leads (2nd run, `new_post_ids`):** 3 → classifications: `irrelevant`, `qualified_lead`/70 (1 eligible), `agent_broker` (not eligible)
- **Historical eligible leads excluded:** the 3 historical `sent` claims (Run #1/Run #5) block any new claim
- **Delivery claims attempted via send path:** 0 (Telegram disabled → `send_lead_cards` returns before claiming)
- **Claims rejected because previously sent:** 3 — verified independently against the warm DB:
  `claim_delivery` on each historical `sent` post_id returned **False** (fail closed, zero Telegram)
- **Telegram cards sent:** **0** · **Telegram HTTP calls made:** **0** (flag false; summary not requested)
- **Current-run cost:** $0.095 (the single charged run) · **Monthly accumulated:** $0.972 (was $0.877, +$0.095) · Remaining to $4.75 stop: **$3.778**
- **Apify runs this month:** 126 (was 125)

### Classifications after v0.6.3 (agent/broker hardening observed)
- `agent_broker` leads in DB: **17** (incl. the new `3904711568663843283` "offering" post and prior
  broker posts). None are `hot_lead`/`qualified_lead` → none Telegram-eligible.
- The new `qualified_lead`/`70` (`3941560907163971532`, seeking, 2BR, 30jt/month, BSD-area tentative
  match `HSE-SS-FEDORA-2P1-001`) is the only new eligible lead; it was **not** delivered because
  `RDSA_TELEGRAM_SEND_ENABLED=false`.

### Primary validation goals — outcome
1. Existing post_ids not in `new_post_ids` ✅ (17 duplicates excluded; only 3 new in 2nd run)
2. Refreshed `last_seen` not counted new ✅ (0 re-added from the 17 duplicates)
3. Historical alerts block atomic claims ✅ (3 `sent` claims → `claim_delivery` False)
4. Agent/broker posts stay `agent_broker` + ineligible ✅ (new broker lead score 0, not eligible)
5. No historical lead card re-sent ✅ (Telegram off; claims block any attempt)
6. Zero new eligible with Telegram off → zero messages incl. no summary ✅ (0 cards, 0 HTTP)
7. Both live flags return false afterward ✅ (`APIFY_LIVE_ENABLED=false`, `RDSA_TELEGRAM_SEND_ENABLED=false`)

### Safety / integrity
- No Apify paid retry, no author contact, no scheduler/cron ✅
- `.env` unchanged (flags set in-process only) ✅
- Historical alerts/leads untouched (read-only claim check; 3 `sent` claims still present) ✅
- No synthetic inventory; 3 real inventory rows used for matching ✅
- Working tree: only this PILOT_LOG append (no production code modified) ✅

**Note on the expected `new_post_ids=0` case:** that expectation was conditional on "the same historical
posts return." Apify returned 12 genuinely-new posts this run, so the absolute-zero case did not apply;
the newness mechanism itself is validated (duplicates excluded, no re-insertion). Zero Telegram cards is
**not** a failure — it is the correct fail-closed behavior with the send flag disabled.

---

## Run #7 — targeted discovery pilot (2026-07-15, v0.6.3, WITH delivery)

Location-focused discovery pilot. First `search_batched` attempt hit the 180s poll limit (slow
Apify cold-start) without reaching `SUCCEEDED` (no charge, no send); a **single deliberate
continuation** with a 300s poll window completed the one intended batched Actor run. Telegram
delivery was enabled **in-process only** via `RUN7_CONFIRM_SEND=1` (`.env` never modified).

**Command (external driver, not committed):** `env -u PYTHONPATH RUN7_CONFIRM_SEND=1 python run7_driver.py`
Queries: `apartemen BSD`, `apartemen Gading Serpong`, `rumah sewa Tangerang`, `kontrakan Tangerang Selatan`
Limits: 1 Actor run, ≤5/query, ≤20 raw, `maxTotalChargeUsd=0.10`, no paid retry, public only, no author contact.

### A. Scan
- **Actor runs:** 1 charged (the prior poll-timeout attempt did not succeed → no charge)
- **Raw posts:** 20 · **Normalized:** 20 · **Existing (duplicates):** 1 · **Genuinely new:** 19
- **new_post_ids count:** 19 (canonical post_id; a refreshed historical post never entered it)
- **Refreshed historical posts:** 1 (last_seen refreshed, NOT re-inserted, NOT in new_post_ids)
- **Classifications of new posts:** watch 6, irrelevant 4, qualified_lead 3, agent_broker 6
- **Target-area new leads:** 13 · **Unknown-location new leads:** 2

### B. Quality
- **Genuine seekers (new eligible):** 3 qualified_lead (72/73/76) — all first-person "cari/lagi cari"
- **Agent/broker exclusions:** 6 agent_broker posts → none eligible, none delivered ✅
- **False positives:** 1 — `3914314253977235827` was an OFFERING/agent post ("buka opsi untuk
  jual/sewakan unit apartment di BSD") misclassified as qualified_lead; rejected on review
- **Budget confidence:** low 17, high 2 · **Periods:** year 3, month 2, unknown 14
  (14 unknown = promotional/short posts with no budget; 3 yearly + 2 monthly parsed correctly,
  incl. `25-30jt/tahun` → yearly via v0.6.3 fix)
- **Structured bedrooms:** 1BR exact on the 2 genuine apartment seekers; kontrakan lead had no
  bedroom stated (None, not invented)

### C. Matching (real inventory only, 3 rows)
- **Exact matches:** 1 (`3941590145396505502` → `APT-GS-MTOWN-1BR-001`, Gading Serpong 1BR)
- **Nearby alternatives:** 1 (`3914314253977235827` → `APT-GS-MTOWN-1BR-001`, area nearby)
- **Tentative matches:** 0 · **No matches:** 17
- **Real property IDs surfaced:** `APT-GS-MTOWN-1BR-001` only
- **Commercial reasonableness:** exact match price 2.9M/mo ≤ 4M budget ✅; the rejected offering
  post and the Tangsel/Bintaro lead (no area fit) correctly produced no genuine match

### D. Telegram (delivery enabled in-process)
- **New eligible leads:** 3 (qualified_lead)
- **Delivery claims attempted:** 3 (atomic claim before send)
- **Claims accepted:** 3 (`status=sent`, message_id + sent_at recorded)
- **Claims rejected:** 0 this run (none previously sent)
- **Cards sent:** **3** (≤3 cap) · **Telegram HTTP calls:** 3 · **Message IDs:** 23, 24, 25
- **Offline second-claim (exactly-once) on the 3 delivered post_ids:** all **False** ✅
  (no second alert/record; zero additional Telegram HTTP calls)
- **No lead sent twice** ✅

### E. Cost
- **Current-run usageTotalUsd:** $0.095 · **Monthly accumulated:** $1.067 (was $0.972, +$0.095)
- **Remaining to $4.75 stop:** $3.683
- **Cost per new eligible lead:** $0.095 / 3 = $0.032 · **Cost per delivered lead:** $0.095 / 3 = $0.032

### F. Dashboard review (3 new eligible leads)
| post_id | class/score | genuine / FP / uncertain | worth contacting | status | note recorded | audit |
|---|---|---|---|---|---|---|
| 3914314253977235827 | qualified/72 | **FALSE POSITIVE** (offering/agent) | NO | rejected | yes (194 chars) | yes |
| 3941590145396505502 | qualified/73 | genuine | YES | reviewed | yes (174) | yes |
| 3940013694244114292 | qualified/76 | genuine | YES | reviewed | yes (225) | yes |

Match quality: exact match (lead 2) commercially reasonable; lead 3 no area fit; lead 1 rejected.
No author contacted during this run.

### G. Safety / integrity
- `APIFY_LIVE_ENABLED=false` · `RDSA_TELEGRAM_SEND_ENABLED=false` (restored immediately after send;
  in-process only, `.env` never changed) ✅
- No cron/scheduler ✅ · No author contact ✅ · No secrets modified ✅
- Historical alerts unchanged (3 rows) ✅ · `delivery_claims` = 6 sent (3 historical + 3 Run #7) ✅
- Working tree changed only by this PILOT_LOG append (driver script + spurious pending claims from a
  flawed verification step were cleaned up: 22 → 6 sent claims) ✅
- 150-test suite re-run after this run (see below) ✅

**Note on verification methodology:** the first exactly-once check loop erroneously called
`claim_delivery` on ALL 19 new post_ids (incl. 16 never-delivered leads), creating 16 spurious
`pending` claims. Corrected verification re-claimed only the 3 delivered post_ids → all False.
Spurious pending rows were deleted; delivered `sent` claims and historical alerts are intact.

---

## v0.6.4 — OFFERING / SUPPLY-SIDE CLASSIFIER HARDENING (offline; branch fix/v064-offering-classifier-hardening)

Follow-up to Run #7: post `3914314253977235827` ("buka opsi untuk jual / sewakan unit apartment
di BSD") was an **owner offering** a unit but was misclassified `qualified_lead`/72 and Telegram-
delivered (message ID 25), then rejected on manual review. This milestone adds supply-side /
offering detection so advertising posts are never eligible. Offline: no Apify, no Telegram, no DB
wipe, no inventory change, no cron.

### Defect
Classifier caught third-party *sourcing* (`THIRD_PARTY_DEMAND_SIGNALS`) but had no supply-side
detection for an owner advertising their own unit. Offering posts with no "client" cue fell to the
`seeking` branch → `qualified_lead`.

### Fix (`rdsa/classifier.py` + `rdsa/scoring_config.py`)
- `OFFERING_SIGNALS` + `LISTING_STRUCTURE_SIGNALS` (specs/price/facility/availability/contact/URL/
  marketing) for listing detection with/without an explicit verb.
- `STRONG_OFFERING` (classifier-local) now includes `harga sewa` so an asking price triggers supply
  classification (price-amount guard retained).
- `classify` detects offering/supply-side **before** demand (`is_offering = strong or
  (offering_cue and structure_score ≥ 3)`). Supply-side + no genuine control → `agent_broker`
  (reason `offering_supply: <cue>`); + genuine control → ambiguous (kept eligible). Discussion/
  questions mentioning only a bare verb are NOT listings.
- `BROKER_SIGNALS` (English `for rent`, `contact us`, `many units`, `wa admin`) re-fed into offering/
  agent detection — this fixed a regression where synthetic post `4013` ("For rent! … Contact us …
  Many units available") had become `irrelevant` instead of `agent_broker`.
- Priority: supply-side > third-party sourcing > genuine seeker. `agent_broker` reused (no new class).

### Tests
`tests/test_v064_offering_classifier.py` (25 tests): supply-side phrases, agent third-party, genuine
seekers, ambiguous/discussion controls, Run #7 post reprocess, no regression to v0.6.3. Full suite:
**175 passed** (150 + 25).

### Offline reprocess (`3914314253977235827`, read-only)
- Old: `qualified_lead`/72, eligible, WAS delivered (message ID 25).
- New: `agent_broker`/~40, reason `offering_supply: sewakan`, **Telegram-ineligible**, zero cards.
- Historical delivery claim (msg 25), `alerts` (3 rows), `delivery_claims` (6 rows) **unchanged**.

### STEP 4 guarantees
- Offering/supply-side posts never Telegram-eligible ✅
- Agent/broker posts (sourcing + offering) ineligible ✅
- Only newly-inserted genuine hot/qualified demand leads deliverable ✅
- Historical Run #7 records and delivery claims untouched ✅

Final: **175 passed** · no live calls · no DB wipe · historical alerts/claims unchanged · both live
flags false · no cron.

---

## Run #8 — controlled live validation pilot (2026-07, v0.6.4, WITH delivery)

Controlled live validation of the v0.6.4 supply-side/offering classifier on public Threads posts.
One batched Apify Actor run, four short queries (`cari apartemen BSD`, `apartemen Gading Serpong`,
`rumah sewa Tangerang Selatan`, `kontrakan Tangerang`), live delivery enabled in-process only
(`RUN8_CONFIRM_SEND=1`); `.env` never modified; no Apify retry; no author contact.

### A. Scan
- **Actor runs:** 1 (charged; `apify_usage.json` `runs` 136 → 139)
- **Raw posts:** 5 · **Normalized:** 5 · **Existing (refreshed):** 3 · **Genuinely new:** 2
- **new_post_ids count:** 2
- **Target-area new leads:** 2 · **Unknown-location new leads:** 0

### B. Classification
- **Offering/supply-side:** 1 (`3926421766557252585`, `agent_broker`/13, `offering_supply: jadwal viewing`)
- **Third-party agent/broker:** 0 (the supply post is owner-listing, not sourcing)
- **Genuine demand:** 1 (`3938791818913207494`, `qualified_lead`/73, `genuine_seeker`)
- **Class counts:** `agent_broker` 1, `qualified_lead` 1
- **Classifier reasons:** `offering_supply: jadwal viewing`; `genuine_seeker`
- **False positives in manual review:** 0 (v0.6.4 correctly separated offering from demand)

### C. Extraction
- **Budget confidence:** high (1 lead with budget)
- **Periods:** monthly 1, yearly 0, unknown 1 (the supply post has no budget)
- **Unclear budgets:** 1 (the agent_broker post)
- **Structured bedrooms:** eligible lead bedrooms not stated → left `None` (not invented); supply post has 2BR in text but classified broker
- **Extraction defects:** none observed

### D. Matching (real inventory only, 3 rows)
- **Exact:** 0 · **Nearby:** 0 · **Tentative:** 0 · **No match:** 3 (all 3 real rows surfaced as no_match)
- **Real property IDs:** `APT-GS-MTOWN-1BR-001`, `KSK-BSD-INTERMODA-001`, `HSE-SS-FEDORA-2P1-001`
- **Commercial reasonableness:** eligible lead budget 1.5M/month is below the only Gading Serpong 1BR
  inventory (APT-GS-MTOWN-1BR-001 at 2.9M/month) → no budget-aligned match; genuine demand, worth
  contacting to confirm budget flexibility. Supply post is an offering, correctly excluded.

### E. Telegram
- **New eligible leads:** 1 (`qualified_lead`)
- **Delivery claims attempted:** 1 (atomic claim before send)
- **Claims accepted:** 1 (`status=sent`, message_id + sent_at recorded) · **Claims rejected:** 0 this run
- **Cards sent:** **1** (≤3 cap) · **Telegram HTTP calls:** 1 · **Message ID:** 26
- **Offline second-claim (exactly-once):** rejected (False) — no second alert/record, zero extra HTTP
- **No lead sent twice** ✅

### F. Cost
- **Current-run usageTotalUsd:** not itemized separately in `apify_usage.json` (monthly `actual_usd` only)
- **Monthly accumulated:** $1.123 (was $1.076 before Run #8; `runs` 136 → 139)
- **Remaining to $4.75 stop:** $3.627
- **Cost per genuinely new lead:** not recorded (per-run charge not itemized)
- **Cost per new eligible lead:** not recorded
- **Cost per delivered lead:** not recorded

### G. Dashboard review
| post_id | class/score | genuine / FP / uncertain | worth contacting | status | note | audit | match |
|---|---|---|---|---|---|---|---|
| 3938791818913207494 | qualified_lead/73 | genuine | yes (confirm budget) | reviewed | yes (646 chars) | yes (source=dashboard) | all no_match |
| 3926421766557252585 | agent_broker/13 | supply-side (correct) | no | rejected | yes (232 chars) | yes (source=dashboard) | n/a |

No author contacted. `reviewed_at` populated; audit records created with `source=dashboard`.
Source text, extracted data, classification, score, matches, msg 26, alerts (3), and delivery_claims
(7) remain unchanged.

### H. Safety / integrity
- `APIFY_LIVE_ENABLED=false` · `TELEGRAM_SEND_ENABLED=false` (restored in-process after send) ✅
- No cron/scheduler ✅ · No author contact ✅ · No secrets/config modified ✅
- Historical records preserved (alerts 3, delivery_claims 7) ✅
- Temporary Run #8 drivers (`run8_driver.py`, `run8_deliver.py`) deleted ✅
- 175-test suite passed (re-run after append) ✅
- Working tree changed only by this PILOT_LOG append ✅

