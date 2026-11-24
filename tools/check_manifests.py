#!/usr/bin/env python3
"""Verify plugin manifests, marketplace catalogs and the README agree. Standard library only.

Per plugin (plugins/<dir>/): the Claude/Copilot manifest (.claude-plugin/plugin.json) and
the Codex manifest (.codex-plugin/plugin.json) must exist, name the plugin after its
directory, share one version, and carry license/homepage/repository. Optional extras
(.cursor-plugin/plugin.json, package.json for OpenCode) must repeat that version.
Paths a manifest declares (skills, mcpServers, logo, composerIcon, screenshots) must exist.
Codex defaultPrompt is at most 3 entries of at most 128 characters.

Optional OpenAI plugin manifest (.openai-plugin/plugin.json, the source of the root plugin.json of an
OpenAI ZIP submission, built by tools/package_openai.py): Agent Plugins schema keys only, name equals the
directory, listing fields under extensions.com.openai.interface with OpenAI's documented limits, existing
asset/onboarding paths, review test cases with real gateway tool names, no hooks, and exactly one https MCP
server whose URL is the same in .mcp.json (Claude, Codex) and mcp.json.

Catalogs (.claude-plugin/, .agents/plugins/, optional .cursor-plugin/ marketplace.json)
must list exactly the plugin directories with source ./plugins/<name>. Claude entries
never carry a version (plugin.json wins silently) and need a category; Codex entries need
category and policy. The root README table must show each plugin's current version.
"""
import json
import re
import sys
from pathlib import Path

CLAUDE_MANIFEST = ".claude-plugin/plugin.json"
CODEX_MANIFEST = ".codex-plugin/plugin.json"
CURSOR_MANIFEST = ".cursor-plugin/plugin.json"
PACKAGE_JSON = "package.json"
OPENAI_MANIFEST = ".openai-plugin/plugin.json"
OPENAI_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
OPENAI_TOP_KEYS = {"$schema", "name", "version", "description", "author", "homepage", "repository",
                   "license", "keywords", "extensions"}
OPENAI_EXT_KEYS = {"interface", "onboardingSkill", "review", "publication"}
OPENAI_REQUIRED_TEXT = {"displayName": 30, "shortDescription": 30, "longDescription": 4000,
                        "developerName": 80, "category": None}
OPENAI_URLS = ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL")
OPENAI_REQUIRED_URLS = ("websiteURL", "supportURL", "privacyPolicyURL")
OPENAI_FORBIDDEN_REVIEW = ("test_credentials", "reviewer_instructions")
OPENAI_NAME = re.compile(r"^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$")
CLAUDE_CATALOG = ".claude-plugin/marketplace.json"
CODEX_CATALOG = ".agents/plugins/marketplace.json"
CURSOR_CATALOG = ".cursor-plugin/marketplace.json"
REQUIRED_METADATA = ("license", "homepage", "repository")
MAX_PROMPTS, MAX_PROMPT_CHARS = 3, 128
README_ROW = re.compile(r"^\|\s*\[`([^`]+)`\]\([^)]*\)\s*\|\s*([^|\s]+)\s*\|", re.MULTILINE)


def _load(path: Path, root: Path, errors: list, required: bool = True):
    """Parse a JSON object file; report problems instead of raising."""
    rel = path.relative_to(root).as_posix()
    if not path.exists() and not required:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{rel}: file is missing")
        return None
    except (OSError, ValueError) as exc:  # ValueError covers JSONDecodeError and UnicodeDecodeError
        errors.append(f"{rel}: cannot read JSON ({exc})")
        return None
    if not isinstance(data, dict):
        errors.append(f"{rel}: must be a JSON object")
        return None
    return data


def _name(value, where: str, errors: list):
    """Return value if it is a non-empty string, else report and return None."""
    if isinstance(value, str) and value:
        return value
    errors.append(f"{where}: name must be a string")
    return None


def _catalog_entries(data: dict, rel: str, errors: list) -> dict:
    """Return {name: entry} for well-formed entries, reporting everything else."""
    entries = {}
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        errors.append(f"{rel}: 'plugins' must be a list")
        return entries
    for i, entry in enumerate(plugins):
        where = f"{rel}: plugins[{i}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be an object")
            continue
        name = _name(entry.get("name"), where, errors)
        if name is None:
            continue
        if name in entries:
            errors.append(f"{rel}: duplicate plugin name {name!r}")
        entries[name] = entry
    return entries


def _declared_paths(manifest: dict) -> list:
    """(label, relative path) for every component/asset path a manifest declares."""
    found = []
    for key in ("icon", "logo"):  # Claude listing icon, Cursor logo
        if isinstance(manifest.get(key), str):
            found.append((key, manifest[key]))
    skills = manifest.get("skills")
    for value in ([skills] if isinstance(skills, str) else skills if isinstance(skills, list) else []):
        found.append(("skills", value))
    if isinstance(manifest.get("mcpServers"), str):
        found.append(("mcpServers", manifest["mcpServers"]))
    interface = manifest.get("interface")
    if isinstance(interface, dict):
        for key in ("logo", "composerIcon"):
            if isinstance(interface.get(key), str):
                found.append((f"interface.{key}", interface[key]))
        shots = interface.get("screenshots")
        for value in (shots if isinstance(shots, list) else []):
            found.append(("interface.screenshots", value))
    return [(label, value) for label, value in found
            if isinstance(value, str) and value and not re.match(r"^([a-z][a-z0-9+.-]*:|/)", value, re.I)]


def _check_manifest_content(label: str, manifest: dict, pdir: Path, root: Path, errors: list):
    where = f"plugins/{pdir.name}/{label}"
    for field in REQUIRED_METADATA:
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            errors.append(f"{where}: {field} is missing")
    for key, value in _declared_paths(manifest):
        if not (pdir / value).exists():
            errors.append(f"{where}: {key} path {value!r} does not exist")
    interface = manifest.get("interface")
    prompts = interface.get("defaultPrompt") if isinstance(interface, dict) else None
    if prompts is not None:
        if not isinstance(prompts, list) or len(prompts) > MAX_PROMPTS:
            errors.append(f"{where}: defaultPrompt must be a list of at most {MAX_PROMPTS} strings")
        elif any(not isinstance(p, str) or len(p) > MAX_PROMPT_CHARS for p in prompts):
            errors.append(f"{where}: each defaultPrompt must be a string of at most {MAX_PROMPT_CHARS} characters")


def _text(value, limit=None) -> bool:
    return isinstance(value, str) and bool(value.strip()) and (limit is None or len(value) <= limit)


def _https(value) -> bool:
    return isinstance(value, str) and len(value) <= 1024 and re.match(r"^https://[^/@\s]+(/\S*)?$", value) is not None


def mcp_servers(path: Path):
    """The server map of an MCP config file, or None when unreadable."""
    try:
        servers = json.loads(path.read_text(encoding="utf-8")).get("mcpServers")
    except (OSError, ValueError, AttributeError):
        return None
    return servers if isinstance(servers, dict) else None


def check_openai_manifest(manifest: dict, pdir: Path, errors: list, claude_version=None):
    """Validate an OpenAI/Agent Plugins plugin.json (source or built) against the documented schema."""
    where = f"plugins/{pdir.name}/{OPENAI_MANIFEST}"
    if manifest.get("$schema") != OPENAI_SCHEMA:
        errors.append(f"{where}: $schema must be {OPENAI_SCHEMA}")
    name = manifest.get("name")
    if name != pdir.name:
        errors.append(f"{where}: name {name!r} must equal the directory name")
    if isinstance(name, str) and (not OPENAI_NAME.match(name) or len(name) > 64 or "--" in name or ".." in name):
        errors.append(f"{where}: name {name!r} does not match the Agent Plugins name pattern")
    for key in sorted(set(manifest) - OPENAI_TOP_KEYS):
        errors.append(f"{where}: unknown top-level key {key!r} (the schema allows only "
                      f"{', '.join(sorted(OPENAI_TOP_KEYS))}; tool-specific data goes under extensions)")
    if "version" in manifest and claude_version is not None and manifest["version"] != claude_version:
        errors.append(f"{where}: version {manifest['version']!r} differs from the Claude manifest "
                      f"({claude_version!r}); omit it, tools/package_openai.py fills it in")

    ext = manifest.get("extensions")
    openai = ext.get("com.openai") if isinstance(ext, dict) else None
    if not isinstance(openai, dict):
        errors.append(f"{where}: extensions.com.openai is missing")
        return
    for key in sorted(set(openai) - OPENAI_EXT_KEYS):
        errors.append(f"{where}: extensions.com.openai.{key} is not supported here "
                      "(hooks and apps cannot be submitted; only interface, onboardingSkill, review, publication)")

    def under_plugin(rel, label, must_be_file=True):
        if not isinstance(rel, str) or not rel.startswith("./") or ".." in rel.split("/"):
            errors.append(f"{where}: {label} must be a relative path starting with ./ ({rel!r})")
        elif not (pdir / rel).is_file():
            errors.append(f"{where}: {label} path {rel!r} does not exist")

    iface = openai.get("interface")
    if not isinstance(iface, dict):
        errors.append(f"{where}: extensions.com.openai.interface is missing")
        iface = {}
    for field, limit in OPENAI_REQUIRED_TEXT.items():
        if not _text(iface.get(field), limit):
            errors.append(f"{where}: interface.{field} is required"
                          + (f" and at most {limit} characters" if limit else ""))
    display = iface.get("displayName")
    if isinstance(display, str) and re.search(r"\b(mcp|plugin)\b", display, re.IGNORECASE):
        errors.append(f"{where}: interface.displayName must not contain 'MCP' or 'Plugin' (OpenAI plugin guidelines 1.3)")
    for field in OPENAI_URLS:
        if field in iface or field in OPENAI_REQUIRED_URLS:
            if not _https(iface.get(field)):
                errors.append(f"{where}: interface.{field} must be an https URL of at most 1024 characters")
    prompts = iface.get("defaultPrompt")
    if prompts is not None:
        if not isinstance(prompts, list) or len(prompts) > MAX_PROMPTS \
                or any(not _text(p, MAX_PROMPT_CHARS) for p in prompts):
            errors.append(f"{where}: interface.defaultPrompt must be at most {MAX_PROMPTS} strings of "
                          f"at most {MAX_PROMPT_CHARS} characters")
        elif len(set(prompts)) != len(prompts):
            errors.append(f"{where}: interface.defaultPrompt entries must be unique")
    for field in ("composerIcon", "logo"):
        if field in iface:
            under_plugin(iface[field], f"interface.{field}")
    for field in ("brandColor", "brandColorDark"):
        if field in iface and not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(iface[field])):
            errors.append(f"{where}: interface.{field} must be #RRGGBB")
    if "onboardingSkill" in openai:
        rel = openai["onboardingSkill"]
        under_plugin(rel, "onboardingSkill")
        if isinstance(rel, str) and not (rel.startswith("./skills/") and rel.endswith("/SKILL.md")):
            errors.append(f"{where}: onboardingSkill must be ./skills/<name>/SKILL.md")

    review = openai.get("review")
    if review is not None:
        if not isinstance(review, dict):
            errors.append(f"{where}: review must be an object")
            return
        for key in OPENAI_FORBIDDEN_REVIEW:
            if key in review:
                errors.append(f"{where}: review.{key} is rejected by OpenAI; enter it in the submission dashboard")
        cases = review.get("test_cases", {})
        known = None
        try:
            tools = json.loads((pdir / "references/gateway-tools.json").read_text(encoding="utf-8")).get("tools")
            known = set(tools) if isinstance(tools, list) else None
        except (OSError, ValueError, AttributeError):
            pass
        for kind, required in (("positive", ("description", "prompt", "tools_triggered", "expected_behavior")),
                               ("negative", ("description", "prompt"))):
            entries = cases.get(kind, []) if isinstance(cases, dict) else None
            if not isinstance(entries, list):
                errors.append(f"{where}: review.test_cases.{kind} must be a list")
                continue
            for i, entry in enumerate(entries):
                label = f"review.test_cases.{kind}[{i}]"
                if not isinstance(entry, dict):
                    errors.append(f"{where}: {label} must be an object")
                    continue
                for field in required:
                    if not _text(entry.get(field)):
                        errors.append(f"{where}: {label}.{field} is required")
                if kind == "positive" and known is not None and isinstance(entry.get("tools_triggered"), str):
                    for tool in re.split(r"[,\s]+", entry["tools_triggered"].strip()):
                        if tool and tool not in known:
                            errors.append(f"{where}: {label} names tool {tool!r}, which is not in "
                                          "references/gateway-tools.json")


def _check_openai_mcp(pdir: Path, claude, codex, errors: list):
    """One https MCP server, the same URL in .mcp.json (Claude, Codex) and mcp.json (Cursor, OpenAI)."""
    where = f"plugins/{pdir.name}"
    for label, manifest in (("Claude", claude), ("Codex", codex)):
        if manifest is not None and manifest.get("mcpServers") != "./.mcp.json":
            errors.append(f"{where}: the {label} manifest mcpServers must be './.mcp.json' "
                          "(the OpenAI package uses the same server)")
    urls = {}
    for rel in (".mcp.json", "mcp.json"):
        servers = mcp_servers(pdir / rel)
        if servers is None:
            errors.append(f"{where}/{rel}: missing or has no mcpServers (needed for the OpenAI package)")
        elif len(servers) != 1:
            errors.append(f"{where}/{rel}: OpenAI allows exactly one MCP server, found {len(servers)}")
        else:
            server = next(iter(servers.values()))
            url = server.get("url") if isinstance(server, dict) else None
            if not _https(url):
                errors.append(f"{where}/{rel}: the MCP server url must be https ({url!r})")
            urls[rel] = url
    if len(set(urls.values())) > 1:
        errors.append(f"{where}/mcp.json: MCP URL {urls.get('mcp.json')!r} differs from .mcp.json "
                      f"({urls.get('.mcp.json')!r}); Claude, Codex and OpenAI must share one URL")


def check(root: Path) -> list:
    root = Path(root)
    errors: list = []

    plugin_names = {}  # directory name -> versions {dir: version of the Claude manifest}
    versions = {}
    plugins_dir = root / "plugins"
    plugin_dirs = sorted(p for p in plugins_dir.iterdir() if p.is_dir()) if plugins_dir.is_dir() else []
    for pdir in plugin_dirs:
        claude = _load(pdir / CLAUDE_MANIFEST, root, errors)
        codex = _load(pdir / CODEX_MANIFEST, root, errors)
        cursor = _load(pdir / CURSOR_MANIFEST, root, errors, required=False)
        package = _load(pdir / PACKAGE_JSON, root, errors, required=False)

        names = {}
        for label, manifest, rel in (("claude", claude, CLAUDE_MANIFEST), ("codex", codex, CODEX_MANIFEST),
                                     ("cursor", cursor, CURSOR_MANIFEST)):
            if manifest is not None:
                names[label] = _name(manifest.get("name"), f"plugins/{pdir.name}/{rel}", errors)
                _check_manifest_content(rel, manifest, pdir, root, errors)
        for label, name in names.items():
            if name is not None and name != pdir.name:
                errors.append(f"plugins/{pdir.name}: {label} manifest name {name!r} must equal the directory name")
        if claude is not None and names.get("claude"):
            versions[pdir.name] = claude.get("version")
            for label, other, rel in (("codex", codex, CODEX_MANIFEST), ("cursor", cursor, CURSOR_MANIFEST),
                                      ("package.json", package, PACKAGE_JSON)):
                if other is None:
                    continue
                if other.get("version") != claude.get("version"):
                    errors.append(
                        f"plugins/{pdir.name}: version differs between manifests "
                        f"({claude.get('version')!r} in {CLAUDE_MANIFEST} vs {other.get('version')!r} in {rel})")
                if label != "package.json" and names.get(label) and names[label] != names["claude"]:
                    errors.append(
                        f"plugins/{pdir.name}: name differs between manifests "
                        f"({names['claude']!r} vs {names[label]!r})")
        plugin_names[pdir.name] = names.get("claude") or pdir.name

        openai = _load(pdir / OPENAI_MANIFEST, root, errors, required=False)
        if openai is not None:
            check_openai_manifest(openai, pdir, errors, claude.get("version") if claude else None)
            _check_openai_mcp(pdir, claude, codex, errors)

        # Cursor reads mcp.json at the plugin root; it must be the same server list as .mcp.json
        both = [pdir / ".mcp.json", pdir / "mcp.json"]
        if all(f.is_file() for f in both):
            loaded = [_load(f, root, errors) for f in both]
            if None not in loaded and loaded[0] != loaded[1]:
                errors.append(f"plugins/{pdir.name}/mcp.json: differs from .mcp.json (Cursor copy must match)")

    known = set(plugin_names.values())
    catalogs = (("Claude", CLAUDE_CATALOG, True), ("Codex", CODEX_CATALOG, True), ("Cursor", CURSOR_CATALOG, False))
    for label, rel, required in catalogs:
        cat = _load(root / rel, root, errors, required=required)
        if cat is None:
            continue
        entries = _catalog_entries(cat, rel, errors)
        for name in sorted(known - set(entries)):
            errors.append(f"{rel}: plugin {name!r} has a directory but no {label} catalog entry")
        for name in sorted(set(entries) - known):
            errors.append(f"{rel}: entry {name!r} does not match any plugin directory/manifest name")
        for name, entry in entries.items():
            expected = f"./plugins/{name}"
            if label == "Codex":
                for field in ("category", "policy"):
                    if field not in entry:
                        errors.append(f"{rel}: entry {name!r} is missing {field}")
                src = entry.get("source")
                source = src.get("path") if isinstance(src, dict) else None
            else:
                if "version" in entry:
                    errors.append(f"{rel}: entry {name!r} sets version; set it only in plugin.json")
                if label == "Claude" and not entry.get("category"):
                    errors.append(f"{rel}: entry {name!r} is missing category")
                source = entry.get("source")
            if source != expected:
                errors.append(f"{rel}: entry {name!r} source must be {expected!r}, got {source!r}")

    readme = root / "README.md"
    if readme.is_file():
        try:
            rows = dict(README_ROW.findall(readme.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"README.md: cannot read ({exc})")
            rows = {}
        if not rows:
            errors.append("README.md: no plugin table found (rows like | [`name`](plugins/name) | 1.0.0 | ... |)")
        else:
            for name in sorted(known):
                if name not in rows:
                    errors.append(f"README.md: plugin {name!r} is missing from the plugin table")
                elif rows[name] != versions.get(name):
                    errors.append(f"README.md: plugin {name!r} shows version {rows[name]!r} "
                                  f"but the manifest says {versions.get(name)!r}")
    return errors


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    errors = check(root)
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print("OK: manifests and catalogs are consistent")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
