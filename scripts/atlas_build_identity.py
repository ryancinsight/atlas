"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from atlas_build_artifacts import artifact_identity, discover_artifacts
from atlas_build_lease import BuildIdentityError, OwnerLease, lease_is_held

VERSION = 2
DEFAULT_LEASE_SECONDS = 900


IdentityError = BuildIdentityError


@dataclass(frozen=True)
class SourceIdentity:
    root: str
    revision: str
    tree_digest: str
    dirty: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "revision": self.revision,
            "tree_digest": self.tree_digest,
            "dirty": self.dirty,
        }


@dataclass(frozen=True)
class BuildSpec:
    source: SourceIdentity
    package: str
    profile: str
    target: str
    features: str
    toolchain: str
    target_dir: str
    command_key: str
    command_cwd: str

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source.as_dict(),
            "package": self.package,
            "profile": self.profile,
            "target": self.target,
            "features": self.features,
            "toolchain": self.toolchain,
            "target_dir": self.target_dir,
            "command_key": self.command_key,
            "command_cwd": self.command_cwd,
        }


@dataclass(frozen=True)
class BuildResult:
    status: str
    record_path: Path
    cleaned: bool
    artifact_files: tuple[Path, ...]


def _git(root: Path, *arguments: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise IdentityError(f"cannot run git in {root}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise IdentityError(f"git {' '.join(arguments)} failed in {root}: {detail}")
    return result.stdout


def _cargo_command() -> tuple[str, ...]:
    configured = os.environ.get("CARGO")
    return (configured,) if configured else ("cargo",)


def _resolve_command(command: Sequence[str]) -> list[str]:
    cargo = _cargo_command()
    resolved: list[str] = []
    for argument in command:
        if argument == "cargo":
            resolved.extend(cargo)
        else:
            resolved.append(str(argument))
    return resolved


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _feed_framed(digest: "hashlib._Hash", data: bytes) -> None:
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)


def _canonical(path: Path, *, strict: bool = False) -> Path:
    try:
        return path.resolve(strict=strict)
    except OSError as error:
        raise IdentityError(f"cannot resolve {path}: {error}") from error


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def source_identity(root: Path, excluded_roots: Sequence[Path] = ()) -> SourceIdentity:
    root = _canonical(root, strict=True)
    top = Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel").strip())).resolve()
    revision = os.fsdecode(_git(top, "rev-parse", "HEAD").strip())
    excluded = tuple(_canonical(path) for path in excluded_roots)
    diff = _git(top, "diff", "--binary", "HEAD", "--")
    untracked = _git(top, "ls-files", "--others", "--exclude-standard", "-z")
    untracked_entries: list[tuple[bytes, Path]] = []
    for raw_path in untracked.split(b"\0"):
        if not raw_path:
            continue
        path = (top / Path(os.fsdecode(raw_path))).resolve()
        if any(_is_within(path, excluded_root) for excluded_root in excluded):
            continue
        untracked_entries.append((raw_path, path))
    if not diff and not untracked_entries:
        return SourceIdentity(
            root=top.as_posix(),
            revision=revision,
            tree_digest=_sha256_bytes(revision.encode()),
            dirty=False,
        )

    digest = hashlib.sha256()
    _feed_framed(digest, diff)
    for raw_path, path in untracked_entries:
        _feed_framed(digest, raw_path)
        try:
            _feed_framed(digest, path.read_bytes())
        except OSError as error:
            raise IdentityError(f"cannot read untracked source {path}: {error}") from error
    return SourceIdentity(
        root=top.as_posix(),
        revision=revision,
        tree_digest=digest.hexdigest(),
        dirty=True,
    )


def toolchain_identity(root: Path) -> str:
    try:
        result = subprocess.run(
            [os.environ.get("RUSTC", "rustc"), "--version", "--verbose"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise IdentityError(f"cannot run rustc: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise IdentityError(f"rustc --version --verbose failed: {detail}")
    return " ".join(result.stdout.split())


def build_spec(
    root: Path,
    package: str,
    target_dir: Path,
    profile: str,
    target: str,
    features: str,
    command: Sequence[str] = (),
    command_cwd: Path | None = None,
    command_key: str | None = None,
) -> BuildSpec:
    if not package:
        raise IdentityError("package must not be empty")
    canonical_root = _canonical(root, strict=True)
    canonical_target = _canonical(target_dir)
    if canonical_target == canonical_root:
        raise IdentityError("target directory must differ from the source root")
    execution_root = _canonical(command_cwd or canonical_root, strict=True)
    normalized_command = [str(argument) for argument in command]
    normalized_key = command_key if command_key is not None else json.dumps(
        normalized_command, separators=(",", ":")
    )
    return BuildSpec(
        source=source_identity(canonical_root, (canonical_target,)),
        package=package,
        profile=profile,
        target=target,
        features=features,
        toolchain=toolchain_identity(root),
        target_dir=canonical_target.as_posix(),
        command_key=normalized_key,
        command_cwd=execution_root.as_posix(),
    )


def _spec_key(spec: BuildSpec) -> str:
    scope = spec.as_dict()
    scope.pop("source")
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(encoded)


def _lease_key(spec: BuildSpec) -> str:
    scope = {"package": spec.package, "target_dir": spec.target_dir}
    return _sha256_bytes(json.dumps(scope, sort_keys=True, separators=(",", ":")).encode())


def record_path(spec: BuildSpec) -> Path:
    return Path(spec.target_dir) / ".atlas" / "source-identity" / f"{_spec_key(spec)}.json"


def lease_path(spec: BuildSpec) -> Path:
    return Path(spec.target_dir) / ".atlas" / "source-identity" / f"{_lease_key(spec)}.lock"


def read_record(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdentityError(f"malformed source identity record {path}: {error}") from error
    if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != VERSION:
        raise IdentityError(f"unsupported source identity record: {path}")
    source = value.get("source")
    build = value.get("build")
    artifact = value.get("artifact")
    if not isinstance(source, dict) or not isinstance(build, dict) or not isinstance(artifact, dict):
        raise IdentityError(f"malformed source identity record: {path}")
    if any(type(source.get(key)) is not str for key in ("root", "revision", "tree_digest")):
        raise IdentityError(f"malformed source identity record: {path}")
    if type(source.get("dirty")) is not bool:
        raise IdentityError(f"malformed source identity record: {path}")
    if any(
        type(build.get(key)) is not str
        for key in (
            "package",
            "profile",
            "target",
            "features",
            "toolchain",
            "target_dir",
            "command_key",
            "command_cwd",
        )
    ):
        raise IdentityError(f"malformed source identity record: {path}")
    files = artifact.get("files")
    if type(files) is not dict or any(type(key) is not str or type(value) is not str for key, value in files.items()):
        raise IdentityError(f"malformed source identity record: {path}")
    if type(artifact.get("digest")) is not str:
        raise IdentityError(f"malformed source identity record: {path}")
    return value


def _write_atomic(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(value, sort_keys=True, indent=2) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as cleanup_error:
            raise IdentityError(
                f"cannot write source identity record {path}: {error}; cleanup failed: {cleanup_error}"
            ) from error
        raise IdentityError(f"cannot write source identity record {path}: {error}") from error


def _run_checked(command: Sequence[str], root: Path, environment: dict[str, str]) -> None:
    try:
        result = subprocess.run(_resolve_command(command), cwd=root, env=environment, check=False)
    except OSError as error:
        raise IdentityError(f"cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise IdentityError(f"command failed with exit code {result.returncode}: {' '.join(command)}")


def run_build(
    root: Path,
    manifest: Path,
    package: str,
    target_dir: Path,
    command: Sequence[str],
    profile: str = "debug",
    target: str = "host",
    features: str = "",
    artifact_paths: Sequence[Path] = (),
    clean_command: Sequence[str] | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    command_cwd: Path | None = None,
    command_key: str | None = None,
) -> BuildResult:
    if not command:
        raise IdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    target_dir = _canonical(target_dir)
    execution_root = _canonical(command_cwd or root, strict=True)
    spec = build_spec(
        root,
        package,
        target_dir,
        profile,
        target,
        features,
        command,
        execution_root,
        command_key,
    )
    record = record_path(spec)
    lock = lease_path(spec)
    owner = {
        "root": spec.source.root,
        "revision": spec.source.revision,
        "package": package,
        "target_dir": target_dir.as_posix(),
    }
    environment = dict(os.environ)
    environment["CARGO_TARGET_DIR"] = target_dir.as_posix()
    cleaned = False
    with OwnerLease(lock, owner, lease_seconds):
        existing = read_record(record)
        artifact_paths = tuple(_canonical(path) for path in artifact_paths)
        stale = existing is None
        if existing is not None:
            try:
                current_artifact = artifact_identity(
                    root,
                    target_dir,
                    package,
                    profile,
                    artifact_paths,
                    target,
                    manifest,
                    execution_root,
                )
            except IdentityError:
                stale = True
            else:
                stale = (
                    existing.get("source") != spec.source.as_dict()
                    or existing.get("build") != spec.as_dict()
                    or existing.get("artifact") != current_artifact
                )
        if stale:
            clean = list(clean_command) if clean_command is not None else [
                *_cargo_command(), "clean", "-p", package, "--manifest-path", str(manifest)
            ]
            _run_checked(clean, execution_root, environment)
            cleaned = True
        _run_checked(command, execution_root, environment)
        final_source = source_identity(root, (target_dir,))
        if final_source.as_dict() != spec.source.as_dict():
            raise IdentityError("source tree changed while the build was running")
        paths = artifact_paths or discover_artifacts(
            target_dir, package, profile, target, manifest, execution_root
        )
        artifact = artifact_identity(
            root, target_dir, package, profile, paths, target, manifest, execution_root
        )
        _write_atomic(
            record,
            {
                "version": VERSION,
                "source": spec.source.as_dict(),
                "build": spec.as_dict(),
                "artifact": artifact,
            },
        )
    return BuildResult("rebuilt" if cleaned else "reused", record, cleaned, tuple(paths))


def check_record(
    root: Path,
    package: str,
    target_dir: Path,
    profile: str = "debug",
    target: str = "host",
    features: str = "",
    artifact_paths: Sequence[Path] = (),
    manifest: Path | None = None,
    command: Sequence[str] = (),
    command_cwd: Path | None = None,
    command_key: str | None = None,
) -> tuple[int, dict[str, object]]:
    spec = build_spec(
        root,
        package,
        target_dir,
        profile,
        target,
        features,
        command,
        command_cwd,
        command_key,
    )
    record_file = record_path(spec)
    if lease_is_held(lease_path(spec)):
        return 3, {"status": "owned", "record": record_file.as_posix()}
    existing = read_record(record_file)
    if existing is None:
        return 2, {"status": "missing", "record": record_file.as_posix()}
    current = artifact_identity(
        root,
        target_dir,
        package,
        profile,
        artifact_paths,
        target,
        manifest,
        command_cwd,
    )
    matches = (
        existing.get("source") == spec.source.as_dict()
        and existing.get("build") == spec.as_dict()
        and existing.get("artifact") == current
    )
    return (0 if matches else 2), {
        "status": "match" if matches else "stale",
        "record": record_file.as_posix(),
    }
