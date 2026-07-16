# Scheduler Failure Modes (v0.7)

Enumerates fail-closed behaviors and the ledger/observability produced for each.

| # | Failure mode | Detection | Ledger status | Behavior | Recovery |
|---|---|---|---|---|---|
| 1 | Scheduler disabled | `RDSA_SCHEDULER_ENABLED=false` | (refused, no row) | Print safe refusal; no Apify/Telegram | enable switch + confirm |
| 2 | Missing confirmation | `--confirm-scheduled-run` absent | (refused, no row) | Print safe refusal; no paid run | pass flag |
| 3 | Lock conflict | lock file exists & process alive | `blocked_lock` | Abort before Apify; zero calls | wait or explicit unlock if dead |
| 4 | Invalid/missing inventory | `validate_real_inventory_for_scan` not ok | `failed` (invalid_inventory) | Stop before scan | fix `inventory_real.csv` |
| 5 | Cost limit | projected > stop threshold | `blocked_cost_limit` | Abort before Apify; zero calls | manual review |
| 6 | Cost warning | projected > warn threshold | (proceeds; warned) | Log warning only; stop threshold wins | n/a |
| 7 | Apify error | provider raises | `failed` (apify_error) | Fail closed; no 2nd paid run | manual run after fix |
| 8 | Uncertain Apify outcome | ambiguous result | `failed` (uncertain) | Require manual review | do not auto-retry |
| 9 | Malformed provider response | parse/validation error | `failed` | Fail closed | fix provider/contract |
| 10 | Database error | sqlite error | `failed` (database_error) | Fail closed; release lock | inspect DB |
| 11 | Telegram failure (send) | notifier raises | `failed` (telegram_failure) | Lead persisted; claim marked failed; no auto-repeat | retry delivery separately |
| 12 | Missing Telegram config (send requested) | token/chat absent | `failed` | Refuse delivery; leads still saved | configure `.env` |
| 13 | Invalid approved chat | chat_id mismatch | `failed` | Refuse delivery | fix `TELEGRAM_ALLOWED_CHAT_ID` |
| 14 | Stale lock | old lock file | (inspect only) | Never auto-deleted | explicit `scheduler-unlock --confirm-unlock` |
| 15 | Timeout | overall > `RDSA_SCHEDULER_TIMEOUT_SECONDS` | `failed` (timeout) | No automatic retry | manual run |
| 16 | Concurrent manual + scheduled | lock held | `blocked_lock` | Second aborts before Apify | serialize |
| 17 | Zero new eligible leads | new_posts>0 but none eligible | `completed_no_eligible_leads` | Zero Telegram calls | n/a |
| 18 | Zero new posts | all duplicates/refreshed | `completed_no_new_leads` | Zero Telegram calls | n/a |

## Exactly-once delivery

- `delivery_claims(post_id, channel)` is UNIQUE. A claim succeeds once; a second
  attempt returns False and never calls Telegram.
- A historical lead (refreshed, not new this run) is excluded by `new_post_ids`.
- `agent_broker` and `offering_supply` leads are not eligible (`preview_eligible`).

## No duplication of historical records

The scheduler only appends `scheduled_runs` ledger rows and new `leads`/`delivery_claims`
for genuinely new posts. It never updates historical alerts or delivery claims.

## Secrets hygiene

- `sanitized_error` strips Telegram tokens (`[REDACTED_TOKEN]`), absolute paths
  (`[path]`), and avoids raw stack traces in the ledger.
- Task Scheduler arguments contain only `--confirm-scheduled-run`; no tokens.
- Dashboard scheduler page omits tokens, chat IDs, `.env` values, usernames, paths.
