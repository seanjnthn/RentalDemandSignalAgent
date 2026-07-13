# PERMISSION_JUSTIFICATION.md — Rental Demand Signal Agent

Text intended to be adapted into the App Review submission's per-permission
"How will your app use this permission?" fields. Written to be honest, specific,
and testable — Meta rejects vague or unverifiable justifications.

---

## App summary (for the reviewer)

Rental Demand Signal Agent helps a small property-rental operator in the Greater
Serpong / South Tangerang area (Indonesia) discover **public** Threads posts from
people who are actively looking to rent a home. For each public post the app
extracts the stated rental requirements, computes a transparent lead score,
classifies the post, and matches strong leads to the operator's own property
inventory. Qualified leads are shown to a **human**, who decides whether to reach
out through normal channels. **The app never replies, comments, follows, DMs, or
publishes anything on Threads, and never contacts anyone automatically.**

---

## `threads_basic`

**How the app uses it:** Required baseline for all Threads API calls. The app
uses it to (1) let the operator authenticate/connect their own Threads account
via the OAuth Authorization Window, and (2) make authorized GET calls to the
Threads Graph API. No profile data is republished; it is used solely to establish
an authenticated session for read-only search.

**What the reviewer will see:** The operator connects a Threads account; the app
obtains a user access token; a subsequent keyword search call succeeds.

---

## `threads_keyword_search`

**How the app uses it:** This is the app's core function. Using
`GET https://graph.threads.net/v1.0/keyword_search`, the app searches **public**
Threads posts for rental-intent keywords (e.g. "cari apartemen", "butuh
apartemen", "looking for apartment") combined with target locations (BSD, Alam
Sutera, Gading Serpong, Tangerang Selatan). Returned public posts
(`id, text, permalink, timestamp, username`) are analyzed locally to extract
rental requirements and produce a transparent lead score for **human** review.

**Why it is necessary:** Without this permission the endpoint returns only the
authenticated user's own posts, so the app cannot perform its sole purpose —
discovering public rental-demand signals. There is no alternative official
endpoint that surfaces public keyword matches.

**Data handling:** Only public fields the API returns are processed and minimally
stored (see privacy policy). No private data, no DMs, no scraping. Post text is
retained only as long as needed for the operator's manual review and is deletable
on request.

**What the reviewer will see:** The reviewer enters a keyword + location, runs the
search, and sees real public Threads results, each with an extracted-requirements
summary, a 0–100 score with a rule-by-rule breakdown, and any matching inventory.

---

## Permissions explicitly NOT requested (and why)

| Permission | Why not requested |
|------------|-------------------|
| `threads_content_publish` | The app never posts to Threads. |
| `threads_manage_replies` / `threads_read_replies` | The app never reads or manages replies; no interaction with commenters. |
| `threads_manage_insights` | The app does not use analytics/insights. |

This minimal footprint is intentional and aligns with data-minimization: the app
requests only what its read-only, human-in-the-loop workflow requires.
