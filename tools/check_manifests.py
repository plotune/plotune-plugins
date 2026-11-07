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
    rel = path.relative_to(root).as_posix()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{rel}: file is missing")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{rel}: cannot read JSON ({exc})")
    return None


def _catalog_entries(data, rel: str, errors: list) -> dict:
    """Return {name: entry}, reporting duplicates."""
    entries = {}
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, list):
        errors.append(f"{rel}: 'plugins' must be a list")
        return entries
    for entry in plugins:
        name = entry.get("name") if isinstance(entry, dict) else None
        if name in entries:
            errors.append(f"{rel}: duplicate plugin name {name!r}")
        entries[name] = entry
    return entries


def check(root: Path) -> list:
    root = Path(root)
    errors: list = []

    manifests = {}  # dir name -> (claude, codex) parsed manifests
    plugins_dir = root / "plugins"
    plugin_dirs = sorted(p for p in plugins_dir.iterdir() if p.is_dir()) if plugins_dir.is_dir() else []
    for pdir in plugin_dirs:
        claude = _load(pdir / CLAUDE_MANIFEST, root, errors)
        codex = _load(pdir / CODEX_MANIFEST, root, errors)
        manifests[pdir.name] = (claude, codex)
        if isinstance(claude, dict) and isinstance(codex, dict):
            for field in ("name", "version"):
                if claude.get(field) != codex.get(field):
                    errors.append(
                        f"plugins/{pdir.name}: {field} differs between manifests "
                        f"({claude.get(field)!r} vs {codex.get(field)!r})")

    manifest_names = {
        name: (m[0] or {}).get("name", name) if isinstance(m[0], dict) else name
        for name, m in manifests.items()
    }

    claude_cat = _load(root / CLAUDE_CATALOG, root, errors)
    codex_cat = _load(root / CODEX_CATALOG, root, errors)

    for label, cat, rel in (("Claude", claude_cat, CLAUDE_CATALOG), ("Codex", codex_cat, CODEX_CATALOG)):
        if cat is None:
            continue
        entries = _catalog_entries(cat, rel, errors)
        listed = set(entries)
        known = set(manifest_names.values())
        for name in sorted(known - listed):
            errors.append(f"{rel}: plugin {name!r} has a directory but no {label} catalog entry")
        for name in sorted(n for n in listed - known if n is not None):
            errors.append(f"{rel}: entry {name!r} does not match any plugin directory/manifest name")
        for name, entry in entries.items():
            if not isinstance(entry, dict):
                continue
            if label == "Claude" and "version" in entry:
                errors.append(f"{rel}: entry {name!r} sets version; set it only in plugin.json")
            if label == "Codex":
                for field in ("category", "policy"):
                    if field not in entry:
                        errors.append(f"{rel}: entry {name!r} is missing {field}")
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
