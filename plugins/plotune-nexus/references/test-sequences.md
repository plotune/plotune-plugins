# Test Sequences And Reporting Reference

## Lifecycle

Primary sequence tools:

- `run_test_sequence(definition)`
- `get_test_sequence(job_id)`
- `get_test_sequence_verdict(job_id)` — consolidated requirement verdict (PASS/FAIL + per-check measured/expected/margin + evidence artifact IDs)
- `wait_for_test_sequence(job_id, ...)`
- `cancel_test_sequence(job_id)`

Sequence execution is ordered, but recordings started by a sequence can run asynchronously while later steps continue.

Before using a target shape that is not shown here, inspect the live `run_test_sequence` schema or load a live Nexus skill with `get_skill(...)`. Stop and ask rather than guessing step fields for active control, flash, or programming.

## Definition Shape

Top-level shape:

```json
{
  "recordings": [],
  "steps": [],
  "timeouts": {},
  "metadata": {}
}
```

Use `metadata` for human-facing names, scenario labels, requirement IDs, source systems, and n8n workflow references. The executable shape is defined by `recordings`, `steps`, and optional `timeouts`.

`recordings` is a list. Each recording has a `protocol` discriminator such as `can`, `xcp`, or `uart`.

Every step should have:

- stable `id`
- `type`
- `target`
- explicit timeout or duration when the action waits or runs
- stable evidence expectations when a diagnostic or wait condition gates later work

Common step types:

- `start_recording`
- `stop_recording`
- `set_value`
- `ramp_value`
- `wait_measurement`
- `wait_duration`
- `send_can_frame`
- `wait_can_frame`
- `send_uds_request`
- `send_dbc_message`
- `wait_dbc_signal`
- `open_uart_session`
- `close_uart_session`
- `send_uart`
- `wait_uart`
- `flash_artifact`

## Target Guidance

Prefer abstract targets when possible:

- `xcp_calibration`
- `xcp_measurement`
- `dbc_signal`
- `dbc_message`
- `uds_request`

Use raw `can_frame` and `can_frame_match` for debugging or when no semantic model exists.

For active XCP session reuse, declare an XCP recording, start it, and pass `recording_id` on XCP targets that should reuse the active session.

For `send_uds_request` steps:

- use `request_hexes` for ordered raw UDS payloads
- use `wait_for_response=false` only when the sequence should continue without waiting for ECU replies
- use `expectations` when the sequence needs to assert a response outcome, service ID, or exact response payload

Example UDS gate step:

```json
{
  "id": "read-vin",
  "type": "send_uds_request",
  "target": {
    "kind": "uds_request",
    "channel": "vcan0",
    "tx_id": "7E0",
    "rx_id": "7E8"
  },
  "request_hexes": ["22F190"],
  "expectations": [
    {
      "outcome": "positive_response",
      "response_service_id": "62"
    }
  ]
}
```

For UART steps, open the named session before send/wait and close it after use:

```json
{
  "steps": [
    {
      "id": "open-console",
      "type": "open_uart_session",
      "target": {
        "kind": "uart_session",
        "session_name": "console",
        "device_path": "/dev/ttyUSB0",
        "baud_rate": 115200
      }
    },
    {
      "id": "send-boot",
      "type": "send_uart",
      "target": {
        "kind": "uart",
        "session_name": "console",
        "mode": "text"
      },
      "value": "AT+BOOT"
    },
    {
      "id": "wait-ready",
      "type": "wait_uart",
      "target": {
        "kind": "uart",
        "session_name": "console",
        "mode": "text"
      },
      "condition": {
        "operator": "contains",
        "value": "READY"
      },
      "timeout_seconds": 5.0
    },
    {
      "id": "close-console",
      "type": "close_uart_session",
      "target": {
        "kind": "uart_session",
        "session_name": "console"
      }
    }
  ]
}
```

For artifact-backed flash steps, use `flash_artifact` only with explicit user approval and artifact segment metadata:

```json
{
  "id": "flash-uds",
  "type": "flash_artifact",
  "protocol": "uds",
  "target": {
    "transport": "can_isotp",
    "channel": "can0",
    "tx_id": "7E0",
    "rx_id": "7E8"
  },
  "segments": [
    {
      "artifact_id": "artifact-app.bin",
      "address": "0x80128000",
      "size_bytes": 4096,
      "offset_bytes": 0
    }
  ]
}
```

XCP flash steps use `protocol="xcp"` and an A2L-backed target. PROGRAM mode adds an `xcp` block with `mode`, `program_prepare`, `program_format`, optional `program_verify`, and optional `program_reset`. Report partial segment failures with bytes transferred and recovery guidance.

## Reporting

Summaries should include:

- scenario intent
- resources read before action
- interfaces or leases used
- sequence/job IDs
- terminal statuses
- key step evidence
- artifact IDs and paths
- cleanup performed
- unresolved risks or rerun conditions

When `stop_recording` ends a recording before its natural duration, the underlying recording job can show `cancelled` while the sequence treats the recording as closed and the artifact as valid. Do not treat that status alone as a failure.

## Working Example

```json
{
  "recordings": [
    {
      "id": "vcan-capture",
      "protocol": "can",
      "channel": "vcan0",
      "interface": "socketcan",
      "duration_seconds": 30
    }
  ],
  "steps": [
    {
      "id": "start-capture",
      "type": "start_recording",
      "target": {
        "kind": "recording",
        "recording_id": "vcan-capture"
      }
    },
    {
      "id": "dwell",
      "type": "wait_duration",
      "target": {
        "kind": "duration"
      },
      "duration_seconds": 2.0
    },
    {
      "id": "stop-capture",
      "type": "stop_recording",
      "target": {
        "kind": "recording",
        "recording_id": "vcan-capture"
      }
    }
  ],
  "metadata": {
    "scenario": "bounded-capture-proof"
  }
}
```
