# Safety And Error Rules

## Bounded Operations

Use explicit limits for all active work:

- `duration_seconds`
- `timeout_seconds`
- `max_runtime_seconds`
- `max_total_duration_seconds`
- `max_frames`
- explicit stop calls

Treat long captures and data collection as async jobs. Start the job, wait or poll status, inspect the terminal result, and use artifacts for outputs.

## Confirmation

Ask for user confirmation before active control or mitigation actions that can affect hardware state, including:

- sending mitigation or actuator CAN frames
- flash or reprogramming operations
- XCP calibration writes
- UDS routines that change ECU state
- starting gateways or containers with bus/network access
- reboot or update actions

Passive reads and status checks usually do not need confirmation unless the user context is ambiguous or safety-critical.

For documented mitigations, exact payloads must come from the user, a live Nexus skill, a DBC/A2L/ODX-backed semantic command, or an approved external runbook. If the procedure is missing exact frames, service payloads, or calibration values, stop and ask instead of guessing.

## Reservations And Cleanup

Acquire leases before active CAN or DoIP work when the tools support it. Release them when done.

Clean up after active workflows:

- stop periodic CAN frames
- stop gateways
- stop or cancel jobs that should not continue
- close UART sessions
- stop UART recordings
- stop containers started for the task
- detach temporary SLCAN interfaces
- delete temporary virtual CAN interfaces when they were created for the task

## Capability Boundaries

Do not assume capabilities from docs alone. Runtime truth comes from:

- `plotune://device/interfaces`
- `get_runtime_capabilities_tool`
- `get_tooling_health_tool`

CAN FD is qualified only on Linux SocketCAN paths reporting FD support and on the `virtual` backend used for tests/simulations.

UDS currently centers on CAN ISO-TP and outbound DoIP. DoIP routing activation is the default activation type.

Policy CAN gateways are CAN-only, allowlist-driven, and should not be treated as generic bridges.

## MCP Error Contract

Nexus MCP tool errors are designed for agents. They include:

- a user-readable message
- a `Tip:`
- a device-context reminder
- a JSON error payload

Read the tip and parse the JSON payload before retrying. Preserve UDS negative response codes, response-pending states, timeouts, and raw diagnostic details in user summaries. Do not collapse them into "no issue."

## Path Rules

Artifact metadata may return a device-local path with a `/host/` prefix. Strip the prefix before passing it back to Nexus tools that expect a local device path:

```text
/host/var/lib/plotune-nexus/recordings/run.asc
/var/lib/plotune-nexus/recordings/run.asc
```

Drive paths are relative to the configured drive root. If the root is `shared`, use:

```text
bench-runs/run.asc
```

not:

```text
shared/bench-runs/run.asc
```
