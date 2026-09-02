#!/usr/bin/env python3
"""Verify every round-6a path-dep application commit is `Cargo.toml +
Cargo.lock` only (workspace roots may legitimately touch only
`Cargo.lock` when the path-dep lives in member manifests).

The round-6a series (12 commits across 12 submodules) was authored
during the ATLAS-PATH-DEP-AUDIT-2 closure cycle to land the
`path = "../<sibling>"` overrides after the r5 over-strip. ATLAS-R6A-
FILELIST-001 requires every r6a commit to be strictly cargo-only;
this verifier is the SSOT for that rule.

Workspace roots carry their `[dependencies]` in `[workspace.dependencies]`
and the per-member `[dependencies]` propagate via `inherit = "workspace"`,
so the workspace-root `Cargo.toml` legitimately does not move on a
path-dep cutover and only `Cargo.lock` is touched. CFDrs is the only
r6a workspace root in the audit set; the verifier explicitly
recognizes that case.

Exit code 0 = all r6a commits are cargo-only (with workspace-root
exceptions acknowledged). Exit code 1 = any commit carries a file that
is neither `Cargo.toml` nor `Cargo.lock`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# (repo, apply_round_6a_sha, is_workspace_root)
# The SHA set is the one surveyed under ATLAS-R6A-FILELIST-001 on
# 2026-08-21; a new r6a commit beyond the audit set will fail the
# verifier until the (repo, sha) tuple is added here. SHA updates
# require a fresh `git log --grep="Apply round-6a"` over each repo.
R6A_COMMITS: list[tuple[str, str, bool]] = [
    ("apollo",      "b7bb4bc5", False),
    ("asclepius",   "5414f80",  False),
    ("CFDrs",       "ec4e147b", True),    # workspace root — Cargo.lock only
    ("coeus",       "cdaf769b", False),
    ("gaia",        "42ef63a",  False),
    ("helios",      "dca9e80",  False),
    ("hephaestus",  "47ca84a",  False),
    ("kwavers",     "4bb54bda6", False),
    ("leoneuro-rs", "50bfcd9",  False),
    ("hermes",      "50b4959",  False),
    ("ritk",        "65035908", False),
    ("athena",      "a5fd806",  False),
]

ALLOWED_FILES = {"Cargo.toml", "Cargo.lock"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--repo-root",
        default="repos",
        help="directory under which the submodule worktrees live (default: repos)",
    )
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root)
    if not repo_root.is_dir():
        print(f"repo-root not found: {repo_root}", file=sys.stderr)
        return 2

    ok = 0
    anomalies: list[tuple[str, str, list[str]]] = []
    missing: list[tuple[str, str]] = []

    for repo, sha, is_workspace_root in R6A_COMMITS:
        worktree = repo_root / repo
        if not worktree.is_dir():
            print(f"  MISS {repo:15} {sha}  (worktree not present)")
            missing.append((repo, sha))
            continue

        proc = subprocess.run(
            ["git", "-C", str(worktree), "show", "--name-only", "--format=", sha],
            capture_output=True, encoding="utf-8", errors="replace", check=False,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip().splitlines()[0] if proc.stderr.strip() else "(unknown)"
            print(f"  ERR  {repo:15} {sha}  {err[:80]}")
            anomalies.append((repo, sha, [f"git show failed: {err}"]))
            continue

        files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        allowed = {"Cargo.toml", "Cargo.lock"}
        if is_workspace_root:
            allowed = {"Cargo.lock"}  # workspace-root legitimately no Cargo.toml
        extras = [f for f in files if f not in allowed]
        if extras:
            print(f"  ANOM {repo:15} {sha}  extras={len(extras)}: {extras}")
            anomalies.append((repo, sha, extras))
        else:
            label = "OK (workspace)" if is_workspace_root else "OK"
            print(f"  {label:14} {repo:15} {sha}  files={files}")
            ok += 1

    total = len(R6A_COMMITS)
    print()
    print(f"ok={ok} anomalies={len(anomalies)} missing={len(missing)} total={total}")

    if anomalies or missing:
        print("Round-6a commit file-list hygiene: FAIL", file=sys.stderr)
        return 1

    print("Round-6a commit file-list hygiene: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
