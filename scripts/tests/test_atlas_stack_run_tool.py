#!/usr/bin/env python3
"""`atlas_stack.run_tool` runs a tool workspace binary from inside that workspace.

rustup resolves the toolchain from cargo's working directory, not from
`--manifest-path`. Two scripts once ran the version-guard tool from the stack
root, whose host-qualified msvc pin no Linux runner can install; every
version-guard run failed from 2026-08-25 until the invocations moved here.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "atlas_stack.py"
SPEC = importlib.util.spec_from_file_location("atlas_stack_run_tool_under_test", SCRIPT)
atlas_stack = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = atlas_stack
SPEC.loader.exec_module(atlas_stack)


class RunToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls: list[tuple[list[str], dict]] = []
        self.original_run = atlas_stack.subprocess.run

        def fake_run(command, **options):
            self.calls.append((list(command), options))
            return subprocess.CompletedProcess(command, 0, "", "")

        atlas_stack.subprocess.run = fake_run

    def tearDown(self) -> None:
        atlas_stack.subprocess.run = self.original_run

    def test_runs_from_the_tool_workspace_not_the_stack_root(self) -> None:
        atlas_stack.run_tool("version-guard", ["coherence"])
        command, options = self.calls[-1]
        workspace = atlas_stack.ROOT / "tools" / "version-guard"
        self.assertEqual(options["cwd"], workspace)
        self.assertEqual(
            command,
            ["cargo", "run", "--quiet", "--manifest-path", str(workspace / "Cargo.toml"),
             "--", "coherence"],
        )

    def test_passes_run_options_through_and_never_raises_on_failure(self) -> None:
        env = {"PATH": "x"}
        atlas_stack.run_tool(
            "gitlink-coherence", ["audit", "--format", "json"],
            env=env, timeout=7, capture_output=True, encoding="utf-8", errors="replace",
        )
        _, options = self.calls[-1]
        self.assertEqual((options["env"], options["timeout"], options["check"]), (env, 7, False))
        self.assertTrue(options["capture_output"])

    def test_every_tool_workspace_carries_a_bare_version_pin(self) -> None:
        # The property the helper relies on: a channel without a host triple
        # resolves on any runner.
        pins = sorted((atlas_stack.ROOT / "tools").glob("*/rust-toolchain.toml"))
        self.assertTrue(pins)
        for pin in pins:
            channels = [
                line for line in pin.read_text(encoding="utf-8").splitlines()
                if line.startswith("channel")
            ]
            self.assertEqual(len(channels), 1, pin)
            for marker in ("-pc-", "-unknown-", "-apple-"):
                self.assertNotIn(marker, channels[0], f"{pin} pins a host-qualified channel")


if __name__ == "__main__":
    unittest.main()
