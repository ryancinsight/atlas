"""Immutable, path-confined Cargo source cohorts."""
from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from atlas_git_process import archive, execute, extract_archive

PROCESS_TIMEOUT_SECONDS = 60
MEMBER_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*", re.ASCII)
COMMIT_ID = re.compile(r"[0-9a-f]{40}", re.ASCII)
DEPENDENCY_TABLES = ("dependencies", "dev-dependencies", "build-dependencies")


class CargoSnapshotError(RuntimeError):
    """A selected cohort is mutable, incomplete, or escapes its snapshot."""


@dataclass(frozen=True)
class SelectedRepository:
    """One repository selected at an immutable commit identity."""
    repository: Path
    revision: str


@dataclass(frozen=True)
class CargoSnapshot:
    """A complete selected topology and its committed lock roots."""
    root: Path
    basis: tuple[tuple[str, str], ...]
    locks: tuple[PurePosixPath, ...]
    lock_bytes: tuple[tuple[PurePosixPath, bytes], ...]


def _selection(name: str, selected: SelectedRepository) -> None:
    if MEMBER_NAME.fullmatch(name) is None:
        raise CargoSnapshotError(f"unsafe selected repository name: {name!r}")
    if COMMIT_ID.fullmatch(selected.revision) is None:
        raise CargoSnapshotError(f"selected revision is not a full commit ID: {name!r}")
    resolved = execute(
        selected.repository,
        ("rev-parse", "--verify", f"{selected.revision}^{{commit}}"),
        timeout=PROCESS_TIMEOUT_SECONDS,
    )
    commit = resolved.stdout.decode("ascii", errors="replace").strip()
    if resolved.returncode or commit != selected.revision:
        raise CargoSnapshotError(f"selected revision is not that commit: {name!r}")


def _inside(root: Path, manifest: Path, raw: str, field: str) -> None:
    if not raw or "\\" in raw:
        raise CargoSnapshotError(f"{manifest}: unsafe {field} path")
    path = Path(raw)
    if path.is_absolute():
        raise CargoSnapshotError(f"{manifest}: absolute {field} path escapes the snapshot")
    target = (manifest.parent / path).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as error:
        raise CargoSnapshotError(f"{manifest}: {field} path escapes the snapshot") from error


def _dependency_paths(root: Path, manifest: Path, table: object, field: str) -> None:
    if table is None:
        return
    if not isinstance(table, dict):
        raise CargoSnapshotError(f"{manifest}: {field} is not a table")
    for dependency, specification in table.items():
        if isinstance(specification, dict) and "path" in specification:
            path = specification["path"]
            if not isinstance(path, str):
                raise CargoSnapshotError(f"{manifest}: dependency {dependency!r} path is not text")
            _inside(root, manifest, path, f"dependency {dependency!r}")


def _manifest_paths(root: Path, manifest: Path) -> None:
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise CargoSnapshotError(f"cannot read selected manifest {manifest}: {error}") from error
    package = document.get("package")
    if isinstance(package, dict) and "workspace" in package:
        workspace = package["workspace"]
        if not isinstance(workspace, str):
            raise CargoSnapshotError(f"{manifest}: package.workspace is not text")
        _inside(root, manifest, workspace, "package.workspace")
    workspace = document.get("workspace")
    if isinstance(workspace, dict):
        for field in ("members", "exclude"):
            values = workspace.get(field, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise CargoSnapshotError(f"{manifest}: workspace.{field} is not a string list")
            for value in values:
                _inside(root, manifest, value, f"workspace.{field}")
        _dependency_paths(root, manifest, workspace.get("dependencies"), "workspace.dependencies")
    for field in DEPENDENCY_TABLES:
        _dependency_paths(root, manifest, document.get(field), field)
    targets = document.get("target", {})
    if not isinstance(targets, dict):
        raise CargoSnapshotError(f"{manifest}: target is not a table")
    for target, tables in targets.items():
        if not isinstance(tables, dict):
            raise CargoSnapshotError(f"{manifest}: target {target!r} is not a table")
        for field in DEPENDENCY_TABLES:
            _dependency_paths(root, manifest, tables.get(field), f"target.{target}.{field}")


def create_snapshot(
    selections: Mapping[str, SelectedRepository], destination: Path
) -> CargoSnapshot:
    """Export and confine every selected input before Cargo can read it."""
    if destination.exists():
        raise CargoSnapshotError(f"snapshot destination already exists: {destination}")
    repos = destination / "repos"
    repos.mkdir(parents=True)
    for name, selected in sorted(selections.items()):
        _selection(name, selected)
        member = repos / name
        member.mkdir()
        try:
            extract_archive(
                archive(selected.repository, selected.revision, timeout=PROCESS_TIMEOUT_SECONDS),
                member,
            )
        except (OSError, RuntimeError) as error:
            raise CargoSnapshotError(f"cannot export selected member {name!r}: {error}") from error
        for required in ("Cargo.toml", "Cargo.lock"):
            if not member.joinpath(required).is_file():
                raise CargoSnapshotError(f"selected member {name!r} has no root {required}")
    for manifest in repos.rglob("Cargo.toml"):
        _manifest_paths(destination, manifest)
    locks = tuple(sorted(PurePosixPath(lock.relative_to(destination).as_posix())
                         for lock in repos.rglob("Cargo.lock")))
    for lock in locks:
        if not destination.joinpath(lock).with_name("Cargo.toml").is_file():
            raise CargoSnapshotError(f"lock has no root manifest: {lock}")
    basis = tuple((name, selected.revision) for name, selected in sorted(selections.items()))
    contents = tuple((lock, destination.joinpath(lock).read_bytes()) for lock in locks)
    return CargoSnapshot(destination, basis, locks, contents)
