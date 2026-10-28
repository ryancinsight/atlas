"""Materialize a fresh CI checkout's exact direct members with bounded workers."""

from __future__ import annotations

import argparse
from collections import deque
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import sys
import tempfile
import time

from atlas_git_process import GitProcessError, GitProcessResult, clean_process_env, execute_process


@dataclass(frozen=True)
class Member:
    name: str
    path: str
    pin: str
    administrative: Path


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], env=clean_process_env(),
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed: " +
                           result.stderr.decode(errors="replace")[-4000:])
    return result.stdout


def text(root: Path, *args: str) -> str:
    return os.fsdecode(git(root, *args)).strip()


def _relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (not path.parts or path.is_absolute() or str(path) != value or
            ".." in path.parts or "\\" in value or
            PureWindowsPath(value).drive or
            any(part.casefold() == ".git" or part.endswith((" ", ".")) or ":" in part
                for part in path.parts)):
        raise RuntimeError(f"unsafe member path/name: {value!r}")
    return path


def _disjoint(paths: list[Path]) -> None:
    for index, path in enumerate(paths):
        for other in paths[index + 1:]:
            if path == other or path in other.parents or other in path.parents:
                raise RuntimeError("member destinations overlap")


def _links(root: Path, *, index: bool = False) -> dict[str, str]:
    arguments = ("ls-files", "--stage", "-z") if index else (
        "ls-tree", "--full-tree", "-r", "-z", "HEAD")
    result = {}
    for record in git(root, *arguments).split(b"\0"):
        if not record:
            continue
        header, path = record.split(b"\t", 1)
        fields = header.split()
        if index and fields[2] != b"0":
            raise RuntimeError("unmerged index entries")
        if fields[0] == b"160000":
            key = os.fsdecode(path)
            if key in result:
                raise RuntimeError("duplicate index gitlink")
            result[key] = fields[1 if index else 2].decode("ascii")
    return result


def _fresh(root: Path, member: Member) -> None:
    destination, admin = root / member.path, member.administrative
    if destination.resolve() != destination or root not in destination.resolve().parents:
        raise RuntimeError("member destination escapes or aliases its root")
    if admin.resolve() != admin:
        raise RuntimeError("member administrative destination is redirected")
    if destination.is_symlink() or (destination.exists() and (
            not destination.is_dir() or any(destination.iterdir()))):
        raise RuntimeError(f"member worktree is not fresh: {member.path}")
    if admin.exists() or admin.is_symlink():
        raise RuntimeError(f"member administrative directory already exists: {member.name}")


def freeze(root: Path) -> tuple[str, list[Member]]:
    if Path(text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise RuntimeError("root is not the repository top level")
    if (root / ".gitmodules").is_symlink():
        raise RuntimeError(".gitmodules must not be a symlink")
    head = text(root, "rev-parse", "HEAD")
    pins = _links(root)
    if not pins:
        raise RuntimeError("no committed direct member gitlinks")
    if _links(root, index=True) != pins:
        raise RuntimeError("index gitlinks differ from committed HEAD")
    git(root, "diff", "--cached", "--exit-code", "HEAD", "--")
    if text(root, "hash-object", "--path=.gitmodules", ".gitmodules") != text(
            root, "rev-parse", "HEAD:.gitmodules"):
        raise RuntimeError("working .gitmodules differs from committed HEAD")
    records = git(root, "config", "--blob", "HEAD:.gitmodules", "-z",
                  "--get-regexp", r"^submodule\..*\.path$")
    module_path = Path(text(root, "rev-parse", "--path-format=absolute",
                            "--git-path", "modules"))
    module_base = module_path.resolve()
    administrative_roots = {
        Path(text(root, "rev-parse", "--absolute-git-dir")).resolve() / "modules",
        Path(text(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve() / "modules",
    }
    if module_base not in administrative_roots:
        raise RuntimeError("member administrative root is redirected")
    members, paths, names = [], set(), set()
    for record in records.split(b"\0"):
        if not record:
            continue
        key, separator, raw_path = record.partition(b"\n")
        if not separator:
            raise RuntimeError("malformed committed submodule mapping")
        name = os.fsdecode(key)[len("submodule."):-len(".path")]
        path = os.fsdecode(raw_path)
        _relative(path)
        administrative = _relative(name)
        admin = module_base.joinpath(*administrative.parts)
        if module_base not in admin.resolve().parents:
            raise RuntimeError("member administrative destination escapes its root")
        if path in paths or name in names or path not in pins:
            raise RuntimeError("duplicate or non-gitlink submodule mapping")
        paths.add(path)
        names.add(name)
        member = Member(name, path, pins[path], admin)
        _fresh(root, member)
        members.append(member)
    if paths != set(pins):
        raise RuntimeError("committed member mappings are incomplete")
    _disjoint([root / m.path for m in members])
    _disjoint([m.administrative for m in members])
    return head, members


def _signature(path: Path) -> tuple | None:
    try:
        stat = path.lstat()
    except FileNotFoundError:
        return None
    return stat.st_dev, stat.st_ino, stat.st_mode, stat.st_size, stat.st_mtime_ns


def _root_files(root: Path) -> list[Path]:
    names = ["config", "config.worktree", "index", "HEAD", "packed-refs"]
    symbolic = subprocess.run(
        ["git", "-C", str(root), "symbolic-ref", "-q", "HEAD"],
        env=clean_process_env(), capture_output=True,
    )
    if symbolic.returncode == 0:
        names.append(os.fsdecode(symbolic.stdout).strip())
    return [root / ".gitmodules", *[
        Path(text(root, "rev-parse", "--path-format=absolute", "--git-path", name))
        for name in names
    ]]


def _pool(root: Path, jobs: int) -> dict:
    head, members = freeze(root)
    mapping_state = _signature(root / ".gitmodules")
    # All root configuration writes finish before any parallel update.
    git(root, "--literal-pathspecs", "submodule", "init", "--",
        *(m.path for m in members))
    for member in members:
        git(root, "config", "--local", f"submodule.{member.name}.active", "true")
    if (_signature(root / ".gitmodules") != mapping_state or
            text(root, "rev-parse", "HEAD") != head or
            _links(root, index=True) != {m.path: m.pin for m in members} or
            text(root, "hash-object", "--path=.gitmodules", ".gitmodules") !=
            text(root, "rev-parse", f"{head}:.gitmodules")):
        raise RuntimeError("committed inputs changed during registration")
    root_files = _root_files(root)
    state = [_signature(path) for path in root_files]
    pending, running, completed = deque(members), [], []

    def unchanged() -> None:
        if [_signature(path) for path in root_files] != state:
            raise RuntimeError("root config/index/HEAD changed during materialization")

    # The enclosing published process-tree supervisor owns this pool and all
    # descendant Git processes. No worker creates a new session/process group.
    with ExitStack() as files:
        try:
            while pending or running:
                unchanged()
                while pending and len(running) < jobs:
                    member = pending.popleft()
                    _fresh(root, member)
                    stdout = files.enter_context(tempfile.TemporaryFile())
                    stderr = files.enter_context(tempfile.TemporaryFile())
                    started = time.monotonic_ns()
                    process = subprocess.Popen(
                        ["git", "-C", str(root), "--literal-pathspecs", "-c",
                         "protocol.version=2", "-c", "submodule.recurse=false",
                         "submodule", "update", "--init", "--checkout", "--force",
                         "--no-recommend-shallow", "--filter=blob:none", "--", member.path],
                        env=clean_process_env(), stdout=stdout, stderr=stderr,
                    )
                    running.append((member, process, stdout, stderr, started))
                for entry in list(running):
                    member, process, stdout, stderr, started = entry
                    if process.poll() is None:
                        continue
                    process.wait()
                    running.remove(entry)
                    if process.returncode:
                        stderr.seek(0)
                        detail = stderr.read().decode(errors="replace")[-4000:]
                        raise RuntimeError(f"member {member.path} failed ({process.returncode}): {detail}")
                    destination = root / member.path
                    if text(destination, "rev-parse", "HEAD") != member.pin:
                        raise RuntimeError(f"member pin mismatch: {member.path}")
                    if text(destination, "rev-parse", "--is-shallow-repository") != "false":
                        raise RuntimeError(f"member history is shallow: {member.path}")
                    if text(destination, "config", "--get", "remote.origin.partialclonefilter") != "blob:none":
                        raise RuntimeError(f"member clone is not blobless: {member.path}")
                    stdout.close()
                    stderr.close()
                    completed.append({"path": member.path, "pin": member.pin,
                                      "started_ns": started,
                                      "finished_ns": time.monotonic_ns()})
                if running:
                    time.sleep(0.02)
            unchanged()
            if text(root, "rev-parse", "HEAD") != head or _links(root, index=True) != {
                    m.path: m.pin for m in members}:
                raise RuntimeError("root snapshot changed")
            if text(root, "hash-object", "--path=.gitmodules", ".gitmodules") != text(
                    root, "rev-parse", f"{head}:.gitmodules"):
                raise RuntimeError("committed member mapping changed")
            for member in members:
                destination = root / member.path
                if text(destination, "rev-parse", "HEAD") != member.pin:
                    raise RuntimeError(f"member pin mismatch: {member.path}")
                if text(destination, "rev-parse", "--is-shallow-repository") != "false":
                    raise RuntimeError(f"member history is shallow: {member.path}")
            return {"head": head, "jobs": jobs, "members": completed}
        finally:
            # Stop queued work on every failure. The outer supervisor retires
            # descendants too, including a Git child whose parent already died.
            for _, process, _, _, _ in running:
                if process.poll() is None:
                    process.terminate()
            for _, process, _, _, _ in running:
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass


def materialize(root: Path, jobs: int, *, timeout: int = 480) -> GitProcessResult:
    """Supervise the real worker pool; the CLI always uses the CI deadline."""
    return execute_process(
        [sys.executable, str(Path(__file__).resolve()), "--root", str(root),
         "--jobs", str(jobs), "--owned-pool"],
        cwd=root, timeout=timeout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--jobs", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--owned-pool", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.owned_pool:
            print(json.dumps(_pool(root, args.jobs), sort_keys=True))
            return 0
        result = materialize(root, args.jobs)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        return result.returncode
    except KeyboardInterrupt:
        return 130
    except (GitProcessError, OSError, RuntimeError, ValueError) as error:
        print(f"CI member materialization failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
