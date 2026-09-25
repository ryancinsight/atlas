"""Identify source trees, ignored inputs, and build environments."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from atlas_build_lease import BuildIdentityError


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
        raise BuildIdentityError(f"cannot run git in {root}: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BuildIdentityError(f"git {' '.join(arguments)} failed in {root}: {detail}")
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
        raise BuildIdentityError(f"cannot resolve {path}: {error}") from error


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _ignored_source_path(path: Path, top: Path) -> bool:
    try:
        parts = path.relative_to(top).parts[:-1]
    except ValueError:
        return True
    return any(
        part
        in {
            ".git",
            "target",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }
        for part in parts
    )


def _diff_bytes(top: Path, ignored: Sequence[Path]) -> bytes:
    arguments = ["diff", "--binary", "HEAD", "--", "."]
    for path in ignored:
        try:
            relative = path.relative_to(top).as_posix()
        except ValueError as error:
            raise BuildIdentityError(
                f"ignored source path is outside the repository: {path}"
            ) from error
        arguments.append(f":(exclude){relative}")
    return _git(top, *arguments)


def source_identity(
    root: Path,
    excluded_roots: Sequence[Path] = (),
    ignored_paths: Sequence[Path] = (),
) -> SourceIdentity:
    root = _canonical(root, strict=True)
    top = Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel").strip())).resolve()
    revision = os.fsdecode(_git(top, "rev-parse", "HEAD").strip())
    excluded = tuple(_canonical(path) for path in excluded_roots)
    ignored = tuple(_canonical(path) for path in ignored_paths)
    diff = _diff_bytes(top, ignored)
    untracked_entries: list[tuple[bytes, bytes, Path]] = []
    for marker, arguments in (
        (b"untracked", ("ls-files", "--others", "--exclude-standard", "-z")),
        (b"ignored", ("ls-files", "--others", "--ignored", "--exclude-standard", "-z")),
    ):
        for raw_path in _git(top, *arguments).split(b"\0"):
            if not raw_path:
                continue
            path = (top / Path(os.fsdecode(raw_path))).resolve()
            if any(_is_within(path, excluded_root) for excluded_root in excluded):
                continue
            if any(_is_within(path, ignored_path) for ignored_path in ignored):
                continue
            if _ignored_source_path(path, top):
                continue
            untracked_entries.append((marker, raw_path, path))
    if not diff and not untracked_entries:
        return SourceIdentity(
            root=top.as_posix(),
            revision=revision,
            tree_digest=_sha256_bytes(revision.encode()),
            dirty=False,
        )

    digest = hashlib.sha256()
    _feed_framed(digest, diff)
    for marker, raw_path, path in untracked_entries:
        _feed_framed(digest, marker)
        _feed_framed(digest, raw_path)
        try:
            _feed_framed(digest, path.read_bytes())
        except OSError as error:
            raise BuildIdentityError(f"cannot read untracked source {path}: {error}") from error
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
        raise BuildIdentityError(f"cannot run rustc: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()
        raise BuildIdentityError(f"rustc --version --verbose failed: {detail}")
    return " ".join(result.stdout.split())


def environment_digest(environment: Mapping[str, str] | None = None) -> str:
    source = os.environ if environment is None else environment
    keys = {
        key
        for key in source
        if key.startswith("CARGO_PROFILE_")
        or key
        in {
            "CARGO",
            "CARGO_BUILD_TARGET",
            "CARGO_ENCODED_RUSTFLAGS",
            "CARGO_INCREMENTAL",
            "RUSTC",
            "RUSTC_WORKSPACE_WRAPPER",
            "RUSTC_WRAPPER",
            "RUSTDOCFLAGS",
            "RUSTFLAGS",
        }
    }
    values = {key: _sha256_bytes(str(source[key]).encode()) for key in sorted(keys)}
    return _sha256_bytes(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    )
