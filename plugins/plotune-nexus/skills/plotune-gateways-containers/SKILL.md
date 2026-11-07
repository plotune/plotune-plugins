---
name: plotune-gateways-containers
description: Use when working with Plotune Nexus policy CAN gateways, managed OCI container images, staged container artifact import, granting CAN or serial access to containers, monitoring gateway forwarding counters, or stopping gateways and containers.
---

# Plotune Nexus Gateways And Containers

Gateways and containers directly affect hardware traffic. Both require explicit user confirmation before starting.

## CAN Gateway

A CAN gateway bridges two CAN interfaces with an allowlist filter. It is not a generic network or serial bridge.

### Step 1 — Confirm Interfaces Are Ready

```
read resource: plotune://device/interfaces
read resource: plotune://device/context
```

Confirm:
- Source and destination interfaces both have `state: up`
- Neither interface is already held by a gateway (`active_gateways` in context)
- No unintended leases exist on either interface

### Step 2 — Ask For Confirmation

Tell the user:
- Source interface and destination interface
- Which frame IDs will be forwarded (allowlist)
- Maximum runtime
- Whether bidirectional forwarding is enabled

### Step 3 — Start The Gateway

```
start_can_gateway(
  source_interface="can0",
  destination_interface="vcan0",
  source_to_destination_rules=[
    {"rule_id": "forward-200", "arbitration_id": 0x200},
    {"rule_id": "forward-201", "arbitration_id": 0x201},
    {"rule_id": "masked-300", "arbitration_id": 0x300, "data_mask_hex": "FF00000000000000"}
  ],
  destination_to_source_rules=None,
  bus_interface="socketcan",
  max_runtime_seconds=300.0,
  metadata={"purpose": "ECM monitoring bridge"}
)
```

Rules are allowlist-only and every rule must include a stable `rule_id` for logs and counters. Frames not matching any rule are dropped. An empty rules list drops all frames from that direction.
Gateway start/status responses expose the `job_id` and counters but redact the internal managed CAN lease session ID.

### Step 4 — Monitor

Check forwarded and dropped frame counts:
```
get_can_gateway(job_id="<gateway-job-id>")
```

Key fields: `forwarded_frame_count`, `dropped_frame_count`, `source_to_destination_forwarded_count`, `destination_to_source_forwarded_count`.

### Step 5 — Stop

```
stop_can_gateway(job_id="<gateway-job-id>", wait_timeout_seconds=1.0)
```

Always stop the gateway explicitly. Do not leave it running after the task.

---

## Managed Containers

Containers run OCI images staged as tar artifacts on the Nexus device. They can be granted access to CAN interfaces, serial devices, host PTYs, and managed volumes.

### Step 1 — Import The Container Image (If Not Already Staged)

Build the OCI image tar off-device, then import it as a two-phase artifact:

**Prepare:**
```
prepare_put_artifact(
  file_name="my-simulator.tar",
  size=<file-size-bytes>,
  sha256="<sha256-hex>",
  content_type="application/octet-stream",
  folder_name="containers"
)
```

**Upload bytes to the returned `upload_url` (outside MCP, e.g. `curl --upload-file my-simulator.tar "<upload_url>"`).** Tars go straight to the device at any size; send tars over 64 MiB in `Content-Range` pieces when connected through the tunnel (see the tool contracts).

**Confirm import:**
```
put_artifact(transfer_id="<transfer-id>")
```

Keep the returned artifact ID — it is the `artifact_id` for `start_container`.

### Step 2 — Ask For Confirmation

Tell the user:
- Container name and image artifact ID
- Which CAN interfaces will be attached (`can_interfaces`)
- Which serial devices will be attached (`serial_devices`)
- Network mode (`none`, `host`, or a specific network)
- Whether host PTYs are shared (`share_host_ptys`)
- Maximum runtime

### Step 3 — Start The Container

```
start_container(
  name="ecm-simulator",
  artifact_id="<container-artifact-id>",
  command=None,
  args=["--config", "/app/config.json"],
  env={"LOG_LEVEL": "debug"},
  volumes=[{"name": "data", "mount_path": "/app/data"}],
  can_interfaces=["can0", "vcan0"],
  serial_devices=["/dev/ttyUSB0"],
  share_host_ptys=False,
  network_mode="none",
  max_runtime_seconds=600.0,
  metadata={"purpose": "ECM simulation for bench test"}
)
```

### Step 4 — Monitor

```
get_container_status(container_id_or_name="ecm-simulator")
```

Check `status` field: `running`, `exited`, `stopped`. Inspect `finished_at` and exit code when the container stops.

### Step 5 — Stop

```
stop_container(container_id_or_name="ecm-simulator", wait_timeout_seconds=1.0)
```

Always stop the container explicitly after the task. A container left running continues consuming CAN interface leases and serial device slots.

## Notes

- Gateways are CAN-only allowlist-driven forwarding jobs. They do not bridge UART, Ethernet, or other protocols.
- Container image paths and artifact IDs are device-local Nexus resources.
- Simulations often use `network_mode="host"` and explicit `can_interfaces`. Confirm these requirements from the simulator documentation or artifact metadata before granting access.
- `share_host_ptys=True` exposes host PTY devices to the container. Only enable this for simulators that create virtual serial ports for other workflows to consume.
