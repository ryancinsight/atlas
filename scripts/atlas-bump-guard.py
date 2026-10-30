#!/usr/bin/env python3
"""Compare selected source with the crate at its manifest version.

Pull-request mode selects changed packages since the merge base; ``--release``
selects all named packages at HEAD, including unchanged packages. ``--manifest-path``
selects the same repository-relative workspace as the release caller. Package
selection and measurement failures block both modes. ADR 0068 owns release policy.

Exit codes: 0 current/unpublished; 3 published artifact drift; 2 measurement or CLI
failure. The PR workflow treats only 3 as information; release blocks every error.
Python startup failures retain their ordinary nonzero code and cannot imply drift.
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
          only: Sequence[str] = (), manifest_path: str = "Cargo.toml") -> tuple[list, list]:
    """The selected crates' readings, and those whose published artifact drifted."""
    with tempfile.TemporaryDirectory(prefix="atlas-bump-guard-") as scratch:
        head_root = (Path(scratch) / "head").resolve()
        head_metadata = drift.export_revision(
            "head", repo, head, head_root, manifest_path)
        all_packages = drift.workspace_packages(head_metadata, head_root)
        packages = drift.publishable_packages(head_metadata, head_root)
        if only:
            if len(only) != len(set(only)):
                raise drift.MeasurementError("--package contains a duplicate name")
            all_names = {package.name for package in all_packages}
            missing = [name for name in only if name not in all_names]
            if missing:
                raise drift.MeasurementError(
                    "--package does not name a package at head: "
                    + ", ".join(missing))
            publishable_by_name = {package.name: package for package in packages}
            packages = [publishable_by_name[name] for name in only
                        if name in publishable_by_name]
        before = None
        fork = None
        if base is not None:
            fork = git_output(repo, "merge-base", base, head)
            fork_root = (Path(scratch) / "fork").resolve()
            fork_metadata = drift.export_revision(
                "merge base", repo, fork, fork_root, manifest_path,
                missing_manifest_is_empty=True)
            before = ({} if fork_metadata is None else {
                package.name: package
                for package in drift.publishable_packages(fork_metadata, fork_root)
            })
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
    parser.add_argument("--manifest-path", default="Cargo.toml",
                        help="repository-relative manifest selected by the release caller")
    parser.add_argument("--release", action="store_true",
                        help="check every named package at head and block artifact drift")
    parser.add_argument("--package", default=None,
                        help="comma-separated crate names to check (default: every "
                             "publishable crate)")
    parser.add_argument("--owner", default=drift.DEFAULT_OWNER,
                        help="crates.io login that must own every indexed name "
                             "(default: %(default)s)")
    options = parser.parse_args(argv)
    if options.package is not None and any(
            not name.strip() for name in options.package.split(",")):
        parser.error("--package contains an empty name")
    if options.release and options.base is not None:
        parser.error("--release and --base are mutually exclusive")
    if not options.release and options.base is None:
        parser.error("--base is required unless --release is set")
    return options


def main(argv: Sequence[str] | None = None, fetch: drift.Fetch = drift.http_get) -> int:
    options = parse_arguments(argv)
    only = (() if options.package is None
            else tuple(name.strip() for name in options.package.split(",")))
    try:
        readings, bumps = guard(options.repo, None if options.release else options.base,
                                options.head, fetch,
                                options.owner, only, options.manifest_path)
    except (drift.RegistryError, drift.MeasurementError) as error:
        print(f"atlas-bump-guard: {error}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - unexpected measurement failures remain blocking
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
    return 3 if bumps else 0


if __name__ == "__main__":
    sys.exit(main())
