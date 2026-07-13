# SCREEN_RECORDING_SCRIPT.md — Rental Demand Signal Agent (App Review)

A tight, review-ready screen recording (~3–5 min) that proves the app uses
`threads_basic` + `threads_keyword_search` as described and is strictly read-only.
Record using a clean browser (no personal tabs), with the App Review Demo UI
loaded over a real `graph.threads.net` connection (not the synthetic stub).

> Capture the whole window. Narrate briefly or add captions. Show the URL bar so
> the reviewer sees real API calls. Do a single take; if a step fails, restart.

---

## 0:00 — Title card (3s)
"Rental Demand Signal Agent — App Review Demo. Read-only public Threads search →
lead scoring → human review. No reply / follow / DM / publish."

## 0:05 — Connect Threads account (exercises `threads_basic`)
- Open Demo URL. Click **Connect Threads**.
- Complete the Threads Authorization Window with the provided test account.
- Show return to app in "Connected" state.
- *Say:* "threads_basic lets the operator connect their Threads account and
  authorize read-only calls."

## 0:50 — Enter keyword + location (exercises `threads_keyword_search`)
- **Keyword:** `cari apartemen`
- **Location:** `BSD`
- Click **Run Search**.
- Open DevTools → Network; filter to `graph.threads.net`. Point to the
  `GET /v1.0/keyword_search` call (params `q`, `search_type=RECENT`,
  `media_type=TEXT`). *Say:* "This is the single GET call the app makes."

## 1:30 — Public results
- Show the list of **public** posts: text, username, timestamp, permalink link.
- Click a permalink → Threads opens the original public post. Return.
- *Say:* "Only public posts are retrieved; we link back to the source."

## 2:10 — Classification + transparent score
- For one result, show the **classification** (e.g. `hot_lead`) and **score 0–100**
  with rule-by-rule breakdown ("+25 seeking intent, +20 target location, …").
- *Say:* "Scoring is transparent and stored for human review."

## 2:50 — Inventory matches
- For a hot lead, show matched sample inventory (location, type, bedrooms, price).
- *Say:* "Strong leads are matched to the operator's own sanitized inventory."

## 3:20 — Prove read-only (critical)
- Sweep the UI; state aloud: "There is no button or option anywhere to reply,
  comment, follow, like, repost, quote, DM, or publish. The app never contacts
  Threads users."
- Optionally: show the repo's `test_no_write_paths.py` passing — "A test greps the
  code to assert no Threads write/reply/follow/DM calls exist."

## 3:50 — End card (5s)
"Summary: threads_basic (connect) + threads_keyword_search (public search only).
No write permissions requested. Human reviews leads manually."

---

## Do / Don't

- ✅ Use the **real** live endpoint and a real test token.
- ✅ Show the `GET /keyword_search` network call.
- ✅ Show public data only; blur anything unexpected.
- ❌ Do not demonstrate any publish/reply/DM — there is none.
- ❌ Do not show secrets (tokens, `.env`); redact the URL if it carries a token.

## If the live search is mid-approval during recording
Record against the real endpoint with the test app in "development" mode using a
role account (search returns the connected user's own posts in dev mode). Clearly
note in the recording that public search activates after approval, and that the
**same** code path/UI is used — only the returned scope differs. Better: wait
until approval so the recording shows true public results.
