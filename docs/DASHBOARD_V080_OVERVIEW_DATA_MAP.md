# Dashboard v0.8 Signal Desk Overview data map

**Phase:** 2B — professional Overview redesign

**Boundary:** This page consumes existing sanitized, read-only repository contracts. It does not add SQL, schema, scoring, classification, extraction, matching, scheduler, delivery, Apify, or Telegram behavior.

## Repository contracts

| Display | Existing repository method | Stored/read field | Presentation rule |
|---|---|---|---|
| Last refreshed | Runtime UTC clock | Not persisted | Human-readable UTC render time; not presented as a source-event timestamp. |
| Database status | `get_overview({})` / `get_leads({})` read outcome | Existing local database | Connected only after a successful repository read; otherwise unavailable. |
| Real inventory status | `get_inventory()` | Validated `rows` and validation `report.ok` | Count only validated real inventory rows. Invalid or unavailable inventory is withheld; no fallback IDs. |
| Scheduler status | `get_scheduler_status()` | `code_readiness`, `scheduler_enabled`, `latest_run`, `lock`, `interrupted_runs` | Disabled is muted, not critical. Required reconciliation, blocked/failed latest run, or a lock whose process is not alive is blocking. A live lock is running; completed reconciliation is historical. |
| Telegram delivery status | `get_scheduler_status()` | `telegram_send_enabled` | Disabled is an expected muted state; enabled is confirmed. No send action is exposed. |
| Review backlog | `get_overview({})` | Aggregated `leads.status == "new"` as `new` | Non-negative integer only; missing/malformed is “Not recorded.” |
| High-signal leads | `get_overview({})` | Aggregated `leads.lead_class == "hot_lead"` as `hot` | Informational blue, never error red. |
| Qualified leads | `get_overview({})` | Aggregated `leads.lead_class == "qualified_lead"` as `qualified` | Non-negative integer only. |
| Target-area leads | `get_overview({})` | `total` and `unknown_location` | Reuses the accepted Phase 2A presentation definition `total - unknown_location`; withheld unless both inputs are valid and the result is non-negative. |
| Active real matches | `get_overview({})` | `exact_match`, `nearby_alternative`, `tentative_match` | Sum of repository-filtered non-legacy active match rows. Any missing/malformed component withholds the KPI. |
| Delivered leads | `get_overview({})` | `telegram_delivered` from immutable Telegram alert records | Recorded deliveries only; no send inference or live lookup. |
| Priority review queue | `get_leads({})` | Repository order `lead_score DESC`, then `first_seen/fetched_at DESC`; stored status/classification/score/area/budget-confidence/budget/match fields | Preserve repository ordering; select actionable `new` hot/qualified/watch leads. Review reason is a transparent label from stored unknown/low-confidence/match state, not a new ranking score. Low/unknown-confidence budgets are labeled “Budget needs confirmation”; any sanitized parsed range is secondary evidence only. |
| Sanitized excerpt | `get_leads({})` | Repository-sanitized `raw_text` | Apply the shared excerpt formatter again; never display author/contact fields. |
| Independent volume stages | `get_overview({})` | `total`, `hot`, `qualified`, active real match fields, `telegram_delivered` | Clearly labeled independent recorded volumes; never described as conversion or a sequential cohort. |
| Classification distribution | `get_leads({})` | Stored `lead_class` | Transparent display grouping: hot/qualified → genuine seeker; watch/missing → review required; agent/broker → offering; irrelevant/spam → irrelevant. No classifier rerun. |
| Match-quality distribution | `get_leads({})` | Sanitized `matches[].match_type`, `matches[].is_legacy` | Exact/Nearby/Tentative count only active real match rows. Leads without an active real match count as No match. Legacy rows are counted only in historical disclosure. |
| Latest scheduler run | `get_scheduler_status()` | `latest_run.status`, timestamps, phase, stored run counts | Missing fields remain “Not recorded.” No run action. |
| Last successful run | `get_scheduler_status()` | `last_successful_run` | Human-readable stored state and timestamp only. |
| Interruption state | `get_scheduler_status()` | `interrupted_runs[].reconciliation` | `required` is blocking red; `completed` is historical muted state. |
| Lock state | `get_scheduler_status()` | `lock.locked` | Free is confirmed. Held without sufficient healthy-running evidence is blocking; no unlock action. |
| Current-run cost | `get_scheduler_status()` | No reliable per-run-incurred-cost field is currently stored | Render `Not recorded`. `latest_run.usage_total_usd` is not used because the scheduler can store a configured charge cap there before any provider call; presenting it as incurred cost would invent provenance. |
| Monthly cumulative usage | `get_scheduler_status()` | `monthly_usage_usd` | Displayed independently from current-run cost. |
| Cost thresholds | `get_scheduler_status()` | `warn_usd`, `stop_usd` | Stored thresholds only; progress is a transparent usage/stop presentation ratio, not a conversion metric. |

## Deliberately excluded

- Private author fields and contacts.
- Tokens, chat IDs, `.env` values, host paths, or process identifiers.
- Raw dictionaries, tuples, JSON, run-log text, and synthetic/legacy inventory IDs.
- False-positive rates, inferred conversion rates, opaque priority formulas, or unstored cost provenance.
