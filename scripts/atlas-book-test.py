#!/usr/bin/env python3
"""Build a library and test its mdBook against Cargo's emitted artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable, Iterable

import process_tree


class BookTestError(RuntimeError):
    """The package build cannot supply a sound mdBook library path."""


def _text(value: bytes | None) -> str:
    return "" if value is None else value.decode("utf-8", errors="replace")


def _run(command: list[str], *, cwd: Path, timeout: float) -> bytes:
    result = process_tree.run(command, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        detail = _text(result.stderr).strip()
        raise BookTestError(
            f"command exited {result.returncode}: {' '.join(command)}"
            + (f"\n{detail}" if detail else "")
        )
    return result.stdout or b""


def _package(metadata: object, name: str, crate: str | None) -> tuple[str, str]:
    if not isinstance(metadata, dict) or not isinstance(metadata.get("packages"), list):
        raise BookTestError("cargo metadata returned no package list")
    packages = [item for item in metadata["packages"] if item.get("name") == name]
    if len(packages) != 1:
        raise BookTestError(f"expected one metadata package named {name!r}, found {len(packages)}")
    package = packages[0]
    targets = [
        item
        for item in package.get("targets", [])
        if "lib" in item.get("kind", []) and (crate is None or item.get("name") == crate)
    ]
    if len(targets) != 1:
        requested = "library" if crate is None else f"library target {crate!r}"
        raise BookTestError(f"expected one {requested} in package {name!r}, found {len(targets)}")
    return package["id"], targets[0]["name"]


def _artifact_messages(output: bytes, package_id: str, crate: str) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    root_seen = False
    for number, raw in enumerate(output.splitlines(), 1):
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as error:
            raise BookTestError(f"malformed Cargo JSON on line {number}: {error.msg}") from error
        if message.get("reason") != "compiler-artifact":
            continue
        target = message.get("target", {})
        root = message.get("package_id") == package_id and target.get("name") == crate
        files = []
        for value in message.get("filenames", []):
            path = Path(value)
            kinds = set(target.get("kind", [])) | set(target.get("crate_types", []))
            if path.suffix == ".rlib" or (
                "proc-macro" in kinds and path.suffix.lower() in {".dll", ".dylib", ".so"}
            ):
                files.append(path)
        if root:
            root_seen = any(path.suffix == ".rlib" for path in files)
        for path in files:
            selected.append(
                {
                    "path": path,
                    "package_id": message.get("package_id"),
                    "target": target.get("name"),
                    "fresh": bool(message.get("fresh")),
                }
            )
    if not root_seen:
        raise BookTestError(f"Cargo emitted no rlib for {package_id} target {crate!r}")
    if not selected:
        raise BookTestError("Cargo emitted no linkable artifacts")
    return selected


def _stage(artifacts: Iterable[dict[str, object]], destination: Path) -> list[dict[str, object]]:
    staged: dict[str, tuple[str, dict[str, object]]] = {}
    for artifact in artifacts:
        source = artifact["path"]
        if not isinstance(source, Path) or not source.is_file() or source.is_symlink():
            raise BookTestError(f"Cargo emitted a missing or non-regular artifact: {source}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        prior = staged.get(source.name)
        if prior is not None:
            if prior[0] != digest:
                raise BookTestError(f"conflicting Cargo artifacts share basename {source.name!r}")
            continue
        target = destination / source.name
        shutil.copyfile(source, target)
        record = {key: value for key, value in artifact.items() if key != "path"}
        record.update(path=str(source), basename=source.name, sha256=digest, size=source.stat().st_size)
        staged[source.name] = (digest, record)
    return [entry[1] for entry in staged.values()]


def _stage_and_run(
    artifacts: Iterable[dict[str, object]],
    command: Callable[[Path], list[str]],
    *,
    cwd: Path,
    timeout: float,
    temp_root: Path | None = None,
) -> dict[str, object]:
    stage_name = ""
    with tempfile.TemporaryDirectory(prefix="atlas-mdbook-", dir=temp_root) as raw_stage:
        stage = Path(raw_stage)
        stage_name = raw_stage
        records = _stage(artifacts, stage)
        _run(command(stage), cwd=cwd, timeout=timeout)
    return {
        "stage": stage_name,
        "artifacts": records,
        "artifact_count": len(records),
        "artifact_bytes": sum(int(item["size"]) for item in records),
    }


def execute(
    manifest: Path,
    package: str,
    crate: str | None,
    book: Path,
    *,
    cargo: str = "cargo",
    mdbook: str = "mdbook",
    build_timeout: float = 720,
    test_timeout: float = 480,
    temp_root: Path | None = None,
) -> dict[str, object]:
    manifest = manifest.resolve()
    cwd = manifest.parent
    metadata_output = _run(
        [cargo, "metadata", "--locked", "--no-deps", "--format-version", "1", "--manifest-path", str(manifest)],
        cwd=cwd,
        timeout=min(build_timeout, 120),
    )
    try:
        metadata = json.loads(metadata_output)
    except json.JSONDecodeError as error:
        raise BookTestError(f"cargo metadata returned malformed JSON: {error.msg}") from error
    package_id, crate_name = _package(metadata, package, crate)
    build_output = _run(
        [cargo, "build", "--locked", "-p", package, "--manifest-path", str(manifest), "--message-format=json-render-diagnostics"],
        cwd=cwd,
        timeout=build_timeout,
    )
    report = _stage_and_run(
        _artifact_messages(build_output, package_id, crate_name),
        lambda stage: [mdbook, "test", str(book.resolve()), "--library-path", str(stage)],
        cwd=cwd,
        timeout=test_timeout,
        temp_root=temp_root,
    )
    report.update(package_id=package_id, crate=crate_name, build_timeout=build_timeout, test_timeout=test_timeout)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("Cargo.toml"))
    parser.add_argument("--package", required=True)
    parser.add_argument("--crate")
    parser.add_argument("--book", type=Path, required=True)
    parser.add_argument("--cargo", default="cargo")
    parser.add_argument("--mdbook", default="mdbook")
    parser.add_argument("--build-timeout-seconds", type=float, default=720)
    parser.add_argument("--test-timeout-seconds", type=float, default=480)
    args = parser.parse_args()
    try:
        report = execute(
            args.manifest, args.package, args.crate, args.book, cargo=args.cargo,
            mdbook=args.mdbook, build_timeout=args.build_timeout_seconds,
            test_timeout=args.test_timeout_seconds,
        )
    except (BookTestError, process_tree.ProcessTreeTimeout, OSError, ValueError) as error:
        print(f"book test failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
