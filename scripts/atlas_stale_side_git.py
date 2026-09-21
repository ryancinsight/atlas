"""Read-only Git queries for the Atlas stale-side guard."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import atlas_git_process as process

GIT_TIMEOUT_SECONDS = 30
FILE_MODES = frozenset({"100644", "100755"})
CHANGED_FILTER = "ACMR"
PATH_CHUNK = 64


@dataclass(frozen=True)
class Revision:
    commit: str
    count: int


@dataclass(frozen=True)
class Finding:
    path: str
    source: str
    blob: str
    revision: Revision
    ancestor: bool | None
    materializes: tuple[str, ...] = ()


def git_env(index: Path | None = None) -> dict[str, str]:
    """Preserve caller config while isolating repository routing."""
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE"):
        env.pop(key, None)
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def run(
    repo: Path,
    *args: str,
    stdin: str | None = None,
    env: dict[str, str] | None = None,
    allowed: tuple[int, ...] = (0,),
) -> tuple[int, str]:
    result = process.execute(
        repo,
        args,
        stdin=None if stdin is None else stdin.encode("utf-8"),
        env=git_env() if env is None else env,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    stdout = result.stdout.decode("utf-8", "replace")
    stderr = result.stderr.decode("utf-8", "replace")
    if result.returncode not in allowed:
        detail = stderr.strip() or stdout.strip() or "no diagnostic"
        raise process.GitProcessError(
            f"git command failed ({result.returncode}): {' '.join(result.command)}\n{detail}"
        )
    return result.returncode, stdout


def run_bytes(
    repo: Path,
    *args: str,
    stdin: bytes | None = None,
    env: dict[str, str] | None = None,
    allowed: tuple[int, ...] = (0,),
) -> tuple[int, bytes]:
    result = process.execute(
        repo,
        args,
        stdin=stdin,
        env=git_env() if env is None else env,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if result.returncode not in allowed:
        detail = result.stderr.decode("utf-8", "replace").strip() or "no diagnostic"
        raise process.GitProcessError(
            f"git command failed ({result.returncode}): {' '.join(result.command)}\n{detail}"
        )
    return result.returncode, result.stdout


def object_id_width(repo: Path) -> int:
    _code, algorithm = run(repo, "rev-parse", "--show-object-format")
    widths = {"sha1": 40, "sha256": 64}
    try:
        return widths[algorithm.strip()]
    except KeyError as exc:
        raise process.GitProcessError(
            f"unsupported Git object format: {algorithm.strip()!r}"
        ) from exc


def decode_path(raw: bytes) -> str:
    return os.fsdecode(raw)


def revision_subject(repo: Path, commit: str) -> str:
    _code, out = run(repo, "log", "-1", "--format=%h %as %s", commit)
    return out.strip() or commit[:10]


def changed_paths(repo: Path, staged: bool) -> list[str]:
    _code, staged_out = run_bytes(
        repo,
        "diff",
        "--cached",
        "--name-only",
        "-z",
        f"--diff-filter={CHANGED_FILTER}",
    )
    records = staged_out.split(b"\0")
    if not staged:
        _code, worktree_out = run_bytes(repo, "ls-files", "-m", "-z")
        records += worktree_out.split(b"\0")
    return sorted({decode_path(item) for item in records if item})


def index_entries(
    repo: Path, index: Path | None = None
) -> dict[str, tuple[str, str]]:
    env = None if index is None else git_env(index)
    _code, out = run_bytes(repo, "ls-files", "--stage", "-z", env=env)
    entries: dict[str, tuple[str, str]] = {}
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, separator, raw_path = record.partition(b"\t")
        fields = meta.split()
        if not separator or len(fields) < 3:
            raise process.GitProcessError("malformed `git ls-files --stage -z` output")
        entries.setdefault(
            decode_path(raw_path),
            (fields[0].decode("ascii"), fields[1].decode("ascii")),
        )
    return entries


def head_blobs(repo: Path) -> dict[str, str]:
    _code, out = run_bytes(repo, "ls-tree", "-rz", "HEAD")
    blobs: dict[str, str] = {}
    for record in out.split(b"\0"):
        if not record:
            continue
        meta, separator, raw_path = record.partition(b"\t")
        fields = meta.split()
        if not separator or len(fields) < 3:
            raise process.GitProcessError("malformed `git ls-tree -rz` output")
        blobs[decode_path(raw_path)] = fields[2].decode("ascii")
    return blobs


def worktree_blobs(repo: Path, paths: list[str]) -> dict[str, str]:
    present = [path for path in paths if (repo / path).is_file()]
    width = object_id_width(repo)
    hashes: dict[str, str] = {}
    for path in present:
        _code, out = run(repo, "hash-object", "--", path)
        blob = out.strip()
        if len(blob) != width:
            raise process.GitProcessError(
                f"malformed `git hash-object` output for {path!r}"
            )
        hashes[path] = blob
    return hashes


def existing_blobs(repo: Path, blobs: set[str]) -> set[str]:
    if not blobs:
        return set()
    _code, out = run(
        repo, "cat-file", "--batch-check", stdin="\n".join(sorted(blobs)) + "\n"
    )
    found = set()
    for line in out.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] != "missing":
            found.add(fields[0])
    return found


def historical_blobs(
    repo: Path, paths: set[str], all_refs: bool
) -> dict[str, dict[str, Revision]]:
    revisions = ["--all"] if all_refs else ["HEAD"]
    tables: dict[str, dict[str, list]] = {path: {} for path in paths}
    ordered = sorted(paths)
    width = object_id_width(repo)
    for start in range(0, len(ordered), PATH_CHUNK):
        chunk = ordered[start : start + PATH_CHUNK]
        _code, out = run_bytes(
            repo,
            "log",
            "--full-history",
            "-m",
            "-z",
            "--format=COMMIT:%H",
            "--raw",
            "--no-abbrev",
            "--no-renames",
            *revisions,
            "--",
            *chunk,
        )
        commit: str | None = None
        records = iter(record for record in out.split(b"\0") if record)
        for record in records:
            normalized = record.lstrip(b"\n")
            if normalized.startswith(b"COMMIT:"):
                commit = normalized.removeprefix(b"COMMIT:").decode("ascii")
                continue
            if not normalized.startswith(b":"):
                raise process.GitProcessError("malformed `git log --raw -z` record")
            fields = normalized.split()
            try:
                label = decode_path(next(records))
            except StopIteration as exc:
                raise process.GitProcessError(
                    "missing path in `git log --raw -z` output"
                ) from exc
            if commit is None or len(fields) < 4 or label not in tables:
                raise process.GitProcessError("malformed `git log --raw -z` metadata")
            post_image = fields[3].decode("ascii")
            if post_image == "0" * width:
                continue
            if len(post_image) != width:
                raise process.GitProcessError("unexpected object id in `git log --raw -z`")
            slot = tables[label].get(post_image)
            if slot is None:
                tables[label][post_image] = [commit, {commit}]
            else:
                slot[1].add(commit)
    return {
        path: {
            blob: Revision(slot[0], len(slot[1])) for blob, slot in table.items()
        }
        for path, table in tables.items()
    }


def is_ancestor(repo: Path, commit: str) -> bool | None:
    code, _ = run(
        repo, "merge-base", "--is-ancestor", commit, "HEAD", allowed=(0, 1)
    )
    return code == 0


def candidate_refs(repo: Path) -> list[str]:
    _code, out = run(
        repo,
        "for-each-ref",
        "--format=%(refname:short)",
        "refs/heads",
        "refs/remotes/origin/main",
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def ref_blob_tables(repo: Path) -> dict[str, dict[str, str]]:
    tables: dict[str, dict[str, str]] = {}
    for ref in candidate_refs(repo):
        _code, out = run_bytes(repo, "ls-tree", "-rz", ref)
        blobs: dict[str, str] = {}
        for record in out.split(b"\0"):
            if not record:
                continue
            meta, separator, raw_path = record.partition(b"\t")
            fields = meta.split()
            if not separator or len(fields) < 3:
                raise process.GitProcessError("malformed `git ls-tree -rz` output")
            blobs[decode_path(raw_path)] = fields[2].decode("ascii")
        tables[ref] = blobs
    return tables


def materializing_refs(
    tables: dict[str, dict[str, str]], path: str, blob: str
) -> tuple[str, ...]:
    return tuple(sorted(ref for ref, items in tables.items() if items.get(path) == blob))


def candidates(
    paths: list[str],
    entries: dict[str, tuple[str, str]],
    heads: dict[str, str],
    worktree: dict[str, str],
    sources: tuple[str, ...],
) -> list[tuple[str, str, str]]:
    found = []
    for path in paths:
        entry = entries.get(path)
        if entry is None or entry[0] not in FILE_MODES:
            continue
        head = heads.get(path)
        if "index" in sources and entry[1] != head:
            found.append((path, "index", entry[1]))
        blob = worktree.get(path)
        if "worktree" in sources and blob and blob != head:
            found.append((path, "worktree", blob))
    return found


def collect(
    repo: Path, staged: bool, sources: tuple[str, ...], all_refs: bool
) -> list[Finding]:
    paths = changed_paths(repo, staged)
    worktree = worktree_blobs(repo, paths) if "worktree" in sources else {}
    pending = candidates(paths, index_entries(repo), head_blobs(repo), worktree, sources)
    known = existing_blobs(repo, {item[2] for item in pending})
    pending = [item for item in pending if item[2] in known]
    if not pending:
        return []
    history = historical_blobs(repo, {path for path, _source, _blob in pending}, all_refs)
    refs = ref_blob_tables(repo)
    return [
        Finding(
            path,
            source,
            blob,
            revision,
            is_ancestor(repo, revision.commit) if all_refs else None,
            materializing_refs(refs, path, blob),
        )
        for path, source, blob in pending
        if (revision := history.get(path, {}).get(blob)) is not None
    ]
