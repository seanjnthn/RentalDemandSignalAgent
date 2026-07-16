<#
.SYNOPSIS
Shared helpers for the RDSA Windows scheduler scripts (preview + install).

.DESCRIPTION
Single source of truth for:
  - reliable RepoRoot derivation from the script file;
  - Python executable resolution (no bare 'python' in the task action);
  - timezone preflight output (Windows TZ id, local time, UTC offset, WIB warning).

Both windows_scheduler_preview.ps1 and windows_scheduler_install.ps1 dot-source
this file so preview and install produce an IDENTICAL task action.
#>

# Resolve the directory that contains THIS script file, robustly across hosts
# (relative/dotted paths, git-bash, etc.). Falls back to $PSScriptRoot.
function Get-ScriptDirectory {
    [CmdletBinding()]
    param()
    $inv = $MyInvocation.MyCommand.Path
    if ($inv) {
        return Split-Path -Parent $inv
    }
    if ($PSScriptRoot) {
        return $PSScriptRoot
    }
    # Last resort: caller-supplied path.
    if ($script:ScriptDir) { return $script:ScriptDir }
    throw "Unable to derive script directory; pass -RepoRoot explicitly."
}

# Derive the repository root from the script's own location.
# Scripts live in <RepoRoot>/scripts, so the parent of the script dir is the repo root.
function Get-RepoRoot {
    [CmdletBinding()]
    param(
        [string]$ExplicitRepoRoot = ''
    )
    if ($ExplicitRepoRoot) {
        $resolved = $null
        try { $resolved = Resolve-Path -Path $ExplicitRepoRoot -ErrorAction Stop } catch { }
        if (-not $resolved) {
            throw "Explicit -RepoRoot '$ExplicitRepoRoot' could not be resolved."
        }
        return $resolved.Path
    }
    $scriptDir = Get-ScriptDirectory
    $parent = Split-Path -Parent $scriptDir
    $resolved = $null
    try { $resolved = Resolve-Path -Path $parent -ErrorAction Stop } catch { }
    if (-not $resolved) {
        throw "Could not resolve repository root from script location. Pass -RepoRoot explicitly."
    }
    return $resolved.Path
}

<#
.SYNOPSIS
Resolve the Python executable that will run the scheduled task.

.DESCRIPTION
Resolution order (per spec):
  1. <RepoRoot>\.venv\Scripts\python.exe when it exists.
  2. Otherwise the currently working interpreter: python -c "import sys; print(sys.executable)".
  3. Convert to an absolute path; confirm the file exists and ends in python.exe.
  4. From RepoRoot, confirm it can run: -m rdsa.cli scheduler-status
Aborts (throws) if no valid interpreter can be resolved. Never returns bare 'python'.
#>
function Resolve-PythonExecutable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    # 1. venv Python (preferred, fully repo-local, no PATH dependency).
    $venvPy = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (Test-Path $venvPy) {
        $exe = (Resolve-Path -Path $venvPy).Path
        Assert-ValidPython -PythonExe $exe -RepoRoot $RepoRoot
        return $exe
    }

    # 2. Currently working interpreter.
    $candidate = $null
    try {
        $candidate = & python -c "import sys; print(sys.executable)" 2>$null
    } catch {
        $candidate = $null
    }
    if (-not $candidate) {
        throw "No Python interpreter resolved: '.venv\Scripts\python.exe' absent and 'python' on PATH is unavailable. Install the venv or supply a Python on PATH."
    }

    # 3. Absolute path; exists; ends in python.exe.
    $abs = $null
    try { $abs = (Resolve-Path -Path $candidate -ErrorAction Stop).Path } catch { }
    if (-not $abs) {
        # candidate may already be absolute but unresolvable via Resolve-Path; normalize.
        $abs = [System.IO.Path]::GetFullPath($candidate)
    }
    Assert-ValidPython -PythonExe $abs -RepoRoot $RepoRoot
    return $abs
}

function Assert-ValidPython {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)] [string]$PythonExe,
        [Parameter(Mandatory = $true)] [string]$RepoRoot
    )
    if (-not (Test-Path $PythonExe)) {
        throw "Resolved Python '$PythonExe' does not exist."
    }
    if (-not ($PythonExe -replace '\\', '/' -match 'python\.exe$')) {
        throw "Resolved executable '$PythonExe' does not end in python.exe."
    }
    # 4. Smoke test: can it run -m rdsa.cli scheduler-status from the repo root?
    # Set PYTHONPATH to the repo root (inherited by Start-Process in PS 5.1, which
    # has no -Environment parameter) so 'rdsa' is importable regardless of cwd.
    $prevPY = $env:PYTHONPATH
    try { $env:PYTHONPATH = $RepoRoot } finally { }
    $ok = $false
    try {
        $p = Start-Process -FilePath $PythonExe -ArgumentList @('-m', 'rdsa.cli', 'scheduler-status') `
            -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardError 'NUL'
        $ok = ($p.ExitCode -eq 0)
    } catch {
        $ok = $false
    } finally {
        if ($null -eq $prevPY) { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue }
        else { $env:PYTHONPATH = $prevPY }
    }
    if (-not $ok) {
        throw "Resolved Python '$PythonExe' cannot run '-m rdsa.cli scheduler-status' from '$RepoRoot'."
    }
}

<#
.SYNOPSIS
Print timezone preflight and warn when the host is not UTC+07:00 (WIB / Asia/Jakarta).
#>
function Show-TimezonePreflight {
    [CmdletBinding()]
    param()
    $tz = [System.TimeZoneInfo]::Local
    $now = Get-Date
    $utcNow = $now.ToUniversalTime()
    $offset = $tz.GetUtcOffset($now)
    $offsetStr = '{0}{1:00}:{2:00}' -f $(if ($offset.TotalMinutes -lt 0) { '-' } else { '+' }), [Math]::Abs($offset.Hours), [Math]::Abs($offset.Minutes)
    $tzId = $tz.Id
    $wibOffset = [System.TimeSpan]::FromHours(7)
    $isWib = ($offset -eq $wibOffset)

    Write-Host "Timezone preflight" -ForegroundColor Yellow
    Write-Host "  Windows timezone ID : $tzId"
    Write-Host ("  Current local time  : " + $now.ToString('yyyy-MM-dd HH:mm:ss'))
    Write-Host "  Current UTC offset  : $offsetStr"
    if (-not $isWib) {
        Write-Host "  WARNING: host is not UTC+07:00 (Asia/Jakarta/WIB). Scheduled -At times are interpreted as THIS host's local time. Set the host timezone to '(UTC+07:00) Bangkok, Hanoi, Jakarta' if 08:30 should mean WIB." -ForegroundColor Red
    } else {
        Write-Host "  Timezone is UTC+07:00 (WIB) - OK." -ForegroundColor Green
    }
    # NOTE: this function never modifies the system timezone.
}
