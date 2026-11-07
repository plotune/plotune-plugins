#!/usr/bin/env python3
"""Offline UDS request/response helper. This script never talks to an ECU."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from safe_paths import require_safe_output


SERVICES = {
    0x10: "DiagnosticSessionControl",
    0x11: "ECUReset",
    0x14: "ClearDiagnosticInformation",
    0x19: "ReadDTCInformation",
    0x22: "ReadDataByIdentifier",
    0x27: "SecurityAccess",
    0x28: "CommunicationControl",
    0x2E: "WriteDataByIdentifier",
    0x31: "RoutineControl",
    0x34: "RequestDownload",
    0x36: "TransferData",
    0x37: "RequestTransferExit",
    0x3E: "TesterPresent",
    0x85: "ControlDTCSetting",
}

NRCS = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported",
    0x13: "incorrectMessageLengthOrInvalidFormat",
    0x22: "conditionsNotCorrect",
    0x24: "requestSequenceError",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x35: "invalidKey",
    0x36: "exceedNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired",
    0x70: "uploadDownloadNotAccepted",
    0x71: "transferDataSuspended",
    0x72: "generalProgrammingFailure",
    0x73: "wrongBlockSequenceCounter",
    0x78: "responsePending",
}

DTC_STATUS_BITS = [
    "testFailed",
    "testFailedThisOperationCycle",
    "pendingDTC",
    "confirmedDTC",
    "testNotCompletedSinceLastClear",
    "testFailedSinceLastClear",
    "testNotCompletedThisOperationCycle",
    "warningIndicatorRequested",
]

KNOWN_DIDS = {
    0xF190: "VehicleIdentificationNumber",
}


def clean_hex(value: str) -> str:
    cleaned = "".join(ch for ch in value if ch not in " _:-")
    if len(cleaned) % 2 != 0:
        raise SystemExit("Hex payload must contain an even number of digits")
    try:
        bytes.fromhex(cleaned)
    except ValueError as error:
        raise SystemExit(f"Invalid hex payload: {value}") from error
    return cleaned.upper()


def service_object(service_id: int) -> dict[str, str]:
    request_id = service_id - 0x40 if service_id >= 0x40 else service_id
    return {
        "id": f"0x{request_id:02X}",
        "name": SERVICES.get(request_id, "unknown"),
    }


def _printable_ascii(data: bytes) -> str:
    return "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in data)


def decode_positive_rdbi(payload: bytes) -> list[dict[str, Any]]:
    decoded = []
    index = 1
    while index + 2 <= len(payload):
        did = int.from_bytes(payload[index : index + 2], "big")
        index += 2
        data = payload[index:]
        entry: dict[str, Any] = {
            "did": f"0x{did:04X}",
            "name": KNOWN_DIDS.get(did, "unknown"),
            "data_hex": data.hex().upper(),
        }
        if did == 0xF190 and data:
            entry["ascii"] = _printable_ascii(data)
        decoded.append(entry)
        break
    return decoded


def decode_payload(payload_hex: str) -> dict[str, Any]:
    payload = bytes.fromhex(clean_hex(payload_hex))
    if not payload:
        raise SystemExit("Payload is empty")
    sid = payload[0]
    if sid == 0x7F:
        if len(payload) < 3:
            raise SystemExit("Negative response must contain SID, original SID, and NRC")
        original_sid = payload[1]
        nrc = payload[2]
        return {
            "kind": "negative_response",
            "raw_hex": payload.hex().upper(),
            "service": service_object(original_sid),
            "negative_response_code": {
                "id": f"0x{nrc:02X}",
                "name": NRCS.get(nrc, "unknown"),
            },
            "notes": ["NRC 0x78 responsePending extends waiting; do not resend automatically." if nrc == 0x78 else "Preserve NRC as diagnostic evidence."],
        }
    positive = sid >= 0x40
    service_id = sid - 0x40 if positive else sid
    result = {
        "kind": "positive_response" if positive else "request",
        "raw_hex": payload.hex().upper(),
        "service": service_object(service_id),
        "payload_hex": payload[1:].hex().upper(),
    }
    if positive and service_id == 0x22:
        result["decoded_data_identifiers"] = decode_positive_rdbi(payload)
    return result


def build_rdbi(dids: list[str]) -> dict[str, Any]:
    cleaned = [clean_hex(did).zfill(4) for did in dids]
    for did in cleaned:
        if len(did) != 4:
            raise SystemExit(f"DID must be 2 bytes: {did}")
    return {
        "kind": "request_builder",
        "service": service_object(0x22),
        "dids": [f"0x{did}" for did in cleaned],
        "request_hex": "22" + "".join(cleaned),
        "notes": ["This builds bytes only; use a transport-specific tool to send the request."],
    }


def decode_status(status_hex: str) -> dict[str, Any]:
    cleaned = clean_hex(status_hex)
    if len(cleaned) != 2:
        raise SystemExit("DTC status must be one byte")
    value = int(cleaned, 16)
    return {
        "kind": "dtc_status",
        "status_byte": f"0x{value:02X}",
        "set_bits": [name for bit, name in enumerate(DTC_STATUS_BITS) if value & (1 << bit)],
        "clear_bits": [name for bit, name in enumerate(DTC_STATUS_BITS) if not value & (1 << bit)],
    }


def render_markdown(report: dict[str, Any]) -> str:
    kind = report.get("kind", "unknown")
    lines = ["# UDS Payload Report", ""]
    if kind == "negative_response":
        svc = report["service"]
        nrc = report["negative_response_code"]
        lines += [
            f"**Negative response** for {svc['name']} ({svc['id']})",
            f"NRC: **{nrc['name']}** ({nrc['id']})",
            f"Raw: `{report['raw_hex']}`",
            "",
        ]
        for note in report.get("notes", []):
            lines.append(f"> {note}")
    elif kind == "positive_response":
        svc = report["service"]
        lines += [
            f"**Positive response** for {svc['name']} ({svc['id']})",
            f"Payload bytes: `{report.get('payload_hex', '')}`",
            f"Raw: `{report['raw_hex']}`",
        ]
        for did in report.get("decoded_data_identifiers", []):
            rendered = did.get("ascii") or did.get("data_hex", "")
            lines.append(f"- {did['name']} ({did['did']}): `{rendered}`")
    elif kind == "request":
        svc = report["service"]
        lines += [
            f"**Request** for {svc['name']} ({svc['id']})",
            f"Payload bytes: `{report.get('payload_hex', '')}`",
            f"Raw: `{report['raw_hex']}`",
        ]
    elif kind == "request_builder":
        svc = report["service"]
        lines += [
            f"**{svc['name']} ({svc['id']}) request**",
            f"DIDs: {', '.join(report.get('dids', []))}",
            f"Request hex: `{report.get('request_hex', '')}`",
            "",
        ]
        for note in report.get("notes", []):
            lines.append(f"> {note}")
    elif kind == "dtc_status":
        set_bits = report.get("set_bits", [])
        lines += [
            f"**DTC status byte: `{report.get('status_byte', '')}`**",
            f"Set: {', '.join(set_bits) if set_bits else 'none'}",
            f"Clear: {', '.join(report.get('clear_bits', []))}",
        ]
    else:
        lines.append("```json")
        lines.append(json.dumps(report, indent=2, sort_keys=True))
        lines.append("```")
    return "\n".join(lines) + "\n"


def emit(report: dict[str, Any], fmt: str, output: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if fmt == "markdown":
        text = render_markdown(report)
    output = require_safe_output(output)
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def main() -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=("json", "markdown"), default="markdown")
    common.add_argument("--output", type=Path)
    parser = argparse.ArgumentParser(description=__doc__, parents=[common])
    subparsers = parser.add_subparsers(dest="command", required=True)
    decode = subparsers.add_parser("decode", parents=[common])
    decode.add_argument("payload_hex")
    rdbi = subparsers.add_parser("rdbi", parents=[common])
    rdbi.add_argument("dids", nargs="+")
    status = subparsers.add_parser("dtc-status", parents=[common])
    status.add_argument("status_hex")
    args = parser.parse_args()

    if args.command == "decode":
        report = decode_payload(args.payload_hex)
    elif args.command == "rdbi":
        report = build_rdbi(args.dids)
    else:
        report = decode_status(args.status_hex)
    emit(report, args.format, args.output)


if __name__ == "__main__":
    main()
