"""Identify each path package by its own files, never its whole repository."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable, Sequence

from atlas_build_lease import BuildIdentityError
from atlas_build_source import (
    _canonical,
    _feed_framed,
    _git,
    _ignored_source_path,
    _is_within,
)


def repository_top(path: Path) -> Path:
    """The working tree holding `path`: its nearest ancestor with a `.git` entry.

    A file system walk, not `git rev-parse` per directory: a stack closure
    names a hundred path packages, and each of the run's several snapshot
    reads would otherwise start that many processes.
    """
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    raise BuildIdentityError(f"{path} is in no Git repository")


def _owner(path: str, packages: dict[str, Path]) -> str | None:
    """The deepest package directory, relative to the top, containing `path`."""
    directory = path
    while directory:
        directory = directory.rpartition("/")[0]
        if directory in packages:
            return directory
    return None


def _within_package(path: str, package: str) -> str:
    return path[len(package) + 1 :] if package else path


def _repository_identities(
    top: Path,
    packages: dict[str, Path],
    excluded: Sequence[Path],
    ignored: Sequence[Path],
) -> dict[Path, dict[str, str]]:
    files = {package: hashlib.sha256() for package in packages}
    for entry in _git(top, "ls-tree", "-r", "-z", "--full-tree", "HEAD").split(b"\0"):
        if not entry:
            continue
        meta, _, raw_path = entry.partition(b"\t")
        mode, _, rest = meta.partition(b" ")
        object_id = rest.rpartition(b" ")[2]
        path = raw_path.decode("utf-8", "surrogateescape")
        package = _owner(path, packages)
        if package is None:
            continue
        name = _within_package(path, package).encode("utf-8", "surrogateescape")
        for part in (name, mode, object_id):
            _feed_framed(files[package], part)

    dirty: dict[str, list[tuple[bytes, ...]]] = {package: [] for package in packages}
    arguments = ["diff", "--raw", "-z", "--no-renames", "HEAD", "--", "."]
    # An ignored path names one repository's file (the export's lock); the
    # root's `source_identity` rejects one outside the root repository.
    ignored = tuple(path for path in ignored if _is_within(path, top))
    arguments += [f":(exclude){path.relative_to(top).as_posix()}" for path in ignored]
    tokens = _git(top, *arguments).split(b"\0")
    changed = [
        (tokens[index], tokens[index + 1].decode("utf-8", "surrogateescape"))
        for index in range(0, len(tokens) - 1, 2)
        if tokens[index].startswith(b":")
    ]
    others: list[tuple[bytes, str]] = []
    for marker, listing in (
        (b"untracked", ("ls-files", "--others", "--exclude-standard", "-z")),
        (b"ignored", ("ls-files", "--others", "--ignored", "--exclude-standard", "-z")),
    ):
        for raw_path in _git(top, *listing).split(b"\0"):
            if raw_path:
                others.append((marker, raw_path.decode("utf-8", "surrogateescape")))
    for marker, path in (*changed, *others):
        package = _owner(path, packages)
        if package is None:
            continue
        absolute = top / path
        if not marker.startswith(b":"):
            resolved = absolute.resolve()
            if (
                any(_is_within(resolved, root) for root in excluded)
                or any(_is_within(resolved, root) for root in ignored)
                or _ignored_source_path(resolved, top)
            ):
                continue
        name = _within_package(path, package).encode("utf-8", "surrogateescape")
        if absolute.is_file():
            try:
                content = absolute.read_bytes()
            except OSError as error:
                raise BuildIdentityError(
                    f"cannot read changed source {absolute}: {error}"
                ) from error
        else:
            # Deleted, or a directory (a gitlink): the diff line's own modes
            # and object IDs say what changed.
            content = b"absent"
        dirty[package].append((marker, name, content))

    identities = {}
    for package, directory in packages.items():
        digest = hashlib.sha256()
        for entry in sorted(dirty[package]):
            for part in entry:
                _feed_framed(digest, part)
        identities[directory] = {
            "files": files[package].hexdigest(),
            "dirty": digest.hexdigest() if dirty[package] else "",
        }
    return identities


def package_identities(
    directories: Iterable[Path],
    excluded_roots: Sequence[Path] = (),
    ignored_paths: Sequence[Path] = (),
) -> dict[Path, dict[str, str]]:
    """Each path package directory's identity, keyed by its canonical path.

    Each tracked file belongs to the deepest package directory containing
    it, so a root package at the repository top does not take its members'
    files. `files` digests the package's `HEAD` entries (path within the
    package, mode, object ID) and `dirty` its share of the working tree's
    changes against `HEAD` and of its untracked and ignored files, by their
    bytes, excluding what `source_identity` excludes. Neither holds a
    revision, so a commit that edits one member leaves every other
    member's identity where it was. One `ls-tree`, one `diff` and two
    `ls-files` serve every package of a repository.
    """
    excluded = tuple(_canonical(path) for path in excluded_roots)
    ignored = tuple(_canonical(path) for path in ignored_paths)
    by_top: dict[Path, dict[str, Path]] = {}
    for directory in {_canonical(path, strict=True) for path in directories}:
        top = repository_top(directory)
        relative = os.path.relpath(directory, top).replace(os.sep, "/")
        by_top.setdefault(top, {})["" if relative == "." else relative] = directory
    identities: dict[Path, dict[str, str]] = {}
    for top, packages in by_top.items():
        identities.update(_repository_identities(top, packages, excluded, ignored))
    return identities
