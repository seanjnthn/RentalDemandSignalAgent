"""Offline / static verification for the Windows scheduler launcher hardening.

These tests shell out to `powershell` (Windows only) and assert the launcher
scripts (a) never embed the bare executable name 'python' in a task action,
(b) prefer <RepoRoot>/.venv/Scripts/python.exe, (c) resolve the system Python to
an absolute path ending in python.exe, (d) abort safely when no interpreter is
resolvable, (e) preview and install resolve the SAME executable, (f) task
arguments contain no secrets, and (g) preview makes no Windows change.

No Windows Scheduled Task is ever created/registered/enabled/run by these tests.
Skipped automatically on hosts without powershell.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
PREVIEW = SCRIPTS / "windows_scheduler_preview.ps1"
INSTALL = SCRIPTS / "windows_scheduler_install.ps1"
COMMON = SCRIPTS / "scheduler_common.ps1"
TASK_NAME = "RentalDemandSignalAgent-Daily"

POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(
    POWERSHELL is None, reason="powershell/pwsh not available on this host"
)


def _run_powershell(script: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-Command", f"& '{script}' " + " ".join(args)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def _current_python_exe() -> str:
    return sys.executable.replace("/", "\\")


def _probe_task() -> str:
    cp = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"if(Get-ScheduledTask -TaskName '{TASK_NAME}' -ErrorAction SilentlyContinue)"
         "{'TASK_EXISTS'}else{'NO_TASK'}"],
        capture_output=True, text=True, timeout=60)
    return cp.stdout.strip()


def test_preview_resolves_absolute_python_no_bare_name():
    cp = _run_powershell(PREVIEW, "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    assert cp.returncode == 0, cp.stderr
    assert "Python exe" in cp.stdout
    action_line = next((l for l in cp.stdout.splitlines()
                        if l.strip().startswith("Action")), "")
    exe = action_line.split(":", 1)[1].strip().split(" -m")[0].strip()
    assert exe.lower().endswith("python.exe"), f"action executable not python.exe: {exe}"
    assert exe.startswith(("C:\\", "\\\\", "/")), f"action executable not absolute: {exe}"
    assert not re.search(r"(?i)(?<![\\/\.])python(?=\s|'|\")", action_line), \
        f"bare 'python' found in action: {action_line}"


def test_preview_makes_no_windows_change():
    pre = _probe_task()
    cp = _run_powershell(PREVIEW, "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    assert cp.returncode == 0, cp.stderr
    assert "PREVIEW ONLY" in cp.stdout
    post = _probe_task()
    assert pre == "NO_TASK" and post == "NO_TASK", f"task state changed: {pre} -> {post}"


def test_venv_python_preferred(tmp_path):
    repo = tmp_path / "fakerepo"
    repo.mkdir(parents=True)
    (repo / "data").mkdir()  # scheduler-status lazily creates the DB here
    venv_py = repo / ".venv" / "Scripts" / "python.exe"
    # Symlink the REAL venv directory into the fake repo so the staged .venv
    # python has all dependencies (requests, etc.) needed by `scheduler-status`.
    # This proves preference (the resolver picks <RepoRoot>/.venv/Scripts/python.exe),
    # not that a placeholder file is chosen.
    real_venv = Path(sys.executable).parent.parent
    try:
        os.symlink(real_venv, repo / ".venv")
    except OSError as e:
        pytest.skip(f"symlink privilege unavailable on this host: {e}")
    assert venv_py.exists(), "symlinked venv python missing"
    # Stage the real rdsa package so '-m rdsa.cli' is importable from the fake repo.
    shutil.copytree(REPO_ROOT / "rdsa", repo / "rdsa")
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy(COMMON, scripts_dir / "scheduler_common.ps1")
    shutil.copy(PREVIEW, scripts_dir / "windows_scheduler_preview.ps1")

    script = scripts_dir / "windows_scheduler_preview.ps1"
    cp = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", f"& '{script}' -TriggerMode ScheduledCanary -At 08:30 -RepoRoot '{repo}'"],
        capture_output=True, text=True, timeout=120)
    assert cp.returncode == 0, cp.stderr
    assert str(venv_py).replace("/", "\\") in cp.stdout, f"venv python not preferred:\n{cp.stdout}"


def test_system_python_resolves_absolute(tmp_path):
    repo = tmp_path / "fakerepo2"
    repo.mkdir(parents=True)
    (repo / "data").mkdir()  # scheduler-status lazily creates the DB here
    # Stage the real rdsa package so '-m rdsa.cli' is importable from the fake repo.
    shutil.copytree(REPO_ROOT / "rdsa", repo / "rdsa")
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy(COMMON, scripts_dir / "scheduler_common.ps1")
    shutil.copy(PREVIEW, scripts_dir / "windows_scheduler_preview.ps1")

    script = scripts_dir / "windows_scheduler_preview.ps1"
    cp = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", f"& '{script}' -TriggerMode Daily -At 09:00 -RepoRoot '{repo}'"],
        capture_output=True, text=True, timeout=120)
    assert cp.returncode == 0, cp.stderr
    assert _current_python_exe() in cp.stdout, \
        f"expected absolute system python {_current_python_exe()} in:\n{cp.stdout}"


def test_unresolved_python_aborts(tmp_path):
    repo = tmp_path / "fakerepo3"
    repo.mkdir(parents=True)
    scripts_dir = repo / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy(COMMON, scripts_dir / "scheduler_common.ps1")
    shutil.copy(PREVIEW, scripts_dir / "windows_scheduler_preview.ps1")

    script = scripts_dir / "windows_scheduler_preview.ps1"
    env = dict(os.environ)
    env["PATH"] = str(tmp_path)  # no python on PATH
    cp = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-Command", f"& '{script}' -TriggerMode Daily -At 09:00 -RepoRoot '{repo}'"],
        capture_output=True, text=True, timeout=120, env=env)
    assert cp.returncode != 0, f"expected abort, got success:\n{cp.stdout}\n{cp.stderr}"


def test_preview_and_install_resolve_same_executable():
    p = _run_powershell(PREVIEW, "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    assert p.returncode == 0, p.stderr
    i = _run_powershell(INSTALL, "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    assert i.returncode != 0, "install must refuse without -ConfirmInstall"
    preview_exe = next(l for l in p.stdout.splitlines() if "Python exe" in l).split(":", 1)[1].strip()
    install_exe = next((l for l in (i.stdout + i.stderr).splitlines()
                        if "Using Python exe" in l), "").split(":", 1)[1].strip()
    assert preview_exe == install_exe, f"exe mismatch: {preview_exe} != {install_exe}"


def test_task_arguments_contain_no_secrets():
    cp = _run_powershell(PREVIEW, "-TriggerMode", "Daily", "-At", "08:30")
    assert cp.returncode == 0, cp.stderr
    # Assert against concrete secret signatures, not the bare word 'token' (the
    # preview note legitimately says "NO tokens are embedded").
    blob = cp.stdout.lower()
    secret_signatures = (
        "telegram_bot_token", "apify_api_token", "apify_api_key",
        "chat_id", "bot" + "1234567890",  # bot<digits>:<secret> style
        "1234567890",  # a fake chat id
        ".env",
    )
    for forbidden in secret_signatures:
        assert forbidden not in blob, f"forbidden secret signature '{forbidden}' in preview output"
    # No Telegram/Apify credential-looking assignment in the action.
    assert "token=" not in blob and "chat_id=" not in blob
    assert "--confirm-scheduled-run" in cp.stdout
    assert "scheduled-run" in cp.stdout


def test_timezone_preflight_output_present():
    cp = _run_powershell(PREVIEW, "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    assert cp.returncode == 0, cp.stderr
    assert "Windows timezone ID" in cp.stdout
    assert "Current local time" in cp.stdout
    assert "Current UTC offset" in cp.stdout
    assert "Set-TimeZone" not in COMMON.read_text(encoding="utf-8")
