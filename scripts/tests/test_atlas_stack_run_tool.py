#!/usr/bin/env python3
"""`atlas_stack.run_tool` runs a locked tool binary from inside that workspace.

rustup resolves the toolchain from cargo's working directory, not from
`--manifest-path`. Two scripts once ran the version-guard tool from the stack
root, whose host-qualified msvc pin no Linux runner can install; every
version-guard run failed from 2026-08-25 until the invocations moved here.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
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
        self.original_load_sibling = atlas_stack.load_sibling

        class OutputMode:
            CAPTURE = "capture"
            INHERIT = "inherit"

        def fake_run(command, **options):
            self.calls.append((list(command), options))
            return subprocess.CompletedProcess(command, 0, b"output", b"error")

        process_tree = types.SimpleNamespace(OutputMode=OutputMode, run=fake_run)
        atlas_stack.load_sibling = lambda *_: process_tree

    def tearDown(self) -> None:
        atlas_stack.load_sibling = self.original_load_sibling

    def test_runs_from_the_tool_workspace_not_the_stack_root(self) -> None:
        atlas_stack.run_tool("version-guard", ["coherence"])
        command, options = self.calls[-1]
        workspace = atlas_stack.ROOT / "tools" / "version-guard"
        self.assertEqual(options["cwd"], workspace)
        self.assertEqual(
            command,
            ["cargo", "run", "--quiet", "--locked", "--manifest-path", str(workspace / "Cargo.toml"),
             "--", "coherence"],
        )

    def test_passes_run_options_through_and_never_raises_on_failure(self) -> None:
        env = {"PATH": "x"}
        atlas_stack.run_tool(
            "gitlink-coherence", ["audit", "--format", "json"],
            env=env, timeout=7, capture_output=True, encoding="utf-8", errors="replace",
        )
        _, options = self.calls[-1]
        self.assertEqual((options["env"], options["timeout"]), (env, 7))
        self.assertEqual(options["output_mode"], "capture")

    def test_decodes_captured_text_and_encodes_input(self) -> None:
        result = atlas_stack.run_tool(
            "version-guard", ["requirements"], input="rows", capture_output=True,
            encoding="utf-8", errors="replace", timeout=7,
        )
        _, options = self.calls[-1]
        self.assertEqual(options["input"], b"rows")
        self.assertEqual((result.stdout, result.stderr), ("output", "error"))

    def test_defaults_to_the_bounded_process_tree_runner(self) -> None:
        atlas_stack.run_tool("version-guard", ["coherence"])
        _, options = self.calls[-1]
        self.assertEqual(options["timeout"], 600)
        self.assertEqual(options["output_mode"], "inherit")

    def test_every_tool_workspace_carries_a_bare_version_pin(self) -> None:
        # The property the helper relies on: a channel without a host triple
        # resolves on any runner.
        pins = sorted((atlas_stack.ROOT / "tools").glob("*/rust-toolchain.toml"))
        self.assertTrue(pins)
        for pin in pins:
            self.assertTrue((pin.parent / "Cargo.lock").is_file(), pin.parent)
            channels = [
                line for line in pin.read_text(encoding="utf-8").splitlines()
                if line.startswith("channel")
            ]
            self.assertEqual(len(channels), 1, pin)
            for marker in ("-pc-", "-unknown-", "-apple-"):
                self.assertNotIn(marker, channels[0], f"{pin} pins a host-qualified channel")


if __name__ == "__main__":
    unittest.main()
