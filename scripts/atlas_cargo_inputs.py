#!/usr/bin/env python3
"""Map changed repository paths to their owning Cargo workspace inputs."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tomllib
from typing import Iterable, Mapping


_PACKAGE = re.compile(r"^\[package\]", re.MULTILINE)
_WORKSPACE = re.compile(r"^\[workspace\]", re.MULTILINE)
_GLOBAL_INPUTS = frozenset(
    {".config/nextest.toml", "rust-toolchain", "rust-toolchain.toml"}
)


@dataclass(frozen=True)
class CargoInputOwners:
    """The workspace packages and external manifests selected by changed paths."""

    packages: tuple[str, ...]
    untestable_packages: tuple[str, ...]
    excluded_manifests: tuple[str, ...]
    standalone_manifests: tuple[str, ...]


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _manifest_sections(path: Path) -> tuple[bool, bool] | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return _PACKAGE.search(text) is not None, _WORKSPACE.search(text) is not None


def _skip_non_cargo(repository_path: str) -> bool:
    if repository_path.startswith((".githooks/", ".github/")):
        return True
    if repository_path in {"backlog.md", "gap_audit.md", "checklist.md"}:
        return True
    if repository_path.startswith("backlog/"):
        relative = repository_path.removeprefix("backlog/")
        return "/" not in relative and relative.endswith(".md")
    return False


_PROSE_SUFFIXES = (".md", ".markdown")
_PATH_BOUNDARY = frozenset('"/\\')
_EXTENSION_LITERALS = ('.md"', '"md"', ".markdown", "*.md")


def _raise(error: OSError) -> None:
    raise error


def _rust_source_text(root: Path) -> str:
    """Concatenate every Rust source under `root`, lowercased.

    Only the root `.git` is skipped, so `target` or `.git` directories deeper
    in the tree are scanned. An unreadable directory or file raises: the
    caller exits non-zero and the hook blocks the push.
    """
    chunks: list[str] = []
    top = os.fspath(root)
    for directory, subdirectories, names in os.walk(root, onerror=_raise):
        if directory == top and ".git" in subdirectories:
            subdirectories.remove(".git")
        for name in names:
            if name.endswith(".rs"):
                path = Path(directory) / name
                chunks.append(path.read_text(encoding="utf-8", errors="replace").lower())
    return "\n".join(chunks)


class _RustSources:
    """The lowercased text of every Rust source, and the file spellings found in it."""

    def __init__(self, root: Path) -> None:
        self._text = _rust_source_text(root)
        self._extension = any(literal in self._text for literal in _EXTENSION_LITERALS)
        self._bounded: dict[str, bool] = {}

    def _spells(self, component: str) -> bool:
        """Whether `component` occurs with a quote or path separator on both sides."""
        if component not in self._bounded:
            text, found = self._text, False
            start = text.find(component)
            while start != -1 and not found:
                end = start + len(component)
                found = (
                    start > 0
                    and end < len(text)
                    and text[start - 1] in _PATH_BOUNDARY
                    and text[end] in _PATH_BOUNDARY
                )
                start = text.find(component, start + 1)
            self._bounded[component] = found
        return self._bounded[component]

    def may_read(self, relative: PurePosixPath) -> bool:
        """Whether some source text can name `relative`, its stem or an ancestor directory.

        A source containing `.md"`, `"md"`, `.markdown` or `*.md` also counts:
        a directory walk filtering by extension reaches any Markdown file
        without spelling it.
        """
        if self._extension:
            return True
        keys = (relative.name, relative.stem, *relative.parts[:-1])
        return any(self._spells(key.lower()) for key in keys if key)


def _text_list(value: object) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def _names(value: object, claimed: str) -> bool:
    """Whether a manifest path value is the claimed file, or is not a string at all."""
    if not isinstance(value, str):
        return True
    return PurePosixPath(value.replace("\\", "/")).as_posix().lower() == claimed


def _manifest_claims(manifest: Path, package_relative: str) -> bool:
    """Whether the package manifest can make Cargo read or package the file.

    A manifest with an `include` key claims every file, as does a malformed
    manifest or a `readme`, `license-file`, `exclude` or `build` value not
    interpreted here (`readme.workspace = true`, a non-string).
    """
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return True
    package = document.get("package")
    if not isinstance(package, dict):
        return True
    claimed = package_relative.lower()
    readme = package.get("readme", True)
    if readme is not False and _names("README.md" if readme is True else readme, claimed):
        return True
    license_file = package.get("license-file")
    if license_file is not None and _names(license_file, claimed):
        return True
    if "include" in package or ("exclude" in package and _text_list(package["exclude"]) is None):
        return True
    return not isinstance(package.get("build", False), (str, bool))


def _is_prose_only(
    root: Path, package_directory: PurePosixPath, changed_path: str, sources: list[_RustSources]
) -> bool:
    """A Markdown file no package target or manifest field can reach.

    Reachability is decided from text, not by running Cargo, and errs toward
    the gate. A file is reachable when the manifest names it (`readme`,
    `license-file`, the default `README.md`) or has an `include` key, or when
    any Rust source in the repository, comments included and case ignored,
    spells its name, its stem or an ancestor directory bounded on both sides
    by a quote or a path separator, or contains `.md"`, `"md"`, `.markdown`
    or `*.md`. A reader that spells a path as string literals (`include_str!`,
    `#[path]`, `concat!`-built paths, a build script or test reading a named
    directory) therefore reaches the file through one of those spellings. The
    cost is breadth: a source containing `"docs"` or a URL with `/docs/` makes
    every file under `docs/` reachable, and any `include_str!("x.md")` makes
    every Markdown file reachable.

    Not covered: a reader that spells no component and no extension, such as a
    build script or test reading every file under `.` and filtering by content.
    Gating on any directory enumeration (`read_dir`, `walkdir`, `glob`) would
    catch it; this function does not.
    """
    path = PurePosixPath(changed_path)
    if path.suffix.lower() not in _PROSE_SUFFIXES:
        return False
    relative = path.relative_to(package_directory)
    if _manifest_claims(root / package_directory / "Cargo.toml", relative.as_posix()):
        return False
    if not sources:
        sources.append(_RustSources(root))
    return not sources[0].may_read(relative)


def cargo_input_owners(
    root: Path,
    workspace_manifest: str,
    metadata: Mapping[str, object],
    changed_paths: Iterable[str],
) -> CargoInputOwners:
    """Classify changed paths using one Cargo metadata document."""
    packages_value = metadata.get("packages")
    members_value = metadata.get("workspace_members")
    if not isinstance(packages_value, list) or not isinstance(members_value, list):
        raise ValueError("Cargo metadata must contain packages and workspace_members arrays")
    members = set(members_value)
    manifests: dict[str, str] = {}
    workspace_packages: list[str] = []
    untestable: list[str] = []
    root = root.resolve()
    for package in packages_value:
        if not isinstance(package, dict) or package.get("id") not in members:
            continue
        name, manifest = package.get("name"), package.get("manifest_path")
        if not isinstance(name, str) or not isinstance(manifest, str):
            raise ValueError("workspace package metadata must name its manifest")
        relative = os.path.relpath(os.path.realpath(manifest), root).replace(os.sep, "/")
        manifests[relative] = name
        workspace_packages.append(name)
        targets = package.get("targets")
        if isinstance(targets, list) and targets and not any(
            isinstance(target, dict) and target.get("test", True) for target in targets
        ):
            untestable.append(name)

    selected: list[str] = []
    excluded: list[str] = []
    standalone: list[str] = []
    workspace_prefix = PurePosixPath(workspace_manifest).parent
    gate_manifest = root / "Cargo.toml"
    gate_sections = _manifest_sections(gate_manifest)
    sources: list[_RustSources] = []
    for changed_path in changed_paths:
        if not changed_path:
            continue
        repository_path = (workspace_prefix / changed_path).as_posix()
        if _skip_non_cargo(repository_path):
            continue
        if changed_path in _GLOBAL_INPUTS or changed_path.startswith(".cargo/"):
            for package in workspace_packages:
                _append_unique(selected, package)
            continue
        directory = PurePosixPath(changed_path).parent
        package_directory: PurePosixPath | None = None
        excluded_manifest: str | None = None
        while directory not in {PurePosixPath("."), PurePosixPath("/")}:
            manifest = root / directory.as_posix() / "Cargo.toml"
            sections = _manifest_sections(manifest)
            if sections is not None:
                has_package, has_workspace = sections
                if has_package:
                    package_directory = directory
                elif has_workspace:
                    excluded_manifest = (directory / "Cargo.toml").as_posix()
                break
            directory = directory.parent
        if excluded_manifest is not None:
            _append_unique(excluded, excluded_manifest)
            continue
        if (
            package_directory is None
            and changed_path == "Cargo.toml"
            and gate_sections is not None
            and gate_sections[1]
        ):
            for package in workspace_packages:
                _append_unique(selected, package)
            continue
        if package_directory is None:
            if gate_sections is None or not gate_sections[0]:
                continue
            package_directory = PurePosixPath(".")
        if _is_prose_only(root, package_directory, changed_path, sources):
            continue
        relative_manifest = (package_directory / "Cargo.toml").as_posix()
        if relative_manifest.startswith("./"):
            relative_manifest = relative_manifest[2:]
        package_name = manifests.get(relative_manifest)
        if package_name is None:
            _append_unique(standalone, relative_manifest)
        else:
            _append_unique(selected, package_name)
    return CargoInputOwners(
        tuple(selected), tuple(untestable), tuple(excluded), tuple(standalone)
    )


def main() -> None:
    """Read metadata and changed paths, then emit stable tab-separated records."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--workspace-manifest", required=True)
    parser.add_argument("--changed-paths", required=True, type=Path)
    arguments = parser.parse_args()
    metadata = json.load(sys.stdin)
    changed = arguments.changed_paths.read_text(encoding="utf-8").splitlines()
    owners = cargo_input_owners(
        arguments.root, arguments.workspace_manifest, metadata, changed
    )
    sys.stdout.reconfigure(newline="\n")
    for kind, values in (
        ("package", owners.packages),
        ("untestable", owners.untestable_packages),
        ("excluded", owners.excluded_manifests),
        ("standalone", owners.standalone_manifests),
    ):
        for value in values:
            print(f"{kind}\t{value}")


if __name__ == "__main__":
    main()
