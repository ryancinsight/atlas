#!/usr/bin/env python3
"""Worktree-lane and copy audit: the mechanical form of the lane rules.

AGENTS.md `git_discipline` (Worktrees) bounds every repository to its main
tree plus at most one linked lane, requires lanes to live under a canonical
lane root on a named branch, and prohibits standalone clones and hand-wired
gitdir mirrors (`concurrent_agents`: copy reconciliation). Until now those
rules were enforced only by agent memory during orient; this script is the
audit orient and the replenishment cycle run.

Checks, per registered member and the meta repository:
  1. `git worktree list` reports at most two trees (main + one lane).
  2. Every linked lane lives under a canonical lane root — the project-root
     `worktrees/` directory or a harness-managed `.claude/worktrees/` — and
     sits on a named branch, never detached HEAD.
  3. `git worktree prune --dry-run` reports nothing (no rotted lane refs).
Plus, for the canonical `worktrees/` root itself:
  4. A child with a `.git` directory is a standalone clone (prohibited copy).
  5. A child with a `.git` file must be a registered linked worktree of some
     member (its gitdir resolves under `<repo>/.git/worktrees/`); anything
     else is a hand-wired gitdir mirror sharing an index it must not share.

Exit is nonzero on any violation so orient can gate on it. Read-only: the
audit names violations for reconciliation (rescue-first) — it never deletes.

Run: `python scripts/atlas-lane-audit.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import (
    LANE_ROOT, ROOT, canonical_lane, git, registered_members, worktree_entries,
)
from atlas_target_dir import (
    MARKER,
    lane_config,
    lane_config_text,
    lane_legacy_config,
    target_dir_override_paths,
)

ARCHIVE_ROOT_NAME = ".archive"


def audit_target_config(violations: list[str]) -> None:
    """Ensure the shared config inherited by lanes is present and current."""
    path = lane_config(ROOT)
    if not path.is_file():
        violations.append(f"lane target config missing: {path}")
    else:
        text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        if MARKER not in text:
            violations.append(f"lane target config is foreign: {path}")
        elif text != lane_config_text(ROOT):
            violations.append(f"lane target config is stale: {path}")
    legacy = lane_legacy_config(ROOT)
    if legacy.is_file():
        violations.append(f"lane target config override: {legacy}")


def audit_lane_target_config(lane: Path, violations: list[str]) -> None:
    """Reject target-dir declarations closer to Cargo than the shared config."""
    for path in target_dir_override_paths(lane):
        violations.append(f"lane target config override: {path}")


def audit_repo(repo: Path, violations: list[str]) -> None:
    entries = worktree_entries(repo)
    if len(entries) > 2:
        violations.append(
            f"{repo.name}: {len(entries)} working trees (bound is main + one lane)"
        )
    for entry in entries[1:]:
        lane = Path(entry.get("worktree", ""))
        if "detached" in entry:
            violations.append(f"{repo.name}: lane {lane} is detached HEAD")
        if lane and not canonical_lane(lane):
            violations.append(f"{repo.name}: lane {lane} outside canonical lane roots")
        if lane:
            audit_lane_target_config(lane, violations)
    prunable = git(repo, "worktree", "prune", "--dry-run", "-v").strip()
    if prunable:
        violations.append(
            f"{repo.name}: rotted lane refs (run `git worktree prune`): "
            f"{prunable.splitlines()[0]}"
        )


def audit_lane_root(violations: list[str]) -> None:
    if not LANE_ROOT.is_dir():
        return
    for child in sorted(LANE_ROOT.iterdir()):
        if not child.is_dir():
            continue
        if child.name == ".cargo":
            # The generated shared target config is inherited by every lane;
            # it is machine state, not a worktree child.
            continue
        if child.name == ARCHIVE_ROOT_NAME:
            # Archived lane manifests are reconciliation records, not
            # worktrees.  They deliberately have no .git marker.
            continue
        marker = child / ".git"
        if marker.is_dir():
            violations.append(
                f"worktrees/{child.name}: standalone clone (prohibited copy -- "
                "rescue-commit, fetch unique refs, delete)"
            )
        elif marker.is_file():
            gitdir = marker.read_text(errors="replace").partition("gitdir:")[2].strip()
            normalized = gitdir.replace("\\", "/")
            # A registered linked worktree resolves under .../worktrees/<lane>
            # (for submodule members: .git/modules/<path>/worktrees/<lane>).
            # A gitdir pointing at a repo's primary gitdir shares its index.
            if "/worktrees/" not in normalized:
                violations.append(
                    f"worktrees/{child.name}: hand-wired gitdir mirror "
                    f"({gitdir or 'unreadable'}) -- shares an index it must not share"
                )
        else:
            # Empty placeholders can remain after interrupted cleanup; they are
            # inert and do not share repository state.
            try:
                has_entries = any(child.iterdir())
            except OSError:
                has_entries = True
            if has_entries:
                violations.append(f"worktrees/{child.name}: not a linked worktree")


def main() -> int:
    violations: list[str] = []
    audit_target_config(violations)
    for repo in [ROOT, *registered_members()]:
        audit_repo(repo, violations)
    audit_lane_root(violations)
    if violations:
        for v in violations:
            print(f"LANE VIOLATION: {v}")
        print(f"{len(violations)} violation(s)")
        return 1
    print("lane audit clean: every repo within the two-tree bound, "
          "lanes canonical and named, no clones or mirrors in the lane root")
    return 0


if __name__ == "__main__":
    sys.exit(main())
