#!/usr/bin/env python3
"""`--check` judges every lock under the repository by the one standalone rule.

The push hook and the shared `lockfile-guard` workflow run `--check` on a tree
that is not a repository to ask (a `git archive` export, a CI checkout), so the
rule is applied to the manifests and locks on disk: the same `judge_locks` that
`--check-staged` and `--check-committed` apply. These tests run `check()` over
real files; only the `cargo metadata --locked` staleness arm is stood in for,
since resolving needs a registry or a network.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_check", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)

NO_DEPENDENCIES = '[package]\nname = "tool"\nversion = "0.1.0"\n'
TWO_GIT_DEPENDENCIES = (
    '[package]\nname = "member"\nversion = "0.1.0"\n\n[dependencies]\n'
    'themis = { git = "https://github.com/ryancinsight/themis", branch = "main" }\n'
    'leto = { git = "https://github.com/ryancinsight/leto", branch = "main" }\n'
)
SERDE = (
    '[[package]]\nname = "serde"\nversion = "1.0.219"\n'
    'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
)


def git_package(name: str, sourced: bool = True) -> str:
    source = (
        f'source = "git+https://github.com/ryancinsight/{name}?branch=main#abc123"\n'
        if sourced
        else ""
    )
    return f'\n[[package]]\nname = "{name}"\nversion = "0.4.0"\n{source}'


def residue(name: str) -> str:
    """What the overlay leaves for a `[patch]` it did not consume: no source."""
    return f'\n[[patch.unused]]\nname = "{name}"\nversion = "0.4.0"\n'


class CheckJudgesEveryLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-lockfile-check-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.original = (
            lockfile.subprocess.run,
            lockfile.REPOSITORY,
            lockfile.LOCKFILE,
            lockfile.SCRIPT_CHECKOUT,
        )
        self.addCleanup(self._restore)
        lockfile.REPOSITORY = self.root
        lockfile.LOCKFILE = self.root / "Cargo.lock"
        lockfile.SCRIPT_CHECKOUT = Path(self.temp.name) / "elsewhere"
        self.resolves = True
        self.resolution_calls = 0

        def fake_run(command, **_kwargs):
            self.resolution_calls += 1
            return subprocess.CompletedProcess(
                command, 0 if self.resolves else 101, "{}", "" if self.resolves else "stale"
            )

        lockfile.subprocess.run = fake_run

    def _restore(self) -> None:
        (
            lockfile.subprocess.run,
            lockfile.REPOSITORY,
            lockfile.LOCKFILE,
            lockfile.SCRIPT_CHECKOUT,
        ) = self.original

    def _write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def _check(self) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = lockfile.check()
        return code, stderr.getvalue()

    def test_a_workspace_without_git_dependencies_passes_with_no_git_sources(self) -> None:
        self._write("Cargo.toml", NO_DEPENDENCIES)
        self._write("Cargo.lock", SERDE)
        self.assertEqual(self._check(), (0, ""))

    def test_a_lock_carrying_its_git_sources_passes(self) -> None:
        self._write("Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("Cargo.lock", SERDE + git_package("themis") + git_package("leto"))
        self.assertEqual(self._check(), (0, ""))

    def test_a_lock_that_lost_every_git_source_is_refused(self) -> None:
        self._write("Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("Cargo.lock", SERDE + git_package("themis", False) + git_package("leto", False))
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("Cargo.lock: `themis` locked without a git source", stderr)
        self.assertEqual(self.resolution_calls, 0, "a flattened lock is not resolved")

    def test_a_partly_stripped_lock_is_refused(self) -> None:
        """One surviving `git+` line used to pass the count; the rule names the
        dependency that lost its source."""
        self._write("Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("Cargo.lock", SERDE + git_package("themis") + git_package("leto", False))
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("`leto` locked without a git source", stderr)
        self.assertNotIn("`themis`", stderr)

    def test_patch_residue_beside_intact_sources_is_refused(self) -> None:
        """The overlay writes `[[patch.unused]]` with no source line, so a lock
        whose sources are all present can still carry the defect."""
        self._write("Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write(
            "Cargo.lock",
            SERDE + git_package("themis") + git_package("leto") + residue("themis"),
        )
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("1 [[patch.unused]] table(s): overlay residue", stderr)

    def test_patch_residue_in_a_workspace_declaring_no_git_dependency_is_refused(self) -> None:
        self._write("Cargo.toml", NO_DEPENDENCIES)
        self._write("Cargo.lock", SERDE + residue("themis"))
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("overlay residue", stderr)

    def test_a_flattened_nested_lock_is_refused_though_the_root_lock_is_sound(self) -> None:
        self._write("Cargo.toml", NO_DEPENDENCIES)
        self._write("Cargo.lock", SERDE)
        self._write("fuzz/Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("fuzz/Cargo.lock", SERDE + git_package("themis") + git_package("leto", False))
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("fuzz/Cargo.lock: `leto` locked without a git source", stderr)

    def test_a_sound_nested_lock_beside_a_sound_root_passes(self) -> None:
        self._write("Cargo.toml", NO_DEPENDENCIES)
        self._write("Cargo.lock", SERDE)
        self._write("fuzz/Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("fuzz/Cargo.lock", SERDE + git_package("themis") + git_package("leto"))
        self.assertEqual(self._check(), (0, ""))

    def test_a_workspace_depending_on_a_sibling_repository_is_exempt_not_judged(self) -> None:
        self._write(
            "Cargo.toml",
            '[package]\nname = "fixture"\nversion = "0.1.0"\n\n[dependencies]\n'
            'sibling = { path = "../../hephaestus" }\n',
        )
        self._write("Cargo.lock", SERDE + residue("themis"))
        self.assertEqual(self._check(), (0, ""))

    def test_the_checkout_the_script_runs_from_is_not_part_of_the_repository(self) -> None:
        """The shared workflow checks Atlas out inside the repository it judges."""
        self._write("Cargo.toml", NO_DEPENDENCIES)
        self._write("Cargo.lock", SERDE)
        self._write("_atlas/tools/Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("_atlas/tools/Cargo.lock", SERDE + residue("themis"))
        lockfile.SCRIPT_CHECKOUT = self.root / "_atlas"
        self.assertEqual(self._check(), (0, ""))
        lockfile.SCRIPT_CHECKOUT = self.root / "elsewhere"
        self.assertEqual(self._check()[0], 1)

    def test_build_output_is_not_judged(self) -> None:
        self._write("Cargo.toml", NO_DEPENDENCIES)
        self._write("Cargo.lock", SERDE)
        self._write("target/debug/build/x/Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("target/debug/build/x/Cargo.lock", SERDE + residue("themis"))
        self.assertEqual(self._check(), (0, ""))

    def test_a_sound_lock_that_does_not_resolve_is_stale_not_flattened(self) -> None:
        self._write("Cargo.toml", TWO_GIT_DEPENDENCIES)
        self._write("Cargo.lock", SERDE + git_package("themis") + git_package("leto"))
        self.resolves = False
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("stale rather than flattened", stderr)
        self.assertIn("cargo said:\nstale", stderr)

    def test_a_missing_root_lock_is_an_error(self) -> None:
        self._write("Cargo.toml", NO_DEPENDENCIES)
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("does not exist", stderr)


if __name__ == "__main__":
    unittest.main()
