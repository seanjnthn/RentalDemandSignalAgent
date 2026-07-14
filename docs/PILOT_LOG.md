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
