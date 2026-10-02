"""Open a pull request and enable auto-merge on it: the one PR-opening path of the sweep tools.

Merging is enabling auto-merge: a PR left for hand collection is a change that
sits unmerged. Every tool that opens a PR (`atlas-lock-sweep.py`,
`atlas-semver-gate-adopt.py`, `atlas-workflow-concurrency-sweep.py`) goes
through `open_pull_request`, so the merge method is stated once: an explicit
`--merge`, never the squash default, which collapses the atomic history.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

STDERR_TAIL_CHARACTERS = 200


@dataclass(frozen=True)
class PullRequestOpening:
    """What opening a pull request did: its URL, and why it is not delivered if it is not.

    `failure` is None when the PR exists with auto-merge enabled. When creation
    failed `url` is None; when only enabling auto-merge failed `url` names the
    PR that now needs collecting."""

    url: str | None
    failure: str | None

    @property
    def delivered(self) -> bool:
        return self.failure is None


def stderr_tail(completed: subprocess.CompletedProcess[str]) -> str:
    return completed.stderr.strip()[-STDERR_TAIL_CHARACTERS:]


def open_pull_request(
    *,
    base: str,
    head: str,
    title: str,
    body: str,
    repo: str | None = None,
    cwd: Path | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> PullRequestOpening:
    """`gh pr create`, then `gh pr merge <url> --auto --merge --delete-branch`.

    `repo` is the `owner/name` slug for a tool with no checkout of the target
    (`-R`); `cwd` is the checkout a tool opens the PR from. A failed enable is
    a failure carrying the stderr tail and the PR URL, so a report shows a PR
    that needs collecting rather than a delivered one."""
    target = ["-R", repo] if repo is not None else []
    created = run(
        ["gh", "pr", "create", *target, "--base", base, "--head", head, "--title", title, "--body", body],
        cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
    )
    if created.returncode != 0:
        return PullRequestOpening(None, f"gh pr create: {stderr_tail(created)}")
    url = created.stdout.strip().splitlines()[-1]
    merge = run(
        ["gh", "pr", "merge", url, "--auto", "--merge", "--delete-branch"],
        cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
    )
    if merge.returncode != 0:
        return PullRequestOpening(url, f"gh pr merge --auto: {stderr_tail(merge)} (PR {url})")
    return PullRequestOpening(url, None)
