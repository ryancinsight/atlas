"""Identify source trees, ignored inputs, and build environments."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from atlas_build_lease import BuildIdentityError
from atlas_git_process import GitProcessError, execute_process
import atlas_build_source_git as source_git


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
        parts = path.relative_to(top).parts
    except ValueError:
        return True
    return (bool(parts) and parts[0] == "target") or any(
        part
        in {
            ".git",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }
        for part in parts
    )


def _excluded(path: Path, roots: Sequence[Path]) -> bool:
    return any(_is_within(path, root) for root in roots)


def _file_state(path: Path, object_format: str) -> tuple[int, bytes, bytes, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise BuildIdentityError(f"cannot open source file {path}: {error}") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise BuildIdentityError(f"source entry is not a regular file: {path}")
        git_digest = hashlib.new(object_format)
        git_digest.update(f"blob {before.st_size}\0".encode("ascii"))
        content_digest = hashlib.sha256()
        size = 0
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                git_digest.update(chunk)
                content_digest.update(chunk)
        after = os.fstat(descriptor)
        if (
            size != before.st_size
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise BuildIdentityError(f"source changed while reading {path}")
        executable = stat.S_IMODE(before.st_mode) & 0o111 if os.name != "nt" else 0
        return size, content_digest.digest(), git_digest.hexdigest().encode("ascii"), executable
    finally:
        os.close(descriptor)


def _is_reparse_point(metadata: os.stat_result) -> bool:
    attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(metadata, "st_file_attributes", 0) & attribute)


def _link_target(path: Path, top: Path, excluded: Sequence[Path]) -> bytes:
    try:
        target = path.readlink()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise BuildIdentityError(f"cannot resolve source link {path}: {error}") from error
    if not _is_within(resolved, top):
        raise BuildIdentityError(f"source link escapes the identified tree: {path}")
    relative = resolved.relative_to(top)
    if (
        ".git" in relative.parts
        or _ignored_source_path(resolved, top)
        or _excluded(resolved, excluded)
    ):
        raise BuildIdentityError(f"source link targets excluded content: {path}")
    return os.fsencode(target)


def _blob_object_id(content: bytes, object_format: str) -> bytes:
    digest = hashlib.new(object_format)
    digest.update(f"blob {len(content)}\0".encode("ascii"))
    digest.update(content)
    return digest.hexdigest().encode("ascii")


def _checkout_manifest(
    top: Path,
    excluded: Sequence[Path],
    ignored: Sequence[Path],
    gitlinks: set[bytes],
    object_format: str,
    expected: dict[bytes, tuple[bytes, bytes]],
) -> tuple[list[tuple[bytes, bytes, bytes, bytes, int]], set[bytes], set[bytes]]:
    files: list[tuple[bytes, bytes, bytes, bytes, int]] = []
    empty_directories: set[bytes] = set()
    present_files: set[bytes] = set()
    stack = [top]
    while stack:
        directory = stack.pop()
        try:
            with os.scandir(directory) as entries:
                children = sorted(entries, key=lambda entry: os.fsencode(entry.name))
        except OSError as error:
            raise BuildIdentityError(f"cannot list source directory {directory}: {error}") from error
        has_included_child = False
        for entry in children:
            path = Path(entry.path)
            if _ignored_source_path(path, top) or _excluded(path, excluded + ignored):
                continue
            try:
                relative = path.relative_to(top)
            except ValueError:
                raise BuildIdentityError(f"source entry escaped the identified tree: {path}")
            raw_path = os.fsencode(relative.as_posix())
            if raw_path in gitlinks:
                try:
                    initialized = path.is_dir() and (path / ".git").exists()
                    empty_uninitialized = path.is_dir() and not any(path.iterdir())
                except OSError as error:
                    raise BuildIdentityError(f"cannot inspect Git submodule {path}: {error}") from error
                if initialized:
                    has_included_child = True
                    continue
                if empty_uninitialized:
                    has_included_child = True
                    continue
            try:
                metadata = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or _is_reparse_point(metadata):
                    payload = _link_target(path, top, excluded + ignored)
                    object_id = _blob_object_id(payload, object_format)
                    present_files.add(raw_path)
                    expected_entry = expected.get(raw_path)
                    if expected_entry != (b"120000", object_id):
                        files.append(
                            (raw_path, b"symlink", object_id, hashlib.sha256(payload).digest(), 0)
                        )
                    has_included_child = True
                elif stat.S_ISDIR(metadata.st_mode):
                    stack.append(path)
                    has_included_child = True
                elif stat.S_ISREG(metadata.st_mode):
                    present_files.add(raw_path)
                    expected_entry = expected.get(raw_path)
                    _size, content_digest, object_id, executable = _file_state(
                        path, object_format
                    )
                    same_mode = (
                        os.name == "nt"
                        or bool(executable) == (expected_entry is not None and expected_entry[0] == b"100755")
                    )
                    if (
                        expected_entry is None
                        or expected_entry[0] not in {b"100644", b"100755"}
                        or object_id != expected_entry[1]
                        or not same_mode
                    ):
                        files.append((raw_path, b"file", object_id, content_digest, executable))
                    has_included_child = True
                else:
                    raise BuildIdentityError(f"unsupported source entry type: {path}")
            except OSError as error:
                raise BuildIdentityError(f"cannot inspect source entry {path}: {error}") from error
        if directory != top and not has_included_child:
            empty_directories.add(os.fsencode(directory.relative_to(top).as_posix()))
    return files, empty_directories, present_files


def _submodule_identity(
    top: Path,
    raw_path: bytes,
    excluded: Sequence[Path],
    ignored: Sequence[Path],
) -> SourceIdentity | None:
    path = top / Path(os.fsdecode(raw_path))
    if path.is_symlink() or not path.is_dir() or not (path / ".git").exists():
        return None
    child_top = Path(os.fsdecode(source_git._git(path, "rev-parse", "--show-toplevel").strip())).resolve()
    if path.resolve(strict=True) != child_top:
        raise BuildIdentityError(f"Git submodule path resolves to a different root: {path}")
    child_excluded = tuple(root for root in excluded if _is_within(root, child_top))
    child_ignored = tuple(root for root in ignored if _is_within(root, child_top))
    return source_identity(child_top, child_excluded, child_ignored)


def _gitlink_state(
    top: Path,
    tree: dict[bytes, tuple[bytes, bytes, bytes]],
    index: dict[bytes, list[tuple[bytes, bytes, bytes]]],
    excluded: Sequence[Path],
    ignored: Sequence[Path],
) -> tuple[set[bytes], list[tuple[bytes, bytes, bytes]]]:
    paths = {
        path
        for path, (mode, kind, _object_id) in tree.items()
        if mode == b"160000" and kind == b"commit"
    }
    paths.update(
        path
        for path, stages in index.items()
        if any(mode == b"160000" for mode, _object_id, _stage in stages)
    )
    included: set[bytes] = set()
    changed: list[tuple[bytes, bytes, bytes]] = []
    for raw_path in sorted(paths):
        path = top / Path(os.fsdecode(raw_path))
        if _excluded(path, excluded + ignored):
            continue
        included.add(raw_path)
        head_id = tree.get(raw_path, (b"", b"", b""))[2]
        index_stages = sorted(
            (mode, object_id, stage)
            for mode, object_id, stage in index.get(raw_path, ())
            if mode == b"160000"
        )
        stage_frame = b";".join(b" ".join(values) for values in index_stages)
        identity = _submodule_identity(top, raw_path, excluded, ignored)
        index_id = next((object_id for _mode, object_id, stage in index_stages if stage == b"0"), b"")
        expected_id = index_id or head_id
        index_differs = bool(index_stages) and index_id != head_id
        index_removed = bool(head_id) and not index_stages
        child_differs = identity is not None and (
            identity.revision.encode("ascii") != expected_id or identity.dirty
        )
        uninitialized_changed = identity is None
        if index_differs or index_removed or child_differs or uninitialized_changed:
            child = (
                b"uninitialized"
                if identity is None
                else json.dumps(identity.as_dict(), sort_keys=True, separators=(",", ":")).encode()
            )
            changed.append((raw_path, head_id + b"\0" + stage_frame, child))
    return included, changed


def source_identity(
    root: Path,
    excluded_roots: Sequence[Path] = (),
    ignored_paths: Sequence[Path] = (),
) -> SourceIdentity:
    root = _canonical(root, strict=True)
    top = Path(os.fsdecode(source_git._git(root, "rev-parse", "--show-toplevel").strip())).resolve()
    revision = os.fsdecode(source_git._git(top, "rev-parse", "HEAD").strip())
    excluded = tuple(_canonical(path) for path in excluded_roots)
    ignored = tuple(_canonical(path) for path in ignored_paths)
    if any(not _is_within(path, top) for path in ignored):
        raise BuildIdentityError("ignored source paths must stay inside the source tree")
    try:
        object_format = os.fsdecode(source_git._git(top, "rev-parse", "--show-object-format").strip())
        hashlib.new(object_format)
    except ValueError as error:
        raise BuildIdentityError(f"unsupported Git object format in {top}") from error
    tree = source_git._tree_entries(top)
    index = source_git._index_entries(top)
    expected = {
        raw_path: (mode, object_id)
        for raw_path, (mode, kind, object_id) in tree.items()
        if kind == b"blob"
        and mode in {b"100644", b"100755", b"120000"}
        and not _excluded(top / Path(os.fsdecode(raw_path)), excluded + ignored)
    }
    gitlink_paths, changed_gitlinks = _gitlink_state(
        top, tree, index, excluded, ignored
    )
    files, empty_directories, present_files = _checkout_manifest(
        top,
        excluded,
        ignored,
        gitlink_paths,
        object_format,
        expected,
    )
    missing_files = set(expected).difference(present_files)
    dirty = bool(files or missing_files or empty_directories or changed_gitlinks)
    digest = hashlib.sha256()
    _feed_framed(digest, revision.encode("ascii"))
    for raw_path in sorted(missing_files):
        _feed_framed(digest, b"missing-entry")
        _feed_framed(digest, raw_path)
    for raw_path, entry_type, object_id, content_digest, executable in sorted(files):
        _feed_framed(digest, b"entry")
        _feed_framed(digest, raw_path)
        _feed_framed(digest, entry_type)
        _feed_framed(digest, object_id)
        _feed_framed(digest, content_digest)
        _feed_framed(digest, executable.to_bytes(2, "big"))
    for raw_path in sorted(empty_directories):
        _feed_framed(digest, b"empty-directory")
        _feed_framed(digest, raw_path)
    for raw_path, index_frame, child in changed_gitlinks:
        _feed_framed(digest, b"gitlink")
        _feed_framed(digest, raw_path)
        _feed_framed(digest, index_frame)
        _feed_framed(digest, child)
    return SourceIdentity(
        root=top.as_posix(),
        revision=revision,
        tree_digest=digest.hexdigest(),
        dirty=dirty,
    )


def toolchain_identity(root: Path) -> str:
    try:
        result = execute_process(
            (os.environ.get("RUSTC", "rustc"), "--version", "--verbose"),
            timeout=60,
            cwd=root,
        )
    except GitProcessError as error:
        raise BuildIdentityError(f"cannot run rustc: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise BuildIdentityError(f"rustc --version --verbose failed: {detail}")
    return " ".join(result.stdout.decode("utf-8", errors="replace").split())


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
