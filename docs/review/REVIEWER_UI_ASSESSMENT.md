# REVIEWER_UI_ASSESSMENT.md — Is a minimal Streamlit App Review Demo needed?

**Decision asked:** Do we need a Streamlit "App Review Demo" (Connect Threads ·
Keyword · Location · Run Search · Results · Classification/score · Matches) for
the Meta App Review submission?

**Recommendation: YES — build a minimal reviewer UI, but gate it behind STEP 4
approval. Do NOT build it yet.** Rationale and scope below.

---

## Why it's necessary

Meta's App Review guidance is explicit and decisive:

> *"we will test your app to verify that it actually uses the permissions and
> features you are requesting. If we are unable to access your app to test it,
> your entire submission will be rejected."*

The reviewer must be able to **personally trigger a keyword search and see real
public results**. Our current interface is a CLI, and two facts make it unsuitable
for reviewers:

1. **A CLI is not reviewer-operable.** Reviewers are not given a shell or your
   environment. They need a URL they can click and type into.
2. **The live path is currently stubbed.** `rdsa/cli.py::run_scan` raises
   `RuntimeError('live Threads source is intentionally stubbed…')` for
   `--source threads`, and `scan` doesn't even accept `--keyword` / `--location`
   flags (it reads a fixed synthetic JSON). An MVP CLI demo cannot exercise real
   `threads_keyword_search` without code changes anyway.

So even setting aside reviewer-friendliness, a thin **live-capable** UI is the
cleanest way to (a) un-stub the live source behind a small, reviewed surface and
(b) give the reviewer something clickable that calls the real `GET /keyword_search`.

## Why NOT just use the CLI + test credentials

- We'd have to provision a Meta test account *and* hand the reviewer an environment
  they can run — fragile, and reviewers are not expected to operate a repo.
- A URL is what the App Review process expects; it's lower-friction and lower-risk
  of an access-based rejection.

## Proposed minimal scope (build only after STEP 4 approval)

A single-file Streamlit app, **read-only**, that wraps the *existing* library
functions (no new domain logic):

| UI element | Wired to (already exists) |
|-----------|---------------------------|
| **Connect Threads** button | OAuth flow → long-lived token (new: ~30 lines, standard Meta snippet) |
| **Keyword** input | `config.KEYWORDS` dropdown + free text |
| **Location** input | `config.LOCATIONS` dropdown + free text |
| **Run Search** button | `ThreadsClient.search(q, location, limit)` → real `GET /keyword_search` |
| **Results** list | per post: text, `username`, `timestamp`, `permalink` link |
| **Classification + score** | `extract → score → classify` (already implemented) + score breakdown |
| **Inventory matches** | `match(lead, inventory)` (sanitized CSV) |

Explicitly **out of scope** for the demo (and the app): any reply / comment /
follow / DM / publish control. The UI must visibly contain **no such control**.

### Engineering notes
- New module `rdsa/web_review.py` (or `app_review_demo.py`); depends on `streamlit`.
  Optional extra in `pyproject.toml` (`demo = ["streamlit"]`).
- Un-stub live search **only inside the demo path** behind a flag; keep the
  production CLI's guard until live is officially enabled (per your "no live API
  yet" instruction).
- Reuse `format_card` for the result card; reuse `test_no_write_paths.py` guard.
- The demo reads the same `.env` credentials as the rest of the app.

### Size estimate
Small — roughly a half-day: ~1 new file, ~150–200 lines, no changes to scoring/
extraction/classification logic.

## Alternatives considered
- **Skip the UI, submit CLI + test account:** rejected — highest risk of
  access-based rejection; reviewers don't run repos.
- **Full dashboard:** explicitly out of scope per your instructions ("do not build
  a dashboard"). The reviewer UI is a *demo surface*, not a product dashboard.

## Bottom line
The reviewer UI is not gold-plating — it's the mechanism that makes the App Review
*testable*, which Meta requires. Build it **only after you approve STEP 4**, and
keep it minimal and read-only.
