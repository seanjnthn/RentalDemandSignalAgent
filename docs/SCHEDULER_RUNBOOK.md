# Scheduler Runbook (v0.7)

**Release status:** built and merged, **defaults disabled**, and **no Windows Scheduled
Task is installed by this release**. This runbook documents the intended operation and
the safe manual paths available today.

## Safety defaults (all OFF)

| Variable | Default | Effect |
|---|---|---|
| `RDSA_SCHEDULER_ENABLED` | `false` | scheduled runs refuse unless explicitly `true` |
| `RDSA_SCHEDULER_SEND_ENABLED` | `false` | delivery suppressed even when a run executes |
| `APIFY_LIVE_ENABLED` | `false` | no live Apify; gated behind preflight + in-process flag |
| `RDSA_TELEGRAM_SEND_ENABLED` | `false` | no Telegram send |

In addition, `scheduled-run` requires the explicit `--confirm-scheduled-run` flag;
without it the CLI refuses. **Nothing runs or sends automatically.**

## Read-only status (always safe)

```powershell
# Dashboard lock/ledger/flags (no Windows change)
python -m rdsa.cli scheduler-status
```

```powershell
# Preview the Windows task that *would* be created (no change)
pwsh scripts/windows_scheduler_preview.ps1 -TriggerMode Daily -At "08:30"
```

## Manual scheduled run (today, with kill switches enabled)

```powershell
$env:RDSA_SCHEDULER_ENABLED = "true"
# optional, for delivery:
# $env:RDSA_SCHEDULER_SEND_ENABLED = "true"
python -m rdsa.cli scheduled-run --confirm-scheduled-run --trigger-type daily_schedule
```

The run acquires the lock, records a ledger row, validates inventory, checks cost, runs
one Apify batch (in-process live only after preflight), persists, claims deliveries
atomically, sends ≤3 cards only if sending enabled, then restores flags and releases the lock.

## Activation (out of scope for v0.7 — documented for readiness)

1. Set `RDSA_SCHEDULER_ENABLED=true` in `.env` (and `RDSA_SCHEDULER_SEND_ENABLED=true`
   only when delivery is desired).
2. Install the task, **Disabled by default**:
   ```powershell
   pwsh scripts/windows_scheduler_install.ps1 -ConfirmInstall -TriggerMode Daily -At "08:30"
   ```
3. Enable only after a successful canary review:
   ```powershell
   pwsh scripts/windows_scheduler_install.ps1 -ConfirmInstall -TriggerMode Daily -At "08:30" -Enable
   # or:
   pwsh scripts/windows_scheduler_enable.ps1 -ConfirmEnable
   ```
4. Verify:
   ```powershell
   pwsh scripts/windows_scheduler_status.ps1
   ```

## Deactivation / rollback

```powershell
pwsh scripts/windows_scheduler_disable.ps1 -ConfirmDisable
# or fully remove:
pwsh scripts/windows_scheduler_remove.ps1 -ConfirmRemove
```

Then set both kill switches back to `false`. No code change is required to deactivate.
**Rollback tag:** `v0.7-daily-scheduler-foundation` (detached HEAD at the merged
foundation). Use `git checkout v0.7-daily-scheduler-foundation` to revert.

## Lock recovery

- A normal run releases its lock on completion or error.
- **Stale locks are not auto-deleted.** Inspect first:
  ```powershell
  python -m rdsa.cli scheduler-status
  ```
- Only clear a lock explicitly, and never while its process is alive:
  ```powershell
  python -m rdsa.cli scheduler-unlock --confirm-unlock
  ```

## Cost guard

- Projected monthly usage = current monthly + configured max run cost (0.10 USD).
- The run aborts **before Apify** if projected exceeds the stop threshold
  (`APIFY_STOP_USD`). Warning threshold logs only.
- No automatic paid retry.

## Delivery / failure behavior

- **No automatic Telegram retry.** On Telegram failure the lead stays persisted and the
  delivery claim is marked `failed` (auditable). `send_lead_cards` claims atomically
  *before* the network call, so no duplicate send and no retry loop.
- **No automatic paid (Apify) retry.** A provider failure records a `failed` ledger row
  and returns; manual retry only via a fresh manual run after the fix.

## Failure triage

| Symptom | Ledger status | Action |
|---|---|---|
| Another run active | `blocked_lock` | wait; or unlock only if process dead |
| Cost limit | `blocked_cost_limit` | manual review; do not force |
| Apify error | `failed` (apify_error) | manual retry via manual run after fix |
| Telegram failure | `failed` (telegram_failure) | leads persist; retry delivery separately |
| Invalid inventory | `failed` (invalid_inventory) | fix `inventory_real.csv` |

## Safety invariants

- No secrets in Task Scheduler arguments (only `--confirm-scheduled-run`).
- Historical leads/alerts/delivery_claims are never modified by a run.
- Dashboard scheduler page is read-only (no run/enable/send/unlock buttons).

## Windows process cleanup note (Streamlit review/demo)

Stopping the parent shell/wrapper may not stop the child `python -m
streamlit.web.bootstrap` process. Operators should verify the listening port
(`Get-NetTCPConnection -LocalPort <port>`) and terminate the actual child process
(`taskkill /PID <pid> /F`) when necessary.
