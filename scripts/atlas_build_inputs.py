"""Compute a build's dimensions and dependency data from its source root and command."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence

from atlas_build_lease import BuildIdentityError
from atlas_build_package_source import cached_package_source_digest
from atlas_build_records import BuildSpec, _content
from atlas_build_snapshot import _cargo_metadata, dependency_snapshot
from atlas_build_source import (
    _canonical,
    _sha256_bytes,
    cargo_config_digest,
    environment_digest,
    source_identity,
    toolchain_identity,
)


def _config_arguments(command: Sequence[str]) -> tuple[str, ...]:
    """The literal `--config` argument values a command line carries.

    Each names or inlines a Cargo configuration source the discovery walk
    in `cargo_config_digest` cannot find by directory alone.
    """
    arguments: list[str] = []
    iterator = iter(command)
    for token in iterator:
        text = str(token)
        if text == "--config":
            value = next(iterator, None)
            if value is not None:
                arguments.append(str(value))
        elif text.startswith("--config="):
            arguments.append(text[len("--config=") :])
    return tuple(arguments)


def _inline_environment(command: Sequence[str]) -> dict[str, str]:
    """The `NAME=VALUE` assignments a leading `env` prefix sets for this command.

    `env RUSTDOCFLAGS=... cargo doc` sets an environment variable no ambient
    `os.environ` snapshot carries, so `environment_digest` alone cannot see
    it move; only a leading run of `NAME=VALUE` tokens right after `env` is
    parsed, matching the `env` program's own simple form (`env` is an
    external program, not a shell builtin, so this command list -- already
    a `Sequence[str]` with no shell involved -- names it as an ordinary
    argument; the parse still stops at `-u`/`-i`/`-C` and any other option,
    since anything past a leading run of assignments is not something this
    identity check can attribute to a specific variable without invoking
    `env` itself).
    """
    values: dict[str, str] = {}
    iterator = iter(command)
    first = next(iterator, None)
    if first != "env":
        return values
    for token in iterator:
        text = str(token)
        if "=" not in text or text.startswith("-"):
            break
        name, _, value = text.partition("=")
        if not name:
            break
        values[name] = value
    return values


def build_spec(
    root: Path,
    package: str,
    target_dir: Path,
    profile: str,
    target: str,
    features: str,
    command: Sequence[str] = (),
    command_key: str | None = None,
    ignore_paths: Sequence[Path] = (),
    dependency_digest: str = "",
    execution_root: Path | None = None,
    selection: Sequence[str] = (),
) -> BuildSpec:
    """`selection` is every package the command builds, `package` alone by default."""
    if not package:
        raise BuildIdentityError("package must not be empty")
    selected = sorted(set(selection) or {package})
    if package not in selected:
        raise BuildIdentityError(f"package {package} is not in its selection {selected}")
    canonical_root = _canonical(root, strict=True)
    canonical_target = _canonical(target_dir)
    if canonical_target == canonical_root:
        raise BuildIdentityError("target directory must differ from the source root")
    normalized_command = [str(argument) for argument in command]
    normalized_key = command_key if command_key is not None else json.dumps(
        normalized_command, separators=(",", ":")
    )
    resolved_execution_root = _canonical(execution_root if execution_root is not None else root)
    # Computed once and shared: a leading `env NAME=VALUE ...` prefix (e.g.
    # `env CARGO_HOME=<h> cargo ...`) must be visible to both digests, not
    # only to `environment_digest` -- `cargo_config_digest` resolves
    # `$CARGO_HOME` through this same merged mapping, never `os.environ`
    # alone, or a build's own `CARGO_HOME` override would look for its
    # config at the ambient `CARGO_HOME` instead.
    merged_environment = {**os.environ, **_inline_environment(normalized_command)}
    return BuildSpec(
        source=source_identity(canonical_root, (canonical_target,), ignore_paths),
        package=package,
        profile=profile,
        target=target,
        features=features,
        toolchain=toolchain_identity(root),
        target_dir=canonical_target.as_posix(),
        command_key=normalized_key,
        selection=",".join(selected),
        environment_digest=environment_digest(merged_environment),
        cargo_config_digest=cargo_config_digest(
            resolved_execution_root, _config_arguments(normalized_command), merged_environment
        ),
        dependency_digest=dependency_digest,
    )


def _dependency_data(
    manifest: Path,
    packages: Sequence[str],
    target_dir: Path,
    metadata_cwd: Path,
    ignore_paths: Sequence[Path],
    has_explicit_artifacts: bool,
) -> dict[str, dict[str, object]]:
    """Each package's dependency snapshot, by package name.

    One `cargo metadata` and one source identity per path package serve the
    whole set: a package several closures share is read once.
    """
    if has_explicit_artifacts:
        snapshots: dict[str, dict[str, object]] = {
            package: {
                "root": package,
                "packages": [],
                "edges": [],
                "clean_packages": [package],
            }
            for package in packages
        }
    else:
        metadata = _cargo_metadata(manifest, metadata_cwd, no_deps=False)
        source_cache: dict[Path, dict[str, object]] = {}
        package_source_cache = target_dir / ".atlas" / "source-identity" / "package-source"

        def identify_source(path: Path) -> dict[str, object]:
            canonical_path = _canonical(path)
            if canonical_path not in source_cache:
                identified = source_identity(canonical_path, (target_dir,), ignore_paths)
                source_cache[canonical_path] = _content(identified.as_dict())
            return source_cache[canonical_path]

        snapshots = {
            package: dependency_snapshot(
                metadata,
                manifest,
                package,
                identify_source,
                lambda path: cached_package_source_digest(path, package_source_cache),
            )
            for package in packages
        }
    digested = {}
    for package, snapshot in snapshots.items():
        snapshot = dict(snapshot)
        snapshot.pop("digest", None)
        snapshot["digest"] = _sha256_bytes(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()
        )
        digested[package] = snapshot
    return digested
