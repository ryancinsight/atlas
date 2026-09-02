#!/usr/bin/env python3
"""`lockfile.py --manifest-path` must reach the cargo invocation.

The overlay runner once declared `manifest: Path = MANIFEST`, binding the
umbrella manifest at definition time; `main`'s `global MANIFEST` reassignment
under `--manifest-path` therefore never reached cargo, and regenerating a tool
workspace's lock silently regenerated the umbrella's instead.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_manifest", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)


class ManifestPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.argv: list[list[str]] = []
        self.original_run = lockfile.subprocess.run
        self.original_manifest = lockfile.MANIFEST

        def fake_run(command, **_kwargs):
            self.argv.append(list(command))
            return subprocess.CompletedProcess(command, 0, "", "")

        lockfile.subprocess.run = fake_run

    def tearDown(self) -> None:
        lockfile.subprocess.run = self.original_run
        lockfile.MANIFEST = self.original_manifest

    def _manifest_argument(self) -> str:
        command = self.argv[-1]
        return command[command.index("--manifest-path") + 1]

    def test_default_follows_the_module_manifest_at_call_time(self) -> None:
        redirected = Path("D:/elsewhere/tools/version-guard/Cargo.toml")
        lockfile.MANIFEST = redirected
        lockfile.run_outside_the_overlay(["metadata", "--locked"])
        self.assertEqual(self._manifest_argument(), str(redirected))

    def test_an_explicit_manifest_wins_over_the_module_default(self) -> None:
        explicit = Path("D:/member/Cargo.toml")
        lockfile.run_outside_the_overlay(["metadata"], manifest=explicit)
        self.assertEqual(self._manifest_argument(), str(explicit))

    def test_the_umbrella_manifest_is_the_default_when_nothing_redirects(self) -> None:
        lockfile.run_outside_the_overlay(["metadata"])
        self.assertEqual(self._manifest_argument(), str(self.original_manifest))


if __name__ == "__main__":
    unittest.main()
