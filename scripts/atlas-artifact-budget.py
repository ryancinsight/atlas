#!/usr/bin/env python3
"""Budget gate for PM boards and tracked images.

Two artifact classes grow without bound unless something measures them, and
by the time this gate was written nothing did: RITK's `backlog.md`,
`checklist.md`, and `gap_audit.md` stood at 6,325, 7,609, and 7,570 lines
against a 1,000-line budget, atlas's own at 14,754, 7,910, and 16,338, and
RITK carried 15 MB of tracked screenshots (twenty over 300 KB, one at 1.5 MB)
committed as per-item evidence. Both classes are mechanically remediable --
compaction is scripted (`atlas-board-compact.py`) and an evidence capture
belongs in the PR body or run-output -- so the policy makes them hard gates
rather than ratcheted debt classes (context_and_memory: artifact
compaction; documentation_discipline: report-file genre).

Ratchet-to-budget semantics, so wiring the gate does not block every
repository whose history already exceeds it:

* a board under budget must stay under budget;
* a board over budget may not grow -- a push or PR that adds lines to it
  fails, one that shrinks or holds it passes with the overage reported;
* a tracked image over the byte budget may not be added or modified; an
  existing oversized image passes until touched.

A board past about forty open items moves its item bodies to per-item
files (`backlog/<anchor>.md`) with `backlog.md` as their generated index
(`atlas-board-index.py`); `backlog.md`'s line count here folds in every
`backlog/*.md` file so the 1,000-line board budget still bounds the whole
board. Each item file additionally carries its own fifteen-line budget,
reported (never gated -- a real item can legitimately run long) as
`items_over_budget` and, under `check`, as `INFO` lines.

A board's identity is its canonical name, not its spelling. Four member
repositories track `CHECKLIST.md`, and matching the path case-sensitively
bounded none of them: they reported `pm_lines_over_budget: 0` while carrying
1,156 to 4,328 lines, so a gate could not see the largest boards in the
stack. The three canonical names are resolved per repository by their
canonical name (`_board_paths`), and a board is ratcheted by that identity
too, so a case-only rename between `--base` and the pushed revision does not
read as one board vanishing and another appearing. Every other lookup keeps
`_exact_path`'s case sensitivity: `BACKLOG/item.MD` is still not
`backlog/item.md`.

Without `--base` there is nothing to ratchet against, and every overage
fails. `report` prints the three counts the conformance scanner records per
member (`pm_lines_over_budget`, `oversized_tracked_images`,
`items_over_budget`).

    python scripts/atlas-artifact-budget.py check --base origin/main --rev HEAD
    python scripts/atlas-artifact-budget.py check --root repos/ritk --base "$base"
    python scripts/atlas-artifact-budget.py report --root repos/metis
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PM_FILES = ("backlog.md", "checklist.md", "gap_audit.md")
IMAGE_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
)
LINE_BUDGET = 1000
IMAGE_BUDGET_BYTES = 200 * 1024
# Past about forty open items a board moves its bodies to per-item files
# (`backlog/<anchor>.md`) and `backlog.md` becomes their generated index
# (context_and_memory: Boards). Fifteen lines is that per-item budget --
# report-only, never a gate: an item narrating real delivered work
# legitimately runs long, and the board's own 1,000-line ceiling (below)
# already bounds the total.
ITEM_BUDGET = 15


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=True, encoding="utf-8",
        errors="replace",
    ).stdout


def _is_git_checkout(root: Path) -> bool:
    """True for a working tree git can query, false for an archived snapshot.

    The conformance scanner extracts a recorded revision with `git archive`
    and writes a `.git` marker file (`gitdir: archived <sha>`) so its
    provider gate admits the snapshot; that marker names no gitdir, so the
    snapshot is walked, never queried.
    """
    marker = root / ".git"
    if marker.is_dir():
        return True
    if not marker.is_file():
        return False
    text = marker.read_text(encoding="utf-8", errors="replace").strip()
    if not text.startswith("gitdir:"):
        return False
    target = text[len("gitdir:"):].strip()
    return (root / target).exists() or Path(target).exists()


def _line_count(text: str) -> int:
    return text.count("\n") + (0 if text.endswith("\n") or not text else 1)


def _exact_path(root: Path, relative: str) -> Path | None:
    """Match Git's case-sensitive names on case-insensitive filesystems too."""
    current = root
    for name in relative.split("/"):
        if not current.is_dir():
            return None
        match = next((entry for entry in current.iterdir() if entry.name == name), None)
        if match is None:
            return None
        current = match
    return current


def _item_file_paths(root: Path, ref: str | None) -> list[str]:
    """Relative paths of `backlog/*.md` at `ref` (or the working tree)."""
    if ref is None:
        item_dir = _exact_path(root, "backlog")
        if item_dir is None or not item_dir.is_dir():
            return []
        return [
            f"backlog/{p.name}" for p in sorted(item_dir.iterdir())
            if p.is_file() and p.suffix == ".md"
        ]
    try:
        listing = _git(root, "ls-tree", "-r", "--name-only", ref, "--", "backlog/")
    except subprocess.CalledProcessError:
        return []
    return [line for line in listing.splitlines() if line.endswith(".md")]


def _read_text(root: Path, relpath: str, ref: str | None) -> str:
    if ref is None:
        path = _exact_path(root, relpath)
        return (
            path.read_text(encoding="utf-8", errors="replace")
            if path is not None and path.is_file() else ""
        )
    try:
        return _git(root, "show", f"{ref}:{relpath}")
    except subprocess.CalledProcessError:
        return ""


def _board_paths(root: Path, ref: str | None = None) -> list[str]:
    """Tracked paths of this repository's boards, resolved by canonical name.

    A board is the file a repository tracks under a canonical `PM_FILES` name,
    whatever case it spells: `CHECKLIST.md` is the checklist board in the four
    members that spell it that way, and skipping it bounded nothing there.
    Paths are returned rather than one match per canonical name because a
    case-sensitive filesystem can legitimately hold two spellings, and each
    counts; on a case-insensitive filesystem the directory listing yields one
    entry either way, so no board is double counted.
    """
    canonical = {name.lower() for name in PM_FILES}
    if ref is None:
        if not root.is_dir():
            return []
        found = [
            entry.name for entry in root.iterdir()
            if entry.is_file() and entry.name.lower() in canonical
        ]
    else:
        try:
            listing = _git(root, "ls-tree", "--name-only", ref)
        except subprocess.CalledProcessError:
            return []
        found = [line for line in listing.splitlines() if line.lower() in canonical]
    return sorted(found)


def board_lines(root: Path, ref: str | None = None) -> dict[str, int]:
    """Line count per board present at `ref` (or in the tree when None),
    keyed by the path the repository tracks for it.

    `backlog.md`'s count folds in its per-item files under `backlog/`
    (`backlog/<anchor>.md`): the board-compaction migration moved item
    bodies there, so the 1,000-line board budget bounds the index plus its
    items together -- the same total a pre-migration single-file board
    would have carried, measured across the files it now spans.
    """
    counts: dict[str, int] = {}
    for relpath in _board_paths(root, ref):
        total = _line_count(_read_text(root, relpath, ref))
        if relpath.lower() == "backlog.md":
            for item_path in _item_file_paths(root, ref):
                total += _line_count(_read_text(root, item_path, ref))
        counts[relpath] = total
    return counts


def _ratchet_previous(counts: dict[str, int], name: str) -> int | None:
    """The base count for the board `name`, tolerating a case-only rename.

    Boards ratchet by canonical identity, so a repository that renamed
    `CHECKLIST.md` to `checklist.md` between `--base` and the pushed revision
    compares against the same board rather than reading as one that vanished.
    """
    if name in counts:
        return counts[name]
    lowered = name.lower()
    return next((n for path, n in counts.items() if path.lower() == lowered), None)


def oversized_item_files(
    root: Path, ref: str | None = None, item_budget: int = ITEM_BUDGET
) -> dict[str, int]:
    """Line count for every `backlog/*.md` item file over the per-item
    budget. Report-only: see `ITEM_BUDGET`."""
    result: dict[str, int] = {}
    for item_path in _item_file_paths(root, ref):
        n = _line_count(_read_text(root, item_path, ref))
        if n > item_budget:
            result[item_path] = n
    return result


def tracked_images(root: Path, ref: str | None = None) -> dict[str, int]:
    """Byte size per tracked image path at `ref`, or in the tree when None.

    A tree without `.git` is an archived snapshot of a revision (the
    conformance scanner scans those): every file in it is tracked by
    construction, so the walk is the listing.
    """
    sizes: dict[str, int] = {}
    if ref is not None or _is_git_checkout(root):
        target = ref or "HEAD"
        try:
            listing = _git(root, "ls-tree", "-r", "-l", "-z", target)
        except subprocess.CalledProcessError:
            return sizes
        for entry in listing.split("\0"):
            if not entry:
                continue
            meta, _, path = entry.partition("\t")
            fields = meta.split()
            if len(fields) < 4 or fields[1] != "blob":
                continue
            if Path(path).suffix.lower() in IMAGE_SUFFIXES:
                sizes[path] = int(fields[3])
        if ref is None:
            # The working tree may hold a modified or added image not yet
            # committed; measure what a commit would record.
            for path in list(sizes):
                live = root / path
                if live.is_file():
                    sizes[path] = live.stat().st_size
        return sizes
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if Path(name).suffix.lower() in IMAGE_SUFFIXES:
                full = Path(dirpath) / name
                sizes[full.relative_to(root).as_posix()] = full.stat().st_size
    return sizes


def counts(root: Path, line_budget: int = LINE_BUDGET,
           image_budget: int = IMAGE_BUDGET_BYTES,
           item_budget: int = ITEM_BUDGET) -> dict[str, int]:
    """The conformance classes for `root`."""
    over = sum(max(0, n - line_budget) for n in board_lines(root).values())
    big = sum(1 for size in tracked_images(root).values() if size > image_budget)
    items_over = len(oversized_item_files(root, item_budget=item_budget))
    return {
        "pm_lines_over_budget": over,
        "oversized_tracked_images": big,
        "items_over_budget": items_over,
    }


def evaluate(root: Path, base: str | None, line_budget: int = LINE_BUDGET,
             image_budget: int = IMAGE_BUDGET_BYTES,
             rev: str | None = None) -> tuple[list[str], list[str]]:
    """Return (failures, warnings) under ratchet-to-budget semantics.

    `rev` evaluates that revision's tree instead of the working tree: a
    pre-push hook judges the commit being pushed, and in a shared tree the
    working copy carries peers' uncommitted state the push does not.
    """
    failures: list[str] = []
    warnings: list[str] = []
    now = board_lines(root, rev)
    before = board_lines(root, base) if base else {}
    for name, lines in sorted(now.items()):
        if lines <= line_budget:
            continue
        overage = lines - line_budget
        previous = _ratchet_previous(before, name)
        if base is None:
            failures.append(
                f"{name}: {lines} lines, {overage} over the {line_budget}-line budget"
            )
        elif previous is None or lines > previous:
            failures.append(
                f"{name}: {lines} lines ({overage} over budget) and grew from "
                f"{previous if previous is not None else 'absent'} at {base}"
            )
        else:
            warnings.append(
                f"{name}: {lines} lines ({overage} over budget); held or shrank "
                f"from {previous} at {base} -- compact before it grows"
            )
    images_now = tracked_images(root, rev)
    images_before = tracked_images(root, base) if base else {}
    for path, size in sorted(images_now.items()):
        if size <= image_budget:
            continue
        kib = size // 1024
        if base is None or images_before.get(path) != size:
            failures.append(
                f"{path}: {kib} KiB tracked image over the {image_budget // 1024} KiB "
                "budget (evidence captures go in the PR body or run-output; a manual "
                "figure is lossless-optimized or downscaled in place)"
            )
        else:
            warnings.append(f"{path}: {kib} KiB tracked image over budget, unchanged")
    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", nargs="?", default="check", choices=["check", "report"])
    parser.add_argument("--root", type=Path, default=Path.cwd(),
                        help="repository root (default: current directory)")
    parser.add_argument("--base", metavar="REF",
                        help="revision to ratchet against; without it every overage fails")
    parser.add_argument("--rev", metavar="REF",
                        help="evaluate this revision's tree instead of the working tree")
    parser.add_argument("--line-budget", type=int, default=LINE_BUDGET)
    parser.add_argument("--image-budget-bytes", type=int, default=IMAGE_BUDGET_BYTES)
    parser.add_argument("--item-budget", type=int, default=ITEM_BUDGET)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"no such directory: {root}", file=sys.stderr)
        return 2
    if args.mode == "report":
        print(json.dumps(
            counts(root, args.line_budget, args.image_budget_bytes, args.item_budget)
        ))
        return 0
    failures, warnings = evaluate(root, args.base, args.line_budget,
                                  args.image_budget_bytes, rev=args.rev)
    for line in warnings:
        print(f"artifact-budget: WARN {line}")
    for line in failures:
        print(f"artifact-budget: FAIL {line}")
    # Per-item-file report: visibility only, never a gate (ITEM_BUDGET).
    oversized_items = oversized_item_files(root, args.rev, args.item_budget)
    if oversized_items:
        print(
            f"artifact-budget: INFO {len(oversized_items)} item file(s) over the "
            f"{args.item_budget}-line per-item budget:"
        )
        for path, lines in sorted(oversized_items.items()):
            print(f"  {path}: {lines} lines")
    if failures:
        sys.stdout.flush()
        print(
            "artifact-budget: boards compact with scripts/atlas-board-compact.py "
            "(done items delete; open items stay under their per-item budget); "
            "oversized images leave git.",
            file=sys.stderr,
        )
        return 1
    if not warnings:
        print("artifact-budget: boards and tracked images within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
