"""Shared path guards for offline automotive helper scripts."""

from __future__ import annotations

from pathlib import Path


def require_regular_input(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(f"{label} not found: {path}")
    if not path.is_file():
        raise SystemExit(f"{label} must be a regular file: {path}")
    return path


def require_safe_output(path: Path | None) -> Path | None:
    if path is None:
        return None
    parent = path.parent if path.parent != Path("") else Path(".")
    if not parent.exists():
        raise SystemExit(f"Output directory not found: {parent}")
    if not parent.is_dir():
        raise SystemExit(f"Output parent must be a directory: {parent}")
    if path.exists() and not path.is_file():
        raise SystemExit(f"Output path must be a regular file: {path}")
    return path
