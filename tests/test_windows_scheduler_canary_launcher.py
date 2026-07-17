"""Offline tests for the v0.7.2 Windows ScheduledCanary launcher path."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
COMMON = SCRIPTS / "scheduler_common.ps1"
PREVIEW = SCRIPTS / "windows_scheduler_preview.ps1"
INSTALL = SCRIPTS / "windows_scheduler_install.ps1"
RUNNER = SCRIPTS / "windows_scheduler_run.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(
    POWERSHELL is None, reason="powershell/pwsh not available on this host"
)


FAKE_CLI = r'''import json
import os
import sys
from pathlib import Path

capture = Path(os.environ["RDSA_TEST_CAPTURE"])
if sys.argv[1:] == ["scheduler-status"]:
    capture.write_text(json.dumps({"argv": sys.argv[1:]}), encoding="utf-8")
    raise SystemExit(0)

capture.write_text(json.dumps({
    "argv": sys.argv[1:],
    "scheduler_enabled": os.environ.get("RDSA_SCHEDULER_ENABLED"),
    "scheduler_send_enabled": os.environ.get("RDSA_SCHEDULER_SEND_ENABLED"),
    "apify_live_enabled": os.environ.get("APIFY_LIVE_ENABLED"),
    "telegram_send_enabled": os.environ.get("RDSA_TELEGRAM_SEND_ENABLED"),
}), encoding="utf-8")
raise SystemExit(int(os.environ.get("RDSA_TEST_CHILD_EXIT", "0")))
'''


def _run_ps_file(script: Path, *args: str, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def _action_line(output: str) -> str:
    return next(line.strip() for line in output.splitlines() if line.strip().startswith("Action"))


def _fake_repo(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    repo = tmp_path / "fake-repo"
    scripts = repo / "scripts"
    fake_venv = repo / ".venv"
    fake_scripts = fake_venv / "Scripts"
    rdsa = repo / "rdsa"
    scripts.mkdir(parents=True)
    fake_scripts.mkdir(parents=True)
    rdsa.mkdir(parents=True)
    (rdsa / "__init__.py").write_text("", encoding="utf-8")
    (rdsa / "cli.py").write_text(FAKE_CLI, encoding="utf-8")
    shutil.copy2(sys.executable, fake_scripts / "python.exe")
    shutil.copy2(Path(sys.executable).parent.parent / "pyvenv.cfg", fake_venv / "pyvenv.cfg")
    shutil.copy(COMMON, scripts / COMMON.name)
    shutil.copy(RUNNER, scripts / RUNNER.name)
    capture = repo / "capture.json"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["RDSA_TEST_CAPTURE"] = str(capture)
    env["APIFY_LIVE_ENABLED"] = "false"
    env["RDSA_TELEGRAM_SEND_ENABLED"] = "false"
    return repo, capture, env


def _run_fake_runner(repo: Path, env: dict[str, str], *extra: str) -> subprocess.CompletedProcess:
    return _run_ps_file(
        repo / "scripts" / RUNNER.name,
        "-RepoRoot", str(repo),
        "-TriggerMode", "scheduled_canary",
        "-ConfirmRun",
        *extra,
        env=env,
    )


def test_trigger_mapping_is_user_facing_to_cli_value():
    canary = _run_ps_file(PREVIEW, "-RepoRoot", str(REPO_ROOT), "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    daily = _run_ps_file(PREVIEW, "-RepoRoot", str(REPO_ROOT), "-TriggerMode", "Daily", "-At", "08:30")
    assert canary.returncode == 0, canary.stderr
    assert daily.returncode == 0, daily.stderr
    assert "Trigger mode (PowerShell) : ScheduledCanary" in canary.stdout
    assert "CLI trigger value        : scheduled_canary" in canary.stdout
    assert "Trigger mode (PowerShell) : Daily" in daily.stdout
    assert "CLI trigger value        : daily_schedule" in daily.stdout


def test_preview_and_install_generate_same_launcher_action():
    preview = _run_ps_file(PREVIEW, "-RepoRoot", str(REPO_ROOT), "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    install = _run_ps_file(INSTALL, "-RepoRoot", str(REPO_ROOT), "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    assert preview.returncode == 0, preview.stderr
    assert install.returncode != 0, "install should refuse without confirmation"
    assert _action_line(preview.stdout) == _action_line(install.stdout + install.stderr)
    action = _action_line(preview.stdout)
    assert "powershell.exe" in action.lower()
    assert "windows_scheduler_run.ps1" in action
    assert "-TriggerMode scheduled_canary" in action
    assert "ScheduledCanary" not in action
    assert "RDSA_SCHEDULER_ENABLED" not in action
    assert "RDSA_SCHEDULER_SEND_ENABLED" not in action


def test_runner_defaults_send_false_and_child_receives_scheduler_enabled(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    result = _run_fake_runner(repo, env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(capture.read_text(encoding="utf-8"))
    assert payload["scheduler_enabled"] == "true"
    assert payload["scheduler_send_enabled"] == "false"
    assert payload["apify_live_enabled"] == "false"
    assert payload["telegram_send_enabled"] == "false"
    assert payload["argv"] == [
        "scheduled-run", "--confirm-scheduled-run", "--trigger-type", "scheduled_canary"
    ]


def test_runner_explicit_send_switch_changes_only_child_value(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    result = _run_fake_runner(repo, env, "-EnableScheduledSend")
    assert result.returncode == 0, result.stderr
    payload = json.loads(capture.read_text(encoding="utf-8"))
    assert payload["scheduler_enabled"] == "true"
    assert payload["scheduler_send_enabled"] == "true"
    assert payload["apify_live_enabled"] == "false"
    assert payload["telegram_send_enabled"] == "false"


def test_runner_accepts_daily_schedule(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    result = _run_ps_file(
        repo / "scripts" / RUNNER.name,
        "-RepoRoot", str(repo), "-TriggerMode", "daily_schedule", "-ConfirmRun", env=env
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(capture.read_text(encoding="utf-8"))["argv"] == [
        "scheduled-run", "--confirm-scheduled-run", "--trigger-type", "daily_schedule"
    ]


def test_runner_requires_explicit_confirmation(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    result = _run_ps_file(
        repo / "scripts" / RUNNER.name,
        "-RepoRoot", str(repo), "-TriggerMode", "scheduled_canary", env=env
    )
    assert result.returncode != 0
    assert not capture.exists()


def test_runner_restores_process_environment_and_does_not_write_user_machine(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    command = (
        f"$env:RDSA_SCHEDULER_ENABLED='outer-enabled'; "
        f"$env:RDSA_SCHEDULER_SEND_ENABLED='outer-send'; "
        f"$u1=[Environment]::GetEnvironmentVariable('RDSA_SCHEDULER_ENABLED','User'); "
        f"$m1=[Environment]::GetEnvironmentVariable('RDSA_SCHEDULER_ENABLED','Machine'); "
        f"& '{repo / 'scripts' / RUNNER.name}' -RepoRoot '{repo}' -TriggerMode scheduled_canary -ConfirmRun; "
        f"$u2=[Environment]::GetEnvironmentVariable('RDSA_SCHEDULER_ENABLED','User'); "
        f"$m2=[Environment]::GetEnvironmentVariable('RDSA_SCHEDULER_ENABLED','Machine'); "
        f"[pscustomobject]@{{processEnabled=$env:RDSA_SCHEDULER_ENABLED; processSend=$env:RDSA_SCHEDULER_SEND_ENABLED; userSame=($u1 -eq $u2); machineSame=($m1 -eq $m2)}} | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout.strip().splitlines()[-1])
    assert state == {
        "processEnabled": "outer-enabled",
        "processSend": "outer-send",
        "userSame": True,
        "machineSame": True,
    }


def test_runner_leaves_env_file_unchanged(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    env_file = repo / ".env"
    original = "RDSA_SCHEDULER_ENABLED=false\nRDSA_SCHEDULER_SEND_ENABLED=false\nSECRET=do-not-touch\n"
    env_file.write_text(original, encoding="utf-8")
    result = _run_fake_runner(repo, env)
    assert result.returncode == 0, result.stderr
    assert env_file.read_text(encoding="utf-8") == original


def test_runner_rejects_invalid_trigger(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    result = _run_ps_file(
        repo / "scripts" / RUNNER.name,
        "-RepoRoot", str(repo), "-TriggerMode", "ScheduledCanary", "-ConfirmRun", env=env
    )
    assert result.returncode != 0
    assert "ValidateSet" in (result.stderr + result.stdout) or "valid values" in (result.stderr + result.stdout)
    assert not capture.exists()


def test_runner_propagates_child_exit_code(tmp_path):
    repo, capture, env = _fake_repo(tmp_path)
    env["RDSA_TEST_CHILD_EXIT"] = "23"
    result = _run_fake_runner(repo, env)
    assert result.returncode == 23
    assert json.loads(capture.read_text(encoding="utf-8"))["scheduler_enabled"] == "true"


def test_runner_is_secret_free_and_has_no_network_client_code():
    text = RUNNER.read_text(encoding="utf-8").lower()
    for forbidden in ("telegram_bot_token", "apify_api_token", "chat_id="):
        assert forbidden not in text
    assert "invoke-webrequest" not in text
    assert "start-bitstransfer" not in text


def test_preview_preserves_task_state_and_makes_no_task_change():
    probe = (
        "$x=@(Get-ScheduledTask -TaskName 'RentalDemandSignalAgent-Daily' "
        "-ErrorAction SilentlyContinue); "
        "if($x){$x | Select-Object TaskName,State,TaskPath | ConvertTo-Json -Compress} else {'NO_TASK'}"
    )
    before = subprocess.run([POWERSHELL, "-NoProfile", "-Command", probe], capture_output=True, text=True, timeout=60)
    preview = _run_ps_file(PREVIEW, "-RepoRoot", str(REPO_ROOT), "-TriggerMode", "ScheduledCanary", "-At", "08:30")
    after = subprocess.run([POWERSHELL, "-NoProfile", "-Command", probe], capture_output=True, text=True, timeout=60)
    assert preview.returncode == 0, preview.stderr
    assert "PREVIEW ONLY" in preview.stdout
    assert before.stdout.strip() == after.stdout.strip()
