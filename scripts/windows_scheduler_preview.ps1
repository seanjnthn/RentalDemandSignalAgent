<#
.SYNOPSIS
Preview the proposed Windows Scheduled Task configuration without changing Windows.

.DESCRIPTION
Shows what 'windows_scheduler_install.ps1 -ConfirmInstall' would create. Does NOT
create, modify, enable, or run any Windows Scheduled Task. Safe to run anytime.

Recommendation: run from a PowerShell prompt (not git-bash) so script-relative paths
resolve correctly. Pass -RepoRoot explicitly if the script location cannot be derived.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('ScheduledCanary', 'Daily')]
    [string]$TriggerMode,

    [Parameter(Mandatory = $true)]
    [string]$At,  # e.g. "08:30" (host local time)

    [string]$TaskName = 'RentalDemandSignalAgent-Daily',
    [string]$RepoRoot = '',  # empty => derive from script location; abort if unresolvable
    [switch]$Enable  # separate explicit enable switch; default task is Disabled
)

$ErrorActionPreference = 'Stop'
$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $script:ScriptDir 'scheduler_common.ps1')

$RepoRoot = Get-RepoRoot -ExplicitRepoRoot $RepoRoot
Show-TimezonePreflight

Write-Host "PREVIEW ONLY - no Windows change will be made." -ForegroundColor Yellow
Write-Host "Repository root : $RepoRoot"
Write-Host "Task name       : $TaskName"
Write-Host "Trigger mode    : $TriggerMode"
Write-Host "At (local)      : $At"

# Resolve the Python executable that the task WOULD use (never bare 'python').
$python = Resolve-PythonExecutable -RepoRoot $RepoRoot
Write-Host "Python exe      : $python" -ForegroundColor Cyan
Write-Host "Initial state   : $(if ($Enable) { 'Enabled' } else { 'Disabled' })"

$actionArgs = "-m rdsa.cli scheduled-run --confirm-scheduled-run --trigger-type $TriggerMode"
Write-Host "Action          : $python $actionArgs"
Write-Host "Working dir     : $RepoRoot"
Write-Host "Note            : Task passes --confirm-scheduled-run only. Apify/Telegram live flags are"
Write-Host "                  enabled in-process by the agent after preflight; NO tokens are embedded in the task."
Write-Host "Idempotent      : install is a no-op if the task name already exists."
