#!/usr/bin/env python3
"""Compile the recorded Aequitas consumer with its declared Eunomia source."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_git_process import (
    GitProcessError,
    GitProcessResult,
    archive,
    clean_process_env,
    execute_process,
    extract_archive,
)
from atlas_stack import ROOT, member_pins

CONSUMER = "aequitas"
PROVIDER = "eunomia"
REGISTRY_PACKAGES = (PROVIDER, "eunomia-derive")
CRATES_IO = "registry+https://github.com/rust-lang/crates.io-index"
PROBE = "atlas-pin-compile-probe"
GIT_TIMEOUT_SECONDS = 30
METADATA_TIMEOUT_SECONDS = 60
COMPILE_TIMEOUT_SECONDS = 180


class MeasurementError(RuntimeError):
    """The recorded pair could not be measured."""


def _text(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _run(
    command: list[str], *, cwd: Path, environment: dict[str, str], timeout: int
) -> GitProcessResult:
    try:
        return execute_process(
            command,
            cwd=cwd,
            env=environment,
            timeout=timeout,
        )
    except GitProcessError as exc:
        raise MeasurementError(str(exc)) from exc


def _pair_label(pins: dict[str, str]) -> str:
    consumer = pins.get(CONSUMER, "<missing>")
    provider = pins.get(PROVIDER, "<missing>")
    return f"{CONSUMER}@{consumer} -> {PROVIDER}@{provider}"


def _materialize(repo: Path, member: str, revision: str, destination: Path) -> Path:
    source = repo / "repos" / member
    if not source.is_dir():
        raise MeasurementError(f"member checkout is missing: {source}")
    payload = archive(source, revision, timeout=GIT_TIMEOUT_SECONDS)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        extract_archive(payload, destination)
    except (OSError, tarfile.TarError) as exc:
        raise MeasurementError(f"cannot extract {member}@{revision}: {exc}") from exc
    return destination


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise MeasurementError(f"cannot read {path.name}: {exc}") from exc


def _provider_source(manifest: Path) -> str | None:
    document = _read_toml(manifest)
    dependencies = document.get("dependencies")
    dependency = dependencies.get(PROVIDER) if isinstance(dependencies, dict) else None
    if isinstance(dependency, str) and dependency.strip():
        return None
    if isinstance(dependency, dict):
        if "git" in dependency:
            git = dependency["git"]
            if isinstance(git, str) and git.strip():
                return git
        else:
            version = dependency.get("version")
            if isinstance(version, str) and version.strip() and not (
                dependency.keys() & {"path", "registry", "registry-index", "workspace"}
            ):
                return None
    raise MeasurementError(f"consumer manifest has no supported source for {PROVIDER}")


def _registry_versions(lockfile: Path) -> dict[str, str]:
    packages = _read_toml(lockfile).get("package", [])
    if not isinstance(packages, list) or any(not isinstance(package, dict) for package in packages):
        raise MeasurementError("Cargo.lock has invalid package entries")
    versions = {}
    for name in REGISTRY_PACKAGES:
        entries = [package for package in packages if package.get("name") == name]
        if len(entries) != 1:
            raise MeasurementError(f"Cargo.lock has {len(entries)} entries for {name}, expected one")
        entry = entries[0]
        version = entry.get("version")
        checksum = entry.get("checksum")
        if (
            entry.get("source") != CRATES_IO
            or not isinstance(version, str)
            or not version.strip()
            or not isinstance(checksum, str)
            or re.fullmatch(r"[0-9a-f]{64}", checksum) is None
        ):
            raise MeasurementError(f"Cargo.lock must record a crates.io version and checksum for {name}")
        versions[name] = version
    return versions


def _toolchain(consumer: Path) -> str:
    document = _read_toml(consumer / "rust-toolchain.toml")
    toolchain = document.get("toolchain")
    channel = toolchain.get("channel") if isinstance(toolchain, dict) else None
    if not isinstance(channel, str) or not channel.strip():
        raise MeasurementError("consumer toolchain has no channel")
    return channel


def _selected_packages(metadata: bytes, names: tuple[str, ...]) -> dict:
    try:
        document = json.loads(_text(metadata))
    except json.JSONDecodeError as exc:
        raise MeasurementError(f"Cargo metadata is not JSON: {exc}") from exc
    packages = document.get("packages") if isinstance(document, dict) else None
    if not isinstance(packages, list):
        raise MeasurementError("Cargo metadata has no package list")
    selected = {}
    for name in names:
        entries = [
            package for package in packages
            if isinstance(package, dict) and package.get("name") == name
        ]
        if len(entries) != 1:
            raise MeasurementError(f"Cargo selected {len(entries)} {name} packages, expected one")
        selected[name] = entries[0]
    return selected


def _cargo_environment(target: Path) -> dict[str, str]:
    environment = clean_process_env()
    environment.update(
        CARGO_INCREMENTAL="0",
        CARGO_TARGET_DIR=str(target),
        CARGO_TERM_COLOR="never",
    )
    return environment


def _metadata(command: list[str], cwd: Path, environment: dict[str, str]) -> bytes:
    result = _run(command, cwd=cwd, environment=environment, timeout=METADATA_TIMEOUT_SECONDS)
    if result.returncode:
        detail = _text(result.stderr).strip() or _text(result.stdout).strip()
        raise MeasurementError(f"Cargo metadata failed: {detail}")
    return result.stdout


def _compile(
    command: list[str], cwd: Path, environment: dict[str, str], label: str
) -> tuple[int, str]:
    checked = _run(command, cwd=cwd, environment=environment, timeout=COMPILE_TIMEOUT_SECONDS)
    if checked.returncode:
        detail = "\n".join(
            value.strip()
            for value in (_text(checked.stdout), _text(checked.stderr))
            if value.strip()
        )
        return 1, f"PIN COMPILE FAIL: {label}\n{detail}"
    return 0, f"PIN COMPILE OK: {label}"


def _compile_registry(
    consumer: Path, revision: str, channel: str, environment: dict[str, str]
) -> tuple[int, str]:
    versions = _registry_versions(consumer / "Cargo.lock")
    cargo = ["cargo", f"+{channel}"]
    locked = ["--manifest-path", str(consumer / "Cargo.toml"), "--locked"]
    metadata = _metadata(
        cargo + ["metadata", "--format-version", "1"] + locked,
        consumer, environment,
    )
    for name, package in _selected_packages(metadata, REGISTRY_PACKAGES).items():
        if package.get("version") != versions[name] or package.get("source") != CRATES_IO:
            raise MeasurementError(f"Cargo did not select locked crates.io {name}@{versions[name]}")
    provider_labels = ", ".join(f"{name}@{version}" for name, version in versions.items())
    return _compile(
        cargo + ["check", "--package", CONSUMER, "--lib"] + locked,
        consumer, environment, f"{CONSUMER}@{revision} -> crates.io {provider_labels}",
    )


def compile_recorded_pair(repo: Path, scratch: Path, target: Path) -> tuple[int, str]:
    """Return the gate status and value-bearing report for the recorded pair."""
    pins = member_pins(repo)
    missing = [member for member in (CONSUMER, PROVIDER) if member not in pins]
    if missing:
        raise MeasurementError(f"recorded gitlinks are missing: {', '.join(missing)}")
    label = _pair_label(pins)
    consumer = _materialize(repo, CONSUMER, pins[CONSUMER], scratch / CONSUMER)
    source = _provider_source(consumer / "Cargo.toml")
    channel = _toolchain(consumer)
    environment = _cargo_environment(target)
    if source is None:
        return _compile_registry(consumer, pins[CONSUMER], channel, environment)

    provider = _materialize(repo, PROVIDER, pins[PROVIDER], scratch / PROVIDER)
    probe = scratch / PROBE
    (probe / "src").mkdir(parents=True)
    (probe / "src" / "lib.rs").write_text("", encoding="utf-8")
    manifest = probe / "Cargo.toml"
    manifest.write_text(
        "[package]\n"
        f'name = "{PROBE}"\n'
        'version = "0.0.0"\n'
        'edition = "2024"\n'
        'publish = false\n'
        "[dependencies]\n"
        f"aequitas = {{ path = {json.dumps(consumer.as_posix())} }}\n"
        "[workspace]\n"
        'resolver = "3"\n',
        encoding="utf-8",
    )
    config = scratch / "cargo-config.toml"
    provider_manifest = provider / "crates" / PROVIDER / "Cargo.toml"
    config.write_text(
        f"[patch.{json.dumps(source)}]\n"
        f"{PROVIDER} = {{ path = {json.dumps(provider_manifest.parent.as_posix())} }}\n",
        encoding="utf-8",
    )
    metadata = _metadata(
        [
            "cargo",
            f"+{channel}",
            "metadata",
            "--format-version",
            "1",
            "--manifest-path",
            str(manifest),
            "--config",
            str(config),
        ],
        probe, environment,
    )
    selected = _selected_packages(metadata, (PROVIDER,))[PROVIDER].get("manifest_path")
    expected = provider_manifest.resolve()
    if not isinstance(selected, str) or Path(selected).resolve() != expected:
        raise MeasurementError(
            f"Cargo selected {selected} instead of archived {expected}"
        )
    return _compile(
        [
            "cargo",
            f"+{channel}",
            "check",
            "--package",
            PROBE,
            "--lib",
            "--manifest-path",
            str(manifest),
            "--config",
            str(config),
            "--locked",
        ],
        probe, environment, label,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo = args.repo.resolve()
    label = _pair_label({})
    try:
        pins = member_pins(repo)
    except RuntimeError as exc:
        print(f"PIN COMPILE UNAVAILABLE: {label}: {exc}")
        return 2
    label = _pair_label(pins)
    try:
        with tempfile.TemporaryDirectory(prefix="atlas-pin-compile-") as directory:
            scratch = Path(directory)
            status, report = compile_recorded_pair(repo, scratch, scratch / "target")
    except (GitProcessError, MeasurementError, OSError) as exc:
        print(f"PIN COMPILE UNAVAILABLE: {label}: {exc}")
        return 2
    print(report)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
