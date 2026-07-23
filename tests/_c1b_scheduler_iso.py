"""C1B isolated Scheduler-page verifier (subprocess).

Run ONLY as a subprocess of the operator unit tests with PYTHONPATH UNSET.
It exists so the dashboard pages can be raw-imported and their default wiring
asserted WITHOUT contaminating the Streamlit form-context stack of the parent
pytest process (which also runs AppTest browser tests in the same process).
The page's module-top-level ``st.form(...)`` calls in one process poison the
next AppTest run with "Forms cannot be nested in other forms."

Three modes (selected by sys.argv[1]):
  import_check  -> import 7_Scheduler only; assert no real external call on
                    import and that the page exposes OS (not start_manual_scan).
  all_pages     -> import every dashboard page; assert none raise on import.
  fail_closed   -> import 7_Scheduler; assert default wiring is fail-closed
                    (not_connected ports, readiness not-ready, task not
                    registered, scan refused) and no real adapter is reached.

Guards: any real scheduler launch, Windows Task Scheduler resolve/set,
subprocess/PowerShell (to powershell/pwsh/Get-ScheduledTask), Apify, or
Telegram call is replaced with a function that aborts the whole subprocess
(SystemExit) — so reaching a real adapter is impossible to miss.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# --- guard: real scheduler launch must never run from default wiring --------
import rdsa.scheduler as S  # noqa: E402
import dashboard.operator_service as OS  # noqa: E402


def _abort(label):
    def _fn(*a, **k):
        raise SystemExit(f"REAL_EXTERNAL_REACHED:{label}")
    return _fn


# Fail-closed subprocess guard.
#
# The ONLY subprocess command permitted while importing the dashboard pages is
# Streamlit's own Windows import-time platform detection call ``ver`` (emitted
# as ``subprocess.run('ver', shell=True)``; equivalently ``cmd /c ver``). Every
# other subprocess invocation -- Python child processes, arbitrary executables,
# PowerShell, Task Scheduler (schtasks / Get-ScheduledTask), Apify, Telegram,
# or anything else -- is aborted by raising SystemExit so a real
# external/adapter reach is impossible to miss.
#
# This is an ALLOW-LIST, not a denylist: we do NOT rely on matching
# powershell/apify/telegram/task-scheduler keywords alone. Anything not on the
# allow-list is rejected, full stop.
_ALLOWED_SUBPROCESS = ("ver", "cmd /c ver")


def _norm_subprocess_cmd(*a, **k):
    """Normalize a subprocess command to a lower-cased string.

    Handles every call style Streamlit / the page may use:
      - positional list/tuple: subprocess.run(['cmd', '/c', 'ver'])
      - positional string:     subprocess.run('ver', shell=True)
      - kwargs form:           subprocess.run(args=['ver'], ...)
                              subprocess.run(command='ver', shell=True)
    """
    cmd = None
    if a:
        cmd = a[0]
    else:
        cmd = k.get("args") or k.get("command") or k.get("shell_cmd")
    if isinstance(cmd, (list, tuple)):
        parts = [str(x) for x in cmd]
    elif cmd is None:
        parts = []
    else:
        # Single string command; preserve it (may be 'ver' or 'cmd /c ver').
        parts = str(cmd).split()
    return " ".join(parts).strip().lower()


class _AllowedResult:
    """Result for the single allow-listed benign ``ver`` probe.

    Streamlit's import-time platform probe calls ``subprocess.run('ver',
    shell=True)`` and may also call ``subprocess.check_output('ver', ...)``
    (which normally returns a *str*, not a CompletedProcess). We satisfy both
    by returning an object that behaves like a CompletedProcess (has .stdout/
    .stderr/.returncode) AND like a str (so any ``result.strip()`` /
    ``result.lower()`` call works). Every other command aborts via SystemExit.
    """

    _STDOUT = "Microsoft Windows [Version 10.0.19045.0]"

    def __init__(self, args):
        self.args = args
        self.returncode = 0
        self.stdout = self._STDOUT
        self.stderr = ""

    # str-like surface so callers that treat the result as a string work.
    def strip(self, *a, **k):
        return self._STDOUT.strip(*a, **k)

    def lower(self, *a, **k):
        return self._STDOUT.lower(*a, **k)

    def __getattr__(self, name):
        return getattr(self._STDOUT, name)

    def __str__(self):
        return self._STDOUT


def _guarded_subprocess_run(*a, **k):
    norm = _norm_subprocess_cmd(*a, **k)
    if norm in _ALLOWED_SUBPROCESS:
        return _AllowedResult(a)
    raise SystemExit("REAL_EXTERNAL_REACHED:subprocess.run:" + norm[:200])


S.run_scheduled_run = _abort("run_scheduled_run")
OS.resolve_windows_task = staticmethod(_abort("resolve_windows_task"))
OS.set_windows_task_enabled = staticmethod(_abort("set_windows_task_enabled"))

import subprocess as _subprocess  # noqa: E402

# Replace every launch path with the same fail-closed guard.
_subprocess.run = _guarded_subprocess_run
_subprocess.check_output = _guarded_subprocess_run
_subprocess.check_call = _guarded_subprocess_run
_subprocess.call = _guarded_subprocess_run


class _GuardedPopen:
    """Popen is also blocked: any real launch via Popen aborts the child."""

    def __init__(self, *a, **k):
        norm = _norm_subprocess_cmd(*a, **k)
        if norm in _ALLOWED_SUBPROCESS:
            real = getattr(_subprocess, "_real_Popen", None)
            if real is None:
                import subprocess as _sp_real
                real = _sp_real.Popen
            real.__init__(self, *a, **k)
        else:
            raise SystemExit("REAL_EXTERNAL_REACHED:Popen:" + norm[:200])


_subprocess.Popen = _GuardedPopen

ALL_PAGES = (
    "dashboard.pages.1_Overview",
    "dashboard.pages.2_Lead_Inbox",
    "dashboard.pages.3_Lead_Detail",
    "dashboard.pages.4_Inventory",
    "dashboard.pages.5_Matching_Review",
    "dashboard.pages.6_Pilot_Analytics",
    "dashboard.pages.7_Scheduler",
)


def _mode_import_check(result):
    mod = importlib.import_module("dashboard.pages.7_Scheduler")
    # The page must NOT define the operator action directly on its module.
    if hasattr(mod, "start_manual_scan"):
        result["ok"] = False
        result["errors"].append("page defines start_manual_scan directly")
    if not hasattr(mod, "OS"):
        result["ok"] = False
        result["errors"].append("page missing OS handle")
    # Importing the page must not have reached a real adapter.
    result["import_clean"] = True


def _mode_all_pages(result):
    for name in ALL_PAGES:
        importlib.import_module(name)
    result["all_pages_imported"] = True


def _mode_fail_closed(result):
    from dashboard.operator_service import OperatorPorts
    mod = importlib.import_module("dashboard.pages.7_Scheduler")
    ports = mod._ports()  # default wiring, no injection
    if not isinstance(ports, OperatorPorts):
        result["ok"] = False
        result["errors"].append("default _ports() not an OperatorPorts")
        return

    readiness = OS.get_manual_run_readiness(ports)
    if readiness.ready is not False:
        result["ok"] = False
        result["errors"].append("default readiness unexpectedly ready")
    if "operator_controls_not_connected" not in readiness.reasons:
        result["ok"] = False
        result["errors"].append(
            "default readiness missing operator_controls_not_connected")

    tcs = OS.get_task_control_state(ports)
    if tcs.exists is not False:
        result["ok"] = False
        result["errors"].append("default task control reports registered")
    if tcs.valid is not False:
        result["ok"] = False
        result["errors"].append("default task control reports valid")

    res = OS.start_manual_scan(confirm=True, ports=ports)
    if res.accepted is not False or res.status != "refused":
        result["ok"] = False
        result["errors"].append(
            f"default scan not refused: accepted={res.accepted} "
            f"status={res.status}")
    result["real_manual_calls"] = 0
    result["real_task_calls"] = 0
    result["ports_fail_closed"] = (
        readiness.ready is False
        and "operator_controls_not_connected" in readiness.reasons
        and tcs.exists is False
        and res.accepted is False
        and res.status == "refused"
    )


def _mode_guard_check(result):
    """Prove the subprocess allow-list is fail-closed.

    Runs from inside this already-guarded child, so every non-allow-listed
    command must raise SystemExit (caught by main -> external_reached=True),
    while the single blessed ``cmd /c ver`` passes. We detect rejection by
    the guard raising SystemExit with the REAL_EXTERNAL_REACHED marker; the
    allowed command must NOT raise that.
    """
    import subprocess as _sp
    rejected = []
    allowed_passed = False

    # The exact benign command proven necessary for Streamlit import
    # (Streamlit emits subprocess.run('ver', shell=True); allow-list also
    # accepts the canonical cmd /c ver form).
    try:
        _sp.run(["cmd", "/c", "ver"], capture_output=True, text=True)
        allowed_passed = True
    except SystemExit as se:
        if str(se).startswith("REAL_EXTERNAL_REACHED:"):
            rejected.append("cmd /c ver: " + str(se))

    # Arbitrary Python child command -> rejected.
    try:
        _sp.run([sys.executable, "-c", "print('x')"], capture_output=True)
        rejected.append("python child not rejected")
    except SystemExit as se:
        if not str(se).startswith("REAL_EXTERNAL_REACHED:"):
            rejected.append("python child raised non-guard exit")

    # Arbitrary executable -> rejected.
    try:
        _sp.run(["some_random_executable", "--version"], capture_output=True)
        rejected.append("arbitrary executable not rejected")
    except SystemExit as se:
        if not str(se).startswith("REAL_EXTERNAL_REACHED:"):
            rejected.append("arbitrary executable raised non-guard exit")

    # PowerShell -> rejected.
    try:
        _sp.run(["powershell", "-NoProfile", "-Command", "Get-Process"],
                 capture_output=True)
        rejected.append("powershell not rejected")
    except SystemExit as se:
        if not str(se).startswith("REAL_EXTERNAL_REACHED:"):
            rejected.append("powershell raised non-guard exit")

    # Windows Task Scheduler (schtasks) -> rejected.
    try:
        _sp.run(["schtasks", "/Query", "/TN", "RentalDemandSignalAgent-Daily"],
                 capture_output=True)
        rejected.append("schtasks not rejected")
    except SystemExit as se:
        if not str(se).startswith("REAL_EXTERNAL_REACHED:"):
            rejected.append("schtasks raised non-guard exit")

    if not allowed_passed:
        result["ok"] = False
        result["errors"].append("allowed cmd /c ver was rejected")
    if rejected:
        result["ok"] = False
        result["errors"].extend(["guard: " + r for r in rejected])
    result["guard_allowed_passed"] = allowed_passed
    result["guard_rejected_count"] = 4  # python/exec/powershell/schtasks
    result["guard_clean"] = allowed_passed and not rejected


def _mode_fail_closed(result):
    from dashboard.operator_service import OperatorPorts
    mod = importlib.import_module("dashboard.pages.7_Scheduler")
    ports = mod._ports()  # default wiring, no injection
    if not isinstance(ports, OperatorPorts):
        result["ok"] = False
        result["errors"].append("default _ports() not an OperatorPorts")
        return

    readiness = OS.get_manual_run_readiness(ports)
    if readiness.ready is not False:
        result["ok"] = False
        result["errors"].append("default readiness unexpectedly ready")
    if "operator_controls_not_connected" not in readiness.reasons:
        result["ok"] = False
        result["errors"].append(
            "default readiness missing operator_controls_not_connected")

    tcs = OS.get_task_control_state(ports)
    if tcs.exists is not False:
        result["ok"] = False
        result["errors"].append("default task control reports registered")
    if tcs.valid is not False:
        result["ok"] = False
        result["errors"].append("default task control reports valid")

    res = OS.start_manual_scan(confirm=True, ports=ports)
    if res.accepted is not False or res.status != "refused":
        result["ok"] = False
        result["errors"].append(
            f"default scan not refused: accepted={res.accepted} "
            f"status={res.status}")
    result["real_manual_calls"] = 0
    result["real_task_calls"] = 0
    result["ports_fail_closed"] = (
        readiness.ready is False
        and "operator_controls_not_connected" in readiness.reasons
        and tcs.exists is False
        and res.accepted is False
        and res.status == "refused"
    )


_MODES = {
    "import_check": _mode_import_check,
    "all_pages": _mode_all_pages,
    "fail_closed": _mode_fail_closed,
    "guard_check": _mode_guard_check,
}


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "fail_closed"
    result = {
        "ok": True,
        "mode": mode,
        "external_reached": False,
        "errors": [],
        "ports_fail_closed": False,
        "real_manual_calls": 0,
        "real_task_calls": 0,
    }
    try:
        _MODES[mode](result)
    except SystemExit as se:
        msg = str(se)
        result["ok"] = False
        if msg.startswith("REAL_EXTERNAL_REACHED:"):
            result["external_reached"] = True
            result["errors"].append(msg)
        else:
            result["errors"].append("system_exit:" + msg)
    except Exception as exc:  # noqa: BLE001
        result["ok"] = False
        result["errors"].append(f"{type(exc).__name__}: {exc}")

    print("C1B_ISO_RESULT " + json.dumps(result))
    return 0 if result["ok"] and not result["external_reached"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
