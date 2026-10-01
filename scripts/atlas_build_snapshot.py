"""Resolve a package's dependency closure from `cargo metadata` into a digested snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Callable

from atlas_build_lease import BuildIdentityError
from atlas_build_source import _canonical, _is_within


def _cargo_metadata(
    manifest: Path,
    metadata_cwd: Path | None = None,
    *,
    no_deps: bool = True,
) -> dict[str, object]:
    cargo = (os.environ["CARGO"],) if os.environ.get("CARGO") else ("cargo",)
    arguments = [
        *cargo,
        "metadata",
        "--format-version",
        "1",
        "--locked",
        "--manifest-path",
        str(manifest),
    ]
    if no_deps:
        arguments.append("--no-deps")
    try:
        result = subprocess.run(
            arguments,
            cwd=metadata_cwd or manifest.parent,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BuildIdentityError(f"cannot read package metadata from {manifest}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise BuildIdentityError(f"cargo metadata failed for {manifest}: {detail}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise BuildIdentityError(f"malformed cargo metadata for {manifest}") from error
    if not isinstance(value, dict):
        raise BuildIdentityError(f"malformed cargo metadata for {manifest}")
    return value


def _stable_package_ids(
    packages: dict[str, dict], workspace_root: object
) -> dict[str, str]:
    """Path-package IDs relative to the workspace root.

    Cargo names a path package by its absolute manifest directory
    (`path+file:///<dir>#<version>`), so the same workspace exported to two
    directories yields two snapshots of one dependency graph. Packages
    inside the workspace are renamed to their workspace-relative directory;
    anything else keeps cargo's ID.
    """
    if not isinstance(workspace_root, str) or not workspace_root:
        return {}
    base = _canonical(Path(workspace_root))
    stable: dict[str, str] = {}
    for package_id, value in packages.items():
        if value.get("source") is not None:
            continue
        directory = _canonical(Path(str(value["manifest_path"]))).parent
        if not _is_within(directory, base):
            continue
        relative = directory.relative_to(base).as_posix()
        stable[package_id] = f"workspace:{relative}#{value['name']}@{value['version']}"
    return stable


def _manifest_digest(value: dict, package_id: str) -> str:
    """Digest of a package's resolved `cargo metadata` entry, without its paths.

    The entry is the manifest after workspace inheritance: dependency
    tables with their features, `cfg` targets and kinds, the feature table,
    the edition and the targets. Cargo's variant names follow these, so
    they change whenever a manifest edit can rename a unit, even where the
    resolved graph's unified feature lists do not. Absolute paths (the
    manifest, each target's source, each path dependency) vary with the
    checkout directory and are dropped; `id` is the stable one.
    """
    entry = {
        key: item
        for key, item in value.items()
        if key not in ("id", "manifest_path", "targets", "dependencies")
    }
    entry["id"] = package_id
    entry["targets"] = [
        {key: item for key, item in target.items() if key != "src_path"}
        for target in value.get("targets", [])
        if isinstance(target, dict)
    ]
    entry["dependencies"] = [
        {key: item for key, item in dependency.items() if key != "path"}
        for dependency in value.get("dependencies", [])
        if isinstance(dependency, dict)
    ]
    return hashlib.sha256(
        json.dumps(entry, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _workspace_manifest_digest(workspace_root: object) -> str | None:
    """Digest of the build's workspace manifest bytes.

    Its `[profile]` tables enter every unit's metadata hash and appear in no
    package entry; Cargo ignores those tables in any other workspace.
    """
    if not isinstance(workspace_root, str) or not workspace_root:
        return None
    try:
        return hashlib.sha256((Path(workspace_root) / "Cargo.toml").read_bytes()).hexdigest()
    except OSError as error:
        raise BuildIdentityError(f"cannot read the workspace manifest under {workspace_root}: {error}") from error


def dependency_snapshot(
    manifest: Path,
    package: str,
    metadata_cwd: Path | None,
    source_identity: Callable[[Path], object],
    content_digest: Callable[[Path], str],
) -> dict[str, object]:
    metadata = _cargo_metadata(manifest, metadata_cwd, no_deps=False)
    try:
        packages = {
            str(value["id"]): value
            for value in metadata["packages"]
            if isinstance(value, dict) and "id" in value
        }
        nodes = {
            str(value["id"]): value
            for value in metadata["resolve"]["nodes"]
            if isinstance(value, dict)
            and "id" in value
            and isinstance(value.get("deps"), list)
        }
    except (KeyError, TypeError) as error:
        raise BuildIdentityError(f"Cargo metadata has no resolved dependency graph for {manifest}") from error
    roots = [
        package_id
        for package_id, value in packages.items()
        if value.get("name") == package
        and (
            not metadata.get("workspace_members")
            or package_id in metadata["workspace_members"]
        )
    ]
    if len(roots) != 1 or roots[0] not in nodes:
        raise BuildIdentityError(f"Cargo metadata has no unique root package {package}")
    stable = _stable_package_ids(packages, metadata.get("workspace_root"))
    reachable: set[str] = set()
    edges: list[dict[str, object]] = []
    pending = [roots[0]]
    while pending:
        package_id = pending.pop()
        if package_id in reachable:
            continue
        reachable.add(package_id)
        node = nodes[package_id]
        for dependency in node["deps"]:
            dependency_id = str(dependency["pkg"])
            edges.append(
                {
                    "from": stable.get(package_id, package_id),
                    "to": stable.get(dependency_id, dependency_id),
                    "dep_kinds": sorted(
                        dependency.get("dep_kinds", []),
                        key=lambda value: json.dumps(value, sort_keys=True),
                    ),
                }
            )
            pending.append(dependency_id)
    records: list[dict[str, object]] = []
    clean_packages: set[str] = set()
    clean_sources: dict[str, str] = {}
    for package_id in sorted(reachable):
        value = packages.get(package_id)
        if value is None:
            raise BuildIdentityError(f"Cargo metadata is missing package {package_id}")
        source = value.get("source")
        manifest_path = Path(str(value["manifest_path"]))
        if source is None:
            identity_value = source_identity(manifest_path.parent)
            record = {
                "id": stable.get(package_id, package_id),
                "name": str(value["name"]),
                "version": str(value["version"]),
                "features": sorted(
                    str(feature) for feature in nodes[package_id].get("features", [])
                ),
                "kind": "path",
                "manifest": _manifest_digest(value, stable.get(package_id, package_id)),
                "identity": identity_value,
            }
        else:
            source_text = str(source)
            kind = "git" if source_text.startswith("git+") else "registry"
            record = {
                "id": package_id,
                "name": str(value["name"]),
                "version": str(value["version"]),
                "features": sorted(
                    str(feature) for feature in nodes[package_id].get("features", [])
                ),
                "kind": kind,
                "source": source_text,
                "manifest": _manifest_digest(value, package_id),
                "content_digest": content_digest(manifest_path.parent),
            }
        if record["kind"] != "registry":
            name = str(record["name"])
            previous = clean_sources.get(name)
            if previous is not None and previous != stable.get(package_id, package_id):
                raise BuildIdentityError(
                    f"dependency package name {name} has multiple non-registry sources"
                )
            clean_sources[name] = stable.get(package_id, package_id)
            clean_packages.add(name)
        records.append(record)
    snapshot = {
        "root": stable.get(roots[0], roots[0]),
        "workspace_manifest": _workspace_manifest_digest(metadata.get("workspace_root")),
        "packages": records,
        "edges": sorted(edges, key=lambda value: json.dumps(value, sort_keys=True)),
        "clean_packages": sorted(clean_packages),
    }
    snapshot["digest"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return snapshot
