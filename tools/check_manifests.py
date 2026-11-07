#!/usr/bin/env python3
"""Verify plugin manifests and marketplace catalogs agree. Standard library only."""
import json
import sys
from pathlib import Path

CLAUDE_MANIFEST = ".claude-plugin/plugin.json"
CODEX_MANIFEST = ".codex-plugin/plugin.json"
CLAUDE_CATALOG = ".claude-plugin/marketplace.json"
CODEX_CATALOG = ".agents/plugins/marketplace.json"


def _load(path: Path, root: Path, errors: list):
    """Parse a JSON object file; report problems instead of raising."""
    rel = path.relative_to(root).as_posix()
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


def check(root: Path) -> list:
    root = Path(root)
    errors: list = []

    plugin_names = {}  # directory name -> claude manifest name (== directory name when valid)
    plugins_dir = root / "plugins"
    plugin_dirs = sorted(p for p in plugins_dir.iterdir() if p.is_dir()) if plugins_dir.is_dir() else []
    for pdir in plugin_dirs:
        claude = _load(pdir / CLAUDE_MANIFEST, root, errors)
        codex = _load(pdir / CODEX_MANIFEST, root, errors)
        names = {}
        for label, manifest, rel in (("claude", claude, CLAUDE_MANIFEST), ("codex", codex, CODEX_MANIFEST)):
            if manifest is not None:
                names[label] = _name(manifest.get("name"), f"plugins/{pdir.name}/{rel}", errors)
        for label, name in names.items():
            if name is not None and name != pdir.name:
                errors.append(f"plugins/{pdir.name}: {label} manifest name {name!r} must equal the directory name")
        if claude is not None and codex is not None and names.get("claude") and names.get("codex"):
            if claude.get("version") != codex.get("version"):
                errors.append(
                    f"plugins/{pdir.name}: version differs between manifests "
                    f"({claude.get('version')!r} vs {codex.get('version')!r})")
            if names["claude"] != names["codex"]:
                errors.append(
                    f"plugins/{pdir.name}: name differs between manifests "
                    f"({names['claude']!r} vs {names['codex']!r})")
        plugin_names[pdir.name] = names.get("claude") or pdir.name

    claude_cat = _load(root / CLAUDE_CATALOG, root, errors)
    codex_cat = _load(root / CODEX_CATALOG, root, errors)

    for label, cat, rel in (("Claude", claude_cat, CLAUDE_CATALOG), ("Codex", codex_cat, CODEX_CATALOG)):
        if cat is None:
            continue
        entries = _catalog_entries(cat, rel, errors)
        known = set(plugin_names.values())
        for name in sorted(known - set(entries)):
            errors.append(f"{rel}: plugin {name!r} has a directory but no {label} catalog entry")
        for name in sorted(set(entries) - known):
            errors.append(f"{rel}: entry {name!r} does not match any plugin directory/manifest name")
        for name, entry in entries.items():
            expected = f"./plugins/{name}"
            if label == "Claude":
                if "version" in entry:
                    errors.append(f"{rel}: entry {name!r} sets version; set it only in plugin.json")
                source = entry.get("source")
            else:
                for field in ("category", "policy"):
                    if field not in entry:
                        errors.append(f"{rel}: entry {name!r} is missing {field}")
                src = entry.get("source")
                source = src.get("path") if isinstance(src, dict) else None
            if source != expected:
                errors.append(f"{rel}: entry {name!r} source must be {expected!r}, got {source!r}")
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
    raise SystemExit(main())
