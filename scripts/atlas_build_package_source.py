"""Content identity of non-path (registry and Git) dependency sources.

Cargo does not fingerprint an unpacked registry or Git checkout, so an edit
there leaves stale artifacts a build would reuse; the dependency snapshot
therefore binds each such package to a digest of its source content. Reading
every file of a large closure costs minutes per pass (kwavers: 437 registry
packages, 24,247 files, 587 MB, 71 s warm), and a run takes the snapshot up
to four times, the last while it holds its closure's exclusive leases. The
digest is therefore memoized under a stat fingerprint of the same file set:
each path, its size and modification time, and each symlink's target. A walk
that stats costs seconds (3.8 s for the same set). An edit that preserves
both size and modification time is not detected, the same bound Cargo's own
fingerprint places on path packages.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from atlas_build_lease import BuildIdentityError
from atlas_build_source import _canonical, _feed_framed, _is_within

_CACHE_VERSION = 1


@dataclass(frozen=True)
class _Entry:
    relative: str
    path: Path
    # (size, modification time) of a regular file; None for a symlink.
    status: tuple[int, int] | None


def _entries(root: Path) -> list[_Entry]:
    """Every file and symlink under `root`, `.git` excluded, sorted by relative path.

    One `scandir` walk: on Windows a `DirEntry` answers `stat` from the
    directory listing, so the walk makes no call per file.
    """
    canonical_root = _canonical(root, strict=True)
    if not canonical_root.is_dir():
        raise BuildIdentityError(f"package source is not a directory: {canonical_root}")
    found: list[_Entry] = []
    pending = [canonical_root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as listing:
                for item in listing:
                    if item.name == ".git":
                        continue
                    path = Path(item.path)
                    relative = path.relative_to(canonical_root).as_posix()
                    if item.is_symlink():
                        found.append(_Entry(relative, path, None))
                    elif item.is_dir(follow_symlinks=False):
                        pending.append(path)
                    elif item.is_file(follow_symlinks=False):
                        status = item.stat(follow_symlinks=False)
                        found.append(
                            _Entry(relative, path, (status.st_size, status.st_mtime_ns))
                        )
        except OSError as error:
            raise BuildIdentityError(f"cannot list package source {directory}: {error}") from error
    return sorted(found, key=lambda entry: entry.relative)


def _symlink_target(path: Path, root: Path) -> str:
    try:
        target = path.readlink().as_posix()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise BuildIdentityError(f"cannot resolve package source symlink {path}: {error}") from error
    if not _is_within(resolved, _canonical(root, strict=True)):
        raise BuildIdentityError(f"package source symlink escapes its package root: {path}")
    return target


def _fingerprint(root: Path, entries: list[_Entry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        _feed_framed(digest, entry.relative.encode("utf-8"))
        if entry.status is None:
            _feed_framed(digest, b"symlink")
            _feed_framed(digest, _symlink_target(entry.path, root).encode("utf-8"))
        else:
            _feed_framed(digest, b"file")
            _feed_framed(digest, "{}:{}".format(*entry.status).encode())
    return digest.hexdigest()


def _content_digest(root: Path, entries: list[_Entry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        if entry.status is None:
            _feed_framed(digest, b"symlink")
            _feed_framed(digest, entry.relative.encode("utf-8"))
            _feed_framed(digest, _symlink_target(entry.path, root).encode("utf-8"))
            continue
        _feed_framed(digest, b"file")
        _feed_framed(digest, entry.relative.encode("utf-8"))
        try:
            _feed_framed(digest, entry.path.read_bytes())
        except OSError as error:
            raise BuildIdentityError(f"cannot read package source {entry.path}: {error}") from error
    return digest.hexdigest()


def package_source_digest(root: Path) -> str:
    """Digest of every file and symlink under `root`, `.git` excluded, read in full."""
    return _content_digest(root, _entries(root))


def _cache_path(cache_dir: Path, root: str) -> Path:
    return cache_dir / f"{hashlib.sha256(root.encode('utf-8')).hexdigest()}.json"


def _cached(path: Path, root: str, fingerprint: str) -> str | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if (
        isinstance(value, dict)
        and value.get("version") == _CACHE_VERSION
        and value.get("root") == root
        and value.get("fingerprint") == fingerprint
        and isinstance(value.get("digest"), str)
    ):
        return value["digest"]
    return None


def _store(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
    except PermissionError:
        # Windows refuses the replace while a concurrent run reads the entry.
        # That run stores the same digest for the same fingerprint, and a
        # missing entry only costs the next run one full read.
        temporary.unlink(missing_ok=True)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise BuildIdentityError(f"cannot write package source cache {path}: {error}") from error


def cached_package_source_digest(root: Path, cache_dir: Path) -> str:
    """`package_source_digest(root)`, read in full only when the stat fingerprint moved.

    An entry is stored only when the fingerprint taken after the read equals
    the one taken before it, so a stored digest always describes the file set
    its fingerprint names.
    """
    canonical = _canonical(root, strict=True).as_posix()
    entries = _entries(root)
    fingerprint = _fingerprint(root, entries)
    path = _cache_path(cache_dir, canonical)
    stored = _cached(path, canonical, fingerprint)
    if stored is not None:
        return stored
    digest = _content_digest(root, entries)
    if _fingerprint(root, _entries(root)) == fingerprint:
        _store(
            path,
            {
                "version": _CACHE_VERSION,
                "root": canonical,
                "fingerprint": fingerprint,
                "digest": digest,
            },
        )
    return digest
