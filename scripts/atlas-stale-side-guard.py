#!/usr/bin/env python3
"""Reject changed files that reproduce their own historical content."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import atlas_git_process as process
import atlas_stale_side_basis as basis
import atlas_stale_side_git as git

ROOT = Path(__file__).resolve().parent.parent
WAIVERS = Path(__file__).resolve().parent / "stale-side-waivers.json"


def load_waivers(path: Path) -> tuple[dict[str, dict], list[str]]:
    if not path.is_file():
        return {}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {}, [f"{path}: unreadable ({exc})"]
    if not isinstance(data, dict) or not isinstance(data.get("waivers"), list):
        return {}, [f"{path}: root must contain a `waivers` list"]
    waivers: dict[str, dict] = {}
    problems = []
    for entry in data["waivers"]:
        target = entry.get("path") if isinstance(entry, dict) else None
        reason = entry.get("reason") if isinstance(entry, dict) else None
        blob = entry.get("blob") if isinstance(entry, dict) else None
        valid_blob = blob is None or (
            isinstance(blob, str)
            and len(blob) in {40, 64}
            and all(character in "0123456789abcdef" for character in blob)
        )
        if (
            not isinstance(target, str)
            or not target
            or not isinstance(reason, str)
            or not reason.strip()
            or not valid_blob
        ):
            problems.append(
                f"{path}: waiver needs string `path` and `reason`, with an optional "
                f"object-id `blob`: {entry!r}"
            )
            continue
        waivers[target] = entry
    return waivers, problems


def waiver_explains(waiver: dict, finding: git.Finding) -> bool:
    pinned = waiver.get("blob")
    return not pinned or pinned == finding.blob


def report_findings(
    repo: Path, findings: list[git.Finding], waivers: dict[str, dict]
) -> tuple[int, int]:
    unexplained = waived = 0
    for finding in findings:
        waiver = waivers.get(finding.path)
        if waiver is not None and waiver_explains(waiver, finding):
            waived += 1
            print(f"waived: {finding.path} [{finding.source}]")
            print(f"        {waiver['reason']}")
            continue
        unexplained += 1
        where = (
            "not an ancestor of HEAD (another ref)"
            if finding.ancestor is False
            else "an ancestor of HEAD"
        )
        print(f"STALE SIDE: {finding.path} [{finding.source}]")
        print(
            f"        content {finding.blob[:10]} is byte-identical to "
            f"{finding.revision.commit[:10]} "
            f"({git.revision_subject(repo, finding.revision.commit)}),"
        )
        print(
            f"        {where} -- {finding.revision.count} revision(s) carry this content."
        )
        if finding.materializes:
            print(f"        Still materializable from: {', '.join(finding.materializes)}")
        print(f"        Reconcile it: git diff HEAD -- {finding.path}")
    return unexplained, waived


def cmd_check(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    waivers, problems = load_waivers(Path(args.waivers))
    for problem in problems:
        print(f"WAIVER PROBLEM: {problem}")
    findings = git.collect(repo, args.staged, args.sources, args.all_refs)
    unexplained, waived = report_findings(repo, findings, waivers)
    matched = {finding.path for finding in findings}
    for path in sorted(set(waivers) - matched):
        print(f"note: waiver for {path} explains nothing in this checkout")
    if problems or unexplained:
        print(
            f"\natlas-stale-side-guard: FAIL - {unexplained} stale side(s)"
            f"{f', {waived} waived' if waived else ''}"
        )
        print(
            "Restore stale content from HEAD, or record the intended revert with a "
            f"reason in {args.waivers}."
        )
        return 1
    print(f"atlas-stale-side-guard: OK - {len(findings)} match(es), none unexplained")
    return 0


def explain(
    repo: Path,
    path: str,
    blob: str,
    head: str | None,
    all_refs: bool,
    waivers: dict[str, dict],
) -> tuple[str, bool]:
    if blob == head:
        return "unchanged content", False
    if blob not in git.existing_blobs(repo, {blob}):
        return "new content", False
    revision = git.historical_blobs(repo, {path: {blob}}, all_refs).get(path, {}).get(blob)
    if revision is None:
        return "new content", False
    finding = git.Finding(path, "", blob, revision, None)
    waiver = waivers.get(path)
    if waiver is not None and waiver_explains(waiver, finding):
        return f"STALE SIDE (waived): {waiver['reason']}", False
    return (
        f"STALE SIDE: matches {revision.commit[:10]} "
        f"({revision.count} revision(s)): {git.revision_subject(repo, revision.commit)}",
        True,
    )


def cmd_status(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    waivers, problems = load_waivers(Path(args.waivers))
    for problem in problems:
        print(f"WAIVER PROBLEM: {problem}")
    paths = git.changed_paths(repo, args.staged)
    entries = git.index_entries(repo)
    heads = git.head_blobs(repo)
    worktree = git.worktree_blobs(repo, paths) if "worktree" in args.sources else {}
    print(f"{'path':<56} {'source':<9} {'content':<11} verdict")
    unexplained = waived = 0
    used: set[str] = set()
    for path in paths:
        entry = entries.get(path)
        if entry is None or entry[0] not in git.FILE_MODES:
            print(f"{path:<56} {'-':<9} {'-':<11} skipped (no file content)")
            continue
        rows = [("index", entry[1])] if "index" in args.sources else []
        if path in worktree:
            rows.append(("worktree", worktree[path]))
        if not rows:
            print(f"{path:<56} {'-':<9} {'-':<11} unchanged")
        for source, blob in rows:
            verdict, is_finding = explain(
                repo, path, blob, heads.get(path), args.all_refs, waivers
            )
            unexplained += int(is_finding)
            if verdict.startswith("STALE SIDE (waived)"):
                waived += 1
                used.add(path)
            print(f"{path:<56} {source:<9} {blob[:10]:<11} {verdict}")
    for path in sorted(set(waivers) - used):
        print(f"note: waiver for {path} explains nothing in this checkout")
    print(
        f"\n{len(paths)} changed path(s): {unexplained} unexplained stale side(s), "
        f"{waived} waived"
    )
    return 1 if problems else 0


def cmd_basis(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    waivers, problems = load_waivers(Path(args.waivers))
    for problem in problems:
        print(f"WAIVER PROBLEM: {problem}")
    print(f"basis: {basis.head_basis(repo)}")
    branches = basis.ancestor_branches(repo)
    if branches:
        print("branches behind HEAD:")
        for ref, changed in branches:
            print(f"    {ref}  ({changed} path(s) differ)")
    else:
        print("branches behind HEAD: none")
    indexes = basis.inspect_indexes(repo)
    if not indexes:
        print("unused alternate indexes: none")
    unexplained = waived = 0
    for item in indexes:
        key = f".git/{item.path.name}"
        waiver = waivers.get(key)
        if waiver is not None:
            waived += 1
            print(f"waived: {key}")
            print(f"        {waiver['reason']}")
            continue
        unexplained += 1
        print(f"STALE BASIS: {key}")
        print(
            f"        unused index records {item.total} path(s); "
            f"{item.differing} currently disagree with HEAD"
        )
        if item.examples:
            print(f"        for instance: {', '.join(item.examples)}")
        print(f"        Inspect staged content with GIT_INDEX_FILE={item.path} git diff --cached")
        print("        Reconcile or remove the index after preserving unique work")
    matched = {f".git/{item.path.name}" for item in indexes}
    for path in sorted(set(waivers) - matched):
        print(f"note: waiver for {path} explains nothing in this checkout")
    if problems or unexplained:
        print(
            f"\natlas-stale-side-guard: FAIL - {unexplained} materializable stale "
            f"basis(es){f', {waived} waived' if waived else ''}"
        )
        return 1
    print(
        "atlas-stale-side-guard: OK - no materializable stale basis "
        f"({len(indexes)} alternate index file(s) found)"
    )
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "basis", "status"))
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--worktree", action="store_true")
    parser.add_argument("--all-refs", action="store_true")
    parser.add_argument("--waivers", default=str(WAIVERS))
    args = parser.parse_args(argv)
    if args.staged and args.worktree:
        parser.error("--staged and --worktree are mutually exclusive")
    args.sources = ("index",) if args.staged else ("worktree",)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repo = Path(args.repo).resolve()
        git.run(repo, "rev-parse", "--verify", "HEAD")
        if args.mode == "check":
            return cmd_check(args)
        if args.mode == "basis":
            return cmd_basis(args)
        return cmd_status(args)
    except (process.GitProcessError, OSError, UnicodeError, ValueError) as exc:
        print(f"atlas-stale-side-guard: ERROR - {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
