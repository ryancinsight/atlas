#!/usr/bin/env python3
"""Classify pointer-scattered container occurrences in Atlas package sources.

Part of ATLAS-ARCH-008 (replace pointer-scattered containers on traversal
paths). The site list delivered 2026-08-03 separated production
``Vec<Vec<_>>`` occurrences from test/bench/example and ``#[cfg(test)]``-
guarded bindings; this script is the committed, reproducible form of that
classifier.

What it does
------------
1. Scans ``*.rs`` sources under the ``.gitmodules``-registered Atlas members
   only (see ``atlas_stack.registered_members``) — never a bare directory
   listing, so git-ignored private consumers never surface. Provider
   ``worktrees/`` lanes are excluded because they are alternate checkouts,
   not member source.
2. Reads those sources through a ``MemberSource``: the working tree by
   default, or — with ``--pinned`` — the gitlink commits ``HEAD`` records,
   straight out of the object store (``git ls-tree`` + ``git cat-file
   --batch``), with no checkout and no temporary trees. ``--pinned`` is the
   mode the committed oracle is generated and verified in, because it is the
   only one that does not measure unlanded feature-branch work.
3. Strips ``//`` line comments, ``/* */`` block comments, and string/char
   literals (including raw strings) before any analysis, so a
   ``feature = "test-utils"`` value or a ``"mod tests {"`` template string
   cannot pose as a ``test`` predicate and a commented ``Vec<Vec<`` is never
   counted as a site.
4. Finds occurrences of the primary pointer-scattered shape ``Vec<Vec<_>>``
   (override with ``--pattern``) in the remaining code.
5. Classifies each occurrence as *test/bench/example-local* when it sits
   under a ``tests/``, ``benches/``, ``examples/``, ``test_data/``, or
   ``fixtures/`` path, in a ``tests.rs``/``*_test.rs``/``bench.rs``-style
   file, inside a ``#[cfg(test)]``-guarded or ``mod tests`` block or a
   ``#[test]``/``proptest!`` region (tracked by brace depth), or in a file
   whose module declaration is ``#[cfg(test)] mod <name>;``-gated at its
   include site; everything else is *production*.

The production-only site list is the input to hotness-profiled conversion
work; ranking by raw count is deliberately not used (see the entry's
re-scope note). The committed oracle at
``scripts/oracles/arch-008-production-sites.txt`` is a *pinned* census, and is
re-verified by ``--pinned --verify-oracle`` (exit 0 match / 1 drift / 2
unreadable oracle), wired as ``make verify-scattered-oracle``. Because both
generation and verification read the gitlink pins, the gate is stable
whatever any member has checked out, and it fails exactly when a gitlink
advances without the oracle riding along -- so the split can never drift
silently from what is committed.

Usage
-----
    python scripts/atlas_scattered_containers_classify.py
    python scripts/atlas_scattered_containers_classify.py --pinned
    python scripts/atlas_scattered_containers_classify.py --site-list scripts/oracles/arch-008-production-sites.txt
    python scripts/atlas_scattered_containers_classify.py --verify-oracle scripts/oracles/arch-008-production-sites.txt
    python scripts/atlas_scattered_containers_classify.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

try:
    from atlas_stack import clean_git_env, member_pins, registered_members
except ModuleNotFoundError:  # running from scripts/ directly
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from atlas_stack import clean_git_env, member_pins, registered_members

VEC_VEC = re.compile(r"\bVec\s*<\s*Vec\s*<")
CFG_ATTR_RE = re.compile(r"#\s*!?\s*\[\s*cfg\s*\((.+?)\)\s*\]")
NOT_TEST_RE = re.compile(r"\bnot\s*\(\s*test\b")
MOD_TESTS_RE = re.compile(r"\bmod\s+tests\b")
TEST_ATTR_RE = re.compile(r"#\s*\[\s*test\s*\]")
PROPTEST_RE = re.compile(r"\bproptest!\s*\{")
PATH_ATTR_RE = re.compile(r'#\s*\[\s*path\s*=\s*"([^"]+)"\s*\]')
MOD_ITEM_RE = re.compile(r"\bmod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;")

TEST_PATH_PARTS = {"tests", "benches", "examples", "test_data", "fixtures"}
TEST_FILE_RE = re.compile(
    r"^(?:test|tests|bench)\.rs$|.*_(?:test|tests|bench|benches)\.rs$"
)

SKIP_DIRS = {".git", "target", "node_modules", "worktrees"}
SKIP_SUFFIXES = (".rs.bk",)


@dataclass(frozen=True)
class Occurrence:
    """One pointer-scattered container occurrence in a member source file."""

    member: str
    path: str  # relative to the atlas root
    line: int
    column: int
    test_local: bool

    def site(self) -> str:
        """One-line form for the production site list."""
        return f"{self.path}:{self.line}:{self.column}"


class MemberSource(Protocol):
    """Read-only view of one member's Rust sources.

    The classification logic depends on this and never on the filesystem, so
    one analysis runs unchanged over a checkout or over pinned git objects.
    Paths are member-relative POSIX either way, which is also what keeps a
    Windows run and a Linux run comparable.
    """

    def files(self) -> list[PurePosixPath]:
        """Every ``*.rs`` path the member contributes, sorted."""

    def read_text(self, rel: PurePosixPath) -> str:
        """The decoded text of one member-relative source path."""

    def exists(self, rel: PurePosixPath) -> bool:
        """Whether a member-relative path is a file in this source."""

    def close(self) -> None:
        """Release whatever the source holds open."""


def _lexical(path: str) -> str:
    """Collapse ``.``/``..``/empty components without touching the filesystem.

    ``#[path = "../foo.rs"]`` has to key to the same path the file itself
    registers under, and in pinned mode there is no directory to walk up.
    """
    out: list[str] = []
    for part in path.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            if out:
                out.pop()
            continue
        out.append(part)
    return "/".join(out)


def _git(repo: Path, *args: str) -> list[str]:
    """Git argv for reading one member's object store.

    ``safe.directory`` is set for exactly the repository named here. A member
    checkout can end up owned by another account -- a sandbox-created tree, a
    restored backup -- and Git then refuses to read it outright. Whether it
    refuses depends on which global config the ambient ``HOME`` resolves to,
    so `make` and a direct run can disagree about the census; observed for
    real when `make` ran with `HOME=/home/RyanClanton` and silently dropped
    `repos/metis` from the scan. Scoping the exception to the one repository
    the caller named makes the census identical everywhere without relaxing
    the guard for anything else.
    """
    return [
        "git", "-C", str(repo), "-c", f"safe.directory={repo.as_posix()}", *args
    ]


@dataclass(frozen=True)
class WorktreeSource:
    """Member sources read from the checked-out tree.

    Measures unlanded work by construction: a member parked on a feature
    branch contributes that branch's sources. Right for local conversion work,
    wrong for any committed artifact -- use ``PinnedSource`` for those.
    """

    member_root: Path

    def files(self) -> list[PurePosixPath]:
        out: list[PurePosixPath] = []
        for path in sorted(self.member_root.rglob("*.rs")):
            if path.suffix in SKIP_SUFFIXES:
                continue
            rel = PurePosixPath(path.relative_to(self.member_root).as_posix())
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            out.append(rel)
        return out

    def read_text(self, rel: PurePosixPath) -> str:
        return (self.member_root / rel.as_posix()).read_text(errors="replace")

    def exists(self, rel: PurePosixPath) -> bool:
        return (self.member_root / rel.as_posix()).is_file()

    def close(self) -> None:
        return None


class _BatchBlobs:
    """One long-lived ``git cat-file --batch`` per member.

    A member contributes thousands of sources; one process per blob would cost
    thousands of process spawns for the same bytes. The batch protocol pays
    one and streams the rest.
    """

    def __init__(self, repo: Path) -> None:
        self._proc = subprocess.Popen(
            _git(repo, "cat-file", "--batch"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=clean_git_env(),
        )

    def read(self, spec: str) -> str | None:
        """The text of ``<rev>:<path>``, or None when the object is absent."""
        proc = self._proc
        if proc.stdin is None or proc.stdout is None:  # pragma: no cover
            return None
        proc.stdin.write(f"{spec}\n".encode())
        proc.stdin.flush()
        header = proc.stdout.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            return None
        payload = proc.stdout.read(int(header[2]))
        proc.stdout.read(1)  # the protocol's trailing newline
        return payload.decode("utf-8", errors="replace")

    def close(self) -> None:
        proc = self._proc
        if proc.stdin is not None:
            proc.stdin.close()
        if proc.stdout is not None:
            proc.stdout.close()
        proc.wait(timeout=30)


@dataclass
class PinnedSource:
    """Member sources read from the gitlink commit ``HEAD`` records.

    No checkout and no temporary tree: the paths come from ``git ls-tree`` and
    the bytes from ``git cat-file``, so a census taken here is the same
    whichever branch a developer happens to have parked the member on.
    """

    member_root: Path
    pin: str

    def __post_init__(self) -> None:
        self._blobs = _BatchBlobs(self.member_root)
        self._paths = self._list_files()
        self._path_set = frozenset(self._paths)

    def _list_files(self) -> list[PurePosixPath]:
        proc = subprocess.run(
            _git(self.member_root, "ls-tree", "-r", "--name-only", self.pin),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=clean_git_env(),
        )
        # A failed listing must never read as "this member has no sources":
        # that is a whole member quietly leaving the census while the gate
        # still reports a match. Git says why -- an unreadable repository, a
        # missing pin, a `safe.directory` refusal under a different HOME --
        # and that reason belongs in the failure, not in a silent zero.
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise SystemExit(
                f"git ls-tree failed for member {self.member_root.name!r} "
                f"at {self.pin} (exit {proc.returncode}): {detail}"
            )
        paths: list[PurePosixPath] = []
        for name in proc.stdout.splitlines():
            if not name.endswith(".rs"):
                continue
            rel = PurePosixPath(name)
            if any(part in SKIP_DIRS for part in rel.parts):
                continue
            paths.append(rel)
        return sorted(paths)

    def files(self) -> list[PurePosixPath]:
        return self._paths

    def read_text(self, rel: PurePosixPath) -> str:
        text = self._blobs.read(f"{self.pin}:{rel.as_posix()}")
        if text is None:
            # Only paths this source listed are ever read, so an absent blob
            # means the object store disagrees with the tree listing.
            raise SystemExit(
                f"git cat-file could not read {rel.as_posix()!r} at "
                f"{self.pin} in member {self.member_root.name!r}"
            )
        return text

    def exists(self, rel: PurePosixPath) -> bool:
        return rel in self._path_set

    def close(self) -> None:
        self._blobs.close()


@dataclass
class LexState:
    """Cross-line lexer state (block comments and strings span lines).

    Rust permits block comments, `"..."` strings with embedded newlines, and
    `r#"..."#` raw strings to span source lines, so these states are carried
    between `clean_line` calls. Char literals never span lines (a bare `'` is
    a lifetime marker, kept as code).
    """

    in_block_comment: bool = False
    in_str: bool = False
    in_raw: bool = False
    raw_delim: str = ""


def clean_line(line: str, state: LexState) -> tuple[str, list[int]]:
    """Return the code characters of a line with comments and literals removed.

    Returns ``(clean, mapping)`` where ``mapping[i]`` is the index into the
    original line of clean character ``i``. ``state`` carries the block-comment
    and multi-line string flags across lines. Line comments, block comments,
    ``"..."`` strings, ``'x'`` char literals, and raw ``r#"..."#`` strings are
    removed; their contents can never arm a cfg predicate or be counted as an
    occurrence. A bare ``'`` (Rust lifetime marker such as ``'a`` or ``'static``)
    is kept as code — it carries no occurrence or brace.
    """
    clean: list[str] = []
    mapping: list[int] = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if state.in_block_comment:
            if line.startswith("*/", i):
                state.in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if state.in_str:
            if ch == "\\":
                i += 2
            elif ch == '"':
                state.in_str = False
                i += 1
            else:
                i += 1
            continue
        if state.in_raw:
            if line.startswith(state.raw_delim, i):
                state.in_raw = False
                i += len(state.raw_delim)
            else:
                i += 1
            continue
        if ch == "/" and i + 1 < n and line[i + 1] == "/":
            break  # line comment: drop the remainder
        if ch == "/" and i + 1 < n and line[i + 1] == "*":
            state.in_block_comment = True
            i += 2
            continue
        if ch == '"':
            state.in_str = True
            i += 1
            continue
        if ch == "'":
            # Char literal only when a closing quote follows quickly; a bare
            # `'ident` is a lifetime marker and stays as code.
            m = re.match(r"'(\\.|[^'\\])'", line[i:])
            if m:
                i += len(m.group(0))
            else:
                clean.append(ch)
                mapping.append(i)
                i += 1
            continue
        if ch == "r" and i + 1 < n and line[i + 1] in ('"', "#"):
            j = i + 1
            hashes = 0
            while j < n and line[j] == "#":
                hashes += 1
                j += 1
            if j < n and line[j] == '"':
                state.in_raw = True
                state.raw_delim = '"' + "#" * hashes
                i = j + 1
                continue
        clean.append(ch)
        mapping.append(i)
        i += 1
    return "".join(clean), mapping


def _is_test_path(path: PurePosixPath) -> bool:
    """True when the file path is test/bench/example/fixture-owned."""
    if TEST_FILE_RE.match(path.name):
        return True
    return any(part in TEST_PATH_PARTS for part in path.parts)


def _is_test_cfg(line: str) -> bool:
    """True when a code line carries a `test` cfg predicate (excluding not(test))."""
    m = CFG_ATTR_RE.search(line)
    if not m:
        return False
    inner = m.group(1)
    if NOT_TEST_RE.search(inner):
        return False
    return re.search(r"\btest\b", inner) is not None


def _include_gate_candidates(
    source: MemberSource, rel: PurePosixPath
) -> list[tuple[PurePosixPath, str]]:
    """(module file, module name) pairs that could declare `rel`.

    A Rust file is reachable through a `mod <name>;` item in its parent
    module file. For `dir/file.rs` that is `dir/mod.rs` (or the sibling
    `dir.rs`); for a file directly under `src/` it is `src/lib.rs` or
    `src/main.rs`; for `dir/mod.rs` the declared name is `dir`. The crate
    roots `lib.rs`/`main.rs` have no `mod` declaration of their own, and
    neither has a file sitting at the member root.
    """
    parent = rel.parent
    if rel.name == "mod.rs":
        if parent.name == "src":
            return []
        name = parent.name
        pp = parent.parent
        cands = [pp / "mod.rs", pp / "lib.rs", pp / "main.rs", pp / (name + ".rs")]
        return [(c, name) for c in cands if source.exists(c)]
    if rel.name in ("lib.rs", "main.rs"):
        return []
    if parent.name == "":  # member root: no module file can declare it
        return []
    stem = rel.stem
    cands = [parent / "mod.rs"]
    if parent.name == "src":
        cands.extend([parent / "lib.rs", parent / "main.rs"])
    else:
        cands.append(parent.parent / (parent.name + ".rs"))
    return [(c, stem) for c in cands if source.exists(c)]


def _path_decl_map(
    source: MemberSource,
) -> dict[str, tuple[PurePosixPath, int]]:
    """Resolved target path (str) -> (declaring file, its `mod <name>;` index).

    A file loaded via `#[path = "..."]` is declared under an arbitrary module
    name, so the `mod <stem>;` lookup cannot find it. This walks each member
    once (cached by the caller, which scans one member at a time) for
    `#[path]` attributes and records the declaration they attach to, keyed by
    the *resolved* target path (`#[path]` is relative to the declaring file's
    directory). A basename key would collide badly -- many modules are named
    `mod.rs` -- and would wrongly gate unrelated files.
    """
    decls: dict[str, tuple[PurePosixPath, int]] = {}
    for rel in source.files():
        lines = source.read_text(rel).splitlines()
        for i, line in enumerate(lines):
            m = PATH_ATTR_RE.search(line)
            if not m:
                continue
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and MOD_ITEM_RE.search(lines[j]):
                target = _lexical(f"{rel.parent.as_posix()}/{m.group(1)}")
                decls[target] = (rel, j)
    return decls


def _gated_attribute_block(lines: list[str], mod_idx: int, our_name: str) -> bool:
    """True when the attribute block above `mod_idx` is cfg(test)-gated and
    the declaration resolves to a file named `our_name` (by stem or #[path]).

    Walks up from the `mod <name>;` line over blank lines, doc comments and
    stacked attributes, stopping at the first non-attribute line so a cfg
    attribute belonging to a *previous* declaration never leaks onto this one.
    """
    if _is_test_cfg(lines[mod_idx]):  # `#[cfg(test)] mod <name>;` on one line
        return True
    attrs: list[str] = []
    j = mod_idx - 1
    while j >= 0:
        s = lines[j].strip()
        if not s:
            j -= 1
            continue
        if s.startswith("#") or s.startswith("///"):
            attrs.append(s)
            j -= 1
            continue
        break
    if not attrs:
        return False
    m = MOD_ITEM_RE.search(lines[mod_idx])
    declared = m.group(1) if m else ""
    stem = PurePosixPath(our_name).stem
    names_our_file = declared == stem or any(
        (pm := PATH_ATTR_RE.search(a)) is not None
        and PurePosixPath(pm.group(1)).name == our_name
        for a in attrs
    )
    if not names_our_file:
        return False
    return any(_is_test_cfg(a) for a in attrs)


def _is_include_gated(
    source: MemberSource,
    rel: PurePosixPath,
    decl_map: dict[str, tuple[PurePosixPath, int]],
) -> bool:
    """True when the file's module declaration is `#[cfg(test)]`-gated upstream.

    In-file markers alone cannot see a whole file compiled only under tests
    via `#[cfg(test)] mod <name>;` in a parent module; without this check such
    a file would be misreported as production. Two lookups: the `mod <stem>;`
    declaration in the normal module candidates, and files loaded under an
    arbitrary name via `#[path = "..."]` (member-wide map, built once).
    """
    for cand, mod_name in _include_gate_candidates(source, rel):
        cand_lines = source.read_text(cand).splitlines()
        for i, line in enumerate(cand_lines):
            m = MOD_ITEM_RE.search(line)
            if not m or m.group(1) != mod_name:
                continue
            # The declaration names the module (`mod <name>;`), which for a
            # `dir/mod.rs` file is the directory name, not "mod.rs".
            if _gated_attribute_block(cand_lines, i, mod_name + ".rs"):
                return True
    hit = decl_map.get(_lexical(rel.as_posix()))
    if hit is None:
        return False
    decl_rel, mod_idx = hit
    return _gated_attribute_block(
        source.read_text(decl_rel).splitlines(), mod_idx, rel.name
    )


def compute_test_regions(clean_lines: list[str]) -> list[bool]:
    """Mark code lines inside `#[cfg(test)]`-guarded or `mod tests` blocks.

    Brace-depth state machine: a test marker (`#[cfg(test)]`, `mod tests`,
    `#[test]`, or a `proptest! {` block) arms `pending_test`; the next block
    that opens at top level is entered into `open_depths` and every line
    while that stack is non-empty is test-local. Semicolon-terminated lines
    disarm the pending marker so a bare `#[cfg(test)] use ...;` never leaks
    into unrelated following blocks. The closing-brace boundary line is
    outside the guarded region.
    """
    in_test = [False] * len(clean_lines)
    depth = 0
    open_depths: list[int] = []
    pending_test = False
    for idx, line in enumerate(clean_lines):
        stripped = line.strip()
        if not stripped:
            continue

        if (
            _is_test_cfg(line)
            or MOD_TESTS_RE.search(line)
            or TEST_ATTR_RE.search(line)
            or PROPTEST_RE.search(line)
        ):
            pending_test = True

        opens = line.count("{")
        closes = line.count("}")
        for _ in range(opens):
            depth += 1
            if pending_test:
                open_depths.append(depth)
                pending_test = False
        for _ in range(closes):
            if open_depths and depth <= open_depths[-1]:
                open_depths.pop()
            depth = max(0, depth - 1)

        if opens == 0 and stripped.endswith(";"):
            pending_test = False

        in_test[idx] = bool(open_depths)
    return in_test


def classify_file(
    member: str,
    source: MemberSource,
    rel: PurePosixPath,
    decl_map: dict[str, tuple[PurePosixPath, int]],
    pattern: re.Pattern[str] = VEC_VEC,
) -> list[Occurrence]:
    """Find and classify every occurrence of ``pattern`` in one source file."""
    lines = source.read_text(rel).splitlines()
    state = LexState()
    clean_lines: list[str] = []
    mappings: list[list[int]] = []
    for line in lines:
        clean, mapping = clean_line(line, state)
        clean_lines.append(clean)
        mappings.append(mapping)

    test_regions = compute_test_regions(clean_lines)
    matches = [
        (idx, match)
        for idx, clean in enumerate(clean_lines)
        for match in pattern.finditer(clean)
    ]
    if not matches:
        return []

    include_gated = _is_include_gated(source, rel, decl_map)
    path_test = _is_test_path(rel)
    # The member's own root is the same for both sources, so the reported path
    # is identical whether it came off the disk or out of the object store.
    root_rel = f"repos/{member}/{rel.as_posix()}"

    occurrences: list[Occurrence] = []
    for idx, match in matches:
        column = (
            mappings[idx][match.start()] + 1
            if match.start() < len(mappings[idx])
            else match.start() + 1
        )
        occurrences.append(
            Occurrence(
                member=member,
                path=root_rel,
                line=idx + 1,
                column=column,
                test_local=path_test or test_regions[idx] or include_gated,
            )
        )
    return occurrences


def build_sources(pinned: bool) -> list[tuple[str, MemberSource]]:
    """One ``(member, source)`` pair per registered member.

    ``pinned`` selects the gitlink commits ``HEAD`` records; the default is
    the working tree. A member with no recorded gitlink is an error rather
    than a silent skip: its sites would otherwise vanish from the census.
    """
    pins = member_pins() if pinned else {}
    sources: list[tuple[str, MemberSource]] = []
    for member_root in registered_members():
        member = member_root.name
        if not pinned:
            sources.append((member, WorktreeSource(member_root)))
            continue
        pin = pins.get(member)
        if pin is None:
            raise SystemExit(
                f"no gitlink recorded for member {member!r} in HEAD; "
                "a pinned census cannot be taken without one"
            )
        sources.append((member, PinnedSource(member_root, pin)))
    return sources


def scan(
    pattern: re.Pattern[str],
    sources: Sequence[tuple[str, MemberSource]],
) -> list[Occurrence]:
    """Classify every pattern occurrence across the given member sources."""
    occurrences: list[Occurrence] = []
    for member, source in sources:
        decl_map = _path_decl_map(source)
        for rel in source.files():
            occurrences.extend(classify_file(member, source, rel, decl_map, pattern))
    return sorted(
        occurrences,
        key=lambda o: (o.member, o.path, o.line, o.column),
    )


def render_table(occurrences: list[Occurrence]) -> str:
    """Per-member production vs test/bench/example counts."""
    rows: dict[str, tuple[int, int]] = {}
    for occ in occurrences:
        prod, test = rows.get(occ.member, (0, 0))
        if occ.test_local:
            test += 1
        else:
            prod += 1
        rows[occ.member] = (prod, test)

    width = max(len(name) for name in rows) if rows else 8
    lines = [
        f"{'member':<{width}}  {'production':>10}  {'test/bench':>10}",
        "-" * (width + 24),
    ]
    total_prod = total_test = 0
    for member in sorted(rows):
        prod, test = rows[member]
        total_prod += prod
        total_test += test
        lines.append(f"{member:<{width}}  {prod:>10}  {test:>10}")
    lines.append("-" * (width + 24))
    lines.append(f"{'TOTAL':<{width}}  {total_prod:>10}  {total_test:>10}")
    return "\n".join(lines)


@dataclass(frozen=True)
class OracleDrift:
    """Outcome of comparing the current scan against the committed oracle."""

    matches: bool
    added: tuple[str, ...]
    removed: tuple[str, ...]


def parse_oracle(oracle: str) -> set[str]:
    """Parse committed site-list oracle text into the set of site keys.

    Each line is the writer's ``path:line:col  # member`` form; the member
    suffix and blank lines are ignored.
    """
    sites: set[str] = set()
    for line in oracle.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        site, _, _ = stripped.partition("#")
        sites.add(site.rstrip())
    return sites


def verify_oracle(production_sites: Sequence[str], oracle: str) -> OracleDrift:
    """Compare the current production sites against committed oracle text.

    ``added`` sites exist in the scan but not the oracle; ``removed`` sites
    are oracle entries that no longer exist (converted or deleted). The gate
    passes only when both are empty — any drift must be a deliberate,
    committed oracle update, never a silent one.
    """
    current = set(production_sites)
    committed = parse_oracle(oracle)
    added = tuple(sorted(current - committed))
    removed = tuple(sorted(committed - current))
    return OracleDrift(matches=not added and not removed, added=added, removed=removed)


def run_verify_oracle(
    oracle_path: str,
    production_sites: list[str],
    total_sites: int,
    pinned: bool,
) -> int:
    """Gate entry: re-verify the split against the committed oracle.

    Returns 0 on match, 1 on drift, 2 when the oracle file is unreadable, so
    orient and the ``make verify-scattered-oracle`` target can gate on it.

    The mode is named in every message because the committed oracle is a
    *pinned* census: verifying it from the working tree reports the members'
    unlanded branches as drift, and that has to read as a mode mismatch rather
    than as a finding.
    """
    path = Path(oracle_path)
    mode = "pinned" if pinned else "worktree"
    regen = (
        "python scripts/atlas_scattered_containers_classify.py "
        + ("--pinned " if pinned else "")
        + f"--site-list {path}"
    )
    if not path.is_file():
        print(
            f"oracle missing: {path} — regenerate it with `{regen}`",
            file=sys.stderr,
        )
        return 2
    test_bench = total_sites - len(production_sites)
    drift = verify_oracle(production_sites, path.read_text(encoding="utf-8"))
    if drift.matches:
        print(
            f"scattered-container oracle OK ({mode}): "
            f"{len(production_sites)} production sites match {path} "
            f"({test_bench} test/bench, {total_sites} total)"
        )
        return 0
    print(
        f"scattered-container oracle DRIFT vs {path} ({mode} census: "
        f"{len(production_sites)} production, {test_bench} test/bench, "
        f"{total_sites} total):"
    )
    if drift.added:
        print(
            f"  {len(drift.added)} site(s) now in production but missing from "
            "the oracle:"
        )
        for site in drift.added:
            print(f"    + {site}")
    if drift.removed:
        print(
            f"  {len(drift.removed)} oracle site(s) no longer in production "
            "(converted/removed):"
        )
        for site in drift.removed:
            print(f"    - {site}")
    print(
        "  Drift must be a deliberate, committed action: regenerate the oracle "
        f"with `{regen}` and commit it alongside the change."
    )
    if not pinned:
        print(
            "  Note: this was a worktree census. The committed oracle is a "
            "pinned one, so a member parked on a feature branch also shows "
            "here; re-run with --pinned to test the committed state."
        )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify pointer-scattered container occurrences in Atlas package "
            "sources into production vs test/bench/example-local bindings."
        )
    )
    parser.add_argument(
        "--pattern",
        default=VEC_VEC.pattern,
        help="regular expression for the scattered shape (default: Vec<Vec<)",
    )
    parser.add_argument(
        "--pinned",
        action="store_true",
        help=(
            "read member sources from the gitlink commits HEAD records "
            "(git ls-tree + git cat-file, no checkout) instead of the working "
            "tree; required for any committed artifact"
        ),
    )
    parser.add_argument(
        "--site-list",
        metavar="FILE",
        help="write the production-only site list (path:line:col) to FILE",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the full classification as JSON instead of the table",
    )
    parser.add_argument(
        "--verify-oracle",
        metavar="FILE",
        help=(
            "re-verify the production split against the committed oracle FILE "
            "(read-only; exit 0 match, 1 drift, 2 unreadable oracle)"
        ),
    )
    args = parser.parse_args(argv)

    pattern = re.compile(args.pattern)
    sources = build_sources(args.pinned)
    try:
        occurrences = scan(pattern, sources)
    finally:
        for _, source in sources:
            source.close()
    production = [o for o in occurrences if not o.test_local]

    if args.verify_oracle:
        return run_verify_oracle(
            args.verify_oracle,
            [o.site() for o in production],
            len(occurrences),
            args.pinned,
        )

    if args.site_list:
        site_list = Path(args.site_list)
        site_list.parent.mkdir(parents=True, exist_ok=True)
        site_list.write_text(
            "\n".join(f"{o.site()}  # {o.member}" for o in production) + "\n",
            encoding="utf-8",
        )

    if args.json:
        payload = {
            "pattern": pattern.pattern,
            "members": {
                member: {
                    "production": sum(
                        1 for o in occurrences if o.member == member and not o.test_local
                    ),
                    "test_bench": sum(
                        1 for o in occurrences if o.member == member and o.test_local
                    ),
                }
                for member in sorted({o.member for o in occurrences})
            },
            "total_production": len(production),
            "total_test_bench": len(occurrences) - len(production),
            "production_sites": [o.site() for o in production],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_table(occurrences))
        print(
            f"\n{len(production)} production, "
            f"{len(occurrences) - len(production)} test/bench/example-local "
            f"({len(occurrences)} total)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
