#!/usr/bin/env python3
"""Audit commit hashes cited by completed Atlas board items.

The report is advisory. A rebased or squash-merged commit is expected not to
be an ancestor by identity, so the tool reports both ancestry and a
same-subject match on the owning provider's default branch. It never edits a
repository, board, branch, or pull request.

Usage::

    python scripts/atlas-board-delivery-audit.py --format json

Exit status is zero for a completed report, one when an auditable hash is not
an ancestor of its provider's fetched default branch (including benign
rewritten delivery), and two for an invocation or repository-read error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HEADING = re.compile(
    r"^##\s+(?P<item_id>[A-Za-z][A-Za-z0-9-]*)\s+—\s+(?P<rest>.+?)\s*$"
)
HASH = re.compile(r"(?<![A-Za-z0-9])(?P<hash>[0-9a-f]{7,40})(?![A-Za-z0-9])", re.I)
REPO_PATH = re.compile(r"(?:repos|worktrees)/(?P<repo>[A-Za-z0-9_-]+)", re.I)
URL_REPO = re.compile(r"github\.com/ryancinsight/(?P<repo>[A-Za-z0-9_-]+)", re.I)
SUBMODULE_PATH = re.compile(
    r"^\s*path\s*=\s*repos/(?P<repo>[A-Za-z0-9_-]+)\s*$", re.I | re.M
)
DONE_STATUS = ("done", "closed", "complete", "merged")
ALIASES = {
    "CFDRS": "CFDrs",
    "HERMES": "hermes",
    "EUNOMIA": "eunomia",
    "MOIRAI": "moirai",
    "MNEMOSYNE": "mnemosyne",
    "HEPHAESTUS": "hephaestus",
    "KWAVERS": "kwavers",
    "CONSUS": "consus",
    "PROTEUS": "proteus",
    "HORAE": "horae",
    "HYPERION": "hyperion",
    "THEMIS": "themis",
    "TYCHE": "tyche",
    "AEQUITAS": "aequitas",
    "ASCLEPIUS": "asclepius",
    "APOLLO": "apollo",
    "IRIS": "iris",
    "LETO": "leto",
    "MELINOE": "melinoe",
    "RITK": "ritk",
    "COEUS": "coeus",
    "ATHENA": "athena",
    "GAIA": "gaia",
}


@dataclass(frozen=True)
class BoardItem:
    """A completed board item and its body."""

    item_id: str
    title: str
    status: str
    body: str

    @property
    def text(self) -> str:
        """Return the heading and body for citation extraction."""
        return f"{self.item_id} {self.title}\n{self.body}"

    @property
    def hashes(self) -> tuple[str, ...]:
        """Return unique hexadecimal commit-looking citations."""
        values: list[str] = []
        for match in HASH.finditer(self.text):
            value = match.group("hash").lower()
            # Numeric run IDs and dates are not commit citations. A commit
            # consisting only of digits is valid Git, but too ambiguous for
            # this advisory sweep and must be supplied by a future manifest.
            if not re.search(r"[a-f]", value) or value in values:
                continue
            values.append(value)
        return tuple(values)

    @property
    def normalized_status(self) -> str:
        """Return the status prefix without release annotations."""
        return self.status.casefold().strip()


def parse_board(text: str) -> list[BoardItem]:
    """Parse level-two board items without interpreting prose outside them."""
    items: list[BoardItem] = []
    current: tuple[str, str, str, list[str]] | None = None
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            if current is not None:
                item_id, title, status, body = current
                items.append(BoardItem(item_id, title, status, "\n".join(body)))
            rest = match.group("rest")
            if " — " in rest:
                title, status = rest.rsplit(" — ", 1)
            else:
                title, status = rest, ""
            current = [match.group("item_id"), title.strip(), status.strip(), []]
        elif current is not None:
            current[3].append(line)
    if current is not None:
        item_id, title, status, body = current
        items.append(BoardItem(item_id, title, status, "\n".join(body)))
    return items


def completed_items(items: list[BoardItem]) -> list[BoardItem]:
    """Select completed items while excluding open and in-progress rows."""
    return [
        item
        for item in items
        if item.normalized_status.startswith(DONE_STATUS) and item.hashes
    ]


def member_paths(root: Path) -> dict[str, Path]:
    """Return registered provider directories keyed case-insensitively."""
    members: dict[str, Path] = {}
    gitmodules = root / ".gitmodules"
    if not gitmodules.is_file():
        return members
    repos = root / "repos"
    if not repos.is_dir():
        return members
    registered = {
        match.group("repo").casefold()
        for match in SUBMODULE_PATH.finditer(gitmodules.read_text(encoding="utf-8"))
    }
    for name in registered:
        path = repos / name
        if path.is_dir() and (path / ".git").exists():
            members[name] = path
    return members


def candidate_names(item: BoardItem, members: dict[str, Path]) -> set[str]:
    """Infer provider candidates from explicit paths, URLs, and item IDs."""
    candidates: set[str] = set()
    for pattern in (REPO_PATH, URL_REPO):
        candidates.update(
            match.group("repo").casefold()
            for match in pattern.finditer(item.text)
            if match.group("repo").casefold() in members
        )
    upper_id = item.item_id.upper()
    for alias, name in ALIASES.items():
        if re.search(rf"(?:^|-){re.escape(alias)}(?:-|$)", upper_id):
            if name.casefold() in members:
                candidates.add(name.casefold())
    return candidates


def run_git(repo: Path, args: list[str], *, input_text: str = "") -> tuple[int, str]:
    """Run a read-only Git query with a bounded timeout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, str(error)
    return result.returncode, (result.stdout or "").strip()


def commit_presence(repo: Path, hashes: list[str]) -> set[str]:
    """Resolve commit objects in one repository with one batch query."""
    if not hashes:
        return set()
    query = "\n".join(hashes) + "\n"
    code, output = run_git(repo, ["cat-file", "--batch-check"], input_text=query)
    if code != 0:
        return set()
    present: set[str] = set()
    for requested, line in zip(hashes, output.splitlines(), strict=False):
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "commit":
            present.add(requested)
    return present


def commit_subject(repo: Path, commit: str) -> str:
    """Return one commit subject."""
    code, subject = run_git(repo, ["show", "-s", "--format=%s", commit])
    return subject if code == 0 else ""


def default_subjects(repo: Path, default_ref: str) -> dict[str, list[str]]:
    """Index default-branch subjects once per provider."""
    code, output = run_git(
        repo,
        [
            "log",
            default_ref,
            "--format=%H%x00%s",
        ],
    )
    if code != 0:
        return {}
    subjects: dict[str, list[str]] = {}
    for line in output.splitlines():
        commit_hash, separator, found_subject = line.partition("\x00")
        if separator:
            subjects.setdefault(found_subject, []).append(commit_hash)
    return subjects


def default_ref(repo: Path) -> str | None:
    """Resolve the fetched default branch without assuming its name."""
    code, symbolic = run_git(
        repo,
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
    )
    if code == 0 and symbolic.startswith("origin/"):
        return symbolic
    for candidate in ("origin/main", "origin/master"):
        code, _ = run_git(repo, ["rev-parse", "--verify", f"{candidate}^{{commit}}"])
        if code == 0:
            return candidate
    return None


def branch_context(repo: Path, commit: str) -> list[str]:
    """Return remote branches containing the cited commit."""
    code, output = run_git(
        repo,
        [
            "for-each-ref",
            "--contains",
            commit,
            "--format=%(refname:short)",
            "refs/remotes/origin",
        ],
    )
    return output.splitlines() if code == 0 and output else []


def classify(
    *,
    ancestor: bool | None,
    rewritten: bool,
    remote_branches: list[str],
) -> str:
    """Classify delivery without treating ancestry as the sole oracle."""
    if ancestor is None:
        return "unverifiable"
    if ancestor:
        return "delivered"
    if rewritten:
        return "delivered-rewritten"
    if remote_branches:
        return "published-not-merged"
    return "undelivered"


def audit(root: Path, board: Path) -> dict[str, Any]:
    """Run the report-only audit and return JSON-compatible evidence."""
    members = member_paths(root)
    items = completed_items(parse_board(board.read_text(encoding="utf-8")))
    hash_items: dict[str, list[BoardItem]] = {}
    for item in items:
        for commit in item.hashes:
            hash_items.setdefault(commit, []).append(item)

    hash_candidates = {
        commit: set().union(
            *(candidate_names(item, members) for item in owners)
        )
        for commit, owners in hash_items.items()
    }
    required_members = set().union(*hash_candidates.values()) if hash_candidates else set()
    presence = {
        name: commit_presence(members[name], list(hash_items))
        for name in required_members
    }
    default_refs = {name: default_ref(members[name]) for name in required_members}
    subject_indexes = {
        name: default_subjects(members[name], ref)
        for name, ref in default_refs.items()
        if ref is not None
    }
    records: list[dict[str, Any]] = []
    for commit, owners in hash_items.items():
        candidate_sets = [candidate_names(item, members) for item in owners]
        candidates = set().union(*candidate_sets) if candidate_sets else set()
        if not candidates:
            records.append(
                {
                    "hash": commit,
                    "items": [item.item_id for item in owners],
                    "candidates": [],
                    "owners": [],
                    "verdict": "unresolved-owner",
                }
            )
            continue
        found = [name for name in candidates if commit in presence.get(name, set())]
        if len(found) != 1:
            records.append(
                {
                    "hash": commit,
                    "items": [item.item_id for item in owners],
                    "candidates": sorted(candidates),
                    "owners": sorted(found),
                    "verdict": "ambiguous-owner" if len(found) > 1 else "unresolved-owner",
                }
            )
            continue
        owner = found[0]
        repo = members[owner]
        ref = default_refs.get(owner)
        if ref is None:
            ancestor = None
        else:
            ancestor_code, _ = run_git(repo, ["merge-base", "--is-ancestor", commit, ref])
            ancestor = True if ancestor_code == 0 else False if ancestor_code == 1 else None
        subject = commit_subject(repo, commit)
        rewritten_hashes = [
            candidate
            for candidate in subject_indexes.get(owner, {}).get(subject, [])
            if candidate != commit
        ]
        rewritten = bool(rewritten_hashes)
        branches = branch_context(repo, commit) if ancestor is False else []
        records.append(
            {
                "hash": commit,
                "items": [item.item_id for item in owners],
                "candidates": sorted(candidates),
                "owner": owner,
                "default_ref": ref,
                "ancestor_of_default": ancestor,
                "remote_branches": branches,
                "same_subject_on_default": [
                    {"hash": candidate, "subject": subject}
                    for candidate in rewritten_hashes
                ],
                "verdict": classify(
                    ancestor=ancestor,
                    rewritten=rewritten,
                    remote_branches=branches,
                ),
            }
        )
    non_ancestor = [
        record
        for record in records
        if record.get("ancestor_of_default") is False
    ]
    unresolved_owner = [
        record for record in records if record["verdict"] == "unresolved-owner"
    ]
    return {
        "board": str(board),
        "completed_items": len(items),
        "cited_hashes": len(hash_items),
        "auditable_hashes": len(records) - len(unresolved_owner),
        "unresolved_owner_hashes": len(unresolved_owner),
        "non_ancestor_flags": len(non_ancestor),
        "genuine_undelivered": sum(record["verdict"] == "undelivered" for record in records),
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the bounded audit and render text or JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--board", type=Path, default=None)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    board = (args.board or root / "backlog.md").resolve()
    if not board.is_file():
        print(f"board not found: {board}", file=sys.stderr)
        return 2
    try:
        report = audit(root, board)
    except (OSError, UnicodeError) as error:
        print(f"audit failed: {error}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "Delivery audit: "
            f"{report['cited_hashes']} cited hashes "
            f"({report['auditable_hashes']} auditable), "
            f"{report['non_ancestor_flags']} non-ancestor flags, "
            f"{report['genuine_undelivered']} undelivered"
        )
        counts: dict[str, int] = {}
        for record in report["records"]:
            counts[record["verdict"]] = counts.get(record["verdict"], 0) + 1
        print("Verdicts: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
        flags = [
            record
            for record in report["records"]
            if record["verdict"] not in {"delivered", "delivered-rewritten"}
        ]
        for record in flags[:20]:
            print(json.dumps(record, sort_keys=True))
        if len(flags) > 20:
            print(f"... {len(flags) - 20} additional records available with --format json")
    return 1 if report["non_ancestor_flags"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
