# Workflow Playbooks

## Standard Read Pass

Use this before most hardware work:

1. Read `plotune://device/context`.
2. Read `plotune://device/interfaces`.
3. Read `plotune://artifacts/recent`.
4. Call `get_tooling_health_tool()` when protocol support matters.
5. If the task references a documented procedure, inspect `plotune://skills/categories`, `list_skills(...)`, and `get_skill(...)`.
6. Select tools only after confirming current runtime support.

## CAN Capture

1. Read runtime resources.
2. Acquire the target CAN interface with `acquire_can_interface(...)` if doing active work.
3. Start `record_can(...)` with a bounded duration; if the interface was acquired, pass the same session ID as `lease_session_id`.
4. Use `wait_for_job(...)` or job status tools.
5. Inspect `get_record_can(...)`.
6. Inspect artifact metadata.
7. Release the interface with `release_can_interface(...)` if acquired.

## CAN Mitigation With Evidence

1. Read runtime resources and device status.
2. Acquire the interface with `acquire_can_interface(...)`.
3. Confirm the fault condition with `wait_can_until(...)` or a bounded snapshot.
4. Resolve the exact mitigation payload from the user, a live Nexus skill, a DBC-backed command, or an approved runbook.
5. Stop if no exact payload is available.
6. Ask for user confirmation before sending mitigation frames unless already explicitly authorized.
7. Send with `send_can_frame_batch(...)` using bounded total duration and inter-frame delay; pass the owning `lease_session_id` for leased interfaces.
8. Confirm the expected clear condition.
9. Capture post-action evidence.
10. Export or upload artifacts if requested.
11. Release the interface with `release_can_interface(...)` and stop any active periodic traffic.

## UART Session

1. Read `plotune://device/interfaces`.
2. Call `list_uart_devices()` if more detail is needed.
3. Open a session with explicit baud, flow control, and RS-485 settings when needed.
4. Use bounded send/read/wait calls.
5. Record only when needed and stop the recording explicitly.
6. Close the session.

## UDS/DoIP Diagnostic

1. Read `plotune://diagnostics/uds/transports`.
2. Read `plotune://diagnostics/uds/recent`.
3. Read `plotune://diagnostics/uds/doip-leases` for DoIP.
4. Read `plotune://settings/hardware` when choosing DoIP `interface_name` or `source_address`.
5. For DoIP, call `discover_doip_vehicles(...)` and acquire a target lease with `acquire_doip_target_lease(...)` before active work.
6. Send bounded raw UDS requests with explicit addressing.
7. Preserve NRCs, response-pending behavior, timeouts, and raw response details.
8. Release DoIP leases with `release_doip_target_lease(...)`.

## XCP Recording Or Calibration

1. Read runtime resources and recent artifacts.
2. Locate required A2L and LAB files from artifacts or configured drives.
3. Choose `transport="can"` or `transport="udp"` from runtime context and A2L metadata.
4. For recording, start `record_xcp(...)` with `duration_seconds` and artifact format.
5. For calibration, ask for confirmation before `set_xcp_calibration(...)`, `set_xcp_job_calibration(...)`, STIM, Seed+Key unlock, or programming.
6. Reuse active XCP recording jobs with job-scoped calibration tools when the scenario needs one master session.
7. Wait for terminal state and inspect `get_record_xcp(...)` artifacts.

## Container Image Import

1. Build and save the OCI image tar off-device.
2. Call `prepare_put_artifact(..., folder_name="containers")`. Tars of any size upload directly to the device; send tars over 64 MiB in `Content-Range` pieces (see the tool contracts).
3. Upload the tar to the returned `upload_url` outside MCP.
4. Call `put_artifact(transfer_id)` and keep the returned container artifact ID.
5. Start the container with explicit `network_mode`, `can_interfaces`, `serial_devices`, `share_host_ptys`, volumes, and `max_runtime_seconds`.
6. Inspect `get_container_status(...)`.
7. Stop the container when the task is complete.

## Artifact Export

1. List artifacts or inspect the job result.
2. Call `get_artifact_metadata_tool(...)`.
3. For small review, use `read_artifact(...)` with `max_bytes`; use `from_end=True` for the tail or `start_line` to jump into a text file.
4. For sharing or full downloads, use `get_artifact(...)` (served directly from the device at any size) or a configured artifact drive.
5. Normalize `/host/` paths before reusing local paths.
6. Keep drive paths relative to the configured root.

## Artifact Import From Configured Drive

1. Call `list_artifact_drives()`.
2. Use `list_drive_content(...)` or `search_in_drive(...)` when supported.
3. Call `download_from_artifact_drive(...)` with a Nexus-local `local_path` or let the tool choose a default.
4. Use the resulting local path as input to later MCP tools.
5. Keep `remote_path` relative to the configured drive root.
