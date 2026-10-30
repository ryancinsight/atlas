"""Immutable, path-confined Cargo source cohorts."""
from __future__ import annotations

import os
import re
import tempfile
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from atlas_git_process import execute

PROCESS_TIMEOUT_SECONDS = 60
READ_BATCH_BYTES = 32 * 1024 * 1024
READ_BATCH_ENTRIES = 10_000
COPY_BYTES = 1024 * 1024
MEMBER_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*", re.ASCII)
COMMIT_ID = re.compile(r"[0-9a-f]{40}", re.ASCII)
DEPENDENCY_TABLES = ("dependencies", "dev-dependencies", "build-dependencies")
WINDOWS_DEVICE = re.compile(
    r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", re.IGNORECASE | re.ASCII
)


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
    resolved = execute(selected.repository,
        ("--no-replace-objects", "rev-parse", "--verify", f"{selected.revision}^{{commit}}"),
        timeout=PROCESS_TIMEOUT_SECONDS,
    )
    commit = resolved.stdout.decode("ascii", errors="replace").strip()
    if resolved.returncode or commit != selected.revision:
        raise CargoSnapshotError(f"selected revision is not that commit: {name!r}")

def _tree_path(
    name: str, seen: dict[tuple[str, ...], tuple[tuple[str, ...], bool]]
) -> PurePosixPath:
    parts = tuple(name.split("/"))
    path = PurePosixPath(name)
    if (path.is_absolute() or PureWindowsPath(name).drive or
            any(not part or part in {".", ".."} or "\\" in part or ":" in part or
                part.endswith((" ", ".")) or any(ord(character) < 32 for character in part) or
                WINDOWS_DEVICE.fullmatch(part) for part in parts)):
        raise CargoSnapshotError(f"selected tree has an unsafe path: {name!r}")
    for length in range(1, len(parts) + 1):
        prefix = parts[:length]
        key = tuple(part.casefold() for part in prefix)
        leaf = length == len(parts)
        previous = seen.get(key)
        if previous is not None and (previous[0] != prefix or previous[1] or leaf):
            raise CargoSnapshotError(f"selected tree has a host path collision: {name!r}")
        seen.setdefault(key, (prefix, leaf))
    return path


def _export(selected: SelectedRepository, destination: Path) -> None:
    environment = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
    listing = execute(selected.repository,
        ("--no-replace-objects", "ls-tree", "-r", "-l", "-z", "--full-tree",
         selected.revision), env=environment, timeout=PROCESS_TIMEOUT_SECONDS,
    )
    if listing.returncode:
        detail = listing.stderr.decode("utf-8", errors="replace").strip()
        raise CargoSnapshotError(detail or "cannot list selected tree")
    entries = []
    try:
        records = listing.stdout.decode("utf-8").split("\0")
    except UnicodeDecodeError as error:
        raise CargoSnapshotError("selected tree has a non-UTF-8 path") from error
    seen = {}
    for record in filter(None, records):
        head, separator, name = record.partition("\t")
        fields = head.split()
        if (not separator or len(fields) != 4 or fields[1] != "blob" or
                fields[0] not in {"100644", "100755"}):
            raise CargoSnapshotError(f"selected tree has an unsupported entry: {name!r}")
        path = _tree_path(name, seen)
        try:
            size = int(fields[3])
        except ValueError as error:
            raise CargoSnapshotError(f"selected blob has no size: {name!r}") from error
        entries.append((fields[0], fields[2], path, size))
    position = 0
    while position < len(entries):
        count = 0
        size = 0
        while position + count < len(entries) and count < READ_BATCH_ENTRIES:
            candidate = entries[position + count][3]
            if count and size + candidate > READ_BATCH_BYTES:
                break
            count += 1
            size += candidate
        batch = entries[position:position + count]
        position += count
        request = b"".join(f"{blob}\n".encode("ascii") for _, blob, _, _ in batch)
        with tempfile.TemporaryFile(mode="w+b") as stream:
            objects = execute(
                selected.repository, ("--no-replace-objects", "cat-file", "--batch"),
                stdin=request, env=environment, stdout_destination=stream,
                timeout=PROCESS_TIMEOUT_SECONDS,
            )
            if objects.returncode:
                raise CargoSnapshotError("cannot read selected tree blobs")
            stream.seek(0)
            for mode, blob, path, expected_size in batch:
                fields = stream.readline().removesuffix(b"\n").split()
                if len(fields) != 3 or fields[:2] != [blob.encode(), b"blob"]:
                    raise CargoSnapshotError(f"cannot read selected blob: {path}")
                size = int(fields[2])
                if size != expected_size:
                    raise CargoSnapshotError(f"selected blob size changed: {path}")
                target = destination.joinpath(*path.parts)
                try:
                    target.resolve().relative_to(destination.resolve())
                except ValueError as error:
                    raise CargoSnapshotError(f"selected tree path escapes its member: {path}") from error
                current = destination
                for part in path.parent.parts:
                    current /= part
                    try:
                        current.mkdir()
                    except FileExistsError:
                        if current.is_symlink() or not current.is_dir():
                            raise CargoSnapshotError(f"selected tree directory aliases a file: {path}")
                try:
                    with target.open("xb") as output:
                        remaining = size
                        while remaining:
                            payload = stream.read(min(COPY_BYTES, remaining))
                            if not payload:
                                raise CargoSnapshotError(f"selected blob is truncated: {path}")
                            output.write(payload)
                            remaining -= len(payload)
                except FileExistsError as error:
                    raise CargoSnapshotError(f"selected tree file already exists: {path}") from error
                if stream.read(1) != b"\n":
                    raise CargoSnapshotError(f"selected blob is truncated: {path}")
                target.chmod(0o755 if mode == "100755" else 0o644)
            if stream.read(1):
                raise CargoSnapshotError("selected blob batch has trailing data")

def _reject_external_workspace(destination: Path) -> None:
    for ancestor in destination.resolve().parents:
        if ancestor.joinpath("Cargo.toml").is_file():
            raise CargoSnapshotError(f"snapshot destination has external workspace: {ancestor}")


def _allowed(target: Path, roots: tuple[Path, ...]) -> bool:
    resolved = target.resolve()
    return any(resolved == root or root in resolved.parents for root in roots)

def _inside(root: Path, manifest: Path, raw: str, field: str,
            allowed_roots: tuple[Path, ...]) -> None:
    if not raw or "\\" in raw:
        raise CargoSnapshotError(f"{manifest}: unsafe {field} path")
    path = Path(raw)
    if PurePosixPath(raw).is_absolute() or PureWindowsPath(raw).drive:
        raise CargoSnapshotError(f"{manifest}: absolute {field} path escapes the snapshot")
    target = (manifest.parent / path).resolve()
    if not _allowed(target, allowed_roots):
        raise CargoSnapshotError(f"{manifest}: {field} path escapes the selected repositories")

def _dependency_paths(root: Path, manifest: Path, table: object, field: str,
                      allowed_roots: tuple[Path, ...]) -> None:
    if table is None:
        return
    if not isinstance(table, dict):
        raise CargoSnapshotError(f"{manifest}: {field} is not a table")
    for dependency, specification in table.items():
        if isinstance(specification, dict) and "path" in specification:
            path = specification["path"]
            if not isinstance(path, str):
                raise CargoSnapshotError(f"{manifest}: dependency {dependency!r} path is not text")
            _inside(root, manifest, path, f"dependency {dependency!r}", allowed_roots)

def _source_path(root: Path, manifest: Path, target: object, field: str,
                 allowed_roots: tuple[Path, ...]) -> None:
    if not isinstance(target, dict):
        raise CargoSnapshotError(f"{manifest}: {field} is not a table")
    if "path" in target:
        path = target["path"]
        if not isinstance(path, str):
            raise CargoSnapshotError(f"{manifest}: {field}.path is not text")
        _inside(root, manifest, path, f"{field}.path", allowed_roots)

def _manifest_paths(root: Path, manifest: Path, allowed_roots: tuple[Path, ...]) -> None:
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise CargoSnapshotError(f"cannot read selected manifest {manifest}: {error}") from error
    package = document.get("package")
    if isinstance(package, dict) and "workspace" in package:
        workspace = package["workspace"]
        if not isinstance(workspace, str):
            raise CargoSnapshotError(f"{manifest}: package.workspace is not text")
        _inside(root, manifest, workspace, "package.workspace", allowed_roots)
    if isinstance(package, dict) and isinstance(package.get("build"), str):
        _inside(root, manifest, package["build"], "package.build", allowed_roots)
    workspace = document.get("workspace")
    if isinstance(workspace, dict):
        for field in ("members", "exclude"):
            values = workspace.get(field, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                raise CargoSnapshotError(f"{manifest}: workspace.{field} is not a string list")
            for value in values:
                _inside(root, manifest, value, f"workspace.{field}", allowed_roots)
        _dependency_paths(root, manifest, workspace.get("dependencies"),
                          "workspace.dependencies", allowed_roots)
    for field in DEPENDENCY_TABLES:
        _dependency_paths(root, manifest, document.get(field), field, allowed_roots)
    _dependency_paths(root, manifest, document.get("replace"), "replace", allowed_roots)
    patches = document.get("patch", {})
    if not isinstance(patches, dict):
        raise CargoSnapshotError(f"{manifest}: patch is not a table")
    for source, table in patches.items():
        _dependency_paths(root, manifest, table, f"patch.{source}", allowed_roots)
    if "lib" in document:
        _source_path(root, manifest, document["lib"], "lib", allowed_roots)
    for field in ("bin", "test", "bench", "example"):
        targets = document.get(field, [])
        if not isinstance(targets, list):
            raise CargoSnapshotError(f"{manifest}: {field} is not an array")
        for index, target in enumerate(targets):
            _source_path(root, manifest, target, f"{field}[{index}]", allowed_roots)
    targets = document.get("target", {})
    if not isinstance(targets, dict):
        raise CargoSnapshotError(f"{manifest}: target is not a table")
    for target, tables in targets.items():
        if not isinstance(tables, dict):
            raise CargoSnapshotError(f"{manifest}: target {target!r} is not a table")
        for field in DEPENDENCY_TABLES:
            _dependency_paths(root, manifest, tables.get(field),
                              f"target.{target}.{field}", allowed_roots)


def confine_manifests(manifests: Iterable[Path], allowed_roots: Iterable[Path]) -> None:
    """Reject Cargo-discovered filesystem inputs outside explicit repositories."""
    roots = tuple(root.resolve() for root in allowed_roots)
    if not roots:
        raise CargoSnapshotError("no repositories define the Cargo input boundary")
    for manifest in manifests:
        if not _allowed(manifest, roots):
            raise CargoSnapshotError(f"Cargo manifest is outside selected repositories: {manifest}")
        for ancestor in manifest.resolve().parents:
            candidate = ancestor / "Cargo.toml"
            if candidate.is_file() and not _allowed(candidate, roots):
                raise CargoSnapshotError(f"Cargo manifest has an external ancestor: {candidate}")
        _manifest_paths(roots[0].parent, manifest, roots)

def create_snapshot(
    selections: Mapping[str, SelectedRepository], destination: Path
) -> CargoSnapshot:
    """Export and confine every selected input before Cargo can read it."""
    if destination.exists():
        raise CargoSnapshotError(f"snapshot destination already exists: {destination}")
    _reject_external_workspace(destination)
    repos = destination / "repos"
    repos.mkdir(parents=True)
    for name, selected in sorted(selections.items()):
        _selection(name, selected)
        member = repos / name
        member.mkdir()
        try:
            _export(selected, member)
        except (OSError, RuntimeError) as error:
            raise CargoSnapshotError(f"cannot export selected member {name!r}: {error}") from error
        for required in ("Cargo.toml", "Cargo.lock"):
            if not member.joinpath(required).is_file():
                raise CargoSnapshotError(f"selected member {name!r} has no root {required}")
    confine_manifests(repos.rglob("Cargo.toml"), (destination,))
    locks = tuple(sorted(PurePosixPath(lock.relative_to(destination).as_posix())
                         for lock in repos.rglob("Cargo.lock")))
    for lock in locks:
        if not destination.joinpath(lock).with_name("Cargo.toml").is_file():
            raise CargoSnapshotError(f"lock has no root manifest: {lock}")
    basis = tuple((name, selected.revision) for name, selected in sorted(selections.items()))
    contents = tuple((lock, destination.joinpath(lock).read_bytes()) for lock in locks)
    return CargoSnapshot(destination, basis, locks, contents)
