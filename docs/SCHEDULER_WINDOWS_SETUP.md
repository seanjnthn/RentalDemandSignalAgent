# Scheduler Windows Setup (v0.7)

Reference for installing the Windows Scheduled Task **out of band** (not performed in
the v0.7 milestone). All scripts live in `scripts/` and are **never executed** by the
agent itself.

## Prerequisites

- Windows 10/11 with Task Scheduler.
- Python available (repository `.venv\Scripts\python.exe` or `python` on PATH).
- `.env` with `RDSA_SCHEDULER_ENABLED=true` (and `RDSA_SCHEDULER_SEND_ENABLED=true`
  for delivery). `APIFY_LIVE_ENABLED`/`RDSA_TELEGRAM_SEND_ENABLED` stay false in `.env`;
  the agent enables them in-process after preflight.
- Asia/Jakarta local operator time used for scheduling.

## Scripts

| Script | Purpose | Mutates Windows? |
|---|---|---|
| `windows_scheduler_preview.ps1` | Show proposed task config | No |
| `windows_scheduler_install.ps1` | Register the task (Disabled by default) | Yes (with `-ConfirmInstall`) |
| `windows_scheduler_disable.ps1` | Disable the task (keep registration) | Yes (with `-ConfirmDisable`) |
| `windows_scheduler_remove.ps1` | Unregister the task | Yes (with `-ConfirmRemove`) |
| `windows_scheduler_status.ps1` | Show task status | No |

## Install (task starts Disabled)

```powershell
pwsh scripts/windows_scheduler_install.ps1 -ConfirmInstall -TriggerMode Daily -At "08:30"
```

Enable only after a successful canary:

```powershell
pwsh scripts/windows_scheduler_install.ps1 -ConfirmInstall -TriggerMode Daily -At "08:30" -Enable
```

## Requirements enforced by the scripts

1. **Preview** performs no task creation.
2. **Install** requires:
   - explicit `-ConfirmInstall`;
   - an explicit time argument `-At "HH:MM"`;
   - an explicit trigger mode (`ScheduledCanary` | `Daily`).
3. Default installation state is **Disabled** unless a separate explicit `-Enable` switch
   is provided.
4. Task action uses the repository's actual Python executable, sets the repository
   working directory, runs `python -m rdsa.cli scheduled-run --confirm-scheduled-run`,
   and uses **process-local** scheduler flags. **No Telegram or Apify tokens** in the task
   command.
5. Asia/Jakarta local operator time via Windows local scheduling.
6. **No hardcoded daily execution time** in code or documentation (operator supplies `-At`).
7. Disable/remove scripts require confirmation.
8. Installation is **idempotent** (re-running does not duplicate the task; it replaces it).
9. Clear task name: **`RentalDemandSignalAgent-Daily`**.

## Post-install verification

```powershell
pwsh scripts/windows_scheduler_status.ps1
python -m rdsa.cli scheduler-status
```

## Rollback

```powershell
pwsh scripts/windows_scheduler_disable.ps1 -ConfirmDisable
# or
pwsh scripts/windows_scheduler_remove.ps1 -ConfirmRemove
```

Then reset `RDSA_SCHEDULER_ENABLED`/`RDSA_SCHEDULER_SEND_ENABLED` to `false`.
