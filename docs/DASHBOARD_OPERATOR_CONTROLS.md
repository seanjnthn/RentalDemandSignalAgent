# Dashboard Operator Controls — Design & Action Flow

**Milestone:** `feature/v080-dashboard-operator-controls` (scan-only)
**Branch base:** `feature/v080-professional-dashboard-redesign` @ `896a9b2`

This milestone adds **safe, read-mostly operator controls** to the Scheduler
dashboard page. It is strictly **scan-only**:

- ✅ Manual lead search now (scan only)
- ✅ Enable / disable the existing recurring scan schedule
- ❌ No scheduled Telegram delivery toggle
- ❌ No Telegram-send toggle
- ❌ No creation, reinstall, repair, or edit of the Windows task
- ❌ No change to trigger, command, arguments, working directory, or cadence

No Apify call, no Telegram call, and no Windows Scheduled Task mutation
happens during implementation or tests.

---

## 1. Architecture

```
Streamlit Scheduler page (dashboard/pages/7_Scheduler.py)
        │  (native st.form, explicit submit only)
        ▼
dashboard/operator_service.py   ← thin, testable abstraction
        │  dependency-injected ports (defaults = real rdsa modules)
        ├── ManualScanPort     → reuses rdsa.scheduler.run_scheduled_run
        ├── TaskControlPort     → validates + toggles the approved Windows task
        ├── SchedulerStatePort → reads lock / ledger / cost / task state
        └── AuditPort          → appends sanitized operator actions to operator_audit
```

- **No subprocess / PowerShell / Windows API is called directly by the page.**
  The page calls only `operator_service`. The *default* `TaskControlPort`
  resolves the scheduled task through an injected function; tests inject a
  fake that returns an in-memory task model, so no real Task Scheduler
  call is ever made.
- The dashboard page never imports `subprocess`, `os.system`, or any
  `.ps1` script.

### Why reuse the existing pipeline

`rdsa.scheduler.run_scheduled_run(args)` already implements every
fail-closed gate the milestone requires (lock, cost, inventory, interruption
recovery, single batched Apify request, no paid retry, Telegram off). We
reuse it verbatim with `trigger_type="dashboard_manual"` and
`confirm_scheduled_run=True`, invoked **in-process only after an explicit
operator confirmation**. We do **not** create a second scanning implementation.

---

## 2. Exact manual-run command path reused

The dashboard invokes the **same orchestrator** the Windows task uses:

```
rdsa.scheduler.run_scheduled_run(args)
    args.trigger_type      = "dashboard_manual"
    args.confirm_scheduled_run = True
```

`run_scheduled_run` internally:
- acquires `SchedulerLock` (single in-flight run),
- validates real inventory,
- evaluates the cost guard (`projected > stop` ⇒ refused),
- enables `APIFY_LIVE_ENABLED` **in-process only** after preflight,
- issues **exactly one** batched Apify Actor request (`search_batched`),
- **never** sets `RDSA_TELEGRAM_SEND_ENABLED` (scan-only),
- restores all flags in `finally`, releases the lock.

The manual control therefore inherits every gate and leaves the ledger
traceable: each accepted run is recorded in `scheduled_runs` with its
`run_id`, exactly like a scheduled run.

---

## 3. Readiness gate (manual search button disabled when)

`get_manual_run_readiness()` returns a structured verdict. The button is
disabled (and the reason surfaced) when **any** of:

1. Another scheduler process is alive (`_pid_alive` on lock pid).
2. An active lock exists (`SchedulerLock.status().locked`).
3. An unresolved non-terminal run exists (`detect_interrupted_runs`).
4. Usage or projected cost reaches the stop gate
   (`evaluate_cost(...).blocked`).
5. Configuration / credentials unavailable (inventory invalid, or
   `rd.REPO_ROOT` / runtime dir not resolvable).
6. A manual launch has already been accepted **in the current interaction**
   (process-local `live_opt_in` flag, see §5).
7. Repository readiness fails (`get_scheduler_status` errors or the DB is
   unavailable).

Readiness is recomputed on every render from live state; the button is a
native `st.form_submit_button` that is `.disabled=not ready`.

---

## 4. Recurring scan control — exact task validation rules

`TaskControlPort` returns a model of the registered task. We **verify**, then
allow only Enable / Disable (state flip of the existing task):

| Field | Approved value | Rule |
|---|---|---|
| task name | `RentalDemandSignalAgent-Daily` | must match **exactly** |
| action execute | absolute `powershell.exe` | must be absolute, ends `powershell.exe` |
| action script | `scripts\windows_scheduler_run.ps1` | must match approved launcher |
| arguments | `-NoProfile -ExecutionPolicy Bypass -File "<run.ps1>" -RepoRoot "<REPO>" -TriggerMode <daily_schedule\|scheduled_canary> -ConfirmRun` | no `-EnableScheduledSend`, no embedded tokens |
| working directory | repository root (`REPO_ROOT`) | must equal resolved repo root |
| trigger mode | `daily_schedule` or `scheduled_canary` | CLI trigger value only |
| scheduled-send opt-in | **absent** | refuse if `-EnableScheduledSend` present |

- If the task is **missing** → controls blocked, message: *task not registered*.
- If the task **definition differs** from approved → controls blocked
  (red), message: *task definition mismatch — operator must reconcile
  out-of-band*.
- If the task carries a **scheduled-send argument** → blocked.
- **Enable** changes *only* the task `Enabled` state (→ Ready).
- **Disable** changes *only* the task `Enabled` state (→ Disabled).
- Neither action installs, recreates, repairs, or edits the task.
- Disabling must **not** terminate an already-running process.
- The next scheduled scan remains scan-only (no delivery opt-in).

---

## 5. Idempotency mechanism

| Threat | Control |
|---|---|
| Double-click launches twice | `start_manual_scan` is guarded by `SchedulerLock.acquire` — the second call sees the held lock and returns `blocked_lock` without a second Apify request. |
| Streamlit rerun repeats the action | The action is performed **only inside the form's `if submitted and confirmed` branch**, which fires once per explicit submit. Reruns that are not a submit event do nothing. Additionally a process-local `live_opt_in` flag is set the moment a launch is *accepted*; readiness then reports `manual_launch_accepted` so the button stays disabled for the life of the process. |
| Repeated Enable on enabled task | `set_recurring_scan_enabled(True)` when already enabled is a **no-op** (returns `already_enabled`, no task mutation). |
| Repeated Disable on disabled task | `set_recurring_scan_enabled(False)` when already disabled is a **no-op** (`already_disabled`). |
| Failed action | Recorded via `AuditPort` with `status=failed` and a sanitized `error_code`/`sanitized_error`; never fabricates success. |
| Manual run traceability | Each accepted run's `run_id` is returned to the page and shown; the run is already in `scheduled_runs`. |

Process-local `live_opt_in` is a plain in-process boolean (default `False`),
never persisted to `.env` or any file.

---

## 6. Audit mechanism

`AuditPort.append(action, ...)` writes a row to the **`operator_audit`**
table (git-ignored runtime DB, created idempotently). Each accepted
operator action carries an **operation ID** (`op_id`, UUID8). Every row records:

- `op_id` — operation idempotency key
- `action` — `manual_scan_start` | `recurring_enable` | `recurring_disable`
- `timestamp` — UTC ISO
- `actor` — `"dashboard"`
- `previous_state` — JSON-sanitized prior state
- `resulting_state` — JSON-sanitized outcome
- `outcome` — `accepted` | `refused` | `failed` | `noop`
- `sanitized_error` — only on failure (token/path/user-free)
- `run_id` — for manual scans

**Sanitization guarantees:** no token, chat ID, private author, absolute
path, or `.env` value is ever stored. We reuse `rdsa.scheduler.sanitize_error`
and `dashboard_repository.sanitize` for error text, and the page exposes
no secrets (already true for the Scheduler page).

---

## 7. UI safety

- The existing **Scheduler status area stays read-only** (unchanged).
- Write controls live in a visually separate **`Operator controls`** section
  (a titled `st.container` / divider).
- Color discipline:
  - **amber** — actions requiring confirmation.
  - **red** — blocked or failed operations only.
  - **muted gray** — intentionally disabled states.
- **No custom HTML buttons.** Only native `st.form` + `st.form_submit_button`.
- **No hidden automatic execution on page load.** `st.session_state` is
  read but no side effect runs at import or top-level render.
- **No action from a checkbox change alone** — the confirmation checkbox is
  read only inside the explicit form submit.
- Every form requires an explicit **Submit**.

---

## 8. Abstraction & dependency injection

`dashboard/operator_service.py` exposes:

- `get_manual_run_readiness() -> Readiness`
- `start_manual_scan(*, confirm, live_opt_in, lock_ttl=None) -> ScanResult`
- `get_task_control_state() -> TaskControlState`
- `set_recurring_scan_enabled(enabled: bool, *, confirm, op_id=None) -> TaskResult`

Dependencies are injected through an `OperatorPorts` dataclass with defaults
pointing at the real `rdsa` implementation:

- `manual_port` → `run_scheduled_run`
- `state_port` → `get_scheduler_status` + `SchedulerLock` + cost helpers
- `task_port` → real Task Scheduler resolver (injected; **tests use fakes**)
- `audit_port` → `operator_audit` writer

Tests inject fakes for `manual_port`, `task_port`, and `audit_port`, so
**no Apify, Telegram, PowerShell, or Task Scheduler is ever touched** in
the offline suite.

---

## 9. Verification

1. Operator-control unit tests (`tests/test_dashboard_operator.py`).
2. Scheduler / dashboard regression suites.
3. Full `pytest` suite.
4. Fresh browser smoke test using **fake** operator-service dependencies
   (injected into the page via a test seam). Proves:
   - no real external call,
   - manual button state follows readiness,
   - confirmation is required,
   - enable/disable state is clear,
   - mismatch states are blocked,
   - no browser warnings/errors,
   - existing Scheduler evidence remains readable.

No real manual scan is executed and no real Windows task is modified in
this phase.
