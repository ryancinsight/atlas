"""Validate target-relative filesystem components."""

from __future__ import annotations

from pathlib import Path

from atlas_build_lease import BuildIdentityError


def _components(path: Path) -> tuple[str, ...]:
    parts = path.parts
    if path.is_absolute() or not parts or any(part in {"", ".", ".."} for part in parts):
        raise BuildIdentityError(f"invalid target-relative artifact path: {path}")
    return tuple(str(part) for part in parts)
