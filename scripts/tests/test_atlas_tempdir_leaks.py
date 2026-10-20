#!/usr/bin/env python3
"""No Atlas fixture leaves a directory behind under the OS temp directory.

A fixture that builds a tree owns it: the tree is removed on success and
on failure. `shutil.rmtree(ignore_errors=True)` is not removal - it
swallows the refusal to delete a fixture's read-only Git objects, and one
fixture had no cleanup at all (ATLAS-TEST-TEMPDIR-LEAKS).

The oracle runs the fixture suites against a private temporary root and
asserts that root is empty afterward. The private root is what makes the
oracle immune to a concurrent suite on the same host: a suite running at
the same time builds its trees under its own root, never under this one,
so the assertion cannot attribute another suite's tree to this fixture.
"""

from __future__ import annotations

import ast
import gc
import io
import pathlib
import tempfile
import unittest

import test_atlas_build_claim
import test_atlas_build_queue_order
import test_atlas_conformance
import test_atlas_pre_push_gate
import test_lockfile_check
import test_lockfile_shared_target
import test_safety_census

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
TESTS = SCRIPTS / "tests"

# The prefixes the fixtures under test own. The assertion is on the
# private root as a whole, so this list records which fixtures the oracle
# runs rather than filtering what it looks at.
OWNED_PREFIXES = (
    "atlas-claim-",
    "atlas-queue-",
    "atlas-safety-census-repo-",
    "atlas-shared-target-",
    "crlf-detector-",
    "gate-tmp-",
    "atlas-lockfile-check-",
)

# The ways a fixture can give its tree back. `shutil.rmtree` with
# `ignore_errors=True` is not one of them: it swallows the refusal to
# delete a read-only Git object and the tree stays.
REMOVALS = ("clear_readonly_tree", "shutil.rmtree", "TemporaryDirectory", "finalize")


def _calls(function: ast.AST) -> list[ast.Call]:
    return [node for node in ast.walk(function) if isinstance(node, ast.Call)]


def _removes(function: ast.AST, source: str) -> bool:
    """Whether the function gives a tree back at all.

    The removal is often a name handed to `addCleanup` rather than a call,
    so the source of the function is what answers this; whether that
    removal can swallow a refusal is `_ignores_errors`'s question.
    """
    body = ast.get_source_segment(source, function) or ""
    return any(removal in body for removal in REMOVALS)


def _ignores_errors(call: ast.Call) -> bool:
    """Whether this removal swallows a refusal to delete an entry."""
    rendered = ast.unparse(call)
    if ast.unparse(call.func).endswith("rmtree") and "ignore_errors" in rendered:
        return True
    if not ast.unparse(call.func).endswith("finalize"):
        return False
    # A finalizer that removes with `shutil.rmtree` and passes `True` as
    # the third argument is that removal with `ignore_errors=True`.
    arguments = list(call.args) + [keyword.value for keyword in call.keywords]
    for index, argument in enumerate(arguments):
        if ast.unparse(argument) != "shutil.rmtree":
            continue
        return any(
            isinstance(other, ast.Constant) and other.value is True
            for other in arguments[index + 1 :]
        )
    return False


class TempDirectoryOwnershipTests(unittest.TestCase):
    """The fixture suites that build trees remove them."""

    def _run(self, cases: list[unittest.TestCase]) -> None:
        suite = unittest.TestSuite(cases)
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        self.assertTrue(
            result.wasSuccessful(),
            "the fixture suite must pass for its cleanup to be meaningful",
        )

    def test_the_fixture_suites_leave_no_temp_directory_behind(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-tempdir-oracle-") as root:
            previous = tempfile.tempdir
            tempfile.tempdir = root
            try:
                self._run(
                    [
                        test_atlas_conformance.CrlfStoredBlobsTestCase(
                            "test_stored_crlf_blob_contradicting_the_policy_is_counted"
                        ),
                        test_atlas_conformance.CrlfStoredBlobsTestCase(
                            "test_a_mixed_blob_is_counted"
                        ),
                        test_safety_census.MainWalkTestCase(
                            "test_main_reports_missing_and_exit_zero"
                        ),
                        test_safety_census.MainWalkTestCase(
                            "test_fail_on_missing_returns_one"
                        ),
                        test_atlas_build_claim.ClaimTest(
                            "test_a_blocked_run_holds_no_lock_an_earlier_request_could_use"
                        ),
                        test_atlas_build_queue_order.QueueOrderTest(
                            "test_a_tie_of_crossed_modes_is_ordered_by_run_at_every_lease"
                        ),
                        test_lockfile_shared_target.SharedTargetDirTestCase(
                            "test_target_dir_resolves_against_the_config_that_declares_it"
                        ),
                        test_lockfile_check.CheckJudgesEveryLockTests(
                            "test_a_symlinked_directory_is_not_walked"
                        ),
                        test_atlas_pre_push_gate.ArtifactBudgetRevisionTestCase(
                            "test_budget_checks_the_pushed_tip_not_head"
                        ),
                    ]
                )
            finally:
                tempfile.tempdir = previous
            # A fixture whose cleanup is a finalizer runs it when the last
            # reference goes; collect so the assertion does not depend on
            # the collector's timing.
            gc.collect()
            left = sorted(entry.name for entry in pathlib.Path(root).iterdir())
            self.assertEqual(
                left,
                [],
                "fixtures left temp directories behind: " + repr(left),
            )

    def test_every_mkdtemp_fixture_removes_its_tree(self) -> None:
        """Every fixture that builds a tree gives it back.

        The behavioural oracle above can only see a leak whose tree
        happens to hold something `shutil.rmtree` refuses to delete, so
        the claim is also checked on the source: no fixture in
        `scripts/tests/` removes its tree with `ignore_errors=True`, and
        every `mkdtemp` call sits in a function that also removes it.
        """
        ignoring: list[str] = []
        unremoved: list[str] = []
        for path in sorted(TESTS.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            functions = [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]

            def owner_of(node: ast.AST) -> ast.AST | None:
                return next(
                    (function for function in functions if node in ast.walk(function)),
                    None,
                )

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = ast.unparse(node.func)
                if name.endswith("mkdtemp"):
                    owner = owner_of(node)
                    if owner is None or not _removes(owner, source):
                        unremoved.append(f"{path.name}:{node.lineno}: {name}")
                    continue
                if not _ignores_errors(node):
                    continue
                # Only a fixture's own tree is at issue: a removal of a
                # shared cache between two runs is not a leak.
                owner = owner_of(node)
                if owner is None:
                    continue
                if any(
                    ast.unparse(inner.func).endswith("mkdtemp")
                    for inner in _calls(owner)
                ):
                    ignoring.append(
                        f"{path.name}:{node.lineno}: {ast.unparse(node)}"
                    )
        self.assertEqual(ignoring, [], "fixtures remove their tree with ignore_errors")
        self.assertEqual(unremoved, [], "fixtures that build a tree but never remove it")


if __name__ == "__main__":
    unittest.main()
