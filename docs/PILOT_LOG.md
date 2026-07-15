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

