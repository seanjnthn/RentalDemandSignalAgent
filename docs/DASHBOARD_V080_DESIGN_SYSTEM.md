# Dashboard v0.8.0 Design System

**Design concept:** **Signal Desk** — a calm, high-trust internal intelligence workspace optimized for scanning, review, and exception handling.

**Platform:** Streamlit desktop application
**Design posture:** Dark neutral foundation, minimal decoration, restrained semantic color, no gradients, no ornamental motion.

The inspected local environment uses Streamlit 1.59.1 and Altair 6.2.2. Implementation must verify version-sensitive navigation, dataframe-selection, styling, and chart behavior against these installed versions rather than assuming older Streamlit behavior.

## 1. Principles

1. **Operational before ornamental.** Every visible element should answer status, priority, evidence, or next safe action.
2. **Calm by default; loud only when blocked.** Normal operation is neutral. Teal confirms. Amber asks for review. Red is reserved for errors and critical warnings.
3. **Evidence over assertion.** Scores, match tiers, delivery state, and analytics always show their denominator, reason, or data-quality boundary.
4. **Progressive disclosure.** Summaries stay visible; technical evidence, raw/source details, and history move into tabs or expanders.
5. **Native accessibility first.** Prefer Streamlit controls and semantic text over custom HTML interactions.
6. **Read-only boundaries stay visible.** Scheduler, Telegram history, audit history, source data, and inventory are visibly immutable where required.
7. **No invented precision.** Missing fields render as “Not recorded” or “Data unavailable,” never zero unless zero is the recorded value.

## 2. Foundations

### 2.1 Color tokens

| Token | Hex | Use |
|---|---:|---|
| `bg.canvas` | `#0B1220` | App background |
| `bg.sidebar` | `#0E1728` | Navigation background |
| `bg.surface` | `#111A2B` | Cards, filters, tables |
| `bg.surface.raised` | `#17243A` | Selected/raised panels |
| `bg.surface.hover` | `#1C2B43` | Hover/selected row support |
| `border.subtle` | `#26364D` | Default card/table boundaries |
| `border.strong` | `#3A4C66` | Focused/selected boundaries |
| `text.primary` | `#F1F5F9` | Main text |
| `text.secondary` | `#CBD5E1` | Supporting text |
| `text.muted` | `#94A3B8` | Metadata; never essential-only text |
| `text.disabled` | `#64748B` | Disabled/historical support only |
| `state.teal` | `#2DD4BF` | Confirmed, healthy, exact, delivered |
| `state.amber` | `#FBBF24` | Review required, tentative, nearby |
| `state.red` | `#F87171` | Error, unresolved interruption, invalid data |
| `state.blue` | `#93C5FD` | Neutral informational/accent state |

Measured contrast against `bg.canvas` / `bg.surface`:

- Primary text: 17.09:1 / 15.89:1
- Secondary text: 12.61:1 / 11.72:1
- Muted text: 7.30:1 / 6.79:1
- Teal: 10.06:1 / 9.35:1
- Amber: 11.22:1 / 10.43:1
- Red: 6.77:1 / 6.29:1

`text.disabled` is not approved for normal body copy because it measures below 4.5:1 on the dark surfaces. It may be used for nonessential decorative/historical metadata at 14 px or larger, paired with an explicit label.

### 2.2 Semantic color rules

| Meaning | Color | Examples |
|---|---|---|
| Confirmed / healthy | Teal | Exact match, validated inventory, completed run, delivered record |
| Review required | Amber | Nearby, tentative, unknown confidence, pending listing, disabled scheduler when expected |
| Critical / broken | Red | Unresolved interrupted run, failed validation, held stale lock, threshold exceeded |
| Informational | Blue | New record, neutral source metadata, active selection |
| Historical / inactive | Muted gray | Legacy match, immutable old audit row, unavailable/disabled data |

**Prohibited semantic uses**

- Do not use red for “Hot lead”; business priority is not an error.
- Do not use green/teal for a normal container border everywhere.
- Do not use color alone. Every state requires a text label; critical states also require an icon.

### 2.3 Typography

Use the Streamlit/system sans stack to avoid external font loading:

```css
font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
             "Segoe UI", sans-serif;
```

| Role | Size / line height | Weight | Usage |
|---|---|---:|---|
| Display | 36 / 44 px | 700 | Overview brand/title at wide desktop only |
| Page title | 28 / 36 px | 700 | Page identity |
| Section title | 20 / 28 px | 650 | Major modules |
| Card title | 16 / 24 px | 650 | Property, lead, match cards |
| Body | 14 / 22 px | 400 | Default content |
| Body strong | 14 / 22 px | 600 | Key inline facts |
| Label | 13 / 18 px | 600 | KPI/table/form labels |
| Metadata | 12 / 18 px | 400–500 | Timestamps, source IDs, helper text |
| KPI value | 28 / 34 px | 700 | Primary counts and money |
| Compact KPI | 22 / 28 px | 700 | Secondary metrics |

Rules:

- Sentence case everywhere; avoid all caps except short external acronyms.
- Use tabular numerals for scores, costs, counts, budgets, and run numbers.
- Keep body lines to approximately 70–90 characters in long-form panels.
- Never render raw JSON as the primary reading format.

### 2.4 Page widths and layout grid

| View | Sidebar | Main content behavior |
|---|---:|---|
| Compact desktop (1180–1439 px) | 216–224 px | Fluid, 24 px outer gutters, max content 1120 px |
| Standard desktop (1440–1919 px) | 232 px | Fluid, 32 px outer gutters, max content 1440 px |
| Wide desktop (1920 px+) | 240 px | Centered, 32 px gutters, max content 1600 px |

Grid rules:

- 12-column conceptual grid.
- Main module gap: 16 px compact, 20 px wide.
- Avoid more than four KPI cards in one row.
- Use 7/5 or 8/4 master-detail splits at wide desktop.
- At compact desktop, comparisons become 6/6 or stack if either panel would fall below 420 px.
- Dashboard is desktop-first; mobile is not a release acceptance target.

### 2.5 Spacing scale

| Token | Value | Use |
|---|---:|---|
| `space.1` | 4 px | Tight icon/text separation |
| `space.2` | 8 px | Related inline items |
| `space.3` | 12 px | Compact form/fact spacing |
| `space.4` | 16 px | Card padding and module gaps |
| `space.6` | 24 px | Section separation |
| `space.8` | 32 px | Page-level separation |
| `space.12` | 48 px | Rare major break only |

### 2.6 Radius, borders, and elevation

| Token | Value | Use |
|---|---:|---|
| `radius.sm` | 6 px | Badges, inputs, compact controls |
| `radius.md` | 8 px | Cards, table shells, callouts |
| `radius.lg` | 12 px | Selected preview or large summary panel only |
| Default border | 1 px `border.subtle` | Every card/table boundary |
| Selected border | 1 px `state.blue` | Current row/panel |
| Critical border | 1 px `state.red` | Critical callout only |
| Shadow | `0 6px 18px rgba(0,0,0,.14)` | Raised preview/overlay only |

Most cards have **no shadow**. Use surface contrast plus a subtle border. Never use gradients, glow, glassmorphism, or large drop shadows.

## 3. Shared shell

### 3.1 Branded header

An 56–64 px compact header contains:

- Product mark: simple 24 px signal/radar glyph or monogram.
- Product name: “Rental Demand Signal”.
- Page title as the dominant text inside the main content, not duplicated in the header.
- Right side: “Read-only intelligence,” last refresh, and compact database state.

No provider tokens, private chat IDs, Windows usernames, or full local paths.

### 3.2 Sidebar

- Brand block at top.
- Grouped navigation with icon, label, active indicator, and no duplicate `app` entry.
- Page filters do not live permanently in the global sidebar.
- Footer status stack:
  - Data source state
  - Scheduler state
  - Apify state
  - Telegram state
- Footer states are concise and link visually—not functionally—to Scheduler. No enable/send controls.

### 3.3 System status strip

A 36–44 px strip under the page header shows no more than four items:

1. Database: Connected / Unavailable
2. Inventory: N active / Pending / Invalid
3. Scheduler: Disabled / Ready / Attention required
4. Cost: current month vs threshold

Normal states use neutral text with a teal dot. Review states use amber. Only broken/critical states use red. Values must come from a read-only presentation contract; hardcoded counts/status are prohibited.

## 4. Components

### 4.1 Card anatomy

```text
┌──────────────────────────────────────────────┐
│ eyebrow / state badge             metadata  │
│ Card title                                  │
│ Primary value or 1–2 line summary           │
│ Supporting facts / visualization            │
│ divider (optional)                          │
│ safe action or disclosure (optional)        │
└──────────────────────────────────────────────┘
```

Rules:

- One dominant idea per card.
- 16 px padding compact; 20 px wide.
- Titles wrap to two lines maximum.
- Card actions are native buttons/links, not clickable custom HTML.

### 4.2 KPI cards

**Primary KPI**

- 112–128 px high.
- Label, value, short context, optional state dot.
- One primary and up to three secondary KPIs per row.

**Compact KPI**

- 84–96 px high.
- Label and value; optional one-line denominator.

Do not use decorative trend arrows unless the comparison period is explicit and available.

### 4.3 Status badges

| Style | Anatomy | Example |
|---|---|---|
| Solid critical | icon + label, dark red fill | `! Attention required` |
| Tinted semantic | dot + label, tinted fill/border | `● Exact match` |
| Neutral outline | label, subtle border | `Historical` |
| Count badge | label + count | `Nearby 12` |

- Height: 24–28 px.
- Horizontal padding: 8–10 px.
- Text: 12–13 px, 600 weight.
- Avoid pills for long phrases; use callouts instead.

### 4.4 Score indicator

Use score as a compact number plus bounded bar or ring:

```text
92 / 100  █████████░
High signal · 4 contributing rules
```

- Neutral/blue for score magnitude.
- Classification badge beside it supplies meaning.
- Never map score to red solely because it is high.
- Include a text label and rule count for accessibility.

### 4.5 Buttons

| Level | Style | Use |
|---|---|---|
| Primary | Teal fill, dark text | One safe page-level action, e.g. Save review |
| Secondary | Surface-raised, strong border | Open detail, apply filters |
| Tertiary | Text/ghost | Reset, close, show more |
| Destructive | Red outline/fill | Not expected in v0.8 dashboard scope |
| Disabled | Muted surface/text | Unavailable affordance; explain why |

Rules:

- One primary action per visible task region.
- Minimum 40 px height and visible focus ring.
- Confirmation text must name the exact write.
- Scheduler has no action buttons.

### 4.6 Tables

Table shell:

- Surface background, 1 px border, 8 px radius.
- 40–44 px header and 44–52 px row height.
- Sticky header where Streamlit supports it.
- Selected row uses raised surface plus blue left indicator.
- No zebra striping unless row separation is otherwise insufficient.

Lead Inbox default columns:

1. Lead / age
2. Score
3. Classification
4. Need (area + type)
5. Budget / confidence
6. Match
7. Review state

Secondary/hidden columns: period, Telegram state, exact IDs, historical metadata.

Formatting:

- Right-align money and numeric counts.
- Use concise text state plus icon; do not depend on HTML badges inside unsupported dataframe cells.
- Truncate long values with accessible tooltip/full preview.
- Define widths through `st.column_config`.
- One sanitized export action only.

### 4.7 Charts

Visual specification:

- Altair through Streamlit; no new chart dependency required.
- Transparent chart background within a surface card.
- Height: 220–280 px compact; 280–340 px wide for trends.
- Subtle grid `#26364D` at low opacity.
- Axis/legend text uses `text.muted`; titles use `text.secondary`.
- Direct labels where possible; legends at top only when needed.
- Teal = confirmed/eligible/delivered; amber = review/nearby/tentative/cost; blue = neutral/new; gray = historical; red = failure only.
- Hover tooltips show label, value, denominator/run, and data quality.
- Disable zoom/pan on categorical mini-charts.
- Adjacent 1–2 sentence textual summary is required for accessibility and fast scanning.
- Count-like series accept non-negative integers only. Fractional, malformed, or ambiguous manual-log values render as a data-quality state and are not plotted.
- Empty/missing series use an explicit empty-state component instead of a chart with infinite or undefined domains.

Do not display:

- A false-positive rate without a sufficient manual-review denominator.
- A funnel whose stages are not a defensible cohort sequence.
- “Classification by run” or “match tiers by run” unless those fields are actually recorded per run.

### 4.8 Filter bar

Persistent Lead Inbox filter bar:

```text
[Search……………………] [Queue ▾] [Class ▾] [Match ▾] [Area ▾] [More filters] [Reset]
```

- One row at wide desktop; up to two rows at compact desktop.
- Selected filter chips appear below only when active.
- “More filters” contains property type, budget confidence, Telegram state, and date range.
- Result count and sort sit on the same baseline as table title.
- Preserve filter and selected-lead state during page navigation.

### 4.9 Fact rows and comparison panels

Replace dictionary output with aligned facts:

```text
Area              Gading Serpong       ✓ aligned
Property type     Apartment            ✓ aligned
Bedrooms          1                     ✓ aligned
Budget / rent     Not stated            Review
Availability      —                     Not recorded
```

In Matching Review, the comparison uses one shared row label with Lead and Inventory columns so differences align horizontally.

## 5. State patterns

### 5.1 Empty state

An empty state contains:

- Simple neutral icon.
- Specific title: “No leads need review.”
- One-sentence explanation tied to current filters/data.
- Optional safe action: “Reset filters.”
- No celebratory illustration or animation.

Examples:

- No matches: “No active real inventory match. This lead remains in review.”
- No inventory: “No validated active inventory is available. Matching recommendations are withheld.”
- No runs: “No pilot run metrics are recorded.”

### 5.2 Loading state

Streamlit reruns make full skeleton control limited. Use:

- `st.status`/spinner with task-specific copy for long read-only loads.
- Stable container heights where practical to reduce page jump.
- “Refreshing dashboard data…” rather than generic “Running.”
- No infinite animation beyond Streamlit’s standard progress treatment.

### 5.3 Error state

Error callout anatomy:

```text
[!] Inventory validation failed
    Invalid rows are withheld. No fallback inventory was loaded.
    Technical detail ▸
```

- State the impact first.
- Keep sanitized technical detail in a collapsed expander.
- Never expose secrets, private IDs, or full host paths.
- Do not offer unsafe retry/run/enable controls.

### 5.4 Warning/review state

Amber callouts explain what confirmation is required and why:

- “Nearby area — confirm suitability before use.”
- “Budget confidence low — verify against source text.”
- “Listing pending — exclude from active recommendations.”

### 5.5 Confirmation patterns

Lead review is the only current dashboard write flow in scope.

- Show an explicit summary of changed fields before save.
- Confirmation copy: “Save status, note, and review timestamp for lead {safe ID}.”
- Do not imply Telegram send, author contact, rematching, or inventory mutation.
- Success: concise inline confirmation with audit timestamp.
- Failure: preserve entered values and show a sanitized error.
- Audit and Telegram records are immutable; no edit/delete controls.

Scheduler confirmation pattern: **none**. Scheduler remains strictly read-only.

## 6. Accessibility requirements

1. WCAG 2.1 AA target for desktop.
2. Normal text contrast ≥ 4.5:1; large text and non-text UI boundaries ≥ 3:1.
3. State is never conveyed by color alone.
4. Keyboard navigation follows visual order; focus ring is at least 2 px and clearly contrasting.
5. Interactive targets are at least 40×40 px where practical.
6. Headings follow a logical H1 → H2 → H3 sequence; avoid heading anchors becoming visual noise.
7. Every form input has a visible label or equivalent accessible label.
8. Charts have descriptive titles, accessible tooltips, and adjacent summaries.
9. Tables use human-readable headers and do not place critical information only off-screen.
10. Respect `prefers-reduced-motion`; no custom animation is required.
11. Avoid emoji-only status. Material icons must be paired with text.
12. Sanitized source excerpts retain readable line breaks and are selectable but read-only.

## 7. Streamlit implementation constraints

- CSS selectors based on `data-testid` are not a stable public API and should be minimized, isolated, and regression-tested.
- Native dataframe cells have limited support for custom HTML badges; use `st.column_config`, concise text, and selection state instead.
- Precise sticky master-detail panels and viewport-height layouts are constrained by Streamlit’s rerun model.
- Breakpoints are limited; design must remain usable when columns wrap rather than relying on exact CSS media behavior.
- `st.tabs` computes/renders all tab content in many versions; avoid expensive queries per tab and reuse cached read-only data.
- Deep-link page loads must continue working without `PYTHONPATH` configuration.
- The default Deploy/menu chrome may vary by runtime/config; hide only what can be safely hidden without harming accessibility.
- Streamlit reruns can reset widget state unless keys/session state are designed deliberately.
- Altair/Vega can emit browser-console scale and infinite-domain warnings even when Streamlit shows no Python error; browser acceptance includes console inspection and treats repeated domain warnings as defects.

## 8. Design acceptance checklist

- [ ] No gradients, glow, or consumer-style animation.
- [ ] Red appears only for actual error/critical conditions.
- [ ] All active inventory identifiers are validated real IDs.
- [ ] Legacy/historical records are muted and excluded from active recommendations/totals.
- [ ] Six to eight Overview KPIs maximum.
- [ ] No raw dictionary/JSON presentation in primary views.
- [ ] One sanitized export affordance.
- [ ] Scheduler has no run/enable/send/unlock/reconcile/install controls.
- [ ] Audit and Telegram history are visibly immutable.
- [ ] Analytics labels match recorded data; missing data is disclosed.
- [ ] 1366×768 and 1920×1080 desktop layouts pass browser acceptance.
- [ ] Keyboard, focus, contrast, empty, loading, and error states are verified.