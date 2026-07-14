# DASHBOARD_SPEC.md — v0.6 Operational Lead Dashboard

## Purpose
A lightweight, **local, read-only-by-default** Streamlit dashboard for the human operator
to review and manage rental leads discovered by the existing Hermes workflow. It is an
**operational review interface** only.

## Non-goals / hard constraints
- No Apify / Threads API calls. No Telegram sends. No author contact.
- No cron. No recurring sending. No credential exposure. No `.env` modification.
- No duplicated scoring/matching logic — reuse `rdsa` modules.
- No synthetic inventory fallback for live leads.

## Pages
1. **Overview** — KPI cards + filters (date range, classification, status, area, property type, match type).
2. **Lead Inbox** — sortable/filterable table; sanitized; no unnecessary PII.
3. **Lead Detail** — read-mostly; editable: status, manual notes, reviewed_at only.
4. **Inventory** — read `data/inventory_real.csv`; validation status; available count by area; missing/invalid handling; no editing.
5. **Matching Review** — leads grouped by `exact_match` / `nearby_alternative` / `tentative_match` / `no_match`; nearby & tentative visually distinct from exact.
6. **Pilot Analytics** — per-run metrics from DB + `docs/PILOT_LOG.md`; distinguish current-run / cumulative / manually-reviewed; no false-positive claim without review.

## Writes (DB) — allowlisted only
- `leads.status`, `leads.notes`, `leads.reviewed_at` (add column if missing).
- Audit row in `status_history` (already exists): `post_id, old_status, new_status, changed_at, note` + a `source='dashboard'` marker (extend schema safely if needed).
- All writes use **parameterized** queries via the repository layer.

## Reads
- `rdsa.db` connect/read helpers; `rdsa.inventory.load_real_inventory`;
  `rdsa.matcher` (for match-type labels only — display, not re-execution);
  `rdsa` canonical-area + budget parser for display formatting.

## Secrets / sanitization
- Never display Telegram token, Apify token, `.env` values, private chat ID, or internal rowids.
- Continue sanitizing phone numbers / emails in displayed post text and notes.

## Lifecycle
- `feature/v06-operational-dashboard` branch; Codex implements; Hermes verifies; **no auto-merge**.
