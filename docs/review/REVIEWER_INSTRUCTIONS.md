# REVIEWER_INSTRUCTIONS.md — Rental Demand Signal Agent

Step-by-step instructions for the Meta App Reviewer to exercise every permission
and confirm the app behaves exactly as described. Paste an adapted version into
the "Instructions for reviewer" field of each permission submission.

> These instructions assume the **App Review Demo UI** (a minimal, read-only web
> app) is provided to the reviewer. If instead you give the reviewer test
> credentials for the CLI, adapt steps 2–6 to the CLI commands noted in brackets.

---

## What this app does (1 sentence)

It searches **public** Threads posts for people looking to rent a home, extracts
their requirements, scores each as a lead, matches strong leads to the operator's
property inventory, and presents results to a human — it never replies, follows,
DMs, or posts.

## Test account

- Threads test account: **[operator fills in]** (added as a Threads Tester) — only
  needed for **Live** mode.
- Demo URL: **[operator fills in — e.g. https://rdsa-review.example.com]**
- The app opens in **Synthetic** mode by default, which needs **no credentials**
  and makes **no network call**. Reviewer can verify the entire flow immediately.
- Live mode is **disabled by default** (`THREADS_LIVE_ENABLED=false`); enabling it
  requires the operator's Meta app credentials + approved permissions.

## Step-by-step

**A. Verify the full flow with zero setup (Synthetic mode — recommended first)**

1. Open the Demo URL. Confirm the **App Overview** panel states public-content-only
   and no-automatic-contact, with links to the privacy policy and data-deletion docs.
2. Leave **Source mode = Synthetic** (default). Optionally enter a **Keyword**
   (e.g. `cari apartemen`) and/or **Location** (e.g. `BSD`); set **Maximum results**
   (capped at 10). Click **Run Search**.
3. Confirm **Search Results** appear — click any result to expand: public post text,
   **Source** permalink, public **author** (@username), timestamp, extracted rental
   requirements (location/type/bedrooms/budget/dates/duration/requirements),
   **classification**, **0–100 score**, **score explanation** (rule-by-rule
   breakdown), and **inventory matches**.
4. Open **Safety & Data Handling**: confirm the statement that the app never
   replies/comments/follows/publishes/DMs, the list of temporarily-processed public
   fields, and the **Delete session data** action.

**B. Exercise permissions (Live mode — needs operator credentials + approval)**

5. **Connect Threads account** *(exercises `threads_basic`)*
   - Click **Connect Threads** → opens the Threads Authorization Window; authorize
     with the test account. Return to the app showing **connected**; granted scopes
     shown as `threads_basic,threads_keyword_search` with the **token hidden**.
   - Use **Disconnect / clear local session** to clear it.
6. Switch **Source mode = Live**. Enter a **Keyword** + **Location**, click
   **Run Search**. The app calls `GET https://graph.threads.net/v1.0/keyword_search`
   (`search_type=RECENT`, `media_type=TEXT`). Repeat steps 3–4 on the live results.
7. If Live is disabled, the UI shows "Live mode disabled. No network/API call will
   be made." and makes no request — confirm this by trying Live with the default
   config.

## What you should conclude

- `threads_basic` is used to connect the account and authorize read-only calls.
- `threads_keyword_search` is used to retrieve **public** posts by keyword — the
  app's core, and non-functional without it.
- The Synthetic flow demonstrates the exact same processing (extract → score →
  classify → match) with no credentials, proving the logic is real and reviewable.
- No automated engagement or messaging of Threads users occurs; tokens are never
  displayed. Data shown is public; retention is minimal and deletable.

## Support

If anything is inaccessible, contact **[operator email]** — do not reject for
access issues before reaching out. (Meta rejects submissions it cannot test, so
the operator will ensure the demo is live and the test account works during review.)
