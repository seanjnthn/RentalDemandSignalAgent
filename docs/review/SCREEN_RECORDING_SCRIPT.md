# SCREEN_RECORDING_SCRIPT.md — Rental Demand Signal Agent (App Review)

A tight, review-ready screen recording (~4–6 min) that proves the app uses
`threads_basic` + `threads_keyword_search` as described and is strictly read-only.
The app opens in **Synthetic** mode (no credentials, no network) — demonstrate that
first, then the Live permission flow. Record over a real `graph.threads.net`
connection for the Live portion.

> Capture the whole window. Narrate briefly or add captions. Show the URL bar so
> the reviewer sees real API calls. Do a single take; if a step fails, restart.

---

## 0:00 — Title card (3s)
"Rental Demand Signal Agent — App Review Demo. Read-only public Threads search →
lead scoring → human review. No reply / follow / DM / publish."

## 0:05 — App Overview (Synthetic mode, zero setup)
- Open Demo URL. App loads in **Synthetic** mode by default.
- Expand **App Overview**: state public-content-only, no-automatic-contact, privacy
  + data-deletion links. *Say:* "Everything runs offline first — no credentials."

## 0:30 — Run a Synthetic search
- Keep **Source mode = Synthetic** (default). Enter **Keyword** `cari apartemen`,
  **Location** `BSD`; set **Maximum results** slider (capped at 10). Click
  **Run Search**.
- Expand a result: public post text, **Source** permalink, **author** @username,
  timestamp, extracted requirements, **classification**, **0–100 score**,
  **score explanation** (rule-by-rule), **inventory matches**.

## 1:20 — Safety & Data Handling
- Expand **Safety & Data Handling**: read the no-reply/comment/follow/publish/DM
  statement; show the "temporarily processed public fields" list and **Delete
  session data**. *Say:* "No write endpoints exist; session data is clearable."

## 1:50 — Connect Threads account (exercises `threads_basic`)
- Switch **Source mode = Live**. If disabled, the UI shows "Live mode disabled. No
  network/API call will be made." (confirm, then proceed once enabled).
- Click **Connect Threads** → Threads Authorization Window with the test account.
- Return to app showing **connected**; granted scopes
  `threads_basic,threads_keyword_search` with the **token hidden** (redacted).
  *Say:* "threads_basic authorizes read-only calls; the token is never shown."

## 2:30 — Keyword search (exercises `threads_keyword_search`)
- **Keyword:** `cari apartemen`, **Location:** `BSD`, click **Run Search**.
- Open DevTools → Network; filter `graph.threads.net`. Point to the
  `GET /v1.0/keyword_search` call (params `q`, `search_type=RECENT`,
  `media_type=TEXT`). *Say:* "This is the single GET call the app makes."

## 3:10 — Public results + score + matches
- Expand a live result: text, username, timestamp, permalink (click → opens the
  original public post, then return). Show classification/score/breakdown + matches.

## 3:50 — Prove read-only (critical)
- Sweep the UI; state aloud: "There is no button or option anywhere to reply,
  comment, follow, like, repost, quote, DM, or publish. The app never contacts
  Threads users."
- Optionally show `test_no_write_paths.py` + `test_demo_no_write_compliance.py`
  passing — "Tests grep the code to assert no Threads write/reply/follow/DM calls."

## 4:20 — End card (5s)
"Summary: threads_basic (connect) + threads_keyword_search (public search only).
No write permissions requested. Human reviews leads manually. Live mode off by
default."

---

## Do / Don't

- ✅ Show the **Synthetic** flow first (instant, no creds) then the Live flow.
- ✅ Use the **real** live endpoint and a real test token for the Live portion.
- ✅ Show the `GET /keyword_search` network call.
- ✅ Show public data only; blur anything unexpected.
- ❌ Do not demonstrate any publish/reply/DM — there is none.
- ❌ Do not show secrets (tokens, `.env`); the UI redacts the token by design.

## If the live search is mid-approval during recording
Record the Live portion against the real endpoint with the test app in
"development" mode using a role account (search returns the connected user's own
posts in dev mode). Clearly note in the recording that public search activates
after approval, and that the **same** code path/UI is used — only the returned
scope differs. Better: wait until approval so the recording shows true public
results.
