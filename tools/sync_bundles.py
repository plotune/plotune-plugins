#!/usr/bin/env python3
"""Copy the declared paths of one plugin into another, so a bundled skill has one source.

tools/bundles.json says what is bundled: for each bundle, a `source` plugin directory, a `target`
plugin directory and the `paths` (files or directories, relative to both) that are copied. The
source stays the only place to edit; the copy in the target is generated and never edited by hand.
A declared directory is mirrored exactly (a file that exists only in the target is removed);
everything in the target outside the declared paths is the target plugin's own and is left alone.
__pycache__ directories and .pyc files are ignored.

Usage:
    python tools/sync_bundles.py [--check] [repo-root]
        --check  report what differs and exit 1, without writing
"""
import argparse
import json
import shutil
import sys
from pathlib import Path, PurePosixPath

CONFIG = "tools/bundles.json"


class BundleError(Exception):
    pass


def load_config(root: Path) -> list:
    """Return the list of bundles from tools/bundles.json, validated."""
    path = Path(root) / CONFIG
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"{CONFIG}: cannot read ({exc})") from exc
    bundles = data.get("bundles") if isinstance(data, dict) else None
    if not isinstance(bundles, list) or not bundles:
        raise BundleError(f"{CONFIG}: 'bundles' must be a non-empty list")
    for i, bundle in enumerate(bundles):
        where = f"{CONFIG}: bundles[{i}]"
        if not isinstance(bundle, dict):
            raise BundleError(f"{where}: must be an object")
        for key in ("source", "target"):
            _plugin_dir(bundle.get(key), f"{where}.{key}")
        if bundle["source"] == bundle["target"]:
            raise BundleError(f"{where}: source and target are the same")
        paths = bundle.get("paths")
        if not isinstance(paths, list) or not paths:
            raise BundleError(f"{where}: 'paths' must be a non-empty list")
        for value in paths:
            _relative(value, where)
    return bundles


def _plugin_dir(value, where: str):
    parts = PurePosixPath(value).parts if isinstance(value, str) else ()
    if len(parts) != 2 or parts[0] != "plugins" or ".." in parts:
        raise BundleError(f"{where}: must be plugins/<name>, got {value!r}")


def _relative(value, where: str):
    if not isinstance(value, str) or not value:
        raise BundleError(f"{where}: every path must be a non-empty string")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "\\" in value:
        raise BundleError(f"{where}: path {value!r} must be relative and stay inside the plugin")


def _ignored(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc"


def _files(base: Path) -> dict:
    """{posix path relative to base: Path} of the files at or under base."""
    if base.is_file():
        return {"": base}
    if not base.is_dir():
        return {}
    return {p.relative_to(base).as_posix(): p for p in sorted(base.rglob("*")) if p.is_file() and not _ignored(p)}


def sync(root: Path, write: bool = True) -> list:
    """Return the repo-relative paths that were (or, with write=False, would be) written or removed."""
    root = Path(root)
    changed = []
    for bundle in load_config(root):
        source, target = root / bundle["source"], root / bundle["target"]
        for rel in bundle["paths"]:
            src, dst = source / rel, target / rel
            if not src.exists():
                raise BundleError(f"{bundle['source']}/{rel}: declared in {CONFIG} but missing in the source")
            src_files, dst_files = _files(src), _files(dst)
            for name, path in src_files.items():
                out = dst / name if name else dst
                if name not in dst_files or dst_files[name].read_bytes() != path.read_bytes():
                    if write:
                        out.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(path, out)
                    changed.append(out.relative_to(root).as_posix())
            for name, path in dst_files.items():
                if name not in src_files:
                    if write:
                        path.unlink()
                    changed.append(path.relative_to(root).as_posix())
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        changed = sync(Path(args.root), write=not args.check)
    except BundleError as exc:
        print(f"ERROR: {exc}")
        return 2
    for path in changed:
        print(("out of date: " if args.check else "wrote ") + path)
    if args.check and changed:
        print("Run: python tools/sync_bundles.py")
        return 1
    if not changed:
        print("OK: bundled copies are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
