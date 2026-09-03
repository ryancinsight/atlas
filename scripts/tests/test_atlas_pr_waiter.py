#!/usr/bin/env python3
"""Tests for atlas-pr-waiter.py's gate: the decision that merges or holds a PR.

The gate must never merge on a rollup that lacks the required check — the
shape a PR takes when its workflow edit made the file invalid and GitHub
scheduled none of that workflow's jobs (melinoe#23, eunomia#76 on 2026-09-02).
"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "atlas-pr-waiter.py"
SPEC = importlib.util.spec_from_file_location("atlas_pr_waiter", SCRIPT)
waiter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = waiter
SPEC.loader.exec_module(waiter)

REQ = re.compile("msrv|Rust 1", re.I)


def run(name: str, status: str, conclusion: str | None) -> dict:
    return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion}


def ctx(context: str, state: str) -> dict:
    return {"__typename": "StatusContext", "context": context, "state": state}


class StatusTests(unittest.TestCase):
    def test_an_unfinished_check_run_is_pending_whatever_its_conclusion_field_says(self) -> None:
        self.assertEqual(waiter.check_status(run("ci", "IN_PROGRESS", None)), "PENDING")
        self.assertEqual(waiter.check_status(run("ci", "QUEUED", "SUCCESS")), "PENDING")
        self.assertEqual(waiter.check_status(run("ci", "COMPLETED", "success")), "SUCCESS")
        self.assertEqual(waiter.check_status(ctx("bot/analysis", "ERROR")), "ERROR")

    def test_advisory_bots_are_excluded_from_the_decisive_set(self) -> None:
        names = waiter.decisive_checks([run("ci", "COMPLETED", "SUCCESS"), ctx("recurseml/analysis", "ERROR"),
                                        ctx("CodeRabbit", "PENDING")])
        self.assertEqual(names, {"ci": "SUCCESS"})


class GateTests(unittest.TestCase):
    def test_merges_only_when_the_required_check_is_present_and_green(self) -> None:
        self.assertEqual(waiter.gate({"Rust 1.95 check": "SUCCESS", "ci": "SUCCESS"}, REQ), "merge")

    def test_a_rollup_without_the_required_check_waits_even_when_all_green(self) -> None:
        # The rejected-workflow shape: every unrelated check green, the changed workflow absent.
        self.assertEqual(waiter.gate({"ci": "SUCCESS", "Lockfile integrity": "SUCCESS"}, REQ), "wait")

    def test_an_empty_rollup_waits(self) -> None:
        self.assertEqual(waiter.gate({}, REQ), "wait")

    def test_a_pending_check_waits_and_a_failed_check_is_red(self) -> None:
        self.assertEqual(waiter.gate({"Rust 1.95 check": "SUCCESS", "ci": "PENDING"}, REQ), "wait")
        self.assertEqual(waiter.gate({"Rust 1.95 check": "SUCCESS", "ci": "FAILURE"}, REQ), "red")
        self.assertEqual(waiter.gate({"MSRV": "CANCELLED"}, REQ), "red")

    def test_skipped_checks_neither_block_nor_satisfy_the_gate(self) -> None:
        self.assertEqual(waiter.gate({"MSRV": "SKIPPED", "ci": "SUCCESS"}, REQ), "wait")
        self.assertEqual(waiter.gate({"MSRV": "SUCCESS", "SemVer": "SKIPPED"}, REQ), "merge")


class AdvisoryTests(unittest.TestCase):
    """A job its own workflow marks continue-on-error reports, it does not veto."""

    def rollup(self):
        return [
            {"name": "Lockfile integrity", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "SemVer gate / SemVer (informational)", "status": "COMPLETED",
             "conclusion": "FAILURE"},
            {"name": "CodeRabbit", "status": "COMPLETED", "conclusion": "FAILURE"},
        ]

    def test_without_the_flag_the_informational_failure_is_a_verdict(self) -> None:
        names = waiter.decisive_checks(self.rollup())
        self.assertIn("SemVer gate / SemVer (informational)", names)
        self.assertEqual(waiter.gate(names, re.compile("Lockfile")), "red")

    def test_the_flag_excludes_it_and_the_merge_proceeds(self) -> None:
        advisory = re.compile(r"SemVer \(informational\)", re.I)
        names = waiter.decisive_checks(self.rollup(), advisory)
        self.assertEqual(sorted(names), ["Lockfile integrity"], "advisory bots stay excluded too")
        self.assertEqual(waiter.gate(names, re.compile("Lockfile")), "merge")

    def test_a_real_failure_still_blocks_under_the_flag(self) -> None:
        rollup = self.rollup() + [{"name": "Tests", "status": "COMPLETED", "conclusion": "FAILURE"}]
        names = waiter.decisive_checks(rollup, re.compile(r"SemVer \(informational\)", re.I))
        self.assertEqual(waiter.gate(names, re.compile("Lockfile")), "red")

if __name__ == "__main__":
    unittest.main()
