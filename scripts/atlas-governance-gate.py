#!/usr/bin/env python3
"""Atlas governance gate for registered member repos.

This is a static guardrail for the higher-level Atlas repository health rules:

- every registered member repo has an explicit Rust toolchain pin
- every member repo has a GitHub workflow directory
- each workflow `uses:` reference is either a local path action, a Docker image,
  or a full 40-character commit SHA

The script is intentionally read-only and designed to work in CI or in local
preflight checks without needing a live GitHub API call.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import registered_members  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def _workflow_files(repo: Path) -> list[Path]:
    workflows = repo / ".github" / "workflows"
    if not workflows.is_dir():
        return []
    return sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml"))


def _workflow_action_issues(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = re.search(r"^\s*(?:-\s*)?uses:\s*(.+?)\s*$", line)
        if not match:
            continue
        ref = match.group(1).strip()
        ref = ref.split("#", 1)[0].strip()
        if not ref:
            continue
        if ref.startswith("./") or ref.startswith("docker://"):
            continue
        if ".github/actions" in ref:
            continue
        if ref.startswith("rustup"):
            continue
        if "@" not in ref:
            issues.append(f"{path}:{lineno}: workflow action is missing an @ref: {ref}")
            continue
        _, sha_ref = ref.rsplit("@", 1)
        if not SHA_RE.fullmatch(sha_ref):
            issues.append(
                f"{path}:{lineno}: workflow action must be pinned to a full 40-char SHA: {ref}"
            )
    return issues


def _member_issues() -> list[str]:
    issues: list[str] = []
    for repo in registered_members():
        if not (repo / "Cargo.toml").is_file():
            issues.append(f"{repo}: missing Cargo.toml")
        if not (repo / "rust-toolchain.toml").is_file():
            issues.append(f"{repo}: missing rust-toolchain.toml")
        workflows = _workflow_files(repo)
        if not workflows:
            issues.append(f"{repo}: missing .github/workflows/*.yml")
        for workflow in workflows:
            issues.extend(_workflow_action_issues(workflow))
    return issues


def main() -> int:
    issues = _member_issues()
    if issues:
        print("atlas-governance-gate: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("atlas-governance-gate: OK - registered members are pinned, workflowed, and SHA-gated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
