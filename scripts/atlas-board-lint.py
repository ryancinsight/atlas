#!/usr/bin/env python3
"""Check the Atlas board for duplicate item ids.

Why: a board id is an anchor. Repo ADRs cite items as
`backlog.md#atlas-arch-010`, commits cite them in `Refs:` trailers, and
agents claim work by id. When two different items share one id, every
inbound reference becomes ambiguous and the claim protocol silently
breaks -- two agents can hold "the same" item and touch unrelated code.

This happened seven times before anyone noticed, once because this agent
filed an item without checking the id was free. Duplicate ids are cheap
to detect and expensive to unpick later, so detect them.

    python scripts/atlas-board-lint.py
    python scripts/atlas-board-lint.py --file checklist.md

Exit status is nonzero when any id is used twice, or when an
ATLAS-* reference resolves to no heading in either board file.

A bare commit hash cited in a board, item file, ADR, or changelog that no
repository in the stack can resolve is reported here and counted per member
by the conformance scan (`unresolved_references`): an identifier is copied
from command output, never typed, and a fabricated one is an escaped defect.

Why the reference check: items cite other items ("follow-ups filed
below", "see ATLAS-XYZ") and those references rot silently - two real
incidents sent work chasing ids that were never filed. A reference is
dangling when its exact id appears as prose in either board but no
heading defines it. Non-ATLAS tokens (crate names, ISSUE-220) are
ignored.

Per-item-file layout (`backlog.md` + `backlog/<anchor>.md`,
`atlas-board-index.py`): past the per-item-file migration, a board's items
live one-per-file under a sibling `backlog/` directory and `backlog.md`
itself carries only the generated index (no `## ` headings to scan). Every
check here generalizes to that layout by treating each `backlog/*.md` file
the way it previously treated one heading's slice of a single big file --
`collisions`/`next_free`/`control_characters` already take one path and
work unchanged when pointed at an item file; `_defined_ids`/`dangling_refs`
already take a *list* of paths, so the item files simply join the list.
`main` detects the layout (a `backlog/` directory beside `backlog.md`) and
switches the file set it scans; nothing about the checks themselves differs.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Historical boards attach an item's original specification as a second
# heading under the SAME id (`## ATLAS-DMRI-IO-001 original specification`).
# The id still resolves to exactly one item, so that appendix is not an
# anchor collision - and per ATLAS-BOARD-CLOSURE-CANON-001, historical
# closure markers are being canonicalized, not renumbered. Anything after
# the id matching this suffix marks an appendix of the item defined above it.
APPENDIX_SUFFIX = re.compile(
    r"^\s+(original\s+specification)\s*$", re.IGNORECASE
)

# C0 controls and DEL, less LF and CR. A Windows path written into a
# non-raw string has its escapes interpreted -- `D:\atlas` becomes BEL and
# `tlas`, `\target` a TAB -- and eight such spans reached the board across
# two authors' merged commits (ATLAS-BOARD-CONTROL-CHARACTERS-2026-09-18),
# because nothing read the board for them. TAB is included: the boards
# indent with spaces, so a TAB is always an interpreted `\t`.
CONTROL = re.compile(r"[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]")


def control_characters(path: pathlib.Path) -> list[tuple[int, str]]:
    """Return (line number, escaped line excerpt) for every line holding a
    control character, reading bytes so no decoder normalizes them away."""
    found = []
    text = path.read_bytes().decode("utf-8", errors="replace")
    for lineno, line in enumerate(text.split("\n"), start=1):
        body = line[:-1] if line.endswith("\r") else line
        if CONTROL.search(body):
            found.append((lineno, body.encode("unicode_escape").decode("ascii")[:120]))
    return found


def collisions(path: pathlib.Path) -> dict[str, list[tuple[int, str]]]:
    """Map each duplicated id to its (line number, title) occurrences.

    The duplicate-id gate must see every heading form the reference check
    sees. `_defined_ids` treats a level-2 or level-3 heading as a definition
    regardless of separator (the board carries em-dash, hyphen, and
    mojibakeed separators), but this function once matched only the em-dash
    level-2 form, so a duplicate id defined via a hyphen or level-3 heading
    escaped the hard gate — the anchor ambiguity the gate exists to prevent.
    Match the same broad heading surface as `_defined_ids`.

    A heading carrying the `original specification` appendix suffix is the
    same item's archived spec, not a second item: it never collides.
    """
    seen: dict[str, list[tuple[int, str]]] = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            m = HEADING_ANY.match(line.rstrip("\r\n"))
            if not m:
                continue
            # Trailing separators vary by era (em dash, hyphen, U+FFFD);
            # the id ends at the first character outside [A-Z0-9-].
            item_id = m.group(1).rstrip("-")
            if APPENDIX_SUFFIX.search(line.rstrip("\r\n")[m.end(1):]):
                continue
            seen.setdefault(item_id, []).append((lineno, line.strip()))
    return {k: v for k, v in seen.items() if len(v) > 1}


def collisions_across(
    paths: list[pathlib.Path],
) -> dict[str, list[tuple[pathlib.Path, int, str]]]:
    """Same rule as `collisions`, generalized across several files.

    Under the per-item-file layout (`atlas-board-index.py`) an id is
    defined by exactly one `backlog/<anchor>.md` file's heading, so a
    genuine collision is now two *files* (or a file and a checklist.md
    heading) claiming the same id rather than two headings inside one
    file -- the source path travels with each occurrence so a report can
    name which files collide.
    """
    seen: dict[str, list[tuple[pathlib.Path, int, str]]] = {}
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                m = HEADING_ANY.match(line.rstrip("\r\n"))
                if not m:
                    continue
                item_id = m.group(1).rstrip("-")
                if APPENDIX_SUFFIX.search(line.rstrip("\r\n")[m.end(1):]):
                    continue
                seen.setdefault(item_id, []).append((path, lineno, line.strip()))
    return {k: v for k, v in seen.items() if len(v) > 1}


def next_free(path: pathlib.Path, prefix: str) -> str:
    """Suggest the next unused numeric id for a prefix, e.g. ATLAS-ARCH."""
    used = set()
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = HEADING_ANY.match(line.rstrip("\r\n"))
            if m:
                item_id = m.group(1).rstrip("-")
            else:
                continue
            if item_id.startswith(prefix + "-"):
                tail = item_id[len(prefix) + 1:]
                if tail.isdigit():
                    used.add(int(tail))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}-{n:03d}"


def next_free_across(paths: list[pathlib.Path], prefix: str) -> str:
    """`next_free`, generalized across several files (the per-item-file
    layout's ids are scattered one per `backlog/<anchor>.md` file)."""
    used: set[int] = set()
    for path in paths:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = HEADING_ANY.match(line.rstrip("\r\n"))
                if not m:
                    continue
                item_id = m.group(1).rstrip("-")
                if item_id.startswith(prefix + "-"):
                    tail = item_id[len(prefix) + 1:]
                    if tail.isdigit():
                        used.add(int(tail))
    n = 1
    while n in used:
        n += 1
    return f"{prefix}-{n:03d}"


REF_PATTERN = re.compile(r"\bATLAS-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
HEADING_ANY = re.compile(r"^#{2,3}\s+(ATLAS-[A-Z0-9-]+)")


def _defined_ids(boards: list[pathlib.Path]) -> set[str]:
    """Every item id defined by a level-2/3 heading across the boards."""
    defined: set[str] = set()
    for board in boards:
        with board.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = HEADING_ANY.match(line.rstrip("\r\n"))
                if m:
                    # Trailing separators vary (em dash, colon); the id ends
                    # at the first character outside [A-Z0-9-].
                    defined.add(m.group(1).rstrip("-"))
    return defined


# Closure is carried in the heading on this board:
# `## ATLAS-ID - title [class] - closed 2026-08-23`.
# The board separates title from state with an em dash; historical
# round-trips replaced some of them with U+FFFD replacement characters
# (mojibake - tracked as its own cleanup item). Match any of the three.
HEADING_CLOSED = re.compile(
    "[\u2014\ufffd-]\\s*(closed|superseded|withdrawn)\\b", re.IGNORECASE
)


def _active_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """(start, end) spans of items whose heading does not mark them closed.

    Closed items are an archive: their prose cites historical context and
    linting it buries signal. Only live items' references are actionable.
    Headings without a closure marker count as active - fail-open keeps new
    items linted from day one.
    """
    starts = [
        i
        for i, line in enumerate(lines)
        if HEADING_ANY.match(line.rstrip("\r\n"))
    ]
    bounds: list[tuple[int, int]] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        if HEADING_CLOSED.search(lines[start]):
            continue
        bounds.append((start, end))
    return bounds


def dangling_refs(
    boards: list[pathlib.Path],
    defined: set[str],
) -> dict[str, list[tuple[str, int]]]:
    """ATLAS-* ids referenced by a *live* item but never defined by a heading.

    References inside closed items are archive prose and skipped; ids that
    are prefixes of defined ids ("MOI-AUDIT" for "MOI-AUDIT-SEC-001") count
    as family mentions, not dangling.
    """
    found: dict[str, list[tuple[str, int]]] = {}
    prefixes = {i.rsplit("-", 1)[0] for i in defined} | {
        i.split("-", 1)[0] for i in defined
    }
    for board in boards:
        lines = board.read_text(encoding="utf-8", errors="replace").splitlines()
        for start, end in _active_blocks(lines):
            for offset, line in enumerate(lines[start:end]):
                if HEADING_ANY.match(line.rstrip("\r\n")):
                    continue
                for ref in REF_PATTERN.findall(line):
                    if ref in defined or ref in prefixes:
                        continue
                    found.setdefault(ref, []).append((board.name, start + offset + 1))
    return found


def _item_files(board: pathlib.Path) -> list[pathlib.Path]:
    """`backlog/*.md` beside `board`, or [] when it is not that layout."""
    item_dir = board.parent / "backlog"
    if board.name != "backlog.md" or not item_dir.is_dir():
        return []
    return sorted(item_dir.glob("*.md"))


# A commit hash in a board, ADR, or changelog is an identifier looked up,
# never typed: an agent completed a hash-shaped slot with hash-shaped noise,
# then narrated "I fabricated that hash" and continued, and nothing measured
# the result. A bare hex run of 7-40 characters carrying at least one digit
# and one letter is a citation to resolve: every English word is digit-free,
# an all-digit run is a hosted run or job id (11 digits, resolved by the
# hosting API rather than an object store), and a real abbreviation lacks
# one class with probability (6/16)^7 + (10/16)^7. Runs preceded by `/`,
# `-`, `.`, `_`, or an alphanumeric are not citations: URLs
# (`commit/<sha>`, the link checker's domain), cargo metadata suffixes
# (`crate-<hash>`), and identifiers.
HASH_PATTERN = re.compile(
    r"(?<![0-9A-Za-z_/.\-])(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}"
    r"(?![0-9A-Za-z_\-])"
)
REFERENCE_BOARDS = ("backlog.md", "checklist.md", "gap_audit.md", "changelog.md")


def _is_git_checkout(path: pathlib.Path) -> bool:
    marker = path / ".git"
    return marker.is_dir() or marker.is_file()


def object_stores(root: pathlib.Path) -> list[pathlib.Path]:
    """Every git checkout whose objects a hash may name: the root and its members.

    A member board cites meta commits and the meta board cites member commits,
    so a hash resolves against the whole stack, not the repository that
    cites it. An archived snapshot has no object store and is skipped.
    """
    stores = [root] if _is_git_checkout(root) else []
    members = root / "repos"
    if members.is_dir():
        stores.extend(
            p for p in sorted(members.iterdir()) if p.is_dir() and _is_git_checkout(p)
        )
    return stores


def reference_artifacts(repo: pathlib.Path) -> list[pathlib.Path]:
    """The files whose cited hashes are checked: boards, item files, ADRs, changelog."""
    found: list[pathlib.Path] = []
    if repo.is_dir():
        found.extend(
            p for p in sorted(repo.iterdir())
            if p.is_file() and p.name.lower() in REFERENCE_BOARDS
        )
    for sub in ("backlog", "docs/adr"):
        d = repo / sub
        if d.is_dir():
            found.extend(sorted(p for p in d.glob("*.md") if p.is_file()))
    return found


def cited_hashes(paths: list[pathlib.Path]) -> dict[str, list[tuple[str, int]]]:
    """Every bare hash token with the (file name, line) sites that cite it."""
    found: dict[str, list[tuple[str, int]]] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for token in HASH_PATTERN.findall(line):
                found.setdefault(token, []).append((path.name, lineno))
    return found


_REACHABLE_INDEX: dict[tuple[pathlib.Path, ...], dict[str, frozenset[str]]] = {}


def _reachable_index(stores: list[pathlib.Path]) -> dict[str, frozenset[str]]:
    """Map 7-char hash prefixes to the full reachable shas they abbreviate.

    Per store, enumerate refs and collect the commits they reach. Enumerate
    refs first (`for-each-ref --format=%(refname)` with no pattern, safe
    across git versions) because rev-listing a raw `refs/remotes/origin`
    prefix is not a revision git accepts; the enumerated names are. Only
    `refs/remotes/origin/*` and `refs/tags/*` count -- those are the refs a
    hash citation is expected to name, and reachability from them is uniform
    across hosts whose object stores differ only in odds and ends. A store
    with none of those refs (a bare fixture or archival checkout) falls back
    to its local `refs/heads/*`, which still answers citations against it.

    A 40-char sha enters the bucket of its first 7 chars. Every process has
    its own index, cached per store list so a stack-wide scan walks the
    reachable history once and each member's token set resolves against it.
    """
    import subprocess
    key = tuple(stores)
    cached = _REACHABLE_INDEX.get(key)
    if cached is not None:
        return cached
    buckets: dict[str, set[str]] = {}
    for store in stores:
        proc = subprocess.run(
            ["git", "-C", str(store), "for-each-ref", "--format=%(refname)"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False,
        )
        names = [
            n for n in proc.stdout.splitlines()
            if n.startswith(("refs/remotes/origin/", "refs/tags/"))
        ]
        if not names:
            local = [
                n for n in proc.stdout.splitlines() if n.startswith("refs/heads/")
            ]
            if local:
                names = local
            else:
                continue
        listed = subprocess.run(
            ["git", "-C", str(store), "rev-list", *names],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False,
        )
        full = (n for n in listed.stdout.splitlines() if re.fullmatch(r"[0-9a-f]{40}", n))
        for n in full:
            buckets.setdefault(n[:7], set()).add(n)
    index = {prefix: frozenset(full) for prefix, full in buckets.items()}
    _REACHABLE_INDEX[key] = index
    return index


def resolve_hashes(tokens: set[str], stores: list[pathlib.Path]) -> set[str]:
    """The subset of `tokens` naming a reachable object in any of `stores`.

    A token resolves when its 7-char prefix has a full sha in `_reachable_index`
    whose own first chars match the token -- git's own abbreviation contract,
    where `ambiguous` still names real objects. The rule is reachability, not
    store contents, so the resolution does not depend on what a working tree
    happens to have materialized.
    """
    index = _reachable_index(stores)
    return {
        t for t in tokens
        if any(full.startswith(t) for full in index.get(t[:7], frozenset()))
    }


def unresolved_hashes(
    paths: list[pathlib.Path], stores: list[pathlib.Path]
) -> dict[str, list[tuple[str, int]]]:
    """Cited hashes that no store can resolve, with their citing sites."""
    cited = cited_hashes(paths)
    resolved = resolve_hashes(set(cited), stores)
    return {token: sites for token, sites in cited.items() if token not in resolved}


def count_unresolved(repo: pathlib.Path, stores: list[pathlib.Path]) -> int:
    """Citation sites of unresolvable hashes in `repo`'s reference artifacts.

    Sites, not distinct tokens: the conformance ratchet counts what one
    correction removes, and a hash cited three times is three corrections.
    """
    return sum(
        len(sites) for sites in unresolved_hashes(reference_artifacts(repo), stores).values()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="backlog.md", help="board file to lint")
    parser.add_argument(
        "--next", metavar="PREFIX",
        help="print the next free id for a prefix (e.g. ATLAS-ARCH) and exit",
    )
    args = parser.parse_args()

    path = ROOT / args.file
    if not path.is_file():
        print(f"no such board file: {path}", file=sys.stderr)
        return 2

    item_files = _item_files(path)
    indexed = bool(item_files) or (path.name == "backlog.md" and (path.parent / "backlog").is_dir())

    if args.next:
        prefix = args.next.rstrip("-")
        if indexed:
            print(next_free_across(item_files, prefix))
        else:
            print(next_free(path, prefix))
        return 0

    # Definitions and dangling-reference scope: the per-item-file layout
    # moves backlog.md's headings into backlog/*.md, so that file set
    # stands in for backlog.md wherever it previously contributed headings.
    boards = [
        *(item_files if indexed else ([path] if path.name == "backlog.md" else [])),
        ROOT / "checklist.md",
    ]
    if path.name != "backlog.md":
        boards.append(path)
    boards = [b for b in boards if b.is_file()]

    defined = _defined_ids(boards)
    refs = dangling_refs(boards, defined)
    dupes = collisions_across(item_files) if indexed else collisions(path)

    status = 0
    # Control characters: the index/preamble file itself, plus every item
    # file when the board is in the per-item-file layout.
    control_targets = [(args.file, path)] + [
        (f"backlog/{f.name}", f) for f in item_files
    ]
    total_controls = 0
    for label, target in control_targets:
        controls = control_characters(target)
        if not controls:
            continue
        total_controls += len(controls)
        print(f"{label}: {len(controls)} line(s) carry control characters\n")
        for lineno, excerpt in controls:
            print(f"  line {lineno}: {excerpt}")
    if total_controls:
        print(
            "\nA control character in a board is an escape interpreted in a "
            "non-raw string (\\a, \\t, \\r from a Windows path). Restore "
            "the original text.\n",
            file=sys.stderr,
        )
        status = 1

    hashes = unresolved_hashes(reference_artifacts(ROOT), object_stores(ROOT))
    if hashes:
        # Report here; the conformance scan ratchets the count per member.
        sites = sum(len(v) for v in hashes.values())
        print(
            f"[report] {sites} citation(s) of {len(hashes)} commit hash(es) no "
            "stack repository can resolve - an identifier is copied from "
            "command output, never typed\n"
        )
        for token, uses in sorted(hashes.items()):
            where = ", ".join(f"{name}:{line}" for name, line in uses[:3])
            print(f"  {token}  {where}")
        print()

    if refs:
        # Report-only until ATLAS-LINT-CALIB normalizes the corpus
        # (closure markers vary by board era; separator mojibake). The
        # duplicate-id gate below stays hard.
        print(
            f"[report] {len(refs)} unreconciled ATLAS-* mention(s) in "
            "live-item prose - see ATLAS-LINT-CALIB\n"
        )

    if not dupes:
        print(f"{args.file}: all item ids unique")
        return status

    print(f"{args.file}: {len(dupes)} duplicated item id(s)\n")
    for item_id, uses in sorted(dupes.items()):
        print(f"  {item_id}")
        for use in uses:
            if len(use) == 3:
                use_path, lineno, title = use
                print(f"    {use_path.name}:{lineno}: {title}")
            else:
                lineno, title = use
                print(f"    line {lineno}: {title}")
        prefix = item_id.rsplit("-", 1)[0]
        if item_id.rsplit("-", 1)[1].isdigit():
            suggestion = (
                next_free_across(item_files, prefix) if indexed else next_free(path, prefix)
            )
            print(f"    -> a free id for this family is {suggestion}")
        print()
    print(
        "Each id is an anchor cited by ADRs, commits and claims. Renumber the "
        "later item and move its inbound references with it.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
