#!/usr/bin/env python3
"""Compile the recorded Aequitas consumer against the recorded Eunomia pin."""

from __future__ import annotations

import argparse
import json
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


def _provider_source(manifest: Path) -> str:
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise MeasurementError(f"cannot read consumer manifest: {exc}") from exc
    dependencies = document.get("dependencies")
    dependency = dependencies.get(PROVIDER) if isinstance(dependencies, dict) else None
    source = dependency.get("git") if isinstance(dependency, dict) else None
    if not isinstance(source, str) or not source.strip():
        raise MeasurementError(f"consumer manifest has no Git source for {PROVIDER}")
    return source


def _toolchain(consumer: Path) -> str:
    manifest = consumer / "rust-toolchain.toml"
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise MeasurementError(f"cannot read consumer toolchain: {exc}") from exc
    toolchain = document.get("toolchain")
    channel = toolchain.get("channel") if isinstance(toolchain, dict) else None
    if not isinstance(channel, str) or not channel.strip():
        raise MeasurementError("consumer toolchain has no channel")
    return channel


def _selected_provider(metadata: bytes) -> Path:
    try:
        document = json.loads(_text(metadata))
    except json.JSONDecodeError as exc:
        raise MeasurementError(f"Cargo metadata is not JSON: {exc}") from exc
    packages = document.get("packages")
    selected = [
        package.get("manifest_path")
        for package in packages or []
        if isinstance(package, dict) and package.get("name") == PROVIDER
    ]
    if len(selected) != 1 or not isinstance(selected[0], str):
        raise MeasurementError(f"Cargo selected {len(selected)} {PROVIDER} packages")
    return Path(selected[0]).resolve()


def compile_recorded_pair(repo: Path, scratch: Path, target: Path) -> tuple[int, str]:
    """Return the gate status and value-bearing report for the recorded pair."""
    pins = member_pins(repo)
    missing = [member for member in (CONSUMER, PROVIDER) if member not in pins]
    if missing:
        raise MeasurementError(f"recorded gitlinks are missing: {', '.join(missing)}")
    label = _pair_label(pins)
    consumer = _materialize(repo, CONSUMER, pins[CONSUMER], scratch / CONSUMER)
    provider = _materialize(repo, PROVIDER, pins[PROVIDER], scratch / PROVIDER)
    source = _provider_source(consumer / "Cargo.toml")
    channel = _toolchain(consumer)
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
    environment = clean_process_env()
    environment.update(
        CARGO_INCREMENTAL="0",
        CARGO_TARGET_DIR=str(target),
        CARGO_TERM_COLOR="never",
    )
    metadata = _run(
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
        cwd=probe,
        environment=environment,
        timeout=METADATA_TIMEOUT_SECONDS,
    )
    if metadata.returncode:
        detail = _text(metadata.stderr).strip() or _text(metadata.stdout).strip()
        raise MeasurementError(f"Cargo metadata failed: {detail}")
    selected = _selected_provider(metadata.stdout)
    expected = provider_manifest.resolve()
    if selected != expected:
        raise MeasurementError(
            f"Cargo selected {selected} instead of archived {expected}"
        )
    checked = _run(
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
        cwd=probe,
        environment=environment,
        timeout=COMPILE_TIMEOUT_SECONDS,
    )
    if checked.returncode:
        detail = "\n".join(
            value.strip()
            for value in (_text(checked.stdout), _text(checked.stderr))
            if value.strip()
        )
        return 1, f"PIN COMPILE FAIL: {label}\n{detail}"
    return 0, f"PIN COMPILE OK: {label}"


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
