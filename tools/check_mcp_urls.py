#!/usr/bin/env python3
"""Check the MCP server URLs that plugins ship.

Collects http/sse URLs from plugins/*/.mcp.json, plugins/*/mcp.json (Cursor) and plugins/*/mcp/*.json. URLs that
contain a ${...} placeholder are per-user values and are skipped. Every URL must be
https (loopback may be http) and, unless --offline, must answer: any HTTP status except
404/410 counts as alive (401/403/405/5xx are expected without credentials).

Usage:
    python tools/check_mcp_urls.py [--offline] [repo-root]
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import namedtuple
from pathlib import Path
from urllib.parse import urlparse

Entry = namedtuple("Entry", "file server url")
DEAD = {404, 410}
LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def _files(root: Path):
    for pdir in sorted((root / "plugins").glob("*")):
        if not pdir.is_dir():
            continue
        for name in (".mcp.json", "mcp.json"):
            if (pdir / name).is_file():
                yield pdir / name
        yield from sorted((pdir / "mcp").glob("*.json"))


def _load(path: Path, root: Path, errors: list):
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("mcpServers") or {}
    except (OSError, ValueError, AttributeError) as exc:
        errors.append(f"{path.relative_to(root).as_posix()}: cannot read MCP config ({exc})")
        return {}


def collect_urls(root: Path, errors: list = None) -> list:
    root = Path(root)
    errors = [] if errors is None else errors
    entries = []
    for path in _files(root):
        for server, config in _load(path, root, errors).items():
            url = config.get("url") if isinstance(config, dict) else None
            if isinstance(url, str) and "${" not in url:
                entries.append(Entry(path.relative_to(root).as_posix(), server, url))
    return entries


def http_status(url: str, timeout: float = 10):
    """HTTP status code of a GET, or None when the host cannot be reached."""
    request = urllib.request.Request(url, headers={"User-Agent": "plotune-plugins-url-check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, OSError, ValueError):
        return None


def check(root: Path, fetch=http_status) -> list:
    errors = []
    for entry in collect_urls(root, errors):
        where = f"{entry.file}: server {entry.server!r} ({entry.url})"
        parsed = urlparse(entry.url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            errors.append(f"{where}: not a valid http(s) URL")
        elif parsed.scheme == "http" and parsed.hostname not in LOOPBACK:
            errors.append(f"{where}: must use https")
        else:
            status = fetch(entry.url)
            if status is None:
                errors.append(f"{where}: unreachable")
            elif status in DEAD:
                errors.append(f"{where}: answered {status}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--offline", action="store_true", help="only check URL shape, no network")
    args = parser.parse_args(argv)
    errors = check(Path(args.root), fetch=(lambda url: 200) if args.offline else http_status)
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print("OK: MCP URLs are well-formed" + ("" if args.offline else " and reachable"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
