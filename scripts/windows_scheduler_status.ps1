<#
.SYNOPSIS
Show the current status of the RDSA scheduled task (read-only).

.DESCRIPTION
Reports whether 'RentalDemandSignalAgent-Daily' exists, its state, next run time,
and last result. Performs no modification.
#>
param(
    [string]$TaskName = 'RentalDemandSignalAgent-Daily'
)
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    Write-Host "Task '$TaskName' is NOT registered." -ForegroundColor Yellow
    return
}
$info = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
Write-Host "Task name   : $TaskName"
Write-Host "State       : $($task.State)"
Write-Host "Enabled     : $($task.State -ne 'Disabled')"
Write-Host "Last result : $($info.LastTaskResult)"
Write-Host "Next run    : $($info.NextRunTime)"
Write-Host "Last run    : $($info.LastRunTime)"
