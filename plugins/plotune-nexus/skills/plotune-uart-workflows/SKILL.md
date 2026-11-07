---
name: plotune-uart-workflows
description: Use when working with Plotune Nexus UART device inventory, opening managed serial sessions, sending or receiving data, recording UART sessions, using RS-485 half-duplex mode, controlling modem lines, or setting up PTY-backed serial simulations.
---

# Plotune Nexus UART Workflows

UART work uses managed sessions with explicit open and close. All paths are Nexus-device paths.

## Step 1 — Inventory UART Devices

```
read resource: plotune://device/interfaces
```

The `uart_serial_devices` array lists all serial devices. Check:
- `usage_status` — must be `available` to open a session
- `device_kind` — `usb-serial`, `tty`, `pty`, etc.
- `supports_slcan_attach` — if `true`, this adapter can be attached as a SLCAN CAN interface instead (use `attach_usb_can`; it also appears in `list_usb_can_adapters`)
- `is_readable` / `is_writable` — confirm device permissions

For more detail:
```
list_uart_devices()
```

## Step 2 — Open A Session

Open with explicit serial parameters:
```
open_uart_session(
  device_path="/dev/ttyUSB0",
  baud_rate=115200,
  data_bits=8,
  parity="none",
  stop_bits=1,
  flow_control="none",
  read_timeout_seconds=0.2,
  line_ending="\n",
  encoding="utf-8"
)
```

**RS-485 half-duplex mode** (RTS-controlled direction switching — only when the adapter and wiring require it):
```
open_uart_session(
  device_path="/dev/ttyUSB0",
  baud_rate=9600,
  data_bits=8,
  parity="none",
  stop_bits=1,
  flow_control="none",
  rs485_mode=True,
  rs485_delay_before_tx_seconds=0.001,
  rs485_delay_before_rx_seconds=0.001
)
```

Do not enable `rs485_mode` unless the hardware and wiring explicitly require half-duplex direction control.

The tool returns a `session_id` — use it in all subsequent calls.

## Step 3 — Send And Receive

**Send text:**
```
send_uart(session_id="<session-id>", mode="text", text="AT+COMMAND\r\n", append_line_ending=False)
```

**Send binary:**
```
send_uart(session_id="<session-id>", mode="binary", data_hex="0A0B0C0D", append_line_ending=False)
```

**Read with timeout (text mode):**
```
read_uart(session_id="<session-id>", mode="text", timeout_seconds=1.0, max_bytes=4096)
```

**Wait until a text pattern appears:**
```
wait_uart(
  session_id="<session-id>",
  mode="text",
  operator="contains",
  timeout_seconds=5.0,
  poll_interval_seconds=0.05,
  hold_time_seconds=0.0,
  value="OK"
)
```

**Wait until a binary pattern appears:**
```
wait_uart(
  session_id="<session-id>",
  mode="binary",
  operator="contains",
  timeout_seconds=5.0,
  pattern_hex="AA55"
)
```

## Step 4 — Record A Session (Optional)

Record when you need a persistent artifact of the serial exchange:
```
record_uart(session_id="<session-id>", duration_seconds=30.0, artifact_format="txt")
```

`artifact_format`: `"txt"` (default, human-readable) or `"binary"`.

Poll for completion:
```
wait_for_job(job_id="<returned-job-id>", timeout_seconds=40.0)
get_record_uart(job_id="<job-id>")
```

Stop early:
```
stop_record_uart(job_id="<job-id>")
```

## Step 5 — Modem Control Lines (Optional)

Read current state:
```
get_uart_modem_lines(session_id="<session-id>")
```

Set DTR and/or RTS:
```
set_uart_modem_lines(session_id="<session-id>", dtr=True, rts=False)
```

Only read or set modem lines when the target device or workflow explicitly requires it.

## Step 6 — Close The Session

```
close_uart_session(session_id="<session-id>")
```

Always close the session when the task is done. A session left open locks the device path for other workflows.

Also stop any recording if it is still running:
```
stop_record_uart(job_id="<recording-job-id>")
```

## Notes

- Serial device paths are Nexus-device paths, not workstation paths. Use the `path` field from `list_uart_devices()`.
- SLCAN-capable adapters appear in UART inventory with `supports_slcan_attach: true`. CAN work still requires `attach_usb_can` — an open UART session and an SLCAN attachment cannot be active simultaneously on the same device.
- PTY-backed simulator paths are device-local resources exposed by managed containers. Treat them as regular UART devices.
- RS-485 mode uses RTS as direction control. Enable it only when the adapter and wiring explicitly require half-duplex switching.
