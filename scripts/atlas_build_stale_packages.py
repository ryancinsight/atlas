"""The packages a mismatched identity record must clean before its command runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from atlas_build_artifacts import changed_packages
from atlas_build_records import BuildSpec, _content, _identified_by_files
from atlas_build_stamps import BuildDirectory, _stale_git


@dataclass
class PackageState:
    """One package's record as read under a run's leases, the clean rule's input.

    `current` is the record's artifact files and `inputs` its
    out-of-directory inputs, each hashed again under the leases.
    """

    existing: dict[str, object] | None
    matched: bool
    current: dict[str, object] | None
    stale_git: set[str]
    inputs: dict[str, object]


def _dimensions(build: object) -> object:
    """A build record's dimensions, without the fields compared on their own.

    `source` is compared against `spec.source` directly, and
    `dependency_digest` restates the dependency snapshot, which
    `_stale_packages` compares record by record.
    """
    content = _content(build)
    if not isinstance(content, dict):
        return content
    return {key: value for key, value in content.items() if key not in ("source", "dependency_digest")}


def _path_packages(dependencies: dict[str, object]) -> tuple[str, ...]:
    """The closure's path packages, the only ones whose files a record names.

    Cargo trusts a path package's artifact while its sources are older, so
    another tree's build of the same workspace-relative package can stand in
    for this one; the record's file digests detect that. A Git or registry
    package's artifact is named after its locked revision or version and
    built from that checkout, so recording it detects nothing, and hashing
    every variant of every one in the shared target cost each run minutes.
    """
    return tuple(
        sorted(
            {
                str(record.get("name"))
                for record in dependencies.get("packages", [])
                if isinstance(record, dict) and record.get("kind") == "path"
            }
        )
    )


def _stale_packages(
    existing: dict[str, object] | None,
    current: dict[str, object] | None,
    spec: BuildSpec,
    dependencies: dict[str, object],
    manifest: Path,
    execution_root: Path,
    inputs: dict[str, object],
) -> tuple[str, ...]:
    """The packages a mismatched record must clean before its command runs.

    Cargo rebuilds a unit whose features, profile, dependencies, edition or
    toolchain changed, under a new metadata hash or in place, so none of
    those leave a stale artifact; only source content can, and the record
    must still name the variant the build uses. A variant is renamed only
    by the build dimensions or by the snapshot's shape: its records without
    their content fields -- each path package's resolved manifest among
    them -- its edges, and the workspace manifest, whose `[profile]` tables
    enter every unit's hash. A source edit renames nothing. `cargo
    metadata` unifies features across `cfg` tables and dependency kinds, so
    which variants a shape change renamed cannot be read from it: a shape
    or dimension change cleans every path package. Otherwise only content
    moved, and the run cleans each path package whose identity -- its own
    directory's files -- moved, each one an input of which moved or is
    unverified (`inputs`, the record's out-of-directory inputs hashed again
    now), and the owners of changed recorded files, or every path package
    when a changed file cannot be attributed to exactly one. A commit to
    one member therefore moves no other member's record. The repository's
    identity cleans the run's own package only where the snapshot cannot
    identify it (`_identified_by_files`). A Git package is cleaned when
    its stamp is
    stale (`_stale_git`). Registry packages are never cleaned. Cleaning the
    whole non-registry closure on any snapshot difference held a
    two-dependency addition's 35 packages exclusive through its command; 34
    were unedited Git checkouts. Cleaning every path package on any source
    move cleaned each separate-repository path dependency, every stack
    member under the development overlay, on every push of its consumer.
    """
    scope = {*_path_packages(dependencies), spec.package}
    stale = _stale_git(dependencies, BuildDirectory(Path(spec.target_dir), spec.profile, spec.target))
    if (
        existing is None
        or current is None
        or _dimensions(existing.get("build")) != _dimensions(spec.as_dict())
        or _shape(existing["dependencies"]) != _shape(dependencies)
    ):
        return tuple(sorted(scope | stale))
    recorded = {
        record.get("id"): record
        for record in existing["dependencies"].get("packages", [])
        if isinstance(record, dict)
    }
    for record in dependencies.get("packages", []):
        if (
            isinstance(record, dict)
            and record.get("kind") == "path"
            and recorded.get(record.get("id")) != record
        ):
            stale.add(str(record.get("name")))
    recorded_inputs = existing.get("inputs")
    for package, files in (recorded_inputs if isinstance(recorded_inputs, dict) else {}).items():
        if inputs.get(package) != files:
            stale.add(package)
    if not _identified_by_files(dependencies) and _content(existing.get("source")) != _content(
        spec.source.as_dict()
    ):
        stale.add(spec.package)
    changed = changed_packages(
        existing["artifact"]["files"],
        current["files"],
        manifest,
        execution_root,
        tuple(sorted(scope)),
    )
    stale |= scope if changed is None else changed
    return tuple(sorted(stale))


# The record fields that carry source content: a path package's own files
# (`package_identities`) and a Git or registry checkout's digest. Neither
# renames a variant.
_CONTENT_FIELDS = ("identity", "content_digest")


def _shape(snapshot: dict[str, object]) -> str:
    """The snapshot without its content fields: every input of a variant name it holds."""
    shape = {
        "workspace_manifest": snapshot.get("workspace_manifest"),
        "packages": sorted(
            (
                {key: value for key, value in record.items() if key not in _CONTENT_FIELDS}
                for record in snapshot.get("packages", [])
                if isinstance(record, dict)
            ),
            key=lambda record: json.dumps(record, sort_keys=True),
        ),
        "edges": snapshot.get("edges"),
    }
    return json.dumps(shape, sort_keys=True)
