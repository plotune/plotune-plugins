"""Small offline DBC parser and decoder shared by automotive helper scripts."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


MESSAGE_RE = re.compile(r"^BO_\s+(\d+)\s+(\w+)\s*:\s+(\d+)\s+(.+?)\s*$")
SIGNAL_RE = re.compile(
    r"^SG_\s+(\w+)(?:\s+([mM][0-9]*))?\s*:\s+(\d+)\|(\d+)@([01])([+-])\s+"
    r"\(([-+0-9.eE]+),([-+0-9.eE]+)\)\s+\[([^\]]*)\]\s+\"([^\"]*)\"\s*(.*?)\s*$"
)
CYCLE_RE = re.compile(r'^BA_\s+"GenMsgCycleTime"\s+BO_\s+(\d+)\s+(\d+)\s*;')


@dataclass
class Signal:
    name: str
    start_bit: int
    length: int
    byte_order: str
    signed: bool
    factor: float
    offset: float
    minimum: str
    maximum: str
    unit: str
    receivers: list[str]
    multiplexer: str | None = None


@dataclass
class Message:
    frame_id: int
    name: str
    dlc: int
    sender: str
    signals: list[Signal]
    cycle_time_ms: int | None = None


def parse_dbc(path: Path) -> list[Message]:
    messages: list[Message] = []
    current: Message | None = None
    by_id: dict[int, list[Message]] = defaultdict(list)

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        message_match = MESSAGE_RE.match(line)
        if message_match:
            current = Message(
                frame_id=int(message_match.group(1)),
                name=message_match.group(2),
                dlc=int(message_match.group(3)),
                sender=message_match.group(4),
                signals=[],
            )
            messages.append(current)
            by_id[current.frame_id].append(current)
            continue
        signal_match = SIGNAL_RE.match(line)
        if signal_match and current is not None:
            min_max = signal_match.group(9).split("|", 1)
            current.signals.append(
                Signal(
                    name=signal_match.group(1),
                    multiplexer=signal_match.group(2),
                    start_bit=int(signal_match.group(3)),
                    length=int(signal_match.group(4)),
                    byte_order="little" if signal_match.group(5) == "1" else "big",
                    signed=signal_match.group(6) == "-",
                    factor=float(signal_match.group(7)),
                    offset=float(signal_match.group(8)),
                    minimum=min_max[0] if min_max else "",
                    maximum=min_max[-1] if min_max else "",
                    unit=signal_match.group(10),
                    receivers=signal_match.group(11).split(),
                )
            )
            continue
        cycle_match = CYCLE_RE.match(line)
        if cycle_match:
            frame_id = int(cycle_match.group(1))
            for message in by_id.get(frame_id, []):
                message.cycle_time_ms = int(cycle_match.group(2))
    return messages


def messages_by_frame_id(messages: list[Message]) -> dict[int, Message]:
    result: dict[int, Message] = {}
    for message in messages:
        result.setdefault(message.frame_id, message)
    return result


def signal_bit_positions(signal: Signal) -> list[int]:
    if signal.byte_order == "little":
        return list(range(signal.start_bit, signal.start_bit + signal.length))

    positions: list[int] = []
    bit = signal.start_bit
    for _ in range(signal.length):
        positions.append(bit)
        if bit % 8 == 0:
            bit += 15
        else:
            bit -= 1
    return positions


def signal_exceeds_payload(signal: Signal, dlc: int) -> bool:
    if signal.length <= 0:
        return True
    return any(bit < 0 or bit >= dlc * 8 for bit in signal_bit_positions(signal))


def extract_signal_raw(payload: bytes, signal: Signal) -> int:
    total_bits = len(payload) * 8
    positions = signal_bit_positions(signal)
    if any(bit < 0 or bit >= total_bits for bit in positions):
        raise ValueError("signal exceeds payload length")

    if signal.byte_order == "little":
        raw_value = int.from_bytes(payload, byteorder="little", signed=False)
        raw = (raw_value >> signal.start_bit) & ((1 << signal.length) - 1)
    else:
        raw = 0
        for bit in positions:
            byte_index = bit // 8
            bit_index = bit % 8
            raw = (raw << 1) | ((payload[byte_index] >> bit_index) & 1)

    if signal.signed and signal.length > 0 and raw & (1 << (signal.length - 1)):
        raw -= 1 << signal.length
    return raw


def decode_message(message: Message, payload_hex: str) -> dict[str, Any]:
    try:
        payload = bytes.fromhex(payload_hex)
    except ValueError as error:
        raise ValueError(f"invalid CAN payload hex: {payload_hex}") from error
    decoded: dict[str, Any] = {}
    multiplexer_value: int | None = None
    for signal in message.signals:
        if signal.multiplexer and signal.multiplexer.lower() != "m":
            continue
        try:
            raw = extract_signal_raw(payload, signal)
        except ValueError:
            continue
        physical = raw * signal.factor + signal.offset
        decoded[signal.name] = {
            "raw": raw,
            "physical": round(physical, 9),
            "unit": signal.unit,
        }
        if signal.multiplexer and signal.multiplexer.lower() == "m":
            multiplexer_value = raw
    if multiplexer_value is None:
        return decoded
    for signal in message.signals:
        if not signal.multiplexer or not signal.multiplexer.lower().startswith("m") or signal.multiplexer.lower() == "m":
            continue
        selector = signal.multiplexer[1:]
        if not selector.isdigit() or int(selector) != multiplexer_value:
            continue
        try:
            raw = extract_signal_raw(payload, signal)
        except ValueError:
            continue
        physical = raw * signal.factor + signal.offset
        decoded[signal.name] = {
            "raw": raw,
            "physical": round(physical, 9),
            "unit": signal.unit,
            "multiplexer_value": multiplexer_value,
        }
    return decoded


def message_to_dict(message: Message) -> dict[str, Any]:
    result = asdict(message)
    result["frame_id"] = f"0x{message.frame_id:X}"
    return result
