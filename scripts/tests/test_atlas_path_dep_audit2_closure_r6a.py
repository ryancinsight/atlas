#!/usr/bin/env python3
"""Tests for the round-6a path-dep commit file-list verifier.

The verifier enforces that every r6a `Apply round-6a` commit is
strictly `Cargo.toml + Cargo.lock` (workspace roots allow `Cargo.lock`
alone). This is the SSOT for ATLAS-R6A-FILELIST-001; future r6a
amends or new r6a commits must keep the rule.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-path-dep-audit2-closure-r6a.py"
_SPEC = importlib.util.spec_from_file_location(
    "atlas_path_dep_audit2_closure_r6a", SCRIPT
)
assert _SPEC is not None and _SPEC.loader is not None
_mod = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _mod
_SPEC.loader.exec_module(_mod)


def _make_repo(path: Path, files: list[str]) -> str:
    """Build a tiny git repo at `path` whose HEAD commit touches `files`."""
    subprocess.check_call(["git", "init", "--initial-branch=main", str(path)])
    subprocess.check_call(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"]
    )
    subprocess.check_call(
        ["git", "-C", str(path), "config", "user.name", "Test"]
    )
    for f in files:
        file_path = path / f
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")
    subprocess.check_call(["git", "-C", str(path), "add", "-A"])
    subprocess.check_call(
        ["git", "-C", str(path), "commit", "-m", "Apply round-6a atlas-root path resolution"]
    )
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


class R6aVerifierTestCase(unittest.TestCase):
    def _run_with_overrides(
        self,
        commits: list[tuple[str, str, bool]],
        repo_root: Path,
    ) -> int:
        orig = _mod.R6A_COMMITS
        _mod.R6A_COMMITS = commits
        try:
            return _mod.main(["--repo-root", str(repo_root)])
        finally:
            _mod.R6A_COMMITS = orig

    def test_passes_on_clean_cargo_only_commit(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            sha = _make_repo(root_path / "fake", ["Cargo.toml", "Cargo.lock"])
            rc = self._run_with_overrides(
                [("fake", sha, False)], root_path,
            )
            self.assertEqual(rc, 0)

    def test_passes_on_workspace_root_cargo_lock_only(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            sha = _make_repo(root_path / "fake", ["Cargo.lock"])
            rc = self._run_with_overrides(
                [("fake", sha, True)], root_path,
            )
            self.assertEqual(rc, 0)

    def test_fails_on_extra_non_cargo_file(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            sha = _make_repo(
                root_path / "fake",
                ["Cargo.toml", "Cargo.lock", "README.md"],
            )
            rc = self._run_with_overrides(
                [("fake", sha, False)], root_path,
            )
            self.assertEqual(rc, 1)

    def test_fails_on_workspace_root_with_cargo_toml(self) -> None:
        """A workspace root legitimately moves only Cargo.lock; if the
        commit also touches Cargo.toml the verifier must reject it."""
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            sha = _make_repo(
                root_path / "fake",
                ["Cargo.toml", "Cargo.lock"],
            )
            rc = self._run_with_overrides(
                [("fake", sha, True)], root_path,
            )
            self.assertEqual(rc, 1)

    def test_fails_when_worktree_missing(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            rc = self._run_with_overrides(
                [("does-not-exist", "deadbeef", False)], root_path,
            )
            self.assertEqual(rc, 1)

    def test_passes_on_current_stack_state(self) -> None:
        """The live D:/atlas state must pass — this is the regression
        gate that locks in ATLAS-R6A-FILELIST-001's accepted state."""
        repo_root = Path(__file__).resolve().parents[2] / "repos"
        if not repo_root.is_dir():
            self.skipTest("atlas repo root not present in this environment")
        rc = self._run_with_overrides(_mod.R6A_COMMITS, repo_root)
        self.assertEqual(rc, 0, "live r6a commits must remain cargo-only")


if __name__ == "__main__":
    unittest.main()
