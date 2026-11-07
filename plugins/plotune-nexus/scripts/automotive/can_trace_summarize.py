#!/usr/bin/env python3
"""Summarize offline CAN trace text without opening any bus interface."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from dbc_tools import decode_message, messages_by_frame_id, parse_dbc
from safe_paths import require_regular_input, require_safe_output


CANDUMP_RE = re.compile(
    r"^\((?P<ts>[0-9.]+)\)\s+\S+\s+(?P<id>[0-9A-Fa-f]+)(?P<sep>##|#)(?P<data>[0-9A-Fa-fRr]*)\s*$"
)
# Vector CANalyzer/CANoe ASC format for CAN FD frames.
# Format: <ts> CANFD <ch> <dir> <id>[x] <brs> <esi> <dlc_hex> <byte_count> <data_bytes...> <timing...>
# The 'x' suffix on the ID indicates a 29-bit extended frame.
CANFD_ASC_RE = re.compile(
    r"^(?P<ts>[0-9.]+)\s+CANFD\s+\d+\s+\S+\s+(?P<id>[0-9A-Fa-f]+)x?\s+"
    r"[01]\s+[01]\s+[0-9a-fA-F]+\s+(?P<len>\d+)\s+"
    r"(?P<raw>[0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)"
)
ASC_LIKE_RE = re.compile(
    r"^(?P<ts>[0-9.]+)\s+\S+\s+(?P<id>[0-9A-Fa-f]+)\s+\S+\s+(?P<kind>[dDrR])(?:\s+\d+\s+(?P<data>[0-9A-Fa-f ]+))?"
)


def _is_metadata_line(stripped: str) -> bool:
    """Return True for known-benign ASC/log header and event lines that are not frame data."""
    if stripped.startswith(("date ", "base ", "//", "Begin ", "End ", "internal ")):
        return True
    if re.match(r"^[0-9.]+\s+(?:Start|End)\s+", stripped):
        return True
    return False


ParsedTraceLine = tuple[float, int, str, bool, bool]


def parse_trace_line(line: str) -> ParsedTraceLine | None:
    parsed, _reason = parse_trace_line_with_reason(line)
    return parsed


def parse_trace_line_with_reason(line: str) -> tuple[ParsedTraceLine | None, str | None]:
    stripped = line.strip()
    if not stripped or _is_metadata_line(stripped):
        return None, None
    match = CANDUMP_RE.match(stripped)
    if match:
        data = match.group("data")
        is_fd = match.group("sep") == "##"
        upper_data = data.upper()
        if upper_data == "R":
            return (float(match.group("ts")), int(match.group("id"), 16), "", True, is_fd), None
        payload = upper_data[1:] if is_fd and upper_data else upper_data
        if len(payload) % 2 != 0:
            return None, "odd_length_payload"
        return (float(match.group("ts")), int(match.group("id"), 16), payload, False, is_fd), None
    match = CANFD_ASC_RE.match(stripped)
    if match:
        frame_id = int(match.group("id"), 16)
        expected_bytes = int(match.group("len"))
        raw_bytes = match.group("raw").split()
        data = "".join(raw_bytes[:expected_bytes]).upper()
        if len(data) != expected_bytes * 2:
            return None, "declared_length_exceeds_payload"
        return (float(match.group("ts")), frame_id, data, False, True), None
    match = ASC_LIKE_RE.match(stripped)
    if match:
        data = (match.group("data") or "").replace(" ", "").upper()
        if len(data) % 2 != 0:
            return None, "odd_length_payload"
        return (float(match.group("ts")), int(match.group("id"), 16), data, match.group("kind").lower() == "r", False), None
    return None, "unrecognized_frame_format"


def frame_bit_count(frame_id: int, payload_hex: str) -> int:
    payload_bytes = len(payload_hex) // 2
    identifier_bits = 29 if frame_id > 0x7FF else 11
    # Approximate arbitration/control/CRC/ACK/intermission overhead. This is
    # enough for relative offline load estimates, not a compliance calculation.
    return identifier_bits + 47 + payload_bytes * 8


def summarize(path: Path, dbc: Path | None = None, bitrate: int | None = None) -> dict[str, Any]:
    by_id: dict[int, list[tuple[float, str, bool, bool]]] = defaultdict(list)
    malformed = 0
    first_ts: float | None = None
    last_ts: float | None = None
    dbc_message_list = parse_dbc(dbc) if dbc is not None else []
    dbc_messages = messages_by_frame_id(dbc_message_list) if dbc is not None else {}
    duplicate_dbc_frame_ids = [
        {
            "frame_id": f"0x{frame_id:X}",
            "message_names": [message.name for message in candidates],
        }
        for frame_id, candidates in sorted(
            (
                (frame_id, [message for message in dbc_message_list if message.frame_id == frame_id])
                for frame_id in {message.frame_id for message in dbc_message_list}
            ),
            key=lambda item: item[0],
        )
        if len(candidates) > 1
    ]
    duplicate_dbc_ids = {int(item["frame_id"], 16) for item in duplicate_dbc_frame_ids}
    malformed_records: list[dict[str, Any]] = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        parsed, malformed_reason = parse_trace_line_with_reason(line)
        if parsed is None:
            stripped = line.strip()
            if stripped and malformed_reason is not None:
                malformed += 1
                if len(malformed_records) < 100:
                    malformed_records.append(
                        {
                            "line": line_number,
                            "reason": malformed_reason,
                            "text": stripped[:160],
                        }
                    )
            continue
        timestamp, frame_id, payload, remote, is_fd = parsed
        by_id[frame_id].append((timestamp, payload, remote, is_fd))
        first_ts = timestamp if first_ts is None else min(first_ts, timestamp)
        last_ts = timestamp if last_ts is None else max(last_ts, timestamp)

    messages: dict[str, Any] = {}
    remote_count = 0
    decoded_frame_ids: set[int] = set()
    total_bus_bits = 0
    for frame_id, frames in sorted(by_id.items()):
        timestamps = [frame[0] for frame in frames]
        payloads = [frame[1] for frame in frames]
        remotes = [frame[2] for frame in frames]
        fd_flags = [frame[3] for frame in frames]
        deltas = [round(b - a, 9) for a, b in zip(timestamps, timestamps[1:])]
        payload_changes = sum(1 for a, b in zip(payloads, payloads[1:]) if a != b)
        remote_count += sum(1 for item in remotes if item)
        total_bus_bits += sum(frame_bit_count(frame_id, payload) for payload in payloads if payload)
        message_definition = dbc_messages.get(frame_id)
        decoded_samples: list[dict[str, Any]] = []
        decode_errors: list[dict[str, str]] = []
        if message_definition is not None:
            seen_payloads: set[str] = set()
            for payload in payloads:
                if not payload or payload in seen_payloads:
                    continue
                seen_payloads.add(payload)
                try:
                    signals = decode_message(message_definition, payload)
                except ValueError as error:
                    decode_errors.append({"payload": payload, "error": str(error)})
                    continue
                if signals:
                    decoded_samples.append({"payload": payload, "signals": signals})
                    decoded_frame_ids.add(frame_id)
                if len(decoded_samples) >= 5:
                    break
        messages[f"0x{frame_id:X}"] = {
            "name": message_definition.name if message_definition else None,
            "count": len(frames),
            "first_timestamp": timestamps[0],
            "last_timestamp": timestamps[-1],
            "period_seconds_avg": round(mean(deltas), 9) if deltas else None,
            "period_seconds_min": min(deltas) if deltas else None,
            "period_seconds_max": max(deltas) if deltas else None,
            "expected_cycle_time_ms": message_definition.cycle_time_ms if message_definition else None,
            "cycle_time_delta_ms_avg": (
                round((mean(deltas) * 1000) - message_definition.cycle_time_ms, 6)
                if deltas and message_definition is not None and message_definition.cycle_time_ms is not None
                else None
            ),
            "payload_changes": payload_changes,
            "remote_frames": sum(1 for item in remotes if item),
            "can_fd_frames": sum(1 for item in fd_flags if item),
            "sample_payloads": sorted(set(payloads))[:5],
            "decoded_samples": decoded_samples,
            "decode_errors": decode_errors,
            "dbc_definition_ambiguous": frame_id in duplicate_dbc_ids,
        }

    total_frames = sum(len(frames) for frames in by_id.values())
    duration = None if first_ts is None or last_ts is None else round(last_ts - first_ts, 9)
    observed_ids = set(by_id)
    dbc_ids = set(dbc_messages)
    bus_load_percent = None
    if bitrate and duration and duration > 0:
        bus_load_percent = round((total_bus_bits / (bitrate * duration)) * 100, 6)
    return {
        "source": str(path),
        "context": {
            "dbc": str(dbc) if dbc else None,
            "dbc_used_for_decoding": bool(decoded_frame_ids),
            "bitrate": bitrate,
        },
        "summary": {
            "frames": total_frames,
            "unique_ids": len(by_id),
            "remote_frames": remote_count,
            "malformed_lines": malformed,
            "extended_frame_ids": sum(1 for frame_id in by_id if frame_id > 0x7FF),
            "can_fd_frames": sum(1 for frames in by_id.values() for _, _, _, is_fd in frames if is_fd),
            "can_fd_like_frames": sum(1 for frames in by_id.values() for _, payload, _, is_fd in frames if is_fd or len(payload) // 2 > 8),
            "first_timestamp": first_ts,
            "last_timestamp": last_ts,
            "duration_seconds": duration,
            "estimated_bus_load_percent": bus_load_percent,
        },
        "dbc_coverage": {
            "observed_ids_known_in_dbc": [f"0x{frame_id:X}" for frame_id in sorted(observed_ids & dbc_ids)],
            "observed_ids_missing_from_dbc": [f"0x{frame_id:X}" for frame_id in sorted(observed_ids - dbc_ids)],
            "dbc_ids_not_observed": [f"0x{frame_id:X}" for frame_id in sorted(dbc_ids - observed_ids)],
            "decoded_ids": [f"0x{frame_id:X}" for frame_id in sorted(decoded_frame_ids)],
        },
        "issues": {
            "malformed_lines": malformed_records,
            "duplicate_dbc_frame_ids": duplicate_dbc_frame_ids,
        },
        "messages": messages,
    }


def _format_signal_sample(signals: dict[str, Any]) -> str:
    parts = []
    for name, value in list(signals.items())[:8]:
        if isinstance(value, dict):
            physical = value.get("physical")
            raw = value.get("raw")
            unit = value.get("unit") or ""
            rendered = physical if physical is not None else raw
            parts.append(f"{name}={rendered}{unit}")
        else:
            parts.append(f"{name}={value}")
    return ", ".join(parts)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CAN Trace Summary",
        "",
        f"Source: `{report['source']}`",
        f"DBC context: `{report['context']['dbc']}`",
        f"Bitrate context: `{report['context']['bitrate']}`",
        "",
        "## Summary",
        "",
        f"- Frames: {report['summary']['frames']}",
        f"- Unique IDs: {report['summary']['unique_ids']}",
        f"- Remote frames: {report['summary']['remote_frames']}",
        f"- Malformed lines: {report['summary']['malformed_lines']}",
        f"- CAN FD frames: {report['summary']['can_fd_frames']}",
        f"- Extended frame IDs: {report['summary']['extended_frame_ids']}",
        f"- Estimated bus load percent: {report['summary']['estimated_bus_load_percent']}",
        "",
        "## DBC Coverage",
        "",
        f"- Observed IDs known in DBC: {len(report['dbc_coverage']['observed_ids_known_in_dbc'])}",
        f"- Observed IDs missing from DBC: {len(report['dbc_coverage']['observed_ids_missing_from_dbc'])}",
        f"- DBC IDs not observed: {len(report['dbc_coverage']['dbc_ids_not_observed'])}",
        f"- Decoded IDs: {len(report['dbc_coverage']['decoded_ids'])}",
        "",
    ]
    missing = report["dbc_coverage"]["observed_ids_missing_from_dbc"][:20]
    if missing:
        lines.extend(["### Unknown Observed IDs", ""])
        lines.append(", ".join(f"`{frame_id}`" for frame_id in missing))
        lines.append("")
    duplicate_ids = report.get("issues", {}).get("duplicate_dbc_frame_ids", [])
    if duplicate_ids:
        lines.extend(["### Duplicate DBC Frame IDs", ""])
        for item in duplicate_ids:
            names = ", ".join(f"`{name}`" for name in item["message_names"])
            lines.append(f"- `{item['frame_id']}` has multiple DBC message definitions: {names}")
        lines.append("")
    malformed_lines = report.get("issues", {}).get("malformed_lines", [])
    if malformed_lines:
        lines.extend(["## Malformed Lines", ""])
        for item in malformed_lines[:20]:
            lines.append(f"- Line {item['line']}: {item['reason']} (`{item['text']}`)")
        lines.append("")
    lines.extend(
        [
        "## Top IDs",
        "",
        ]
    )
    top = sorted(report["messages"].items(), key=lambda item: item[1]["count"], reverse=True)[:20]
    for frame_id, details in top:
        name = f" `{details['name']}`" if details.get("name") else ""
        extras = []
        if details.get("can_fd_frames"):
            extras.append(f"{details['can_fd_frames']} CAN FD")
        if details.get("remote_frames"):
            extras.append(f"{details['remote_frames']} remote")
        if details.get("dbc_definition_ambiguous"):
            extras.append("ambiguous DBC definition")
        suffix = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"- `{frame_id}`{name}: {details['count']} frames, {details['payload_changes']} payload changes{suffix}")
    decoded_rows = [
        (frame_id, details)
        for frame_id, details in report["messages"].items()
        if details.get("decoded_samples")
    ]
    if decoded_rows:
        lines.extend(["", "## Decoded Signal Samples", ""])
        for frame_id, details in decoded_rows[:20]:
            name = f" `{details['name']}`" if details.get("name") else ""
            for sample in details["decoded_samples"][:3]:
                lines.append(
                    f"- `{frame_id}`{name} payload `{sample['payload']}`: "
                    f"{_format_signal_sample(sample['signals'])}"
                )
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- Unknown IDs need DBC coverage before signal-level conclusions are trusted.",
            "- Duplicate DBC frame IDs make decoding ambiguous; resolve the DBC before using decoded values as evidence.",
            "- Malformed lines are excluded from timing, payload-change, and bus-load calculations.",
        ]
    )
    return "\n".join(lines) + "\n"


def emit(report: dict[str, Any], fmt: str, output: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n" if fmt == "json" else render_markdown(report)
    output = require_safe_output(output)
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--dbc", type=Path, help="Optional DBC for signal decoding and coverage checks.")
    parser.add_argument("--bitrate", type=int, help="Optional bitrate context for reports.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.trace, "Trace")
    if args.dbc is not None:
        require_regular_input(args.dbc, "DBC")
    emit(summarize(args.trace, args.dbc, args.bitrate), args.format, args.output)


if __name__ == "__main__":
    main()
