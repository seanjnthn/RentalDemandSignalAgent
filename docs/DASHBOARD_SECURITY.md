# DASHBOARD_SECURITY.md — v0.6 operational dashboard

## Principles
1. **Read-only by default.** DB writes permitted ONLY for `leads.status`, `leads.notes`,
   `leads.reviewed_at` (and the audit row). Everything else is read.
2. **Parameterized queries only.** No string interpolation into SQL. Use `?` placeholders.
3. **No secret exposure.** Never display Telegram token, Apify token, `.env` values, or the
   private chat ID. The dashboard imports `config` for logic only; it must not `st.write`
   any `config.*_TOKEN` / `TELEGRAM_ALLOWED_CHAT_ID`. Add tests asserting these are absent
   from any rendered string.
4. **Sanitization.** Continue redacting phone numbers / emails in post text and notes.
5. **No internal IDs leaked** unless needed for support; prefer `post_id`.
6. **No permanent session data.** Streamlit session state is ephemeral; do not persist
   dashboard session artifacts to disk.
7. **Confirmation before status updates.** Require an explicit confirm control before
   committing a status change.
8. **Audit logging.** Every status change inserts a `status_history` row
   (`post_id, old_status, new_status, changed_at, note`) with `source='dashboard'`.
9. **Never modify Telegram alert history** (`alerts` table is read-only here).
10. **No live side-effects.** No Apify call path, no Telegram send path, no synthetic
    inventory fallback. Tests must assert these paths are unreachable from the dashboard.

## Test surface (security)
- `test_dashboard_security.py`: empty DB load, lead table load, filtering, canonical area
  display, budget confidence display, structured-match parsing, legacy `[null]` normalization,
  exact/nearby/tentative labels, real inventory load, missing inventory, invalid inventory,
  status update, notes update, audit-log insertion, parameterized queries, Telegram creds
  never exposed, Apify creds never exposed, no Telegram send path, no Apify call path,
  no synthetic inventory fallback, sanitization of phone/email.

## Files
- `dashboard/app.py` — entrypoint + Overview; `@st.cache_data` for reads.
- `dashboard/pages/*.py` — Inbox / Inventory / Matching Review / Pilot Analytics.
- `rdsa/dashboard_repository.py` — service layer (DB access, parameterized, audit).
- `tests/test_dashboard_repository.py`, `tests/test_dashboard_security.py`.
- `docs/DASHBOARD_GUIDE.md` — operator manual.
