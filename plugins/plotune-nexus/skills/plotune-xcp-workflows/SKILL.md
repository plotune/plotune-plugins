---
name: plotune-xcp-workflows
description: Use when working with Plotune Nexus XCP measurement recording, A2L or LAB artifact selection, calibration read or write, active-job calibration reuse, STIM signal injection, Seed and Key security unlock, or choosing between CAN and UDP XCP transports.
---

# Plotune Nexus XCP Workflows

XCP work is artifact-backed and transport-explicit. Always locate A2L and LAB files before building tool calls.

## Step 1 — Read Runtime State

```
read resource: plotune://device/interfaces
read resource: plotune://device/context
read resource: plotune://artifacts/recent
```

From interfaces: confirm the CAN interface is `up` and CAN XCP is viable.
From context: check if an XCP recording job is already running — reuse it with job-scoped calibration tools rather than opening a second XCP master.
From recent artifacts: find A2L and LAB file artifact IDs.

## Step 2 — Locate A2L And LAB Files

List artifacts to find A2L and LAB files:
```
list_artifacts_tool()
```

Get the device-local path:
```
get_artifact_metadata_tool(artifact_id="<id>")
```

Strip any `/host/` prefix from the returned path before using it in XCP tools:
```
/host/var/lib/plotune-nexus/a2l/ECM.a2l  →  /var/lib/plotune-nexus/a2l/ECM.a2l
```

If A2L and LAB files are available on the workstation, run offline checks first:
```bash
python3 scripts/automotive/a2l_lab_check.py --a2l path/to/ECM.a2l --lab path/to/measurements.lab --format json
python3 scripts/automotive/xcp_daq_plan.py --a2l path/to/ECM.a2l --lab path/to/measurements.lab --format json
```

## Step 3 — Choose Transport

| Condition | Transport | Key parameters |
|---|---|---|
| A2L has `XCP_ON_CAN` and a CAN interface is available | `transport="can"` | `channel="can0"`, `interface="socketcan"` |
| A2L has `XCP_ON_ETH` or user provides host/port | `transport="udp"` | `host="<ecu-ip>"`, `port=13400` |

## Step 4 — XCP Recording

Start a bounded recording job:
```
record_xcp(
  lab_file_path="/var/lib/plotune-nexus/lab/measurements.lab",
  a2l_file_path="/var/lib/plotune-nexus/a2l/ECM.a2l",
  channel="can0",
  duration_seconds=30.0,
  interface="socketcan",
  event_channel=0,
  artifact_format="mf4",
  lease_session_id="<session-id-if-leased>"
)
```

`artifact_format`: `"mf4"` (standard MDF4, default) or `"xmraw"` (raw XCP frames, requires DAQ hardware support).

Wait for completion:
```
wait_for_job(job_id="<returned-job-id>", timeout_seconds=45.0)
```

Inspect the result and artifact path:
```
get_record_xcp(job_id="<job-id>")
```

Stop early:
```
stop_record_xcp(job_id="<job-id>")
```

## Step 5 — Calibration Read

```
read_xcp_calibration(
  a2l_file_path="/var/lib/plotune-nexus/a2l/ECM.a2l",
  calibration_name="IdleSpeed",
  channel="can0",
  interface="socketcan",
  transport="can",
  lease_session_id="<session-id-if-leased>"
)
```

For Ethernet XCP:
```
read_xcp_calibration(
  a2l_file_path="/var/lib/plotune-nexus/a2l/ECM.a2l",
  calibration_name="IdleSpeed",
  transport="udp",
  host="192.168.1.50",
  port=13400
)
```

## Step 6 — Calibration Write

Requires explicit user confirmation before calling.

Scalar value:
```
set_xcp_calibration(
  a2l_file_path="/var/lib/plotune-nexus/a2l/ECM.a2l",
  calibration_name="IdleSpeed",
  value=850.0,
  channel="can0",
  interface="socketcan",
  transport="can",
  lease_session_id="<session-id-if-leased>"
)
```

Array value:
```
set_xcp_calibration(
  a2l_file_path="/var/lib/plotune-nexus/a2l/ECM.a2l",
  calibration_name="SpeedTable",
  value=[0.0, 500.0, 1000.0, 2000.0],
  channel="can0",
  interface="socketcan",
  transport="can",
  lease_session_id="<session-id-if-leased>"
)
```

After writing, run a diff against a baseline if you have one:
```bash
python3 scripts/automotive/calibration_diff.py --base path/to/baseline.json --candidate path/to/new.json --format json
```

## Step 7 — Reuse An Active Recording Job For Calibration

When an XCP recording is already running, avoid opening a second master. Use job-scoped tools:
```
read_xcp_job_calibration(job_id="<recording-job-id>", calibration_name="IdleSpeed", timeout_seconds=5.0)

set_xcp_job_calibration(job_id="<recording-job-id>", calibration_name="IdleSpeed", value=850.0, timeout_seconds=5.0)
```

## Step 8 — STIM (Signal Injection)

Requires explicit user confirmation. Use a list of signal name and value pairs:
```
stim_xcp_signals(
  a2l_file_path="/var/lib/plotune-nexus/a2l/ECM.a2l",
  stimulations=[
    {"name": "PedalPosition", "value": 0.5},
    {"name": "BrakeRequest", "value": 0.0}
  ],
  duration_seconds=10.0,
  stim_interval_seconds=0.01,
  channel="can0",
  interface="socketcan",
  transport="can",
  lease_session_id="<session-id-if-leased>"
)
```

## Step 9 — Seed And Key Security Unlock

Seed+Key is a stateful two-step flow. Keep session and transport stable throughout.

Step 1 — get the seed for the protected resource:
```
xcp_get_seed(
  resource="PGM",
  a2l_file_path="/var/lib/plotune-nexus/a2l/ECM.a2l",
  channel="can0",
  interface="socketcan",
  transport="can",
  ttl_seconds=30.0,
  lease_session_id="<session-id-if-leased>"
)
```

The response contains `session_id` and `seed_hex`. Compute the key with your key-generation logic, then unlock:
```
xcp_unlock(session_id="<returned-session-id>", key_hex="<computed-key-hex>")
```

## Notes

- A2L byte order matters. If the tool reports an unsupported or missing byte-order field, fix the A2L metadata — do not guess the byte order.
- Calibration values are scalars or arrays depending on the A2L characteristic type. Check the A2L before passing a value.
- When using XCP on SocketCAN and the CAN interface is leased, pass the same session ID as `lease_session_id`.
- Seed+Key sessions are stateful. Do not switch transport, channel, or interface between `xcp_get_seed` and `xcp_unlock`.
- Do not run heavy offline A2L processing on the device MCP surface — export artifacts and process them on the workstation.
