#!/usr/bin/env python3
"""Run the release API gate against locks shipped in published crate archives."""

import argparse
import json
import os
from pathlib import Path
import tempfile

from atlas_git_process import extract_archive
from atlas_semver_locked import digest_bytes, permission
from atlas_semver_pr import library_name, locked_rustdoc, run, tail, workspace_packages
from atlas_stack import load_sibling


drift = load_sibling("atlas_published_drift", Path(__file__).with_name("atlas-published-drift.py"))


def select_baseline(rows, current):
    """Select the latest stable, unyanked release below the candidate."""
    older = [entry for entry in rows if not entry["yanked"] and "-" not in entry["vers"]
             and drift.version_key(entry["vers"]) < drift.version_key(current)]
    if not older:
        raise ValueError(f"no usable earlier stable release before {current}")
    return max(older, key=lambda entry: drift.version_key(entry["vers"]))


def published_baseline(name, current, destination):
    index = f"https://index.crates.io/{drift.crates_pending.index_path(name)}"
    status, data = drift.http_get(index)
    if status == 404:
        return None
    if status != 200:
        raise RuntimeError(f"{name}: crates.io index returned HTTP {status}")
    record = select_baseline([json.loads(line) for line in data.splitlines()], current)
    version = record["vers"]
    status, data = drift.http_get(drift.CRATE_URL.format(name=name, version=version))
    if status != 200 or digest_bytes(data) != record["cksum"]:
        raise RuntimeError(f"{name} {version}: could not verify the published archive checksum")
    extract_archive(data, destination)
    source = destination / f"{name}-{version}"
    if not (source / "Cargo.lock").is_file():
        raise RuntimeError(f"{name} {version}: the published archive lacks Cargo.lock")
    print(f"{name} {version}: verified crate archive {record['cksum']}", flush=True)
    return source / "Cargo.toml", version


def compare_api(manifest, name, previous, current, boundary, env):
    command = ["cargo", "semver-checks", "check-release", "--baseline-rustdoc", str(previous),
               "--current-rustdoc", str(current)]
    audit = run([*command, "--release-type", "patch"], manifest.parent, env)
    print(tail(audit, 60), flush=True)
    if audit.returncode == 0:
        return
    if audit.returncode != 100 or boundary == "patch":
        raise RuntimeError(f"{name}: patch-compatibility audit exited {audit.returncode}")
    verdict = run([*command, "--release-type", boundary], manifest.parent, env)
    print(tail(verdict, 60), flush=True)
    if verdict.returncode != 0:
        raise RuntimeError(f"{name}: the {boundary} version boundary did not pass the API check")


def verify_package(manifest, package, scratch, toolchain, env):
    name, version = package["name"], package["version"]
    if not (Path(package["workspace_root"]) / "Cargo.lock").is_file():
        raise RuntimeError(f"{name}: the candidate workspace lacks Cargo.lock")
    baseline = published_baseline(name, version, scratch)
    if baseline is None:
        print(f"{name}: first publication has no registry baseline", flush=True)
        return
    previous_manifest, old_version = baseline
    previous = workspace_packages(previous_manifest, env)[name]
    if previous["version"] != old_version or not library_name(previous):
        raise RuntimeError(f"{name} {old_version}: the archive has no matching library")
    previous_doc = locked_rustdoc(previous_manifest, previous, library_name(previous),
                                  scratch / "baseline-target", env, toolchain)
    current_doc = locked_rustdoc(manifest, package, library_name(package),
                                 scratch / "current-target", env, toolchain)
    boundary = permission(old_version, version)
    print(f"{name} {old_version} -> {version} ({boundary})", flush=True)
    compare_api(manifest, name, previous_doc, current_doc, boundary, env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--packages", required=True)
    parser.add_argument("--rustdoc-toolchain", required=True)
    args = parser.parse_args()
    manifest = args.manifest_path.resolve()
    env = dict(os.environ, CARGO_INCREMENTAL="0", CARGO_PROFILE_DEV_DEBUG="0")
    packages = workspace_packages(manifest, env)
    with tempfile.TemporaryDirectory(prefix="atlas-registry-semver-") as path:
        for name in args.packages.split(","):
            verify_package(manifest, packages[name], Path(path), args.rustdoc_toolchain, env)


if __name__ == "__main__":
    main()
