---
name: plotune-uds-doip-diagnostics
description: Use when working with Plotune Nexus raw UDS over CAN ISO-TP or DoIP, DoIP vehicle discovery, DoIP target leases, DTC read or clear, RDBI/WDBI, RoutineControl, ECU reset, SecurityAccess, flashing, diagnostic NRCs, or response-pending behavior.
---

# Plotune Nexus UDS And DoIP Diagnostics

## Step 1 — Read Diagnostic Resources

Always start with these four resources before any UDS work:

```
read resource: plotune://diagnostics/uds/transports
read resource: plotune://diagnostics/uds/recent
read resource: plotune://diagnostics/uds/doip-leases
read resource: plotune://settings/hardware
```

From `transports`: which UDS transports are `available_now` vs. planned only? Nexus ships CAN ISO-TP and outbound DoIP. Do not assume a transport is available without checking this.

From `recent`: prior UDS exchanges give addressing hints and confirm the ECU responded before.

From `doip-leases`: active leases mean another session is already working with a DoIP target. Owner session IDs are redacted; keep the session ID returned by your own acquire call and coordinate before acquiring another lease to the same ECU.

From `hardware settings`: check `doip_discovery` candidate paths when choosing `interface_name` or `source_address` for multi-NIC benches.

## Step 2 — Choose Transport

| Condition | Transport | Target shape |
|---|---|---|
| CAN bus available, ECU uses ISO-TP | `can_isotp` | See CAN target below |
| ECU accessible via Ethernet, DoIP stack running | `doip` | See DoIP target below |

**CAN ISO-TP target:**
```json
{
  "transport": "can_isotp",
  "channel": "can0",
  "tx_id": "7E0",
  "rx_id": "7E8",
  "addressing_mode": "normal"
}
```

**DoIP target:**
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

Use `source_address` or `interface_name` in the DoIP target when the bench has multiple NICs and you need path-stable diagnostics:
```json
{
  "transport": "doip",
  "host": "192.168.0.10",
  "port": 13400,
  "tester_logical_address": "0E00",
  "ecu_logical_address": "0001",
  "interface_name": "eth0"
}
```

## Step 3 — DoIP: Discover And Lease (DoIP Only)

**Discover vehicles on the network:**
```
discover_doip_vehicles(
  interface_name="eth0",
  timeout_seconds=1.5,
  port=13400,
  max_results=20,
  address_family="auto"
)
```

**Acquire a DoIP target lease before any active diagnostic work:**
```
acquire_doip_target_lease(
  target={"transport": "doip", "host": "192.168.0.10", "port": 13400, "tester_logical_address": "0E00", "ecu_logical_address": "0001"},
  agent_id="<agent-id>",
  session_id="<unique-session-id>",
  purpose="DTC read and clear"
)
```

Pass the same `session_id` as `lease_session_id` on every `send_uds_request` call for this target.
For CAN ISO-TP targets, pass the owning CAN interface lease `session_id` as `lease_session_id` when the SocketCAN channel is leased.

## Step 4 — Send UDS Requests

**Read DTC summary (0x19 0x02 with status mask 0xFF):**
```
send_uds_request(
  target={"transport": "can_isotp", "channel": "can0", "tx_id": "7E0", "rx_id": "7E8", "addressing_mode": "normal"},
  request_hexes=["190201"],
  timeout_seconds=2.0,
  lease_session_id="<session-id-if-can0-is-leased>"
)
```

**Read data by identifier (0x22 for DID F190 — VIN):**
```
send_uds_request(
  target={"transport": "can_isotp", "channel": "can0", "tx_id": "7E0", "rx_id": "7E8", "addressing_mode": "normal"},
  request_hexes=["22F190"],
  timeout_seconds=2.0,
  lease_session_id="<session-id-if-can0-is-leased>"
)
```

**Extended diagnostic session (0x10 0x03) followed by DID read:**
```
send_uds_request(
  target={"transport": "doip", "host": "192.168.0.10", "port": 13400, "tester_logical_address": "0E00", "ecu_logical_address": "0001"},
  request_hexes=["1003", "22F190"],
  timeout_seconds=2.0,
  lease_session_id="<session-id-from-lease>"
)
```

**Slow routine — use `max_response_pending_wait_seconds` for NRC 0x78:**
```
send_uds_request(
  target={...},
  request_hexes=["3101FF0100"],
  timeout_seconds=5.0,
  max_response_pending_wait_seconds=30.0
)
```

Do not resend when you receive NRC 0x78 — this means the ECU is still processing. `max_response_pending_wait_seconds` extends the receive deadline without resending.

## Step 5 — NRC Handling

Preserve all NRCs and raw response bytes in your output. Do not collapse them into "no response" or "failed."

| NRC | Meaning | Action |
|---|---|---|
| 0x78 | Response pending | Increase `max_response_pending_wait_seconds` |
| 0x7F | Service not supported | Check which diagnostic session is active |
| 0x22 | Conditions not correct | Check ignition state or required prior step |
| 0x24 | Request sequence error | A prerequisite step was skipped |
| 0x25 | No response from subnet component | Network routing issue; check DoIP path |
| 0x31 | Request out of range | DID, RID, or block address is not valid for this ECU |
| 0x33 | Security access denied | SecurityAccess unlock required first |
| 0x35 | Invalid key | Wrong key in SecurityAccess; check key-generation logic |

Ask for confirmation before routines, resets, writes, flashing, or any action that changes ECU state.

## Step 6 — Release DoIP Lease

After diagnostic work is complete:
```
release_doip_target_lease(
  target={"transport": "doip", "host": "192.168.0.10", "port": 13400, "tester_logical_address": "0E00", "ecu_logical_address": "0001"},
  session_id="<session-id>"
)
```

## Offline Payload Verification

Before executing live sequences, validate payload bytes offline:
```bash
python3 scripts/automotive/uds_payload.py decode 7F2278 --format json
python3 scripts/automotive/uds_payload.py rdbi F190 F187 --format json
python3 scripts/automotive/uds_sequence_lint.py --sequence path/to/sequence.csv --format json
python3 scripts/automotive/odx_inspect.py --odx path/to/database.odx --format json
```

## Notes

- DoIP routing activation type is `default` unless the ECU spec requires a different type.
- Recent UDS history (`plotune://diagnostics/uds/recent`) is bounded context for support, not a full artifact archive.
- A timeout, NRC, or routing activation failure is diagnostic evidence. Report it precisely with the raw response bytes.
- CAN ISO-TP addressing mode is `normal` (11-bit) by default. Use `extended` when the ECU requires extended addressing.
