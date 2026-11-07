---
name: plotune-safety-and-errors
description: Use when a Plotune Nexus task sends traffic, writes calibration, runs diagnostics, starts containers or gateways, manages interface leases, handles MCP error responses, or requires cleanup of active hardware work.
---

# Plotune Nexus Safety And Errors

Hardware-adjacent MCP actions must be bounded, explainable, and cleaned up. This skill defines the rules for confirmation, limits, lease management, error handling, and cleanup.

## Before Active Work

1. Read `plotune://device/context` and `plotune://device/interfaces`.
2. Identify any conflicting active jobs, gateways, or leases from prior sessions.
3. Have the exact target confirmed: interface name, channel, device path, ECU address.
4. Confirm the exact payload or command from the user, a live Nexus skill, DBC/A2L/ODX data, or an approved runbook. If the payload is missing, stop and ask — do not invent frames, service requests, or calibration values.

## Actions That Require Explicit Confirmation

Ask the user to confirm before any of these, even if previously discussed:

- Sending CAN frames that actuate hardware, trigger faults, or clear fault conditions
- XCP calibration writes: `set_xcp_calibration`, `set_xcp_job_calibration`
- STIM signal injection: `stim_xcp_signals`
- UDS routines that change ECU state: RoutineControl, ECUReset, SecurityAccess unlock
- UDS flash or erase sequences
- Starting a CAN gateway: `start_can_gateway`
- Starting a container with CAN, serial, or host-network access: `start_container`
- Deleting artifacts: `delete_artifact_tool`
- Running artifact retention cleanup: `run_artifact_cleanup(dry_run=False)`

Passive reads, status checks, snapshots, and resource reads do not need confirmation unless the user context is ambiguous or safety-critical.

## Bounds — Always Set Explicit Limits

Every active operation requires a limit parameter. Do not omit these:

| Tool | Required bound |
|---|---|
| `record_can`, `record_xcp`, `record_uart` | `duration_seconds` |
| `wait_can_until`, `wait_dbc_signal`, `wait_uart` | `timeout_seconds` |
| `send_can_frame_batch` | `max_total_duration_seconds` |
| `send_periodic_can_frame` | `max_runtime_seconds` |
| `start_can_gateway` | `max_runtime_seconds` |
| `start_container` | `max_runtime_seconds` |
| `capture_can_snapshot` | `duration_seconds`, `max_frames` |
| `send_uds_request` | `timeout_seconds` |

An unbounded gateway or container runs until the device restarts. An unbounded recording fills disk.

## Interface And Target Leases

**Acquire a CAN interface lease before active send or recording work:**
```
acquire_can_interface(
  interface_name="can0",
  agent_id="<your-agent-id>",
  session_id="<unique-session-id>",
  purpose="CAN FD capture for ECM fault analysis"
)
```

**Release when the task ends or fails:**
```
release_can_interface(interface_name="can0", session_id="<session-id>")
```

**Acquire a DoIP target lease before UDS/DoIP diagnostic work:**
```
acquire_doip_target_lease(
  target={"transport": "doip", "host": "192.168.0.10", "port": 13400, "tester_logical_address": "0E00", "ecu_logical_address": "0001"},
  agent_id="<your-agent-id>",
  session_id="<unique-session-id>",
  purpose="DTC read and clear"
)
```

Pass the same `session_id` as `lease_session_id` on every `send_uds_request` call while a CAN interface lease or DoIP target lease is active.
CAN and DoIP lease listings redact owner session IDs, so keep the `session_id` returned by your own acquire call for cleanup.

**Release the DoIP lease when done:**
```
release_doip_target_lease(
  target={"transport": "doip", "host": "192.168.0.10", ...},
  session_id="<session-id>"
)
```

## MCP Error Response Handling

Nexus MCP errors are structured for agents. When a tool returns an error:

1. Read the `Tip:` line in the error message before retrying.
2. Parse the JSON error payload — it contains error code, context, and suggested resolution.
3. Address the root cause from the tip. Do not retry blindly.
4. Preserve NRCs, timeouts, routing activation failures, and raw response bytes in your output. Do not collapse them into "no issue found."

**Common patterns and resolutions:**

| Error | Likely cause | Resolution |
|---|---|---|
| Interface not found | Interface is down or not attached as SocketCAN | Read `plotune://device/interfaces`, call `set_can_interface_state_tool`, or `attach_usb_can` for an adapter from `list_usb_can_adapters` |
| Interface already leased | Another session holds the lease | Ask user whether to wait or cancel the other session |
| Device unreachable | Device is offline, remote access is off, or the managed tunnel is down | Inform user; check the device's tunnel settings and connectivity |
| UDS NRC 0x78 response pending | ECU is still processing | Use `max_response_pending_wait_seconds` — do not resend |
| UDS NRC 0x7F service not supported | Service not available in current session or security level | Check session state; may need SecurityAccess first |
| UDS NRC 0x22 conditions not correct | ECU precondition not met | Check ignition state, engine state, or required prior step |
| Job not found | Job ID is stale or from another session | Call `list_jobs_tool()` to find current job IDs |

## Cleanup Checklist

Run this at the end of every hardware workflow and before stopping on any error:

- [ ] `release_can_interface(interface_name, session_id)` for each CAN lease acquired
- [ ] `release_doip_target_lease(target, session_id)` for each DoIP lease acquired
- [ ] `stop_periodic_can_frame(handle_id)` for each periodic frame started
- [ ] `stop_can_gateway(job_id)` for each gateway started by this task
- [ ] `stop_record_can(job_id)` / `stop_record_xcp(job_id)` / `stop_record_uart(job_id)` for recordings not at terminal state
- [ ] `cancel_job_tool(job_id)` for any job that should not continue running
- [ ] `close_uart_session(session_id)` for each UART session opened
- [ ] `stop_record_uart(job_id)` for any UART recording still running
- [ ] `stop_container(name)` for each container started by this task
- [ ] `detach_usb_can(interface_name)` for any USB CAN adapter attached temporarily
- [ ] `delete_can_interface(interface_name)` for any virtual CAN interface created for this task

## Path Rules

Artifact metadata may return device-local paths with a `/host/` prefix. Strip it before passing to tools:
```
/host/var/lib/plotune-nexus/recordings/run.asc  →  /var/lib/plotune-nexus/recordings/run.asc
```

Drive paths are relative to the configured drive root. Use `bench-runs/run.asc`, not `shared/bench-runs/run.asc`.
