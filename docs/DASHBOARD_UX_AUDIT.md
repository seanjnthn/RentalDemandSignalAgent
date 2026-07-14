# Dashboard UX audit

The v0.6.1 dashboard exposed the right read-only repository data, but its six views
felt like debug screens: the page title, filters, KPIs, and tables had no hierarchy;
the overview left large unused areas; and table columns used raw field names that
made score, status, budget period, and match tiers hard to scan. Classification and
match values were unstyled strings, so “nearby”, “tentative”, and historical data
looked equivalent. Empty inventory and no-match states were easy to miss.

Reviewers had to move between pages, expand raw JSON, and infer which controls were
safe. The inbox had no search, quick filters, bounded results, preview, or export;
detail mixed source text, scoring, delivery metadata, and workflow in one stream.
Inventory did not distinguish the three active records from legacy matches. Matching
review did not provide a side-by-side comparison or a clear confirmation warning.

Typography and spacing were browser defaults, cards were absent, and the dense KPI
grid did not establish an operational “what needs attention” path. The refresh keeps
the repository contract but introduces a restrained dark intelligence-workspace
system, reusable badges/cards, readable currency and age labels, and charted trends.
