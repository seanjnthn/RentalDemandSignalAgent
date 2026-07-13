# CREDENTIALS_AND_PERMISSIONS.md — Rental Demand Signal Agent (MVP)

**Last updated:** 2026-07-13
**Source:** Verified against official Threads API docs (updated Jul 2026).

---

## 1. What the Threads Keyword Search API actually provides (verified)

- **Endpoint:** `GET https://graph.threads.net/v1.0/keyword_search`
- **Query params:**
  - `q` *(required)* — keyword(s).
  - `search_type` — `TOP` (default) or `RECENT`. **Use `RECENT`** for fresh demand.
  - `search_mode` — `KEYWORD` (default) or `TAG`.
  - `media_type` — `TEXT` / `IMAGE` / `VIDEO`. **Use `TEXT`** for MVP.
  - `since` / `until` — Unix timestamp window (`since` ≥ `1688540400`).
  - `limit` — default 25, max **100**.
  - `author_username` — optional exact-match filter.
  - `fields` — e.g. `id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply`.
- **Returned per post:** `id, text, media_type, permalink, timestamp, username,
  has_replies, is_quote_post, is_reply`.
  - ⚠️ **No location/geo, no follower count, no engagement metrics.**
  - ⚠️ The `owner` field is **excluded** from keyword search results.
- **Rate limit:** **2,200 queries / rolling 24h per user** (shared across apps).
  Queries returning **no results do not count**. Sensitive/offensive keywords
  return an **empty array**.

## 2. Credentials required

| Item | Purpose | Where to get it |
|------|---------|-----------------|
| **Meta app (Threads use case)** | Registers the integration | developers.facebook.com → Create App → Threads use case. Use the **Threads app ID + Threads app secret** (there are two pairs; pick the Threads ones). |
| **Threads app ID + secret** | OAuth client creds | App dashboard. |
| **Threads user access token (long-lived)** | Authenticates API calls | OAuth 2.0 Authorization Window → short-lived token (1h) → exchange for long-lived (60 days) → refresh before expiry. |
| **Redirect URI** | OAuth callback | Configured in the app; needed once to complete the auth flow. |
| **Telegram bot token** | Send alerts | Create a bot via @BotFather. |
| **Telegram chat_id** | Alert destination | The operator's channel/group/DM id. |

## 3. Permissions (scopes)

| Permission | Needed for | App Review? |
|------------|-----------|:-----------:|
| `threads_basic` | Any Threads API call | Required |
| `threads_keyword_search` | Public keyword search (GET `/keyword_search`) | **Required — via App Review** |

> **Critical gate:** Until `threads_keyword_search` is **approved via App Review
> and the app is published**, the endpoint searches **only the authenticated
> user's own posts**. Threads *testers* can grant permissions pre-approval, but
> public results require approval. **Therefore all MVP development and testing
> runs against the 20 synthetic posts**; live public scanning is unlocked only
> after Meta approval.

## 4. What we will NOT request

- No `threads_content_publish`, `threads_manage_replies`, `threads_manage_insights`,
  or any write/reply scope — the system is read-only on Threads by policy.

## 5. Environment variables (`.env`, git-ignored)

```dotenv
# Threads
THREADS_APP_ID=
THREADS_APP_SECRET=
THREADS_ACCESS_TOKEN=          # long-lived user token
THREADS_API_BASE=https://graph.threads.net/v1.0

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Runtime
RDSA_QUERY_BUDGET_PER_RUN=40   # stay far under 2200/24h
RDSA_DB_PATH=data/rdsa.sqlite3
RDSA_INVENTORY_CSV=data/inventory.csv
```

## 6. Credential acquisition checklist (operator, one-time)

- [ ] Create Meta app with **Threads use case**.
- [ ] Record Threads app ID + secret.
- [ ] Add yourself as a **Threads tester** (enables pre-approval testing on own posts).
- [ ] Implement/complete the Authorization Window flow → get long-lived token.
- [ ] Submit **App Review** for `threads_keyword_search`; publish the app.
- [ ] Create Telegram bot via @BotFather → bot token.
- [ ] Get the destination `chat_id`.
- [ ] Fill `.env`; never commit it.

## 7. Query-budget math

- Keywords: 7 · Locations: 4 → up to 28 keyword×location combos.
- One `RECENT` query per combo per scan = 28 queries.
- At, say, 4 scans/day = 112 queries/day — comfortably under 2,200.
- Empty-result queries don't count, giving further headroom.
