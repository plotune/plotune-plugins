---
name: plotune-can-workflows
description: Use when working with Plotune Nexus CAN capture, snapshots, frame send, DBC message send, periodic frames, interface leases, SLCAN attach, virtual CAN creation, bitrate configuration, wait conditions, CAN FD, or CAN gateway setup.
---

# Plotune Nexus CAN Workflows

## Step 1 — Read Runtime State

Always start with:
```
read resource: plotune://device/interfaces
read resource: plotune://device/context
```

From `plotune://device/interfaces`, check:
- Interface `state` — must be `up` before CAN operations
- `fd_enabled` — required for CAN FD transmit (or use virtual backend)
- `leases` — existing lease means another session is active on this interface
- `attachable_usb_can_adapters` — USB CAN adapters (SLCAN, Vector VN16xx) not yet attached as CAN interfaces

From `plotune://device/context`, check:
- `active_jobs` — any running recording or gateway on this interface?
- `active_gateways` — gateways occupy two interfaces

If the interface is down, bring it up:
```
set_can_interface_state_tool(interface_name="can0", state="up", lease_session_id="<session-id-if-leased>")
```

## Step 2 — Prepare The Interface

**USB CAN adapter that needs attaching (SLCAN serial adapter, Vector VN16xx):**
```
list_usb_can_adapters()
attach_usb_can(adapter_id="<adapter_id>", bitrate=500000)
# Vector VN1610, both channels: channels=[{"channel": 1}, {"channel": 2, "bitrate": 250000}]
```
The result lists the CAN interface names (slcanN / vncanN). After work: `detach_usb_can(interface_name="<name>", lease_session_id="<session-id-if-leased>")`

**Virtual CAN for simulation (no hardware required):**
```
create_virtual_can(name="vcan0", bring_up=True)
```
After work: `delete_can_interface(interface_name="vcan0")`

**Bitrate mismatch:**
```
configure_can_bitrate(interface_name="can0", bitrate=500000, lease_session_id="<session-id-if-leased>")
```

**Acquire a lease for active send or exclusive recording:**
```
acquire_can_interface(
  interface_name="can0",
  agent_id="<agent-id>",
  session_id="<unique-session-id>",
  purpose="<describe the task>"
)
```
When a SocketCAN interface is leased, pass the same session ID as `lease_session_id` on subsequent record, transmit, bitrate, detach, or state-change tools that operate on that interface. Omit `lease_session_id` only when no active lease exists.

## Step 3 — Choose The Right Tool

| Task | Tool |
|---|---|
| Record bus traffic to an artifact file | `record_can` |
| Quick inline look at current traffic | `capture_can_snapshot` |
| Wait for a frame before acting | `wait_can_until` |
| Wait for a DBC signal to reach a value | `wait_dbc_signal` |
| Send one raw frame | `send_can_frame` |
| Send multiple frames with timing control | `send_can_frame_batch` |
| Send a named DBC message by signal values | `send_dbc_message` |
| Send a frame repeatedly | `send_periodic_can_frame` |
| Bridge two CAN interfaces with filtering | `start_can_gateway` |

## Recording

Start a bounded recording job:
```
record_can(channel="can0", duration_seconds=30, interface="socketcan", lease_session_id="<session-id-if-leased>")
```

Wait for completion:
```
wait_for_job(job_id="<returned-job-id>", timeout_seconds=45.0)
```

Inspect the result and artifact path:
```
get_record_can(job_id="<job-id>")
```

Stop early:
```
stop_record_can(job_id="<job-id>")
```

## Quick Snapshot (No Artifact)

```
capture_can_snapshot(channel="can0", interface="socketcan", duration_seconds=0.5, max_frames=50)
```

Returns decoded frames inline. Use for debugging or quick bus health checks — no artifact is created.

## Wait For A Condition

Wait until a specific arbitration ID appears:
```
wait_can_until(
  channel="can0",
  timeout_seconds=10.0,
  interface="socketcan",
  arbitration_id=513,
  data_pattern_hex="01",
  data_mask_hex="FF"
)
```

Wait until a DBC signal crosses a threshold:
```
wait_dbc_signal(
  dbc_file_path="/var/lib/plotune-nexus/dbc/network.dbc",
  message_name="BrakePressure",
  signal_name="FrontLeft",
  operator="gt",
  timeout_seconds=5.0,
  channel="can0",
  interface="socketcan",
  value=50.0,
  hold_time_seconds=0.2
)
```

## Send A Single Frame

```
send_can_frame(
  channel="can0",
  arbitration_id="0x200",
  data_hex="0102030405060708",
  interface="socketcan",
  is_extended_id=False,
  lease_session_id="<session-id-if-leased>"
)
```

CAN FD (only on interfaces with `fd_enabled: true` or virtual backend):
```
send_can_frame(
  channel="can0",
  arbitration_id="0x200",
  data_hex="0102030405060708090A0B0C",
  interface="socketcan",
  is_fd=True,
  bitrate_switch=True,
  lease_session_id="<session-id-if-leased>"
)
```

Confirm with the user before sending any frame that actuates hardware or clears faults.

## Send A DBC Message By Signal Name

```
send_dbc_message(
  dbc_file_path="/var/lib/plotune-nexus/dbc/network.dbc",
  message_name="EngineControl",
  signal_values={"ThrottleRequest": 0.0, "EngineEnable": 0},
  channel="can0",
  interface="socketcan",
  lease_session_id="<session-id-if-leased>"
)
```

DBC file paths are Nexus-device paths. Strip any `/host/` prefix if reusing an artifact metadata path.

## Send A Periodic Frame

```
send_periodic_can_frame(
  channel="can0",
  arbitration_id="0x700",
  data_hex="0000000000000000",
  period_seconds=0.02,
  max_runtime_seconds=60.0,
  interface="socketcan",
  session_id="<session-id>",
  lease_session_id="<session-id>"
)
```

Stop explicitly when done — do not leave periodic frames running:
```
stop_periodic_can_frame(handle_id="<returned-handle-id>")
```

## Gateway (Bridge Two Interfaces With Allowlist)

Confirm with the user before starting. The gateway runs until stopped or until `max_runtime_seconds` expires.

```
start_can_gateway(
  source_interface="can0",
  destination_interface="vcan0",
  source_to_destination_rules=[
    {"rule_id": "forward-200", "arbitration_id": 0x200},
    {"rule_id": "forward-201", "arbitration_id": 0x201}
  ],
  bus_interface="socketcan",
  max_runtime_seconds=300.0
)
```

Each gateway rule must include a stable `rule_id`; forwarded/drop counters and error details reference that ID.
Gateway start/status responses expose the `job_id` and counters but redact the internal managed CAN lease session ID.

Monitor (check `forwarded_frame_count`, `dropped_frame_count`):
```
get_can_gateway(job_id="<gateway-job-id>")
```

Stop:
```
stop_can_gateway(job_id="<gateway-job-id>")
```

## Step 4 — Release And Clean Up

After any active work:
```
release_can_interface(interface_name="can0", session_id="<session-id>")
stop_periodic_can_frame(handle_id)    # if periodic frames were started
stop_can_gateway(job_id)             # if a gateway was started
detach_usb_can(interface_name, lease_session_id="<session-id-if-leased>")  # if a USB CAN adapter was attached
delete_can_interface(interface_name) # if virtual CAN was created for this task
```

## Notes

- CAN FD transmit requires `fd_enabled: true` in interface metadata or the `virtual` backend. Confirm from runtime — do not assume from the interface name.
- DBC file paths are Nexus-device paths. Strip `/host/` prefix if reusing artifact metadata paths.
- Gateways are allowlist-only CAN forwarding jobs — not generic network or serial bridges.
- After capturing a recording artifact, get the path with `get_artifact_metadata_tool`, then run the offline CAN trace summarizer if needed.
