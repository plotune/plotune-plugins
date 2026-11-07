#!/usr/bin/env python3
"""Inspect A2L symbols: extract MEASUREMENT, CHARACTERISTIC, and FUNCTION blocks for a symbol."""
import argparse
import json
import re
from pathlib import Path


SECTION_NAMES = ("IN_MEASUREMENT", "OUT_MEASUREMENT", "LOC_MEASUREMENT", "DEF_CHARACTERISTIC")


def normalize_symbols(symbols):
    return [symbol for symbol in symbols if symbol]


def read_a2l_lines(a2l_path):
    return Path(a2l_path).read_text(encoding="latin-1", errors="replace").splitlines()


def block_declared_name(block_lines, block_type):
    if not block_lines:
        return ""
    match = re.match(rf"\s*/begin\s+{re.escape(block_type)}\s+(\S+)", block_lines[0])
    if match:
        return match.group(1)
    for block_line in block_lines[1:]:
        stripped = block_line.strip()
        if stripped and not stripped.startswith("/") and not stripped.startswith('"'):
            return stripped.split()[0]
    return ""


def first_quoted_text(block_lines):
    for block_line in block_lines:
        match = re.search(r'"([^"]*)"', block_line)
        if match:
            return match.group(1)
    return ""


def find_line_value(block_lines, key):
    pattern = re.compile(rf"\b{re.escape(key)}\b\s+(.+)$")
    for block_line in block_lines:
        match = pattern.search(block_line.strip())
        if match:
            return match.group(1).strip().split()[0]
    return ""


def find_first_hex_after_name(block_lines):
    for block_line in block_lines[2:]:
        match = re.search(r"\b0x[0-9A-Fa-f]+\b", block_line)
        if match:
            return match.group(0)
    return ""


def iter_a2l_blocks(lines, block_type):
    begin_marker = f"/begin {block_type}"
    end_marker = f"/end {block_type}"
    current_block = None
    current_start_line = 0
    for line_number, line_text in enumerate(lines, start=1):
        stripped = line_text.strip()
        if stripped.startswith(begin_marker):
            current_block = [line_text]
            current_start_line = line_number
        elif current_block is not None:
            current_block.append(line_text)
            if stripped.startswith(end_marker):
                yield current_start_line, current_block
                current_block = None


def extract_section_symbols(function_block, section_name):
    begin_marker = f"/begin {section_name}"
    end_marker = f"/end {section_name}"
    in_section = False
    symbols = []
    for block_line in function_block:
        stripped = block_line.strip()
        if stripped.startswith(begin_marker):
            in_section = True
            continue
        if stripped.startswith(end_marker):
            in_section = False
            continue
        if in_section:
            symbols.extend(token for token in stripped.split() if token and not token.startswith("/"))
    return symbols


def summarize_measurement(start_line, block_lines):
    name = block_declared_name(block_lines, "MEASUREMENT")
    return {
        "name": name,
        "description": first_quoted_text(block_lines),
        "display_identifier": find_line_value(block_lines, "DISPLAY_IDENTIFIER"),
        "ecu_address": find_line_value(block_lines, "ECU_ADDRESS"),
        "start_line": start_line,
        "end_line": start_line + len(block_lines) - 1,
    }


def summarize_characteristic(start_line, block_lines):
    name = block_declared_name(block_lines, "CHARACTERISTIC")
    return {
        "name": name,
        "description": first_quoted_text(block_lines),
        "address": find_line_value(block_lines, "ECU_ADDRESS") or find_first_hex_after_name(block_lines),
        "record_layout": extract_characteristic_record_layout(block_lines),
        "start_line": start_line,
        "end_line": start_line + len(block_lines) - 1,
    }


def extract_characteristic_record_layout(block_lines):
    content_tokens = []
    for block_line in block_lines[1:10]:
        stripped = block_line.strip()
        if stripped and not stripped.startswith("/") and not stripped.startswith('"'):
            content_tokens.extend(stripped.split())
    for token_index, token in enumerate(content_tokens):
        if token.lower().startswith("0x") and token_index + 1 < len(content_tokens):
            return content_tokens[token_index + 1]
    return ""


def summarize_function(start_line, block_lines):
    function_summary = {
        "name": block_declared_name(block_lines, "FUNCTION"),
        "description": first_quoted_text(block_lines),
        "start_line": start_line,
        "end_line": start_line + len(block_lines) - 1,
    }
    for section_name in SECTION_NAMES:
        function_summary[section_name.lower()] = extract_section_symbols(block_lines, section_name)
    return function_summary


def symbol_matches(summary, symbol):
    candidates = {summary.get("name", ""), summary.get("display_identifier", "")}
    return symbol in candidates


def function_contains_symbol(function_summary, symbol):
    for section_name in SECTION_NAMES:
        if symbol in function_summary.get(section_name.lower(), []):
            return True
    return False


def empty_symbol_result():
    return {
        "measurements": [],
        "characteristics": [],
        "functions": [],
    }


def inspect_a2l_file(a2l_path, symbols):
    requested_symbols = normalize_symbols(symbols)
    lines = read_a2l_lines(a2l_path)
    result = {
        "file": str(a2l_path),
        "symbols": {symbol: empty_symbol_result() for symbol in requested_symbols},
    }

    for start_line, block_lines in iter_a2l_blocks(lines, "MEASUREMENT"):
        measurement = summarize_measurement(start_line, block_lines)
        for symbol in requested_symbols:
            if symbol_matches(measurement, symbol):
                result["symbols"][symbol]["measurements"].append(measurement)

    for start_line, block_lines in iter_a2l_blocks(lines, "CHARACTERISTIC"):
        characteristic = summarize_characteristic(start_line, block_lines)
        for symbol in requested_symbols:
            if symbol == characteristic["name"]:
                result["symbols"][symbol]["characteristics"].append(characteristic)

    for start_line, block_lines in iter_a2l_blocks(lines, "FUNCTION"):
        function_summary = summarize_function(start_line, block_lines)
        for symbol in requested_symbols:
            if function_contains_symbol(function_summary, symbol):
                result["symbols"][symbol]["functions"].append(function_summary)

    return result


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect A2L symbols and function context.")
    parser.add_argument("--a2l", required=True, help="Path to A2L file")
    parser.add_argument("--symbol", action="append", required=True, help="Symbol to inspect; repeat for multiple")
    parser.add_argument("--format", choices=("json",), default="json")
    return parser.parse_args()


def main():
    args = parse_args()
    result = inspect_a2l_file(args.a2l, args.symbol)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
