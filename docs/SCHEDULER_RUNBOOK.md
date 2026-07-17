# Scheduler Runbook (v0.7.2)

**Release status:** v0.7.2 is merged and tagged, **defaults disabled**. The existing
out-of-band Windows task remains registered but disabled; it was not updated or run by
this release step. Reinstall/update it separately only after an explicit operator review.

## Safety defaults (all OFF)

| Variable | Default | Effect |
|---|---|---|
| `RDSA_SCHEDULER_ENABLED` | `false` | scheduled runs refuse unless explicitly `true` |
| `RDSA_SCHEDULER_SEND_ENABLED` | `false` | delivery suppressed even when a run executes |
| `APIFY_LIVE_ENABLED` | `false` | no live Apify; gated behind preflight + in-process flag |
| `RDSA_TELEGRAM_SEND_ENABLED` | `false` | no Telegram send |

In addition, `scheduled-run` requires the explicit `--confirm-scheduled-run` flag;
without it the CLI refuses. **Nothing runs or sends automatically.**

## Windows launcher behavior

The PowerShell-facing trigger names remain stable and map to the exact CLI values:

| PowerShell mode | CLI trigger value |
|---|---|
| `ScheduledCanary` | `scheduled_canary` |
| `Daily` | `daily_schedule` |

Preview and install print both values. The generated Task Scheduler action uses an
absolute `powershell.exe` path and an absolute `scripts/windows_scheduler_run.ps1`
path, rather than storing a direct Python command:

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <RepoRoot>\scripts\windows_scheduler_run.ps1 -RepoRoot <RepoRoot> -TriggerMode scheduled_canary -ConfirmRun
```

The launcher resolves `<RepoRoot>\.venv\Scripts\python.exe` and sets
`RDSA_SCHEDULER_ENABLED=true` only in its own process before starting the child.
`RDSA_SCHEDULER_SEND_ENABLED=false` is the default. Sending requires the separate,
explicit `-EnableScheduledSend` switch. The launcher restores prior process values in
`finally`; it never edits `.env` or writes user-scope or machine-scope environment
variables. No token, chat ID, or other secret is placed in task arguments.

The installed task currently retains its old action until it is separately reinstalled
or updated. The patched preview/install scripts generate the launcher action above.

## Read-only status (always safe)

```powershell
# Dashboard lock/ledger/flags (no Windows change)
python -m rdsa.cli scheduler-status
```

```powershell
# Preview the Windows task that *would* be created (no change)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <RepoRoot>\scripts\windows_scheduler_preview.ps1 -TriggerMode ScheduledCanary -At "08:30"
```

## Fail-closed refusal (safe no-op)

```powershell
$env:RDSA_SCHEDULER_ENABLED = "false"
$env:RDSA_SCHEDULER_SEND_ENABLED = "false"
<RepoRoot>\.venv\Scripts\python.exe -m rdsa.cli scheduled-run `
  --confirm-scheduled-run `
  --trigger-type scheduled_canary
```

With scheduler flags false, this prints `Scheduler disabled: ...`, returns refusal JSON,
and currently exits `0`. It returns before acquiring the lock or opening the scheduled-run
ledger path: zero Apify calls, zero Telegram calls, and no database mutation.

## Controlled process-local activation path

For a separately approved canary, invoke the launcher with explicit confirmation. The
launcher enables scheduled execution only for its child process and keeps sending off:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File <RepoRoot>\scripts\windows_scheduler_run.ps1 `
  -RepoRoot <RepoRoot> -TriggerMode scheduled_canary -ConfirmRun
```

Add `-EnableScheduledSend` only as a separate, explicit sending approval. Do not put
either scheduler flag in `.env` for this launcher path; the launcher does not modify
`.env`, user environment, or machine environment.

## Task installation/update (out of band)

1. Preview the mapped action first.
2. Separately reinstall/update the task, **Disabled by default**, only with explicit
   operator approval:
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File <RepoRoot>\scripts\windows_scheduler_install.ps1 -ConfirmInstall -TriggerMode ScheduledCanary -At "08:30"
   ```
3. Do not enable or run the task until a separate live-canary gate is approved.
4. Verify:
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File <RepoRoot>\scripts\windows_scheduler_status.ps1
   ```

## Deactivation / rollback

```powershell
pwsh scripts/windows_scheduler_disable.ps1 -ConfirmDisable
# or fully remove:
pwsh scripts/windows_scheduler_remove.ps1 -ConfirmRemove
```

Then set both kill switches back to `false`. No code change is required to deactivate.
**Rollback tag:** `v0.7.1-windows-launcher-hardening` (the prior merged launcher
release). Use `git checkout v0.7.1-windows-launcher-hardening` to inspect or roll back.

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
