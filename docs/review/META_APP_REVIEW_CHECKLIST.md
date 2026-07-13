# META_APP_REVIEW_CHECKLIST.md — Rental Demand Signal Agent

**Purpose:** Everything the operator must complete to get `threads_keyword_search`
approved so the app can search **public** Threads posts. Ordered, gated.

> Source of truth: Meta "App Review" docs (Resp. Platform Initiatives) and the
> Threads API "Get Started" + "Keyword Search" guides. Verify against the live
> App Dashboard at submission time — Meta changes wording/flows periodically.

---

## 0. Exact permissions this app requires

| Permission | Why | App Review? |
|------------|-----|:-----------:|
| `threads_basic` | Baseline for ALL Threads API calls; connect account, read own profile/media | **Yes** (standard access is limited; advanced needs review) |
| `threads_keyword_search` | The core feature — search **public** posts by keyword via `GET /v1.0/keyword_search` | **Yes — mandatory.** Without approval, search returns only the authenticated user's own posts |

**We request NOTHING else.** Explicitly NOT requested (and not in the code):
`threads_content_publish`, `threads_manage_replies`, `threads_read_replies`,
`threads_manage_insights`. This is a read-only, no-publish app.

## 1. Prerequisites (before you can submit)

- [ ] **Meta account** with a verified Threads account connected.
- [ ] **Create a Meta app** → choose the **Threads use case** (App Dashboard →
      Create App). Note: two app ID/secret pairs are generated — use the **Threads**
      app ID + secret.
- [ ] Add yourself (and any reviewer-safe account) as a **Threads Tester**; accept
      the tester invite from the Threads app settings.
- [ ] Configure **OAuth redirect URI** and complete the Authorization Window flow
      once to confirm you can obtain a long-lived user token.
- [ ] **Business Verification** — may be required for advanced access. Start early;
      it can take days and needs business documents. (Check the dashboard's
      "See Also → Business Verification".)
- [ ] **App must be able to run and be publicly reachable for reviewers** (see §4).

## 2. App settings to complete (App Dashboard)

- [ ] App icon, display name ("Rental Demand Signal Agent"), category.
- [ ] **Privacy Policy URL** (host `PRIVACY_POLICY_DRAFT.md` publicly; put the URL here).
- [ ] **User Data Deletion** — either a Data Deletion Request URL or clear
      instructions (see `DATA_DELETION_INSTRUCTIONS.md`).
- [ ] App domains / valid OAuth redirect URIs.
- [ ] Data Use Checkup / Data Handling questionnaire answered honestly (read-only,
      minimal retention).
- [ ] Switch app **Live** (published) — required for approved permissions to work
      for non-role users.

## 3. Per-permission submission content

For **each** of `threads_basic` and `threads_keyword_search`, provide:

- [ ] **Clear description** of how the app uses it (from `PERMISSION_JUSTIFICATION.md`).
- [ ] **Step-by-step reviewer instructions** (from `REVIEWER_INSTRUCTIONS.md`).
- [ ] **Screen recording** demonstrating the full flow (from `SCREEN_RECORDING_SCRIPT.md`).
- [ ] Confirmation the permission is actually exercised in the demo (Meta tests this).

## 4. The critical reviewer-access requirement

> Meta states: *"we will test your app to verify that it actually uses the
> permissions… If we are unable to access your app to test it, your entire
> submission will be rejected."*

This is the make-or-break item. The reviewer must be able to **trigger a keyword
search and see public results**. Options (see `LIVE_SMOKE_TEST_PLAN.md` + the
Streamlit assessment in the STEP 4 report):

- [ ] Provide **test credentials** / a reviewer test account with a role on the app.
- [ ] Provide a **runnable UI** the reviewer can operate (the CLI is likely NOT
      reviewer-friendly — a minimal Streamlit "App Review Demo" is proposed).
- [ ] Ensure the demo hits the **real** `graph.threads.net` endpoint (not the stub).

## 5. Compliance evidence to include

- [ ] State plainly: **no** automated reply/comment/follow/DM/publish; **no**
      scraping; official API + public content only; Threads only.
- [ ] Show minimal data retention + deletion (`DATA_DELETION_INSTRUCTIONS.md`).
- [ ] Link the privacy policy.

## 6. Submit & iterate

- [ ] Submit for review; respond to any rejection with the FAQ guidance.
- [ ] On approval: confirm public search works with a real token; run
      `LIVE_SMOKE_TEST_PLAN.md`.

## 7. Do-not / out-of-scope for this submission

- ❌ Do not request write/publish/reply/insights permissions.
- ❌ Do not submit anything automatically — the operator submits via the dashboard.
- ❌ Do not claim capabilities the app doesn't have.
