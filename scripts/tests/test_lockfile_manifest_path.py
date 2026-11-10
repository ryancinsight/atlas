#!/usr/bin/env python3
"""`lockfile.py --manifest-path` must reach the cargo invocation.

The overlay runner once declared `manifest: Path = MANIFEST`, binding the
umbrella manifest at definition time; `main`'s `global MANIFEST` reassignment
under `--manifest-path` therefore never reached cargo, and regenerating a tool
workspace's lock silently regenerated the umbrella's instead.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
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
        self.original_run = lockfile.run_bounded
        self.original_manifest = lockfile.MANIFEST

        def fake_run(command, **_kwargs):
            self.argv.append(list(command))
            return subprocess.CompletedProcess(command, 0, "", "")

        lockfile.run_bounded = fake_run

    def tearDown(self) -> None:
        lockfile.run_bounded = self.original_run
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


@unittest.skipUnless(shutil.which("cargo"), "needs real Cargo")
class EnvironmentTests(unittest.TestCase):
    def test_real_cargo_receives_explicit_environment_without_parent_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lockfile-env-") as directory:
            root = Path(directory).resolve()
            (root / "src").mkdir()
            (root / "Cargo.toml").write_text(
                '[package]\nname="environment-probe"\nversion="0.1.0"\nedition="2024"\n',
                encoding="utf-8",
            )
            (root / "src/lib.rs").write_text("", encoding="utf-8")
            target = root / "selected-target"
            supplied = {**os.environ, "CARGO_TARGET_DIR": str(target)}
            parent = dict(os.environ)

            result = lockfile.run_outside_the_overlay(
                ["metadata", "--no-deps", "--format-version", "1"],
                manifest=root / "Cargo.toml",
                env=supplied,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)["target_directory"]).resolve(), target)
            self.assertEqual(dict(os.environ), parent)
            self.assertEqual(supplied["CARGO_TARGET_DIR"], str(target))


if __name__ == "__main__":
    unittest.main()
