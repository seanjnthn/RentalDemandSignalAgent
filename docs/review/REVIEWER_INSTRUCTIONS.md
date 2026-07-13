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

- Threads test account: **[operator fills in]** (added as a Threads Tester).
- Demo URL: **[operator fills in — e.g. https://rdsa-review.example.com]**
- If prompted to authorize, use the provided test account.

## Step-by-step

1. **Connect Threads account** *(exercises `threads_basic`)*
   - Open the Demo URL. Click **Connect Threads**.
   - Authorize with the test account in the Threads Authorization Window.
   - Confirm you are returned to the app in a connected state.
   - *(CLI: the operator completes OAuth and shows the obtained token scope.)*

2. **Enter a keyword** *(exercises `threads_keyword_search`)*
   - In **Keyword**, type e.g. `cari apartemen` (or `looking for apartment`).

3. **Enter a location**
   - In **Location**, choose/type e.g. `BSD`.

4. **Run Search**
   - Click **Run Search**. The app calls
     `GET https://graph.threads.net/v1.0/keyword_search` with `search_type=RECENT`,
     `media_type=TEXT`.
   - *(CLI: `rdsa scan --source threads --keyword "cari apartemen" --location BSD --dry-run`)*

5. **Review Results (public posts)**
   - Confirm a list of **public** Threads posts appears, each showing the post
     text, author username, timestamp, and a link to the original public post.

6. **Review Classification & Score explanation**
   - For each result, confirm a **classification** (e.g. hot_lead / qualified /
     watch / agent_broker / spam / irrelevant) and a **0–100 score** with a
     rule-by-rule breakdown (e.g. "+25 explicit seeking intent; +20 target
     location; …") are shown. This demonstrates the analysis is transparent.

7. **Review Inventory Matches**
   - For hot/qualified leads, confirm matching sample inventory listings are shown
     (location, type, bedrooms, price).

8. **Confirm NO write actions exist**
   - Observe there is no button/option to reply, comment, follow, like, repost,
     quote, DM, or publish anywhere in the app. The app is read-only on Threads.

## What you should conclude

- `threads_basic` is used to connect the account and authorize read-only calls.
- `threads_keyword_search` is used to retrieve **public** posts by keyword — the
  app's core, and non-functional without it.
- No automated engagement or messaging of Threads users occurs.
- Data shown is public; retention is minimal and deletable (see privacy policy +
  data deletion instructions).

## Support

If anything is inaccessible, contact **[operator email]** — do not reject for
access issues before reaching out. (Meta rejects submissions it cannot test, so
the operator will ensure the demo is live and the test account works during review.)
