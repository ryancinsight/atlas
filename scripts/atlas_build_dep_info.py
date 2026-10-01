"""The files outside its own directory that a path package's units read.

A path package's identity covers only the files of its own directory
(`atlas_build_package_identity`). Its units can read others: an
`include_str!` or `#[path]` module in a sibling directory, a build script's
watched path. Cargo names them in the unit's dep-info (`deps/*.d`, and a
build script's `build/<unit>/*.d`) and in the build script's
`build/<unit>/output` (`rerun-if-changed`). A record lists each such file
by a path stable across exports with its digest, and every run hashes the
listed files again: a moved one makes its package stale.
"""

from __future__ import annotations

import functools
import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping

from atlas_build_artifacts import UNVERIFIED, artifact_package, metadata_artifact_owners
from atlas_build_lease import BuildIdentityError
from atlas_build_package_identity import repository_top
from atlas_build_snapshot import _cargo_metadata
from atlas_build_source import _canonical, _cargo_home, _is_within

# A recorded path that names nothing on disk now.
MISSING = "missing"


@dataclass(frozen=True)
class PackageLayout:
    """Where a workspace's path packages live, read from one `cargo metadata`."""

    workspace_root: Path
    # Every path package's directory by name; None when two share a name.
    directories: Mapping[str, Path | None]
    owners: Mapping[str, frozenset[str]]
    repositories: tuple[Path, ...]
    skipped: tuple[Path, ...]

    @functools.cached_property
    def packages(self) -> dict[Path, str]:
        return {directory: name for name, directory in self.directories.items() if directory}

    def bucket(self, path: Path) -> str | None:
        """The path package whose directory is the deepest one containing `path`."""
        for directory in (path, *path.parents):
            if directory in self.packages:
                return self.packages[directory]
        return None


def package_layout(manifest: Path, metadata_cwd: Path, target_dir: Path) -> PackageLayout:
    metadata = _cargo_metadata(manifest, metadata_cwd, no_deps=False)
    try:
        workspace_root = _canonical(Path(str(metadata["workspace_root"])))
        listed: dict[str, list[Path]] = {}
        for value in metadata["packages"]:
            if value.get("source") is None:
                directory = _canonical(Path(str(value["manifest_path"]))).parent
                listed.setdefault(str(value["name"]), []).append(directory)
    except (KeyError, TypeError) as error:
        raise BuildIdentityError(f"malformed cargo metadata for {manifest}") from error
    directories = {name: found[0] if len(found) == 1 else None for name, found in listed.items()}
    tops = {repository_top(directory) for found in listed.values() for directory in found}
    return PackageLayout(
        workspace_root,
        directories,
        metadata_artifact_owners(metadata, manifest),
        tuple(sorted(tops | {workspace_root})),
        (_canonical(target_dir), _canonical(_cargo_home())),
    )


@functools.cache
def _sysroot() -> Path | None:
    try:
        result = subprocess.run(
            [os.environ.get("RUSTC", "rustc"), "--print", "sysroot"],
            check=False, capture_output=True, timeout=60, text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _canonical(Path(result.stdout.strip())) if result.returncode == 0 else None


def _unit_input(relative: str) -> str | None:
    """`dep-info`, `output` (a build script's), or None for any other recorded file."""
    parts = relative.split("/")
    if len(parts) >= 3 and parts[-3] == "build":
        if parts[-1] == "output":
            return "output"
        return "dep-info" if parts[-1].endswith(".d") else None
    if len(parts) >= 2 and parts[-2] == "deps" and parts[-1].endswith(".d"):
        return "dep-info"
    return None


def _dep_info_paths(text: str) -> set[str]:
    """Every prerequisite a Makefile-syntax dep-info file names.

    rustc escapes only a space (`\\ `). A line without `: ` is a phony
    target repeating a prerequisite; `#` lines name environment variables.
    """
    paths: set[str] = set()
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        _, separator, prerequisites = line.partition(": ")
        if not separator:
            continue
        word: list[str] = []
        index = 0
        while index < len(prerequisites):
            character = prerequisites[index]
            if character == "\\" and prerequisites[index + 1 : index + 2] == " ":
                word.append(" ")
                index += 2
                continue
            if character == " ":
                if word:
                    paths.add("".join(word))
                word = []
            else:
                word.append(character)
            index += 1
        if word:
            paths.add("".join(word))
    return paths


_VERBATIM = "\\\\?\\"
_VERBATIM_UNC = _VERBATIM + "UNC\\"


def _plain(path: str) -> str:
    """`path` without a Windows verbatim prefix, which clippy gives `clippy.toml`."""
    if path.startswith(_VERBATIM_UNC):
        return "\\\\" + path[len(_VERBATIM_UNC) :]
    return path[len(_VERBATIM) :] if path.startswith(_VERBATIM) else path


def _watched_paths(text: str) -> set[str]:
    paths = set()
    for line in text.splitlines():
        for prefix in ("cargo:rerun-if-changed=", "cargo::rerun-if-changed="):
            if line.startswith(prefix):
                paths.add(line[len(prefix) :].strip())
    return paths


def _digest(path: Path) -> str | None:
    """A file's bytes; a directory's every file, as Cargo scans a watched one.

    None when it cannot be read, which equals no recorded digest.
    """
    try:
        if path.is_dir():
            digest = hashlib.sha256()
            for file in sorted(item for item in path.rglob("*") if item.is_file()):
                digest.update(file.relative_to(path).as_posix().encode("utf-8", "surrogateescape"))
                digest.update(b"\0" + hashlib.sha256(file.read_bytes()).digest())
            return "dir:" + digest.hexdigest()
        if not path.exists():
            return MISSING
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


# A dep-info path this record does not list: the package's own directory
# (its identity covers it), the shared target, Cargo's home or the toolchain.
_OWN = object()


def _stable_key(path: Path, package: str, layout: PackageLayout) -> object:
    """The record's key for `path`, `_OWN`, or None for a file in no tree of ours."""
    # Resolved only when the path as written matches no tree: an 8.3 name
    # or a link spells a tree another way.
    for resolve in (False, True):
        candidate = _canonical(path) if resolve else path
        if any(_is_within(candidate, root) for root in layout.skipped):
            return _OWN
        if layout.bucket(candidate) == package:
            return _OWN
        if _is_within(candidate, layout.workspace_root):
            return candidate.relative_to(layout.workspace_root).as_posix()
        if any(_is_within(candidate, top) for top in layout.repositories):
            return candidate.as_posix()
    sysroot = _sysroot()
    if sysroot is not None and _is_within(_canonical(path), sysroot):
        return _OWN
    return None


def _package_inputs(package: str, units: list[tuple[str, Path]], layout: PackageLayout) -> object:
    directory = layout.directories.get(package)
    if directory is None:
        return UNVERIFIED
    paths: set[Path] = set()
    for kind, unit in units:
        try:
            text = unit.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            # Rewritten by a peer's Cargo: the next run cleans the package.
            return UNVERIFIED
        # rustc runs in the workspace root, so a member's dep-info paths
        # are relative to it; a build script's watched paths are relative to
        # its package, as Cargo resolves them.
        base, entries = (
            (layout.workspace_root, _dep_info_paths(text))
            if kind == "dep-info"
            else (directory, _watched_paths(text))
        )
        paths.update(Path(os.path.normpath(base / _plain(entry))) for entry in entries)
    files: dict[str, str] = {}
    for path in paths:
        key = _stable_key(path, package, layout)
        if key is _OWN:
            continue
        digest = _digest(path)
        if key is None or digest is None:
            return UNVERIFIED
        files[str(key)] = digest
    return dict(sorted(files.items()))


def record_inputs(
    target_dir: Path,
    names: Iterable[str],
    packages: Iterable[str],
    layout: Callable[[], PackageLayout],
) -> dict[str, object]:
    """Each of `packages`' inputs outside its directory, from the recorded files `names`.

    `UNVERIFIED` replaces a package's inputs when a file its units read is
    in no tree of ours -- not the workspace, a path package's repository,
    the target, Cargo's home or the toolchain -- or when a unit's dep-info
    cannot be read or attributed: it equals no re-hash, so the next run
    cleans that package.
    """
    found: dict[str, list[tuple[str, Path]]] = {package: [] for package in packages}
    for relative in sorted(names):
        kind = _unit_input(relative)
        if kind is None:
            continue
        owner = artifact_package(relative, layout().owners)
        if owner is None:
            return {package: UNVERIFIED for package in found}
        if owner in found:
            found[owner].append((kind, target_dir / relative))
    return {
        package: _package_inputs(package, units, layout()) if units else {}
        for package, units in sorted(found.items())
    }


def current_inputs(recorded: object, layout: Callable[[], PackageLayout]) -> dict[str, object]:
    """`recorded`'s inputs hashed again now; an `UNVERIFIED` package reads as None."""
    if not isinstance(recorded, dict):
        return {}
    current: dict[str, object] = {}
    for package, files in recorded.items():
        if not isinstance(files, dict):
            current[package] = None
            continue
        current[package] = {
            key: _digest(Path(key) if Path(key).is_absolute() else layout().workspace_root / key)
            for key in files
        }
    return current
