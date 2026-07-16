# Scheduler Specification (v0.7)

Safe, observable, once-daily scheduling foundation around the existing v0.6.4
pipeline. This milestone makes scheduled execution **technically ready** but does
**NOT** install, create, enable, or run a real Windows Scheduled Task.

## Scope

- Code + docs + tests only. No live Apify run, no Telegram send, no real task.
- Reuses the existing `process_raw` → classify → match → atomic-claim delivery path.
- Adds kill switches, a process lock, a run ledger, a cost guard, failure handling,
  Windows scripts (unexecuted), and a read-only dashboard page.

## Scheduled execution flow

1. Acquire process lock (atomic file in a git-ignored runtime dir).
2. Create a `scheduled_runs` ledger record (`starting`).
3. Run preflight (inventory validation).
4. Check projected cost (current monthly + max run cost) vs stop threshold.
5. Load and validate real inventory.
6. Execute **one** batched Apify Actor request (no paid retry).
7. Normalize + persist via `process_raw`.
8. Use **current-run `new_post_ids` only** for eligibility.
9. Classify + match.
10. Atomically claim eligible deliveries (existing `delivery_claims` unique guard).
11. Send **at most 3 cards** only when `RDSA_SCHEDULER_SEND_ENABLED=true`.
12. Complete the ledger (`completed` / `completed_no_new_leads` / `completed_no_eligible_leads`).
13. Release the process lock.
14. Restore process-local flags (`APIFY_LIVE_ENABLED=false`, `TELEGRAM_SEND_ENABLED=false`).

## Kill switches (defaults: OFF)

- `RDSA_SCHEDULER_ENABLED=false`
- `RDSA_SCHEDULER_SEND_ENABLED=false`

Rules:

1. Both default to false.
2. Scheduled execution refuses to run unless `RDSA_SCHEDULER_ENABLED=true` **and** an
   explicit CLI confirmation flag (`--confirm-scheduled-run`) is supplied.
3. Telegram delivery during a scheduled run additionally requires
   `RDSA_SCHEDULER_SEND_ENABLED=true`.
4. Existing `.env` values `APIFY_LIVE_ENABLED=false` and `RDSA_TELEGRAM_SEND_ENABLED=false`
   remain unchanged.
5. Live execution is enabled **in-process only** after all scheduler preflight checks pass.
6. All flags return to their safe process state after completion or error.
7. Secrets are never stored in Task Scheduler arguments.

## Process locking

- Cross-platform atomic file creation (`os.open(O_CREAT|O_EXCL|O_WRONLY)`).
- Lock payload: `run_id`, `pid`, `started_at`, `hostname`.
- Lock file lives in a git-ignored runtime directory.
- Normal completion removes the lock; exceptions also release it where safe.
- **Stale locks are NOT auto-deleted merely because they are old.**
- A separate `scheduler-unlock --confirm-unlock` command is required.
- A lock whose process is verifiably still running is never cleared.

## Run ledger (`scheduled_runs`)

Idempotent table. Fields: `run_id`, `trigger_type` (manual|scheduled_canary|daily_schedule),
`started_at`, `finished_at`, `status`, `actor_run_id`, `raw_posts`, `normalized_posts`,
`existing_posts`, `new_posts`, `eligible_leads`, `claimed_deliveries`, `sent_cards`,
`usage_total_usd`, `monthly_usage_usd`, `error_code`, `sanitized_error`,
`scheduler_send_enabled`, `process_id`.

Status vocabulary: `starting`, `preflight_failed`, `running`, `completed`,
`completed_no_new_leads`, `completed_no_eligible_leads`, `blocked_cost_limit`,
`blocked_lock`, `failed`.

- No secrets or full API responses stored.
- Raw exception text is **sanitized** (tokens, absolute paths, usernames stripped).
- Every attempted scheduled run gets an auditable terminal state where possible.
- Historical lead, alert, and delivery records remain unchanged.

## Cost policy

- `projected_monthly_usage = current_monthly_usage + configured_max_run_cost`.
- Abort **before Apify** when projected usage exceeds the stop threshold.
- Warning threshold logs a warning but never overrides the stop threshold.
- Never confuse current-run cost / cumulative monthly cost / warning / stop thresholds.
- No automatic retry after a charged or uncertain Actor attempt.
- If Actor outcome is uncertain, record `failed`/uncertain and require manual review.

## Retry policy

- **No automatic paid retry** of Apify under any failure (cost, error, timeout, uncertain).
- **No automatic retry** of a failed Telegram send.

## Timeout policy

- Configurable overall timeout (default **15 minutes** / 900s) via `RDSA_SCHEDULER_TIMEOUT_SECONDS`.
- A timeout must not cause automatic retry.

## Failure recovery

Fail closed for: invalid inventory, missing Telegram configuration when scheduled sending
is requested, invalid approved chat, lock conflict, projected cost above stop, Apify error,
malformed provider response, database error, Telegram failure.

- Apify failure → no second paid run.
- Telegram failure → no automatic repeat; lead persistence remains valid.
- Failed delivery claims remain auditable.
- No raw credentials in logs; no Telegram failure-summary message in v0.7.
- Failures recorded locally in the ledger and logs.

## Manual fallback

Operators may always run `python -m rdsa.cli scheduled-run --confirm-scheduled-run`
manually (with kill switches enabled) or use the existing `pilot-send` path. The
lock prevents concurrent runs; a stale lock is cleared only via explicit
`scheduler-unlock --confirm-unlock` (and never while its process is alive).

## Activation / rollback

- Activation (out of scope for v0.7): set `RDSA_SCHEDULER_ENABLED=true`, optionally
  `RDSA_SCHEDULER_SEND_ENABLED=true`, then install the Windows task via the provided
  scripts with `-ConfirmInstall -At <HH:MM> -TriggerMode Daily` (task starts Disabled
  unless `-Enable` is passed).
- Rollback: `windows_scheduler_disable.ps1 -ConfirmDisable` or `-ConfirmRemove`;
  reset both kill switches to false. No code rollback required for deactivation.
