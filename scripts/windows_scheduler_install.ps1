<#
.SYNOPSIS
Install (register) the Windows Scheduled Task for the RDSA daily scheduler.

.DESCRIPTION
Creates the 'RentalDemandSignalAgent-Daily' scheduled task. The task action runs
the scheduled-run CLI with --confirm-scheduled-run only. Live Apify/Telegram flags
are enabled in-process by the agent after preflight; NO credentials are embedded in
the task command. Idempotent: re-running does not duplicate the task.

REQUIRES explicit -ConfirmInstall, an explicit -At time, and a trigger mode.
Task is created Disabled unless -Enable is also supplied.

Recommendation: run from a PowerShell prompt (not git-bash). Pass -RepoRoot explicitly
if the script location cannot be derived.
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('ScheduledCanary', 'Daily')]
    [string]$TriggerMode,

    [Parameter(Mandatory = $true)]
    [string]$At,  # e.g. "08:30" (host local time)

    [string]$TaskName = 'RentalDemandSignalAgent-Daily',
    [string]$RepoRoot = '',  # empty => derive from script location; abort if unresolvable
    [switch]$ConfirmInstall,
    [switch]$Enable  # separate explicit enable; default task is Disabled
)

$ErrorActionPreference = 'Stop'
$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $script:ScriptDir 'scheduler_common.ps1')

$RepoRoot = Get-RepoRoot -ExplicitRepoRoot $RepoRoot
Show-TimezonePreflight

# Resolve the Python executable that the task WOULD use (read-only; never bare 'python').
# Done before the install guard so the operator sees exactly what will run, and so
# preview and install are provably driven by the same resolver.
$python = Resolve-PythonExecutable -RepoRoot $RepoRoot
Write-Host "Using Python exe : $python" -ForegroundColor Cyan

if (-not $ConfirmInstall) {
    Write-Error "Refusing to install. Re-run with -ConfirmInstall, -At '<HH:MM>', and a trigger mode."
    exit 1
}

$repoRootNative = (Resolve-Path $RepoRoot).Path
$actionArgs = "-m rdsa.cli scheduled-run --confirm-scheduled-run --trigger-type $TriggerMode"

# Idempotent: remove any existing task with the same name first.
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing task '$TaskName' for idempotent install..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Use the absolute interpreter so the task does not depend on the scheduler user's PATH.
$action = New-ScheduledTaskAction -Execute $python -Argument $actionArgs -WorkingDirectory $repoRootNative
if ($TriggerMode -eq 'Daily') {
    $trigger = New-ScheduledTaskTrigger -Daily -At $At
} else {
    # ScheduledCanary: weekly is a conservative default for a canary; operator may adjust.
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $At
}
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

$state = if ($Enable) { 'Ready' } else { 'Disabled' }
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
if (-not $Enable) {
    Disable-ScheduledTask -TaskName $TaskName | Out-Null
}
Write-Host "Installed task '$TaskName' (state: $state). No credentials embedded in the task." -ForegroundColor Green
