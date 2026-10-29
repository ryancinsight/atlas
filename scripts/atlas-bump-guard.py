#!/usr/bin/env python3
"""Compare selected crate source with the artifact at its manifest version.

A crate whose manifest version crates.io already carries reads as released, so a
change to its source under that version never reaches consumers: the push-mode
planner (ADR 0068) sees nothing pending, and dependents later fail `cargo publish`
verification against the stale registry copy (ATLAS-PUB-011). Pull requests report
that state without requiring release authority. An explicit release checks every
named package and blocks before SemVer comparison or publication.

    python scripts/atlas-bump-guard.py --repo <member checkout> --base <rev> --head <rev>
        [--package <name>[,<name>...]]
    python scripts/atlas-bump-guard.py --release --repo <member checkout> --head <rev>
        [--package <name>[,<name>...]]

Pull-request selection contains only crates the pull request touches. The diff is
read from the merge base of `--base` and `--head`, so a branch behind its base does
not select crates the base moved. A publishable crate (`cargo metadata --no-deps` at
the head, `publish` not `[]`) is touched when its `src/**` or its `Cargo.toml` differs
from the merge base, or when its resolved normal or build dependency requirements
differ. A `workspace = true` dependency therefore moves with the workspace root
without its own manifest changing. A crate absent from the merge-base publishable
set is touched. `--package` narrows this selection.

Release selection contains every named publishable package at `--head`, even when
the release commit changes none of its files. An unknown, duplicate, or
nonpublishable name is malformed input and fails the measurement. With no
`--package`, either mode considers every publishable package allowed by that mode.

Decision, per selected crate, by `atlas-published-drift.py`'s `measure_crate` (one
definition of the comparison): the head's `src/**`, `Cargo.toml`, and dependency
requirements against the `.crate` crates.io holds at the head's manifest version.
`published-drifted` returns the distinct artifact-drift status. The pull-request
workflow renders it as an informational finding; the release workflow blocks it and
requires an explicitly authorized version change. Every other status passes:
`never-published` and `unpublished-version` have nothing to compare with,
`published-current` matches, and `foreign-name` is another account's crate, which no
bump of ours reconciles (ATLAS-PUB-003). Pull-request mode never charges pre-existing
drift in an untouched crate to the current change.

Every selected revision is read from `git archive`, never the working tree.

Exit status: 0 no selected crate drifted; 1 a selected crate differs from the artifact
at its indexed manifest version, and nothing else; 2 the measurement failed
(registry, git, cargo, malformed selection, or any unexpected error). A registry
outage is never read as current or unpublished, and a crash is never read as drift.
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


def guard(repo: Path, base: str | None, head: str, fetch: drift.Fetch,
          owner: str = drift.DEFAULT_OWNER,
          only: Sequence[str] = ()) -> tuple[list, list]:
    """The selected crates' readings, and those whose published artifact drifted."""
    with tempfile.TemporaryDirectory(prefix="atlas-bump-guard-") as scratch:
        head_root = (Path(scratch) / "head").resolve()
        packages = drift.publishable_packages(
            drift.export_revision("head", repo, head, head_root), head_root)
        if only:
            if len(only) != len(set(only)):
                raise drift.MeasurementError("--package contains a duplicate name")
            by_name = {package.name: package for package in packages}
            missing = [name for name in only if name not in by_name]
            if missing:
                raise drift.MeasurementError(
                    "--package does not name a publishable package at head: "
                    + ", ".join(missing))
            packages = [by_name[name] for name in only]
        before = None
        fork = None
        if base is not None:
            fork = git_output(repo, "merge-base", base, head)
            fork_root = (Path(scratch) / "fork").resolve()
            before = {p.name: p for p in drift.publishable_packages(
                drift.export_revision("merge base", repo, fork, fork_root), fork_root)}
        readings = []
        for package in packages:
            if (before is not None
                    and not touched(repo, fork, head, package, before.get(package.name))):
                continue
            readings.append(drift.measure_crate(
                package.name, package.version, package.manifest,
                head_root / package.directory, package.dependencies, fetch, owner))
    return readings, [r for r in readings if r.status == drift.PUBLISHED_DRIFTED]


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path, default=Path.cwd(),
                        help="the member repository holding both revisions (default: cwd)")
    parser.add_argument("--base", help="the pull request's base revision")
    parser.add_argument("--head", required=True, help="the pull request's head revision")
    parser.add_argument("--release", action="store_true",
                        help="check every named package at head and block artifact drift")
    parser.add_argument("--package", default="",
                        help="comma-separated crate names to check (default: every "
                             "publishable crate)")
    parser.add_argument("--owner", default=drift.DEFAULT_OWNER,
                        help="crates.io login that must own every indexed name "
                             "(default: %(default)s)")
    options = parser.parse_args(argv)
    if options.release and options.base is not None:
        parser.error("--release and --base are mutually exclusive")
    if not options.release and options.base is None:
        parser.error("--base is required unless --release is set")
    return options


def main(argv: Sequence[str] | None = None, fetch: drift.Fetch = drift.http_get) -> int:
    options = parse_arguments(argv)
    only = tuple(name.strip() for name in options.package.split(",") if name.strip())
    try:
        readings, bumps = guard(options.repo, None if options.release else options.base,
                                options.head, fetch,
                                options.owner, only)
    except (drift.RegistryError, drift.MeasurementError) as error:
        print(f"atlas-bump-guard: {error}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - exit 1 means "bump required" and nothing else
        print("atlas-bump-guard: measurement failed unexpectedly", file=sys.stderr)
        traceback.print_exc()
        return 2
    if not readings and options.release:
        print("No selected publishable package has a published artifact to update.")
    elif not readings:
        print("No publishable crate's source, manifest, or dependency requirements changed.")
    for reading in readings:
        print(f"- `{reading.name}` {reading.version}: {reading.status}")
    for reading in bumps:
        boundary = "release blocked" if options.release else "release artifact drift"
        print(f"{reading.name} {reading.version}: {boundary}; crates.io already carries "
              f"{reading.version} and the source differs from it ({describe(reading)}); "
              "an explicitly authorized release requires a version change",
              file=sys.stderr)
    return 1 if bumps else 0


if __name__ == "__main__":
    sys.exit(main())
