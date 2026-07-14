# DASHBOARD_DATA_MAP.md — v0.6 data sources & field mapping

## SQLite (read) — table `leads` (key columns)
| Dashboard field | SQLite column | Notes |
|---|---|---|
| Score | `lead_score` | int |
| Classification | `lead_class` | hot_lead/qualified_lead/watch/agent_broker/irrelevant/spam |
| First seen | `first_seen` | ISO; used for age + date filter |
| Last seen | `last_seen` | ISO |
| Post age | `post_timestamp` | public post time; age = now - post_timestamp |
| Canonical area | `desired_location` | canonical area or None/unknown |
| Property type | `property_type` | |
| Bedrooms | `bedrooms` | int or None |
| Budget min/max | `budget_min`/`budget_max` | int IDR or None |
| Budget period | `budget_period` | month/year/unknown |
| Budget confidence | `budget_confidence` | high/medium/low |
| Match type | derived from `matched_inventory` | see below |
| Matched property IDs | derived from `matched_inventory` | |
| Status | `status` | new/reviewed/contacted/responded/viewing_scheduled/converted/negotiating/rejected/duplicate/irrelevant |
| Telegram sent | `alerts` table join on `post_id` | exists => sent; `message_id` available |
| Reviewed at | `reviewed_at` (add if missing) | |
| Notes | `notes` | |
| Sanitized text | `raw_text` | sanitize phone/email on display |
| Source URL | `source_url` | public Threads URL |

## `matched_inventory` format (two shapes — normalize both)
Legacy (v0.5 pilot): `[{"inventory_id":..., "match_reasons":[...], "title":..., "location":..., "property_type":..., "bedrooms":..., "price":...}]`
v0.5.1+ (hardening): `[{"property_id":..., "match_type": exact_match|nearby_alternative|tentative_match|no_match, "score":int, "reasons":[...], "warnings":[...]}]`

**Normalization rule:** map `inventory_id`→`property_id`; `match_reasons`→`reasons`; default `match_type = "nearby_alternative"` when legacy + areas differ, else infer. Treat `[null]`/`[None]`/empty as `[]` (no match). Never synthesize IDs.

## `alerts` (read)
`post_id, sent_at, channel, message_id` — drives "Telegram sent" + delivery metadata.
Never written by dashboard.

## `status_history` (write — audit)
`post_id, old_status, new_status, changed_at, note`. Add `source='dashboard'` column if absent (safe ALTER).

## Inventory (read) — `data/inventory_real.csv`
Columns: `property_id, area, building, property_type, bedrooms, monthly_price, furnished, available_from, features, status, listing_url`
- Monthly equivalent = `monthly_price`.
- Annual asking = parse from `features` text when present (e.g. "35 juta/tahun"); else None.
- `furnished` 1/0; `status` must be available to count.
- Validation: reuse `rdsa.inventory.validate_real_inventory_for_scan`. Missing/invalid => warning state, NO synthetic fallback.

## Pilot Analytics — `docs/PILOT_LOG.md`
Parse the `## Run #N` sections for per-run: raw/normalized/dup/new/classifications/
target-area/unknown-loc/budget-confidence/match-tier counts/cards sent/cost. Distinguish
current-run vs cumulative vs manually-reviewed. Do NOT assert false-positive rate without review.
