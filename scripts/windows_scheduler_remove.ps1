<#
.SYNOPSIS
Remove (unregister) the RDSA scheduled task entirely.

.DESCRIPTION
Unregisters 'RentalDemandSignalAgent-Daily'. Requires confirmation. After removal,
no schedule exists; re-install via windows_scheduler_install.ps1.
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [string]$TaskName = 'RentalDemandSignalAgent-Daily',
    [switch]$ConfirmRemove
)
if (-not $ConfirmRemove) {
    Write-Error "Refusing to remove. Re-run with -ConfirmRemove."
    exit 1
}
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Removed task '$TaskName'." -ForegroundColor Green
