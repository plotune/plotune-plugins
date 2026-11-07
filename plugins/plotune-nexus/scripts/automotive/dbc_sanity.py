#!/usr/bin/env python3
"""Offline DBC sanity checks for common CAN database issues."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from dbc_tools import Message, parse_dbc, message_to_dict, signal_bit_positions, signal_exceeds_payload
from safe_paths import require_regular_input, require_safe_output


def analyze(path: Path) -> dict[str, Any]:
    messages = parse_dbc(path)
    frame_id_counts = Counter(message.frame_id for message in messages)
    duplicate_ids = [f"0x{frame_id:X}" for frame_id, count in frame_id_counts.items() if count > 1]
    invalid_dlc: list[dict[str, Any]] = []
    overlapping_signals: list[dict[str, Any]] = []
    invalid_signal_ranges: list[dict[str, Any]] = []
    missing_units: list[str] = []
    missing_receivers: list[str] = []
    suspicious_cycle_times: list[dict[str, Any]] = []
    multiplexed_messages: list[str] = []

    for message in messages:
        if not 0 <= message.dlc <= 64:
            invalid_dlc.append({"message": message.name, "frame_id": f"0x{message.frame_id:X}", "dlc": message.dlc})
        if message.cycle_time_ms is not None and (message.cycle_time_ms <= 0 or message.cycle_time_ms > 10000):
            suspicious_cycle_times.append(
                {"message": message.name, "frame_id": f"0x{message.frame_id:X}", "cycle_time_ms": message.cycle_time_ms}
            )
        occupied: dict[int, str] = {}
        for signal in message.signals:
            if signal.multiplexer:
                multiplexed_messages.append(message.name)
            if signal_exceeds_payload(signal, message.dlc):
                invalid_signal_ranges.append(
                    {
                        "message": message.name,
                        "signal": signal.name,
                        "start_bit": signal.start_bit,
                        "length": signal.length,
                        "dlc": message.dlc,
                    }
                )
            if not signal.unit:
                missing_units.append(signal.name)
            if not signal.receivers:
                missing_receivers.append(signal.name)
            if signal.multiplexer and signal.multiplexer.startswith("m"):
                continue
            for bit in signal_bit_positions(signal):
                previous = occupied.get(bit)
                if previous is not None:
                    overlapping_signals.append(
                        {
                            "message": message.name,
                            "frame_id": f"0x{message.frame_id:X}",
                            "bit": bit,
                            "signals": [previous, signal.name],
                        }
                    )
                    break
                occupied[bit] = signal.name

    return {
        "source": str(path),
        "summary": {
            "messages": len(messages),
            "signals": sum(len(message.signals) for message in messages),
            "extended_frame_ids": sum(1 for message in messages if message.frame_id > 0x7FF),
            "can_fd_messages": sum(1 for message in messages if message.dlc > 8),
            "multiplexed_messages": len(set(multiplexed_messages)),
        },
        "issues": {
            "duplicate_frame_ids": duplicate_ids,
            "invalid_dlc": invalid_dlc,
            "invalid_signal_ranges": invalid_signal_ranges,
            "overlapping_signals": overlapping_signals,
            "missing_units": sorted(set(missing_units)),
            "missing_receivers": sorted(set(missing_receivers)),
            "suspicious_cycle_times": suspicious_cycle_times,
        },
        "messages": [message_to_dict(message) for message in messages],
    }


def render_markdown(report: dict[str, Any]) -> str:
    issue_counts = {key: len(value) for key, value in report["issues"].items()}
    lines = [
        "# DBC Sanity Report",
        "",
        f"Source: `{report['source']}`",
        "",
        "## Summary",
        "",
        f"- Messages: {report['summary']['messages']}",
        f"- Signals: {report['summary']['signals']}",
        f"- Extended frame IDs: {report['summary']['extended_frame_ids']}",
        f"- CAN FD messages: {report['summary']['can_fd_messages']}",
        f"- Multiplexed messages: {report['summary']['multiplexed_messages']}",
        "",
        "## Issues",
        "",
    ]
    for name, count in issue_counts.items():
        lines.append(f"- {name.replace('_', ' ')}: {count}")
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
    parser.add_argument("--dbc", required=True, type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.dbc, "DBC")
    emit(analyze(args.dbc), args.format, args.output)


if __name__ == "__main__":
    main()
