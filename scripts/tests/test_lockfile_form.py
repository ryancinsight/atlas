#!/usr/bin/env python3
"""The rule defining a standalone `Cargo.lock`, and the sweep over committed locks.

The rule separates two things a `git+` line count cannot: a lock whose git
source was *stripped* by the stack overlay, and a workspace that legitimately
resolves no git dependency at all. Both directions are asserted on the
predicate, then through `check_committed` over synthetic repositories so the
failure path is exercised end to end and the verdict is shown to come from the
commit, never the working tree.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path, PurePosixPath

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_form", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)

ROOT_WORKSPACE = PurePosixPath(".")

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

MANIFEST = textwrap.dedent(
    """\
    [package]
    name = "member"
    version = "0.1.0"

    [dependencies]
    eunomia = { version = "0.8", git = "https://github.com/ryancinsight/eunomia" }
    """
)


class ViolationPredicateTestCase(unittest.TestCase):
    LOCAL = {"member"}
    DEPS = {"eunomia"}

    def test_standalone_lock_is_clean(self) -> None:
        self.assertEqual(lockfile.violations(STANDALONE, self.LOCAL, self.DEPS), [])

    def test_stripped_source_is_flagged(self) -> None:
        found = lockfile.violations(STRIPPED, self.LOCAL, self.DEPS)
        self.assertIn("`eunomia` locked without a git source (stripped)", found)

    def test_one_provider_stripped_while_another_keeps_its_source_is_flagged(self) -> None:
        """A partial strip: a count of first-party sources is still nonzero, so
        only the per-package rule sees it."""
        lock = STANDALONE + '\n[[package]]\nname = "hermes"\nversion = "0.2.0"\n'
        found = lockfile.violations(lock, self.LOCAL, {"eunomia", "hermes"})
        self.assertEqual(found, ["`hermes` locked without a git source (stripped)"])

    def test_patch_unused_residue_is_flagged_even_without_git_deps(self) -> None:
        """A workspace with zero git dependencies can still carry overlay residue:
        the overlay patches URLs it does not use, and cargo records them."""
        found = lockfile.violations(STRIPPED, self.LOCAL, set())
        self.assertEqual(found, ["1 [[patch.unused]] table(s): overlay residue"])

    def test_residue_beside_intact_sources_is_flagged(self) -> None:
        lock = STANDALONE + '\n[[patch.unused]]\nname = "themis-topology"\nversion = "0.3.0"\n'
        found = lockfile.violations(lock, self.LOCAL, self.DEPS)
        self.assertEqual(found, ["1 [[patch.unused]] table(s): overlay residue"])

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
        self.assertEqual(lockfile.violations(registry_only, {"member"}, set()), [])

    def test_declared_but_unused_workspace_dependency_is_not_a_violation(self) -> None:
        """A `[workspace.dependencies]` row no crate consumes never reaches the
        lock; absence is correct, not a stripped source."""
        found = lockfile.violations(STANDALONE, self.LOCAL, self.DEPS | {"ritk-core"})
        self.assertEqual(found, [])

    def test_local_path_package_shadowing_a_git_name_is_not_a_violation(self) -> None:
        """A workspace that both declares and defines a package resolves it by
        path; a sourceless entry is then correct."""
        found = lockfile.violations(STRIPPED, {"member", "eunomia"}, self.DEPS)
        self.assertTrue(all("eunomia" not in problem for problem in found))

    def test_an_unparseable_lock_is_a_violation(self) -> None:
        found = lockfile.violations("[[package\n", self.LOCAL, self.DEPS)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("unparseable lock"))


class DependencyTablesTestCase(unittest.TestCase):
    """A dependency declared in any table counts, so no declaration hides a strip."""

    def declared(self, manifest: str) -> frozenset[str]:
        facts = lockfile.workspace_facts({"Cargo.toml": manifest}, ROOT_WORKSPACE, [])
        return facts.git_dependencies

    def test_every_table_that_declares_dependencies_is_read(self) -> None:
        git = '{ git = "https://github.com/ryancinsight/p" }'
        tables = {
            "[dependencies]": "regular",
            "[dev-dependencies]": "development",
            "[build-dependencies]": "build",
            "[workspace.dependencies]": "shared",
            "[target.'cfg(unix)'.dependencies]": "unix",
            "[target.'cfg(unix)'.dev-dependencies]": "unixdev",
            "[target.'cfg(unix)'.build-dependencies]": "unixbuild",
        }
        for header, name in tables.items():
            with self.subTest(header):
                manifest = f'[package]\nname = "m"\nversion = "0.1.0"\n\n{header}\n{name} = {git}\n'
                self.assertEqual(self.declared(manifest), {name})

    def test_a_renamed_dependency_is_declared_under_its_package_name(self) -> None:
        manifest = (
            '[package]\nname = "m"\nversion = "0.1.0"\n\n[dependencies]\n'
            'alias = { package = "real", git = "https://github.com/ryancinsight/p" }\n'
        )
        self.assertEqual(self.declared(manifest), {"real"})

    def test_registry_and_path_dependencies_are_not_git_dependencies(self) -> None:
        manifest = (
            '[package]\nname = "m"\nversion = "0.1.0"\n\n[dependencies]\n'
            'serde = "1"\nlocal = { path = "../local" }\n'
        )
        self.assertEqual(self.declared(manifest), frozenset())

    def test_a_stripped_dev_dependency_is_found_through_the_whole_rule(self) -> None:
        manifest = (
            '[package]\nname = "member"\nversion = "0.1.0"\n\n[dev-dependencies]\n'
            'eunomia = { version = "0.8", git = "https://github.com/ryancinsight/eunomia" }\n'
        )
        problems, exempt = lockfile.judge_locks({"Cargo.toml": manifest, "Cargo.lock": STRIPPED})
        self.assertIn("Cargo.lock: `eunomia` locked without a git source (stripped)", problems)
        self.assertEqual(exempt, [])


class FixtureDetectionTestCase(unittest.TestCase):
    """Only a workspace reaching *outside its own repository* by path is an
    in-tree fixture. An intra-repo `path = ".."` (the fuzz-crate idiom) must
    not exempt the whole workspace from the rule."""

    def facts(self, dependency: str, directory: str = "fuzz") -> lockfile.WorkspaceFacts:
        manifests = {
            "Cargo.toml": '[package]\nname = "member"\nversion = "0.1.0"\n',
            f"{directory}/Cargo.toml": (
                f'[package]\nname = "sub"\nversion = "0.1.0"\n\n[dependencies]\n{dependency}\n'
            ),
        }
        return lockfile.workspace_facts(manifests, ROOT_WORKSPACE, [])

    def test_intra_repo_parent_path_is_not_a_fixture(self) -> None:
        self.assertFalse(self.facts('member = { path = ".." }').fixture)

    def test_cross_repo_path_is_a_fixture(self) -> None:
        self.assertTrue(self.facts('other = { path = "../../sibling" }').fixture)

    def test_a_path_leaving_the_repository_from_a_deeper_manifest_is_a_fixture(self) -> None:
        self.assertTrue(self.facts('other = { path = "../../../x" }', "a/b").fixture)

    def test_a_path_staying_inside_from_a_deeper_manifest_is_not_a_fixture(self) -> None:
        self.assertFalse(self.facts('other = { path = "../../c" }', "a/b").fixture)

    def test_an_absolute_path_is_a_fixture(self) -> None:
        self.assertTrue(self.facts('other = { path = "/opt/other" }').fixture)

    def test_a_windows_drive_path_is_a_fixture_in_either_separator(self) -> None:
        self.assertTrue(self.facts('other = { path = "C:/opt/other" }').fixture)
        self.assertTrue(self.facts(r"other = { path = 'C:\opt\other' }").fixture)

    def test_a_path_resolving_exactly_to_the_parent_of_the_repository_is_a_fixture(self) -> None:
        """`..` from the root manifest and `../../..` from `a/b` both name the
        directory above the repository, with no component left after the `..`."""
        self.assertTrue(
            lockfile.workspace_facts(
                {"Cargo.toml": '[dependencies]\nup = { path = ".." }\n'}, ROOT_WORKSPACE, []
            ).fixture
        )
        self.assertTrue(self.facts('other = { path = "../../.." }', "a/b").fixture)

    def test_a_path_resolving_to_the_repository_root_is_not_a_fixture(self) -> None:
        self.assertFalse(self.facts('other = { path = "../.." }', "a/b").fixture)

    def test_a_fixture_lock_is_exempt_and_reported(self) -> None:
        manifests = {
            "Cargo.toml": '[package]\nname = "m"\nversion = "0.1.0"\n\n[dependencies]\n'
            'x = { path = "../../sibling" }\n',
            "Cargo.lock": STRIPPED,
        }
        problems, exempt = lockfile.judge_locks(manifests)
        self.assertEqual((problems, exempt), ([], ["Cargo.lock"]))


class WorkspaceScopeTestCase(unittest.TestCase):
    def test_a_nested_workspace_owns_its_manifests(self) -> None:
        """Manifests under a sibling lock's root belong to that lock."""
        manifests = {
            "Cargo.toml": '[package]\nname = "outer"\nversion = "0.1.0"\n',
            "fuzz/Cargo.toml": '[package]\nname = "inner"\nversion = "0.1.0"\n\n[dependencies]\n'
            'p = { git = "https://github.com/ryancinsight/p" }\n',
        }
        outer = lockfile.workspace_facts(manifests, ROOT_WORKSPACE, [PurePosixPath("fuzz")])
        inner = lockfile.workspace_facts(manifests, PurePosixPath("fuzz"), [])
        self.assertEqual((outer.local, outer.git_dependencies), ({"outer"}, frozenset()))
        self.assertEqual((inner.local, inner.git_dependencies), ({"inner"}, {"p"}))

    def test_build_output_manifests_are_not_part_of_a_workspace(self) -> None:
        manifests = {
            "Cargo.toml": '[package]\nname = "m"\nversion = "0.1.0"\n',
            "target/package/x/Cargo.toml": '[dependencies]\np = { git = "https://x/p" }\n',
        }
        self.assertEqual(
            lockfile.workspace_facts(manifests, ROOT_WORKSPACE, []).git_dependencies, frozenset()
        )

    def test_a_manifest_that_does_not_parse_makes_the_lock_unjudgeable(self) -> None:
        problems, _ = lockfile.judge_locks({"Cargo.toml": "[package\n", "Cargo.lock": STANDALONE})
        self.assertEqual(
            problems, ["Cargo.lock: Cargo.toml does not parse, so the lock cannot be judged"]
        )


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository), "-c", "user.email=t@t", "-c", "user.name=t", *arguments],
        check=True,
        capture_output=True,
    )


class CommittedSweepTestCase(unittest.TestCase):
    """Drive `check_committed` over synthetic repositories."""

    def repository(self, files: dict[str, str]) -> Path:
        directory = tempfile.TemporaryDirectory(prefix="atlas-lock-sweep-")
        self.addCleanup(directory.cleanup)
        repository = Path(directory.name) / "synthetic"
        repository.mkdir()
        git(repository, "init", "-q", "-b", "main")
        for name, text in files.items():
            path = repository / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        git(repository, "add", "-A")
        git(repository, "commit", "-q", "-m", "seed")
        return repository

    def sweep(self, *repositories: Path) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = lockfile.check_committed(list(repositories))
        return status, output.getvalue()

    def test_a_committed_stripped_lock_fails(self) -> None:
        status, output = self.sweep(self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED}))
        self.assertEqual(status, 1)
        self.assertIn("LOCK FORM VIOLATION: synthetic/Cargo.lock: `eunomia` locked without", output)
        self.assertIn("2 violation(s) across 1 committed lock(s)", output)

    def test_a_committed_standalone_lock_passes(self) -> None:
        status, output = self.sweep(self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STANDALONE}))
        self.assertEqual(status, 0)
        self.assertIn("lock form clean: 1 committed lock(s) resolve standalone", output)

    def test_a_stripped_lock_in_a_tool_workspace_is_flagged(self) -> None:
        """A cargo run inside a tool workspace walks up into the stack overlay
        exactly as a member's does, so every tracked lock is judged, not only
        the root's."""
        repository = self.repository(
            {"tools/synthetic/Cargo.toml": MANIFEST, "tools/synthetic/Cargo.lock": STRIPPED}
        )
        status, output = self.sweep(repository)
        self.assertEqual(status, 1)
        self.assertIn("synthetic/tools/synthetic/Cargo.lock", output)

    def test_the_commit_is_judged_not_the_working_file(self) -> None:
        repository = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        (repository / "Cargo.lock").write_text(STANDALONE, encoding="utf-8", newline="\n")
        self.assertEqual(self.sweep(repository)[0], 1)

    def test_a_staged_change_is_not_part_of_the_commit_being_judged(self) -> None:
        sound = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STANDALONE})
        (sound / "Cargo.lock").write_text(STRIPPED, encoding="utf-8", newline="\n")
        git(sound, "add", "Cargo.lock")
        self.assertEqual(self.sweep(sound)[0], 0)
        stripped = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        (stripped / "Cargo.lock").write_text(STANDALONE, encoding="utf-8", newline="\n")
        git(stripped, "add", "Cargo.lock")
        self.assertEqual(self.sweep(stripped)[0], 1)

    def test_a_flattened_working_file_does_not_fail_a_sound_commit(self) -> None:
        repository = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STANDALONE})
        (repository / "Cargo.lock").write_text(STRIPPED, encoding="utf-8", newline="\n")
        self.assertEqual(self.sweep(repository)[0], 0)

    def test_a_directory_that_is_not_a_repository_root_is_skipped_with_a_warning(self) -> None:
        """An uninitialized submodule is an empty directory inside its parent,
        and git run there answers for the parent."""
        parent = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        (parent / "repos" / "absent").mkdir(parents=True)
        status, output = self.sweep(parent / "repos" / "absent")
        self.assertEqual(status, 0)
        self.assertIn("::warning::absent: not a repository root; skipped", output)
        self.assertNotIn("VIOLATION", output)

    def test_a_repository_git_cannot_read_is_a_failure(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="atlas-lock-sweep-")
        self.addCleanup(directory.cleanup)
        repository = Path(directory.name) / "unborn"
        repository.mkdir()
        git(repository, "init", "-q", "-b", "main")
        status, output = self.sweep(repository)
        self.assertEqual(status, 1)
        self.assertIn("unborn: cannot be read", output)

    def test_the_command_line_sweeps_the_repositories_it_names(self) -> None:
        repository = self.repository({"Cargo.toml": MANIFEST, "Cargo.lock": STRIPPED})
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--check-committed", str(repository)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn("LOCK FORM VIOLATION", completed.stdout)


if __name__ == "__main__":
    unittest.main()
