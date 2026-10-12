#!/usr/bin/env python3
"""Fail a pull request that changes a published crate's source without a version bump.

A crate whose manifest version crates.io already carries reads as released, so a
change to its source under that version never reaches consumers: the push-mode
planner (ADR 0068) sees nothing pending, and dependents later fail `cargo publish`
verification against the stale registry copy (ATLAS-PUB-011). This guard runs on a
member's pull request and stops that change while it is still in review.

    python scripts/atlas-bump-guard.py --repo <member checkout> --base <rev> --head <rev>

Selection: the crates the pull request touches, never the whole member. The diff is
read from the merge base of `--base` and `--head`, so a branch behind its base does
not select the crates the base moved. A publishable crate (`cargo metadata --no-deps`
at the head, `publish` not `[]`) is touched when its `src/**` or its `Cargo.toml`
differs from the merge base, or when its resolved normal or build dependency
requirements differ: a `workspace = true` dependency moves with the workspace root
without its own manifest changing. A crate absent at the merge base is touched.

Decision, per touched crate, by `atlas-published-drift.py`'s `measure_crate` (one
definition of the comparison): the head's `src/**`, `Cargo.toml`, and dependency
requirements against the `.crate` crates.io holds at the head's manifest version.
`published-drifted` fails, naming the crate with "bump required". Every other status
passes: `never-published` and `unpublished-version` (the version moved, or the crate
is new) have nothing to compare with, `published-current` matches, and
`foreign-name` is another account's crate, which no bump of ours reconciles
(ATLAS-PUB-003). Drift in a crate the pull request does not touch is not this pull
request's to fix and does not fail it.

Both revisions are read from `git archive`, never the working tree.

Exit status: 0 no touched crate needs a bump; 1 a touched crate changed at a version
the registry already carries; 2 the measurement failed (registry, git, or cargo). A
registry outage is never read as "no bump required".
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from atlas_crate_requirements import (  # noqa: E402
    RequirementError,
    compare_requirements,
    metadata_requirements,
)
from atlas_git_process import (  # noqa: E402
    GitProcessError,
    archive as git_archive,
    execute as execute_git,
    extract_archive,
)

# The registry fetch, the ownership and index lookups, the digest comparison, and the
# crate classification are the published-drift scan's; its file name is not a Python
# identifier, so it loads by path, once.
drift = sys.modules.get("atlas_published_drift")
if drift is None:
    _spec = importlib.util.spec_from_file_location(
        "atlas_published_drift", SCRIPTS / "atlas-published-drift.py")
    if _spec is None or _spec.loader is None:
        raise ImportError(f"cannot load {SCRIPTS / 'atlas-published-drift.py'}")
    drift = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = drift
    _spec.loader.exec_module(drift)

GIT_TIMEOUT_SECONDS = drift.GIT_TIMEOUT_SECONDS


@dataclass(frozen=True)
class Package:
    """One package of a revision's export: its directory and resolved dependencies."""

    name: str
    version: str
    directory: PurePosixPath
    dependencies: tuple[dict, ...]


def export_packages(repo: Path, revision: str, root: Path) -> dict[str, Package]:
    """Every package of `revision`, exported under `root`; empty with no root manifest."""
    try:
        extract_archive(git_archive(repo, revision, timeout=GIT_TIMEOUT_SECONDS), root)
    except GitProcessError as error:
        raise drift.MeasurementError(f"cannot archive {revision}: {error}") from error
    manifest = root / "Cargo.toml"
    if not manifest.is_file():
        return {}
    metadata = drift.run_cargo_metadata(manifest)
    packages = {}
    for package in metadata["packages"]:
        if not drift.crates_pending.publishable(package):
            continue
        directory = Path(package["manifest_path"]).resolve().parent.relative_to(root.resolve())
        packages[package["name"]] = Package(package["name"], package["version"],
                                            PurePosixPath(directory.as_posix()),
                                            tuple(package["dependencies"]))
    return packages


def merge_base(repo: Path, base: str, head: str) -> str:
    result = execute_git(repo, ("merge-base", base, head), timeout=GIT_TIMEOUT_SECONDS)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise drift.MeasurementError(f"no merge base of {base} and {head}: {detail}")
    return result.stdout.decode("utf-8").strip()


def source_changed(repo: Path, fork: str, head: str, directory: PurePosixPath) -> bool:
    """Whether `directory`'s `src/**` or `Cargo.toml` differs between two commits."""
    paths = [(directory / "src").as_posix(), (directory / "Cargo.toml").as_posix()]
    result = execute_git(repo, ("diff", "--name-only", fork, head, "--", *paths),
                         timeout=GIT_TIMEOUT_SECONDS)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise drift.MeasurementError(f"cannot diff {fork}..{head}: {detail}")
    return bool(result.stdout.strip())


def touched(repo: Path, fork: str, head: str, package: Package,
            before: Package | None) -> bool:
    if before is None or source_changed(repo, fork, head, package.directory):
        return True
    return bool(compare_requirements(metadata_requirements(before.dependencies),
                                     metadata_requirements(package.dependencies)))


def describe(reading) -> str:
    found = reading.drift
    parts = [f"{label} {', '.join(paths)}" for label, paths in
             (("changed", found.changed), ("added", found.added), ("removed", found.removed))
             if paths]
    if found.dependencies:
        parts.append("dependency requirements " + "; ".join(
            f"{item.name}: {item.reason}" for item in found.dependencies))
    return "; ".join(parts)


def guard(repo: Path, base: str, head: str, fetch: drift.Fetch,
          owner: str = drift.DEFAULT_OWNER) -> tuple[list, list]:
    """The touched crates' readings, and those among them that need a bump."""
    fork = merge_base(repo, base, head)
    with tempfile.TemporaryDirectory(prefix="atlas-bump-guard-") as scratch:
        before = export_packages(repo, fork, Path(scratch) / "base")
        head_root = Path(scratch) / "head"
        after = export_packages(repo, head, head_root)
        readings = []
        for name in sorted(after):
            package = after[name]
            if not touched(repo, fork, head, package, before.get(name)):
                continue
            readings.append(drift.measure_crate(
                name, package.version, (package.directory / "Cargo.toml").as_posix(),
                head_root / package.directory, package.dependencies, fetch, owner))
    return readings, [r for r in readings if r.status == drift.PUBLISHED_DRIFTED]


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=Path.cwd(),
                        help="the member repository holding both revisions (default: cwd)")
    parser.add_argument("--base", required=True, help="the pull request's base revision")
    parser.add_argument("--head", required=True, help="the pull request's head revision")
    parser.add_argument("--owner", default=drift.DEFAULT_OWNER,
                        help="crates.io login that must own every indexed name "
                             "(default: %(default)s)")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, fetch: drift.Fetch = drift.http_get) -> int:
    options = parse_arguments(argv)
    try:
        readings, bumps = guard(options.repo, options.base, options.head, fetch,
                                options.owner)
    except (drift.RegistryError, drift.MeasurementError, GitProcessError,
            RequirementError) as error:
        print(f"atlas-bump-guard: {error}", file=sys.stderr)
        return 2
    if not readings:
        print("No publishable crate's source, manifest, or dependency requirements changed.")
    for reading in readings:
        print(f"- `{reading.name}` {reading.version}: {reading.status}")
    for reading in bumps:
        print(f"{reading.name} {reading.version}: bump required; crates.io already carries "
              f"{reading.version} and the source differs from it ({describe(reading)})",
              file=sys.stderr)
    return 1 if bumps else 0


if __name__ == "__main__":
    sys.exit(main())
