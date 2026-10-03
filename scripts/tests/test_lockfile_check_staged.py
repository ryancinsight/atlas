#!/usr/bin/env python3
"""`lockfile.py --check-staged` judges the staged locks of the current repository.

The member `pre-commit` hook runs the stack's copy of the script from inside
the member, so the index it reads is the member's. The staged blob is judged
against the same rule as every committed lock, manifests are read from
the index, and anything git cannot answer refuses the commit: an error is never
an empty listing.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_staged", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)

SOURCE = 'source = "git+https://github.com/ryancinsight/{name}.git?branch=main#abc123"\n'
SOUND = (
    '[[package]]\nname = "provider"\nversion = "0.1.0"\n' + SOURCE.format(name="provider")
)
FLATTENED = '[[package]]\nname = "provider"\nversion = "0.1.0"\n'
RESIDUE = '\n[[patch.unused]]\nname = "unused"\nversion = "0.3.0"\n'
GIT = '{ git = "https://github.com/ryancinsight/provider", version = "0.1" }'
IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]


def manifest(table: str = "[dependencies]", dependencies: str = f"provider = {GIT}") -> str:
    return f'[package]\nname = "member"\nversion = "0.1.0"\n\n{table}\n{dependencies}\n'


DECLARES = manifest()
DECLARES_NOTHING = manifest(dependencies='serde = "1"\nlocal = { path = "crates/local" }')


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *IDENT, *args],
        check=True,
        capture_output=True,
        env=None if env is None else {**os.environ, **env},
    )


def check_staged(repo: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check-staged"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=None if env is None else {**os.environ, **env},
    )


class StagedFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="atlas-lock-staged-")
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        git(self.repo, "init", "-q")
        self.write("Cargo.toml", DECLARES)
        self.write("Cargo.lock", SOUND)
        git(self.repo, "add", "Cargo.toml", "Cargo.lock")
        git(self.repo, "commit", "-q", "-m", "seed")

    def write(self, name: str, text: str) -> None:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def stage(self, name: str, text: str) -> None:
        self.write(name, text)
        git(self.repo, "add", name)

    def refused(self, completed: subprocess.CompletedProcess[str]) -> str:
        self.assertEqual(completed.returncode, 1, completed.stderr)
        return completed.stderr


class CheckStagedTests(StagedFixture):
    def test_a_commit_that_stages_no_lock_is_not_judged(self) -> None:
        self.stage("other.txt", "x")
        self.assertEqual(check_staged(self.repo).returncode, 0)

    def test_a_staged_lock_with_its_sources_passes(self) -> None:
        self.stage("Cargo.lock", SOUND + "# touched\n")
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_only_the_staged_locks_are_judged_not_every_tracked_one(self) -> None:
        """A flattened lock already committed beside the staged one is not this
        commit's to refuse; the committed sweep owns it."""
        self.write("fuzz/Cargo.toml", DECLARES)
        self.write("fuzz/Cargo.lock", FLATTENED)
        git(self.repo, "add", "fuzz")
        git(self.repo, "commit", "-q", "-m", "committed flattened nested lock")
        self.stage("Cargo.lock", SOUND + "# touched\n")
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.stage("fuzz/Cargo.lock", FLATTENED + "# touched\n")
        self.assertIn("fuzz/Cargo.lock", self.refused(check_staged(self.repo)))

    def test_a_flattened_staged_lock_is_refused_and_named(self) -> None:
        self.stage("Cargo.lock", FLATTENED)
        stderr = self.refused(check_staged(self.repo))
        self.assertIn(
            "LOCK FORM VIOLATION (staged): Cargo.lock: `provider` locked without a git source", stderr
        )
        self.assertNotIn("SKIP_LOCKFILE_CHECK", stderr)

    def test_one_provider_stripped_while_another_keeps_its_source_is_refused(self) -> None:
        """The partial strip: first-party sources remain in the lock, so a test
        for their total absence passes it and only the per-package rule sees it."""
        self.stage(
            "Cargo.toml",
            manifest(dependencies=f"provider = {GIT}\nsecond = {GIT.replace('provider', 'second')}"),
        )
        self.stage(
            "Cargo.lock",
            SOUND + '\n[[package]]\nname = "second"\nversion = "0.1.0"\n',
        )
        stderr = self.refused(check_staged(self.repo))
        self.assertIn("`second` locked without a git source", stderr)
        self.assertNotIn("`provider`", stderr)

    def test_overlay_residue_beside_intact_sources_is_refused(self) -> None:
        self.stage("Cargo.lock", SOUND + RESIDUE)
        self.assertIn("1 [[patch.unused]] table(s)", self.refused(check_staged(self.repo)))

    def test_residue_is_refused_in_a_workspace_declaring_no_provider(self) -> None:
        self.stage("Cargo.toml", DECLARES_NOTHING)
        self.stage("Cargo.lock", FLATTENED + RESIDUE)
        self.assertIn("[[patch.unused]]", self.refused(check_staged(self.repo)))

    def test_a_dependency_in_any_table_counts_as_declared(self) -> None:
        tables = (
            "[dev-dependencies]",
            "[build-dependencies]",
            "[target.'cfg(unix)'.dependencies]",
            "[target.'cfg(unix)'.dev-dependencies]",
        )
        for table in tables:
            with self.subTest(table):
                self.stage("Cargo.toml", manifest(table))
                self.stage("Cargo.lock", FLATTENED)
                self.refused(check_staged(self.repo))

    def test_a_workspace_dependency_a_member_uses_counts_as_declared(self) -> None:
        self.stage(
            "Cargo.toml",
            '[workspace]\nmembers = ["crates/a"]\n\n[workspace.dependencies]\n'
            f"provider = {GIT}\n",
        )
        self.stage("Cargo.lock", FLATTENED)
        self.refused(check_staged(self.repo))

    def test_an_idle_workspace_dependency_is_not_a_violation(self) -> None:
        """Declared but resolved by no crate, so it never reaches the lock."""
        self.stage(
            "Cargo.toml",
            f'[workspace]\nmembers = []\n\n[workspace.dependencies]\nprovider = {GIT}\n',
        )
        self.stage("Cargo.lock", "version = 4\n")
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_a_nested_member_manifest_counts_as_declaring_a_provider(self) -> None:
        self.stage("Cargo.toml", '[workspace]\nmembers = ["crates/a"]\n')
        self.stage("crates/a/Cargo.toml", DECLARES)
        self.stage("Cargo.lock", FLATTENED)
        self.refused(check_staged(self.repo))

    def test_a_staged_nested_lock_is_judged_with_its_own_workspace(self) -> None:
        self.stage("fuzz/Cargo.toml", DECLARES)
        self.stage("fuzz/Cargo.lock", FLATTENED)
        stderr = self.refused(check_staged(self.repo))
        self.assertIn("fuzz/Cargo.lock: `provider` locked without a git source", stderr)

    def test_a_workspace_declaring_no_provider_may_have_a_lock_without_one(self) -> None:
        self.stage("Cargo.toml", DECLARES_NOTHING)
        self.stage("Cargo.lock", FLATTENED)
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_a_manifest_that_does_not_parse_refuses_the_commit(self) -> None:
        self.stage("Cargo.toml", "[package\n")
        self.stage("Cargo.lock", SOUND + "# touched\n")
        self.assertIn("does not parse", self.refused(check_staged(self.repo)))

    def test_a_cross_repository_fixture_lock_is_not_judged(self) -> None:
        self.stage("Cargo.toml", manifest(dependencies='x = { path = "../../sibling" }'))
        self.stage("Cargo.lock", FLATTENED + RESIDUE)
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_the_index_is_judged_not_the_repaired_working_file(self) -> None:
        self.stage("Cargo.lock", FLATTENED)
        self.write("Cargo.lock", SOUND)
        self.refused(check_staged(self.repo))

    def test_a_flattened_working_file_is_not_judged_when_the_index_is_sound(self) -> None:
        self.stage("Cargo.lock", SOUND + "# touched\n")
        self.write("Cargo.lock", FLATTENED)
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_the_declaration_is_read_from_the_index_not_the_working_manifest(self) -> None:
        self.stage("Cargo.lock", FLATTENED)
        self.write("Cargo.toml", DECLARES_NOTHING)
        self.refused(check_staged(self.repo))

    def test_a_staged_deletion_of_the_lock_is_not_judged(self) -> None:
        git(self.repo, "rm", "-q", "Cargo.lock")
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)


class PrivateIndexTests(StagedFixture):
    """A hook commit may stage through a private `GIT_INDEX_FILE`; the check
    must read that index, since the shared one holds nothing of the commit."""

    def private_index_staging(self, name: str, text: str) -> dict[str, str]:
        index = str(self.repo / ".git" / "private-index")
        env = {"GIT_INDEX_FILE": index}
        git(self.repo, "read-tree", "HEAD", env=env)
        blob = subprocess.run(
            ["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"],
            input=text.encode("utf-8"),
            capture_output=True,
            check=True,
        ).stdout.decode().strip()
        git(self.repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{name}", env=env)
        return env

    def test_a_flattened_lock_staged_through_a_private_index_is_refused(self) -> None:
        env = self.private_index_staging("Cargo.lock", FLATTENED)
        self.refused(check_staged(self.repo, env))

    def test_the_shared_index_alone_holds_nothing_to_judge(self) -> None:
        self.private_index_staging("Cargo.lock", FLATTENED)
        completed = check_staged(self.repo)
        self.assertEqual(completed.returncode, 0, completed.stderr)


class GitFailureTests(StagedFixture):
    """A listing that errors is a refusal, never an empty listing."""

    def run_with_failing(self, command: str) -> tuple[int, str]:
        real = lockfile.run_git
        repo = self.repo

        def failing(arguments, repository=None, stdin=None):
            if arguments[0] == command:
                raise lockfile.GitUnavailable(f"git {command} exited 128: injected")
            return real(arguments, repository if repository is not None else repo, stdin)

        stderr = io.StringIO()
        lockfile.run_git = failing
        try:
            with contextlib.redirect_stderr(stderr):
                status = lockfile.check_staged()
        finally:
            lockfile.run_git = real
        return status, stderr.getvalue()

    def test_a_failing_listing_of_the_index_refuses_the_commit(self) -> None:
        self.stage("Cargo.lock", FLATTENED)
        status, stderr = self.run_with_failing("ls-files")
        self.assertEqual(status, 1)
        self.assertIn("injected", stderr)

    def test_a_failing_read_of_the_staged_paths_refuses_the_commit(self) -> None:
        self.stage("Cargo.lock", FLATTENED)
        status, stderr = self.run_with_failing("diff")
        self.assertEqual(status, 1)
        self.assertIn("injected", stderr)

    def test_a_failing_read_of_the_blobs_refuses_the_commit(self) -> None:
        self.stage("Cargo.lock", FLATTENED)
        status, _ = self.run_with_failing("cat-file")
        self.assertEqual(status, 1)

    def test_the_same_commit_without_a_failure_is_judged_normally(self) -> None:
        self.stage("Cargo.lock", FLATTENED)
        status, stderr = self.run_with_failing("no-such-command")
        self.assertEqual(status, 1)
        self.assertIn("locked without a git source", stderr)


if __name__ == "__main__":
    unittest.main()
