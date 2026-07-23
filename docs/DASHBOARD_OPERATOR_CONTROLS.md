# Dashboard Operator Controls — Manual Search Only

**Milestone:** `feature/v080-real-operator-adapters`
**Current release scope:** manual dashboard lead search only

This release intentionally narrows C2A to one operator action:

- ✅ **Run lead search manually from the dashboard**
- ❌ Recurring schedule enable/disable controls are deferred
- ❌ The installed Windows Scheduled Task remains **disabled and read-only** in the dashboard
- ❌ Telegram delivery remains unsupported and off for manual dashboard scans

No implementation step, test, or browser smoke in this milestone may call Telegram, mutate `.env`, start/enable/disable/recreate/repair/modify the Windows Scheduled Task, or run a real Apify Actor without an explicit later live-canary approval.

---

## 1. Dashboard architecture

```text
Streamlit Scheduler page (dashboard/pages/7_Scheduler.py)
        │  native st.form, explicit submit only
        ▼
dashboard/operator_service.py
        │  dependency-injected ports; default = fail closed
        ├── ManualScanPort      → feature-flagged async child launcher
        ├── TaskStatusPort      → read-only installed task evidence
        ├── SchedulerStatePort  → existing ledger / lock / cost / interruption evidence
        └── AuditPort           → sanitized persistent operator audit
```

The Streamlit page does not import subprocess, PowerShell, Task Scheduler mutation APIs, Apify clients, Telegram clients, or `.env` writers. It calls only `operator_service` interfaces.

Default wiring remains fail-closed. Without `RDSA_DASHBOARD_OPERATOR_CONTROLS_ENABLED=true` and readiness validation, the page resolves `not_connected_ports()` and cannot launch a real scan.

---

## 2. Exact manual execution path

A confirmed dashboard submission launches the project-local Python asynchronously:

```text
python -m rdsa.cli dashboard-manual-scan \
  --operation-id <OPERATION_ID> \
  --confirm-run
```

The child CLI then invokes the existing scheduler pipeline with:

```text
trigger_type = dashboard_manual
confirm_scheduled_run = True
```

The manual adapter does **not** create a second scan implementation. It reuses `rdsa.scheduler.run_scheduled_run`, including the existing scheduler ledger, lock, unresolved/interrupted-run gate, monthly cost warning/stop gates, real-inventory validation, single batched Apify request path, and no automatic paid retry behavior.

---

## 3. Manual scan safety posture

Manual dashboard scan is scan-only:

- Telegram delivery: **Off**
- scheduled Telegram sending: **Off**
- no `.env` mutation
- no Streamlit-process global `os.environ` mutation
- Apify live opt-in is process-local to the child execution path only
- maximum one Apify Actor request intent through the existing scheduler provider call
- no automatic paid retry after failed or unknown child outcomes
- child stdout/stderr is bounded and sanitized before any UI/audit surface

The dashboard returns an operation ID immediately after accepted launch and polls status read-only through audit/ledger evidence. It never blocks the Streamlit request thread indefinitely and never exposes command lines, environment values, tokens, chat IDs, local paths, or provider responses.

---

## 4. Dashboard behavior

The existing Scheduler observability remains read-only and continues to show:

- scheduler history / latest run / last successful run
- process lock evidence
- interruption-recovery evidence
- monthly usage and cost thresholds
- task state evidence where available

A separate **Operator controls** section contains exactly one form: **Run lead search**.

The form displays:

- Mode: Scan only
- Telegram delivery: Off
- Monthly Apify usage
- Projected maximum cost
- Warn threshold
- Stop threshold
- Lock state
- Unresolved-run state
- Credentials/configuration readiness
- Installed task Enabled/Disabled state as read-only evidence

The action requires both:

1. explicit confirmation checkbox, and
2. explicit **Run search now** submit.

No action occurs on page load, checkbox change, Streamlit rerun, duplicate operation ID, or double-click.

The action is disabled or blocked when the feature flag is false, credentials/configuration are unavailable, an active scheduler process or lock exists, an unresolved non-terminal run exists, the cost stop gate would be exceeded, repository readiness fails, another manual operation is launching/running, or the operation ID has already been accepted.

---

## 5. Feature flag

Default remains:

```text
RDSA_DASHBOARD_OPERATOR_CONTROLS_ENABLED=false
```

Rules:

- `false` → the dashboard remains fail-closed and the button is safely unavailable.
- `true` → the real manual adapter may become available only after readiness validation.
- The flag does **not** enable Apify by itself.
- The flag does **not** enable Telegram.
- The flag does **not** enable the scheduler service.
- The flag does **not** enable scheduled sending.
- The flag does **not** enable any Windows Scheduled Task mutation.
- Implementation and tests must not write this flag to `.env`.

---

## 6. Persistent idempotency and audit

Each submission has a persistent operation ID. Sanitized audit evidence records:

- operation ID
- action: `dashboard_manual_scan` / `dashboard_manual_cli`
- state: `accepted`, `blocked/refused`, `failed`, `running`, `completed`, or `interrupted`
- timestamp
- scheduler run ID when available
- sanitized message/error code

Guarantees:

- one accepted operation launches at most once
- Streamlit rerun does not relaunch
- duplicate operation ID returns existing status
- unknown child outcome does not trigger an automatic retry
- audit and UI contain no secrets, command lines, full paths, provider payloads, token values, or chat IDs

---

## 7. Installed Windows Scheduled Task is read-only

The dashboard may display the installed task evidence:

- task name
- Enabled/Disabled state
- cadence when available
- next run when available
- task-definition mismatch evidence when available

This release exposes **no** recurring enable/disable form and no task mutation adapter. The installed task must remain unchanged and disabled unless an operator performs an out-of-band approved procedure in a future milestone.

Deferred recurring scope:

- enabling the installed task
- disabling the installed task
- starting the task
- recreating/repairing/editing the task
- scheduled Telegram sending controls

---

## 8. One-time live canary procedure (future approval required)

Do not perform this during implementation. When explicitly approved later:

1. Confirm the working tree and `.env` safety defaults are unchanged.
2. Confirm required credentials are present by boolean only; never print values.
3. Run Streamlit with `RDSA_DASHBOARD_OPERATOR_CONTROLS_ENABLED=true` process-locally only.
4. Submit exactly one confirmed manual operation ID.
5. Verify one asynchronous child launch and one scheduler ledger row.
6. Confirm Apify request count/cost, Telegram sends = 0, scheduled send = off.
7. Confirm the installed Windows task stayed unchanged and disabled.
8. Restore/close the process-local flag and report results.
9. Stop for approval; do not merge, tag, push, enable scheduling, or call Telegram.

---

## 10. Canary Results (2026-07-22)

**Operation ID:** `cea91d85`<br>
**Run ID:** `sch-20260722T095641Z-3cd6d106`<br>
**Status:** `completed`<br>
**New leads:** 5 (127 → 132)<br>
**Classifications:** qualified_lead ×3, watch ×1, agent_broker ×1<br>
**Telegram:** 0 calls (send flag remained `false`)<br>
**Actual cost:** $0.045 (Apify `usageTotalUsd`)<br>
**Monthly usage:** $1.230 → $1.275

### Inventory Readiness Bug Fix

**Issue:** `_inventory_available()` in `dashboard/operator_service.py` line 250 was checking
`report.get("rows")` instead of `report.get("accepted_rows")`. This caused the readiness gate to
return `False` even when valid inventory was present.

**Fix:** Changed to `report.get("accepted_rows")`. Verified by the canary (successful scan after fix).

**Regression tests:** Added `tests/test_inventory_readiness.py` (7 tests covering all inventory gate
scenarios: valid accepted_rows, empty, missing, false ok flag, mixed valid/invalid, all synthetic,
malformed report).

### Cost Provenance

The `usage_total_usd` field in `scheduled_runs` stores `config.SCHEDULER_MAX_CHARGE_USD` ($0.10) —
the **configured maximum charge cap**, not the actual Apify cost. The actual cost ($0.045) is tracked
in `data/apify_usage.json` via `MonthlyUsageGuard.record_run()`:

- `actual_usd`: incremented by Apify-reported `usageTotalUsd` (real cost)
- `estimated_usd`: incremented by `SCHEDULER_MAX_CHARGE_USD` (configured cap)

The dashboard displays `max_charge_usd` from config, not `actual_usd`. This is a documentation
issue, not a code bug — the label could be clarified to "Max charge cap" vs "Actual cost".

### Pre-Canary Attempts (Audit Only)

Two attempts failed before reaching Apify:

- `sch-20260722T095147Z-5cb8f4aa`: `failed` / `apify_error` / `APIFY_API_TOKEN is required...`
- `sch-20260722T095322Z-b3509a51`: `failed` / `apify_error` / `APIFY_API_TOKEN is required...`

These rows were logged to `scheduled_runs` as an audit trail, but no Apify call occurred. The token
check happens in `ApifyThreadsProvider.__init__()` before the API call. The rows serve as evidence
that the operator attempted to run but was blocked by missing credentials.

### Security Verification

- Token absent from git diff ✅
- Token absent from tracked files ✅
- Token absent from audit output ✅
- Token absent from runtime logs ✅
- Token absent from UI output ✅
- Shell history: Token may be present (user provided via paste) — **rotation recommended**

### Operator Approval

Manual dashboard scan is **approved for normal operator use** with:

1. Inventory readiness bug fix applied ✅
2. Regression test coverage added ✅
3. Cost provenance documented ✅

---

## 9. Rollback procedure

1. Stop the Streamlit process.
2. Unset the process-local dashboard feature flag.
3. Leave `.env` untouched.
4. Do not change the Windows Scheduled Task from the dashboard.
5. Verify no scheduler lock remains.
6. Review `operator_audit` for the last sanitized operation state.
7. If a future out-of-band procedure changed the Windows task, rollback must also be out-of-band and explicitly approved; this release contains no dashboard task mutation control.

Scheduled Telegram delivery remains unsupported and off.
