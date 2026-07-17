# Dashboard v0.8.0 Implementation Plan

**Status:** Proposed; implementation requires separate approval

**Phase:** Product and visual design only

**Branch:** `feature/v080-professional-dashboard-redesign`
**Release target:** Professional desktop Streamlit dashboard at 1366×768 and 1920×1080

## 1. Scope and safety contract

This plan changes the dashboard presentation and its read-only presentation contracts only. It does not authorize implementation in this phase.

### Protected behavior — do not change

- Scheduler behavior, Windows Scheduled Task configuration, locks, reconciliation, or ledger writes.
- Classification, extraction, scoring, matching, or inventory-validation logic.
- Apify, Threads, Telegram, notification, delivery, or contact behavior.
- Database schema or migrations.
- Existing delivery and audit records.
- The Lead Detail write allowlist: only status, sanitized notes, and review timestamp remain editable through the existing audited repository path.

### Prohibited during implementation and acceptance

- Do not run the Windows task.
- Do not call Apify or Telegram.
- Do not add run, enable, disable, send, unlock, reconcile, install, rematch, or contact controls.
- Do not expose credentials, private author fields, chat IDs, usernames, host paths, or unsanitized source text.
- Do not display legacy or historical inventory identifiers as active supply, recommendations, KPIs, or export fields.
- Do not infer missing analytics values or a false-positive rate.

## 2. Delivery strategy

Build in eight small, independently reviewable stages, including the final merge gate. Each build stage ends with an offline verification checkpoint. Do not combine all page rewrites into one change.

Implementation should preserve the current no-`PYTHONPATH` launch behavior and use the installed Streamlit/Altair stack rather than introducing a new UI framework. Prefer native Streamlit controls for interaction and accessibility; isolate CSS overrides in the theme layer.

### Definition of done for every stage

1. The changed view renders from a fresh Streamlit process with `PYTHONPATH` unset.
2. No browser-visible traceback and no server traceback.
3. Empty, partial, normal, warning, and error states relevant to the stage are exercised with offline fixtures/mocks.
4. No protected behavior is changed.
5. Dashboard source remains free of network/delivery imports and private fields.
6. Keyboard order, visible focus, labels, and contrast are checked.
7. The targeted test set passes before moving on.

## 3. Stage 1 — Shared theme and components

### Goal

Create the **Signal Desk** shell and reusable presentation primitives before redesigning pages.

### Primary files

- `dashboard/app.py`
- `dashboard/theme.py`
- `dashboard/common.py`
- `dashboard/components.py`
- `dashboard/formatters.py`
- `dashboard/charts.py`
- Dashboard page bootstraps only where required for the shared shell
- `.streamlit/config.toml` only if a supported configuration is required to control nonessential Streamlit chrome

### Work items

1. Establish one canonical app entry/navigation model; eliminate the duplicate `app`/Overview destination.
2. Add the compact branded shell:
   - product identity;
   - grouped navigation;
   - active-page state;
   - read-only footer health summary;
   - page title/purpose region;
   - optional system status strip.
3. Implement design tokens from `DASHBOARD_V080_DESIGN_SYSTEM.md`:
   - colors;
   - typography;
   - spacing;
   - page widths;
   - radius;
   - borders;
   - focus ring;
   - limited elevation.
4. Replace broad page-specific HTML with reusable presentation components:
   - primary/compact KPI card;
   - semantic badge;
   - status strip item;
   - callout;
   - empty/loading/error state;
   - card header and fact row;
   - score indicator;
   - immutable-history treatment.
5. Define reusable table configuration and sanitized export helpers.
6. Define the shared Altair theme and chart-card wrapper; remove unnecessary pan/zoom on categorical charts.
7. Add formatting utilities for human-readable UTC timestamps, ages, counts, money, unavailable values, and confidence states.
8. Keep custom CSS selectors localized and documented. Do not build custom HTML controls.

### Presentation-contract notes

- Replace hardcoded refresh/database/inventory values with existing read-only repository values where available.
- If a shell status is unavailable from the current contract, render `Not available`; do not infer it and do not add a database migration.
- Any new repository helper must be read-only, sanitized, and kept in `rdsa/dashboard_repository.py`; business modules remain untouched.

### Targeted verification

- Component unit tests for badges, score indicator, state cards, formatters, and export columns.
- Theme token/contrast assertions for essential text and semantic states.
- Navigation test proving one Overview destination.
- Fresh-terminal imports for app and every page.
- Static safety tests for forbidden network/delivery imports, private fields, and active legacy IDs.

### Exit criteria

- Shared shell renders consistently on every page.
- No duplicate Overview navigation.
- No gradients, glow, excessive shadows, or animation.
- Red is limited to actual critical/error states.

## 4. Stage 2 — Overview

### Goal

Turn Overview into a ten-second operational brief rather than a wall of equal KPIs and charts.

### Primary files

- Canonical Overview page/entrypoint
- `dashboard/charts.py`
- `dashboard/common.py`
- `rdsa/dashboard_repository.py` only for separately approved, read-only presentation aggregation
- Overview/component/chart tests

### Work items

1. Render the compact header and system strip.
2. Limit the page to 6–8 KPIs:
   - needs review;
   - hot + qualified;
   - leads with active real matches;
   - delivered leads;
   - unknown/low-confidence records;
   - latest run state;
   - monthly cost versus threshold;
   - active inventory when width permits.
3. Give needs-review and high-signal demand primary weight; keep cost/inventory/run as compact supporting KPIs.
4. Implement the requested lead funnel only with defensible stage definitions and explicit denominators. If a strict sequential cohort cannot be produced from current data, label it as a stage/volume summary rather than implying conversion.
5. Add match-quality distribution: Exact, Nearby, Tentative, No match; exclude legacy records from active totals.
6. Add classification distribution as a supporting module.
7. Add a 5–8 row priority queue with age, classification, score, need, confidence/match warning, and a handoff to Lead Inbox/Detail.
8. Combine scheduler and cost health into one compact operational module.
9. Move location/property-type distributions and metric definitions into disclosure.
10. Remove hardcoded status/count text and redundant charts.

### Data fallback rules

- Missing count: `Not available`, not zero.
- Latest run fields missing: show data completeness state.
- No active inventory: withhold active match claims.
- Historical/legacy matches: excluded from active totals and IDs.

### Targeted verification

- KPI count is between six and eight.
- Funnel/stage labels include definitions and do not imply unsupported conversion.
- Priority queue excludes raw/private fields and historical inventory identifiers.
- Overview renders at both target desktop sizes without four narrow analytical columns.
- Empty database, unavailable inventory, incomplete run, and normal data snapshots.

### Exit criteria

An operator can identify health, review backlog, high-priority demand, match coverage, and cost/run posture within the first viewport.

## 5. Stage 3 — Lead Inbox and Lead Detail

### Goal

Create one continuous CRM-like review flow: queue → preview → evidence → confirmed local review update → preserved queue.

### Primary files

- `dashboard/pages/2_Lead_Inbox.py`
- `dashboard/pages/3_Lead_Detail.py`
- `dashboard/components.py`
- `dashboard/formatters.py`
- `rdsa/dashboard_repository.py` only for sanitized/read-only view-model support; preserve the existing write allowlist
- Inbox/detail/security tests

### Lead Inbox work items

1. Build a persistent compact filter bar:
   - search;
   - queue;
   - classification;
   - match tier;
   - area;
   - More filters;
   - reset.
2. Place status, property type, budget confidence, Telegram state, and date range in More filters.
3. Show active-filter chips, result count, sort mode, and one sanitized export action.
4. Reduce the default table to seven operational columns defined in the design system.
5. Configure widths, numeric formatting, date/age display, selected-row state, and hidden secondary columns.
6. At 1920×1080, use a queue/preview 7/5 or 8/4 split. At 1366×768, keep the table dominant and show a compact selected summary, with full preview below.
7. Preview classification, score, need, confidence warning, source excerpt, top active real match, and review state.
8. Provide an explicit handoff to Lead Detail while preserving filters, sort, and selected lead.
9. Export only approved sanitized display fields and the full filtered set; do not export raw text or legacy IDs.

### Lead Detail work items

1. Support Inbox-origin navigation with a clear back-to-queue path; retain a lead selector only as a secondary fallback.
2. Build an executive summary from stored display fields without generating new business conclusions.
3. Show source/extraction as semantic facts and sanitized read-only text.
4. Replace raw score JSON with point/reason rows and progressive disclosure.
5. Replace match dictionaries with active real inventory match cards and explicit no-match/legacy states.
6. Put review decision beside the executive summary at wide width and directly after it at compact width.
7. Replace manual raw ISO entry where native date/time widgets can preserve the existing value contract safely.
8. Before save, show exactly which allowlisted fields will change and require explicit confirmation.
9. Keep audit and Telegram records in separate immutable-history tabs with no action controls.
10. Preserve entered values on validation/write errors and show only sanitized error text.

### Targeted verification

- Filter combinations, reset, state persistence, row selection, and sort behavior.
- Sanitized export schema and filtered-row count.
- No raw source text in table/export; sanitized excerpt only in preview/detail.
- No author username, credentials, internal row IDs, or historical active inventory IDs.
- Review form writes only status, notes, and reviewed timestamp and creates the existing audit entry.
- Telegram/audit history has no edit, delete, resend, or contact affordance.
- Compact and wide master-detail browser acceptance.

### Exit criteria

A reviewer can triage, open, understand, safely update, and return to the same queue without losing context.

## 6. Stage 4 — Inventory and Matching Review

### Goal

Make real supply and match evidence comparable, while keeping pending/legacy states honest and inactive.

### Primary files

- `dashboard/pages/4_Inventory.py`
- `dashboard/pages/5_Matching_Review.py`
- Shared cards/fact rows/table helpers
- Inventory/matching/legacy-safety tests

### Inventory work items

1. Replace the normal success banner with a compact validation state.
2. Show active/pending/invalid counts only when the current validated read model supports them.
3. Use two property-card columns at 1366×768 and three at 1920×1080.
4. Prioritize title, area/type, monthly price, availability, and match activity.
5. Demote real inventory ID to metadata.
6. Distinguish Active, Pending listing, Missing link, and Invalid/withheld without inventing listing state.
7. Keep a compact comparison table with a different job from cards: sorting and cross-property comparison.
8. Never load or display fallback inventory.

### Matching Review work items

1. Keep five groups: Exact, Nearby, Tentative, No match, Legacy; add counts to labels.
2. Exclude Legacy from active totals and recommendations.
3. Use one aligned Lead vs Inventory comparison grid with a result column.
4. Separate positive evidence from warnings.
5. Make human-confirmation requirements explicit for nearby/tentative/uncertain comparisons.
6. Treat No match as an operational state, not a red system error; show missing/unknown blockers only when recorded.
7. Keep Legacy muted and historical; never expose its old inventory identifier in the primary view/export.
8. Add safe handoffs to Lead Detail and the selected real Inventory record.
9. Do not add rematch, inventory edit, or confirmation-write behavior.

### Targeted verification

- Missing, invalid, empty, pending, and normal inventory states.
- Only validated real IDs appear in active cards/table/comparisons.
- Each tier has correct count, tone, warning, and empty state.
- Side-by-side facts align and stack safely at compact widths.
- No matching or inventory-validation function is executed from a new action path.

### Exit criteria

Supply is easy to compare, and every match tier communicates evidence, uncertainty, and active/historical status without ambiguity.

## 7. Stage 5 — Pilot Analytics and Scheduler

### Goal

Deliver trustworthy operational analytics and scheduler observability without unsupported metrics or controls.

### Primary files

- `dashboard/pages/6_Pilot_Analytics.py`
- `dashboard/pages/7_Scheduler.py`
- `dashboard/charts.py`
- `rdsa/dashboard_repository.py` only for sanitized, read-only presentation data
- Analytics/scheduler visual and safety tests

### Pilot Analytics work items

1. Place data source/completeness status above all metrics.
2. Show latest run, new, eligible, delivered, run cost, cumulative/monthly cost, and reviewed denominator only when recorded.
3. Render missing run fields as gaps/Not recorded, never zero.
4. Validate count-like values before plotting; fractional or malformed lead counts become an explicit data-quality warning rather than a plotted count.
5. Use tabs: Yield, Cost, Quality, Run ledger.
6. Plot New/Eligible/Delivered by run only for available fields.
7. Plot cost by run and cumulative/monthly cost with warn/stop context where the read contract supplies it.
8. Show cost per eligible/delivered only when denominators are recorded and nonzero.
9. Use cumulative classification, budget confidence, and match-quality distributions with scope labels.
10. Show manual review coverage and `Insufficient reviewed sample` when the denominator is unavailable/inadequate.
11. Do not display a false-positive rate unless a future separately approved contract stores a defined sufficient reviewed denominator and outcome.
12. Remove charts whose titles do not match their actual series.

### Scheduler work items

1. Compute a presentation-only readiness verdict from the current sanitized read model:
   - Ready but disabled;
   - Running;
   - Attention required;
   - Unavailable.
2. Place unresolved interruption, failed run, lock conflict, or cost threshold breach immediately below the verdict.
3. Distinguish unresolved critical interruption from reconciled historical interruption.
4. Consolidate enabled/sending/Apify/Telegram/lock flags into one compact state row.
5. Present latest run, last successful run, lock, and cost posture without duplicate facts.
6. Humanize UTC timestamps and use `Not recorded` rather than `None / None` or ambiguous dashes.
7. Use Overview, Run ledger, and Failures & interruptions tabs.
8. If the existing sanitized repository contract cannot provide a full ledger, render a documented unavailable state. Do not change scheduler/database logic or schema to fill the design.
9. Preserve text-only out-of-band guidance only for unresolved operator-required reconciliation.
10. Keep the page strictly read-only: no action controls of any kind.

### Targeted verification

- Analytics missing/partial/malformed/manual data cases.
- Chart titles and series-field contracts.
- No false-positive rate text or calculation.
- Scheduler snapshots: ready-disabled, enabled-read-only, active lock, failed latest run, unresolved interruption, reconciled interruption, threshold warning, DB unavailable.
- Source assertion that Scheduler contains no run/enable/send/unlock/reconcile/install buttons or callbacks.
- No scheduler command, Windows task, Apify call, or Telegram call during tests.

### Exit criteria

Analytics communicates evidence quality honestly, and Scheduler exposes the most important state first while remaining demonstrably read-only.

## 8. Stage 6 — Browser acceptance

### Goal

Verify real rendered behavior at both target desktop sizes; HTTP 200 alone is not acceptance.

### Test matrix

| View | 1366×768 | 1920×1080 | Required states |
|---|---:|---:|---|
| Shared shell/navigation | Yes | Yes | active page, collapsed sidebar, long labels |
| Overview | Yes | Yes | normal, empty, system attention |
| Lead Inbox | Yes | Yes | no filters, filtered empty, selected row, long values |
| Lead Detail | Yes | Yes | no match, active matches, warnings, history empty/populated, write error |
| Inventory | Yes | Yes | normal, empty, missing, invalid/pending |
| Matching Review | Yes | Yes | all five tiers and empty groups |
| Pilot Analytics | Yes | Yes | complete, partial, malformed/missing run fields |
| Scheduler | Yes | Yes | normal disabled, failure, lock, interruption, unavailable |

### Acceptance checks

1. Launch a fresh process on a new port with `PYTHONPATH` unset.
2. Load root first and navigate in-session to every page.
3. Confirm no server `Traceback`, `ModuleNotFoundError`, or browser JavaScript error.
4. Record screenshots at exact 1366×768 and 1920×1080 for every page and key state.
5. Check above-the-fold requirements against `DASHBOARD_V080_WIREFRAMES.md`.
6. Check no horizontal page overflow; table overflow is bounded and intentional.
7. Verify long sanitized text, large budgets, missing values, and long timestamps do not break cards.
8. Keyboard-only pass: navigation, filters, tabs, table selection where supported, form, confirmation, save.
9. Focus ring and state-label pass.
10. Contrast pass for text, borders, controls, and charts.
11. Confirm only one sanitized export path is presented intentionally.
12. Confirm default Streamlit chrome is either safely suppressed or accepted/documented.
13. Inspect browser console for Altair warnings caused by invalid/empty domains; treat repeated infinite-domain warnings as defects.

### Evidence package

- Screenshot index by page, state, and viewport.
- Browser/server log summary.
- Accessibility/keyboard checklist.
- Known Streamlit limitations and accepted deviations.

## 9. Stage 7 — Tests and regression gate

### Goal

Prove the redesign is a presentation change and has not weakened operational safety.

### Targeted tests to add or update

- `tests/test_dashboard_components.py`
- `tests/test_dashboard_charts.py`
- `tests/test_dashboard_repository.py` for approved read-only presentation contracts
- `tests/test_dashboard_runtime_and_legacy.py`
- `tests/test_dashboard_security.py`
- `tests/test_dashboard_visual_safety.py`
- New browser/layout acceptance harness only if it remains deterministic and offline

### Required test categories

1. Component/state rendering.
2. Formatter behavior for missing/invalid/large values.
3. Chart data contracts, empty domains, and truthful labels.
4. Filter/export/select/state-persistence behavior.
5. Active-real-versus-legacy inventory boundaries.
6. Lead review write allowlist and audit behavior.
7. Scheduler read-only source assertions.
8. No network/provider/delivery imports.
9. Fresh terminal, page deep-link/import, and Streamlit boot behavior.
10. Snapshot/view-model tests for critical states.

### Offline commands

Run targeted tests after each stage, then the full suite from the repository root:

```bash
env -u PYTHONPATH python -m pytest -q tests/test_dashboard_components.py tests/test_dashboard_charts.py

env -u PYTHONPATH python -m pytest -q tests/test_dashboard_repository.py tests/test_dashboard_runtime_and_legacy.py tests/test_dashboard_security.py tests/test_dashboard_visual_safety.py

env -u PYTHONPATH python -m pytest -q
```

Browser acceptance uses only the local Streamlit server and offline local fixtures. It must not invoke Apify, Telegram, or the Windows task.

### Regression invariants

- Existing classification/extraction/matching outputs are unchanged.
- No database schema change.
- No new scheduler or delivery action path.
- No live provider call in app or tests.
- Existing lead review write path remains the only dashboard mutation.
- Legacy/historical inventory remains inactive and excluded.

## 10. Stage 8 — Merge gate

Implementation completion does **not** authorize commit, merge, tag, push, or release.

### Pre-merge evidence required

1. User-approved final screenshots at both target sizes.
2. All browser acceptance checks passed.
3. Full offline test suite passed from the final working tree.
4. `git diff --check` clean.
5. Diff limited to approved dashboard, read-only presentation-contract, test, configuration, and documentation files.
6. No secrets/private fields introduced.
7. Static proof of no scheduler/Apify/Telegram/delivery controls or calls.
8. Explicit list of Streamlit deviations/limitations accepted by the user.
9. Final `git status` and diff summary.

### Human gate

Stop and request explicit approval before any commit or merge. A visual approval does not automatically authorize merge. Do not tag or push unless separately requested.

## 11. Streamlit-specific implementation limitations

1. **Breakpoints are approximate.** `st.columns` responds to container width but does not provide a full responsive grid API. Layout must remain usable when columns stack.
2. **Sticky master/detail is constrained.** Avoid brittle JavaScript. At compact width, allow the preview to stack.
3. **Dataframe styling is limited.** Native dataframe cells do not reliably render custom HTML badges; use column configuration, concise state text, and selected-row context.
4. **Dataframe toolbar cannot always be productized fully.** If the native CSV action remains, document or intentionally differentiate it from the sanitized export; never assume CSS alone guarantees its removal.
5. **Custom CSS selectors are version-sensitive.** `data-testid` overrides are not a stable public API. Keep selectors isolated and test against the installed Streamlit version.
6. **Tabs may evaluate all content.** Cache/reuse read-only data and avoid per-tab side effects or expensive repeated queries.
7. **Reruns reset state unless managed.** Filters, selected lead, active tab, and return-to-queue context require deliberate keys/session state/query parameters.
8. **HTTP 200 is not render proof.** A Streamlit page can return 200 while showing an exception. Require clean server logs and real browser navigation.
9. **Deep links require per-page import bootstrap.** Preserve fresh-terminal/deep-link import behavior without assuming `PYTHONPATH`.
10. **Exact viewport-height fitting is not guaranteed.** Prioritize content order and disclosure over brittle fixed-height CSS.
11. **Altair empty/invalid domains can warn silently.** Sanitize chart inputs and use explicit empty states rather than constructing charts from unavailable values.
12. **Default chrome varies by runtime.** Suppress only nonessential artifacts through supported configuration or narrowly tested CSS; preserve accessibility and sidebar controls.

## 12. Delivery sequence and review checkpoints

| Stage | Deliverable | Review checkpoint |
|---|---|---|
| 1 | Shared shell, theme, primitives | Approve visual foundation before pages |
| 2 | Overview | Approve hierarchy/KPIs/charts |
| 3 | Inbox + Detail | Approve end-to-end review workflow |
| 4 | Inventory + Matching | Approve supply/match evidence model |
| 5 | Analytics + Scheduler | Approve truthfulness/read-only observability |
| 6 | Browser acceptance evidence | Approve both desktop layouts |
| 7 | Full tests/regression report | Confirm technical readiness |
| 8 | Merge gate | Explicit user approval required |

## 13. Phase 1 stop condition

The five v0.8.0 design documents are the complete Phase 1 deliverable. Do not begin Stage 1 implementation until the user explicitly approves the design direction and authorizes production-code work.