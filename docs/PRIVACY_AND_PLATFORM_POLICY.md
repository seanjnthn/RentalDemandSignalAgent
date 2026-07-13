# PRIVACY_AND_PLATFORM_POLICY.md — Rental Demand Signal Agent (MVP)

**Last updated:** 2026-07-13
**Applies to:** all code, scans, storage, and operator use of this system.

This is a hard boundary document. If a proposed feature conflicts with anything
here, the feature does not ship.

---

## 1. Golden rules

1. **Official APIs only.** Threads data is obtained solely via the official
   Threads Keyword Search API (`graph.threads.net`). No scraping, no
   headless-browser harvesting, no unofficial/reverse-engineered endpoints.
2. **Public content only.** Only publicly searchable Threads posts are processed.
   No private accounts, no private messages/DMs, no follower-gated content.
3. **Read-only on Threads.** The system never replies, comments, likes, reposts,
   quotes, follows, or DMs. There is no code path to do so.
4. **No automated contact with leads — ever.** Outreach is 100% manual by a human.
5. **Threads only (for now).** No Instagram, Facebook, X, or TikTok.

## 2. What we collect (minimal, public)

Only the fields the API returns for a public post:
`id, text, media_type, permalink, timestamp, username, has_replies,
is_quote_post, is_reply`, plus fields we *derive* (extraction, score, class).

We do **not** collect: private profile data, contact details, email, phone,
location beyond what the author voluntarily wrote publicly, follower lists, or
any data behind authentication/privacy walls.

## 3. Data minimization & retention

- Store the **minimum** needed for a human to review and act on a lead.
- `raw_text` is retained only as long as needed for review. Recommended:
  purge or truncate `raw_text` for leads in terminal states (`converted`,
  `rejected`) older than **30 days** (configurable). Keep the `permalink` so the
  human can always view the live public source instead of our copy.
- Provide a `purge` CLI command to delete leads/authors on request.
- No selling, sharing, or re-publishing of collected data.

## 4. Compliance with Meta / Threads Platform Terms

- Respect the documented rate limit: **2,200 queries / rolling 24h per user**,
  shared across apps. The query planner enforces a conservative per-run budget.
- Use only approved permissions: `threads_basic` + `threads_keyword_search`.
- Honor that **without `threads_keyword_search` App Review approval**, search only
  returns the authenticated user's own posts — so no public data is accessed until
  Meta approves the use case. Development/testing uses **synthetic data** until then.
- Do not attempt to access the excluded `owner` field or circumvent sensitive-
  keyword filtering (which returns empty arrays by design).
- Follow Meta Platform Terms and Developer Policies; the stated use case
  (surfacing public rental-demand signals for manual human follow-up) must match
  what is declared in App Review.

## 5. Respecting the individual

- These are real people who posted publicly, not lead-list commodities.
- The human operator contacts them through **normal, appropriate channels** and
  identifies themselves honestly. No pretexting, no spam.
- Honor any "do not contact" / opt-out: mark such authors and exclude them from
  future alerts (a local suppression list).
- If a post is later deleted or made private, the live `permalink` will reflect
  that; do not rely on or re-surface our cached copy as if still public.

## 6. Security

- All tokens (Threads access token, Telegram bot token) live in environment
  variables / `.env`, never committed. `.env` is git-ignored.
- The SQLite DB may contain public-but-personal text; store it on the operator's
  own machine, not in a shared repo.
- Telegram alerts go only to the operator's own configured chat_id.

## 7. Enforcement in code (verifiable)

- The Threads client module exposes **only** search/GET functions.
- A test asserts the codebase contains no Threads write/reply/follow/DM calls
  (grep-based guard in `tests/test_no_write_paths.py`).
- The only outbound-messaging component is the Telegram notifier, targeting the
  operator — never a Threads user.
- CI/test run is fully offline (synthetic data), proving no accidental live calls.

## 8. Prohibited features (will not be built)

- ❌ Auto-reply / auto-DM / auto-comment / auto-follow on any platform.
- ❌ Scraping or unofficial APIs for Threads, IG, FB, X, TikTok.
- ❌ Harvesting contact info or de-anonymizing users.
- ❌ Bulk export of personal data for third parties.
- ❌ Bypassing rate limits, sensitive-keyword filters, or permission gates.
