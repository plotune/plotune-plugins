---
name: plotune-dds-workflows
description: Use when working with Plotune Nexus DDS simulators, DDS topic publish/subscribe workflows, QoS profiles, domain IDs, managed DDS containers, network discovery, or DDS evidence capture.
---

# Plotune Nexus DDS Workflows

DDS operations run on the Nexus device and normally use the bench Ethernet network. Treat DDS traffic as an active test-bench signal source: inspect state first, bound every operation, and clean up when finished.

## Sessions

All DDS operations require a **named session** that holds a live `DomainParticipant`. The session caches writers and readers per topic — the first call to a topic waits for DDS discovery (~1.5 s), all subsequent calls on the same session use the cached objects immediately.

Join a session at the start of any workflow, leave it at the end:
```
join_dds_session(name="throttle-test", domain_id=10, cyclonedds_uri="<xml>")
→ { session_id: "<hex>", name: "throttle-test", ... }
```

```
leave_dds_session(session_id="<hex>")
```

Sessions expire automatically after 30 minutes of inactivity. The session `name` is human-readable and used for traceability. Pass `session_id` to every DDS data-plane tool call: `publish_dds_message`, `capture_dds_snapshot`, `wait_dds_signal`, and `record_dds_topics`. Topic and participant discovery are independent calls and accept `domain_id` and (when needed) `cyclonedds_uri`.

The session creates the long-lived participant and carries its `cyclonedds_uri`. The current tool surface still accepts an optional `domain_id` on data-plane calls; use the same domain as the joined session (or omit it only when `PLOTUNE_DDS_DOMAIN_ID` is that domain). Do not treat a session ID as proof that a conflicting per-call domain override was rejected.

## Network Binding (`cyclonedds_uri`)

Pass `cyclonedds_uri` to `join_dds_session` (not to individual tools) when the publisher or ECU runs on a **different machine**, or when either host has multiple interfaces (Ethernet, Wi‑Fi, Tailscale, container bridges). Without it CycloneDDS may bind the wrong interface or fall back to local-only mode, and discovery silently returns nothing.

Bind the Nexus's bench interface and point unicast discovery at the publisher's IP:
```
<CycloneDDS><Domain><General><Interfaces>
  <NetworkInterface name="<nexus-bench-iface>" multicast="default"/>
</Interfaces></General><Discovery><Peers>
  <Peer address="<publisher-ip>"/>
</Peers></Discovery></Domain></CycloneDDS>
```

The simulator side must likewise bind its LAN interface and list the Nexus IP as a peer. Both `domain_id` values must match.

## Step 1 — Read Runtime State

Start with:
```
read resource: plotune://device/context
read resource: plotune://device/interfaces
read resource: plotune://artifacts/recent
```

Then check:
- `get_runtime_capabilities_tool` for `dds_udp`, `dds_multicast`, `dds_middleware`, and `dds_ros2_distro`
- `get_tooling_health_tool` for `dds_middleware_available`, `dds_domain_reachable`, `dds_multicast_functional`, `mcap_support`, and `command:ros2`
- `list_dds_participants_tool(domain_id=<domain>, cyclonedds_uri="<xml-if-needed>")`
- `list_dds_topics_tool(domain_id=<domain>, cyclonedds_uri="<xml-if-needed>")`

Use a dedicated bench LAN such as `eth1` for live DDS multicast when available. `dds_middleware_available=ok` is the live data-plane gate: CycloneDDS Python bindings let Nexus discover, capture, record, wait, and publish DDS traffic from another device without ROS 2 installed on the Nexus device. `command:ros2` is optional and only indicates whether ROS 2 CLI diagnostics are available locally.

## Step 2 — Join A Session

Join a session before any DDS operation. Choose a descriptive `name` for traceability:
```
join_dds_session(
  name="speed-capture",
  domain_id=10,
  cyclonedds_uri="<xml-or-omit>"
)
→ { session_id: "<hex>", name: "speed-capture", joined_at: ... }
```

Leave when done:
```
leave_dds_session(session_id="<hex>")
```

## Step 3 — Discover Topics

```
list_dds_participants_tool(domain_id=10)
list_dds_topics_tool(domain_id=10)
```

Preserve topic names, type names, domain ID, QoS fields, timestamps, and participant IDs in notes or reports.

## Step 4 — Capture Or Record

Quick inline snapshot (pass `type_name` when known to skip discovery and capture immediately; it is required for a cross-machine unicast-peer subscription):
```
capture_dds_snapshot(
  topic_name="/vehicle/speed",
  type_name="std_msgs/msg/Float32",
  session_id="<hex>",
  duration_seconds=1.0,
  max_messages=20
)
```

Bounded recording — `record_dds_topics` records one **or many** topics into a **single MCAP artifact** (each topic is a separate channel). Pass a one-item list for a single topic, or several for a drive cycle (NEDC/WLTP) so speed, rpm, gear, etc. land in one file that can be analysed together:
```
record_dds_topics(
  topics=[
    {"topic_name": "/vehicle/speed", "type_name": "std_msgs/msg/Float32"},
    {"topic_name": "/vehicle/engine_rpm", "type_name": "std_msgs/msg/Float32"},
    {"topic_name": "/vehicle/gear", "type_name": "std_msgs/msg/Int8"}
  ],
  duration_seconds=30.0,
  domain_id=10,
  session_id="<hex>"
)
```

It returns **one job** (one `job_id`, one `artifact_path`). The result's `topics` field reports per-topic message counts; `messages_recorded` is the total. `type_name` is optional in a topic entry but should be supplied for live/cross-machine topics; the runtime fallback is `plotune_msgs/msg/Json`. Manage it with the **generic job tools** (DDS recordings flow through them):
```
wait_for_job(job_id="<job-id>", timeout_seconds=45.0)
get_job_status_tool(job_id="<job-id>")
cancel_job_tool(job_id="<job-id>")   # stop early
list_jobs_tool()
```

Expect `artifact_format="mcap"` when MCAP support is installed. Otherwise the tool returns `artifact_format="jsonl"` and writes an explicit JSONL fallback artifact. These artifacts capture the Nexus recording representation and receipt time; they are evidence for the run, not a claim of replay-grade ROS 2 bag capture for arbitrary message types.

If `capture_dds_snapshot` returns `message_count: 0` or `wait_dds_signal` times out with `sample_count: 0`, read the `hint` field on the result — it names the Nexus interfaces and gives a ready-to-paste `cyclonedds_uri` template plus the usual silent-failure checklist (type_name, domain_id match, publisher firewall).

## Step 5 — Wait For A Signal

```
wait_dds_signal(
  topic_name="/adas/object_list",
  field="count",
  operator=">",
  value=0,
  timeout_seconds=10.0,
  session_id="<hex>"
)
```

Use field paths such as `vehicle.speed` for nested JSON-like payloads. `wait_dds_signal` waits for fresh samples by default; set `include_existing=true` only when matching a sample deliberately published earlier in the same workflow.

## Step 6 — Publish Stimulus

Confirm with the operator before sending DDS messages that affect a HIL bench or DUT behavior.

A successful `publish_dds_message` result proves only that Nexus accepted and stored the message locally (and may have attempted a middleware write). It does **not** prove a remote subscriber matched or acted on it. For a safety-relevant command, publish a bounded one-shot or periodic stimulus, then independently verify the intended state on a separate feedback topic with `wait_dds_signal`; stop any periodic handle before leaving the session. Do not use remote periodic publishing as a timing-critical control loop.

Single message — omit `period_seconds` for a one-shot publish:
```
publish_dds_message(
  topic_name="/vehicle/throttle_request",
  type_name="std_msgs/msg/Float32",
  message={"data": 0.25},
  session_id="<hex>"
)
```

Periodic bounded stimulus — set `period_seconds` together with `max_runtime_seconds` on the same `publish_dds_message` tool. It then returns a periodic-job handle instead of a one-shot result:
```
publish_dds_message(
  topic_name="/vehicle/brake_request",
  type_name="std_msgs/msg/Float32",
  message={"data": 0.1},
  period_seconds=0.05,
  max_runtime_seconds=2.0,
  session_id="<hex>"
)
```

Cleanup:
```
stop_periodic_dds_message(handle_id="<handle-id>")
```

## Step 7 — Use DDS Simulators

Container-ready DDS simulators live under `simulations/`:
- `dds_vehicle_dynamics_simulation`
- `dds_sensor_fusion_simulation`
- `dds_ecu_shadow_simulation`

Build and stage them through the container artifact flow, then start with `network_mode="host"` and `args=["--domain-id", "<bench-domain>"]` on the external simulator device. The simulator entrypoints set `ROS_DOMAIN_ID` from `--domain-id`, so do not rely on an environment-only `ROS_DOMAIN_ID` override. Ask for confirmation before starting containers that emit network traffic.

Cleanup:
```
get_container_status(container_id_or_name="<name>")
stop_container(container_id_or_name="<name>")
```

## Step 8 — Mixed CAN + DDS Sequence

Use `run_test_sequence` when DDS waits or publishes must coordinate with CAN, XCP, UDS, or UART actions. Open a DDS session with `dds_join_session` as the first step; all subsequent DDS steps and recording resources reference it by `session_name`. The sequence closes sessions it owns during cleanup. For a cross-machine run, put `cyclonedds_uri` on `dds_join_session`; do not rely on the `cyclonedds_uri` field of a DDS recording resource, because the current sequence recording path does not forward that field to the joined participant.

```json
{
  "recordings": [
    {
      "id": "dds-speed",
      "protocol": "dds",
      "topic_name": "/vehicle/speed",
      "type_name": "std_msgs/msg/Float32",
      "domain_id": 10,
      "session_name": "bench",
      "duration_seconds": 30
    }
  ],
  "steps": [
    {
      "id": "join",
      "type": "dds_join_session",
      "name": "bench",
      "domain_id": 10,
      "cyclonedds_uri": "<xml-or-omit>"
    },
    {"id": "start-dds", "type": "dds_record_start", "recording_id": "dds-speed"},
    {
      "id": "wait-object",
      "type": "dds_wait",
      "topic": "/adas/object_list",
      "field": "count",
      "operator": ">",
      "value": 0,
      "timeout_seconds": 10.0,
      "session_name": "bench"
    },
    {
      "id": "publish-target-speed",
      "type": "dds_publish",
      "topic": "/vehicle/target_speed",
      "type_name": "std_msgs/msg/Float32",
      "message": {"data": 50.0},
      "session_name": "bench"
    },
    {"id": "stop-dds", "type": "dds_record_stop", "recording_id": "dds-speed"}
  ]
}
```

For CAN/DDS correlation patterns, also use `plotune-can-workflows` and `plotune-xcp-workflows`.

## Troubleshooting — Cross-Device Discovery Fails (firewall)

When the publisher runs on a separate machine and discovery/capture returns nothing **even with a correct `cyclonedds_uri`**, suspect a **host firewall on the publisher machine** before assuming a code or config problem. This is the single most common cause and is easy to miss: tools like `ufw`/`firewalld` need root to inspect, so they look "off" to a normal check while a default `INPUT DROP` policy is silently dropping inbound UDP.

The tell-tale signature: ICMP (ping) works and the publisher → Nexus direction works, but Nexus → publisher UDP is dropped. DDS needs **bidirectional** UDP, so discovery and the reliable handshake never complete.

You cannot run privileged commands on the operator's machine yourself. Ask the operator to run this on the **machine running the simulator/publisher** (it allows inbound UDP from the bench LAN and prints the resulting rules):
```
sudo iptables -I INPUT -p udp -s <bench-subnet>/24 -j ACCEPT && sudo iptables -S INPUT
```
For example, for a `192.168.1.0/24` bench: `sudo iptables -I INPUT -p udp -s 192.168.1.0/24 -j ACCEPT`. For a persistent rule, suggest the firewall's own front-end (e.g. `sudo ufw allow from <bench-subnet>/24 proto udp`). The bare `iptables -I` form is ephemeral and is lost on reboot.

To confirm the diagnosis is firewall-shaped (not routing), the operator can check that ping succeeds while a one-shot UDP probe to the publisher does not — asymmetry points squarely at inbound UDP filtering on the publisher host.
