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
