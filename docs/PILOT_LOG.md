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
