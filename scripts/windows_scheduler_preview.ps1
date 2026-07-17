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

$mode = Get-TriggerModeInfo -TriggerMode $TriggerMode
$python = Resolve-PythonExecutable -RepoRoot $RepoRoot
$actionSpec = Get-SchedulerTaskAction -RepoRoot $RepoRoot -TriggerMode $TriggerMode

Write-Host "PREVIEW ONLY - no Windows change will be made." -ForegroundColor Yellow
Write-Host "Repository root : $RepoRoot"
Write-Host "Task name       : $TaskName"
Write-Host "Trigger mode (PowerShell) : $($mode.PowerShellMode)"
Write-Host "CLI trigger value        : $($mode.CliMode)"
Write-Host "At (local)      : $At"
Write-Host "Python exe      : $python" -ForegroundColor Cyan
Write-Host "Initial state   : $(if ($Enable) { 'Enabled' } else { 'Disabled' })"

Write-Host "Action          : $($actionSpec.Execute) $($actionSpec.Arguments)"
Write-Host "Working dir     : $RepoRoot"
Write-Host "Note            : Action invokes the process-local launcher with scheduler sending disabled by default."
Write-Host "                  The launcher enables scheduler execution only in its own process; NO tokens are embedded in the task."
Write-Host "Idempotent      : install is a no-op if the task name already exists."
