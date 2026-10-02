#!/usr/bin/env python3
"""Tests for atlas_pull_request.py, the one PR-opening path of the sweep tools.

A PR the sweep opens must have auto-merge enabled with an explicit `--merge`
(never the squash default), and a PR whose auto-merge could not be enabled must
read as a failure carrying its URL: a delivered-looking row for a PR nobody
will collect is the defect this module exists to prevent.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from atlas_pull_request import PullRequestOpening, open_pull_request  # noqa: E402

NL = chr(10)
URL = "https://github.com/ryancinsight/leto/pull/7"


def scripted_runner(create: tuple[int, str, str], merge: tuple[int, str, str]):
    """A `subprocess.run` stand-in answering `gh pr create` and `gh pr merge` from the script."""
    calls: list[tuple[list[str], Path | None]] = []

    def run(argv, cwd=None, **_options):
        calls.append((argv, cwd))
        code, out, err = create if argv[:3] == ["gh", "pr", "create"] else merge
        return subprocess.CompletedProcess(argv, code, out, err)

    return run, calls


class OpenPullRequestTests(unittest.TestCase):
    lane = Path("worktrees/leto-lock-sweep")

    def open(self, run, **where):
        return open_pull_request(
            base="main", head="build/hermes-simd-6da6d139", title="build(deps): t", body="body", run=run, **where
        )

    def test_auto_merge_is_enabled_on_the_created_pr_with_an_explicit_merge_method(self) -> None:
        run, calls = scripted_runner((0, f"warning: x{NL}{URL}{NL}", ""), (0, "", ""))
        opening = self.open(run, cwd=self.lane)
        self.assertEqual(
            calls[0][0],
            ["gh", "pr", "create", "--base", "main", "--head", "build/hermes-simd-6da6d139",
             "--title", "build(deps): t", "--body", "body"],
        )
        self.assertEqual(calls[1][0], ["gh", "pr", "merge", URL, "--auto", "--merge", "--delete-branch"])
        self.assertEqual(len(calls), 2)
        self.assertEqual([cwd for _, cwd in calls], [self.lane, self.lane])
        self.assertEqual(opening, PullRequestOpening(URL, None))
        self.assertTrue(opening.delivered)

    def test_a_repository_slug_targets_the_create_call(self) -> None:
        run, calls = scripted_runner((0, URL + NL, ""), (0, "", ""))
        self.open(run, repo="ryancinsight/leto")
        self.assertEqual(calls[0][0][:5], ["gh", "pr", "create", "-R", "ryancinsight/leto"])
        self.assertEqual(calls[1][0], ["gh", "pr", "merge", URL, "--auto", "--merge", "--delete-branch"])

    def test_failed_auto_merge_is_a_failure_carrying_the_stderr_tail_and_the_pr_url(self) -> None:
        run, calls = scripted_runner((0, URL + NL, ""), (1, "", "x" + NL + "GraphQL: auto merge is not allowed"))
        opening = self.open(run)
        self.assertEqual(len(calls), 2)
        self.assertFalse(opening.delivered)
        self.assertEqual(opening.url, URL)
        self.assertEqual(
            opening.failure, f"gh pr merge --auto: x{NL}GraphQL: auto merge is not allowed (PR {URL})"
        )

    def test_only_the_tail_of_a_long_stderr_is_reported(self) -> None:
        run, _ = scripted_runner((1, "", "a" * 500 + "TAIL"), (0, "", ""))
        opening = self.open(run)
        self.assertEqual(opening.failure, "gh pr create: " + "a" * 196 + "TAIL")

    def test_failed_create_does_not_attempt_a_merge(self) -> None:
        run, calls = scripted_runner((1, "", "boom"), (0, "", ""))
        opening = self.open(run)
        self.assertEqual(len(calls), 1)
        self.assertEqual(opening, PullRequestOpening(None, "gh pr create: boom"))
        self.assertFalse(opening.delivered)


if __name__ == "__main__":
    unittest.main()
