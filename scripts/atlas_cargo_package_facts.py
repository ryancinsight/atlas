"""Cargo-owned package and dependency facts from immutable stack snapshots."""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from atlas_cargo_snapshot import SelectedRepository, create_snapshot
from atlas_git_process import execute_process

PROCESS_TIMEOUT_SECONDS = 60


class PackageFactError(RuntimeError):
    """The selected source cohort cannot produce complete Cargo facts."""


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


@dataclass(frozen=True, order=True)
class ProviderIdentity:
    """A consumed package bound to its declared first-party repository."""
    package: str
    repository: str


@dataclass(frozen=True)
class PackageCatalog:
    """Selected package declarations and source-bound providers."""
    basis: tuple[tuple[str, str], ...]
    packages: tuple[PackageFact, ...]
    providers: Mapping[ProviderIdentity, PackageFact]


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


def _metadata(topology: Path, lock: PurePosixPath) -> tuple[PackageFact, ...]:
    manifest = topology.joinpath(lock).with_name("Cargo.toml")
    command = ("cargo", "metadata", "--locked", "--offline", "--no-deps",
               "--format-version", "1", "--manifest-path", str(manifest))
    with tempfile.TemporaryDirectory(prefix="atlas-cargo-facts-") as neutral:
        result = execute_process(command, cwd=Path(neutral), env=dict(os.environ),
                                 timeout=PROCESS_TIMEOUT_SECONDS)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise PackageFactError(f"cargo metadata failed for {lock}: {detail}")
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
            path = Path(_string(package, "manifest_path")).resolve().relative_to(topology.resolve())
        except ValueError as error:
            raise PackageFactError("cargo metadata returned a manifest outside the cohort") from error
        facts.append(PackageFact(
            _string(package, "name"), _string(package, "version"),
            PurePosixPath(path.as_posix()),
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
    """Extract Cargo declarations from every confined committed lock root."""
    snapshot = create_snapshot(selections, destination)
    by_manifest: dict[PurePosixPath, PackageFact] = {}
    for lock in snapshot.locks:
        for fact in _metadata(snapshot.root, lock):
            previous = by_manifest.setdefault(fact.manifest, fact)
            if previous != fact:
                raise PackageFactError(f"conflicting Cargo facts for {fact.manifest}")
    before = dict(snapshot.lock_bytes)
    changed = [lock for lock in snapshot.locks
               if snapshot.root.joinpath(lock).read_bytes() != before[lock]]
    if changed:
        raise PackageFactError(f"cargo metadata changed committed locks: {changed!r}")
    packages = tuple(sorted(by_manifest.values(), key=lambda fact: fact.manifest.as_posix()))
    consumed = {
        ProviderIdentity(dependency.package, repository)
        for package in packages for dependency in package.dependencies
        if (repository := _first_party_repository(dependency.source)) is not None
    }
    providers = {}
    for identity in sorted(consumed):
        candidates = [package for package in packages
                      if package.name == identity.package
                      and package.manifest.parts[1].lower() == identity.repository]
        if len(candidates) != 1:
            raise PackageFactError(
                f"consumed first-party {identity!r} has {len(candidates)} selected providers"
            )
        providers[identity] = candidates[0]
    return PackageCatalog(snapshot.basis, packages, providers)
