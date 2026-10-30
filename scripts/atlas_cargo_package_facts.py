"""Cargo-owned package and dependency facts from stack source cohorts."""
from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

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
    provider: ProviderIdentity | None
    repository_url: str | None


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
    basis: tuple[tuple[str, str | None], ...]
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
    package = _string(record, "name")
    source = _string(record, "source", optional=True)
    binding = _first_party_source(source)
    return DependencyFact(
        package, _string(record, "rename", optional=True), source, _string(record, "req"),
        _string(record, "kind", optional=True), _string(record, "target", optional=True),
        ProviderIdentity(package, binding[0]) if binding is not None else None,
        binding[1] if binding is not None else None,
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


def _first_party_source(source: str | None) -> tuple[str, str] | None:
    if source is None or not source.startswith("git+"):
        return None
    parsed = urlsplit(source.removeprefix("git+").split("#", 1)[0])
    parts = parsed.path.strip("/").split("/")
    if (parsed.hostname or "").lower() != "github.com" or parts[0].lower() != "ryancinsight":
        return None
    if parsed.scheme != "https" or parsed.port not in (None, 443) or len(parts) != 2:
        raise PackageFactError("unsupported first-party Git source identity")
    repository = parts[1].removesuffix(".git").lower()
    location = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return repository, location


def _declarations(topology: Path, locks: tuple[PurePosixPath, ...]) -> tuple[PackageFact, ...]:
    by_manifest: dict[PurePosixPath, PackageFact] = {}
    for lock in locks:
        for fact in _metadata(topology, lock):
            previous = by_manifest.setdefault(fact.manifest, fact)
            if previous != fact:
                raise PackageFactError(f"conflicting Cargo facts for {fact.manifest}")
    return tuple(sorted(by_manifest.values(), key=lambda fact: fact.manifest.as_posix()))


def _catalog(basis: tuple[tuple[str, str | None], ...],
             packages: tuple[PackageFact, ...]) -> PackageCatalog:
    consumed = {dependency.provider for package in packages for dependency in package.dependencies
                if dependency.provider is not None}
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
    return PackageCatalog(basis, packages, providers)


def load_selected(selections: Mapping[str, SelectedRepository],
                  destination: Path) -> PackageCatalog:
    """Extract Cargo declarations from every confined committed lock root."""
    snapshot = create_snapshot(selections, destination)
    packages = _declarations(snapshot.root, snapshot.locks)
    before = dict(snapshot.lock_bytes)
    changed = [lock for lock in snapshot.locks
               if snapshot.root.joinpath(lock).read_bytes() != before[lock]]
    if changed:
        raise PackageFactError(f"cargo metadata changed committed locks: {changed!r}")
    return _catalog(snapshot.basis, packages)


def load_working(repositories: Mapping[str, Path]) -> PackageCatalog:
    """Extract live declarations from canonical ``repos/<member>`` trees."""
    resolved = {name: repository.resolve() for name, repository in repositories.items()}
    roots = set()
    for name, repository in resolved.items():
        if repository.name != name or repository.parent.name != "repos":
            raise PackageFactError("working repository is not a canonical repos member")
        roots.add(repository.parent.parent)
    if not resolved or len(roots) != 1:
        raise PackageFactError("working repositories are not one canonical repos topology")
    topology = roots.pop()
    locks = tuple(sorted(
        PurePosixPath(lock.relative_to(topology).as_posix())
        for repository in resolved.values() for lock in repository.rglob("Cargo.lock")
    ))
    for name, repository in resolved.items():
        if not repository.joinpath("Cargo.toml").is_file() or not repository.joinpath("Cargo.lock").is_file():
            raise PackageFactError(f"working repository {name!r} lacks a root manifest or lock")
    before = {lock: topology.joinpath(lock).read_bytes() for lock in locks}
    packages = _declarations(topology, locks)
    if any(topology.joinpath(lock).read_bytes() != content for lock, content in before.items()):
        raise PackageFactError("cargo metadata changed a working lock")
    return _catalog(tuple((name, None) for name in sorted(resolved)), packages)
