#!/usr/bin/env python3
"""The flattened-lock diagnosis must consult what the workspace declares.

A lock with no first-party git sources is the overlay's signature only when
the manifests declare first-party git dependencies. The atlas tool workspaces
declare none, so their locks legitimately carry no such source; `--check`
reported every one of them as flattened.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_heuristic", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)

THIRD_PARTY_ONLY = {"packages": [{"name": "tool", "dependencies": [
    {"name": "serde", "source": "registry+https://github.com/rust-lang/crates.io-index"},
]}]}
WITH_FIRST_PARTY = {"packages": [{"name": "member", "dependencies": [
    {"name": "serde", "source": "registry+https://github.com/rust-lang/crates.io-index"},
    {"name": "themis", "source": "git+https://github.com/ryancinsight/themis?branch=main"},
]}]}
LOCK_WITHOUT_GIT_SOURCES = '''version = 4

[[package]]
name = "serde"
version = "1.0.219"
source = "registry+https://github.com/rust-lang/crates.io-index"
'''
LOCK_WITH_GIT_SOURCE = LOCK_WITHOUT_GIT_SOURCES + '''
[[package]]
name = "themis"
version = "0.4.0"
source = "git+https://github.com/ryancinsight/themis?branch=main#abc"
'''


class FirstPartyHeuristicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-lockfile-heuristic-")
        self.original = (lockfile.subprocess.run, lockfile.LOCKFILE)
        lockfile.LOCKFILE = Path(self.temp.name) / "Cargo.lock"

    def tearDown(self) -> None:
        lockfile.subprocess.run, lockfile.LOCKFILE = self.original
        self.temp.cleanup()

    def _cargo(self, metadata: dict) -> None:
        def fake_run(command, **_kwargs):
            return subprocess.CompletedProcess(command, 0, json.dumps(metadata), "")
        lockfile.subprocess.run = fake_run

    def _check(self) -> tuple[int, str]:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = lockfile.check()
        return code, stderr.getvalue()

    def test_a_workspace_without_first_party_dependencies_passes_with_no_git_sources(self) -> None:
        lockfile.LOCKFILE.write_text(LOCK_WITHOUT_GIT_SOURCES, encoding="utf-8")
        self._cargo(THIRD_PARTY_ONLY)
        code, stderr = self._check()
        self.assertEqual((code, stderr), (0, ""))

    def test_a_workspace_with_first_party_dependencies_is_flattened_when_none_resolve_to_git(self) -> None:
        lockfile.LOCKFILE.write_text(LOCK_WITHOUT_GIT_SOURCES, encoding="utf-8")
        self._cargo(WITH_FIRST_PARTY)
        code, stderr = self._check()
        self.assertEqual(code, 1)
        self.assertIn("contains no first-party git sources", stderr)

    def test_a_lock_carrying_its_first_party_sources_passes(self) -> None:
        lockfile.LOCKFILE.write_text(LOCK_WITH_GIT_SOURCE, encoding="utf-8")
        self._cargo(WITH_FIRST_PARTY)
        self.assertEqual(self._check(), (0, ""))


if __name__ == "__main__":
    unittest.main()
