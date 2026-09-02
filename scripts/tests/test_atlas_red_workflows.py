#!/usr/bin/env python3
"""Tests for atlas-red-workflows.py's pure selection and log-scan functions.

The collector's contract: newest completed run per workflow, non-success
conclusions reported (cancelled and skipped included — an unfinished merge gate
leaves its merge unverified), in-progress runs never masking a red one.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "atlas-red-workflows.py"
SPEC = importlib.util.spec_from_file_location("atlas_red_workflows", SCRIPT)
red = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = red
SPEC.loader.exec_module(red)


def run(workflow: str, status: str, conclusion: str | None, sha: str) -> dict:
    return {"workflowName": workflow, "status": status, "conclusion": conclusion, "headSha": sha,
            "databaseId": 1, "createdAt": "2026-09-02T00:00:00Z", "url": "u", "event": "push"}


class SelectionTests(unittest.TestCase):
    def test_newest_completed_run_wins_per_workflow(self) -> None:
        runs = [  # gh run list order: newest first
            run("version-guard", "completed", "success", "cccccccc"),
            run("version-guard", "completed", "failure", "bbbbbbbb"),
            run("conformance", "completed", "failure", "cccccccc"),
            run("conformance", "completed", "success", "aaaaaaaa"),
        ]
        latest = red.latest_completed_per_workflow(runs)
        self.assertEqual({k: v["headSha"] for k, v in latest.items()},
                         {"version-guard": "cccccccc", "conformance": "cccccccc"})
        self.assertEqual([r["workflowName"] for r in red.red_runs(runs)], ["conformance"])

    def test_an_in_progress_run_does_not_mask_the_latest_completed_red(self) -> None:
        runs = [
            run("version-guard", "in_progress", None, "dddddddd"),
            run("version-guard", "completed", "failure", "cccccccc"),
        ]
        self.assertEqual([r["headSha"] for r in red.red_runs(runs)], ["cccccccc"])

    def test_cancelled_and_skipped_latest_runs_are_reported(self) -> None:
        runs = [
            run("conformance", "completed", "cancelled", "cccccccc"),
            run("docs", "completed", "skipped", "cccccccc"),
            run("ci", "completed", "success", "cccccccc"),
        ]
        self.assertEqual(sorted(r["workflowName"] for r in red.red_runs(runs)), ["conformance", "docs"])

    def test_all_green_reports_nothing(self) -> None:
        runs = [run("ci", "completed", "success", "a"), run("ci", "completed", "failure", "b")]
        self.assertEqual(red.red_runs(runs), [])


class LogScanTests(unittest.TestCase):
    def test_first_error_line_skips_setup_noise_and_strips_prefixes(self) -> None:
        log = "\n".join([
            "job\tstep\t2026-09-02T04:03:20.68Z ##[group]Run python3 sweep.py",
            "job\tstep\t2026-09-02T04:03:20.68Z env:",
            "job\tstep\t2026-09-02T04:03:23.21Z toolchain preflight: OK",
            "job\tstep\t2026-09-02T04:03:23.21Z error: target tuple in channel name '1.97.0-x86_64-pc-windows-msvc'",
            "job\tstep\t2026-09-02T04:03:23.22Z ##[error]Process completed with exit code 1.",
        ])
        self.assertEqual(red.first_error_line(log),
                         "error: target tuple in channel name '1.97.0-x86_64-pc-windows-msvc'")

    def test_ratchet_violations_and_test_failures_count_as_error_lines(self) -> None:
        self.assertEqual(red.first_error_line("x\ty\tRATCHET VIOLATION: apollo/print_dbg: 4 -> 10"),
                         "RATCHET VIOLATION: apollo/print_dbg: 4 -> 10")
        self.assertEqual(red.first_error_line("test a::b ... FAILED"), "test a::b ... FAILED")

    def test_no_match_is_reported_honestly(self) -> None:
        self.assertEqual(red.first_error_line("all quiet\n"), "(no error line matched)")


class SlugTests(unittest.TestCase):
    def test_slug_parsing_handles_https_ssh_and_git_suffix(self) -> None:
        original = red.git
        try:
            for url, expected in {
                "https://github.com/ryancinsight/atlas.git": "ryancinsight/atlas",
                "https://github.com/ryancinsight/Mnemosyne": "ryancinsight/Mnemosyne",
                "git@github.com:ryancinsight/leto.git": "ryancinsight/leto",
            }.items():
                red.git = lambda repo, *args, _u=url: _u
                self.assertEqual(red.slug_of(Path(".")), expected)
            red.git = lambda repo, *args: ""
            self.assertIsNone(red.slug_of(Path(".")))
        finally:
            red.git = original


if __name__ == "__main__":
    unittest.main()
