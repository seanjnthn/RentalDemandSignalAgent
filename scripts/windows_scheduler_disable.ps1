<#
.SYNOPSIS
Disable the RDSA scheduled task without removing it.

.DESCRIPTION
Disables 'RentalDemandSignalAgent-Daily' so it no longer fires, but keeps the task
registration for later re-enable. Requires confirmation.
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [string]$TaskName = 'RentalDemandSignalAgent-Daily',
    [switch]$ConfirmDisable
)
if (-not $ConfirmDisable) {
    Write-Error "Refusing to disable. Re-run with -ConfirmDisable."
    exit 1
}
Disable-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Write-Host "Disabled task '$TaskName' (kept for re-enable)." -ForegroundColor Green
