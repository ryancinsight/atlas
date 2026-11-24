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
_PROGRAM_FILES = frozenset({"config", "config.toml", "nextest.toml"})
_DEPENDENCY_TABLES = frozenset(
    {"dependencies", "dev-dependencies", "build-dependencies", "dev_dependencies", "build_dependencies"}
)
_CAPABILITY = re.compile(
    r"\b(?:fs|process|env|read_dir|extern|asm|global_asm|naked_asm)\b|\binclude\s*!"
    r'|\bpath\s*=(?!\s*"[^"\x5c]*\.rs")'
)
_INCLUDE_CALL = re.compile(r"\binclude_(?:str|bytes)\s*!")
_INCLUDE_LITERAL = re.compile(r'\binclude_(?:str|bytes)\s*!\s*\(\s*"([^"\x5c]*)"\s*\)')
_UNSUPPORTED_GLOB = re.compile(r"[\[\]\\]")


def _raise(error: OSError) -> None:
    raise error


def _manifest_runs_unscanned_code(node: object) -> bool:
    """Whether a parsed manifest declares a dependency or a target path not ending `.rs`."""
    if isinstance(node, list):
        return any(_manifest_runs_unscanned_code(item) for item in node)
    return isinstance(node, dict) and any(
        (key in _DEPENDENCY_TABLES and bool(value))
        or (key in {"path", "build"} and isinstance(value, str) and not value.lower().endswith(".rs"))
        or _manifest_runs_unscanned_code(value)
        for key, value in node.items()
    )


def _scan(root: Path) -> tuple[str, bool]:
    """The lowercased Rust sources under `root`, and whether tracked files run other code.

    Other code is a symlink, a Cargo or nextest config, or a manifest that
    declares a dependency, cannot be parsed or names a target not ending `.rs`.
    Only the root `.git` is skipped; an unreadable path raises, so the hook blocks.
    """
    rust, other = [], False
    top = os.fspath(root)
    for directory, subdirectories, names in os.walk(root, onerror=_raise):
        if directory == top and ".git" in subdirectories:
            subdirectories.remove(".git")
        other = other or any(os.path.islink(os.path.join(directory, n)) for n in (*names, *subdirectories))
        for name in names:
            lowered, path = name.lower(), Path(directory) / name
            if lowered.endswith(".rs"):
                rust.append(path.read_text(encoding="utf-8", errors="replace").lower())
            elif lowered in _PROGRAM_FILES:
                other = True
            elif lowered == "cargo.toml":
                try:
                    manifest = tomllib.loads(path.read_text(encoding="utf-8"))
                    other = other or _manifest_runs_unscanned_code(manifest)
                except (tomllib.TOMLDecodeError, UnicodeDecodeError):
                    other = True
    return "\n".join(rust), other


class _RustSources:
    """What the Rust sources of a repository can make Cargo read."""

    def __init__(self, root: Path) -> None:
        text, other = _scan(root)
        literals = _INCLUDE_LITERAL.findall(text)
        self._unscanned = (
            other or _CAPABILITY.search(text) is not None or len(literals) != len(_INCLUDE_CALL.findall(text))
        )
        self._included = {literal.rsplit("/", 1)[-1] for literal in literals}

    def may_read(self, relative: PurePosixPath) -> bool:
        """Whether the proof that no source reads `relative` fails."""
        return self._unscanned or relative.name.lower() in self._included


def _text_list(value: object) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def _include_matches(pattern: str, candidate: str) -> bool:
    """Whether a `.gitignore`-style `include` pattern selects `candidate` or an ancestor of it.

    `*`, `?`, `**` (also matching zero directories), a leading `/` and a trailing
    `/` are interpreted. A character class or escape selects every file; a
    negation only narrows the list and is skipped.
    """
    if pattern.startswith("!"):
        return False
    if _UNSUPPORTED_GLOB.search(pattern):
        return True
    body = pattern.removeprefix("./").rstrip("/")
    segments = body.lstrip("/").split("/")
    expression = "" if "/" in body else "(?:.*/)?"
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        if segment == "**":
            expression += ".*" if last else "(?:[^/]+/)*"
        else:
            translated = "".join(
                {"*": "[^/]*", "?": "[^/]"}.get(char) or re.escape(char) for char in segment
            )
            expression += translated if last else translated + "/"
    parts = candidate.split("/")
    return any(
        re.fullmatch(expression, "/".join(parts[: count + 1]), re.IGNORECASE)
        for count in range(len(parts))
    )


def _names(value: object, claimed: str) -> bool:
    """Whether a manifest path value is the claimed file, or is not a string at all."""
    if not isinstance(value, str):
        return True
    return PurePosixPath(value.replace("\\", "/")).as_posix().lower() == claimed


def _manifest_claims(manifest: Path, package_relative: str) -> bool:
    """Whether the package manifest can make Cargo read or package the file.

    A malformed manifest, or a `readme`, `license-file`, `include`, `exclude`
    or `build` value not interpreted here (`readme.workspace = true`, a
    non-string), claims every file.
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
    if any(key in package and _text_list(package[key]) is None for key in ("include", "exclude")):
        return True
    if not isinstance(package.get("build", False), (str, bool)):
        return True
    return any(_include_matches(glob, claimed) for glob in package.get("include", []))


def _is_prose_only(
    root: Path, package_directory: PurePosixPath, changed_path: str, sources: list[_RustSources]
) -> bool:
    """A Markdown file that no Cargo step can read, proved from the repository text.

    False keeps origin/main's package owner. True needs all of:
    1. the package manifest does not claim the file (`_manifest_claims`);
    2. no tracked file runs code outside the scanned Rust text (`_scan`): no
       symlink, Cargo or nextest config, dependency in any manifest, or
       target path not ending `.rs`;
    3. the Rust text, doc comments included, names no `fs`, `process`, `env`,
       `read_dir`, `extern`, `asm` or `include!`, has no `path` but a plain
       `.rs` literal, and passes every `include_str!` and `include_bytes!` one
       plain literal whose last component is not the file's name (`_RustSources`).

    Premise: without a dependency or foreign code, std opens a path only
    through those names, so the file is read only by a literal inclusion.
    Cost: a crate with a dependency, or a source that touches the file system
    or environment, gates every Markdown file under it.
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
