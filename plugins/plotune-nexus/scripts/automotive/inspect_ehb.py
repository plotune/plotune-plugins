#!/usr/bin/env python3
"""Search compressed EHB ZIP archives for signal documentation without full extraction."""
import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile


TEXT_EXTENSIONS = {
    ".componentmanifest",
    ".dita",
    ".ditamap",
    ".htm",
    ".html",
    ".json",
    ".kaom",
    ".log",
    ".properties",
    ".svg",
    ".txt",
    ".xml",
}


def is_text_like_entry(entry_name):
    lowered_name = entry_name.lower()
    return any(lowered_name.endswith(extension) for extension in TEXT_EXTENSIONS)


def entry_module(entry_name):
    parts = entry_name.replace("\\", "/").split("/")
    if "documentation" in parts:
        index = parts.index("documentation")
        if index + 1 < len(parts):
            return parts[index + 1]
    return parts[0] if len(parts) > 1 else ""


def entry_type(entry_name):
    suffix = Path(entry_name).suffix.lower().lstrip(".")
    return suffix or "unknown"


def entry_matches_filters(entry_name, module=None, entry_type_filter=None):
    if module and entry_module(entry_name) != module:
        return False
    if entry_type_filter and entry_type(entry_name) != entry_type_filter.lower().lstrip("."):
        return False
    return True


def make_snippet(text, symbol, snippet_chars):
    match_index = text.find(symbol)
    if match_index < 0:
        return ""
    start_index = max(0, match_index - snippet_chars // 2)
    end_index = min(len(text), match_index + len(symbol) + snippet_chars // 2)
    return " ".join(text[start_index:end_index].split())


def first_xml_text(text, tag_name):
    match = re.search(rf"<{re.escape(tag_name)}(?:\s[^>]*)?>(.*?)</{re.escape(tag_name)}>", text, re.DOTALL)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def first_attribute(text, attribute_name):
    match = re.search(rf'\b{re.escape(attribute_name)}="([^"]*)"', text)
    return match.group(1) if match else ""


def strip_xml(text):
    return " ".join(re.sub(r"<[^>]+>", " ", text).split())


def symbol_xml_context(text, symbol):
    name_match = re.search(rf"<name>\s*{re.escape(symbol)}\s*</name>", text)
    if name_match:
        variable_text = ""
        variable_start = text.rfind("<variable", 0, name_match.start())
        variable_end = text.find("</variable>", name_match.end())
        if variable_start >= 0 and variable_end >= 0:
            variable_text = text[variable_start : variable_end + len("</variable>")]
        row_text = ""
        row_start = text.rfind("<row", 0, name_match.start())
        row_end = text.find("</row>", name_match.end())
        if row_start >= 0 and row_end >= 0:
            row_text = text[row_start : row_end + len("</row>")]
        if variable_text or row_text:
            return variable_text, row_text or variable_text

    row = re.search(rf"<row\b[^>]*>[^<]*(?:<(?!/row>).)*?{re.escape(symbol)}.*?</row>", text, re.DOTALL)
    if row:
        return row.group(0), row.group(0)
    return "", ""


def describe_symbol_entry(text, symbol):
    symbol_window = ""
    match_index = text.find(symbol)
    if match_index >= 0:
        symbol_window = text[max(0, match_index - 1000) : min(len(text), match_index + len(symbol) + 1000)]
    else:
        symbol_window = text[:2000]
    symbol_block, row_block = symbol_xml_context(text, symbol)
    metadata_context = symbol_block or symbol_window
    port_direction = ""
    port_match = re.search(
        rf'<childPorts\b[^>]*\bname="{re.escape(symbol)}"[^>]*\bportType" value="([^"]+)"',
        symbol_window,
    )
    if port_match:
        port_direction = port_match.group(1)
    longname = first_xml_text(metadata_context, "longname") or first_attribute(metadata_context, "longName")
    mode = first_xml_text(metadata_context, "mode") or first_attribute(metadata_context, "mode")
    access = first_xml_text(metadata_context, "access") or first_attribute(metadata_context, "access")
    row_values = [strip_xml(entry) for entry in re.findall(r"<entry\b[^>]*>(.*?)</entry>", row_block, flags=re.DOTALL)]
    description = first_xml_text(metadata_context, "entry") or first_xml_text(metadata_context, "desc")
    ignored_values = {symbol, longname, mode, access, "VALUE", ""}
    for value in row_values:
        if value and symbol not in value and value not in ignored_values:
            description = value
            break
    if not description:
        description = longname
    return {
        "longname": longname,
        "mode": mode,
        "access": access,
        "description": description,
        "kaom_port_direction": port_direction,
    }


def search_ehb_files(
    ehb_paths,
    symbols,
    max_entry_bytes=5_000_000,
    max_matches=100,
    snippet_chars=500,
    module=None,
    entry_type_filter=None,
):
    result = {
        "files": [str(ehb_path) for ehb_path in ehb_paths],
        "matches": [],
        "match_counts_by_file": {},
        "searched_archives": [],
        "skipped_entries": [],
    }
    for ehb_path in ehb_paths:
        archive_match_count = 0
        searched_entries = 0
        with ZipFile(ehb_path) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or not is_text_like_entry(entry.filename):
                    continue
                if not entry_matches_filters(entry.filename, module=module, entry_type_filter=entry_type_filter):
                    continue
                searched_entries += 1
                if entry.file_size > max_entry_bytes:
                    if len(result["skipped_entries"]) < 100:
                        result["skipped_entries"].append(
                            {
                                "file": str(ehb_path),
                                "entry": entry.filename,
                                "size": entry.file_size,
                                "reason": "entry_too_large",
                            }
                        )
                    continue
                try:
                    raw_content = archive.read(entry)
                    text = raw_content.decode("utf-8", errors="replace")
                except Exception as exc:
                    result["skipped_entries"].append(
                        {
                            "file": str(ehb_path),
                            "entry": entry.filename,
                            "reason": f"read_error: {exc}",
                        }
                    )
                    continue
                for symbol in symbols:
                    if symbol in text:
                        description = describe_symbol_entry(text, symbol)
                        result["matches"].append(
                            {
                                "file": str(ehb_path),
                                "entry": entry.filename,
                                "symbol": symbol,
                                "module": entry_module(entry.filename),
                                "entry_type": entry_type(entry.filename),
                                "size": entry.file_size,
                                "snippet": make_snippet(text, symbol, snippet_chars),
                                **description,
                            }
                        )
                        archive_match_count += 1
                        if len(result["matches"]) >= max_matches:
                            result["match_counts_by_file"][str(ehb_path)] = archive_match_count
                            result["searched_archives"].append(
                                {
                                    "file": str(ehb_path),
                                    "searched_entries": searched_entries,
                                    "matches": archive_match_count,
                                    "status": "match_limit_reached",
                                }
                            )
                            return result
        result["match_counts_by_file"][str(ehb_path)] = archive_match_count
        result["searched_archives"].append(
            {
                "file": str(ehb_path),
                "searched_entries": searched_entries,
                "matches": archive_match_count,
                "status": "matched" if archive_match_count else "searched_no_match",
            }
        )
    return result


def list_ehb_entries(ehb_paths, limit=200, module=None, entry_type_filter=None):
    entries = []
    for ehb_path in ehb_paths:
        with ZipFile(ehb_path) as archive:
            for entry in archive.infolist():
                if len(entries) >= limit:
                    return entries
                if not entry_matches_filters(entry.filename, module=module, entry_type_filter=entry_type_filter):
                    continue
                entries.append(
                    {
                        "file": str(ehb_path),
                        "entry": entry.filename,
                        "module": entry_module(entry.filename),
                        "entry_type": entry_type(entry.filename),
                        "size": entry.file_size,
                        "compressed_size": entry.compress_size,
                    }
                )
    return entries


def render_markdown(report):
    lines = ["# EHB Inspection", ""]
    if "entries" in report:
        lines.extend(["## Entries", ""])
        for entry in report["entries"]:
            lines.append(
                f"- `{entry['entry']}` ({entry['module']}, {entry['entry_type']}): "
                f"{entry['size']} bytes"
            )
        return "\n".join(lines) + "\n"
    lines.extend(["## Summary", ""])
    lines.append(f"- Files: {len(report.get('files', []))}")
    lines.append(f"- Matches: {len(report.get('matches', []))}")
    lines.append(f"- Skipped entries: {len(report.get('skipped_entries', []))}")
    lines.extend(["", "## Archive Search Results", ""])
    for archive in report.get("searched_archives", []):
        lines.append(
            f"- `{archive['file']}`: {archive['searched_entries']} entries searched, "
            f"{archive['matches']} matches ({archive['status']})"
        )
    lines.extend(["", "## Matches", ""])
    for match in report.get("matches", [])[:50]:
        details = []
        for key in ("longname", "mode", "access", "kaom_port_direction"):
            if match.get(key):
                details.append(f"{key}={match[key]}")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"- `{match['symbol']}` in `{match['entry']}`{suffix}")
    return "\n".join(lines) + "\n"


def parse_args():
    parser = argparse.ArgumentParser(description="Search compressed EHB ZIP content without full extraction.")
    parser.add_argument("--ehb", action="append", required=True, help="Path to EHB file; repeat for multiple")
    parser.add_argument("--symbol", action="append", help="Symbol to search; repeat for multiple")
    parser.add_argument("--max-entry-bytes", type=int, default=5_000_000)
    parser.add_argument("--max-matches", type=int, default=100)
    parser.add_argument("--limit", type=int, default=200, help="Maximum entries returned by --list-entries")
    parser.add_argument("--module", help="Filter EHB entries by documentation module name")
    parser.add_argument("--entry-type", help="Filter entries by extension/type, e.g. dita, kaom, svg")
    parser.add_argument("--list-entries", action="store_true")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def main():
    args = parse_args()
    ehb_paths = [Path(ehb_path) for ehb_path in args.ehb]
    if args.list_entries:
        result = {"entries": list_ehb_entries(ehb_paths, limit=args.limit, module=args.module, entry_type_filter=args.entry_type)}
    else:
        if not args.symbol:
            raise SystemExit("--symbol is required unless --list-entries is used")
        result = search_ehb_files(
            ehb_paths,
            args.symbol,
            max_entry_bytes=args.max_entry_bytes,
            max_matches=args.max_matches,
            module=args.module,
            entry_type_filter=args.entry_type,
        )
    if args.format == "markdown":
        print(render_markdown(result), end="")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
