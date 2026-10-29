#!/usr/bin/env python3
"""Fail a pull request that changes a published crate's source without a version bump.

A crate whose manifest version crates.io already carries reads as released, so a
change to its source under that version never reaches consumers: the push-mode
planner (ADR 0068) sees nothing pending, and dependents later fail `cargo publish`
verification against the stale registry copy (ATLAS-PUB-011). This guard runs on a
member's pull request and stops that change while it is still in review.

    python scripts/atlas-bump-guard.py --repo <member checkout> --base <rev> --head <rev>
        [--package <name>[,<name>...]]

Selection: the crates the pull request touches, never the whole member. The diff is
read from the merge base of `--base` and `--head`, so a branch behind its base does
not select the crates the base moved. A publishable crate (`cargo metadata --no-deps`
at the head, `publish` not `[]`) is touched when its `src/**` or its `Cargo.toml`
differs from the merge base, or when its resolved normal or build dependency
requirements differ: a `workspace = true` dependency moves with the workspace root
without its own manifest changing. A crate that is not a publishable package at the
merge base is touched. `--package` narrows the selection to the named crates, so a
member that calls the shared gate once per crate queries each crate once.

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
the registry already carries, and nothing else; 2 the measurement failed (registry,
git, cargo, or any unexpected error). A registry outage is never read as "no bump
required", and a crash is never read as "bump required".
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import traceback
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from atlas_crate_requirements import (  # noqa: E402
    compare_requirements,
    metadata_requirements,
)
from atlas_git_process import execute as execute_git  # noqa: E402
from atlas_stack import load_sibling  # noqa: E402

# The registry fetch, the ownership and index lookups, the export, the digest
# comparison, and the crate classification are the published-drift scan's.
drift = load_sibling("atlas_published_drift", SCRIPTS / "atlas-published-drift.py")

GIT_TIMEOUT_SECONDS = drift.GIT_TIMEOUT_SECONDS


def git_output(repo: Path, *args: str) -> str:
    result = execute_git(repo, args, timeout=GIT_TIMEOUT_SECONDS)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise drift.MeasurementError(f"git {' '.join(args)}: {detail}")
    return result.stdout.decode("utf-8").strip()


def source_changed(repo: Path, fork: str, head: str, directory: PurePosixPath) -> bool:
    """Whether `directory`'s `src/**` or `Cargo.toml` differs between two commits."""
    paths = ((directory / "src").as_posix(), (directory / "Cargo.toml").as_posix())
    return bool(git_output(repo, "diff", "--name-only", fork, head, "--", *paths))


def touched(repo: Path, fork: str, head: str, package, before) -> bool:
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
          owner: str = drift.DEFAULT_OWNER,
          only: Sequence[str] = ()) -> tuple[list, list]:
    """The touched crates' readings, and those among them that need a bump."""
    fork = git_output(repo, "merge-base", base, head)
    with tempfile.TemporaryDirectory(prefix="atlas-bump-guard-") as scratch:
        fork_root = (Path(scratch) / "fork").resolve()
        head_root = (Path(scratch) / "head").resolve()
        before = {p.name: p for p in drift.publishable_packages(
            drift.export_revision("merge base", repo, fork, fork_root), fork_root)}
        readings = []
        for package in drift.publishable_packages(
                drift.export_revision("head", repo, head, head_root), head_root):
            if only and package.name not in only:
                continue
            if not touched(repo, fork, head, package, before.get(package.name)):
                continue
            readings.append(drift.measure_crate(
                package.name, package.version, package.manifest,
                head_root / package.directory, package.dependencies, fetch, owner))
    return readings, [r for r in readings if r.status == drift.PUBLISHED_DRIFTED]


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=Path.cwd(),
                        help="the member repository holding both revisions (default: cwd)")
    parser.add_argument("--base", required=True, help="the pull request's base revision")
    parser.add_argument("--head", required=True, help="the pull request's head revision")
    parser.add_argument("--package", default="",
                        help="comma-separated crate names to check (default: every "
                             "publishable crate)")
    parser.add_argument("--owner", default=drift.DEFAULT_OWNER,
                        help="crates.io login that must own every indexed name "
                             "(default: %(default)s)")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None,
         fetch: drift.Fetch = drift.REGISTRY_POLICY) -> int:
    options = parse_arguments(argv)
    only = tuple(name.strip() for name in options.package.split(",") if name.strip())
    try:
        readings, bumps = guard(options.repo, options.base, options.head, fetch,
                                options.owner, only)
    except (drift.RegistryError, drift.MeasurementError) as error:
        print(f"atlas-bump-guard: {error}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - exit 1 means "bump required" and nothing else
        print("atlas-bump-guard: measurement failed unexpectedly", file=sys.stderr)
        traceback.print_exc()
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
