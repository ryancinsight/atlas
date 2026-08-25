#!/usr/bin/env python3
"""Regression tests for the committed-Cargo.lock-form gate (ADR-0021).

The gate's whole value is that it separates two things a `git+` line count
cannot: a lock whose git source was *stripped* by the stack overlay, and a
member that legitimately resolves no git dependency at all. Both directions are
asserted here, plus an end-to-end run against a synthetic member repository so
the failure path is exercised through `check` itself and not only through the
predicate it calls.
"""
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lock-form.py"
_SPEC = importlib.util.spec_from_file_location("atlas_lock_form", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_lock_form = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_lock_form)


STANDALONE = textwrap.dedent(
    """\
    version = 4

    [[package]]
    name = "member"
    version = "0.1.0"
    dependencies = ["eunomia"]

    [[package]]
    name = "eunomia"
    version = "0.8.0"
    source = "git+https://github.com/ryancinsight/eunomia#abc123"
    """
)

STRIPPED = textwrap.dedent(
    """\
    version = 4

    [[package]]
    name = "member"
    version = "0.1.0"
    dependencies = ["eunomia"]

    [[package]]
    name = "eunomia"
    version = "0.8.0"

    [[patch.unused]]
    name = "themis-topology"
    version = "0.3.0"
    """
)


class ViolationPredicateTestCase(unittest.TestCase):
    LOCAL = {"member"}
    DEPS = {"eunomia"}

    def test_standalone_lock_is_clean(self) -> None:
        self.assertEqual(_lock_form.violations(STANDALONE, self.LOCAL, self.DEPS), [])

    def test_stripped_source_is_flagged(self) -> None:
        found = _lock_form.violations(STRIPPED, self.LOCAL, self.DEPS)
        self.assertTrue(any("`eunomia` locked without a git source" in f for f in found))

    def test_patch_unused_residue_is_flagged_even_without_git_deps(self) -> None:
        """A member with zero git dependencies can still carry overlay residue:
        the overlay patches URLs it does not use, and cargo records them."""
        found = _lock_form.violations(STRIPPED, self.LOCAL, set())
        self.assertEqual(len(found), 1)
        self.assertIn("[[patch.unused]]", found[0])

    def test_member_with_no_git_dependencies_is_not_a_violation(self) -> None:
        """The false positive a `git+` line count would produce: zero git
        sources is correct when nothing is sourced from git."""
        registry_only = textwrap.dedent(
            """\
            version = 4

            [[package]]
            name = "member"
            version = "0.1.0"

            [[package]]
            name = "serde"
            version = "1.0.0"
            source = "registry+https://github.com/rust-lang/crates.io-index"
            """
        )
        self.assertEqual(_lock_form.violations(registry_only, {"member"}, set()), [])

    def test_declared_but_unused_workspace_dependency_is_not_a_violation(self) -> None:
        """A `[workspace.dependencies]` row no crate consumes never reaches the
        lock; absence is correct, not a stripped source."""
        found = _lock_form.violations(
            STANDALONE, self.LOCAL, self.DEPS | {"ritk-core"}
        )
        self.assertEqual(found, [])

    def test_local_path_package_shadowing_a_git_name_is_not_a_violation(self) -> None:
        """A workspace that both declares and defines a package resolves it by
        path; a sourceless entry is then correct."""
        found = _lock_form.violations(STRIPPED, {"member", "eunomia"}, self.DEPS)
        self.assertTrue(all("eunomia" not in f for f in found))


class RestoreGuardTestCase(unittest.TestCase):
    def test_transitively_stripped_sibling_is_restorable(self) -> None:
        """Patching one crate to a path makes its whole workspace resolve by
        path, so siblings the `[patch]` table never names lose their source
        too. Eligibility follows the committed source, not the patch keys."""
        head = STANDALONE + (
            '\n[[package]]\nname = "eunomia-macros"\nversion = "0.8.0"\n'
            'source = "git+https://github.com/ryancinsight/eunomia#abc123"\n'
        )
        work = STRIPPED + (
            '\n[[package]]\nname = "eunomia-macros"\nversion = "0.8.0"\n'
        )
        self.assertTrue(_lock_form._strip_only(head, work))

    def test_moved_git_rev_is_not_restorable(self) -> None:
        """A first-party package repinned to a different rev is a real
        re-resolve, not the overlay dropping a source."""
        work = STANDALONE.replace("#abc123", "#deadbee")
        self.assertFalse(_lock_form._strip_only(STANDALONE, work))

    def test_pure_overlay_strip_is_restorable(self) -> None:
        self.assertTrue(_lock_form._strip_only(STANDALONE, STRIPPED))

    def test_patched_package_ahead_in_the_local_tree_is_restorable(self) -> None:
        """The local tree is routinely ahead of the pinned rev, so a patched
        package's version moves too. That is still pure churn."""
        ahead = STRIPPED.replace('version = "0.8.0"', 'version = "0.9.0"')
        self.assertTrue(_lock_form._strip_only(STANDALONE, ahead))

    def test_untouched_package_version_change_is_not_restorable(self) -> None:
        """A package the overlay does not patch changing version is a real
        re-resolve; restore must never discard it."""
        head = STANDALONE + '\n[[package]]\nname = "rand"\nversion = "0.8.0"\n'
        work = STRIPPED + '\n[[package]]\nname = "rand"\nversion = "0.9.0"\n'
        self.assertFalse(_lock_form._strip_only(head, work))

    def test_gained_source_is_not_restorable(self) -> None:
        """Churn only ever drops sources. A source the committed lock never
        carried means the working copy re-resolved for real."""
        work = STRIPPED.replace(
            'name = "eunomia"\nversion = "0.8.0"',
            'name = "eunomia"\nversion = "0.8.0"\n'
            'source = "git+https://github.com/ryancinsight/eunomia#deadbee"',
        )
        self.assertFalse(_lock_form._strip_only(STANDALONE, work))

    def test_residue_removal_is_not_restorable(self) -> None:
        """A working copy that repairs a residue-carrying committed lock must
        survive `restore`; churn only ever adds residue, never removes it."""
        self.assertFalse(_lock_form._strip_only(STRIPPED, STANDALONE))

    def test_added_untouched_package_is_not_restorable(self) -> None:
        added = STRIPPED + '\n[[package]]\nname = "rand"\nversion = "0.9.0"\n'
        self.assertFalse(_lock_form._strip_only(STANDALONE, added))


class FixtureDetectionTestCase(unittest.TestCase):
    """Only a workspace reaching *outside its own repository* by path is an
    in-tree fixture. An intra-repo `path = ".."` (the fuzz-crate idiom) must
    not exempt the whole member from the gate."""

    def _facts(self, dep_line: str, sub: str = "fuzz"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name) / "repos" / "member"
        (repo / sub).mkdir(parents=True)
        (repo / "Cargo.toml").write_text(
            '[package]\nname = "member"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        (repo / sub / "Cargo.toml").write_text(
            f'[package]\nname = "sub"\nversion = "0.1.0"\n\n[dependencies]\n{dep_line}\n',
            encoding="utf-8",
        )
        (Path(tmp.name) / "repos" / "sibling").mkdir(parents=True, exist_ok=True)
        return _lock_form.workspace_facts(repo, [], repo)

    def test_intra_repo_parent_path_is_not_a_fixture(self) -> None:
        _, _, fixture = self._facts('member = { path = ".." }')
        self.assertFalse(fixture)

    def test_cross_repo_path_is_a_fixture(self) -> None:
        _, _, fixture = self._facts('other = { path = "../../sibling" }')
        self.assertTrue(fixture)


class EndToEndCheckTestCase(unittest.TestCase):
    """Drive `check` over a synthetic member so the gate is observed failing."""

    def _member(self, root: Path, lock_text: str) -> None:
        repo = root / "repos" / "synthetic"
        repo.mkdir(parents=True)
        (repo / "Cargo.toml").write_text(
            textwrap.dedent(
                """\
                [package]
                name = "member"
                version = "0.1.0"

                [dependencies]
                eunomia = { version = "0.8", git = "https://github.com/ryancinsight/eunomia" }
                """
            ),
            encoding="utf-8",
        )
        (repo / "Cargo.lock").write_text(lock_text, encoding="utf-8")
        for args in (
            ["init", "-q", "-b", "main"],
            ["add", "Cargo.toml", "Cargo.lock"],
            ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "seed"],
        ):
            subprocess.run(["git", "-C", str(repo), *args], check=True)

    def _run_check(self, lock_text: str) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._member(root, lock_text)
            with (
                patch.object(_lock_form, "REPOS", root / "repos"),
                patch.object(
                    _lock_form, "registered_member_names", lambda: {"synthetic"}
                ),
            ):
                return _lock_form.cmd_check(None)

    def test_check_fails_on_a_committed_stripped_lock(self) -> None:
        self.assertEqual(self._run_check(STRIPPED), 1)

    def test_check_passes_on_a_committed_standalone_lock(self) -> None:
        self.assertEqual(self._run_check(STANDALONE), 0)


class StagedGateTestCase(EndToEndCheckTestCase):
    """The pre-commit arm: the churn is caught where it would escape."""

    def _run_staged(self, committed: str, staged: str) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._member(root, committed)
            repo = root / "repos" / "synthetic"
            (repo / "Cargo.lock").write_text(staged, encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "Cargo.lock"], check=True)
            with (
                patch.object(_lock_form, "REPOS", root / "repos"),
                patch.object(
                    _lock_form, "registered_member_names", lambda: {"synthetic"}
                ),
            ):
                args = type("Args", (), {"repo": str(repo)})()
                return _lock_form.cmd_staged(args)

    def test_staging_overlay_churn_is_rejected(self) -> None:
        self.assertEqual(self._run_staged(STANDALONE, STRIPPED), 1)

    def test_staging_a_deliberate_standalone_regeneration_is_allowed(self) -> None:
        repinned = STANDALONE.replace("#abc123", "#feedface")
        self.assertEqual(self._run_staged(STANDALONE, repinned), 0)


if __name__ == "__main__":
    unittest.main()
