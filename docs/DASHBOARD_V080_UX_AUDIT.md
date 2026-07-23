# Dashboard v0.8.0 UX Audit

**Phase:** Product and visual design only

**Scope:** `dashboard/` Streamlit application and existing dashboard documentation/tests

**Branch:** `feature/v080-professional-dashboard-redesign`
**Safety boundary:** No scheduler, classification, extraction, matching, Telegram, Apify, database, or delivery logic changes are proposed in this document.

## 1. Audit method

The audit covered:

- `dashboard/app.py`, shared theme/components/formatters/charts, and all seven page modules.
- Existing dashboard specifications, data map, guide, design system, UX audit, and wireframes.
- Dashboard repository presentation contracts and dashboard-specific tests.
- A local read-only Streamlit render, inspected in-browser across all seven pages. The server started with `PYTHONPATH` unset, emitted no Python traceback, and was stopped after inspection.
- No tracked PNG, JPG, WebP, GIF, or SVG dashboard screenshots were found. The live layout was therefore the primary visual reference.
- Browser-console inspection found repeated Altair/Vega warnings for interactive categorical scales and empty/infinite value domains. These are not visible Python failures, but they indicate chart input/interaction states that need explicit empty-domain handling.

## 2. Executive assessment

The current dashboard is functionally broad and safer than a typical prototype, but it still reads as a styled Streamlit diagnostic surface rather than a professional intelligence workspace. It has the right pages and many of the right concepts, yet lacks a consistent operational hierarchy: system health, review urgency, lead quality, and exceptions compete for attention.

The primary design problem is not missing data. It is **weak prioritization and presentation**:

1. The default Streamlit shell remains visible and unbranded (`app` navigation item, Deploy button, main menu, heading anchors, generic widget language).
2. Overview presents eight same-weight KPI cards followed by six same-size charts; nothing clearly answers “what needs attention now?”
3. Lead Inbox spends too much vertical space on filters and puts the selected-lead preview below the table instead of beside it.
4. Lead Detail renders score components and match facts as raw dictionary/JSON structures, creating a long, technical reading path.
5. Inventory cards are full-width stacked records, so only a small number can be compared at once.
6. Matching Review is conceptually correct but raw dictionaries undermine the intended side-by-side comparison.
7. Pilot Analytics contains redundant or incorrectly titled chart concepts; current `classification_by_run` and `tiers_by_run` both plot only “new leads.”
8. Scheduler repeats enabled/disabled and lock information across several sections, while the interrupted run—the highest-severity operational fact—appears below the fold.
9. The inspected Pilot Analytics view plotted a fractional `0.7` as a lead count for the latest run, demonstrating that manual-log parsing can yield semantically invalid count data unless the presentation validates and qualifies it.

## 3. Severity summary

| Severity | Finding | Operational effect |
|---|---|---|
| Critical | None found in the visual layer | Existing safety constraints remain explicit. |
| High | Review urgency is not visually prioritized | Operators must scan multiple cards/charts/pages to find actionable leads or warnings. |
| High | Raw JSON/dictionary rendering on Lead Detail and Matching Review | Slows comprehension and looks unfinished; field relationships are unclear. |
| High | Scheduler critical state appears below duplicated status blocks | Interrupted/failing states can be missed. |
| High | Analytics labels can imply data not actually plotted | Reduces trust in the dashboard. |
| High | Count-like analytics can accept fractional/misparsed manual-log values | Produces authoritative-looking but semantically invalid charts. |
| Medium | Inbox filters consume excessive vertical space | The core table and selected lead lose above-the-fold space. |
| Medium | Same visual weight for primary and secondary KPIs | Important signals are diluted. |
| Medium | Navigation exposes default Streamlit artifacts and duplicate `app`/Overview entries | Weakens orientation and perceived product quality. |
| Medium | Wide dataframes hide trailing columns and rely on horizontal interaction | Review state, delivery, and match information are easy to miss. |
| Low | Inconsistent capitalization and labels (`Lead inbox`, `No match matches`) | Reduces polish and clarity. |

## 4. Heuristic audit

### 4.1 Visual hierarchy

**Current weaknesses**

- Page title, caption, KPIs, charts, and tables use near-equal spacing and contrast.
- KPI cards are uniform even when their importance differs. “Total leads” competes equally with “Cost per contacted lead.”
- Overview’s four-column chart row and app entrypoint’s two chart rows create a wall of equally sized visualizations.
- Scheduler’s critical interrupted run is subordinate to duplicated flags and cost metrics.
- Lead Detail’s first meaningful interpretation is pushed down by eight facts and an expanded raw score breakdown.

**Direction**

- Establish three layers: page identity → operational status/priority → supporting analysis.
- Limit Overview to one dominant “needs attention” path, 6–8 KPIs with two weight levels, and four high-value visual modules.
- Use red only for blocking/critical conditions, not ordinary high-scoring leads.

### 4.2 Navigation

**Current weaknesses**

- Streamlit auto-navigation shows `app` plus `Overview`, creating two overview-like destinations.
- Navigation is a plain list with no grouping, active-state treatment, or product identity.
- Sidebar behavior is inconsistent: Overview adds filters and system badges; other pages have only navigation.
- Lead Inbox selection does not naturally carry into Lead Detail.

**Direction**

- Use a compact branded sidebar with grouped navigation:
  - **Monitor:** Overview, Pilot Analytics, Scheduler
  - **Review:** Lead Inbox, Lead Detail, Matching Review
  - **Supply:** Inventory
- Keep system-wide health at the sidebar footer, not page-specific filter widgets.
- Provide clear “Open detail” and “Review match” handoffs through session state/query parameters where Streamlit supports them.

### 4.3 Readability

**Current weaknesses**

- Long technical captions carry policy explanations that compete with the task.
- Raw dictionaries use code-like punctuation instead of labeled rows.
- Currency, dates, and identifiers vary in visual weight; ISO timestamps are not humanized.
- Lead identifiers are often the dominant label although they are not meaningful to operators.
- Some observed budgets appear implausible or ambiguous; the UI does not visually foreground low/unknown confidence.

**Direction**

- Use sentence-case labels, aligned values, human-readable dates, tabular numerals, and visible confidence/warning treatments.
- Show source ID as secondary metadata; lead summary should begin with classification, score, area, property need, and age.
- Replace dictionaries with semantic fact rows, reason lists, and warning callouts.

### 4.4 Information density

**Current weaknesses**

- Inbox has search, pills, seven filters, reset, section heading, table, export, selector, and preview in one vertical stack.
- Lead Detail serializes all score rules inline before source, matches, and workflow.
- Scheduler repeats the same flag states in KPI cards and “Current flags.”
- Inventory stacks one full-width card per property before repeating the data in a table.

**Direction**

- Prefer progressive disclosure: core facts visible; raw/source metadata, audit, and historical detail in tabs or expanders.
- Keep persistent filters to one compact row plus an “More filters” popover/expander.
- Use tables for scanning and a fixed/adjacent preview pane for interpretation.

### 4.5 Spacing

**Current weaknesses**

- The theme defines a scale but page modules do not consistently use it.
- Repeated `section()` headings add vertical gaps even when a compact divider/label would suffice.
- Native Streamlit widgets introduce inconsistent internal heights and margins.
- Full-width stacked inventory/match containers produce excessive scrolling.

**Direction**

- Adopt a 4/8/12/16/24/32/48 px spacing scale.
- Use 24 px between major sections, 16 px inside cards, and 8–12 px between related facts.
- Cap content width and reduce top padding to preserve the first viewport.

### 4.6 Typography

**Current weaknesses**

- Most typography remains Streamlit/browser default.
- The title-to-section scale is shallow; card labels and captions are visually similar.
- Numerical KPIs do not consistently use tabular figures.
- Badges use a 650 weight, but body hierarchy lacks an equivalent systematic scale.

**Direction**

- Use Streamlit’s system sans stack for reliability, with a defined 12/13/14/16/20/28/36 px scale.
- Reserve 36 px for the Overview display title at large desktop; use 28 px page titles elsewhere.
- Use 12–13 px uppercase-free metadata labels and tabular numerals for scores, money, and counts.

### 4.7 KPI design

**Current weaknesses**

- Eight KPIs are displayed as two undifferentiated rows.
- No KPI indicates review backlog, stale leads, scheduler exception, or unknown-quality data—the items most likely to require action.
- Cost explanation is a long caption detached from the metric.
- “Target area” is derived as total minus unknown and can be mistaken for a quality score.

**Direction**

- Use 6–8 metrics maximum:
  1. New leads requiring review
  2. Hot + qualified leads
  3. Leads with active real matches
  4. Delivered leads
  5. Unknown/low-confidence records
  6. Latest run state
  7. Monthly cost / threshold
  8. Active inventory (optional at 1920 px)
- Pair values with a short denominator or state, not decorative deltas that lack historical meaning.
- Use semantic accent only when the KPI represents a state requiring interpretation.

### 4.8 Table usability

**Current weaknesses**

- Lead table has ten columns; at the inspected viewport only columns through Status were immediately visible.
- Classification/status are plain text inside the native dataframe, so badge semantics disappear in the main scanning surface.
- Table selection and preview use a separate selectbox below the table rather than row selection.
- The custom export button sits after the table while Streamlit also exposes a built-in dataframe CSV action, creating duplicate export affordances.
- Inventory repeats cards and table without a clear distinction in purpose.

**Direction**

- Define a compact primary column set and hide secondary columns by default.
- Pin/select the lead identity column where Streamlit supports it; use single-row selection to update the preview pane.
- Use column configuration for numeric progress, dates, status text, links, and widths.
- Provide one clearly labeled **Export sanitized results** action and document that exports mirror current filters.
- Never include raw source text, private author data, or legacy/synthetic inventory IDs in exports.

### 4.9 Chart usefulness

**Current weaknesses**

- Six equal charts on the app entrypoint exceed the value of the available evidence.
- Location distribution is lower priority than review backlog or priority leads.
- `classification_by_run` and `tiers_by_run` currently plot the same “new leads” series despite different titles.
- `raw_normalized_new_funnel` uses only the latest parsed run and can display incomplete/manual values without a visible data-quality qualifier.
- The inspected latest-run chart rendered `0.7` as “New,” a strong signal that version/cost text can be misread by the permissive log parser and should not be presented as a lead count without validation.
- Every chart is `.interactive()`, adding pan/zoom where it provides little benefit.
- Overview funnel combines all leads, hot+qualified, and Telegram delivered even though these are not necessarily a strict sequential cohort.

**Direction**

- Use charts only for comparison or trend questions:
  - lead stages with clearly defined denominators
  - classification distribution
  - match-quality distribution
  - new/eligible/delivered by run
  - cost by run with threshold reference
- Use direct labels and tooltips; remove redundant legends.
- Disable zoom/pan for compact categorical charts; retain hover and selected run highlighting.
- If required fields are unavailable, show an honest “data not recorded” state rather than inferring a metric.
- Treat count fields as non-negative integers at the presentation boundary. Fractional, malformed, or ambiguous values become `Invalid source value`/`Not recorded`, not plotted data.
- Resolve repeated Altair/Vega empty-domain and scale-binding warnings through explicit empty states and interaction appropriate to the chart type.

### 4.10 Lead-review workflow

**Current weaknesses**

- Inbox and detail feel like separate reports rather than one review workflow.
- “Needs review” is defined only as `status == new`; no visible reason or age is shown.
- Selected preview is below a long table and does not expose next actions.
- Detail editing requires manual ISO entry for reviewed time and a generic confirmation checkbox.
- Audit and Telegram history appear as separate full tables at the bottom without immutable-history framing.

**Direction**

- Make Inbox the queue and Detail the decision workspace.
- Preserve filters and selected lead when moving between views.
- Preview should show summary, warning reason, top match, source excerpt, and clear **Open lead detail** action.
- Review form should separate reversible status selection from confirmation; explain exactly what will be written.
- Audit and Telegram delivery should be visually immutable, chronological, and subordinate to the current review.

### 4.11 Responsive desktop behavior

**Current weaknesses**

- Four-column sections become narrow at laptop widths.
- Native Streamlit columns wrap/stack based on available width but offer limited breakpoint control.
- Wide dataframes require horizontal scrolling; selected preview cannot remain adjacent at smaller widths.
- Sidebar filters further reduce content width on Overview.

**Direction**

- Design two explicit desktop modes:
  - **1366×768:** 2-column KPI rows, 2-column analysis modules, inbox preview below/overlay if needed.
  - **1920×1080:** 4-column KPI row, wider two-column analysis, persistent inbox master/detail split.
- Treat widths below 1180 px as compact desktop: collapse lower-priority columns and stack comparisons.
- Do not promise pixel-perfect breakpoint behavior Streamlit cannot guarantee.

### 4.12 Status and alert clarity

**Current weaknesses**

- “Hot lead” is mapped to red, conflating business priority with system error.
- Success banners are used for ordinary validated inventory state, consuming high-salience color.
- Scheduler “enabled no,” “off,” and “free” states repeat without a single readiness verdict.
- Reconciled interrupted runs use warning styling while unresolved runs use error styling, but both sit late in the page.

**Direction**

- Teal: confirmed/healthy/validated/exact.
- Amber: needs human review, nearby/tentative, low-confidence, disabled-but-expected.
- Red: broken, unresolved interruption, failed validation, blocked operation only.
- Muted gray: historical, disabled, unavailable, legacy.
- Priority leads use neutral surfaces with score/classification emphasis—not red error styling.

### 4.13 Accessibility

**Current weaknesses**

- Semantic meaning relies heavily on color in badges.
- Custom HTML cards and badges need explicit text and focus behavior; they are not interactive elements.
- Small 12 px badge text and muted copy can become difficult at lower brightness.
- Raw JSON structures produce noisy screen-reader output.
- Default chart accessibility is present through Vega, but long generated descriptions can be overwhelming.

**Direction**

- Every semantic color is paired with a text label and, for critical state, an icon.
- Minimum 4.5:1 contrast for normal text and 3:1 for large text/UI boundaries.
- Maintain visible focus rings, keyboard order, and 40 px minimum interactive height.
- Do not put actions inside custom HTML; use native Streamlit controls with accessible labels.
- Give charts concise titles and adjacent textual summaries.
- Respect reduced-motion settings; the design requires no animation.

### 4.14 Default Streamlit visual artifacts

Observed artifacts include:

- Deploy button and main menu in the header.
- Duplicate `app` and Overview navigation entries.
- Automatic anchor-link icons beside headings.
- Native widget labels, dataframe toolbar, and generic info/success/warning blocks.
- Canvas-based dataframe behavior and Vega toolbars that feel external to the product.
- Default sidebar collapse control and large top chrome.

**Direction**

- Configure navigation intentionally (prefer `st.navigation`/`st.Page` if compatible with the pinned Streamlit version).
- Hide only nonessential chrome through supported configuration/CSS, while preserving keyboard and accessibility behavior.
- Style—not replace—native controls where possible. Avoid brittle selectors as the primary architecture.
- Keep one export path; suppress or clearly account for duplicate dataframe actions if supported.

## 5. Page-specific current weaknesses

### Overview

- `dashboard/app.py` and `pages/1_Overview.py` duplicate Overview with different chart sets and header metadata.
- Eight same-weight KPIs and four-to-six charts create dashboard wallpaper.
- “Last refreshed,” database status, and active inventory are partly hardcoded in the app entrypoint.
- Priority lead table lacks age, review reason, and an explicit open/review path.

### Lead Inbox

- Filter controls dominate the first viewport.
- Selected-lead preview is disconnected from table selection.
- Separate custom export plus dataframe export is duplicative.
- Table truncates key columns on laptop desktop.
- No saved view, filter summary, review age, or explicit queue ordering.

### Lead Detail

- Score breakdown is raw JSON and can consume several screens.
- Summary facts are repeated again in source/match sections.
- Match cards use raw dictionaries.
- Manual ISO input is error-prone.
- Audit and Telegram history need clearer immutable treatment and empty states.

### Inventory

- “Validated” success banner is too visually loud for a normal state.
- Three full-width stacked cards do not support comparison.
- IDs are overemphasized; availability and match activity should be easier to scan.
- Cards and table repeat the same facts without distinct jobs.

### Matching Review

- Tab model is correct, but tab counts are missing from labels.
- Side-by-side columns contain raw dictionaries rather than aligned fact rows.
- “No match matches” is awkward language.
- Reasons, warnings, and confirmation requirement lack a clear evidence hierarchy.
- Legacy is correctly separated but should remain visually muted and excluded from active totals.

### Pilot Analytics

- Six charts exceed the quality of the recorded per-run data.
- Chart titles and implementation are not always aligned.
- Latest-run funnel can imply precision despite missing manually recorded fields.
- Review quality is described only as a boundary statement; there is no visible reviewed/unreviewed denominator.
- Cost lacks threshold context in the chart itself.

### Scheduler

- Read-only safety is clear and must remain.
- Status is duplicated across top metrics and current flags.
- Latest run, last successful run, and interrupted run are separated even though they form one operational narrative.
- Critical interruption is below the fold.
- Raw ISO timestamps and `None` values weaken scanability.
- The page should never expose run, enable, send, unlock, reconcile, or install controls.

## 6. Current duplication

1. `dashboard/app.py` and `dashboard/pages/1_Overview.py` both implement Overview.
2. Overview KPI values and chart concepts repeat analytics content.
3. Scheduler enabled/disabled and lock states repeat in KPIs, flags, lock section, and footer copy.
4. Inventory cards and table repeat identical facts without separate primary/secondary purposes.
5. Inbox exposes two CSV affordances: custom sanitized export and native dataframe download.
6. Lead summary facts reappear in match/source dictionaries.
7. Read-only/safety policy text is repeated across captions rather than concentrated into the shell and relevant confirmations.

## 7. What deserves stronger emphasis

- New/high-priority leads awaiting review.
- Unknown or low-confidence extraction requiring human confirmation.
- Match tier and warnings, especially Nearby and Tentative.
- Unresolved scheduler interruption, failed latest run, held lock, or threshold breach.
- Current selected lead and the next safe review action.
- Inventory unavailable/pending state.
- Data-quality boundaries in Pilot Analytics.

## 8. What should be removed or demoted

- Duplicate app/Overview destination.
- Low-value Overview location chart from the first viewport.
- Repeated system policy captions.
- Raw dictionary/JSON rendering.
- Generic normal-state success banners.
- Repeated scheduler flag blocks.
- Charts whose titles are unsupported by the underlying fields.
- Synthetic/legacy IDs from all active tables, exports, KPIs, and recommendations.
- Any false-positive rate without a valid manually reviewed denominator.

## 9. Design conclusion

The next version should feel like a **calm operational signal desk**: neutral navy surfaces, disciplined typography, one clear queue, and restrained semantic color. The redesign must improve interpretation without changing protected behavior. Where data is missing or historically incomplete, the visual system should say so plainly rather than fill the gap with an inferred metric.