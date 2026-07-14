# Dashboard design system

Rental Demand Signal uses a dark navy/charcoal foundation (`#0b1220`, `#111a2b`)
with high-contrast text (`#e7eef7`) and a subdued border (`#26364d`). Teal
(`.teal`, `#35c6b0`) means confirmed/healthy; amber (`#f2b84b`) means tentative or
confirmation required; red (`#ef6b73`) means serious warning/error; muted gray
(` #7d8da3`) marks legacy/historical information. Cards use 0.5rem radii, 1px
borders, and a small shadow; spacing follows 4/8/12/16/24/32px.

Inter/system sans is used for labels, with compact numeric KPIs and sentence-case
headings. Badges are pill-shaped, score bars are teal-to-amber, and area chips are
quiet blue-gray. Plotly charts use the same dark plot background, restrained grid,
and semantic series colors. Tables use short human labels, pinned lead identity
where useful, bounded height, sorting, and sanitized display text.

Every view has explicit loading, empty, invalid-data, and error states. Responsive
layouts prefer Streamlit containers and four-column maximum grids; comparisons stack
on narrow screens. The system has no live-scan, live-send, credential, or synthetic
inventory affordance.
