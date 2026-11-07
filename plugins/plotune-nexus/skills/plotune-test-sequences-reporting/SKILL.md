---
name: plotune-test-sequences-reporting
description: Use when designing Plotune Nexus run_test_sequence definitions, converting manual tool choreography into managed steps, monitoring sequence job status, gathering test evidence, or writing technical reports from Nexus artifacts.
---

# Plotune Nexus Test Sequences And Reporting

Use managed test sequences when a scenario has ordered steps, overlapping recordings, timed waits, and evidence requirements. A sequence runs on the device and coordinates all steps atomically.

## When To Use A Sequence

Use `run_test_sequence` instead of individual tool calls when:
- Multiple recordings must start and stop in a defined order
- A wait condition must gate a subsequent action
- Evidence must be collected and linked to specific steps
- Steps must have stable IDs for traceability

For simple one-step capture or single-request diagnostics, use the relevant workflow skill directly.

## Step 1 — Read Runtime State

```
read resource: plotune://device/context
read resource: plotune://device/interfaces
read resource: plotune://artifacts/recent
read resource: plotune://notes/context
```

Confirm that required interfaces are `up`, no conflicting jobs or gateways are running, and any required A2L, LAB, or DBC files are available.
Check recent notes for setup changes, failed tests, linked artifacts, or operator observations that should affect the sequence plan.

## Step 2 — Design The Sequence

Model your scenario as an ordered list of steps. Each step has a unique `id`, a `type`, and type-specific parameters.

**Sequence definition structure:**
```json
{
  "recordings": [
    {
      "id": "can-cold-start",
      "protocol": "can",
      "channel": "can0",
      "interface": "socketcan",
      "duration_seconds": 60
    },
    {
      "id": "xcp-cold-start",
      "protocol": "xcp",
      "lab_file_path": "/var/lib/plotune-nexus/lab/measurements.lab",
      "a2l_file_path": "/var/lib/plotune-nexus/a2l/ECM.a2l",
      "channel": "can0",
      "interface": "socketcan",
      "duration_seconds": 60,
      "artifact_format": "mf4"
    }
  ],
  "steps": [
    {
      "id": "start-can-recording",
      "type": "start_recording",
      "target": {
        "kind": "recording",
        "recording_id": "can-cold-start"
      }
    },
    {
      "id": "start-xcp-recording",
      "type": "start_recording",
      "target": {
        "kind": "recording",
        "recording_id": "xcp-cold-start"
      }
    },
    {
      "id": "wait-for-rpm-signal",
      "type": "wait_dbc_signal",
      "target": {
        "kind": "dbc_signal",
        "dbc_file_path": "/var/lib/plotune-nexus/dbc/network.dbc",
        "message_name": "EngineStatus",
        "signal_name": "RPM",
        "channel": "can0",
        "interface": "socketcan"
      },
      "condition": {
        "operator": ">",
        "value": 500.0
      },
      "timeout_seconds": 30
    },
    {
      "id": "read-dtcs",
      "type": "send_uds_request",
      "target": {
        "transport": "can_isotp",
        "channel": "can0",
        "tx_id": "7E0",
        "rx_id": "7E8",
        "addressing_mode": "normal"
      },
      "request_hexes": ["190201"],
      "timeout_seconds": 2.0
    },
    {
      "id": "stop-can-recording",
      "type": "stop_recording",
      "target": {
        "kind": "recording",
        "recording_id": "can-cold-start"
      }
    },
    {
      "id": "stop-xcp-recording",
      "type": "stop_recording",
      "target": {
        "kind": "recording",
        "recording_id": "xcp-cold-start"
      }
    }
  ],
  "metadata": {
    "scenario": "ECM Cold Start Validation",
    "description": "Record CAN and XCP during cold start, then send a diagnostic request"
  }
}
```

### DDS recordings, publishes, waits, and ramps

DDS scenarios use the same shape. Declare a `dds` recording resource and drive it with
`dds_record_start` / `dds_record_stop`; publish with `dds_publish`; gate with `dds_wait`;
linearly ramp a numeric field over time with `dds_ramp`.
For cross-machine simulators, start with a `dds_join_session` step that binds the Nexus bench
interface and lists the publisher IP as a peer; reference that session by `session_name` from DDS
steps and recording resources. Do not rely on a DDS recording resource's `cyclonedds_uri` field:
the current sequence recording path does not forward it to its participant — see
[[plotune-dds-workflows]].

```json
{
  "recordings": [
    {
      "id": "vehicle-speed",
      "protocol": "dds",
      "topic_name": "/vehicle/speed",
      "type_name": "std_msgs/msg/Float32",
      "domain_id": 0,
      "session_name": "bench",
      "duration_seconds": 60,
    }
  ],
  "steps": [
    { "id": "join-dds", "type": "dds_join_session", "name": "bench", "domain_id": 0,
      "cyclonedds_uri": "<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\"enp4s0f1\" multicast=\"default\"/></Interfaces></General><Discovery><Peers><Peer address=\"192.168.1.116\"/></Peers></Discovery></Domain></CycloneDDS>" },
    { "id": "rec-speed", "type": "dds_record_start", "recording_id": "vehicle-speed" },
    { "id": "wait-30kph", "type": "dds_wait", "topic": "/vehicle/speed", "field": "data",
      "operator": ">=", "value": 8.3, "domain_id": 0, "session_name": "bench", "timeout_seconds": 30 },
    { "id": "stop-speed", "type": "dds_record_stop", "recording_id": "vehicle-speed" },
    { "id": "leave-dds", "type": "dds_leave_session", "session_name": "bench" }
  ]
}
```

**`dds_ramp` — linearly sweep a numeric DDS field** without crafting dozens of publish+wait steps.
Publishes `{field: value}` at each step period, interpolating from `start_value` to `value` over
`duration_seconds`. Respects sequence cancellation at every step boundary.

```json
{
  "id": "throttle-up",
  "type": "dds_ramp",
  "topic": "/vehicle/throttle_request",
  "field": "data",
  "type_name": "std_msgs/msg/Float32",
  "start_value": 0.0,
  "value": 1.0,
  "duration_seconds": 30,
  "step_period_seconds": 0.1,
  "domain_id": 0
}
```

Use `dds_ramp` for open-loop profiles (throttle sweep, brake application, steering angle sweep).
**If the scenario requires feedback control** — tracking a target speed, PID, or closed-loop ramp
— use a controller container instead (see next section).

### Choosing between `dds_ramp` and a controller container

| Scenario | Use |
|---|---|
| Sweep a command from A to B over T seconds (open loop) | `dds_ramp` step |
| Track a target (speed, temperature, torque) with feedback | Controller container |
| Multi-phase profile with > ~15 publish/wait steps | Controller container |
| Closed-loop maneuver (PID, bang-bang, model-based) | Controller container |

**Rule of thumb:** if your sequence has more than ~15 steps, or any step depends on the *measured
response* of a previous publish (not just a fixed wait), deploy a controller container instead.

### Controller-driven dynamic tests (closed loop)

When the plant must be *driven* through a profile that requires feedback — a closed-loop ramp,
a PID speed hold, a drive cycle — do not script the actuation step-by-step inside the sequence.
Deploy a controller container that closes the loop and let the sequence record its effect.
The controller runs on the Nexus while the simulator/plant runs on the bench host; build and
deploy it per [[plotune-controller-simulations]] and [[plotune-gateways-containers]].

Pattern:
1. `start_container(...)` the controller (host networking, `CYCLONEDDS_URI`, `--scenario ...`) — a
   managed container, started *before* the sequence, not a sequence step.
2. **Start the DDS recording first** and give peer discovery a few seconds before the controller
   engages, so the leading phase of the feedback signal is captured.
3. Optionally add `dds_wait` steps to assert the profile was tracked (e.g. speed reached the hold
   target, then returned to zero) as pass/fail gates.
4. `stop_container(...)` when the cycle completes.

The recorded feedback + command topics (e.g. `/vehicle/speed`, `/vehicle/throttle_request`,
`/vehicle/brake_request`) in one MCAP are the evidence for the dynamic test.

## Step 3 — Run The Sequence

```
run_test_sequence(definition=<sequence-dict-above>)
```

Returns a `job_id`. The sequence manages all step execution on the device.
When sequence CAN/XCP resources or CAN/DBC/UDS/XCP targets use a leased SocketCAN channel, include the owning CAN lease `session_id` as `lease_session_id` on that resource or target.

## Step 4 — Monitor

Wait for terminal state (completed, failed, cancelled):
```
wait_for_test_sequence(job_id="<job-id>", timeout_seconds=120.0)
```

Or poll with status tools during long sequences:
```
get_test_sequence(job_id="<job-id>")
```

Once terminal, get the requirement verdict (PASS/FAIL + per-check measured/expected/margin + evidence) instead of hand-synthesising it from raw step results:
```
get_test_sequence_verdict(job_id="<job-id>")
```

Check the response for:
- `status` — `running`, `completed`, `failed`, `cancelled`
- `steps` — per-step status, output, and artifact IDs
- `failed_step` — which step caused a failure and why

Recording jobs started by a sequence that ends early may appear as `cancelled` — this is correct when the sequence closed them intentionally.

## Step 5 — Cancel If Needed

```
cancel_test_sequence(job_id="<job-id>")
```

## Step 6 — Collect Evidence

From the sequence result, gather:
- Step artifact IDs (recordings, UDS responses)
- Per-step terminal status
- Any wait-condition results (the value that satisfied or timed out the condition)

Get artifact paths for downstream analysis:
```
get_artifact_metadata_tool(artifact_id="<artifact-id-from-step>")
```

If requirements or test records are available locally, run traceability checks:
```bash
python3 scripts/automotive/requirements_trace_lint.py --requirements path/to/requirements.md --tests path/to/tests.csv --format json
python3 scripts/automotive/evidence_pack.py --inputs path/to/report.json path/to/capture.log --classification bench --format json
```

## Step 7 — Write The Report

A complete Nexus test report includes:

| Section | Content |
|---|---|
| Request | What was asked and by whom |
| Pre-action state | Resources read, active jobs/gateways before the sequence |
| Sequence definition | Step IDs, types, targets, and bounds |
| Execution result | Job ID, terminal status, per-step results |
| Evidence | Artifact IDs, paths, sizes, and formats |
| Diagnostic details | NRCs, wait outcomes, signal values — raw, not summarized |
| Post-action cleanup | What was stopped, released, or deleted |
| Open items | Remaining risks, retest conditions, or unresolved steps |

After the report, preserve short device-local context for the next operator or agent:

```
write_note(
  body_markdown="Cold start validation failed at wait-for-rpm-signal; RPM stayed below 500 before timeout.",
  links=[
    {"kind": "file", "target_id": "<artifact-id>", "label": "cold-start.asc"},
    {"kind": "channel", "target_id": "can0", "label": "can0"}
  ]
)
```

Use `search_notes(query="<symptom-or-test-name>", linked_only=True)` before reruns to find prior observations linked to artifacts, channels, or interfaces.

## Notes

- Step IDs are stable identifiers for traceability. Use meaningful names like `"read-engine-dtcs"` rather than `"step-1"`.
- A sequence that completes with a failed step returns `status: failed`. Inspect `failed_step` to understand the root cause before recommending a retry.
- Sequences that run recordings coordinate stop timing internally. Do not manually stop recordings that are part of a running sequence unless the sequence itself has failed.
- Use `run_test_sequence` for integration test scenarios. For iterative development and debugging, use individual CAN, XCP, and UDS workflow skills to build and validate each step first.
- Notes are concise device context, not issue tracking. Link them to artifacts, channels, or interfaces when that helps future troubleshooting.
