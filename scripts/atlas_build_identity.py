"""Bind shared Cargo artifacts to their source tree and build dimensions."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

VERSION = 1
DEFAULT_LEASE_SECONDS = 900
ARTIFACT_SUFFIXES = frozenset({".a", ".dll", ".dylib", ".lib", ".rlib", ".rmeta", ".so"})


class IdentityError(RuntimeError):
    """A source identity cannot be established or safely used."""


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
    command_key: str = ""

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


def _canonical(path: Path, *, strict: bool = False) -> Path:
    try:
        return path.resolve(strict=strict)
    except OSError as error:
        raise IdentityError(f"cannot resolve {path}: {error}") from error


def _exclusions(top: Path, ignore_paths: Sequence[Path]) -> list[str]:
    """Pathspecs that leave `ignore_paths` out of every source query.

    A gate that rewrites a file and restores it afterwards (the pre-push
    gate does this to `Cargo.lock`) must not turn its own transient edit into
    a new source identity, or each of its steps would clean the previous
    step's artifacts.
    """
    pathspecs = ["--", "."]
    for path in ignore_paths:
        resolved = _canonical(path if path.is_absolute() else top / path)
        try:
            relative = resolved.relative_to(top).as_posix()
        except ValueError as error:
            raise IdentityError(f"ignored path is outside the source tree: {resolved}") from error
        pathspecs.append(f":(exclude,literal){relative}")
    return pathspecs


def source_identity(root: Path, ignore_paths: Sequence[Path] = ()) -> SourceIdentity:
    root = _canonical(root, strict=True)
    top = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    revision = _git(top, "rev-parse", "HEAD").decode().strip()
    pathspecs = _exclusions(top, ignore_paths)
    status = _git(top, "status", "--porcelain=v1", "-z", "--untracked-files=all", *pathspecs)
    if not status:
        return SourceIdentity(
            root=top.as_posix(),
            revision=revision,
            tree_digest=_sha256_bytes(revision.encode()),
            dirty=False,
        )

    digest = hashlib.sha256()
    digest.update(_git(top, "diff", "--binary", "HEAD", *pathspecs))
    untracked = _git(top, "ls-files", "--others", "--exclude-standard", "-z", *pathspecs)
    for raw_path in untracked.split(b"\0"):
        if not raw_path:
            continue
        path = top / Path(raw_path.decode("utf-8"))
        digest.update(raw_path)
        try:
            digest.update(path.read_bytes())
        except OSError as error:
            raise IdentityError(f"cannot read untracked source {path}: {error}") from error
    return SourceIdentity(
        root=top.as_posix(),
        revision=revision,
        tree_digest=digest.hexdigest(),
        dirty=True,
    )


def toolchain_identity() -> str:
    try:
        result = subprocess.run(
            ["rustc", "--version", "--verbose"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
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
    command_key: str = "",
    ignore_paths: Sequence[Path] = (),
) -> BuildSpec:
    if not package:
        raise IdentityError("package must not be empty")
    return BuildSpec(
        source=source_identity(root, ignore_paths),
        package=package,
        profile=profile,
        target=target,
        features=features,
        toolchain=toolchain_identity(),
        target_dir=_canonical(target_dir).as_posix(),
        command_key=command_key,
    )


def _spec_key(spec: BuildSpec) -> str:
    scope = spec.as_dict()
    scope.pop("source")
    encoded = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    return _sha256_bytes(encoded)


def record_path(spec: BuildSpec) -> Path:
    return Path(spec.target_dir) / ".atlas" / "source-identity" / f"{_spec_key(spec)}.json"


def lease_path(spec: BuildSpec) -> Path:
    return record_path(spec).with_suffix(".lock")


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
    root: Path, target_dir: Path, package: str, profile: str, paths: Sequence[Path]
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
        deps = target_dir / profile / "deps"
        if deps.is_dir():
            for path in deps.iterdir():
                if path.is_file() and (
                    path.name.startswith(f"{package}-")
                    or path.name.startswith(f"lib{package}-")
                ) and path.suffix in ARTIFACT_SUFFIXES:
                    selected.add(path.resolve())
        fingerprints = target_dir / ".fingerprint"
        if fingerprints.is_dir():
            for directory in fingerprints.iterdir():
                if directory.is_dir() and directory.name.startswith(f"{package}-"):
                    selected.update(path.resolve() for path in directory.rglob("*") if path.is_file())

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


def _sibling_matches(spec: BuildSpec) -> bool:
    """Whether another command's record already built this exact source.

    Records differ only by `command_key` when one gate runs several commands
    over a package. A missing record for the next command is then no evidence
    of a foreign source, so it must not clean what the previous command built.
    """
    build = spec.as_dict()
    build.pop("command_key")
    directory = record_path(spec).parent
    if not directory.is_dir():
        return False
    for candidate in directory.glob("*.json"):
        try:
            record = read_record(candidate)
        except IdentityError:
            continue
        if record is None:
            continue
        other = record.get("build")
        if not isinstance(other, dict):
            continue
        other = dict(other)
        other.pop("command_key", None)
        if other == build and record.get("source") == spec.source.as_dict():
            return True
    return False


def read_record(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdentityError(f"malformed source identity record {path}: {error}") from error
    if not isinstance(value, dict) or value.get("version") != VERSION:
        raise IdentityError(f"unsupported source identity record: {path}")
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


class OwnerLease:
    def __init__(self, path: Path, owner: dict[str, object], seconds: int) -> None:
        if seconds <= 0:
            raise IdentityError("lease duration must be positive")
        self.path = path
        self.owner = owner
        self.seconds = seconds
        self.held = False

    def __enter__(self) -> OwnerLease:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        token = uuid.uuid4().hex
        payload = {
            **self.owner,
            "token": token,
            "expires_ns": time.time_ns() + self.seconds * 1_000_000_000,
        }
        self.owner = {**self.owner, "token": token}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        for _ in range(2):
            try:
                descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                    expires = int(existing.get("expires_ns", 0))
                except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
                    raise IdentityError(f"malformed source identity lease {self.path}") from error
                if expires > time.time_ns():
                    owner = existing.get("root", "unknown")
                    revision = existing.get("revision", "unknown")
                    raise IdentityError(
                        f"source identity is owned by {owner} at {revision}; retry after it releases"
                    )
                try:
                    self.path.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
            self.held = True
            return self
        raise IdentityError(f"could not acquire source identity lease {self.path}")

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if not self.held:
            return
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
            if current.get("token") == self.owner.get("token"):
                self.path.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError, AttributeError) as error:
            raise IdentityError(f"cannot release source identity lease {self.path}") from error


def _run_checked(command: Sequence[str], cwd: Path, environment: dict[str, str]) -> None:
    try:
        result = subprocess.run(list(command), cwd=cwd, env=environment, check=False)
    except OSError as error:
        raise IdentityError(f"cannot run {command[0]}: {error}") from error
    if result.returncode != 0:
        raise IdentityError(f"command failed with exit code {result.returncode}: {' '.join(command)}")


def discover_artifacts(target_dir: Path, package: str, profile: str) -> tuple[Path, ...]:
    target_dir = _canonical(target_dir)
    selected: set[Path] = set()
    deps = target_dir / profile / "deps"
    if deps.is_dir():
        for path in deps.iterdir():
            if path.is_file() and (
                path.name.startswith(f"{package}-")
                or path.name.startswith(f"lib{package}-")
            ) and path.suffix in ARTIFACT_SUFFIXES:
                selected.add(path.resolve())
    fingerprints = target_dir / ".fingerprint"
    if fingerprints.is_dir():
        for directory in fingerprints.iterdir():
            if directory.is_dir() and directory.name.startswith(f"{package}-"):
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
    command_cwd: Path | None = None,
    command_key: str = "",
    ignore_paths: Sequence[Path] = (),
) -> BuildResult:
    """Run `command` against artifacts recorded for this exact source.

    `command_cwd` is where the clean and build commands run (the source root
    by default). `command_key` separates records for different commands over
    one package -- clippy, tests and rustdoc leave different artifacts, so a
    shared record would make each step see the previous one as stale.
    """
    if not command:
        raise IdentityError("a build command is required")
    root = _canonical(root, strict=True)
    manifest = _canonical(manifest, strict=True)
    target_dir = _canonical(target_dir)
    cwd = _canonical(command_cwd, strict=True) if command_cwd is not None else root
    spec = build_spec(
        root, package, target_dir, profile, target, features, command_key, ignore_paths
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
        stale = existing is None and not _sibling_matches(spec)
        if existing is not None:
            try:
                current_artifact = artifact_identity(root, target_dir, package, profile, artifact_paths)
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
            _run_checked(clean, cwd, environment)
            cleaned = True
        _run_checked(command, cwd, environment)
        paths = artifact_paths or discover_artifacts(target_dir, package, profile)
        artifact = artifact_identity(root, target_dir, package, profile, paths)
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
    command_key: str = "",
    ignore_paths: Sequence[Path] = (),
) -> tuple[int, dict[str, object]]:
    spec = build_spec(
        root, package, target_dir, profile, target, features, command_key, ignore_paths
    )
    record_file = record_path(spec)
    existing = read_record(record_file)
    if existing is None:
        return 2, {"status": "missing", "record": record_file.as_posix()}
    current = artifact_identity(root, target_dir, package, profile, artifact_paths)
    matches = (
        existing.get("source") == spec.source.as_dict()
        and existing.get("build") == spec.as_dict()
        and existing.get("artifact") == current
    )
    return (0 if matches else 2), {
        "status": "match" if matches else "stale",
        "record": record_file.as_posix(),
    }
