# MCP Tool Contracts Quick Reference

Read this when a workflow needs exact tool names or argument shapes. Runtime schemas from the connected MCP server remain authoritative.

## Resources

Read-only resources commonly used before tool calls:

- `plotune://skills/categories`
- `plotune://device/interfaces`
- `plotune://device/context`
- `plotune://artifacts/recent`
- `plotune://notes/context`
- `plotune://settings/hardware`
- `plotune://diagnostics/uds/transports`
- `plotune://diagnostics/uds/recent`
- `plotune://diagnostics/uds/doip-leases`

## Skill Catalog

- `list_skill_category()`
- `list_skills(category=None, kind=None)`
- `get_skill(skill_name)`

Use live skills for exact mitigation payloads, sequence definitions, and procedure-specific details.

## Argument Glossary

- `channel`: CAN bus/channel name used by observe/transmit tools, for example `vcan0` or `can0`.
- `interface`: python-can backend name used by CAN observe/transmit tools, normally `socketcan`; `virtual` is a python-can in-process backend and is not a Linux interface.
- `interface_name`: Linux interface lifecycle/lease target used by tools such as `create_virtual_can`, `delete_can_interface`, `get_can_interface_status_tool`, and `acquire_can_interface`.
- `device_path`: Nexus-local UART path from `list_uart_devices`.
- `a2l_file_path`, `dbc_file_path`, and `lab_file_path`: Nexus-local paths, not artifact IDs. If artifact metadata returns a path with `/host/`, strip the `/host` prefix before passing it back to path-based tools.

## CAN And Interface Lifecycle

- `record_can(channel, duration_seconds, interface="socketcan", bitrate=None, lease_session_id=None)`
- `get_record_can(job_id)`
- `stop_record_can(job_id)`
- `wait_for_job(job_id, timeout_seconds=30.0, poll_interval_seconds=0.25)`
- `wait_can_until(channel, timeout_seconds, interface="socketcan", bitrate=None, arbitration_id=None, data_mask_hex=None, data_pattern_hex=None)`
- `capture_can_snapshot(channel, interface="socketcan", bitrate=None, duration_seconds=0.5, max_frames=50)`
- `send_can_frame(channel, arbitration_id, data_hex="", interface="socketcan", bitrate=None, is_extended_id=False, is_remote_frame=False, is_fd=False, bitrate_switch=False, error_state_indicator=False, lease_session_id=None)`
- `send_can_frame_batch(channel, frames, interface="socketcan", bitrate=None, inter_frame_delay_seconds=0.0, max_total_duration_seconds=2.0, lease_session_id=None)`
- `send_dbc_message(dbc_file_path, message_name, signal_values, channel, interface="socketcan", bitrate=None, lease_session_id=None)`
- `wait_dbc_signal(dbc_file_path, message_name, signal_name, operator, timeout_seconds, channel, interface="socketcan", bitrate=None, hold_time_seconds=0.2, value=None, lower_bound=None, upper_bound=None)`
- `send_periodic_can_frame(channel, arbitration_id, period_seconds, max_runtime_seconds, data_hex="", interface="socketcan", bitrate=None, is_extended_id=False, is_remote_frame=False, is_fd=False, bitrate_switch=False, error_state_indicator=False, session_id=None, lease_session_id=None)`
- `stop_periodic_can_frame(handle_id, wait_timeout_seconds=1.0)`
- `list_can_interfaces_tool()`
- `get_can_interface_status_tool(interface_name)`
- `acquire_can_interface(interface_name, agent_id, session_id, purpose, metadata=None)`
- `release_can_interface(interface_name, session_id)`
- `list_usb_can_adapters()`
- `attach_usb_can(adapter_id=None, bitrate=500000, channels=None, interface_name=None, data_bitrate=None, listen_only=False, bitrate_code=None, serial_baud=None, experimental=False)`
- `detach_usb_can(interface_name=None, adapter_id=None, lease_session_id=None)`
- `create_virtual_can(name, bring_up=True)`
- `delete_can_interface(interface_name)`
- `set_can_interface_state_tool(interface_name, state, lease_session_id=None)`
- `configure_can_bitrate(interface_name, bitrate, sample_point=None, sjw=None, prop_seg=None, phase_seg1=None, phase_seg2=None, lease_session_id=None)`

CAN FD transmit and observation must be confirmed from runtime metadata such as `fd_enabled=true`, except for the `virtual` backend used in tests and simulations.
When a SocketCAN interface has an active CAN lease, MCP record/transmit, interface-mutation, UDS-over-CAN, and XCP-on-CAN tools reject the request unless `lease_session_id` matches the owning `acquire_can_interface(...)` session.

## DDS

- `join_dds_session(name, domain_id=None, cyclonedds_uri=None)`
- `leave_dds_session(session_id)`
- `list_dds_participants_tool(domain_id=None, cyclonedds_uri=None)`
- `list_dds_topics_tool(domain_id=None, cyclonedds_uri=None)`
- `get_dds_domain_status_tool(domain_id=None)`
- `publish_dds_message(topic_name, message, session_id, type_name=None, domain_id=None, period_seconds=None, max_runtime_seconds=None)`
- `stop_periodic_dds_message(handle_id, wait_timeout_seconds=1.0)`
- `capture_dds_snapshot(topic_name, session_id, type_name=None, duration_seconds=0.5, max_messages=50, domain_id=None)`
- `wait_dds_signal(topic_name, field, operator, timeout_seconds, session_id, value=None, lower_bound=None, upper_bound=None, type_name=None, domain_id=None, poll_interval_seconds=0.05, hold_time_seconds=0.0, include_existing=False)`
- `record_dds_topics(topics, duration_seconds, session_id, domain_id=None)`

Create one named session before any DDS data-plane operation and close it with `leave_dds_session(...)`. The session supplies the long-lived participant and its optional `cyclonedds_uri`; pass that XML only to `join_dds_session`, not to data-plane tool calls. Use the same `domain_id` as the session on every call (or omit it only when the configured default is the same domain). Discovery tools have no `session_id`; pass their `domain_id` and, for a multi-NIC or cross-machine bench, the same `cyclonedds_uri` used to join.

`record_dds_topics` takes a non-empty list of `{"topic_name": ..., "type_name": ...}` entries. `type_name` is optional but should be explicit for live and cross-machine topics; the runtime fallback is `plotune_msgs/msg/Json`. It starts one async job and writes all requested topics into one MCAP/JSONL artifact. Use generic job tools to poll, wait, or cancel it. A cancelled recording can still have a readable partial artifact.

For periodic publishing, set both `period_seconds` and `max_runtime_seconds`; use `stop_periodic_dds_message(...)` for early cleanup. A publish result does not establish remote delivery or actuator effect. Verify a separate feedback topic with `wait_dds_signal(...)`, especially for commands that affect a DUT or HIL bench.

## XCP

- `record_xcp(lab_file_path, a2l_file_path, channel=None, duration_seconds=10.0, interface="socketcan", bitrate=None, event_channel=0, artifact_format="mf4", lease_session_id=None)`
- `get_record_xcp(job_id)`
- `stop_record_xcp(job_id)`
- `read_xcp_calibration(a2l_file_path, calibration_name, channel=None, interface="socketcan", bitrate=None, transport="can", host=None, port=13400, lease_session_id=None)`
- `set_xcp_calibration(a2l_file_path, calibration_name, value, channel=None, interface="socketcan", bitrate=None, transport="can", host=None, port=13400, lease_session_id=None)`
- `read_xcp_job_calibration(job_id, calibration_name, timeout_seconds=5.0)`
- `set_xcp_job_calibration(job_id, calibration_name, value, timeout_seconds=5.0)`
- `stim_xcp_signals(a2l_file_path, stimulations, duration_seconds, stim_interval_seconds=0.01, channel=None, interface="socketcan", transport="can", host=None, port=13400, bitrate=None, lease_session_id=None)`
- `xcp_get_seed(resource, a2l_file_path, channel=None, interface="socketcan", transport="can", host=None, port=13400, bitrate=None, ttl_seconds=30.0, lease_session_id=None)`
- `xcp_unlock(session_id, key_hex)`

Use `transport="udp"` for XCP-on-Ethernet non-recording calls when host/port are provided or can be read from an A2L `XCP_ON_ETH` block.
For XCP-on-CAN (`transport="can"` with `interface="socketcan"`), pass the owning CAN interface lease `session_id` as `lease_session_id` when the channel is leased.

## UDS And DoIP

- `list_uds_transports()`
- `send_uds_request(target, request_hexes, timeout_seconds=2.0, wait_for_response=True, lease_session_id=None, raise_on_negative_response=False, max_response_pending_wait_seconds=None)`
- `discover_doip_vehicles(interface_name=None, source_address=None, timeout_seconds=1.5, port=13400, max_results=20, address_family="auto", vin=None, eid_hex=None)`
- `list_doip_target_leases()`
- `acquire_doip_target_lease(target, agent_id, session_id, purpose, tester_present=None, metadata=None)`
- `release_doip_target_lease(target, session_id)`

CAN UDS target shape:

```json
{
  "transport": "can_isotp",
  "channel": "can0",
  "tx_id": "7E0",
  "rx_id": "7E8",
  "addressing_mode": "normal"
}
```

DoIP target shape:

```json
{
  "transport": "doip",
  "host": "192.168.0.10",
  "port": 13400,
  "tester_logical_address": "0E00",
  "ecu_logical_address": "0001",
  "routing_activation_type": "default"
}
```

Use `source_address` or `interface_name` in DoIP targets when a multi-NIC bench needs path-stable diagnostics and lease coordination.

Use one ECU target per `send_uds_request(...)` call. For leased CAN ISO-TP work, pass the same `session_id` used with `acquire_can_interface(...)` as `lease_session_id`. For leased DoIP work, pass the same `session_id` used with `acquire_doip_target_lease(...)` as `lease_session_id`. `max_response_pending_wait_seconds` extends the receive deadline for NRC `0x78` response-pending without resending the request. Preserve NRCs and timeouts as evidence.
DoIP lease listings and resources redact owner session IDs. Keep the `session_id` returned by your own `acquire_doip_target_lease(...)` call for later `send_uds_request(...)` and `release_doip_target_lease(...)` calls.

## UART

- `list_uart_devices()`
- `open_uart_session(device_path, baud_rate, data_bits=8, parity="none", stop_bits=1, flow_control="none", read_timeout_seconds=0.2, line_ending="\n", encoding="utf-8", rs485_mode=False, rs485_delay_before_tx_seconds=0.0, rs485_delay_before_rx_seconds=0.0)`
- `get_uart_session(session_id)`
- `close_uart_session(session_id)`
- `send_uart(session_id, mode, text=None, data_hex=None, append_line_ending=True)`
- `read_uart(session_id, mode, timeout_seconds, max_bytes=4096)`
- `wait_uart(session_id, mode, operator, timeout_seconds, poll_interval_seconds=0.05, hold_time_seconds=0.0, value=None, pattern_hex=None)`
- `record_uart(session_id, duration_seconds, artifact_format="txt")`
- `get_record_uart(job_id)`
- `stop_record_uart(job_id)`
- `get_uart_modem_lines(session_id)`
- `set_uart_modem_lines(session_id, dtr=None, rts=None)`

USB CAN adapters to attach come from `list_usb_can_adapters()`; options an adapter does not support (for example `data_bitrate` on SLCAN, `bitrate_code` on Vector) are rejected with `usb_can_option_unsupported`.

## Gateways And Containers

- `start_can_gateway(source_interface, destination_interface, source_to_destination_rules, destination_to_source_rules=None, bus_interface="socketcan", source_channel=None, destination_channel=None, max_runtime_seconds=None, metadata=None)`
- `get_can_gateway(job_id)`
- `stop_can_gateway(job_id, wait_timeout_seconds=1.0)`
- `start_container(name, artifact_id, command=None, args=None, env=None, volumes=None, can_interfaces=None, serial_devices=None, share_host_ptys=False, network_mode="none", max_runtime_seconds=None, metadata=None)`
- `get_container_status(container_id_or_name)`
- `stop_container(container_id_or_name, wait_timeout_seconds=1.0)`

Gateways are allowlist-only CAN forwarding jobs. Every gateway rule must include `rule_id` so counters, logs, and errors can identify the matching rule. Gateway start/status responses redact internal managed lease session IDs; use the returned `job_id` for monitoring and stop calls. Managed containers require staged OCI tar artifacts.

## Artifacts And Drives

- `list_artifacts_tool(only_complete=False, limit=None, job_id=None, job_type=None, format=None, interface=None, since=None)`
  - `job_id` accepts a recording job ID (`record_can`, `record_xcp`, `record_uart`) or a test-sequence job ID; test-sequence IDs are expanded to their related artifact IDs.
- `get_artifact_metadata_tool(artifact_id)`
- `read_artifact(artifact_id, encoding=None, max_bytes=65536, offset_bytes=0, from_end=False, start_line=None)`
  - Returns at most 256 KiB per call and follows `next_offset` until `eof`. `from_end=True` returns the tail; `start_line=N` starts at line N of a text file.
- `get_artifact(artifact_id, transfer_cloud_id=None, folder_name="artifacts", mode="direct")`
- `prepare_put_artifact(file_name, size, sha256=None, content_type="application/octet-stream", transfer_cloud_id=None, folder_name="artifacts", mode="direct")`
- `put_artifact(transfer_id)`
- `put_artifact_content(file_name, content_text=None, content_base64=None)` — inline upload up to 8 MiB; the file body costs conversation tokens, so prefer `prepare_put_artifact` beyond small text files.
- `delete_artifact_tool(artifact_id)`
- `run_artifact_cleanup(dry_run=True)`
- `list_artifact_drives()`
- `list_drive_content(drive_id, remote_path="", recursive=False, limit=100)`
- `search_in_drive(drive_id, query, remote_path="", limit=50)`
- `upload_to_artifact_drive(drive_id, local_path, remote_path="", overwrite=False)`
- `download_from_artifact_drive(drive_id, remote_path, local_path=None, overwrite=False)`

If metadata path values start with `/host/`, strip that prefix before passing the path back to tools that expect Nexus-local paths.

Transfers go directly between the client and the device by default (`mode="direct"`, `transport="direct"`), at any size: no cloud setup or internet access is needed, and the link works from a shell with plain `curl`. Pass `mode="cloud"` (or `transfer_cloud_id`) to use the Plotune transfer cloud instead, for example to share a file with someone who cannot reach the device (`transport="cloud"`).

Import flow is two phase: call `prepare_put_artifact(...)`, send the bytes with `PUT <upload_url>` outside MCP (for example `curl --upload-file <file> "<upload_url>"`, no extra headers), then call `put_artifact(transfer_id)` to get the device path. Over the local network one request can carry the whole file. Through the device tunnel (`https://<device>.plotune.net`) one request is capped at 64 MiB, so send larger files as pieces of up to 32 MiB with `Content-Range: bytes <start>-<end>/<size>`; the device appends pieces in order and verifies the SHA-256 after the last. A piece from the wrong offset is refused (409) with `received`, the byte count to resume from, and `GET <upload_url>` reports the same. The link stays valid while pieces keep arriving and expires after 15 minutes of silence (5 minutes if no piece has arrived yet, so unused uploads release their disk space), and `GET <upload_url>` reports `partial`, `finalizing` (every byte arrived and the file is being saved; keep asking) or the finished result. A failed upload can be retried on the same link, and `DELETE <upload_url>` abandons it. The prepare result carries `max_request_bytes` (the per-request limit through the tunnel) and `part_size` to use. Uploads are classified like other imports, so the retention policy (when enabled) can later remove them.

```bash
# upload.sh: send FILE to <upload_url> in 32 MiB pieces. Safe to rerun: it asks the
# device how much has arrived and carries on from there. Run it with `bash upload.sh`.
FILE="<path of the file>"; URL="<upload_url>"
SIZE=$(stat -c%s "$FILE"); PIECE=$((32*1024*1024))
STATUS=$(curl -fsS "$URL") || { echo "cannot reach the upload link" >&2; exit 1; }
case "$STATUS" in *completed*) echo "already uploaded"; exit 0;; esac
OFFSET=$(printf '%s' "$STATUS" | sed -n 's/.*"received": *\([0-9]*\).*/\1/p'); OFFSET=${OFFSET:-0}
while [ "$OFFSET" -lt "$SIZE" ]; do
  END=$(( OFFSET + PIECE < SIZE ? OFFSET + PIECE : SIZE ))
  tail -c +$((OFFSET+1)) "$FILE" | head -c $((END-OFFSET)) |
    curl -sS --fail-with-body -X PUT -H "Content-Range: bytes $OFFSET-$((END-1))/$SIZE" --data-binary @- "$URL" ||
    { echo "piece at byte $OFFSET failed; run again to resume" >&2; exit 1; }
  OFFSET=$END
done
# All bytes are in. The device now saves the file ("finalizing"); if saving failed
# earlier, an empty PUT asks it to try again.
for _ in $(seq 1 60); do
  STATUS=$(curl -fsS "$URL") || break
  case "$STATUS" in *completed*) echo "uploaded; call put_artifact with the transfer_id"; exit 0;; esac
  case "$STATUS" in *finalizing*) ;; *) curl -sS --fail-with-body -X PUT --data-binary "" "$URL" >/dev/null || true;; esac
  sleep 2
done
echo "the device has not finished saving the file; check with GET on the upload link" >&2; exit 1
```

Use `folder_name="containers"` for OCI tar images intended for `start_container(...)`.

Export flow: `get_artifact(...)` returns a `download_url` and the `file_name` to save it under. Download it outside MCP with `curl -fL -C - -o <file_name> "<download_url>"` (resumable) or a browser; a direct link needs no auth header and stays valid while it is being used, up to a few hours. Check `transport` in the result to know which route was used.

Deletion is permanent. Use `delete_artifact_tool(...)` only after the operator confirms the exact artifact ID. Use `run_artifact_cleanup(dry_run=True)` to preview retention deletion candidates, summarize `deleted_count` and `deleted_paths`, and call `run_artifact_cleanup(dry_run=False)` only after explicit operator confirmation.

## Notes And Test Context

- `write_note(body_markdown, links=None)`
- `search_notes(query=None, linked_only=False, linked_kind=None, linked_target_id=None, page=1, page_size=20)`

MCP-written notes are always attributed to `nexus@plotune.net`.

Read `plotune://notes/context` before interpreting ambiguous failures, rerunning diagnostics, or deciding whether an artifact is reusable. The resource returns recent operator and agent notes, newest first, and is intended to carry bench context that is not obvious from jobs or artifacts alone.

Use `search_notes(...)` when you need older or filtered context:
- search by symptom: `"pressure"`, `"timeout"`, `"routing activation"`, or a DTC
- set `linked_only=True` when you only want notes tied to files, channels, or interfaces
- set `linked_kind` to `file`, `channel`, or `interface` when the investigation has a specific context type
- set `linked_target_id` to an artifact, channel, or interface ID when checking for notes about a specific target
- failed searches automatically return spelling suggestions and the latest five notes

Use `write_note(...)` after a meaningful observation, especially when:
- failed tests need setup context, retest conditions, or operator observations preserved
- a test run passed with a non-obvious setup condition
- an artifact needs interpretation, such as "brake pressure stayed flat after step 3"
- the operator changed bench wiring, ignition state, firmware, gateway routing, or calibration setup
- cleanup left a retest condition or follow-up risk

Keep notes concise and evidence-oriented. Prefer markdown links or structured `links` entries for artifacts, channels, or interfaces. Do not store secrets, bearer tokens, customer personal data, or raw payload dumps that belong in artifacts. Notes are persistent device context for operators and future agents; they are not issue tracking or project management records.
