#!/usr/bin/env python3
"""Excluding the overlay must not also exclude the shared build cache.

`run_outside_the_overlay` runs cargo from a neutral working directory so cargo's
config discovery — which walks up from the *cwd* — cannot reach the stack's
`[patch]` overlay. That is deliberate. What is not deliberate is that the same
mechanism hides `target-dir`, so cargo falls back to `<manifest dir>/target` and
writes a repo-local cache into the member being inspected: the `target_forks`
class the conformance ratchet counts, produced by the tooling that measures it.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_target", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)


class SharedTargetDirTestCase(unittest.TestCase):
    def stack(self, config_body: str | None) -> tuple[Path, Path]:
        """A stack root with an optional `.cargo/config.toml`, and a member manifest."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: None)
        member = root / "repos" / "member"
        member.mkdir(parents=True)
        (member / "Cargo.toml").write_text("[package]\nname = \"m\"\n", encoding="utf-8")
        if config_body is not None:
            cargo = root / ".cargo"
            cargo.mkdir()
            (cargo / "config.toml").write_text(config_body, encoding="utf-8")
        return root, member / "Cargo.toml"

    def test_target_dir_resolves_against_the_config_that_declares_it(self) -> None:
        root, manifest = self.stack('[build]\ntarget-dir = "target"\n')
        self.assertEqual(lockfile.shared_target_dir(manifest), (root / "target").resolve())

    def test_a_member_config_wins_over_the_stack_root(self) -> None:
        """Nearest config first: walking up stops at the first declaration."""
        root, manifest = self.stack('[build]\ntarget-dir = "target"\n')
        member_cargo = manifest.parent / ".cargo"
        member_cargo.mkdir()
        (member_cargo / "config.toml").write_text(
            '[build]\ntarget-dir = "own"\n', encoding="utf-8"
        )
        self.assertEqual(
            lockfile.shared_target_dir(manifest), (manifest.parent / "own").resolve()
        )

    def test_absent_config_yields_none(self) -> None:
        """CI has no stack config, and each job is isolated: nothing to restore."""
        _, manifest = self.stack(None)
        self.assertIsNone(lockfile.shared_target_dir(manifest))

    def test_config_without_a_target_dir_yields_none(self) -> None:
        _, manifest = self.stack('[build]\nrustflags = []\n')
        self.assertIsNone(lockfile.shared_target_dir(manifest))

    def test_a_commented_declaration_is_not_one(self) -> None:
        _, manifest = self.stack('[build]\n# target-dir = "target"\n')
        self.assertIsNone(lockfile.shared_target_dir(manifest))

    def test_single_quoted_and_padded_values_resolve(self) -> None:
        root, manifest = self.stack("[build]\ntarget-dir   =   'build/out'\n")
        self.assertEqual(
            lockfile.shared_target_dir(manifest), (root / "build/out").resolve()
        )


if __name__ == "__main__":
    unittest.main()
