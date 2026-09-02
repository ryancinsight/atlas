#!/usr/bin/env python3
"""Emit, verify, and query revision-keyed SCIP symbol indexes for the stack.

Per AGENTS.md `context_and_memory: code-search ladder`, a static symbol
index emitted per tree is the third rung: it resolves definitions and
references without full-file reads. The index is revision-keyed (one file
per member HEAD) so any worktree of one gitdir is worktree-safe, and it is
derived state under the generator contract: `check` fails on drift so the
sweep can gate freshness exactly like the stack overlay and the ADR index.

The payloads `rust-analyzer scip` emits on this host are raw protobuf
(no gzip framing; the reader sniffs either), keyed to the current SCIP
protocol: `Index.documents = 2`, `Document.relative_path = 1`,
`Document.occurrences = 2`, `Occurrence.range = 1` (packed int32),
`Occurrence.symbol = 2`, `Occurrence.symbol_roles = 3`. The decoder here
is a minimal purpose-built reader over exactly the fields this tool reads;
it is not a general protobuf runtime.

Modes:

    generate  emit an index for every Cargo stack member at its current
              HEAD (`.scip/<member>/<sha>.scip`), pruning stale revisions
    check     verify each member's current index exists, is non-empty, and
              decodes as SCIP; nonzero exit on drift
    lookup    print occurrences whose symbol contains a token, as
              `<member> <relpath>:<1-based line>:<1-based col> <role> <symbol>`

`lookup` performs no full-file reads: the SCIP range yields the exact
line, so an agent reads only that region afterwards.

    python scripts/search-ladder-index.py generate
    python scripts/search-ladder-index.py check
    python scripts/search-ladder-index.py lookup NumericLu
    python scripts/search-ladder-index.py lookup --defs-only NumericLu
"""

from __future__ import annotations

import argparse
import gzip
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS = ROOT / "repos"
INDEX_DIR = ROOT / ".scip"

# Current SCIP SymbolRole enum (scip-code/scip scip.proto).
ROLE_BITS = (
    (0x1, "def"),
    (0x2, "import"),
    (0x4, "write"),
    (0x8, "read"),
    (0x10, "generated"),
    (0x20, "test"),
    (0x40, "forward-def"),
)


def members(selected: list[str]) -> list[pathlib.Path]:
    """Stack members holding a Cargo workspace, in stable order.

    Untracked drops (a private consumer kept out of the stack by
    .gitignore) are skipped: they are not ours to index.
    """
    found = []
    for path in sorted(REPOS.iterdir()):
        if not (path / "Cargo.toml").is_file():
            continue
        if selected and path.name not in selected:
            continue
        tracked = subprocess.run(
            ["git", "check-ignore", "-q", f"repos/{path.name}"],
            cwd=ROOT,
            capture_output=True,
        )
        if tracked.returncode == 0:
            continue
        found.append(path)
    return found


def head_sha(repo: pathlib.Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, encoding="utf-8", errors="replace"
    )
    return proc.stdout.strip()


def role_label(roles: int) -> str:
    parts = [name for bit, name in ROLE_BITS if roles & bit]
    return ",".join(parts) if parts else "ref"


def varint(data: bytes, pos: int) -> tuple[int, int]:
    shift = 0
    result = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos
        shift += 7


def fields(data: bytes) -> dict[int, list[object]]:
    """Decode a protobuf message into {field_no: [values]}.

    Wire type 0 values are ints, wire type 2 values are bytes (raw), and
    wire types 1/5 are little-endian integers. Messages are NOT recursed
    here; callers pass the message bytes to `fields` again.
    """
    out: dict[int, list[object]] = {}
    pos = 0
    while pos < len(data):
        key, pos = varint(data, pos)
        fno, wt = key >> 3, key & 7
        if wt == 0:
            val, pos = varint(data, pos)
        elif wt == 1:
            val = int.from_bytes(data[pos : pos + 8], "little")
            pos += 8
        elif wt == 2:
            n, pos = varint(data, pos)
            val = data[pos : pos + n]
            pos += n
        elif wt == 5:
            val = int.from_bytes(data[pos : pos + 4], "little")
            pos += 4
        else:
            raise ValueError(f"wire type {wt} at offset {pos}")
        out.setdefault(fno, []).append(val)
    return out


def packed_varints(data: bytes) -> list[int]:
    out = []
    pos = 0
    while pos < len(data):
        v, pos = varint(data, pos)
        out.append(v)
    return out


def decode_index(data: bytes) -> list[tuple[str, list[tuple[int, int, int, str, int]]]]:
    """Return [(relative_path, [(line, start_char, end_char, symbol, roles)])].

    Ranges are 0-based per the SCIP spec; the caller converts for display.
    """
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    top = fields(data)
    documents = []
    for raw_doc in top.get(2, []):
        doc = fields(raw_doc)
        rel = doc.get(1, [b""])[0]
        path = rel.decode("utf-8", "replace")
        occs = []
        for raw_occ in doc.get(2, []):
            occ = fields(raw_occ)
            rng = packed_varints(occ.get(1, [b""])[0]) if occ.get(1) else []
            if len(rng) < 2:
                continue
            symbol = occ.get(2, [b""])[0].decode("utf-8", "replace")
            roles = occ.get(3, [0])[0]
            occs.append((rng[0], rng[1], rng[2] if len(rng) > 2 else rng[1], symbol, roles))
        documents.append((path, occs))
    return documents


def read_index(repo: pathlib.Path, sha: str) -> pathlib.Path | None:
    target = INDEX_DIR / repo.name / f"{sha}.scip"
    if not target.is_file() or target.stat().st_size == 0:
        return None
    return target


def filter_occurrences(
    docs: list[tuple[str, list[tuple[int, int, int, str, int]]]],
    token: str,
    defs_only: bool,
) -> list[tuple[str, int, int, str, int]]:
    """Flatten decoded documents into occurrences matching a symbol token.

    Each entry is (relative_path, line, start_col, symbol, roles), lines and
    columns 0-based as in the SCIP range.
    """
    out = []
    for relpath, occs in docs:
        for line, col, _end, symbol, roles in occs:
            if token not in symbol:
                continue
            if defs_only and not (roles & 0x1):
                continue
            out.append((relpath, line, col, symbol, roles))
    return out


def format_occurrence(repo: str, relpath: str, line: int, col: int, symbol: str, roles: int) -> str:
    return f"{repo}  {relpath}:{line + 1}:{col + 1}  {role_label(roles):>12}  {symbol}"


def generate(selected: list[str], timeout: int) -> int:
    targets = members(selected)
    if not targets:
        print("no matching stack members", file=sys.stderr)
        return 2
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    failed = 0
    for repo in targets:
        sha = head_sha(repo)
        target = INDEX_DIR / repo.name / f"{sha}.scip"
        tmp = target.with_suffix(".tmp")
        try:
            proc = subprocess.run(
                ["rust-analyzer", "scip", "--output", str(tmp)],
                cwd=repo,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"  ! {repo.name}: rust-analyzer failed to run ({exc})", file=sys.stderr)
            failed += 1
            continue
        if proc.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
            print(
                f"  ! {repo.name}: rust-analyzer scip exited {proc.returncode}; "
                f"last stderr: {proc.stderr.splitlines()[-1] if proc.stderr.splitlines() else '(none)'}",
                file=sys.stderr,
            )
            tmp.unlink(missing_ok=True)
            failed += 1
            continue
        tmp.replace(target)
        # Prune stale revisions: only the current HEAD index is consulted.
        for old in (INDEX_DIR / repo.name).glob("*.scip"):
            if old.name != target.name:
                old.unlink()
        print(f"indexed     {repo.name}  {sha[:12]}")
    if failed:
        print(f"\n{failed} member(s) failed to index", file=sys.stderr)
        return 1
    print(f"\nindexed {len(targets)} members under {INDEX_DIR}")
    return 0


def check(selected: list[str]) -> int:
    targets = members(selected)
    if not targets:
        print("no matching stack members", file=sys.stderr)
        return 2
    stale = 0
    for repo in targets:
        sha = head_sha(repo)
        index = read_index(repo, sha)
        if index is None:
            stale += 1
            print(f"STALE       {repo.name}  (need index for {sha[:12]})")
            continue
        try:
            docs = decode_index(index.read_bytes())
            if not docs:
                stale += 1
                print(f"STALE       {repo.name}  (index decodes with no documents)")
                continue
        except (ValueError, IndexError) as exc:
            stale += 1
            print(f"STALE       {repo.name}  (index does not decode: {exc})")
            continue
        print(f"ok          {repo.name}  {sha[:12]}  {sum(len(o) for _, o in docs)} occurrences")
    if stale:
        print(f"\n{stale} member(s) stale. Regenerate with `python scripts/search-ladder-index.py generate`", file=sys.stderr)
        return 1
    print(f"\nall {len(targets)} member indexes fresh")
    return 0


def lookup(token: str, selected: list[str], defs_only: bool, limit: int) -> int:
    targets = members(selected)
    if not targets:
        print("no matching stack members", file=sys.stderr)
        return 2
    shown = 0
    for repo in targets:
        sha = head_sha(repo)
        index = read_index(repo, sha)
        if index is None:
            print(f"  ! {repo.name}: no index for current HEAD ({sha[:12]}); regenerate", file=sys.stderr)
            continue
        for relpath, line, col, symbol, roles in filter_occurrences(
            decode_index(index.read_bytes()), token, defs_only
        ):
            if shown >= limit:
                return 0
            print(format_occurrence(repo.name, relpath, line, col, symbol, roles))
            shown += 1
    if shown == 0:
        print(f"no occurrences of {token!r} in {len(targets)} member index(es)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    gen = sub.add_parser("generate", help="emit indexes for all members at current HEAD")
    gen.add_argument("--members", nargs="*", help="limit to these members")
    gen.add_argument("--timeout", type=int, default=600, help="per-member rust-analyzer timeout (s)")

    chk = sub.add_parser("check", help="verify indexes are fresh for every member")
    chk.add_argument("--members", nargs="*", help="limit to these members")

    lk = sub.add_parser("lookup", help="print occurrences whose symbol contains a token")
    lk.add_argument("token")
    lk.add_argument("--members", nargs="*", help="limit to these members")
    lk.add_argument("--defs-only", action="store_true", help="only Definition-role occurrences")
    lk.add_argument("--limit", type=int, default=100, help="max matches to print")

    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    if args.mode == "generate":
        return generate(args.members or [], args.timeout)
    if args.mode == "check":
        return check(args.members or [])
    return lookup(args.token, args.members or [], args.defs_only, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
