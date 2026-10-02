#!/usr/bin/env python3
"""Tests for atlas-lock-sweep.py's pure decisions.

The sweep's repository operations are exercised by running it; what unit
tests pin is every decision that could silently exclude or misplace a
consumer: which manifest lines count as a first-party git dependency, which
locked revision a lock names, when a consumer counts as current, and what the
branch and report look like. A wrong answer to any of these is a consumer
skipped without a row — the failure the tool exists to prevent.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "atlas-lock-sweep.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("atlas_lock_sweep", SCRIPT)
sweep = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# dataclasses resolve `from __future__` annotations through sys.modules.
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)

HERMES = "https://github.com/ryancinsight/hermes.git"
NL = chr(10)


class UrlTests(unittest.TestCase):
    def test_provider_name_ignores_suffix_case_and_trailing_slash(self) -> None:
        for url in (HERMES, "https://github.com/ryancinsight/Hermes", "https://github.com/ryancinsight/hermes/"):
            self.assertEqual(sweep.provider_repo_name(url), "hermes", url)

    def test_normalized_urls_compare_equal_across_spellings(self) -> None:
        self.assertEqual(
            sweep.normalize_repo_url("https://github.com/ryancinsight/Mnemosyne.git"),
            sweep.normalize_repo_url("https://github.com/ryancinsight/mnemosyne"),
        )


class ManifestTests(unittest.TestCase):
    def test_workspace_table_entry_is_found(self) -> None:
        text = '[workspace.dependencies]\nhermes-simd = { version = "0.7.0", git = "%s" }\nleto = { version = "0.42.0", git = "https://github.com/ryancinsight/leto.git" }\n' % HERMES
        self.assertEqual(sweep.declared_git_source(text, "hermes-simd"), HERMES)

    def test_key_order_inside_the_table_does_not_matter(self) -> None:
        text = 'hermes-simd = { git = "%s", version = "0.7.0" }\n' % HERMES
        self.assertEqual(sweep.declared_git_source(text, "hermes-simd"), HERMES)

    def test_a_crate_whose_name_is_a_prefix_of_another_is_not_matched(self) -> None:
        text = 'hermes-simd-core = { version = "0.7.0", git = "%s" }\n' % HERMES
        self.assertIsNone(sweep.declared_git_source(text, "hermes-simd"))

    def test_registry_and_path_dependencies_are_not_consumers(self) -> None:
        self.assertIsNone(sweep.declared_git_source('hermes-simd = "0.7.0"\n', "hermes-simd"))
        self.assertIsNone(sweep.declared_git_source('hermes-simd = { path = "../hermes" }\n', "hermes-simd"))

    def test_a_renamed_dependency_is_matched_by_its_package_name(self) -> None:
        """Nine members reach mnemosyne-memory as `mnemosyne = { package = ... }`.
        Matching the declaration key alone reported no consumers at all while
        the lock, keyed by real package name, held every one of them."""
        text = 'mnemosyne = { package = "hermes-simd", version = "0.7.0", git = "%s" }\n' % HERMES
        self.assertEqual(sweep.declared_git_source(text, "hermes-simd"), HERMES)

    def test_a_renamed_dependency_is_not_matched_by_its_key(self) -> None:
        """The key is a local alias; the lock never contains it, so a sweep
        keyed on it would advance nothing."""
        text = 'mnemosyne = { package = "hermes-simd", version = "0.7.0", git = "%s" }\n' % HERMES
        self.assertIsNone(sweep.declared_git_source(text, "mnemosyne"))

    def test_a_rename_to_another_package_is_not_matched(self) -> None:
        text = 'hermes-simd = { package = "hermes-simd-core", git = "%s" }\n' % HERMES
        self.assertIsNone(sweep.declared_git_source(text, "hermes-simd"))

    def test_third_party_git_sources_are_not_first_party_consumers(self) -> None:
        text = 'hermes-simd = { git = "https://github.com/someone-else/hermes.git" }\n'
        self.assertIsNone(sweep.declared_git_source(text, "hermes-simd"))


class LockTests(unittest.TestCase):
    LOCK = (
        '[[package]]\nname = "hermes-simd"\nversion = "0.7.0"\n'
        'source = "git+https://github.com/ryancinsight/hermes.git#6da6d139abcdef0123456789abcdef0123456789"\n\n'
        '[[package]]\nname = "hermes-simd-core"\nversion = "0.7.0"\n'
        'source = "git+https://github.com/ryancinsight/hermes.git#6da6d139abcdef0123456789abcdef0123456789"\n\n'
        '[[package]]\nname = "csv"\nversion = "1.4.0"\n'
        'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
    )

    def test_locked_rev_reads_the_exact_package_block(self) -> None:
        self.assertEqual(sweep.locked_rev(self.LOCK, "hermes-simd"), "6da6d139abcdef0123456789abcdef0123456789")

    def test_registry_packages_have_no_git_rev(self) -> None:
        self.assertIsNone(sweep.locked_rev(self.LOCK, "csv"))

    def test_absent_packages_are_none_not_a_neighbour(self) -> None:
        self.assertIsNone(sweep.locked_rev(self.LOCK, "leto"))


class PlanTests(unittest.TestCase):
    consumer = sweep.Consumer(Path("repos/leto"), HERMES)

    def test_current_when_locked_rev_is_the_target(self) -> None:
        row = sweep.PlanRow(self.consumer, "6da6d139" + "0" * 32, "6da6d139" + "0" * 32)
        self.assertFalse(row.needs_advance)

    def test_advance_when_behind_or_absent(self) -> None:
        self.assertTrue(sweep.PlanRow(self.consumer, "efe6b5e2" + "0" * 32, "6da6d139" + "0" * 32).needs_advance)
        self.assertTrue(sweep.PlanRow(self.consumer, None, "6da6d139" + "0" * 32).needs_advance)

    def test_branch_name_is_crate_and_short_revision(self) -> None:
        self.assertEqual(sweep.branch_name("hermes-simd", "6da6d139" + "0" * 32), "build/hermes-simd-6da6d139")

    def test_report_lists_every_consumer_with_its_action(self) -> None:
        rows = [
            sweep.Outcome(self.consumer, "current", "already at 6da6d139", True),
            sweep.Outcome(sweep.Consumer(Path("repos/kwavers"), HERMES), "failed", "cargo check: error[E0425]", False),
        ]
        report = sweep.render_report("hermes-simd", "6da6d139" + "0" * 32, rows)
        self.assertIn("leto", report)
        self.assertIn("kwavers", report)
        self.assertIn("failed", report)
        self.assertIn("hermes-simd -> 6da6d139", report)


class OpenConsumerPullRequestTests(unittest.TestCase):
    consumer = sweep.Consumer(Path("repos/leto"), HERMES)
    lane = Path("worktrees/leto-lock-sweep")
    url = "https://github.com/ryancinsight/leto/pull/7"

    def runner(self, create: tuple[int, str, str], merge: tuple[int, str, str]):
        calls: list[tuple[list[str], Path]] = []

        def run(argv, cwd=None, **_options):
            calls.append((argv, cwd))
            code, out, err = create if argv[:3] == ["gh", "pr", "create"] else merge
            return subprocess.CompletedProcess(argv, code, out, err)

        return run, calls

    def open(self, run):
        return sweep.open_consumer_pull_request(
            self.consumer, self.lane, "main", "build/hermes-simd-6da6d139", "build(deps): t", "body", run=run
        )

    def test_the_pr_is_created_from_the_lane_then_auto_merged_with_an_explicit_merge_method(self) -> None:
        run, calls = self.runner((0, f"warning: x{NL}{self.url}{NL}", ""), (0, "", ""))
        outcome = self.open(run)
        self.assertEqual([argv[:3] for argv, _ in calls], [["gh", "pr", "create"], ["gh", "pr", "merge"]])
        self.assertEqual(calls[1][0], ["gh", "pr", "merge", self.url, "--auto", "--merge", "--delete-branch"])
        self.assertEqual([cwd for _, cwd in calls], [self.lane, self.lane])
        self.assertEqual((outcome.action, outcome.detail, outcome.ok), ("opened", self.url, True))

    def test_a_pr_whose_auto_merge_failed_is_a_failed_row_carrying_its_url(self) -> None:
        run, _ = self.runner((0, self.url + NL, ""), (1, "", "GraphQL: auto merge is not allowed"))
        outcome = self.open(run)
        self.assertEqual((outcome.action, outcome.ok), ("failed", False))
        self.assertIn(self.url, outcome.detail)


if __name__ == "__main__":
    unittest.main()
