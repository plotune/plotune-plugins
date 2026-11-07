#!/usr/bin/env python3
"""Verify plugin manifests, marketplace catalogs and the README agree. Standard library only.

Per plugin (plugins/<dir>/): the Claude/Copilot manifest (.claude-plugin/plugin.json) and
the Codex manifest (.codex-plugin/plugin.json) must exist, name the plugin after its
directory, share one version, and carry license/homepage/repository. Optional extras
(.cursor-plugin/plugin.json, package.json for OpenCode) must repeat that version.
Paths a manifest declares (skills, mcpServers, logo, composerIcon, screenshots) must exist.
Codex defaultPrompt is at most 3 entries of at most 128 characters.

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
    return [(label, value) for label, value in found if isinstance(value, str) and value.startswith("./")]


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
                if label != "cursor":
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
        if rows:
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
