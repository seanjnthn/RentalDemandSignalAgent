# Dashboard v0.8.0 Information Architecture

**Product role:** Internal rental-demand intelligence and human lead-review workspace

**Primary user:** Operator/reviewer
**Primary job:** Identify the highest-value review work, understand the evidence, and record a safe review decision without triggering acquisition, matching, delivery, or scheduler behavior.

## 1. Proposed architecture

### 1.1 Navigation model

```text
Rental Demand Signal

MONITOR
  Overview
  Pilot Analytics
  Scheduler

REVIEW
  Lead Inbox
  Lead Detail
  Matching Review

SUPPLY
  Inventory

────────────────────
Database      Connected
Inventory     3 active
Scheduler     Disabled
Delivery      Disabled
```

Rules:

- Remove the duplicate `app` destination. There is one canonical Overview.
- Active page is indicated by a left rule, raised surface, icon, and text—not color alone.
- Navigation labels remain short and stable.
- Sidebar system states are read-only summaries, not controls.
- Page-specific filters live in the page header/filter bar, not permanently in the sidebar.

### 1.2 Shared page anatomy

1. Compact product/header shell.
2. Page title, one-sentence purpose, optional right-aligned safe action.
3. System status strip where operational context is relevant.
4. Page-specific primary task region.
5. Supporting evidence/analysis.
6. Historical or technical detail in tabs/expanders.

### 1.3 Core user flows

**Daily review**

```text
Overview attention state
  → Lead Inbox filtered to needs-review/high priority
  → selected-lead preview
  → Lead Detail
  → confirm status/note/review timestamp
  → audit record
  → next lead / return to preserved queue
```

**Match validation**

```text
Lead Detail match summary
  → Matching Review at selected tier/lead
  → compare lead vs real inventory
  → return to Lead Detail review form
```

**Operational monitoring**

```text
Overview scheduler/cost state
  → Scheduler read-only evidence
  → out-of-band operator process if action is required
```

**Inventory context**

```text
Lead/Match view inventory reference
  → Inventory selected property
  → read-only listing facts and match activity
```

## 2. Overview

### Purpose

Answer, in under 10 seconds:

1. Is the system healthy?
2. What needs review now?
3. How much qualified demand exists?
4. Is real inventory covering that demand?
5. Is the latest run/cost posture acceptable?

### Above the fold

- Compact branded page header and refresh time.
- System status strip: database, inventory, scheduler, monthly cost.
- 6–8 KPIs, with “Needs review” and “Hot + qualified” visually primary.
- Lead funnel or stage summary.
- Priority Leads queue preview (top 5–8).

### Content order

1. **Status strip**
2. **KPI strip**
   - Needs review
   - Hot + qualified
   - Active real matches
   - Delivered leads
   - Unknown/low-confidence
   - Latest run
   - Monthly cost / threshold
   - Active inventory (wide desktop only or combined with status strip)
3. **Demand and match health**
   - Requested lead funnel when a defensible sequential cohort is available; otherwise a clearly labeled stage/volume summary with independent denominators
   - Match-quality distribution: Exact, Nearby, Tentative, No match
4. **Priority leads**
   - ID/age, classification, score, need, budget confidence, top match/review reason
5. **Classification distribution**
6. **Run and cost health**
   - Compact latest-run summary + cost threshold progress

### Tabs/expanders

- `More distributions`: location and property type, only if useful.
- `Metric definitions`: KPI denominator/meaning.
- No raw run-log text in the main view.

### Remove/demote

- Duplicate Overview implementation.
- Six equal-sized charts.
- Location distribution from the first viewport.
- Hardcoded “Database connected” and inventory count.
- Long cost definition caption under the entire KPI grid.

### Strongest emphasis

- Review backlog.
- High-priority leads.
- Scheduler attention state or data-source failure.
- Match-quality gaps.

## 3. Lead Inbox

### Purpose

Operate as a CRM-like triage queue: filter, scan, select, preview, and open a lead without exposing unsanitized data.

### Above the fold

- Page title and filtered result count.
- Persistent compact filter bar.
- Queue/table with 8–12 visible rows.
- At 1920×1080: selected-lead preview fixed beside the table.
- At 1366×768: table dominates; preview appears beneath or in a clear secondary panel after selection.

### Filter architecture

**Always visible**

- Search sanitized fields
- Queue: All / Needs review / Hot / Unknown area
- Classification
- Match tier
- Area
- More filters
- Reset

**More filters**

- Status
- Property type
- Budget confidence
- Telegram delivery state
- First-seen date range

**Active filter summary**

- Removable text chips under the bar.
- Result count and sort mode shown together.

### Table architecture

Default columns:

1. Lead + age
2. Score
3. Classification
4. Need (area / type / bedrooms)
5. Budget + confidence
6. Match tier / warning
7. Review state

Secondary hidden columns:

- Budget period
- Telegram state
- Validated real property reference
- First/last seen

Do not expose:

- Raw text in the table/export.
- Author username/private contact data.
- Internal row IDs.
- Raw synthetic/legacy inventory IDs.

### Selected-lead preview

- Classification + score.
- Area, property need, budget/confidence.
- Sanitized source excerpt.
- Top active real match and warning.
- Review status/age.
- **Open lead detail** secondary action.

### Export

- One action: **Export sanitized results**.
- Export exactly the filtered result set and approved display columns.
- Filename includes date/time but no private identifier.
- Clearly distinguish from Streamlit’s native dataframe download if it cannot be disabled.

### Tabs/expanders

- Avoid tabs for the main queue.
- Use “More filters” expander/popover.
- Optional `Columns` configuration through native dataframe tools.

### Remove/demote

- Seven always-visible filters.
- Separate selected-lead selectbox.
- Duplicate export affordance.
- Low-value table columns from the default view.

### Strongest emphasis

- Selected row.
- Review-required reason.
- Classification + score.
- Confidence/match warnings.

## 4. Lead Detail

### Purpose

Provide one complete, evidence-based review workspace and the only allowed dashboard write path: status, note, and review timestamp.

### Above the fold

- Back to preserved Inbox queue.
- Lead identity with classification, score, status, age, and source link state.
- Executive summary: intent, area, type, bedrooms, budget/confidence, top warning.
- Best active real match or explicit no-match state.
- Review decision panel at wide desktop; immediately after summary at compact desktop.

### Content architecture

**Header summary**

- Lead safe ID (secondary)
- Classification badge
- Score + rule count
- Current review state
- First seen/age

**Executive summary**

- 2–4 sentence synthesis using already stored/displayed fields only.
- Need facts: area, property type, bedrooms, budget, period, confidence.
- Extraction warnings/unknowns.

**Source & extraction panel**

- Sanitized source excerpt.
- Public source URL state.
- Extracted fields shown as labeled fact rows.
- No unsanitized author/contact information.

**Score explanation**

- Total score.
- Each rule as `+points · reason` row.
- No raw JSON.
- Collapsed by default after the first 3 contributors if lengthy.

**Match cards**

Each active match shows:

- Validated real property title/reference.
- Tier and score.
- Price, area, type, bedrooms, availability.
- Aligned/misaligned reasons.
- Warnings and confirmation requirement.
- Link to Matching Review.

Legacy matches appear only in a muted historical disclosure and never as recommendations.

**Review workflow**

- Status selector.
- Notes.
- Review timestamp with safe default/current value; no requirement to type raw ISO when a suitable widget is possible.
- Change summary.
- Explicit confirmation naming the exact local dashboard write.
- Save review.

**Immutable history**

- `Audit history` tab: chronological status transitions and sanitized notes.
- `Telegram history` tab: sent time, channel, immutable message ID state.
- No resend/edit/delete controls.

### Tabs/expanders

Recommended secondary tabs:

- Evidence
- Audit history
- Telegram history

Expanders:

- Full score explanation
- Historical/legacy matches
- Sanitized technical metadata

### Remove/demote

- Lead selector as the primary navigation mechanism when arriving from Inbox.
- Raw JSON score breakdown.
- Raw match dictionaries.
- Repeated summary facts.
- Generic checkbox wording (“Confirm dashboard-only update”).

### Strongest emphasis

- Executive summary.
- Unknown/low-confidence fields.
- Best match and confirmation warning.
- Exact fields that will be saved.

## 5. Inventory

### Purpose

Show validated real supply, availability, price, and match activity without creating or editing inventory.

### Above the fold

- Inventory validation state and active/pending counts.
- Property card grid:
  - 2 columns at 1366×768
  - 3 columns at 1920×1080
- First row shows price, area, availability, and active match count.

### Property card anatomy

- Property title and type.
- Area.
- Monthly price; annual asking as secondary if recorded.
- Bedrooms/furnishing.
- Availability state/date.
- Active match count and tier mix if already available.
- Listing state: Active / Pending listing / Missing link.
- Real inventory ID as subdued metadata, not the headline.

### Compact table

Purpose: comparison and sorting, not repetition.

Columns:

- Property
- Area/type
- Bedrooms
- Monthly price
- Availability
- Match activity
- Listing state

### Tabs/expanders

- `Cards` / `Table` tabs are optional if vertical length becomes excessive; otherwise show cards first and keep table compact.
- Property-level `Details` expander for features/listing metadata.

### Empty/error states

- Missing real inventory: amber warning, zero active recommendations, no fallback.
- Validation failure: red only if active recommendation safety is blocked.
- Pending listing: amber/muted state; excluded from active recommendation where the existing validated data contract requires it.

### Remove/demote

- Full-width one-card-per-row layout.
- Normal-state full-width success banner.
- Synthetic or legacy inventory of any kind.
- Property ID as primary card title.

### Strongest emphasis

- Availability.
- Price.
- Area/property type.
- Match activity.
- Pending/invalid listing state.

## 6. Matching Review

### Purpose

Let the operator compare lead demand against real inventory and understand why a match is Exact, Nearby, Tentative, No match, or Legacy.

### Above the fold

- Tier tabs with counts:
  - Exact
  - Nearby
  - Tentative
  - No match
  - Legacy
- Selected comparison header with tier, score, and confirmation state.
- Side-by-side aligned Lead vs Inventory facts.

### Tier semantics

| Tier | Meaning | Treatment |
|---|---|---|
| Exact | Core recorded criteria aligned | Teal |
| Nearby | Alternative area/location relationship | Amber; confirm suitability |
| Tentative | One or more uncertain/weak fields | Amber; stronger warning copy |
| No match | No active real inventory recommendation | Neutral/amber, not system error |
| Legacy | Historical inactive record | Muted; excluded from active totals |

### Comparison anatomy

```text
Criterion         Lead                    Inventory              Result
Area              BSD                     Gading Serpong          Nearby
Property type     Apartment               Apartment               Aligned
Bedrooms          1                       1                       Aligned
Budget / rent     IDR 8m monthly          IDR 7.5m monthly        Within
Availability      Needed now              Available 20 Jul        Confirm
```

Then show:

- Match score.
- Reasons as positive evidence.
- Warnings as separate amber/red callouts.
- Explicit “Human confirmation required” state where applicable.
- Link back to Lead Detail and selected Inventory record.

### No-match view

- Lead requirement summary.
- Why no active real recommendation exists, if recorded.
- Unknown fields that may block matching.
- No invented alternative and no rematch button.

### Legacy view

- Historical record label and safe lead ID.
- No active property card or active recommendation styling.
- Explanation that legacy data is retained only for audit/history.
- No raw synthetic inventory IDs in the primary UI or export.

### Tabs/expanders

- Tabs are the primary tier navigation.
- Reasons and warnings remain visible.
- Technical match metadata may be an expander.

### Remove/demote

- Raw dictionaries.
- “No match matches” wording.
- Legacy data in active counts.
- Confirmation requirement as a Boolean field.

### Strongest emphasis

- Differences between lead and inventory.
- Nearby/tentative warning.
- Real inventory identity.
- Human-confirmation requirement.

## 7. Pilot Analytics

### Purpose

Evaluate run trends, acquisition cost, lead yield, delivery yield, and manual quality-review coverage without making unsupported quality claims.

### Above the fold

- Data-quality note: source and latest recorded run.
- Compact KPIs:
  - Latest run state
  - New leads
  - Eligible leads
  - Delivered leads
  - Latest run cost
  - Cumulative/monthly cost
  - Reviewed denominator / quality state (only if recorded)
- Primary trend: New vs Eligible vs Delivered by run.
- Cost by run with warn/stop context if available.

### Content architecture

1. **Run yield**
   - New, eligible, delivered trends.
   - Explicit missing-data gaps; no zero substitution for unavailable fields.
   - Non-negative integer validation for count-like fields; fractional or ambiguous parsed values are withheld and flagged.
2. **Cost**
   - Cost per run.
   - Cumulative/monthly cost.
   - Cost per eligible/delivered only with nonzero denominators; otherwise “Not available.”
3. **Demand quality**
   - Classification distribution for current cumulative data.
   - Budget confidence distribution.
   - Match-quality distribution.
4. **Quality review state**
   - Reviewed count / eligible review population.
   - “Insufficient reviewed sample” if denominator is missing or too small.
   - No false-positive rate unless the definition and denominator are explicit and stored.
5. **Run ledger table**
   - Run, timestamp/state, raw, normalized, new, eligible, delivered, cost, data completeness.

### Tabs/expanders

- Tabs: `Yield`, `Cost`, `Quality`, `Run ledger`.
- Expander: metric definitions and manual-log limitations.
- Raw `PILOT_LOG.md` text is not displayed.

### Remove/demote

- Charts titled as classification/match-tier trends when the run data only contains new lead counts.
- Latest-run funnel when the recorded fields are incomplete.
- Six equal charts in one continuous page.
- Any misleading false-positive metric.

### Strongest emphasis

- Trend by run.
- Missing/incomplete run data.
- Cost threshold.
- Reviewed denominator and honest quality state.

## 8. Scheduler

### Purpose

Provide strictly read-only operational observability for readiness, enabled state, latest run, lock, ledger, costs, failures, and interrupted runs.

### Non-negotiable interaction boundary

The page has **no**:

- Run button
- Enable/disable control
- Send control
- Unlock control
- Reconcile control
- Install-task control
- Windows task execution

Out-of-band CLI guidance may be shown as text only when existing policy requires it.

### Above the fold

1. Overall readiness verdict:
   - Ready but disabled
   - Running
   - Attention required
   - Unavailable
2. Critical alert, if any:
   - unresolved interrupted run
   - failed latest run
   - held/stale lock
   - threshold breach
3. Compact state row:
   - Scheduler enabled
   - Scheduled sending
   - Apify live
   - Telegram send
   - Lock
4. Latest run summary and cost posture.

### Content architecture

**Readiness card**

- Overall verdict.
- Code readiness.
- Expected disabled/enabled state.
- “Read-only” badge.

**Latest run**

- Status.
- Started/finished/duration.
- Current/last phase where recorded.
- Raw/new/eligible/sent values, with “Not recorded” instead of `None`/dash ambiguity.
- Sanitized failure detail.

**Lock**

- Free / held.
- Sanitized run reference, process state, started time when available.
- No unlock action.

**Cost**

- Monthly usage.
- Warn and stop thresholds.
- Remaining budget and threshold status.

**Interrupted/failure state**

- Appears immediately below readiness when unresolved.
- Reconciled historical interruptions are amber/muted history, not current critical alerts.
- Out-of-band CLI instruction is shown only for an unresolved required reconciliation.

**Ledger**

- Latest scheduled runs table.
- Status, trigger, start/finish, phase, raw/new/eligible/sent, cost, sanitized failure.
- If the current read-only presentation contract cannot supply a full ledger, show a clear data-unavailable state; do not modify scheduler/database logic merely to fill the design.

### Tabs/expanders

- Tabs: `Overview`, `Run ledger`, `Failures & interruptions`.
- Expander: state definitions and out-of-band operator guidance.
- Keep current critical alert outside tabs.

### Remove/demote

- Duplicate current flags and top metrics.
- Repeated read-only policy paragraphs.
- Raw ISO timestamps when a human-readable timestamp can be shown with UTC retained.
- `None / None` and ambiguous dash values.

### Strongest emphasis

- Overall readiness.
- Unresolved interruption/failure.
- Lock state.
- Latest run.
- Cost vs thresholds.

## 9. Above-the-fold summary

| Page | Must be above the fold |
|---|---|
| Overview | Status, priority KPIs, funnel/stage, priority leads |
| Lead Inbox | Filter bar, queue/table, selected preview at wide desktop |
| Lead Detail | Executive summary, warnings, best match, review decision |
| Inventory | Validation/counts and first property-card row |
| Matching Review | Tier counts and first complete side-by-side comparison |
| Pilot Analytics | Data-quality state, yield KPIs/trend, cost posture |
| Scheduler | Readiness, critical alert, flags, latest run/cost |

## 10. Content moved into tabs/expanders

| Content | Destination |
|---|---|
| Score rule details | Lead Detail score expander |
| Full sanitized source/extraction metadata | Lead Detail Evidence tab |
| Audit and Telegram history | Separate immutable tabs |
| Legacy matches | Historical expander/tab |
| Optional location/property distributions | Overview “More distributions” |
| Inventory details/features | Property detail expander |
| Analytics metric definitions/manual-log caveats | Definitions expander |
| Scheduler ledger/history | Ledger and Failures tabs |

## 11. Content removed

- Duplicate Overview/app destination.
- Raw JSON/dictionary output.
- Hardcoded operational counts/status.
- Red treatment for priority leads/no-match states.
- Repeated scheduler flags and policy copy.
- Unsupported chart claims.
- Duplicate CSV export.
- Synthetic/legacy inventory IDs from active views and exports.
- False-positive rate without a stored, sufficient review denominator.

## 12. Data and behavior guardrails

- All changes remain in the presentation layer unless a separately approved, read-only dashboard presentation contract is required.
- Do not alter classification, extraction, matching, inventory validation, scheduler, Telegram, Apify, database, or delivery behavior.
- Do not run the Windows task.
- Do not call Apify or Telegram.
- Lead Detail preserves the existing allowlisted dashboard review write only; no new write fields or side effects.
- Scheduler remains strictly read-only.
- Missing analytics or ledger fields must degrade honestly rather than being inferred or backfilled.