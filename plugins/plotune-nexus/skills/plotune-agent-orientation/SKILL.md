---
name: plotune-agent-orientation
description: Use when starting work with a connected Plotune Nexus MCP server, planning device-local DAQ or diagnostics tasks, or deciding which Nexus resources and tools to read before taking any action.
---

# Plotune Nexus Agent Orientation

Plotune Nexus is an appliance-style MCP platform. All hardware interfaces, jobs, artifacts, containers, and gateway state live on the Nexus device. The MCP server exposes them as resources and tools. Read resources first, then act.

## Required — Read These Before Any Action

Read these four resources at the start of every session and before any hardware interaction:

**Device context** — running jobs, active gateways, active containers, system load, clock sync:
```
read resource: plotune://device/context
```
Check: Are there active recording jobs from a prior session? Active gateways or containers occupying interfaces? High memory load (> 85%) that may cause job failures? Clock sync drift that affects timestamps in recordings?

**Interface inventory** — attached CAN, SLCAN, virtual CAN, UART, and their state:
```
read resource: plotune://device/interfaces
```
Check: Which interfaces are present and `up`? Is there an existing socket or lease on the interface you plan to use? Is `fd_enabled: true` for a CAN FD workflow? Which UART devices have `usage_status: available`?

**Recent artifacts** — artifacts from the last 2 hours plus connected drives:
```
read resource: plotune://artifacts/recent
```
Check: Did a previous job produce A2L, LAB, DBC, or recording artifacts you can reuse? What is the device recording directory?

**Recent notes** — operator and agent context for tests, setup changes, failures, and linked artifacts:
```
read resource: plotune://notes/context
```
Check: Did an operator leave setup notes, failure observations, or links to recordings/artifacts that explain the current state? Does a previous agent note mention a retest condition or cleanup risk?

**For diagnostics, also read:**
```
read resource: plotune://diagnostics/uds/transports
read resource: plotune://diagnostics/uds/recent
read resource: plotune://diagnostics/uds/doip-leases
read resource: plotune://settings/hardware
```

## Interpreting The Device Context

After reading `plotune://device/context`, apply these rules:

| Field | Action |
|---|---|
| `active_jobs` with `status: running` | Check if owned by this session. Cancel orphaned jobs with `cancel_job_tool(job_id)` after confirming with the user. |
| `active_gateways` | Each gateway holds two CAN interfaces. Stop any not needed with `stop_can_gateway(job_id)`. |
| `active_containers` | Containers may hold CAN or serial leases. Stop idle containers with `stop_container(name)`. |
| `clock_sync.synced: false` | Note in any evidence report — recording timestamps may drift. |
| `system_load.memory_used_percent > 85` | Warn the user before starting more jobs. |

## Interpreting The Interface Inventory

After reading `plotune://device/interfaces`, apply these rules:

| Field | Action |
|---|---|
| `state` not `up` | Call `set_can_interface_state_tool(name, "up")` or ask the user if the interface should be brought up. |
| `leases` is non-empty | Another session holds the interface. Do not acquire without checking with the user. |
| `fd_enabled: false` | CAN FD transmit is not supported on this interface. Use a virtual backend for FD simulation. |
| `uart_serial_devices[].usage_status: busy` | The UART device is in use. List sessions with `get_uart_session`. |
| `attachable_usb_can_adapters` non-empty | USB CAN adapters (SLCAN, Vector VN16xx) are connected but not yet attached. Use `attach_usb_can` with their `adapter_id` before using them as CAN interfaces. |

## Execution Model

- All MCP tools run on the Nexus device, not the workstation.
- File paths in tool arguments are device-local. If a path from artifact metadata starts with `/host/`, strip that prefix before reusing it.
- Long-running work (recordings, test sequences, containers) is async. Trigger the job, then poll with `wait_for_job(job_id)` or job-specific status tools, then inspect artifacts.
- Use `search_notes(...)` before rerunning failed tests or interpreting ambiguous artifacts. Use `write_note(...)` after meaningful observations so future operators and agents can understand what happened.
- The Plotune cloud control plane and cloud storage are separate planes. Do not reference them in device-side tool arguments.

## When A Documented Procedure Is Needed

Before sending any active-control frames or diagnostic requests, check the live skill catalog on the device:
```
list_skill_category()
list_skills(category="diagnostics")
get_skill("skill-name")
```

If no documented procedure, exact payload, or approved runbook is available, stop and ask the user rather than guessing.

## Capability Check

When protocol support or tooling availability matters, call:
```
get_runtime_capabilities_tool()
get_tooling_health_tool()
```

These report installed kernel drivers, available tool binaries, and protocol readiness. Do not assume CAN FD, SLCAN, vCAN, or DoIP support from interface names alone — confirm from runtime.
