#!/usr/bin/env python3
"""Attempt native SemVer analysis and retain exact locked-graph evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
import process_tree
TOOL_VERSION = "0.51.0"
COMMAND_SECONDS = 600
KNOWN_RESOLUTION_DIAGNOSTICS = (
    "failed to select a version for the requirement",
    "candidate versions found which didn't match",
    "location searched: Git repository",
)
def text(data: bytes | None) -> str:
    """Decode tool output without hiding malformed bytes."""
    return (data or b"").decode("utf-8", errors="replace")
def invoke(argv: list[str], cwd: Path, env: dict[str, str], timeout: float = COMMAND_SECONDS):
    """Run one command under Atlas's process-tree deadline."""
    return process_tree.run(
        argv, cwd=cwd, env=env, timeout=timeout,
        output_mode=process_tree.OutputMode.CAPTURE,
    )
def checked(argv: list[str], cwd: Path, env: dict[str, str], timeout: float = COMMAND_SECONDS):
    """Run a command and preserve both output streams on failure."""
    result = invoke(argv, cwd, env, timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"command exited {result.returncode}: {' '.join(argv)}\n"
            f"{text(result.stdout)}{text(result.stderr)}"
        )
    return result
def digest_bytes(data: bytes) -> str:
    """Return the evidence digest used by the report."""
    return hashlib.sha256(data).hexdigest()
def digest(path: Path) -> str:
    """Hash one immutable input or generated artifact."""
    return digest_bytes(path.read_bytes())
def commit(repo: Path, ref: str, env: dict[str, str]) -> str:
    """Resolve a commit without accepting option-shaped revisions."""
    value = text(checked(
        ["git", "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"],
        repo, env, 120,
    ).stdout).strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise ValueError(f"invalid resolved commit: {value!r}")
    return value
def export(repo: Path, revision: str, destination: Path, env: dict[str, str]) -> None:
    """Export committed source without reading the shared checkout."""
    archive = checked(
        ["git", "archive", "--format=tar", revision], repo, env, 120,
    ).stdout
    destination.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(destination, filter="data")
def permission(baseline: str, current: str) -> str:
    """Return the manifest boundary's Cargo-compatible change class."""
    def core(version: str) -> tuple[int, int, int]:
        match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:[-+].*)?", version)
        if match is None:
            raise ValueError(f"unsupported version {version!r}")
        return tuple(map(int, match.groups()))

    old, new = core(baseline), core(current)
    if new < old:
        raise ValueError(f"version decreases: {baseline} -> {current}")
    if (new[0] > old[0] or (old[0] == 0 and new[1] > old[1])
            or (old[:2] == (0, 0) and new[2] > old[2])):
        return "major"
    if new[1] > old[1]:
        return "minor"
    return "patch"
def cargo_features(policy: str, features: list[str]) -> list[str]:
    """Map one explicit feature policy to Cargo flags."""
    flags = {"all": ["--all-features"], "default": [], "explicit": ["--no-default-features"]}[policy]
    return flags + (["--features", ",".join(features)] if features else [])
def semver_features(policy: str, features: list[str]) -> list[str]:
    """Map the same feature policy to cargo-semver-checks flags."""
    flags = {
        "all": ["--all-features"],
        "default": ["--default-features"],
        "explicit": ["--only-explicit-features"],
    }[policy]
    return flags + sum((["--features", feature] for feature in features), [])
def inventory(manifest: Path, env: dict[str, str]) -> tuple[dict[str, dict], Path]:
    """Read resolved package facts without changing the committed lock."""
    result = checked([
        "cargo", "metadata", "--locked", "--no-deps", "--format-version", "1",
        "--manifest-path", str(manifest),
    ], manifest.parent, env)
    metadata = json.loads(text(result.stdout))
    members = set(metadata["workspace_members"])
    packages = {item["name"]: item for item in metadata["packages"] if item["id"] in members}
    return packages, Path(metadata["workspace_root"]) / "Cargo.lock"

def generate(manifest: Path, package: dict, output: Path, env: dict[str, str], config: dict) -> Path:
    """Generate one locked Rustdoc artifact for supplemental comparison."""
    targets = [target for target in package["targets"]
               if {"lib", "rlib", "dylib", "cdylib", "staticlib"} & set(target["kind"])]
    if len(targets) != 1:
        raise ValueError(f"{package['name']} has {len(targets)} library targets")
    command = [
        "cargo", "rustdoc", "--locked", "--manifest-path", str(manifest),
        "--package", package["name"], "--lib", "--target", config["target"],
        *cargo_features(config["feature_policy"], config["features"]), "--",
        "-Z", "unstable-options", "--output-format=json", "--document-private-items",
        "--document-hidden-items",
    ]
    checked(command, manifest.parent, dict(env, RUSTC_BOOTSTRAP="1"))
    generated = Path(env["CARGO_TARGET_DIR"]) / config["target"] / "doc" / f"{targets[0]['name']}.json"
    data = json.loads(generated.read_text(encoding="utf-8"))
    if data["crate_version"] != package["version"] or not data["includes_private"]:
        raise ValueError(f"incomplete Rustdoc for {package['name']}")
    shutil.copyfile(generated, output)
    return output


def native_command(manifest: Path, package: str, baseline: str, config: dict) -> list[str]:
    """Build the native command; every Git baseline uses --baseline-rev."""
    return [
        "cargo", "semver-checks", "--manifest-path", str(manifest), "--package", package,
        "--baseline-rev", baseline, "--release-type", config["change_class"],
        "--target", config["target"], *semver_features(config["feature_policy"], config["features"]),
    ]


def result_record(command: list[str], result) -> dict:
    """Record a reviewable command result without interpreting exit 101 as success."""
    diagnostics = text(result.stdout) + text(result.stderr)
    statuses = {0: "pass", 100: "deny_findings", 101: "execution_error"}
    return {
        "command": command,
        "exit_code": result.returncode,
        "status": statuses.get(result.returncode, "unknown_failure"),
        "diagnostics": diagnostics,
        "diagnostics_sha256": digest_bytes(diagnostics.encode()),
    }


def attempt(command: list[str], cwd: Path, env: dict[str, str], timeout: float = COMMAND_SECONDS) -> dict:
    """Classify execution and cleanup failures without fabricating a verdict."""
    try:
        return result_record(command, invoke(command, cwd, env, timeout))
    except process_tree.ProcessTreeTimeout as error:
        diagnostics = text(error.stdout) + text(error.stderr)
        return {"command": command, "exit_code": None, "status": "timeout",
                "diagnostics": diagnostics,
                "diagnostics_sha256": digest_bytes(diagnostics.encode())}
    except process_tree.ProcessTreeCleanupError as error:
        diagnostics = str(error)
        return {"command": command, "exit_code": None, "status": "cleanup_error",
                "diagnostics": diagnostics,
                "diagnostics_sha256": digest_bytes(diagnostics.encode())}


def supplemental(roots: list[Path], manifests: list[Path], pair: list[dict], locks: list[Path],
                 package: str, env: dict[str, str], config: dict, workspace: Path) -> dict:
    """Collect locked consumer and prebuilt-Rustdoc evidence after a known native limitation."""
    before = [digest(lock) for lock in locks]
    checks = []
    cargo_flags = cargo_features(config["feature_policy"], config["features"])
    for root, manifest in zip(roots, manifests):
        command = ["cargo", "check", "--locked", "--manifest-path", str(manifest),
                   "--package", package, "--target", config["target"], *cargo_flags]
        checks.append(attempt(command, root, env))
    docs = [generate(manifest, item, workspace / f"{arm}-{package}.json", env, config)
            for arm, manifest, item in zip(("baseline", "current"), manifests, pair)]
    if before != [digest(lock) for lock in locks]:
        raise RuntimeError(f"Cargo.lock changed while documenting {package}")
    command = [
        "cargo", "semver-checks", "--baseline-rustdoc", str(docs[0]),
        "--current-rustdoc", str(docs[1]), "--release-type", config["change_class"],
    ]
    comparison = attempt(command, roots[1], env)
    return {
        "kind": "SUPPLEMENTAL",
        "disposition": "requires-review",
        "consumer_contract": checks,
        "comparison": comparison,
        "baseline_lock_sha256": before[0],
        "current_lock_sha256": before[1],
        "baseline_rustdoc_sha256": digest(docs[0]),
        "current_rustdoc_sha256": digest(docs[1]),
    }


def compare(args) -> int:
    """Attempt every native baseline and write evidence even when one is unavailable."""
    repo = args.repo.resolve()
    env = dict(os.environ, RUSTUP_TOOLCHAIN=args.toolchain)
    target_dir = Path(env.get("CARGO_TARGET_DIR", "")).resolve()
    if not env.get("CARGO_TARGET_DIR"):
        raise ValueError("CARGO_TARGET_DIR must name the shared build cache")
    env["CARGO_TARGET_DIR"] = str(target_dir)
    base, head = commit(repo, args.base, env), commit(repo, args.head, env)
    if commit(repo, "HEAD", env) != head:
        raise ValueError("--head must be the checked-out revision used by the native tool")
    if invoke(["git", "diff-index", "--quiet", head, "--"], repo, env, 120).returncode != 0:
        raise ValueError("native comparison requires a clean tracked checkout")
    config = {
        "change_class": args.change_class,
        "feature_policy": args.feature_policy,
        "features": args.features,
        "target": args.target,
        "toolchain": args.toolchain,
    }
    tool = shutil.which("cargo-semver-checks")
    if tool is None:
        raise RuntimeError("cargo-semver-checks 0.51.0 is not installed")
    version = text(checked(["cargo", "semver-checks", "--version"], repo, env, 120).stdout).strip()
    if version != f"cargo-semver-checks {TOOL_VERSION}":
        raise RuntimeError(f"expected cargo-semver-checks {TOOL_VERSION}, found {version!r}")
    report = {
        "schema": 1, "base": base, "head": head, "configuration": config,
        "tool": {"version": version, "sha256": digest(Path(tool))}, "packages": [],
    }
    exit_code = 0
    args.report.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="atlas-semver-") as directory:
            workspace = Path(directory)
            roots = [workspace / "baseline", workspace / "current"]
            for revision, root in zip((base, head), roots):
                export(repo, revision, root, env)
            relative = Path(args.manifest_path)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("manifest path must stay inside the committed snapshot")
            manifests = [root / relative for root in roots]
            inventories, locks = zip(*(inventory(manifest, env) for manifest in manifests))
            for package in args.packages:
                pair = [inventory_[package] for inventory_ in inventories]
                boundary = permission(pair[0]["version"], pair[1]["version"])
                command = native_command(repo / relative, package, base, config)
                native = attempt(command, repo, env)
                entry = {
                    "name": package, "versions": [pair[0]["version"], pair[1]["version"]],
                    "manifest_permission": boundary, "native": native,
                    "manifest_sha256": [digest(manifest) for manifest in manifests],
                    "lock_sha256": [digest(lock) for lock in locks],
                }
                if {"patch": 0, "minor": 1, "major": 2}[boundary] < {
                    "patch": 0, "minor": 1, "major": 2
                }[args.change_class]:
                    entry["manifest_error"] = "declared change class exceeds manifest boundary"
                    exit_code = 101
                if native["exit_code"] == 100:
                    exit_code = max(exit_code, 100)
                elif native["exit_code"] != 0:
                    exit_code = 101
                    known = all(fragment in native["diagnostics"]
                                for fragment in KNOWN_RESOLUTION_DIAGNOSTICS)
                    entry["known_resolution_limitation"] = known
                    if known:
                        try:
                            entry["supplemental"] = supplemental(
                                roots, manifests, pair, list(locks), package, env, config, workspace,
                            )
                        except Exception as error:
                            entry["supplemental"] = {
                                "kind": "SUPPLEMENTAL", "disposition": "failed",
                                "error": f"{type(error).__name__}: {error}",
                            }
                report["packages"].append(entry)
    finally:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return exit_code


def parse_args():
    """Parse the explicit comparison contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--manifest-path", default="Cargo.toml")
    parser.add_argument("--package", required=True)
    parser.add_argument("--toolchain", required=True)
    parser.add_argument("--change-class", choices=("patch", "minor", "major"), required=True)
    parser.add_argument("--feature-policy", choices=("all", "default", "explicit"), required=True)
    parser.add_argument("--features", default="")
    parser.add_argument("--target", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    args.packages = [name.strip() for name in args.package.split(",") if name.strip()]
    args.features = [name.strip() for name in args.features.split(",") if name.strip()]
    if not args.packages or len(args.packages) != len(set(args.packages)):
        parser.error("--package must contain unique names")
    if args.feature_policy != "explicit" and args.features:
        parser.error("--features requires --feature-policy explicit")
    return args


def main() -> int:
    """Run the comparison contract."""
    return compare(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
