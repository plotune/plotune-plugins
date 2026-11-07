# MCP Adversarial Test Protocol

Re-test checklist and methodology for hardening the Plotune Nexus MCP tool surface.
Run this after each fix PR to verify regressions are absent and each bug is closed.

All tests use MCP tools only - no direct SSH and no direct device filesystem access.
Prefer existing fixture artifacts. If a test requires uploading a fixture, use the
two-phase MCP artifact import flow only after operator approval for the signed PUT
URL upload step.
Each test section has a PASS/FAIL criterion stated as a single observable fact.

---

## Environment Setup

Before starting any wave, run:

```
get_device_status_tool
get_runtime_capabilities_tool
list_can_interfaces_tool
list_uart_devices
```

Confirm the device is reachable and note the baseline set of CAN interfaces, jobs,
UART devices, and artifacts. Runtime MCP schemas are authoritative; if an example
below is rejected as an unexpected argument, update this protocol before
continuing the test.

Use only test-created virtual CAN interfaces unless an operator has explicitly
assigned an isolated bench target. Linux interface names are limited, so keep
throwaway names short and unique, for example `vcanadv1a`.

```
create_virtual_can name=<wave-specific-name> bring_up=true
get_can_interface_status_tool interface_name=<wave-specific-name>
```

Only continue if the status confirms the interface is virtual/test-created. Never
run this protocol against production `can*`, `slcan*`, DoIP, UART, or XCP targets.

Cleanup every wave explicitly:

- stop and wait for any recording job before deleting its interface;
- stop periodic transmit, gateway, container, UART, or XCP jobs created by the test;
- release CAN leases with `release_can_interface interface_name=<name> session_id=<session-id>`;
- close UART sessions created by the test;
- delete only virtual CAN interfaces created by the test and absent from the baseline;
- never call artifact deletion or `run_artifact_cleanup dry_run=false` without operator confirmation.

Prohibited live-target actions for this protocol: UDS routines, XCP writes/STIM,
XCP unlock, gateway forwarding on real buses, SLCAN attach/detach on unknown
serial adapters, and containers with bus/network/serial access outside an
operator-confirmed isolated bench.

---

## Wave 1 — Ghost Resource Errors

Goal: confirm error payloads for nonexistent resources do NOT embed lists of live items.

### W1-T1 — Ghost job ID

```
get_job_status_tool job_id=00000000000000000000000000000000
```

**PASS:** Response contains `error_code` and `available_job_count: N`. No `jobs` array embedded.
**FAIL:** Response body contains a list of real job IDs or job records.

### W1-T2 — Ghost artifact ID

```
get_artifact_metadata_tool artifact_id=00000000000000000000000000000000
```

**PASS:** Response contains `error_code` and `available_artifact_count: N`. No artifact list embedded.
**FAIL:** Response body contains a list of real artifact entries.

### W1-T3 — Ghost artifact read

```
read_artifact artifact_id=00000000000000000000000000000000
```

If text decoding is needed, use `encoding=text`; `read_artifact` has no `mode` argument.

**PASS:** Same as W1-T2 - no embedded list.
**FAIL:** A list of artifact IDs or records appears in the error body.

### W1-T4 — Ghost wait_for_job

```
wait_for_job job_id=00000000000000000000000000000000
```

**PASS:** Returns `managed_job_not_found` with `available_job_count` only.
**FAIL:** Embeds live job records.

---

## Wave 2 — Format Confusion / Silent Failures

Goal: tools that validate input format must reject wrong formats explicitly, not silently.

### W2-T1 — inspect_a2l with DBC file

Prerequisites: have at least one `.dbc` artifact on the device.

```
list_artifacts_tool
# identify an artifact with a .dbc filename
get_artifact_metadata_tool artifact_id=<dbc-artifact-id>
# use the metadata path, stripping a leading /host if present
inspect_a2l a2l_file_path=<device-local-dbc-path>
```

**PASS:** Returns an error with `error_code` containing a message like "not an A2L file" or "format not recognized".
**FAIL:** Returns `{"measurements":{"total":0},"calibrations":{"total":0}}` with no error.

### W2-T2 — inspect_a2l with plain text

Identify an existing non-A2L artifact, or upload a harmless text fixture through
the approved artifact import flow:

```
get_artifact_metadata_tool artifact_id=<non-a2l-artifact-id>
inspect_a2l a2l_file_path=<device-local-non-a2l-path>
```

**PASS:** Same as W2-T1 — explicit error, not empty result.
**FAIL:** Empty result with no error.

### W2-T3 — Artifact read on failed and cancelled-job artifacts

Prefer pre-existing fixture artifacts that cover both cases:

- a failed artifact whose `is_readable` field is `false`;
- a cancelled artifact with non-zero bytes whose `is_readable` field is `true` and `is_partial` is `true`.

```
list_artifacts_tool only_complete=false
list_artifacts_tool only_complete=false job_type=record_can
```

If no failed/cancelled artifact exists, skip this case or create one only in an
operator-approved isolated test setup. Do not try to force a failed recording by
deleting an active interface; delete should be guarded by Wave 3.

Then:

```
read_artifact artifact_id=<artifact-id-from-job>
```

**PASS:** Failed artifacts return `error_code: "artifact_not_readable"` (or equivalent distinguishable code) with a reason explaining the job failed. Cancelled artifacts that have bytes and are marked readable return bounded content and remain identifiable as partial/cancelled metadata.
**FAIL:** Returns the same `not_found` error as for a truly missing artifact.

Also check `list_artifacts_tool`:

**PASS:** Failed artifacts are either absent from default listing or marked with `is_readable: false`; cancelled partial artifacts are marked with `source_job_status: "cancelled"` and `is_partial: true`.
**FAIL:** Failed artifacts are listed with no indication they cannot be read, or cancelled partial artifacts look indistinguishable from completed recordings.

### W2-T4 — start_container with wrong artifact type

```
list_artifacts_tool
# find a recording artifact (ASC or MF4)
start_container artifact_id=<recording-artifact-id> name=test-wrong-type
```

**PASS:** Returns an error that clearly states the artifact is a recording file, not a container image.
**FAIL:** Returns `container_artifact_root_invalid` without any explanation of the type mismatch.

---

## Wave 3 — Race Conditions / Lifecycle Safety

Goal: deleted or missing CAN interfaces must not allow new recordings to be accepted.
Delete must be blocked when live recording jobs are attached.

### W3-T1 — Delete CAN interface while recording job is active

```
create_virtual_can name=vcanadv3a
record_can channel=vcanadv3a interface=socketcan duration_seconds=60
# do NOT wait - immediately:
delete_can_interface interface_name=vcanadv3a
```

**PASS:** `delete_can_interface` returns an error with `error_code` like `interface_has_active_jobs`. Interface is NOT deleted. Recording job continues running.
**FAIL:** Delete succeeds. Recording job later reports "Network is down" or Errno 100.

Cleanup: `stop_record_can job_id=<job-id>`, `wait_for_job job_id=<job-id>`, then
`delete_can_interface interface_name=vcanadv3a`.

### W3-T2 — record_can on a deleted interface

```
create_virtual_can name=vcanadv3b
delete_can_interface interface_name=vcanadv3b
record_can channel=vcanadv3b interface=socketcan duration_seconds=5
```

**PASS:** Returns a synchronous error like `can_interface_not_found`, `interface_not_found`, or `channel_unavailable`; no job is created for that channel.
**FAIL:** Returns `status: "running"` followed by the job transitioning to `failed` asynchronously.

### W3-T3 — cross-type wait (wait_for_job on a test_sequence)

```
list_jobs_tool
# find any test_sequence job
wait_for_job job_id=<test-sequence-job-id>
```

**PASS:** Returns `error_code: "job_type_mismatch"` or equivalent, with `actual_job_type: "test_sequence"` and a message clearly stating to use `wait_for_test_sequence` instead.
**FAIL:** Returns `managed_job_not_found` — misleading because the job exists.

### W3-T4 — cancel_job on already-terminal job

```
list_jobs_tool
# find any job with status=completed or status=failed
cancel_job_tool job_id=<terminal-job-id>
```

**PASS:** Response includes `already_terminal: true` (or equivalent field) so the caller knows no action was taken.
**FAIL:** Response returns success with job record but no indication the job was already finished.

### W3-T5 — Delete CAN interface while a lease is active

```
create_virtual_can name=vcanadv3c
acquire_can_interface interface_name=vcanadv3c agent_id=agent-A session_id=session-A-001 purpose="delete guard test"
delete_can_interface interface_name=vcanadv3c
```

**PASS:** `delete_can_interface` rejects before deletion and reports redacted active lease metadata without exposing the owner session ID.
**FAIL:** Delete succeeds while a lease is active.

Cleanup:

```
release_can_interface interface_name=vcanadv3c session_id=session-A-001
delete_can_interface interface_name=vcanadv3c
```

---

## Wave 4 — Lease System Enforcement

Goal: `acquire_can_interface` must prevent concurrent leases on the same interface.
Tools operating on a leased interface without holding the lease should be blocked before side effects.

### W4-T1 — Double-grant on same interface

```
create_virtual_can name=vcanadv4a
acquire_can_interface interface_name=vcanadv4a agent_id=agent-A session_id=session-A-001 purpose="adversarial lease test"
acquire_can_interface interface_name=vcanadv4a agent_id=agent-B session_id=session-B-001 purpose="adversarial lease test"
```

**PASS:** Second `acquire_can_interface` returns `error_code: "interface_lease_conflict"` or equivalent with the existing lease details.
**FAIL:** Both calls succeed; `list_can_interfaces_tool` shows two leases on the same interface.

### W4-T2 — record_can on leased interface without holding lease

```
# Continuing from W4-T1, session-A-001 holds the lease
record_can channel=vcanadv4a interface=socketcan duration_seconds=5
# call without presenting the lease token
```

**PASS:** Rejects before job creation with a lease-conflict error unless the caller passes `lease_session_id=session-A-001`.
**FAIL:** Recording starts and returns `status: "running"`, even if it also includes `lease_conflict: true`.

### W4-T3 — send_can_frame on leased interface without holding lease

```
send_can_frame channel=vcanadv4a interface=socketcan arbitration_id="0x123" data_hex=DEADBEEF
```

**PASS:** Rejects before transmit with a lease-conflict error unless the caller passes `lease_session_id=session-A-001`.
**FAIL:** The response includes `sent: true`, even if it also includes `lease_conflict: true`; the frame already left the tool boundary.

Cleanup:

```
stop_record_can job_id=<record-job-id-if-created>
wait_for_job job_id=<record-job-id-if-created>
release_can_interface interface_name=vcanadv4a session_id=session-A-001
delete_can_interface interface_name=vcanadv4a
```

---

## Wave 5 — UART Device Honesty

Goal: `list_uart_devices` must not report builtin tty ports as writable/available when they cannot be opened.

### W5-T1 — list then open builtin UART

```
list_uart_devices
```

Identify a `device_kind: "builtin_uart"` entry (e.g., `/dev/ttyS0`).

Inventory-only expected behavior:

**PASS:** builtin ports that are not hardware-backed are marked `is_readable: false`, `is_writable: false`, and `usage_status: "unavailable"`.
**FAIL:** builtin ports are advertised as writable/available when the runtime cannot open them.

Only continue to `open_uart_session` when an operator has assigned an isolated,
non-production UART and the listed entry is writable:

```
open_uart_session device_path=<operator-confirmed-device-path> baud_rate=115200
```

**PASS:** `open_uart_session` succeeds only on the assigned writable device, or fails without embedding unavailable builtin ports as recommended alternatives.
**FAIL:** an unavailable builtin port is suggested back to the agent in an `available_uart_devices` list.

---

## Wave 6 — XCP Master Ownership

Goal: `flash_artifact` with `protocol: "xcp"` must not open a second XCP master
on a target already owned by a running `record_xcp` job. Channel names are scoped
by python-can backend, so matching must include `interface`.

Run as a unit/regression test by default. Only run live on an operator-confirmed
XCP simulation bench with disposable memory.

### W6-T1 — XCP flash while record_xcp owns same target

Precondition: a running `record_xcp` job owns the same `channel`, `interface`,
A2L path, request CAN ID, and response CAN ID as the flash target.

```
run_test_sequence definition=<xcp-flash-artifact-step-for-same-target>
```

**PASS:** The flash step rejects before creating a pyxcp Master and names the active `record_xcp` job.
**FAIL:** Flash opens a second XCP master or begins download/programming while the recording is running.

### W6-T2 — Same channel name on a different backend

Precondition: a running `record_xcp` job uses the same channel name and CAN IDs
through a different python-can backend, for example `interface="virtual"` while
the flash target uses `interface="socketcan"`.

**PASS:** The flash ownership check does not block solely on channel name; it treats the different backend as a different bus.
**FAIL:** The flash step rejects because it ignored `interface`.

### W6-T3 — Same XCP transport target with different A2L path

Precondition: a running `record_xcp` job uses the same `channel`, `interface`,
request CAN ID, and response CAN ID, but the flash step points at a different
A2L path that resolves the same CAN IDs.

**PASS:** The flash step still rejects before creating a pyxcp Master. XCP master ownership is transport identity, not exact A2L path identity.
**FAIL:** Flash starts because the active recorder used a different A2L file path.

### W6-T4 — XCP STIM or seed request while record_xcp owns same target

Precondition: a running `record_xcp` job owns the same CAN XCP target as a
standalone `stim_xcp_signals` or `xcp_get_seed` request.

```
stim_xcp_signals a2l_file_path=<a2l> channel=<same-channel> interface=<same-interface> stimulations=<...> duration_seconds=1
xcp_get_seed resource=cal a2l_file_path=<a2l> channel=<same-channel> interface=<same-interface>
```

**PASS:** Both calls reject before opening another XCP master and name the active `record_xcp` job.
**FAIL:** Either call starts a standalone XCP session while the recording is running.

---

## Review Disposition

Latest live run: 2026-06-07 against deployed `main`.

| Area | Disposition | Review comment |
|------|-------------|----------------|
| W4-T3 transmit while leased | Real issue; hardened in current branch | Misaligned with the Nexus safety model. The live tool reported `lease_conflict: true` but also `sent: true`; current branch changes this to reject before frame send unless the caller owns the lease. |
| W4-T2 record while leased | Real hardening gap; hardened in current branch | Warning-only behavior is machine-readable but easy for lower-capability agents to ignore; current branch changes this to reject before job creation unless the caller owns the lease. |
| W2-T1/W2-T2 format confusion | Real validation/test gap, plus protocol drift | Wrong suffixes are rejected, but malformed content inside a `.a2l` path still needs an explicit invalid-A2L regression. Protocol must use `a2l_file_path`, not `artifact_id`. |
| W1 ghost-resource responses | Mostly fixed; keep as regression | Live errors return counts only and do not embed live records. Add/keep tests for `read_artifact` and sentinel ID absence. |
| W2-T3 failed/cancelled artifacts | Implemented behavior; keep MCP regression | Failed artifacts return `artifact_not_readable`; cancelled non-empty artifacts can be readable partials and must carry `source_job_status: "cancelled"` plus partial metadata. |
| W3 lifecycle cases | Mostly fixed; missing MCP regressions | Delete-active and missing-interface behavior passed live. Cross-type wait is clear, though `job_type_mismatch` would be a better machine-readable code than generic `usage_error`. |
| W3-T5 delete while leased | Real issue; hardened in current branch | Delete previously guarded active recordings but not active CAN leases. Current branch rejects deletion while leases are held. |
| W5 UART honesty | Mostly fixed; missing negative tests | Live inventory marked builtin `/dev/ttyS*` ports unavailable. Keep inventory-first guidance and add no-driver/`port` driver tests. |
| W6 XCP master ownership | Real issue; hardened in current branch | Flash, STIM, and XCP seed requests could open standalone XCP masters while `record_xcp` owned the same transport target. Current branch rejects same channel/interface/CAN IDs, including alternate A2L paths, and does not falsely block the same channel name on a different backend. |

These points are aligned with Plotune Nexus' direction when framed as safety
boundary enforcement, deterministic agent guidance, and explicit error contracts.
They are not just generic improvement requests, except where noted as regression
coverage for behavior that already passes live.

---

## Haiku Failure Mode Catalog

These are observed failure patterns when a lower-capability agent operates on the Nexus MCP surface.
Each entry describes the trigger, the bad behavior, and the hardened-system expected behavior.

| # | Trigger | Haiku bad behavior | Fixed system behavior |
|---|---------|-------------------|----------------------|
| H1 | `not_found` error embeds 20-item list | Agent picks item[0] from embedded list as "the right resource" | Error returns count-only fields such as `available_job_count` or `available_artifact_count`; agent must call list tool |
| H2 | `record_can` returns `status: "running"` on deleted interface | Agent reports "recording started successfully" | Synchronous error before job creation |
| H3 | `inspect_a2l` returns empty result on DBC file | Agent reports "A2L has 0 measurements — nothing to calibrate" | Explicit error identifying wrong file type |
| H4 | `list_uart_devices` shows builtin ttyS ports as available | Agent iterates all 32 ttyS ports trying `open_uart_session` on each | Ports absent from default listing or marked `is_openable: false` |
| H5 | `wait_for_job` returns `not_found` for test_sequence ID | Agent calls `list_jobs_tool`, finds the job, retries `wait_for_job`, loops | `job_type_mismatch` error breaks the loop |
| H6 | `cancel_job_tool` on terminal job returns success silently | Agent believes it cancelled a running job | `already_terminal: true` in response |
| H7 | `delete_can_interface` succeeds with live recording | Agent proceeds; recording failure surfaces 30s later as cryptic SocketCAN errno | Delete blocked with `interface_has_active_jobs` |
| H8 | Double-grant on same CAN interface | Agent starts two parallel workflows on one interface | Second `acquire_can_interface` rejected |
| H9 | Protocol or reference uses stale argument aliases | Agent retries with invented combinations such as `interface=` where `channel=` is required | References show exact runtime argument names and tell agents to stop on schema mismatch |
| H10 | `send_can_frame` returns `sent: true` plus `lease_conflict: true` | Agent treats warning as harmless because the command "worked" | Transmit is rejected before any frame is sent unless caller passes the owning `lease_session_id` |
| H11 | XCP standalone tools ignore active `record_xcp` ownership | Agent starts flash, STIM, or seed/unlock setup because the request schema validates, colliding with an existing XCP master | Standalone XCP tools reject before Master creation when the same channel, backend, and CAN IDs are already owned |
| H12 | `delete_can_interface` ignores active leases | Agent deletes a bus another workflow explicitly reserved | Delete rejects and names redacted active lease metadata |

---

## Post-Fix Regression Check

After the fix PR (`issue-140` branch) is merged and deployed, run the following quick regression pass before the full wave tests:

1. **Device reachable:** `get_device_status_tool` returns `status: "ready"` or the current healthy status used by the deployed server.
2. **Artifact list sane:** `list_artifacts_tool` returns existing metadata plus only expected test-created artifacts.
   - `list_artifacts_tool(job_id=<recording-job-id>)` returns only artifacts for that recording job.
   - `list_artifacts_tool(job_id=<test-sequence-job-id>)` expands to related test-sequence recording artifacts.
   - `list_artifacts_tool(job_type="record_can", format="asc", interface=<test-interface>, limit=3)` returns only matching artifacts and honors the limit.
   - `list_artifacts_tool(since=<future-timestamp>)` returns an empty list.
3. **Existing recording jobs unaffected:** `list_jobs_tool` shows no unexpected state changes.
4. **Virtual CAN create/delete still works:** `create_virtual_can name=vcanreg1` -> `delete_can_interface interface_name=vcanreg1`.
5. **Normal record_can on valid interface still works:** Full cycle - create vcan, record 5s, wait, confirm `status: "completed"`, delete.

If all 5 pass, proceed to the per-bug wave tests above.

---

## Issue Traceability

| Test | Reviewed status |
|------|-----------------|
| W3-T1 | Live behavior passed; keep as regression for delete-active guard. |
| W3-T2 | Live behavior passed; keep as regression that missing SocketCAN interfaces fail synchronously before job creation. |
| W3-T5 | Confirmed lifecycle issue: current branch blocks delete while CAN leases are active. |
| W4-T1 | Live behavior passed with `interface_lease_conflict`; protocol previously used the wrong code name. |
| W4-T2 | Confirmed hardening gap: warning-only record start is agent-risky; current branch rejects before job creation. |
| W4-T3 | Confirmed real issue: transmit can return `sent: true` while reporting `lease_conflict: true`; current branch rejects before frame send. |
| W2-T1, W2-T2 | Confirmed validation/test gap plus protocol drift: use `a2l_file_path`, and test malformed `.a2l` content as well as wrong suffixes. |
| W2-T3 | Live behavior passed; keep regression coverage for failed unreadable artifacts and cancelled readable partial artifacts. |
| W1-T1-W1-T4 | Mostly fixed; add/keep count-only regressions, especially ghost `read_artifact`. |
| W5-T1 | Live behavior passed; add negative tests for builtin UARTs with no driver or `port` driver. |
| W6-T1-W6-T4 | Confirmed issue and false-positive risk: current branch blocks same-transport flash/STIM/seed while preserving different-backend channel scopes. |
| W3-T3 | Live behavior is understandable; prefer a stronger machine-readable `job_type_mismatch` error code. |
| W3-T4 | Live behavior passed; keep regression for `already_terminal: true`. |
| W2-T4 | Live behavior passed with explicit type mismatch; keep regression. |

GitHub issue: https://github.com/plotune/plotune-nexus/issues/140
