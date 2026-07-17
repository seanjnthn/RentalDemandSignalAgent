<#
.SYNOPSIS
Run one confirmed scheduled scan with scheduler kill switches scoped to this process.

.DESCRIPTION
This is the only task action entrypoint. It enables scheduled execution in this
PowerShell process, keeps scheduled sending disabled unless -EnableScheduledSend is
explicitly supplied, invokes the project-local Python, and restores the prior process
environment before exiting. It never writes .env, user environment, or machine
environment state.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('scheduled_canary', 'daily_schedule')]
    [string]$TriggerMode,

    [string]$RepoRoot = '',

    [Parameter(Mandatory = $true)]
    [switch]$ConfirmRun,

    [switch]$EnableScheduledSend
)

$ErrorActionPreference = 'Stop'
$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $script:ScriptDir 'scheduler_common.ps1')

if (-not $ConfirmRun) {
    Write-Error 'Refusing to run. Re-run with -ConfirmRun.'
    exit 1
}

$RepoRoot = Get-RepoRoot -ExplicitRepoRoot $RepoRoot
$python = Resolve-PythonExecutable -RepoRoot $RepoRoot
$environmentNames = @('RDSA_SCHEDULER_ENABLED', 'RDSA_SCHEDULER_SEND_ENABLED')
$previous = @{}
foreach ($name in $environmentNames) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

$exitCode = 1
$locationPushed = $false
try {
    [Environment]::SetEnvironmentVariable('RDSA_SCHEDULER_ENABLED', 'true', 'Process')
    $sendValue = if ($EnableScheduledSend) { 'true' } else { 'false' }
    [Environment]::SetEnvironmentVariable('RDSA_SCHEDULER_SEND_ENABLED', $sendValue, 'Process')

    Push-Location -LiteralPath $RepoRoot
    $locationPushed = $true
    Write-Host "Scheduler enabled process-local : true"
    Write-Host "Scheduler send process-local    : $sendValue"
    Write-Host "Python exe                     : $python"
    Write-Host "Trigger type                   : $TriggerMode"

    & $python -m rdsa.cli scheduled-run --confirm-scheduled-run --trigger-type $TriggerMode
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 0 }
} catch {
    Write-Error $_
    $exitCode = 1
} finally {
    if ($locationPushed) { Pop-Location }
    foreach ($name in $environmentNames) {
        $value = $previous[$name]
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

exit $exitCode