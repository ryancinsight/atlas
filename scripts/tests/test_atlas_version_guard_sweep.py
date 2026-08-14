#!/usr/bin/env python3
"""Tests for the Atlas version-guard sweep wrapper."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-version-guard-sweep.py"
_SPEC = importlib.util.spec_from_file_location("atlas_version_guard_sweep", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_sweep = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _sweep
_SPEC.loader.exec_module(_sweep)


class VersionGuardSweepTestCase(unittest.TestCase):
    def test_clean_rust_env_removes_compiler_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {"RUSTC": "foreign-rustc", "RUSTDOC": "foreign-rustdoc"},
            clear=False,
        ):
            env = _sweep.clean_rust_env()

        self.assertNotIn("RUSTC", env)
        self.assertNotIn("RUSTDOC", env)

    def test_main_runs_preflight_then_coherence(self) -> None:
        calls: list[tuple[list[str], dict[str, str] | None]] = []

        def fake_run(command: list[str], *, cwd: Path, env: dict[str, str] | None, check: bool) -> object:
            calls.append((command, env))
            return subprocess.CompletedProcess(command, 0)

        with patch.dict(os.environ, {"RUSTC": "", "RUSTDOC": ""}, clear=False):
            with patch.object(_sweep.subprocess, "run", side_effect=fake_run):
                exit_code = _sweep.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0][0], sys.executable)
        self.assertIn("atlas-toolchain-preflight.py", calls[0][0][1])
        self.assertEqual(calls[1][0][0], "cargo")
        self.assertIn("coherence", calls[1][0])
        self.assertIn("--atlas-root", calls[1][0])
        self.assertNotIn("RUSTC", calls[1][1] or {})
        self.assertNotIn("RUSTDOC", calls[1][1] or {})


if __name__ == "__main__":
    unittest.main()
