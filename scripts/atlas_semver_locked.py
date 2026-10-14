#!/usr/bin/env python3
"""Compare committed APIs using each revision's compatible locked source graph.

cargo-semver-checks' local-project generator runs cargo update and discards its
temporary lock. First-party Git providers can advance past the source version
a consumer requires. Generate complete Rustdoc JSON with Cargo --locked instead,
then use the tool's supported prebuilt-JSON comparison. Build, schema, and
comparison failures remain failures; no failure is interpreted as a version bump.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile


def run(argv: list[str], cwd: Path, env: dict[str, str], *, capture: bool = False):
    """Run an actual tool with bounded execution and preserve its diagnostics."""
    return subprocess.run(
        argv, cwd=cwd, env=env, check=True, text=True, encoding="utf-8", errors="replace",
        stdout=subprocess.PIPE if capture else None,
        timeout=1800,
    )


def commit(repo: Path, ref: str, env: dict[str, str]) -> str:
    result = run(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"],
        repo, env, capture=True,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", result):
        raise ValueError(f"invalid resolved commit: {result!r}")
    return result


def export(repo: Path, revision: str, destination: Path, env: dict[str, str]) -> None:
    # Export both arms outside an Atlas ancestor's path overlay. Only committed
    # content enters the comparison; dirty files and a shared index cannot drift it.
    archive = subprocess.run(
        ["git", "archive", "--format=tar", revision], cwd=repo, env=env,
        stdout=subprocess.PIPE, check=True, timeout=120,
    ).stdout
    destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(destination, filter="data")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release_type(baseline: str, current: str) -> str:
    """Enforce the declared SemVer change, including pre-1.0 minor breaks."""
    def core(version: str) -> tuple[int, int, int]:
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", version)
        if match is None:
            raise ValueError(f"unsupported version {version!r}")
        return tuple(map(int, match.groups()))

    old, new = core(baseline), core(current)
    if new < old:
        raise ValueError(f"version decreases: {baseline} -> {current}")
    if new[0] > old[0] or (new[0] == 0 and new[1] > old[1]):
        return "major"
    if new[1] > old[1]:
        return "minor"
    return "patch"


def inventory(manifest: Path, env: dict[str, str]) -> tuple[dict, Path]:
    metadata = json.loads(run(
        ["cargo", "metadata", "--locked", "--no-deps", "--format-version", "1",
         "--manifest-path", str(manifest)], manifest.parent, env, capture=True,
    ).stdout)
    members = set(metadata["workspace_members"])
    return ({p["name"]: p for p in metadata["packages"] if p["id"] in members},
            Path(metadata["workspace_root"]) / "Cargo.lock")


def library(package: dict) -> dict:
    kinds = {"lib", "rlib", "dylib", "cdylib", "staticlib"}
    targets = [t for t in package["targets"] if kinds.intersection(t["kind"])]
    if len(targets) != 1:
        raise ValueError(f"{package['name']} has {len(targets)} library targets")
    return targets[0]


def generate(manifest: Path, package: dict, destination: Path, env: dict[str, str]) -> Path:
    target = library(package)
    # Bootstrap is used only for the JSON/visibility extraction flags, as in
    # cargo-semver-checks itself; runtime builds keep the pinned stable toolchain.
    run(
        ["cargo", "rustdoc", "--locked", "--manifest-path", str(manifest),
         "--package", package["name"], "--lib", "--all-features", "--",
         "-Z", "unstable-options", "--output-format=json",
         "--document-private-items", "--document-hidden-items"],
        manifest.parent, dict(env, RUSTC_BOOTSTRAP="1"),
    )
    generated = Path(env["CARGO_TARGET_DIR"]) / "doc" / f"{target['name']}.json"
    data = json.loads(generated.read_text())
    if data["crate_version"] != package["version"] or not data["includes_private"]:
        raise ValueError(f"incomplete or wrong-version Rustdoc for {package['name']}")
    root = data["index"][str(data["root"])]
    if root["name"] != target["name"]:
        raise ValueError(f"wrong Rustdoc crate identity for {package['name']}")
    shutil.copyfile(generated, destination)
    return destination


def compare(repo: Path, base: str, head: str, manifest_path: str,
            packages: list[str], toolchain: str, report: Path) -> None:
    relative = Path(manifest_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("manifest path must stay inside the committed snapshot")
    if not packages or any(not name for name in packages) or len(set(packages)) != len(packages):
        raise ValueError("provide a nonempty, unique package selection")
    env = dict(os.environ, RUSTUP_TOOLCHAIN=toolchain)
    # A caller's custom build target would redirect JSON to a target-specific
    # folder and alter the comparison's API universe. Require an explicit native
    # invocation here; target-specific comparison can be added as a full contract.
    if env.get("CARGO_BUILD_TARGET"):
        raise ValueError("locked comparison requires the native toolchain target")
    base_sha, head_sha = commit(repo, base, env), commit(repo, head, env)
    evidence = {"base": base_sha, "head": head_sha, "packages": [], "completed": False}
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="atlas-semver-") as directory:
            workspace = Path(directory)
            snapshots = [workspace / "baseline", workspace / "current"]
            for sha, root in zip((base_sha, head_sha), snapshots):
                export(repo, sha, root, env)
            manifests = [root / relative for root in snapshots]
            inventories, locks = zip(*(inventory(m, env) for m in manifests))
            # Save an immutable copy immediately after each successful build:
            # the shared Cargo target may overwrite the same crate's JSON later.
            env["CARGO_TARGET_DIR"] = str(workspace / "target")
            for name in packages:
                pair = [items[name] for items in inventories]
                # The workspace lock, not a member-local phantom lock, pins Git.
                before = [digest(lock) for lock in locks]
                kind = release_type(pair[0]["version"], pair[1]["version"])
                docs = [generate(m, p, workspace / f"{arm}-{name}.json", env)
                        for arm, m, p in zip(("base", "head"), manifests, pair)]
                if before != [digest(lock) for lock in locks]:
                    raise ValueError(f"Cargo.lock changed while documenting {name}")
                print(f"Locked API: {name} {pair[0]['version']} -> {pair[1]['version']} ({kind})",
                      flush=True)
                run(["cargo", "semver-checks", "--baseline-rustdoc", str(docs[0]),
                     "--current-rustdoc", str(docs[1]), "--release-type", kind],
                    repo, env)
                evidence["packages"].append({
                    "name": name, "base_version": pair[0]["version"],
                    "head_version": pair[1]["version"], "release_type": kind,
                    "base_lock_sha256": before[0], "head_lock_sha256": before[1],
                    "base_json_sha256": digest(docs[0]), "head_json_sha256": digest(docs[1]),
                })
            evidence["completed"] = True
    finally:
        report.write_text(json.dumps(evidence, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--manifest-path", default="Cargo.toml")
    parser.add_argument("--package", required=True, help="comma-separated library package names")
    parser.add_argument("--toolchain", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    compare(args.repo.resolve(), args.base, args.head, args.manifest_path,
            [name.strip() for name in args.package.split(",")], args.toolchain,
            args.report.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
