<#
.SYNOPSIS
Preview the proposed Windows Scheduled Task configuration without changing Windows.

.DESCRIPTION
Shows what 'windows_scheduler_install.ps1 -ConfirmInstall' would create. Does NOT
create, modify, enable, or run any Windows Scheduled Task. Safe to run anytime.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('ScheduledCanary', 'Daily')]
    [string]$TriggerMode,

    [Parameter(Mandatory = $true)]
    [string]$At,  # e.g. "08:30" (Asia/Jakarta local operator time)

    [string]$TaskName = 'RentalDemandSignalAgent-Daily',
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')),
    [switch]$Enable  # separate explicit enable switch; default task is Disabled
)

Write-Host "PREVIEW ONLY - no Windows change will be made." -ForegroundColor Yellow
Write-Host "Repository root : $RepoRoot"
Write-Host "Task name       : $TaskName"
Write-Host "Trigger mode    : $TriggerMode"
Write-Host "At (local)      : $At"
Write-Host "Initial state   : $(if ($Enable) { 'Enabled' } else { 'Disabled' })"
$python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }
$action = "$python -m rdsa.cli scheduled-run --confirm-scheduled-run --trigger-type $TriggerMode"
Write-Host "Action          : $action"
Write-Host "Note            : Task passes --confirm-scheduled-run only. Apify/Telegram live flags are"
Write-Host "                  enabled in-process by the agent after preflight; NO tokens are embedded in the task."
Write-Host "Idempotent      : install is a no-op if the task name already exists."
