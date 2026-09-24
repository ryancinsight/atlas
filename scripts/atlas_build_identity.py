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

from atlas_build_lease import BuildIdentityError, OwnerLease, lease_is_held

VERSION = 1
DEFAULT_LEASE_SECONDS = 900
ARTIFACT_SUFFIXES = frozenset(
    {".a", ".d", ".dll", ".dylib", ".exe", ".json", ".lib", ".pdb", ".rlib", ".rmeta", ".so"}
)


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
    command: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source.as_dict(),
            "package": self.package,
            "profile": self.profile,
            "target": self.target,
            "features": self.features,
            "toolchain": self.toolchain,
            "target_dir": self.target_dir,
            "command": list(self.command),
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


def source_identity(root: Path) -> SourceIdentity:
    root = _canonical(root, strict=True)
    top = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    revision = _git(top, "rev-parse", "HEAD").decode().strip()
    status = _git(top, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if not status:
        return SourceIdentity(
            root=top.as_posix(),
            revision=revision,
            tree_digest=_sha256_bytes(revision.encode()),
            dirty=False,
        )

    digest = hashlib.sha256()
    _feed_framed(digest, status)
    _feed_framed(digest, _git(top, "diff", "--binary", "HEAD", "--"))
    untracked = _git(top, "ls-files", "--others", "--exclude-standard", "-z")
    for raw_path in untracked.split(b"\0"):
        if not raw_path:
            continue
        path = top / Path(raw_path.decode("utf-8"))
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
            ["rustc", "--version", "--verbose"],
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
) -> BuildSpec:
    if not package:
        raise IdentityError("package must not be empty")
    return BuildSpec(
        source=source_identity(root),
        package=package,
        profile=profile,
        target=target,
        features=features,
        toolchain=toolchain_identity(root),
        target_dir=_canonical(target_dir).as_posix(),
        command=tuple(str(argument) for argument in command),
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


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise IdentityError(f"cannot hash artifact {path}: {error}") from error
    return digest.hexdigest()


def artifact_identity(
    root: Path,
    target_dir: Path,
    package: str,
    profile: str,
    paths: Sequence[Path],
    target: str = "host",
    manifest: Path | None = None,
) -> dict[str, object]:
    _canonical(root, strict=True)
    target_dir = _canonical(target_dir)
    selected: set[Path] = set()
    for path in paths:
        resolved = _canonical(path, strict=True)
        try:
            resolved.relative_to(target_dir)
        except ValueError as error:
            raise IdentityError(f"artifact is outside the shared target: {resolved}") from error
        if not resolved.is_file():
            raise IdentityError(f"artifact does not exist: {resolved}")
        selected.add(resolved)

    if not selected:
        selected.update(discover_artifacts(target_dir, package, profile, target, manifest))

    if not selected:
        raise IdentityError(f"no artifact found for {package} in {target_dir / profile}")
    files = {}
    for path in sorted(selected):
        try:
            relative = path.relative_to(target_dir).as_posix()
        except ValueError as error:
            raise IdentityError(f"artifact is outside the shared target: {path}") from error
        files[relative] = _file_digest(path)
    digest = _sha256_bytes(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())
    return {"files": files, "digest": digest}


def read_record(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdentityError(f"malformed source identity record {path}: {error}") from error
    if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != VERSION:
        raise IdentityError(f"unsupported source identity record: {path}")
    for key in ("source", "build", "artifact"):
        if not isinstance(value.get(key), dict):
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
        result = subprocess.run(list(command), cwd=root, env=environment, check=False)
    except OSError as error:
        raise IdentityError(f"cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise IdentityError(f"command failed with exit code {result.returncode}: {' '.join(command)}")


def _workspace_package_names(manifest: Path) -> frozenset[str]:
    try:
        result = subprocess.run(
            ["cargo", "metadata", "--no-deps", "--format-version", "1", "--manifest-path", str(manifest)],
            cwd=manifest.parent,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise IdentityError(f"cannot read package metadata from {manifest}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise IdentityError(f"cargo metadata failed for {manifest}: {detail}")
    try:
        packages = json.loads(result.stdout)["packages"]
        names = frozenset(str(package["name"]) for package in packages)
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise IdentityError(f"malformed cargo metadata for {manifest}") from error
    if not names:
        raise IdentityError(f"cargo metadata contains no packages for {manifest}")
    return names


def _artifact_owner(filename: str, package_names: frozenset[str], requested: str) -> str | None:
    stem = filename[3:] if filename.startswith("lib") else filename
    stem = stem.split(".", 1)[0]
    matches = [name for name in package_names if stem == name or stem.startswith(f"{name}-")]
    if not matches:
        return requested if stem == requested or stem.startswith(f"{requested}-") else None
    owner = max(matches, key=len)
    return owner if owner == requested else None


def discover_artifacts(
    target_dir: Path,
    package: str,
    profile: str,
    target: str = "host",
    manifest: Path | None = None,
) -> tuple[Path, ...]:
    target_dir = _canonical(target_dir)
    package_names = _workspace_package_names(manifest) if manifest is not None else frozenset({package})
    selected: set[Path] = set()
    dep_dirs = [target_dir / profile / "deps"]
    if target != "host":
        dep_dirs.append(target_dir / target / profile / "deps")
    for deps in dep_dirs:
        if not deps.is_dir():
            continue
        for path in deps.iterdir():
            if path.is_file() and path.suffix in ARTIFACT_SUFFIXES and _artifact_owner(path.name, package_names, package) == package:
                selected.add(path.resolve())
    fingerprints = target_dir / ".fingerprint"
    if fingerprints.is_dir():
        for directory in fingerprints.iterdir():
            if directory.is_dir() and _artifact_owner(directory.name, package_names, package) == package:
                selected.update(path.resolve() for path in directory.rglob("*") if path.is_file())
    return tuple(sorted(selected))


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
) -> BuildResult:
    if not command:
        raise IdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    target_dir = _canonical(target_dir)
    spec = build_spec(root, package, target_dir, profile, target, features, command)
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
                    root, target_dir, package, profile, artifact_paths, target, manifest
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
                "cargo", "clean", "-p", package, "--manifest-path", str(manifest)
            ]
            _run_checked(clean, root, environment)
            cleaned = True
        _run_checked(command, root, environment)
        final_source = source_identity(root)
        if final_source.as_dict() != spec.source.as_dict():
            raise IdentityError("source tree changed while the build was running")
        paths = artifact_paths or discover_artifacts(target_dir, package, profile, target, manifest)
        artifact = artifact_identity(root, target_dir, package, profile, paths, target, manifest)
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
) -> tuple[int, dict[str, object]]:
    spec = build_spec(root, package, target_dir, profile, target, features, command)
    record_file = record_path(spec)
    if lease_is_held(lease_path(spec)):
        return 3, {"status": "owned", "record": record_file.as_posix()}
    existing = read_record(record_file)
    if existing is None:
        return 2, {"status": "missing", "record": record_file.as_posix()}
    current = artifact_identity(root, target_dir, package, profile, artifact_paths, target, manifest)
    matches = (
        existing.get("source") == spec.source.as_dict()
        and existing.get("build") == spec.as_dict()
        and existing.get("artifact") == current
    )
    return (0 if matches else 2), {
        "status": "match" if matches else "stale",
        "record": record_file.as_posix(),
    }
