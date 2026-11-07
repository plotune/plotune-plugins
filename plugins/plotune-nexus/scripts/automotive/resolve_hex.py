#!/usr/bin/env python3
"""Resolve calibration bytes from an Intel HEX file at A2L ECU addresses."""
import argparse
from collections import defaultdict
import json
from pathlib import Path


def validate_record_semantics(byte_count, address, record_type):
    if record_type == 0x01 and (byte_count != 0 or address != 0):
        raise ValueError("Intel HEX EOF record must have byte count 0 and address 0x0000")
    if record_type in (0x02, 0x04) and (byte_count != 2 or address != 0):
        raise ValueError("Intel HEX extended address records must have byte count 2 and address 0x0000")
    if record_type in (0x03, 0x05) and (byte_count != 4 or address != 0):
        raise ValueError("Intel HEX start address records must have byte count 4 and address 0x0000")


def parse_hex_record(line_text):
    stripped = line_text.strip()
    if not stripped:
        return None
    if not stripped.startswith(":"):
        raise ValueError(f"Invalid Intel HEX record: {stripped[:20]}")
    byte_count = int(stripped[1:3], 16)
    expected_length = 11 + byte_count * 2
    if len(stripped) != expected_length:
        raise ValueError(f"Invalid Intel HEX length for record: {stripped[:20]}")
    address = int(stripped[3:7], 16)
    record_type = int(stripped[7:9], 16)
    data_text = stripped[9 : 9 + byte_count * 2]
    data_bytes = bytes.fromhex(data_text)
    checksum = int(stripped[9 + byte_count * 2 : 11 + byte_count * 2], 16)
    checksum_total = byte_count + (address >> 8) + (address & 0xFF) + record_type + sum(data_bytes) + checksum
    if checksum_total & 0xFF:
        raise ValueError(f"Invalid Intel HEX checksum for record at 0x{address:04X}")
    validate_record_semantics(byte_count, address, record_type)
    return {
        "byte_count": byte_count,
        "address": address,
        "record_type": record_type,
        "data": data_bytes,
    }


def iter_hex_records(hex_path):
    with Path(hex_path).open("r", encoding="ascii", errors="ignore") as hex_file:
        for line_text in hex_file:
            record = parse_hex_record(line_text)
            if record is not None:
                yield record


def format_resolved_bytes(address, length, bytes_by_offset):
    missing_addresses = [address + offset for offset in range(length) if offset not in bytes_by_offset]
    if missing_addresses:
        return {
            "status": "missing",
            "address": f"0x{address:08X}",
            "length": length,
            "missing_addresses": [f"0x{missing_address:08X}" for missing_address in missing_addresses[:20]],
            "raw_bytes": "",
        }
    data_bytes = bytes(bytes_by_offset[offset] for offset in range(length))
    return {
        "status": "resolved",
        "address": f"0x{address:08X}",
        "length": length,
        "raw_bytes": " ".join(f"{byte_value:02X}" for byte_value in data_bytes),
        "unsigned_big_endian": int.from_bytes(data_bytes, byteorder="big"),
        "unsigned_little_endian": int.from_bytes(data_bytes, byteorder="little"),
    }


def resolve_many_bytes(hex_path, requests):
    request_states = {}
    address_lookup = defaultdict(list)
    for request_name, address, length in requests:
        request_states[request_name] = {
            "address": address,
            "length": length,
            "bytes_by_offset": {},
        }
        for offset in range(length):
            address_lookup[address + offset].append((request_name, offset))

    upper_linear_address = 0
    segment_address = 0
    for record in iter_hex_records(hex_path):
        record_type = record["record_type"]
        if record_type == 0x00:
            base_address = upper_linear_address + segment_address + record["address"]
            for offset, byte_value in enumerate(record["data"]):
                for request_name, request_offset in address_lookup.get(base_address + offset, []):
                    request_states[request_name]["bytes_by_offset"][request_offset] = byte_value
        elif record_type == 0x01:
            break
        elif record_type == 0x02:
            segment_address = int.from_bytes(record["data"], byteorder="big") << 4
            upper_linear_address = 0
        elif record_type == 0x04:
            upper_linear_address = int.from_bytes(record["data"], byteorder="big") << 16
            segment_address = 0

    return {
        request_name: format_resolved_bytes(
            state["address"],
            state["length"],
            state["bytes_by_offset"],
        )
        for request_name, state in request_states.items()
    }


def resolve_bytes(hex_path, address, length):
    return resolve_many_bytes(hex_path, [("__request__", address, length)])["__request__"]


def parse_int(value):
    return int(value, 0)


def parse_args():
    parser = argparse.ArgumentParser(description="Resolve bytes from an Intel HEX file.")
    parser.add_argument("--hex", required=True, help="Path to Intel HEX file")
    parser.add_argument("--address", type=parse_int, required=True, help="Address such as 0xB001AE2C")
    parser.add_argument("--length", type=int, default=1, help="Number of bytes to resolve")
    return parser.parse_args()


def main():
    args = parse_args()
    result = resolve_bytes(args.hex, args.address, args.length)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
