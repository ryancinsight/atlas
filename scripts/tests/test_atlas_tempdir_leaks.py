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
# runs and what its failure message names; it does not filter what the
# assertion looks at.
OWNED_PREFIXES = (
    "atlas-claim-",
    "atlas-gate-",
    "atlas-lockfile-check-",
    "atlas-queue-",
    "atlas-safety-census-repo-",
    "atlas-shared-target-",
    "crlf-detector-",
    "gate-tmp-",
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


def _names_a_removal(node: ast.AST) -> bool:
    """Whether this expression names a removal.

    A removal is often handed to another call rather than called:
    `self.addCleanup(shutil.rmtree, root, ignore_errors=True)` names
    `shutil.rmtree` as an argument, so a walk that only saw calls would
    miss the very form it is looking for.
    """
    if isinstance(node, ast.Attribute):
        return node.attr == "rmtree"
    if isinstance(node, ast.Name):
        return node.id == "rmtree"
    return False


def _ignores_errors(call: ast.Call) -> bool:
    """Whether this removal swallows a refusal to delete an entry.

    Two forms carry the refusal: a direct `rmtree(..., ignore_errors=True)`
    call, and a removal handed to another call that then passes
    `ignore_errors=True` -- `addCleanup(shutil.rmtree, root, True)` -- or
    `True` in the position `rmtree` takes it, as
    `weakref.finalize(self, shutil.rmtree, path, True)` does.
    """
    rendered = ast.unparse(call)
    if ast.unparse(call.func).endswith("rmtree") and "ignore_errors" in rendered:
        return True
    positional = list(call.args)
    for index, argument in enumerate(positional):
        if not _names_a_removal(argument):
            continue
        if any(
            keyword.arg == "ignore_errors"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in call.keywords
        ):
            return True
        return any(
            isinstance(other, ast.Constant) and other.value is True
            for other in positional[index + 1 :]
        )
    return False


def _names_the_tree(call: ast.Call, created: set[str]) -> bool:
    """Whether this removal names one of the fixture's own trees.

    The tree is the argument the removal is handed: the one after the
    removal itself. A path *inside* a created tree is not that tree --
    a fixture that clears a cache directory between two runs is not
    removing its tree -- so a created name followed by a path join does
    not count.
    """
    positional = list(call.args)
    for index, argument in enumerate(positional):
        if not _names_a_removal(argument):
            continue
        if index + 1 >= len(positional):
            return False
        target = ast.unparse(positional[index + 1])
        for name in created:
            position = target.find(name)
            if position < 0:
                continue
            if target[position + len(name) :].lstrip().startswith("/"):
                continue
            return True
    return False
def _scopes(tree: ast.Module) -> list[ast.AST]:
    """The units a fixture's tree belongs to: each class, and each function
    that is not inside one.

    A fixture's tree is usually created in `setUp` and removed in a test
    method, so the unit is the class, not the method.
    """
    classes = [
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    ]
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    scopes: list[ast.AST] = list(classes)
    scopes.extend(
        function
        for function in functions
        if not any(function in ast.walk(klass) for klass in classes)
    )
    return scopes


def _owner_of(scope: ast.AST, node: ast.AST) -> ast.AST | None:
    """The function inside `scope` that holds `node`."""
    return next(
        (
            function
            for function in ast.walk(scope)
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node in ast.walk(function)
        ),
        None,
    )
def _created_trees(function: ast.AST) -> set[str]:
    """The names a function binds from `mkdtemp`, and from those.

    A fixture's tree is often bound through an attribute (`self.base = ...`)
    and the path a removal names is sometimes one step derived from it
    (`outside = self.root.parent / ...`), so the derivation is followed one
    level: a name whose value mentions a created tree is itself a name for
    that tree.
    """
    def creates_tree(value: ast.AST) -> bool:
        """Whether this expression builds a temporary tree."""
        return any(
            isinstance(node, ast.Call)
            and ast.unparse(node.func).rsplit(".", 1)[-1]
            in ("mkdtemp", "TemporaryDirectory")
            for node in ast.walk(value)
        )

    def referenced(value: ast.AST) -> set[str]:
        """The names an expression reads."""
        return {
            ast.unparse(node)
            for node in ast.walk(value)
            if isinstance(node, (ast.Name, ast.Attribute))
        }

    def targets_of(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Assign):
            return [ast.unparse(target) for target in node.targets]
        if isinstance(node, ast.AnnAssign):
            return [ast.unparse(node.target)]
        return []

    created: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        if node.value is None or not creates_tree(node.value):
            continue
        created.update(targets_of(node))
    # The derivation is followed to a fixed point: a fixture's tree is
    # often bound through an attribute (`self.root = Path(self.temp.name)`)
    # and the path a removal names is derived from that
    # (`outside = self.root.parent / ...`).
    known = set(created)
    while True:
        derived: set[str] = set()
        for node in ast.walk(function):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            if node.value is None:
                continue
            if not referenced(node.value) & known:
                continue
            derived.update(targets_of(node))
        if derived <= known:
            return known
        known |= derived


class TempDirectoryOwnershipTests(unittest.TestCase):
    """The fixture suites that build trees remove them."""

    def _run(self, cases: list[unittest.TestCase]) -> None:
        suite = unittest.TestSuite(cases)
        captured = io.StringIO()
        result = unittest.TextTestRunner(stream=captured).run(suite)
        self.assertTrue(
            result.wasSuccessful(),
            "the fixture suite must pass for its cleanup to be meaningful:\n"
            + captured.getvalue(),
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
                "fixtures left temp directories behind: "
                + repr(left)
                + " (the fixtures own "
                + ", ".join(OWNED_PREFIXES)
                + ")",
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
            for scope in _scopes(tree):
                created = _created_trees(scope)
                for node in ast.walk(scope):
                    if not isinstance(node, ast.Call):
                        continue
                    name = ast.unparse(node.func)
                    if name.endswith("mkdtemp"):
                        owner = _owner_of(scope, node)
                        if owner is None or not _removes(owner, source):
                            unremoved.append(
                                f"{path.name}:{node.lineno}: {name}"
                            )
                        continue
                    if not _ignores_errors(node):
                        continue
                    # Only a fixture's own tree is at issue: a removal of
                    # a shared cache between two runs is not a leak, and
                    # that cache is not the tree the fixture created.
                    if not created:
                        continue
                    if _names_the_tree(node, created):
                        ignoring.append(
                            f"{path.name}:{node.lineno}: {ast.unparse(node)}"
                        )
        self.assertEqual(ignoring, [], "fixtures remove their tree with ignore_errors")
        self.assertEqual(unremoved, [], "fixtures that build a tree but never remove it")


if __name__ == "__main__":
    unittest.main()
