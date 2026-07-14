# v0.6 Operational Dashboard

Run locally from the repository root with `streamlit run dashboard/app.py`.
The app is a local, read-only-by-default review surface. It reads the pilot
SQLite database, the validated `data/inventory_real.csv`, `docs/PILOT_LOG.md`,
and `data/apify_usage.json` when present. Missing or invalid real inventory is
reported and never replaced with synthetic rows.

Use the sidebar filters on Overview and Lead Inbox. Lead Detail permits only a
confirmed update to status, notes, and reviewed time. Every save writes one
dashboard audit record to `status_history`; alerts and delivery metadata remain
read-only. Refresh clears the read cache. Source text and notes are sanitized
for phone numbers and email addresses.

The dashboard does not call external services and does not display credentials,
private chat identifiers, internal row IDs, or provider tokens. It does not
send Telegram messages, fetch Threads/Apify data, re-run matching, edit
inventory, or modify `.env`.
