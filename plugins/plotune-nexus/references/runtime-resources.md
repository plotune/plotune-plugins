# Runtime Resources And Tool Families

## Contents

- Resource-first orientation
- Device-local execution model
- Tool families

## Resource-First Orientation

Before mutating a device, read fast MCP resources when available:

1. `plotune://device/context`
2. `plotune://device/interfaces`
3. `plotune://artifacts/recent`

When the user asks for a documented Plotune procedure or mitigation, also inspect the skill catalog:

4. `plotune://skills/categories`

For UDS or DoIP diagnostics, also read:

5. `plotune://diagnostics/uds/transports`
6. `plotune://diagnostics/uds/recent`
7. `plotune://diagnostics/uds/doip-leases`
8. `plotune://settings/hardware`

Use resources for current-state snapshots. Use tools for mutations, reservations, transfers, and long-running work.
DoIP lease resources are for coordination only and redact owner session IDs; keep the session ID returned by your own acquire call for cleanup.

Read `tool-contracts.md` when exact tool names or argument shapes are needed.

## Device-Local Execution Model

MCP tool execution happens on the Plotune Nexus device. Unless a tool explicitly says otherwise, these are Nexus-device resources:

- file paths
- CAN, SLCAN, UART, DoIP, and XCP interfaces
- serial adapters
- jobs
- artifacts
- managed containers
- gateway state
- local clocks and runtime capabilities

Do not invent workstation shell commands for work that the connected MCP server exposes as a Nexus tool.

## Tool Families

Catalog and skills:

- `list_skill_category`
- `list_skills`
- `get_skill`
- `get_devices`

Use `get_skill(...)` for a live documented workflow when the task depends on exact payloads, sequence definitions, or mitigation steps. Do not invent active-control frames or diagnostic payloads when the live catalog, user request, DBC/A2L/ODX data, or external runbook does not provide them.

Device and runtime:

- `get_device_context_tool`
- `get_device_status_tool`
- `get_runtime_capabilities_tool`
- `get_tooling_health_tool`
- `get_clock_sync_status_tool`

Jobs and test sequences:

- `list_jobs_tool`
- `get_job_status_tool`
- `cancel_job_tool`
- `wait_for_job`
- `run_test_sequence`
- `get_test_sequence`
- `wait_for_test_sequence`
- `cancel_test_sequence`

CAN, DBC, and gateways:

- record, stop, and inspect CAN jobs
- send single, batch, DBC, and periodic frames
- wait for raw or DBC signal conditions
- capture snapshots
- lease interfaces
- configure bitrate and interface state
- attach and detach SLCAN
- create and delete virtual CAN
- start, stop, and inspect policy gateways

XCP:

- recording jobs
- calibration read/write
- active-job calibration reuse
- STIM
- Seed+Key unlock
- CAN and UDP/Ethernet transports

UDS and DoIP:

- list transports
- send raw UDS requests
- discover DoIP vehicles
- acquire and release DoIP target leases
- read hardware settings for DoIP source path selection on multi-NIC benches

UART:

- list devices
- open and close sessions
- send, read, and wait
- record and inspect UART recordings
- manage modem lines
- use flow control and RS-485 mode

Containers:

- start, inspect, and stop managed controller or simulator containers from staged OCI tar artifacts

Artifacts and drives:

- list and inspect local artifacts
- bounded inline artifact reads, including tail and line-range reads
- import/export transfer flows through `prepare_put_artifact`, `put_artifact`, and `get_artifact`: files transfer directly with the device at any size (uploads resume in `Content-Range` pieces); the Plotune transfer cloud is only for sharing with someone who cannot reach the device
- configured artifact drives for local files, SFTP, Google Drive, and OneDrive/SharePoint
