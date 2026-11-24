#!/usr/bin/env python3
"""Generate plugins/plotune/references/gateway-tools.json from the monorepo's MCP gateway catalog.

Reads <catalog>/{rms,stream,nexus}.json, <catalog>/mapping.json and the Nexus device manifest
<catalog>/../nexus-v2/fixtures/session-tools.json, and computes the gateway tool names the way
packages/contracts/mcp-catalog/catalog.ts does: a product tool keeps its name unless mapping.json
renames it, tools listed under `exclude` are dropped, and Nexus device tools are included unless the
manifest marks them internal (_meta.nexus.internal) or mapping.json excludes them. The gateway's own
`plotune_projects_list` is added. The file also records the old (product) names of renamed tools and
the excluded names, so check_gateway_tools.py can tell a skill which name to use.

The plugins repository never needs the monorepo for its checks: it only reads the generated file.
Run this by hand when the catalog changes, review the diff and commit it with the skill change.

Usage:
    python tools/generate_gateway_tools.py <path to packages/contracts/mcp-catalog>
        [--commit SHA] [--out FILE] [--check]
    --commit  monorepo commit the catalog is at (default: git rev-parse HEAD in the catalog folder)
    --out     default plugins/plotune/references/gateway-tools.json
    --check   compare the catalog with --out and exit 1 when they differ (the commit is not compared)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PRODUCTS = ("rms", "stream", "nexus")
PROJECTS_TOOL = "plotune_projects_list"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "plugins/plotune/references/gateway-tools.json"


class GenerateError(Exception):
    pass


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GenerateError(f"{path}: cannot read ({exc})") from exc


def generate(catalog: Path, commit: str) -> dict:
    catalog = Path(catalog)
    mapping = _load(catalog / "mapping.json")
    renames = mapping.get("renames") or {}
    exclude = mapping.get("exclude") or {}
    renamed_to = {}  # (product, product tool name) -> gateway name
    for gateway, target in renames.items():
        renamed_to[(target["product"], target["tool"])] = gateway

    def gateway_name(product, name):
        return renamed_to.get((product, name), name)

    tools, renamed, excluded = {PROJECTS_TOOL}, {}, {}

    def add(product, name):
        tools.add(gateway_name(product, name))
        if (product, name) in renamed_to:
            renamed[name] = renamed_to[(product, name)]

    for product in PRODUCTS:
        for tool in _load(catalog / f"{product}.json")["tools"]:
            name = tool["name"]
            reason = (exclude.get(product) or {}).get(name)
            if reason:
                excluded[name] = reason
            else:
                add(product, name)
    manifest = _load(catalog.parent / "nexus-v2/fixtures/session-tools.json")
    for tool in manifest["tools"]:
        name = tool["name"]
        meta = (tool.get("_meta") or {}).get("nexus") or {}
        reason = (exclude.get("nexus") or {}).get(name)
        if meta.get("internal") is True:
            excluded[name] = "Internal Nexus tool; the gateway does not list it."
        elif reason:
            excluded[name] = reason
        else:
            add("nexus", name)
    return {
        "generatedFrom": {"repository": "plotune monorepo", "catalog": "packages/contracts/mcp-catalog", "commit": commit},
        "tools": sorted(tools),
        "renamed": dict(sorted(renamed.items())),
        "excluded": dict(sorted(excluded.items())),
    }


def _commit(catalog: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(catalog), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GenerateError(f"cannot read the commit of {catalog} (pass --commit): {exc}") from exc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("catalog")
    parser.add_argument("--commit")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out)
    try:
        catalog = Path(args.catalog)
        if not catalog.is_dir():
            raise GenerateError(f"{catalog}: not a directory")
        if args.check:
            current = _load(out)
            data = generate(catalog, current.get("generatedFrom", {}).get("commit", ""))
            if data != current:
                print(f"out of date: {out} (regenerate with tools/generate_gateway_tools.py)")
                return 1
            print("OK: gateway-tools.json matches the catalog")
            return 0
        data = generate(catalog, args.commit or _commit(catalog))
    except GenerateError as exc:
        print(f"ERROR: {exc}")
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(data['tools'])} tools, commit {data['generatedFrom']['commit']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
