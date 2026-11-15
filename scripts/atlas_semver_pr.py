#!/usr/bin/env python3
"""Compare crates against a pull-request base built from the base's own lock.

cargo-semver-checks 0.51.0 resolves a `--baseline-rev`/`--baseline-root` afresh with
`cargo update` in a placeholder workspace (`run_cargo_update`, src/data_generation/
generate.rs), so a git dependency that moved past the base's requirement fails before
any comparison. Following ADR 0069's separate development evidence, this script builds
both rustdoc JSON files under `cargo doc --locked` on a pinned nightly (no `RUSTC_BOOTSTRAP`)
and passes them with `--baseline-rustdoc`/`--current-rustdoc`. Export and command running
are shared with atlas_semver_locked.py.

Limits: on this path cargo-semver-checks reads no `metadata.cargo-semver-checks` lint levels
(`OverrideStack::new()` in 0.51.0), and a lock-only change can register as an API change
because each side resolves its own lock (a hypothesis, not witnessed).

Exit status: 0 no update required, 100 an update is required, 101 a comparison failed.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import NamedTuple

import process_tree
from atlas_semver_locked import export, invoke as run, text

# The rustdoc flags and heuristic feature filter cargo-semver-checks 0.51.0 applies itself.
RUSTDOCFLAGS = ("-Z unstable-options --document-private-items --document-hidden-items "
                "--output-format=json --cap-lints=allow")
IGNORED_FEATURES = frozenset({"unstable", "nightly", "bench", "no_std"})
IGNORED_PREFIXES = ("_", "unstable-", "unstable_")
PROCESS_FAILURES = (process_tree.ProcessTreeTimeout, process_tree.ProcessTreeCleanupError)
LIBRARY_KINDS = frozenset({"lib", "rlib", "dylib", "cdylib", "staticlib"})
DETAILS = {"clean": "no update required",
           "update-required": "the manifest version does not cover the detected change",
           "failed": "cargo-semver-checks rendered no verdict"}


class Outcome(NamedTuple):
    """One crate's result: clean, update-required, failed, or skipped."""

    package: str
    status: str
    detail: str


def heuristic_features(features: dict[str, list[str]]) -> list[str]:
    """Return the features the checker enables when none is requested."""
    return sorted(n for n in features
                  if n not in IGNORED_FEATURES and not n.startswith(IGNORED_PREFIXES))


def classify(code: int) -> str:
    """Map a cargo-semver-checks exit code to a status; only 0 and 100 are verdicts."""
    return {0: "clean", 100: "update-required"}.get(code, "failed")


def tail(result, lines: int = 12) -> str:
    """Return the last diagnostic lines of a finished command."""
    lines_out = (text(result.stdout) + text(result.stderr)).strip().splitlines()
    return chr(10).join(lines_out[-lines:])


def workspace_packages(manifest: Path, env: dict[str, str]) -> dict[str, dict]:
    """Return workspace members by name; `--no-deps` needs no resolution."""
    result = run(["cargo", "metadata", "--no-deps", "--format-version", "1",
                  "--manifest-path", str(manifest)], manifest.parent, env)
    if result.returncode != 0:
        raise RuntimeError(f"cargo metadata failed:\n{tail(result)}")
    metadata = json.loads(result.stdout)
    members = set(metadata["workspace_members"])
    return {p["name"]: dict(p, workspace_root=metadata["workspace_root"])
            for p in metadata["packages"] if p["id"] in members}


def library_name(package: dict) -> str | None:
    """Return the library target's crate name, or None when it has no API surface."""
    return next((t["name"].replace("-", "_") for t in package["targets"]
                 if LIBRARY_KINDS & set(t["kind"])), None)


def locked_rustdoc(manifest: Path, package: dict, library: str, target_dir: Path,
                   env: dict[str, str], toolchain: str) -> Path:
    """Build one side's rustdoc JSON from its committed lock when it has one."""
    locked = (Path(package["workspace_root"]) / "Cargo.lock").is_file()
    command = ["cargo", "doc", "--manifest-path", str(manifest), "--package", package["name"],
               "--lib", "--no-deps", "--target-dir", str(target_dir)]
    command += ["--locked"] if locked else []
    features = heuristic_features(package["features"])
    command += ["--features", ",".join(features)] if features else []
    flags = f"{env.get('RUSTDOCFLAGS', '')} {RUSTDOCFLAGS}".strip()
    # RUSTC/RUSTDOC overrides would defeat the pinned toolchain.
    pinned = {k: v for k, v in env.items() if k not in ("RUSTC", "RUSTDOC")}
    result = run(command, manifest.parent,
                 dict(pinned, RUSTUP_TOOLCHAIN=toolchain, RUSTDOCFLAGS=flags))
    if result.returncode != 0:
        raise RuntimeError(f"rustdoc build failed ({'locked' if locked else 'no committed lock'}):"
                           f"{chr(10)}{tail(result)}")
    produced = target_dir / "doc" / f"{library}.json"
    if not produced.is_file():
        raise RuntimeError(f"rustdoc build produced no {produced.name}")
    return produced


def compare_package(name: str, manifests: tuple[Path, Path], packages: tuple[dict, dict],
                    scratch: Path, env: dict[str, str], toolchain: str) -> Outcome:
    """Compare one crate (base, head), reporting skipped, failed, or a verdict."""
    if name not in packages[0] or name not in packages[1]:
        return Outcome(name, "skipped", "absent from the base or head, so nothing to compare")
    libraries = [library_name(p[name]) for p in packages]
    if None in libraries:
        return Outcome(name, "skipped", "no library target on one side")
    documents = []
    for side, manifest, side_packages, library in zip(("base", "head"), manifests, packages,
                                                      libraries):
        try:
            documents.append(locked_rustdoc(manifest, side_packages[name], library,
                                            scratch / side, env, toolchain))
        except (RuntimeError, *PROCESS_FAILURES) as error:
            return Outcome(name, "failed", f"{side} rustdoc unavailable: {error}")
    try:
        result = run(["cargo", "semver-checks", "--manifest-path", str(manifests[1]),
                      "--package", name, "--baseline-rustdoc", str(documents[0]),
                      "--current-rustdoc", str(documents[1])], manifests[1].parent, env)
    except PROCESS_FAILURES as error:
        return Outcome(name, "failed", f"cargo-semver-checks did not finish: {error}")
    print(f"--- {name}: exit {result.returncode}{chr(10)}{tail(result, 40)}", flush=True)
    status = classify(result.returncode)
    return Outcome(name, status, DETAILS[status] + (
        f" (exit {result.returncode})" if status == "failed" else ""))


def cell(detail: str) -> str:
    """Return a detail that stays inside one Markdown table cell."""
    return " ".join(detail.split()).replace("|", "\\|")


def render(outcomes: list[Outcome], base: str) -> str:
    """Render the per-crate summary; a tool failure is never a version-bump request."""
    labels = {"clean": "compared", "update-required": "compared",
              "failed": "FAILED to run", "skipped": "not compared"}
    lines = [f"### SemVer against base `{base[:12]}` (rustdoc built `--locked` on each side that has a committed lock)",
             "", "| crate | comparison | result |", "| --- | --- | --- |"]
    lines += [f"| `{o.package}` | {labels[o.status]} | {cell(o.detail)} |" for o in outcomes]
    for status, note in (("failed", "**Tool failure** for {}: no verdict was rendered, which "
                          "says nothing about their API."),
                         ("update-required", "A version update is required for {}.")):
        names = ", ".join(f"`{o.package}`" for o in outcomes if o.status == status)
        lines += ["", note.format(names)] if names else []
    return "\n".join(lines) + "\n"


def compare_all(args: argparse.Namespace, env: dict[str, str]) -> list[Outcome]:
    """Export the base once and compare every requested package."""
    relative = Path(args.manifest_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("manifest path must stay inside the repository")
    repo = args.repo.resolve()  # cargo runs in the manifest's directory, so a relative path breaks
    with tempfile.TemporaryDirectory(prefix="atlas-semver-pr-") as directory:
        scratch = Path(directory)
        export(repo, args.base, scratch / "base", env)
        manifests = (scratch / "base" / relative, repo / relative)
        packages = tuple(workspace_packages(m, env) for m in manifests)
        return [compare_package(name, manifests, packages, scratch / "target", env,
                                args.rustdoc_toolchain) for name in args.packages]


def main(argv: list[str] | None = None) -> int:
    """Compare every package and write the summary; a crash is a reported tool failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--manifest-path", default="Cargo.toml")
    parser.add_argument("--package", required=True)
    parser.add_argument("--rustdoc-toolchain", required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    args.packages = [n.strip() for n in args.package.split(",") if n.strip()]
    if not args.packages:
        parser.error("--package must name a crate")
    try:
        outcomes = compare_all(args, dict(os.environ))
    except (RuntimeError, ValueError, OSError, *PROCESS_FAILURES) as error:
        outcomes = [Outcome(n, "failed", f"comparison did not start: {error}")
                    for n in args.packages]
    summary = render(outcomes, args.base)
    print(summary)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as stream:
            stream.write(summary)
    statuses = {o.status for o in outcomes}
    return 101 if "failed" in statuses else 100 if "update-required" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
