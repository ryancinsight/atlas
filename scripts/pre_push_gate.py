#!/usr/bin/env python3
"""Own the complete pre-push or documentation process tree and wall bound."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parent))
import process_tree

DEADLINE_SECONDS = 600
LOG_TAIL_BYTES = 32768


def _emit(value: bytes | None, stream) -> None:
    if value:
        stream.buffer.write(value)
        stream.flush()


def _progress_report(progress: Path) -> None:
    marker = progress / "stages.log"
    if marker.is_file():
        print("pre-push: bounded stage timings:", file=sys.stderr)
        print(
            marker.read_text(encoding="utf-8", errors="replace"),
            end="",
            file=sys.stderr,
        )


def _progress_log(progress: Path) -> None:
    log = progress / "gate.log"
    if log.is_file():
        print("pre-push: final bounded gate log bytes:", file=sys.stderr)
        _emit(log.read_bytes()[-LOG_TAIL_BYTES:], sys.stderr)


def _cache_git(git_dir: Path, *arguments: str, stdout=None) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    for name in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_REPLACE_REF_BASE", "BASH_ENV", "ENV"):
        environment.pop(name, None)
    return subprocess.run(
        ["bash", "-c", 'exec git "$@"', "git", "--no-replace-objects", f"--git-dir={git_dir}", *arguments],
        check=False,
        capture_output=stdout is None,
        stdout=stdout,
        env=environment,
    )


def _cache_hash(git_dir: Path, path: Path) -> str | None:
    if not path.exists():
        return None
    result = _cache_git(git_dir, "hash-object", "--no-filters", "--", str(path))
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(f"git hash-object exited {result.returncode}: {detail}")
    return result.stdout.decode("ascii").strip()


def _cache_worker(git_dir: Path, blob: str, cache: Path) -> int:
    """Materialize one verified hook blob under the shared publication lease."""
    import atlas_build_lock

    if cache.is_dir() and not cache.is_symlink():
        print(f"atlas hooks: {cache} is a directory", file=sys.stderr)
        return 1
    lock = cache.parent.parent / ".cache-locks" / blob
    handle = None
    partial: Path | None = None
    try:
        cached_hash = _cache_hash(git_dir, cache)
        if cached_hash == blob:
            return 0
        if cache.is_dir() and not cache.is_symlink():
            raise OSError(f"{cache} is a directory")
        cache.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f"{blob}.", dir=cache.parent)
        os.close(descriptor)
        partial = Path(temporary)
        with partial.open("wb") as output:
            result = _cache_git(git_dir, "cat-file", "blob", blob, stdout=output)
        if result.returncode != 0:
            _emit(result.stderr, sys.stderr)
            return 1
        digest = _cache_hash(git_dir, partial)
        if digest != blob:
            return 1
        partial.chmod(0o755)
        handle = atlas_build_lock._take(
            lock, atlas_build_lock.EXCLUSIVE, wait=atlas_build_lock.LockWait.BLOCKING
        )
        if handle is None:
            raise OSError("the blocking hook publication lock was not acquired")
        cached_hash = _cache_hash(git_dir, cache)
        if cached_hash == blob:
            return 0
        if cache.is_dir() and not cache.is_symlink():
            raise OSError(f"{cache} is a directory")
        os.replace(partial, cache)
        partial = None
        return 0
    except (OSError, atlas_build_lock.BuildIdentityError) as error:
        print(f"atlas hooks: cache publication failed: {error}", file=sys.stderr)
        return 1
    finally:
        if partial is not None:
            partial.unlink(missing_ok=True)
        if handle is not None:
            atlas_build_lock._release(handle, True)


def _cache_command(arguments: list[str]) -> int:
    if len(arguments) != 3:
        print("pre-push: BLOCKED -- malformed cache publication", file=sys.stderr)
        return 2
    git_dir = Path(arguments[0])
    blob = arguments[1]
    cache = Path(arguments[2])
    try:
        result = process_tree.run(
            [sys.executable, "-I", __file__, "--cache-worker", str(git_dir), blob, str(cache)],
            timeout=DEADLINE_SECONDS,
        )
    except process_tree.ProcessTreeTimeout as error:
        _emit(error.output, sys.stdout)
        _emit(error.stderr, sys.stderr)
        detail = "process-tree retirement completed"
        if error.cleanup_error is not None:
            detail = f"process-tree retirement failed: {error.cleanup_error}"
        print(f"pre-push: BLOCKED -- cache phase exceeded {DEADLINE_SECONDS} seconds; {detail}", file=sys.stderr)
        return 124
    except process_tree.ProcessTreeCleanupError as error:
        print(f"pre-push: BLOCKED -- cache phase cleanup failed: {error}", file=sys.stderr)
        return 1
    _emit(result.stdout, sys.stdout)
    _emit(result.stderr, sys.stderr)
    if result.returncode == 0:
        print(cache)
    return result.returncode


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--cache-worker":
        if len(sys.argv) != 5:
            return 2
        return _cache_worker(Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
    if len(sys.argv) >= 2 and sys.argv[1] == "cache":
        return _cache_command(sys.argv[2:])
    if len(sys.argv) < 4:
        print("pre-push: BLOCKED -- malformed process-tree bootstrap", file=sys.stderr)
        return 2
    entry_kind, phase, hook, *arguments = sys.argv[1:]
    if entry_kind not in {"direct", "shim"}:
        print(
            f"pre-push: BLOCKED -- invalid bounded entry kind {entry_kind}",
            file=sys.stderr,
        )
        return 2
    if phase not in {"push", "documentation"}:
        print(f"pre-push: BLOCKED -- invalid bounded phase {phase}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="pg-progress.") as temporary:
        progress = Path(temporary)
        os.environ["ATLAS_GATE_PROGRESS_DIR"] = str(progress)
        if entry_kind == "shim":
            os.environ["ATLAS_GATE_BOUNDED"] = "1"
            command = ["bash", hook, "--atlas-shim-bounded", *arguments]
        else:
            command = ["bash", hook, "--bounded-entry", *arguments]
        try:
            # Inherit the native environment block. Rebuilding it from
            # os.environ on Windows uppercases caller variable and exported
            # function names, changing the hook's input contract.
            result = process_tree.run(
                command,
                timeout=DEADLINE_SECONDS,
            )
        except process_tree.ProcessTreeTimeout as error:
            _emit(error.output, sys.stdout)
            _emit(error.stderr, sys.stderr)
            _progress_report(progress)
            _progress_log(progress)
            cleanup_error = error.cleanup_error
            if cleanup_error is None:
                retirement = "its process tree was retired"
            else:
                retirement = (
                    "process-tree retirement failed: "
                    f"{cleanup_error}"
                )
            print(
                f"pre-push: BLOCKED -- {phase} phase exceeded "
                f"{DEADLINE_SECONDS} seconds; {retirement}",
                file=sys.stderr,
            )
            return 124
        except process_tree.ProcessTreeCleanupError as error:
            print(
                f"pre-push: BLOCKED -- {phase} phase cleanup failed: {error}",
                file=sys.stderr,
            )
            return 1
        _emit(result.stdout, sys.stdout)
        _emit(result.stderr, sys.stderr)
        _progress_report(progress)
        if result.returncode != 0:
            _progress_log(progress)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
