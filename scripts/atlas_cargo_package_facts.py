"""Cargo-owned package and dependency facts from immutable stack snapshots."""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from atlas_git_process import archive, execute_process, extract_archive

PROCESS_TIMEOUT_SECONDS = 60
IGNORED_DIRECTORIES = frozenset({".git", "node_modules", "target", "worktrees"})


class PackageFactError(RuntimeError):
    """The selected source cohort cannot produce complete Cargo facts."""


@dataclass(frozen=True)
class SelectedRepository:
    """One immutable repository tree selected for the source cohort."""
    repository: Path
    revision: str


@dataclass(frozen=True)
class DependencyFact:
    """One dependency after Cargo resolves workspace inheritance."""
    package: str
    rename: str | None
    source: str | None
    requirement: str
    kind: str | None
    target: str | None


@dataclass(frozen=True)
class PackageFact:
    """One package and its Cargo-resolved dependencies."""
    name: str
    version: str
    manifest: PurePosixPath
    dependencies: tuple[DependencyFact, ...]


@dataclass(frozen=True)
class PackageCatalog:
    """Selected packages and unique providers for consumed stack packages."""
    packages: tuple[PackageFact, ...]
    providers: Mapping[str, PackageFact]


def _member_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or path.parts != (name,) or name in {".", ".."}:
        raise PackageFactError(f"unsafe selected repository name: {name!r}")
    return name


def export_selected(selections: Mapping[str, SelectedRepository], destination: Path) -> Path:
    """Export selected Git trees under one ``repos/<member>`` topology."""
    if destination.exists():
        raise PackageFactError(f"snapshot destination already exists: {destination}")
    repos = destination / "repos"
    repos.mkdir(parents=True)
    for name, selected in sorted(selections.items()):
        member = repos / _member_name(name)
        member.mkdir()
        try:
            payload = archive(selected.repository, selected.revision,
                              timeout=PROCESS_TIMEOUT_SECONDS)
            extract_archive(payload, member)
        except (OSError, RuntimeError) as error:
            raise PackageFactError(f"cannot export selected member {name!r}: {error}") from error
    return destination


def _lock_roots(topology: Path) -> tuple[Path, ...]:
    for member in topology.joinpath("repos").iterdir():
        if not member.joinpath("Cargo.toml").is_file():
            raise PackageFactError(f"selected member has no root manifest: repos/{member.name}")
        if not member.joinpath("Cargo.lock").is_file():
            raise PackageFactError(f"selected member has no root lock: repos/{member.name}")
    locks = tuple(sorted(path for path in topology.joinpath("repos").rglob("Cargo.lock")
                         if not ({part.lower() for part in path.parts} & IGNORED_DIRECTORIES)))
    if not locks:
        raise PackageFactError("selected cohort contains no committed Cargo.lock")
    for lock in locks:
        if not lock.with_name("Cargo.toml").is_file():
            raise PackageFactError(f"lock has no root manifest: {lock.relative_to(topology)}")
    return locks


def _string(record: dict, field: str, *, optional: bool = False) -> str | None:
    value = record.get(field)
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value:
        raise PackageFactError(f"cargo metadata returned invalid {field!r} field")
    return value


def _dependency(record: object) -> DependencyFact:
    if not isinstance(record, dict):
        raise PackageFactError("cargo metadata returned a non-table dependency")
    return DependencyFact(
        _string(record, "name"), _string(record, "rename", optional=True),
        _string(record, "source", optional=True), _string(record, "req"),
        _string(record, "kind", optional=True), _string(record, "target", optional=True),
    )


def _metadata(topology: Path, lock: Path) -> tuple[PackageFact, ...]:
    command = ("cargo", "metadata", "--locked", "--offline", "--no-deps",
               "--format-version", "1", "--manifest-path", str(lock.with_name("Cargo.toml")))
    with tempfile.TemporaryDirectory(prefix="atlas-cargo-facts-") as neutral:
        result = execute_process(command, cwd=Path(neutral), env=dict(os.environ),
                                 timeout=PROCESS_TIMEOUT_SECONDS)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise PackageFactError(f"cargo metadata failed for {lock.relative_to(topology)}: {detail}")
    try:
        document = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PackageFactError("cargo metadata returned unreadable JSON") from error
    packages = document.get("packages") if isinstance(document, dict) else None
    if not isinstance(packages, list):
        raise PackageFactError("cargo metadata returned no package list")
    facts = []
    for package in packages:
        if not isinstance(package, dict) or not isinstance(package.get("dependencies"), list):
            raise PackageFactError("cargo metadata returned an invalid package")
        try:
            manifest = Path(_string(package, "manifest_path")).resolve().relative_to(topology.resolve())
        except ValueError as error:
            raise PackageFactError("cargo metadata returned a manifest outside the cohort") from error
        facts.append(PackageFact(
            _string(package, "name"), _string(package, "version"),
            PurePosixPath(manifest.as_posix()),
            tuple(_dependency(item) for item in package["dependencies"]),
        ))
    return tuple(facts)


def _first_party_repository(source: str | None) -> str | None:
    if source is None or not source.startswith("git+"):
        return None
    parsed = urlsplit(source.removeprefix("git+").split("#", 1)[0])
    parts = parsed.path.strip("/").split("/")
    if (parsed.hostname or "").lower() != "github.com" or parts[0].lower() != "ryancinsight":
        return None
    if parsed.scheme != "https" or parsed.port not in (None, 443) or len(parts) != 2:
        raise PackageFactError("unsupported first-party Git source identity")
    return parts[1].removesuffix(".git").lower()


def load_selected(selections: Mapping[str, SelectedRepository],
                  destination: Path) -> PackageCatalog:
    """Export and ask Cargo for complete facts at every committed lock root."""
    topology = export_selected(selections, destination)
    locks = _lock_roots(topology)
    lock_bytes = {lock: lock.read_bytes() for lock in locks}
    by_manifest: dict[PurePosixPath, PackageFact] = {}
    for lock in locks:
        for fact in _metadata(topology, lock):
            previous = by_manifest.setdefault(fact.manifest, fact)
            if previous != fact:
                raise PackageFactError(f"conflicting Cargo facts for {fact.manifest}")
    changed = [lock.relative_to(topology) for lock, before in lock_bytes.items()
               if lock.read_bytes() != before]
    if changed:
        raise PackageFactError(f"cargo metadata changed committed locks: {changed!r}")
    packages = tuple(sorted(by_manifest.values(), key=lambda fact: fact.manifest.as_posix()))
    consumed = {dependency.package for package in packages for dependency in package.dependencies
                if _first_party_repository(dependency.source) is not None}
    providers = {}
    for name in sorted(consumed):
        candidates = [package for package in packages if package.name == name]
        if len(candidates) != 1:
            raise PackageFactError(
                f"consumed first-party package {name!r} has {len(candidates)} selected providers"
            )
        providers[name] = candidates[0]
    return PackageCatalog(packages, providers)
