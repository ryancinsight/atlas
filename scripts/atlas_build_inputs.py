"""Compute a build's dimensions and dependency data from its source root and command."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import threading
import tomllib
from typing import Sequence

from atlas_build_lease import BuildIdentityError
from atlas_build_package_identity import package_identities
from atlas_build_package_source import cached_package_source_digest
from atlas_build_records import BuildSpec
from atlas_build_snapshot import _cargo_metadata, dependency_snapshot
from atlas_build_source import (
    _canonical,
    _sha256_bytes,
    cargo_config_digest,
    environment_digest,
    source_identity,
    toolchain_identity,
)


_ENVIRONMENT_LOCK = threading.RLock()
_ENCODED_SEPARATOR = "\x1f"
_FUZZ_CFG = ("--cfg", "fuzzing")


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


def _cargo_fuzz_manifest(manifest: Path) -> bool:
    """Whether the exact manifest declares Cargo's fuzz-package metadata."""
    try:
        document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise BuildIdentityError(f"cannot read fuzz metadata from {manifest}: {error}") from error
    package = document.get("package")
    if package is None:
        return False
    if not isinstance(package, dict):
        raise BuildIdentityError(f"malformed [package] table in {manifest}")
    metadata = package.get("metadata")
    if metadata is None:
        return False
    if not isinstance(metadata, dict):
        raise BuildIdentityError(f"malformed [package.metadata] table in {manifest}")
    value = metadata.get("cargo-fuzz", False)
    if not isinstance(value, bool):
        raise BuildIdentityError(
            f"package.metadata.cargo-fuzz must be a boolean in {manifest}"
        )
    return value


def _has_fuzz_cfg(tokens: Sequence[str]) -> bool:
    return any(
        token == "--cfg=fuzzing"
        or (
            token == _FUZZ_CFG[0]
            and index + 1 < len(tokens)
            and tokens[index + 1] == _FUZZ_CFG[1]
        )
        for index, token in enumerate(tokens)
    )


def _rustflag_tokens(value: object, source: str) -> list[str]:
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list) and all(isinstance(token, str) for token in value):
        return list(value)
    raise BuildIdentityError(f"{source} must be a string or a list of strings")


def _configured_rustflags(
    execution_root: Path,
    command: Sequence[str],
    environment: Mapping[str, str],
) -> list[str]:
    """Resolve non-target Cargo rustflags without replacing configured tokens."""
    targeted = sorted(
        key
        for key in environment
        if (key.startswith("CARGO_TARGET_") or key.startswith("CARGO_HOST_"))
        and key.endswith("_RUSTFLAGS")
    )
    if targeted:
        raise BuildIdentityError(
            "cannot resolve target-qualified rustflags while adding cfg(fuzzing): "
            + ", ".join(targeted)
        )
    cargo = environment.get("CARGO", "cargo")
    query_environment = dict(environment)
    query_environment["RUSTC_BOOTSTRAP"] = "1"
    query = [cargo]
    for argument in _config_arguments(command):
        query.extend(("--config", argument))
    query.extend(("-Z", "unstable-options", "config", "get", "--format=json"))
    try:
        result = subprocess.run(
            query,
            cwd=execution_root,
            env=query_environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise BuildIdentityError(f"cannot resolve Cargo rustflags: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BuildIdentityError(f"cannot resolve Cargo rustflags: {detail}")
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise BuildIdentityError(f"Cargo config returned malformed JSON: {error}") from error
    if not isinstance(document, dict):
        raise BuildIdentityError("Cargo config did not return a table")
    for table_name in ("target", "host"):
        table = document.get(table_name, {})
        if not isinstance(table, dict):
            raise BuildIdentityError(f"Cargo config {table_name} must be a table")
        qualified = [
            name
            for name, value in table.items()
            if isinstance(value, dict) and "rustflags" in value
        ]
        if qualified:
            raise BuildIdentityError(
                f"cannot resolve {table_name}-qualified rustflags while adding cfg(fuzzing): "
                + ", ".join(sorted(qualified))
            )
    build = document.get("build", {})
    if not isinstance(build, dict):
        raise BuildIdentityError("Cargo config build must be a table")
    value = build.get("rustflags")
    return [] if value is None else _rustflag_tokens(value, "Cargo build.rustflags")


def effective_compiler_command(
    command: Sequence[str], environment: Mapping[str, str]
) -> tuple[str, ...]:
    """Carry normalized inline compiler assignments into actual execution."""
    normalized = [str(argument) for argument in command]
    if not normalized or normalized[0] != "env":
        return tuple(normalized)
    for index in range(1, len(normalized)):
        assignment = normalized[index]
        if "=" not in assignment or assignment.startswith("-"):
            break
        name, _, _value = assignment.partition("=")
        if name in {
            "CARGO_BUILD_RUSTFLAGS",
            "CARGO_ENCODED_RUSTFLAGS",
            "RUSTFLAGS",
        } and name in environment:
            normalized[index] = f"{name}={environment[name]}"
    return tuple(normalized)


def effective_compiler_environment(
    manifest: Path | None,
    execution_root: Path,
    command: Sequence[str] = (),
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the compiler environment shared by discovery and execution.

    A cargo-fuzz manifest requires `cfg(fuzzing)`. The effective flag is
    installed before any Cargo metadata or compiler-identity probe, and is
    appended at Cargo's highest-precedence representation so existing
    encoded, environment, or Cargo-config flags remain effective.
    """
    effective = dict(os.environ if environment is None else environment)
    effective.update(_inline_environment(command))
    if manifest is None or not _cargo_fuzz_manifest(_canonical(manifest, strict=True)):
        return effective
    encoded = effective.get("CARGO_ENCODED_RUSTFLAGS")
    if encoded is not None:
        tokens = encoded.split(_ENCODED_SEPARATOR) if encoded else []
        if not _has_fuzz_cfg(tokens):
            effective["CARGO_ENCODED_RUSTFLAGS"] = _ENCODED_SEPARATOR.join([*tokens, *_FUZZ_CFG])
        return effective
    rustflags = effective.get("RUSTFLAGS")
    if rustflags is not None:
        if not _has_fuzz_cfg(rustflags.split()):
            effective["RUSTFLAGS"] = f"{rustflags} {' '.join(_FUZZ_CFG)}".strip()
        return effective
    tokens = _configured_rustflags(execution_root, command, effective)
    configured = effective.get("CARGO_BUILD_RUSTFLAGS")
    if configured is not None:
        if not _has_fuzz_cfg(configured.split()):
            effective["CARGO_BUILD_RUSTFLAGS"] = (
                f"{configured} {' '.join(_FUZZ_CFG)}".strip()
            )
        return effective
    if not _has_fuzz_cfg(tokens):
        tokens.extend(_FUZZ_CFG)
    effective["CARGO_ENCODED_RUSTFLAGS"] = _ENCODED_SEPARATOR.join(tokens)
    return effective


@contextmanager
def compiler_environment(environment: Mapping[str, str]) -> Iterator[None]:
    """Install one effective environment for inherited Cargo subprocesses."""
    with _ENVIRONMENT_LOCK:
        previous = dict(os.environ)
        os.environ.clear()
        os.environ.update(environment)
        try:
            yield
        finally:
            os.environ.clear()
            os.environ.update(previous)


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
        toolchain=toolchain_identity(
            resolved_execution_root,
            merged_environment,
            _config_arguments(normalized_command),
            normalized_command,
        ),
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

    One `cargo metadata`, one `package_identities`, and one external
    package digest serve the whole set: a package several closures share is
    read once. Every path package in the metadata is identified, not only
    the closures', so a nested package's files never fall to the package
    around it.
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
        package_source_cache = target_dir / ".atlas" / "source-identity" / "package-source"
        package_digests: dict[Path, str] = {}
        try:
            # A metadata package whose directory this export does not
            # materialize is identified by nothing; a closure that names it
            # still refuses at `identify_source`.
            directories = [
                parent
                for value in metadata["packages"]
                if isinstance(value, dict) and value.get("source") is None
                for parent in (Path(str(value["manifest_path"])).parent,)
                if parent.is_dir()
            ]
        except (KeyError, TypeError) as error:
            raise BuildIdentityError(f"malformed cargo metadata for {manifest}") from error
        identities = package_identities(directories, (target_dir,), ignore_paths)

        def identify_source(path: Path) -> dict[str, object]:
            try:
                return identities[_canonical(path)]
            except KeyError as error:
                raise BuildIdentityError(f"no path package is identified at {path}") from error

        def digest_package_source(path: Path) -> str:
            canonical = _canonical(path, strict=True)
            if canonical not in package_digests:
                package_digests[canonical] = cached_package_source_digest(
                    canonical, package_source_cache
                )
            return package_digests[canonical]

        snapshots = {
            package: dependency_snapshot(
                metadata,
                manifest,
                package,
                identify_source,
                digest_package_source,
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
