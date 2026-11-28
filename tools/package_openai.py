#!/usr/bin/env python3
"""Build and validate the OpenAI plugin submission ZIP of a plugin. Standard library only.

OpenAI's "Agent Plugins" ZIP has `plugin.json`, `mcp.json`, `skills/` and `assets/` at its root
(https://developers.openai.com/plugins/deploy/submission). This repository keeps one body per plugin with a
thin manifest per tool, which cannot be uploaded as it is, for three reasons this script handles:

  * A root `plugin.json` inside plugins/<name>/ would shadow `.claude-plugin/plugin.json` in tools that read
    a root manifest first, so the OpenAI manifest lives in `.openai-plugin/plugin.json` (checked by
    tools/check_manifests.py) and is copied to the ZIP root here, with `version` taken from the Claude manifest.
  * The repository's `mcp.json` is the Claude/Cursor shape (`"type": "http"`, no `$schema`). OpenAI's portable
    `mcp.json` needs `$schema` and `"type": "streamable-http"`, so it is generated from `.mcp.json`.
  * OpenAI cannot accept lifecycle hooks, apps or secrets, so `hooks/` and other tools' files are left out.

Shipped: plugin.json, mcp.json and everything under the plugin directory except hidden files and folders,
`hooks/`, `evals/`, `tests/`, `node_modules/`, `dist/`, `index.js`, `package.json`, `README.md`,
`CHANGELOG.md`, `__pycache__` and `*.pyc`. The ZIP is deterministic (sorted, fixed timestamps).

Errors fail the command; warnings list what the owner must still supply in the submission (terms URL,
demo recording, the 5 positive and 3 negative test cases). `--strict` turns warnings into failures.

Usage:
    python tools/package_openai.py <plugin> [--root .] [--out dist] [--strict]
"""
import argparse
import json
import re
import struct
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_manifests  # noqa: E402

MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
OPENAI_MANIFEST = check_manifests.OPENAI_MANIFEST
EXCLUDED_TOP = {"hooks", "evals", "tests", "node_modules", "dist", "index.js", "package.json",
                "README.md", "CHANGELOG.md", "mcp.json", ".mcp.json", "plugin.json"}
EXCLUDED_ANYWHERE = {"__pycache__", ".DS_Store"}
# Runs only from hooks/hooks.json, which an OpenAI package cannot carry: it would ship as dead code.
EXCLUDED_FILES = {"scripts/pool_hook.py"}
SECRET_NAMES = re.compile(r"(^\.env($|\.)|\.(pem|key|p12|pfx)$|^id_(rsa|ed25519|ecdsa)|^credentials(\.|$))", re.I)
SECRET_CONTENT = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bghp_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"
    r"|\bsk-[A-Za-z0-9]{32,}|\bAKIA[0-9A-Z]{16}\b|\bxox[bap]-[A-Za-z0-9-]{20,}")
ICON_MIN, ICON_MAX, ICON_BYTES = 48, 4096, 5 * 1024 * 1024
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


class PackageError(Exception):
    pass


def _json(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PackageError(f"{path}: cannot read JSON ({exc})")
    if not isinstance(data, dict):
        raise PackageError(f"{path}: must be a JSON object")
    return data


def portable_mcp(source: dict) -> dict:
    """The Agent Plugins mcp.json for the single HTTP server of a Claude-style .mcp.json."""
    servers = source.get("mcpServers")
    if not isinstance(servers, dict) or len(servers) != 1:
        raise PackageError(".mcp.json: OpenAI allows exactly one MCP server")
    name, server = next(iter(servers.items()))
    url = server.get("url") if isinstance(server, dict) else None
    if not isinstance(url, str) or not url.startswith("https://"):
        raise PackageError(f".mcp.json: server {name!r} needs an https url")
    return {"$schema": MCP_SCHEMA, "mcpServers": {name: {"type": "streamable-http", "url": url}}}


def _skipped(parts) -> bool:
    return ("/".join(parts) in EXCLUDED_FILES or parts[0].startswith(".") or parts[0] in EXCLUDED_TOP
            or any(p in EXCLUDED_ANYWHERE or p.startswith(".") for p in parts[1:])
            or parts[-1].endswith(".pyc"))


def _files(pdir: Path) -> list:
    """(relative path, file) of everything that ships; secret-looking files fail even when skipped."""
    found = []
    for path in sorted(pdir.rglob("*")):
        rel = path.relative_to(pdir)
        if path.is_symlink():
            raise PackageError(f"{rel.as_posix()}: symbolic links cannot be packaged")
        if path.is_dir():
            continue
        if SECRET_NAMES.search(rel.name):
            raise PackageError(f"{rel.as_posix()}: looks like a secret file; remove it before packaging")
        if not _skipped(rel.parts):
            found.append((rel.as_posix(), path))
    return found


def _scan_secret(name: str, data: bytes):
    if SECRET_NAMES.search(PurePosixPath(name).name):
        raise PackageError(f"{name}: looks like a secret file; remove it before packaging")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    if SECRET_CONTENT.search(text):
        raise PackageError(f"{name}: contains something that looks like a key or token; remove it")


def build(root: Path, plugin: str, out_dir: Path = None) -> Path:
    """Write <out>/<plugin>-<version>-openai.zip (default <root>/dist) and return its path."""
    root = Path(root)
    pdir = root / "plugins" / plugin
    if not pdir.is_dir():
        raise PackageError(f"unknown plugin {plugin!r}")
    claude = _json(pdir / ".claude-plugin/plugin.json")
    version = claude.get("version")
    if not isinstance(version, str) or not version:
        raise PackageError(".claude-plugin/plugin.json: version is missing")
    source = _json(pdir / OPENAI_MANIFEST)
    errors: list = []
    check_manifests.check_openai_manifest(source, pdir, errors, version)
    check_manifests._check_openai_mcp(pdir, claude, None, errors)
    if errors:
        raise PackageError("source manifest is invalid:\n  " + "\n  ".join(errors))

    manifest = {"$schema": source["$schema"], "name": source["name"], "version": version}
    manifest.update({k: v for k, v in source.items() if k not in manifest})
    entries = {
        "plugin.json": (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
        "mcp.json": (json.dumps(portable_mcp(_json(pdir / ".mcp.json")), indent=2) + "\n").encode("utf-8"),
    }
    modes = {}
    for rel, path in _files(pdir):
        data = path.read_bytes()
        _scan_secret(rel, data)
        entries[rel] = data
        modes[rel] = 0o755 if path.stat().st_mode & 0o111 else 0o644

    out_dir = Path(out_dir) if out_dir else root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{plugin}-{version}-openai.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100000 | modes.get(name, 0o644)) << 16
            z.writestr(info, entries[name])
    return target


def _png_size(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def _frontmatter(text: str) -> dict:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    fields = {}
    for line in (match.group(1).splitlines() if match else []):
        key, sep, value = line.partition(":")
        if sep and not key.startswith((" ", "\t")):
            fields[key.strip()] = value.strip()
    return fields


def validate(zip_path: Path):
    """Check a built ZIP against OpenAI's documented requirements. Returns (errors, warnings)."""
    errors, warnings = [], []
    try:
        z = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"{zip_path}: not a readable ZIP ({exc})"], []
    with z:
        names = z.namelist()
        unsafe = [n for n in names if n.startswith("/") or ".." in PurePosixPath(n).parts]
        if unsafe:
            return [f"unsafe path in ZIP: {unsafe[0]}"], []
        for n in names:
            parts = PurePosixPath(n).parts
            if parts[0] == "hooks" or parts[-1] in ("hooks.json", ".app.json") or "__pycache__" in parts:
                errors.append(f"{n}: hooks, apps and bytecode cannot be submitted; remove it from the package")
            if SECRET_NAMES.search(parts[-1]):
                errors.append(f"{n}: looks like a secret; keep secrets out of the ZIP")
        for need in ("plugin.json", "mcp.json"):
            if need not in names:
                errors.append(f"{need} is missing at the ZIP root")
        if not any(n.startswith("skills/") and n.endswith("/SKILL.md") for n in names):
            errors.append("skills/<name>/SKILL.md is missing: the package has no skills")
        for n in names:
            if n.startswith("skills/") and n.endswith("/SKILL.md"):
                front = _frontmatter(z.read(n).decode("utf-8", "replace"))
                for field in ("name", "description"):
                    if not front.get(field):
                        errors.append(f"{n}: frontmatter {field} is missing")
                if front.get("name") and front["name"] != PurePosixPath(n).parts[1]:
                    errors.append(f"{n}: frontmatter name must equal its directory")
        if "plugin.json" not in names or "mcp.json" not in names:
            return errors, warnings

        try:
            manifest = json.loads(z.read("plugin.json"))
            mcp = json.loads(z.read("mcp.json"))
        except ValueError as exc:
            return errors + [f"plugin.json / mcp.json: invalid JSON ({exc})"], warnings

        # mcp.json: portable schema, exactly one https streamable-http server
        if not isinstance(mcp, dict) or mcp.get("$schema") != MCP_SCHEMA:
            errors.append(f"mcp.json: $schema must be {MCP_SCHEMA}")
        servers = mcp.get("mcpServers") if isinstance(mcp, dict) else None
        if not isinstance(servers, dict) or len(servers) != 1:
            errors.append("mcp.json: OpenAI allows exactly one MCP server")
        else:
            server = next(iter(servers.values()))
            if not isinstance(server, dict) or server.get("type") != "streamable-http":
                errors.append("mcp.json: the server type must be streamable-http")
            if not isinstance(server, dict) or not str(server.get("url", "")).startswith("https://"):
                errors.append("mcp.json: the server url must be https")

        # plugin.json: reuse the repository check on an extracted copy so paths and tools resolve
        if isinstance(manifest, dict):
            with tempfile.TemporaryDirectory() as tmp:
                pdir = Path(tmp) / str(manifest.get("name", "plugin"))
                z.extractall(pdir)
                found: list = []
                check_manifests.check_openai_manifest(manifest, pdir, found)
                prefix = f"plugins/{pdir.name}/{OPENAI_MANIFEST}: "
                errors.extend("plugin.json: " + e[len(prefix):] if e.startswith(prefix) else e for e in found)
                iface = manifest.get("extensions", {}).get("com.openai", {}).get("interface", {})
                for key in ("composerIcon", "logo"):
                    rel = iface.get(key)
                    if isinstance(rel, str) and (pdir / rel).is_file() and rel.lower().endswith(".png"):
                        data = (pdir / rel).read_bytes()
                        size = _png_size(data)
                        label = rel.lstrip("./")
                        if size is None:
                            errors.append(f"{label}: not a valid PNG")
                        elif size[0] != size[1] or not ICON_MIN <= size[0] <= ICON_MAX:
                            errors.append(f"{label}: must be square, at least {ICON_MIN}x{ICON_MIN} and at most "
                                          f"{ICON_MAX} pixels per side (is {size[0]}x{size[1]})")
                        if len(data) > ICON_BYTES:
                            errors.append(f"{label}: larger than 5 MiB")
            openai = manifest.get("extensions", {}).get("com.openai", {})
            iface = openai.get("interface", {}) if isinstance(openai, dict) else {}
            review = openai.get("review", {}) if isinstance(openai, dict) else {}
            cases = review.get("test_cases", {}) if isinstance(review, dict) else {}
            if not iface.get("termsOfServiceURL"):
                warnings.append("interface.termsOfServiceURL is missing (required for MCP review)")
            if not review.get("demo_recording_url"):
                warnings.append("review.demo_recording_url is missing (required for MCP review)")
            for kind, need in (("positive", 5), ("negative", 3)):
                have = len(cases.get(kind, [])) if isinstance(cases, dict) and isinstance(cases.get(kind), list) else 0
                if have < need:
                    warnings.append(f"review.test_cases: initial MCP review needs {need} {kind} cases, found {have}")
    return errors, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate the OpenAI plugin ZIP of a plugin.")
    parser.add_argument("plugin")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--out", help="output directory (default <root>/dist, which is gitignored)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args(argv)
    try:
        path = build(Path(args.root), args.plugin, Path(args.out) if args.out else None)
    except PackageError as exc:
        print(f"ERROR: {exc}")
        return 1
    errors, warnings = validate(path)
    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARNING: {w}")
    if errors or (warnings and args.strict):
        return 1
    print(f"OK: {path} ({len(zipfile.ZipFile(path).namelist())} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
