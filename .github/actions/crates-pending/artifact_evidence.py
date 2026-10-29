"""Bind independently reproduced Cargo archives to one publication candidate."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
from typing import Callable

_COMMON = Path(__file__).resolve().parents[1] / "crate-release-identity" / "release_identity.py"
_SPEC = importlib.util.spec_from_file_location("crate_release_identity", _COMMON)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load the shared crate release identity owner")
_IDENTITY = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _IDENTITY
_SPEC.loader.exec_module(_IDENTITY)
COMMIT, PACKAGE_NAME, SHA256 = _IDENTITY.COMMIT, _IDENTITY.NAME, _IDENTITY.SHA256
METADATA_LIMIT = _IDENTITY.METADATA_LIMIT
IdentityError = _IDENTITY.IdentityError
index_path = _IDENTITY.index_path
parse_json = _IDENTITY.parse_json
read_url = _IDENTITY.read_url
sparse_index_versions = _IDENTITY.sparse_index_versions

ARTIFACT_PROFILE = "cargo-package-verify"

Run = Callable[[list[str]], "subprocess.CompletedProcess[str]"]
Fetch = Callable[[str, int], "tuple[int, bytes]"]


@dataclass(frozen=True)
class ArtifactContext:
    candidate: str
    toolchain: str
    target: str
    profile: str


@dataclass(frozen=True)
class ExpectedArtifacts:
    context: ArtifactContext
    cohort: tuple[tuple[str, str], ...]
    artifacts: dict[str, str]


def parse_expected_artifacts(text: str) -> ExpectedArtifacts:
    """Parse the independently generated package-archive evidence manifest."""
    try:
        value = parse_json(text)
    except (TypeError, ValueError) as error:
        raise SystemExit(f"invalid expected-artifacts manifest: {error}") from error
    if not isinstance(value, dict) or set(value) != {"context", "cohort", "artifacts"}:
        raise SystemExit("expected-artifacts must contain only context, cohort, and artifacts")
    context = value["context"]
    if (not isinstance(context, dict)
            or set(context) != {"candidate", "toolchain", "target", "profile"}
            or not isinstance(context.get("candidate"), str)
            or not COMMIT.fullmatch(context["candidate"])
            or any(not isinstance(context.get(key), str) or not context[key]
                   for key in ("toolchain", "target", "profile"))):
        raise SystemExit("expected-artifacts context is malformed")
    cohort = value["cohort"]
    if not isinstance(cohort, list):
        raise SystemExit("expected-artifacts cohort must be a package list")
    identities = []
    for package in cohort:
        if (not isinstance(package, dict) or set(package) != {"name", "version"}
                or not isinstance(package.get("name"), str)
                or not PACKAGE_NAME.fullmatch(package["name"])
                or not isinstance(package.get("version"), str) or not package["version"]):
            raise SystemExit("expected-artifacts cohort contains a malformed package identity")
        identities.append((package["name"], package["version"]))
    if len({name for name, _ in identities}) != len(identities):
        raise SystemExit("expected-artifacts cohort contains a duplicate package")
    artifacts = value["artifacts"]
    expected_files = {f"{name}-{version}.crate" for name, version in identities}
    if (not isinstance(artifacts, dict) or set(artifacts) != expected_files
            or any(not isinstance(digest, str) or not SHA256.fullmatch(digest)
                   for digest in artifacts.values())):
        raise SystemExit("expected-artifacts archive map is incomplete or malformed")
    return ExpectedArtifacts(
        ArtifactContext(context["candidate"], context["toolchain"],
                        context["target"], context["profile"]),
        tuple(identities), artifacts)


def checked_output(runner: Run, argv: list[str], description: str) -> str:
    result = runner(argv)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"{description} failed")
    return result.stdout.strip()


def validate_context(expected: ExpectedArtifacts, candidate: str, runner: Run) -> None:
    """Bind evidence to this clean checkout and the installed packaging toolchain."""
    if not COMMIT.fullmatch(candidate) or expected.context.candidate != candidate:
        raise SystemExit("expected-artifacts candidate differs from GITHUB_SHA")
    if checked_output(runner, ["git", "rev-parse", "HEAD"], "checkout revision query") != candidate:
        raise SystemExit("checkout HEAD differs from expected-artifacts candidate")
    status = checked_output(
        runner, ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        "checkout cleanliness query")
    if status:
        raise SystemExit("expected-artifacts checkout is dirty")
    rustc = checked_output(runner, ["rustc", "-Vv"], "Rust toolchain query")
    fields = dict(line.split(": ", 1) for line in rustc.splitlines() if ": " in line)
    if (fields.get("release") != expected.context.toolchain
            or fields.get("host") != expected.context.target):
        raise SystemExit("expected-artifacts toolchain or target differs from the installed Rust host")
    if expected.context.profile != ARTIFACT_PROFILE:
        raise SystemExit(f"expected-artifacts profile must be {ARTIFACT_PROFILE}")


def validate_selection(expected: ExpectedArtifacts, names: list[str], packages: list[dict]) -> None:
    """Require the expected cohort to be exactly the frozen planned set."""
    by_name = {package["name"]: package for package in packages}
    actual = []
    for name in names:
        package = by_name.get(name)
        registries = None if package is None else package.get("publish")
        if package is None or (registries is not None and "crates-io" not in registries):
            raise SystemExit(f"planned package is not publishable workspace metadata: {name}")
        actual.append((name, package["version"]))
    if tuple(actual) != expected.cohort:
        raise SystemExit("expected-artifacts cohort differs from the frozen planned package set")


def packaged_checksums(expected: ExpectedArtifacts, metadata_value: dict) -> dict[str, str]:
    """Hash the complete Cargo archives produced for the frozen cohort."""
    root = Path(metadata_value["target_directory"]) / "package"
    checksums = {}
    for name, version in expected.cohort:
        filename = f"{name}-{version}.crate"
        try:
            with (root / filename).open("rb") as stream:
                checksums[filename] = hashlib.file_digest(stream, "sha256").hexdigest()
        except OSError as error:
            raise SystemExit(f"packaged archive is missing or unreadable: {filename}: {error}") from error
    return checksums


def verify_expected_artifacts(expected: ExpectedArtifacts, names: list[str],
                              metadata_value: dict, candidate: str,
                              runner: Run, *, package: bool) -> None:
    """Verify clean source, exact cohort, and complete package bytes."""
    validate_context(expected, candidate, runner)
    validate_selection(expected, names, metadata_value["packages"])
    if package:
        arguments = [arg for name in names for arg in ("--package", name)]
        packaged = runner(["cargo", "package", "--locked", *arguments])
        if packaged.returncode != 0:
            sys.stderr.write(packaged.stderr)
            raise SystemExit("expected-artifacts package verification failed")
    if packaged_checksums(expected, metadata_value) != expected.artifacts:
        raise SystemExit("packaged archive checksum differs from expected-artifacts")
    validate_context(expected, candidate, runner)


def published_checksum(name: str, version: str, fetch: Fetch) -> str:
    """Return one exact sparse-index checksum, rejecting ambiguous records."""
    try:
        versions = sparse_index_versions(name, fetch)
    except IdentityError as error:
        raise ValueError(str(error)) from error
    checksum = None if versions is None else versions.get(version)
    if checksum is None:
        raise ValueError(f"crates.io index lacks one valid checksum for {name}@{version}")
    return checksum
