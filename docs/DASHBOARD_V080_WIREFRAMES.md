# Dashboard v0.8.0 Low-Fidelity Wireframes

These wireframes define hierarchy and responsive desktop behavior, not pixel-perfect implementation. All controls are presentation/read-only unless the Lead Detail review form explicitly identifies its allowlisted local write.

Numbers and timestamps shown below are low-fidelity examples based on the inspected local snapshot where useful; they are not hardcoded product requirements. Production values must come from sanitized read-only presentation contracts, and unavailable values remain unavailable.

## 1. Layout assumptions

### 1366×768 — compact desktop

- Sidebar: approximately 216–224 px.
- Main content: fluid with 24 px gutters.
- Two KPI cards per row when labels need room; four compact cards may fit only for very short states.
- Analysis modules use two columns, then stack.
- Tables prioritize seven core columns and may hide secondary columns.
- Target first viewport content height is approximately 620–660 px after browser/application chrome.

### 1920×1080 — wide desktop

- Sidebar: approximately 240 px.
- Main content: centered, up to 1600 px, 32 px gutters.
- Four KPI cards per row.
- Master-detail layouts use a 7/5 or 8/4 split.
- Charts can use 280–340 px height.
- Target first viewport content height is approximately 900–960 px after browser/application chrome.

### Legend

```text
[Button]      interactive native control
{Badge}       status label
▾             expander/popover
●             state dot (always paired with text)
!             warning/critical state
→             navigation handoff
```

---

# 2. Shared shell

## 1366×768

```text
┌──────────────────────┬────────────────────────────────────────────────────────────────────────┐
│  ◉ RDSA              │ Rental Demand Signal                               Read-only · 06:42 UTC │
│  Signal Desk         ├────────────────────────────────────────────────────────────────────────┤
│                      │ PAGE TITLE                                      optional safe action     │
│ MONITOR              │ One-sentence page purpose                                              │
│  ▌ Overview          ├────────────────────────────────────────────────────────────────────────┤
│    Pilot Analytics   │ ● DB Connected  ● Inventory 3 active  ○ Scheduler disabled  Cost $1.20 │
│    Scheduler         ├────────────────────────────────────────────────────────────────────────┤
│                      │                                                                        │
│ REVIEW               │                          PAGE CONTENT                                  │
│    Lead Inbox        │                                                                        │
│    Lead Detail       │                                                                        │
│    Matching Review   │                                                                        │
│                      │                                                                        │
│ SUPPLY               │                                                                        │
│    Inventory         │                                                                        │
│                      │                                                                        │
│ ───────────────────  │                                                                        │
│ DB         Connected │                                                                        │
│ Scheduler   Disabled │                                                                        │
│ Delivery    Disabled │                                                                        │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

## 1920×1080

```text
┌────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│ ◉ RDSA Signal Desk     │ Rental Demand Signal                                              Read-only · 06:42 UTC │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│ MONITOR                │ PAGE TITLE                                                              optional action │
│ ▌ Overview             │ One concise sentence                                                                  │
│   Pilot Analytics      ├──────────────────────────────────────────────────────────────────────────────────────────┤
│   Scheduler            │ ● Database Connected   ● Inventory 3 active   ○ Scheduler Disabled   Cost $1.20 / $4.75 │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│ REVIEW                 │                                                                                          │
│   Lead Inbox           │                                     PAGE CONTENT                                         │
│   Lead Detail          │                                                                                          │
│   Matching Review      │                                                                                          │
│                        │                                                                                          │
│ SUPPLY                 │                                                                                          │
│   Inventory            │                                                                                          │
│                        │                                                                                          │
│ ─────────────────────  │                                                                                          │
│ ● Database Connected  │                                                                                          │
│ ○ Scheduler Disabled  │                                                                                          │
│ ○ Delivery Disabled   │                                                                                          │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 3. Overview

## 1366×768

```text
┌─ sidebar ─────────────┬────────────────────────────────────────────────────────────────────────┐
│                      │ Overview                                                Refreshed 06:42 │
│                      │ Demand, review priority, and operational health                          │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ ● DB Connected  ● 3 inventory  ○ Scheduler disabled  Cost 25% of stop   │
│                      ├───────────────────────────────────┬────────────────────────────────────┤
│                      │ NEEDS REVIEW                      │ HOT + QUALIFIED                    │
│                      │ 42                                │ 25                                 │
│                      │ New leads awaiting review         │ High-signal demand                 │
│                      ├───────────────────────────────────┼────────────────────────────────────┤
│                      │ ACTIVE REAL MATCHES               │ DELIVERED                          │
│                      │ 14                                │ 3                                  │
│                      │ 5 properties involved             │ Immutable delivery history        │
│                      ├───────────────────────────────────┴────────────────────────────────────┤
│                      │ LEAD VOLUME / FUNNEL*               MATCH QUALITY                        │
│                      │ All 127 ▬▬▬▬▬▬▬▬▬                 Exact 5     ▬▬▬                      │
│                      │ Qualified 25 ▬▬                   Nearby 6    ▬▬▬▬                     │
│                      │ Delivered 3  ▏                    Tentative 3 ▬▬                       │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ PRIORITY LEADS                                          [Open inbox →] │
│                      │ 4020 · 12m  Score 100  Hot      Tangerang Selatan   Review budget       │
│                      │ 4004 · 18m  Score 100  Hot      Tangerang Selatan   Low confidence      │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
*Use “funnel” only if the implemented stages form a defensible sequential cohort; otherwise retain the independent volume label and explicit denominators.
ABOVE FOLD ENDS: status, four primary KPIs, two core distributions, first priority rows.
Below fold: remaining 2–4 KPIs, classification distribution, latest run/cost detail, metric definitions.
```

## 1920×1080

```text
┌─ sidebar ───────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│                        │ Overview                                                                  Refreshed 06:42 │
│                        │ Review priority, demand quality, and operational health                                    │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ ● DB Connected  ● Inventory 3 active  ○ Scheduler disabled  Cost $1.20 / $4.75            │
│                        ├──────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┤
│                        │ NEEDS REVIEW         │ HOT + QUALIFIED      │ ACTIVE MATCHES       │ DELIVERED            │
│                        │ 42                   │ 25                   │ 14                   │ 3                    │
│                        │ 33% of all leads     │ High-signal demand   │ Real inventory only  │ Immutable history    │
│                        ├──────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│                        │ LOW/UNKNOWN CONF.    │ LATEST RUN           │ MONTHLY COST         │ ACTIVE INVENTORY     │
│                        │ 18                   │ Interrupted {History}│ $1.20 / $4.75       │ 3                    │
│                        ├─────────────────────────────────────────────┬─────────────────────────────────────────────┤
│                        │ LEAD VOLUME / FUNNEL*                       │ MATCH QUALITY                               │
│                        │ All 127 ▬▬▬▬▬▬▬▬▬▬▬                        │ Exact      5 ▬▬▬                           │
│                        │ Qualified 25 ▬▬                            │ Nearby     6 ▬▬▬▬                          │
│                        │ Delivered 3 ▏                              │ Tentative  3 ▬▬                            │
│                        │ Defined denominators                       │ No match 109 ▬▬▬▬▬▬▬▬▬                     │
│                        ├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│                        │ PRIORITY LEADS                              │ CLASSIFICATION                              │
│                        │ 4020  100 Hot  Area…  Review budget         │ Hot 6 / Qualified 19 / Watch…              │
│                        │ 4004  100 Hot  Area…  Low confidence        │ compact horizontal bars                     │
│                        │ 4003  100 Hot  Area…  Tentative match       │                                               │
│                        │ [Open full inbox →]                         │                                               │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
*Use “funnel” only with sequential cohort definitions; otherwise these are independent volume stages.
ABOVE FOLD ENDS: status, all KPIs, two primary analyses, priority queue and classification start.
Below fold: run/cost detail and optional distributions.
```

---

# 4. Lead Inbox

## 1366×768

```text
┌─ sidebar ─────────────┬────────────────────────────────────────────────────────────────────────┐
│                      │ Lead Inbox                                           127 results         │
│                      │ Triage sanitized lead records                                            │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ [Search……………………………] [Queue ▾] [Class ▾] [Match ▾]                    │
│                      │ [Area ▾] [More filters ▾] [Reset]   Active: Needs review ×                │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ REVIEW QUEUE                  Sort: Priority ▾   [Export sanitized]       │
│                      │ ┌──────┬─────┬──────────┬──────────────┬──────────┬──────────┬──────────┐ │
│                      │ │Lead  │Score│Class     │Need          │Budget    │Match     │Review    │ │
│                      │ ├──────┼─────┼──────────┼──────────────┼──────────┼──────────┼──────────┤ │
│                      │ │▌4020 │100  │Hot       │Tangsel House │7–9m ?    │No match  │New       │ │
│                      │ │ 4004 │100  │Hot       │Tangsel House │2k–90m !  │Tentative │New       │ │
│                      │ │ 4003 │100  │Hot       │GS Contract   │3k–4m !   │Nearby    │New       │ │
│                      │ │ 4001 │100  │Hot       │BSD Apt       │8m High   │Exact     │New       │ │
│                      │ │ 4002 │94   │Hot       │AS Apt        │6m High   │Nearby    │New       │ │
│                      │ │ …    │     │          │              │          │          │          │ │
│                      │ └──────┴─────┴──────────┴──────────────┴──────────┴──────────┴──────────┘ │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ SELECTED: 4020 · Hot · 100                [Open Lead Detail →]           │
│                      │ Tangerang Selatan · House · Budget confidence unknown · No active match  │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
ABOVE FOLD ENDS: filters, 6–8 rows, compact selected summary.
The full preview stacks below on compact desktop; it does not compete with table width.
```

## 1920×1080

```text
┌─ sidebar ───────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│                        │ Lead Inbox                                                         127 filtered results   │
│                        │ Triage sanitized lead records                                                               │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ [Search………………………………] [Queue ▾] [Class ▾] [Match ▾] [Area ▾] [More ▾] [Reset]          │
│                        │ Active: Needs review × · High priority ×                             [Export sanitized]   │
│                        ├────────────────────────────────────────────────────┬─────────────────────────────────────┤
│                        │ REVIEW QUEUE                         Sort: Priority │ SELECTED LEAD                       │
│                        │ ┌──────┬─────┬───────┬───────────┬────────┬───────┐│ {Hot}  Score 100       New · 12m   │
│                        │ │Lead  │Score│Class  │Need       │Budget  │Match  ││ 4020                                 │
│                        │ ├──────┼─────┼───────┼───────────┼────────┼───────┤│ Tangerang Selatan · House            │
│                        │ │▌4020 │100  │Hot    │Tangsel H. │7–9m ?  │None   ││ Budget IDR 7–9m · confidence unknown │
│                        │ │ 4004 │100  │Hot    │Tangsel H. │2k–90m! │Tent.  ││                                       │
│                        │ │ 4003 │100  │Hot    │GS Contract│3k–4m ! │Nearby ││ REVIEW REQUIRED                       │
│                        │ │ 4001 │100  │Hot    │BSD Apt    │8m High │Exact  ││ Budget range needs confirmation.      │
│                        │ │ 4002 │94   │Hot    │AS Apt     │6m High │Nearby ││ No active real inventory match.       │
│                        │ │ …    │     │       │           │        │       ││                                       │
│                        │ │      │     │       │           │        │       ││ Sanitized source excerpt…             │
│                        │ │      │     │       │           │        │       ││                                       │
│                        │ └──────┴─────┴───────┴───────────┴────────┴───────┘│ [Open Lead Detail →]                  │
│                        │ 1–50 of 127                                        │                                       │
│                        └────────────────────────────────────────────────────┴─────────────────────────────────────┘
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
ABOVE FOLD ENDS: complete master-detail triage workspace.
```

---

# 5. Lead Detail

## 1366×768

```text
┌─ sidebar ─────────────┬────────────────────────────────────────────────────────────────────────┐
│                      │ [← Inbox]  Lead 4020                           {Hot}  Score 100  {New}     │
│                      │ First seen 12m ago · Sanitized source available                           │
│                      ├──────────────────────────────────────────┬─────────────────────────────┤
│                      │ EXECUTIVE SUMMARY                        │ REVIEW DECISION             │
│                      │ Seeking a house in Tangerang Selatan.    │ Status [New ▾]              │
│                      │ Budget recorded as IDR 7–9m monthly,     │ Notes […………………]             │
│                      │ but confidence is unknown.               │ Reviewed at [auto/current]  │
│                      │                                          │                             │
│                      │ Area        Tangerang Selatan             │ Changes: status, note, time │
│                      │ Type        House                         │ [ ] Confirm exact local write│
│                      │ Budget      IDR 7–9m {Review}             │ [Save review]               │
│                      ├──────────────────────────────────────────┴─────────────────────────────┤
│                      │ ! REVIEW REQUIRED  Budget confidence unknown; confirm against source.  │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ BEST MATCH                                                             │
│                      │ No active real inventory match. This lead remains in review.            │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ [Evidence] [Audit history] [Telegram history]                            │
│                      │ Sanitized source excerpt…                                  Score rules ▾ │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
ABOVE FOLD ENDS: summary, warning, match state, decision workflow, history tabs.
```

## 1920×1080

```text
┌─ sidebar ───────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│                        │ [← Back to 127-lead queue]  Lead 4020          {Hot lead}  Score 100  {New}  12m ago      │
│                        ├──────────────────────────────────────────────────────────┬───────────────────────────────┤
│                        │ EXECUTIVE SUMMARY                                        │ REVIEW DECISION               │
│                        │ Seeking a house in Tangerang Selatan with a recorded      │ Current status  New           │
│                        │ monthly budget of IDR 7–9m. Budget confidence is unknown. │ New status [Reviewed ▾]       │
│                        │                                                          │ Notes […………………………………]      │
│                        │ Area      Tangerang Selatan   Type    House                │ Reviewed at [17 Jul 06:42 UTC]│
│                        │ Bedrooms Not recorded        Budget  IDR 7–9m monthly     │                               │
│                        │ Confidence {Review required} Source  Public URL available │ Will write: status/note/time  │
│                        │                                                          │ [ ] Confirm exact local write│
│                        │ ! Verify budget against source before using it.           │ [Save review]                 │
│                        ├──────────────────────────────────────────────────────────┴───────────────────────────────┤
│                        │ ACTIVE REAL MATCHES                                                                          │
│                        │ ┌──────────────────────────────────────────────────────────────────────────────────────┐ │
│                        │ │ No active real inventory match · Lead remains in review                            │ │
│                        │ └──────────────────────────────────────────────────────────────────────────────────────┘ │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ [Evidence] [Audit history] [Telegram history]                                           │
│                        │ Sanitized source excerpt             │ Extracted facts         │ Score explanation ▾         │
│                        │ “…”                                  │ Area / type / budget…   │ +25 explicit intent…       │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 6. Inventory

## 1366×768

```text
┌─ sidebar ─────────────┬────────────────────────────────────────────────────────────────────────┐
│                      │ Inventory                                      3 active · 0 pending      │
│                      │ Validated real properties only                                            │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ ● Inventory validated   Last checked 06:42 UTC   [Cards] [Table]          │
│                      ├───────────────────────────────────┬────────────────────────────────────┤
│                      │ SERPONG M-TOWN                    │ SUVARNA SUTERA FEDORA               │
│                      │ Apartment · Gading Serpong        │ House · Suvarna Sutera              │
│                      │ IDR 2.92m / month                 │ IDR 1.67m / month                  │
│                      │ 1 bed · Furnished                 │ 3 bed · Unfurnished                │
│                      │ Available 14 Jul                  │ Available 14 Jul                   │
│                      │ 6 active matches                  │ 5 active matches                   │
│                      │ ID APT-GS-… (metadata)            │ ID HSE-SS-… (metadata)             │
│                      ├───────────────────────────────────┼────────────────────────────────────┤
│                      │ PASAR MODERN INTERMODA            │ EMPTY / NEXT CARD                  │
│                      │ Kiosk · BSD                       │                                     │
│                      │ IDR 0.83m / month                 │                                     │
│                      │ Available 14 Jul · 3 matches      │                                     │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
ABOVE FOLD ENDS: status and all three active properties.
Below fold: compact sortable table and property details.
```

## 1920×1080

```text
┌─ sidebar ───────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│                        │ Inventory                                                     3 active · 0 pending         │
│                        │ Validated real properties, availability, and match activity                                  │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ ● Inventory validated  Last checked 06:42 UTC                                  [Cards|Table]│
│                        ├──────────────────────────────┬──────────────────────────────┬──────────────────────────────┤
│                        │ SERPONG M-TOWN               │ SUVARNA SUTERA FEDORA        │ PASAR MODERN INTERMODA       │
│                        │ Apartment · Gading Serpong   │ House · Suvarna Sutera       │ Kiosk · BSD                  │
│                        │ IDR 2.92m / month            │ IDR 1.67m / month           │ IDR 0.83m / month           │
│                        │ 1 bed · Furnished            │ 3 bed · Unfurnished          │ Commercial · Unfurnished    │
│                        │ {Available} 14 Jul           │ {Available} 14 Jul          │ {Available} 14 Jul          │
│                        │ 6 active matches             │ 5 active matches             │ 3 active matches             │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ INVENTORY TABLE                                                                            │
│                        │ Property        Area / type       Price       Availability      Match activity   Listing │
│                        │ M-Town          GS · Apartment    2.92m       Available 14 Jul   6                Active  │
│                        │ Fedora          SS · House        1.67m       Available 14 Jul   5                Active  │
│                        │ Intermoda       BSD · Kiosk       0.83m       Available 14 Jul   3                Active  │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 7. Matching Review

## 1366×768

```text
┌─ sidebar ─────────────┬────────────────────────────────────────────────────────────────────────┐
│                      │ Matching Review                                      15 active reviews  │
│                      │ Compare demand with validated real inventory                             │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ [Exact 1] [Nearby 8] [Tentative 5] [No match 109] [Legacy 2]             │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ {Exact match}  Lead 394159… → M-Town Apartment       Score 100            │
│                      │ No confirmation warning                                                  │
│                      ├───────────────┬────────────────────────┬────────────────────────┬────────┤
│                      │ Criterion     │ Lead                   │ Inventory              │ Result │
│                      ├───────────────┼────────────────────────┼────────────────────────┼────────┤
│                      │ Area          │ Gading Serpong         │ Gading Serpong         │ Align  │
│                      │ Type          │ Apartment              │ Apartment              │ Align  │
│                      │ Bedrooms      │ 1                      │ 1                      │ Align  │
│                      │ Budget / rent │ Not stated             │ IDR 2.92m monthly      │ Review │
│                      │ Availability  │ Needed / not recorded  │ Available 14 Jul       │ Review │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ EVIDENCE  ✓ area aligned  ✓ type aligned  ✓ bedrooms aligned            │
│                      │ [Open Lead Detail]                                      [Open Inventory] │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

## 1920×1080

```text
┌─ sidebar ───────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│                        │ Matching Review                                                    15 active comparisons   │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ [Exact 1]  [Nearby 8]  [Tentative 5]  [No match 109]  [Legacy 2]                         │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ {Exact match}  Lead 394159… → Serpong M-Town Residence      Score 100  No warning         │
│                        ├──────────────────┬────────────────────────────────┬────────────────────────────────┬──────┤
│                        │ Criterion        │ Lead                           │ Inventory                      │Result│
│                        ├──────────────────┼────────────────────────────────┼────────────────────────────────┼──────┤
│                        │ Area             │ Gading Serpong                 │ Gading Serpong                 │Align │
│                        │ Property type    │ Apartment                      │ Apartment                      │Align │
│                        │ Bedrooms         │ 1                              │ 1                              │Align │
│                        │ Budget / rent    │ Not stated                     │ IDR 2.92m monthly              │Review│
│                        │ Availability     │ Needed date not recorded       │ Available 14 Jul               │Review│
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ EVIDENCE                                   │ WARNINGS                                           │
│                        │ ✓ Area aligned                             │ None                                               │
│                        │ ✓ Property type aligned                    │ Confirmation required: No                         │
│                        │ ✓ Bedrooms aligned                         │                                                    │
│                        │ [Open Lead Detail]                         │ [Open Inventory record]                            │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
Nearby/Tentative replace the neutral warning area with an amber confirmation callout.
No match has no inventory column content and never invents an alternative.
Legacy is muted and excluded from active totals/recommendations.
```

---

# 8. Pilot Analytics

## 1366×768

```text
┌─ sidebar ─────────────┬────────────────────────────────────────────────────────────────────────┐
│                      │ Pilot Analytics                                    Latest recorded run 10│
│                      │ Yield, cost, and quality-review coverage                                │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ ! Some run fields are not recorded; gaps are not treated as zero.       │
│                      ├───────────────────────────────────┬────────────────────────────────────┤
│                      │ NEW / ELIGIBLE / DELIVERED        │ LATEST RUN COST                    │
│                      │  — / Not recorded / Not recorded  │ $0.70 · manual record             │
│                      ├───────────────────────────────────┼────────────────────────────────────┤
│                      │ CUMULATIVE COST                   │ QUALITY REVIEW                     │
│                      │ $1.20 / $4.75 stop               │ Insufficient reviewed denominator │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ [Yield] [Cost] [Quality] [Run ledger]                                    │
│                      │ NEW vs ELIGIBLE vs DELIVERED BY RUN                                     │
│                      │ 20 ┤                 ●                                                   │
│                      │ 10 ┤ ●       ●                                                           │
│                      │  0 ┼──●──●──●────●──●──●──●                                             │
│                      │     1  2  3  4    7  8  9 10      Gaps shown where data unavailable      │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
ABOVE FOLD ENDS: data quality, key KPIs, primary trend.
Below fold: cost threshold chart, quality distributions, run ledger and definitions.
```

## 1920×1080

```text
┌─ sidebar ───────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│                        │ Pilot Analytics                                                  Latest recorded run 10   │
│                        │ Run yield, cost, and manual quality-review coverage                                      │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ ! Some manually logged fields are unavailable; missing values remain gaps.              │
│                        ├──────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┤
│                        │ NEW LEADS           │ ELIGIBLE             │ DELIVERED            │ LATEST RUN COST      │
│                        │ Not recorded        │ Not recorded         │ Not recorded         │ $0.70                │
│                        ├──────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│                        │ CUMULATIVE COST     │ COST / ELIGIBLE      │ REVIEWED SAMPLE      │ QUALITY STATE        │
│                        │ $1.20 / $4.75      │ Not available        │ Not recorded         │ Insufficient data    │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ [Yield] [Cost] [Quality] [Run ledger]                                                       │
│                        ├─────────────────────────────────────────────┬─────────────────────────────────────────────┤
│                        │ NEW / ELIGIBLE / DELIVERED BY RUN           │ COST BY RUN + THRESHOLDS                    │
│                        │ 20 ┤             ●                          │ $1 ┤ ●                                      │
│                        │ 10 ┤ ●  ●                                   │    ┤   ● ● …                                  │
│                        │  0 ┼──●──●──●──●──●──●                     │ $0 ┼────────────────                        │
│                        │ Missing series render as gaps               │ Warn $4 / Stop $4.75 context               │
│                        ├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│                        │ CLASSIFICATION (cumulative)                 │ MATCH QUALITY / BUDGET CONFIDENCE          │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 9. Scheduler

## 1366×768

```text
┌─ sidebar ─────────────┬────────────────────────────────────────────────────────────────────────┐
│                      │ Scheduler                                              {Read-only}       │
│                      │ Readiness, latest run, lock, ledger, cost, and failures                  │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ READY BUT DISABLED                                                     │
│                      │ Code ready · Scheduler off · Scheduled send off · Lock free              │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ ! HISTORICAL INTERRUPTION RECONCILED                                    │
│                      │ Latest run interrupted; reconciliation completed. No current action.     │
│                      ├───────────────────────────────────┬────────────────────────────────────┤
│                      │ LATEST RUN                        │ COST POSTURE                       │
│                      │ Interrupted · Historical          │ $1.201 / $4.750 stop             │
│                      │ Started 04:23 · Finished 06:20    │ 25% used                           │
│                      │ Raw/New: Not recorded             │ Warn at $4.000                    │
│                      ├───────────────────────────────────┼────────────────────────────────────┤
│                      │ CURRENT FLAGS                     │ PROCESS LOCK                       │
│                      │ Apify off · Telegram off          │ ● Free                             │
│                      │ Scheduler off · Send off          │                                    │
│                      ├────────────────────────────────────────────────────────────────────────┤
│                      │ [Overview] [Run ledger] [Failures & interruptions]                       │
└──────────────────────┴────────────────────────────────────────────────────────────────────────┘
ABOVE FOLD ENDS: verdict, highest-severity state, latest run, cost, flags, lock.
No action buttons are present.
```

## 1920×1080

```text
┌─ sidebar ───────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│                        │ Scheduler                                                                  {Read-only}    │
│                        │ Readiness, run ledger, lock, cost, failures, and interruptions                             │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ READY BUT DISABLED                                                                        │
│                        │ Code ready · Scheduler off · Scheduled send off · Apify off · Telegram off · Lock free    │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ ! Historical interruption reconciled · Latest run is not an unresolved incident           │
│                        ├─────────────────────────────────────────────┬─────────────────────────────────────────────┤
│                        │ LATEST RUN                                  │ COST POSTURE                                │
│                        │ {Interrupted · reconciled}                  │ Monthly usage        $1.201                │
│                        │ 17 Jul 04:23 → 06:20 UTC                    │ Warning threshold    $4.000                │
│                        │ Trigger: scheduled canary                   │ Stop threshold       $4.750                │
│                        │ Raw/New/Eligible/Sent: Not recorded         │ █████░░░░░░░░░░ 25% used                   │
│                        ├────────────────────────────┬────────────────┼─────────────────────────────────────────────┤
│                        │ FLAGS                      │ LOCK           │ LAST SUCCESSFUL RUN                         │
│                        │ Scheduler off              │ ● Free         │ Completed · 4 new · 0 sent                 │
│                        │ Scheduled send off         │                │ Finished 17 Jul 02:03 UTC                  │
│                        │ Apify off · Telegram off   │                │                                             │
│                        ├──────────────────────────────────────────────────────────────────────────────────────────┤
│                        │ [Overview] [Run ledger] [Failures & interruptions]                                        │
│                        │ RUN LEDGER                                                                               │
│                        │ Run / date        Status           Phase       New   Eligible   Sent   Cost   Failure     │
│                        │ 17 Jul 04:23      Interrupted      Starting    —     —          —      —      Reconciled  │
│                        │ 17 Jul 01:55      Completed        Finished    4     —          0      …      —           │
└────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
No run, enable, send, unlock, reconcile, or install controls appear at any width.
```

---

# 10. Responsive behavior summary

| Pattern | 1366×768 | 1920×1080 |
|---|---|---|
| KPI grid | 2×N primary cards | 4×2 compact grid |
| Overview charts | 2 columns | 2 large columns |
| Inbox | Table + compact selected summary; preview below | Persistent 7/5 master-detail |
| Lead Detail | Summary/review 60/40; match below | Summary/review + evidence in one viewport |
| Inventory cards | 2 columns | 3 columns |
| Match comparison | Shared 4-column fact table | Wider aligned comparison + evidence split |
| Analytics | One primary chart above fold | Two primary charts side by side |
| Scheduler | Verdict + 2-column operational cards | Verdict + latest/cost + flags/lock/success + ledger |
| Secondary fields | Hidden/expanders | Visible where space permits |

## 11. Fold and disclosure rules

- Critical alert and next safe action never start below the fold.
- Audit, Telegram history, legacy data, metric definitions, and technical detail may be below the fold or collapsed.
- Filters may use two compact rows at 1366; they must not occupy more than approximately one quarter of the usable first viewport.
- At 1920, the Lead Inbox preview remains visible while scanning the queue.
- If Streamlit cannot guarantee sticky positioning, preserve hierarchy and accept normal page scroll rather than introducing brittle custom JavaScript.