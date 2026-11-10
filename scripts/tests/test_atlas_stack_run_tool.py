#!/usr/bin/env python3
"""`atlas_stack.run_tool` runs a tool workspace binary from inside that workspace.

rustup resolves the toolchain from cargo's working directory, not from
`--manifest-path`. Two scripts once ran the version-guard tool from the stack
root, whose host-qualified msvc pin no Linux runner can install; every
version-guard run failed from 2026-08-25 until the invocations moved here.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
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
        self.configs: list[str] = []
        self.original_load_sibling = atlas_stack.load_sibling

        class OutputMode:
            CAPTURE = "capture"
            INHERIT = "inherit"

        def fake_run(command, **options):
            self.calls.append((list(command), options))
            self.configs.append(Path(command[2]).read_text(encoding="utf-8"))
            return subprocess.CompletedProcess(command, 0, b"output", b"error")

        process_tree = types.SimpleNamespace(OutputMode=OutputMode, run=fake_run)
        atlas_stack.load_sibling = lambda name, *_: (
            process_tree if name == "atlas_process_tree" else self.original_load_sibling(name, *_)
        )

    def tearDown(self) -> None:
        atlas_stack.load_sibling = self.original_load_sibling

    def test_runs_from_the_tool_workspace_not_the_stack_root(self) -> None:
        atlas_stack.run_tool("version-guard", ["coherence"])
        command, options = self.calls[-1]
        workspace = atlas_stack.ROOT / "tools" / "version-guard"
        self.assertNotEqual(options["cwd"], workspace)
        self.assertEqual(command[-7:], ["run", "--quiet", "--locked", "--manifest-path",
                                       str(workspace / "Cargo.toml"), "--", "coherence"])
        self.assertNotIn("[patch", self.configs[-1])
        self.assertIn('["profile"."dev"]', self.configs[-1])
        self.assertEqual(json.loads(command[4].partition("=")[2])[-1], str(workspace))

    def test_passes_run_options_through_and_never_raises_on_failure(self) -> None:
        env = {"PATH": "x", "GIT_DIR": "foreign", "RUSTUP_TOOLCHAIN": "foreign"}
        atlas_stack.run_tool(
            "gitlink-coherence", ["audit", "--format", "json"],
            env=env, timeout=7, capture_output=True, encoding="utf-8", errors="replace",
        )
        _, options = self.calls[-1]
        self.assertEqual((options["env"]["PATH"], options["timeout"]), ("x", 7))
        self.assertEqual(options["env"]["CARGO_TARGET_DIR"], str(atlas_stack.ROOT / "target"))
        self.assertRegex(options["env"]["RUSTUP_TOOLCHAIN"], r"^\d+\.\d+\.\d+$")
        self.assertNotIn("GIT_DIR", options["env"])
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


@unittest.skipUnless(shutil.which("cargo"), "cargo is required")
class RealCargoRunToolTests(unittest.TestCase):
    def test_excludes_unused_patch_without_changing_lock_or_binary_cwd(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        workspace = root / "tools" / "probe"
        (workspace / "src").mkdir(parents=True)
        provider = root / "provider"
        (provider / "src").mkdir(parents=True)
        (root / ".cargo").mkdir()
        package = "atlas-run-tool-probe"
        (workspace / "Cargo.toml").write_text(
            f'[package]\nname="{package}"\nversion="0.1.0"\nedition="2024"\n', encoding="utf-8")
        (workspace / "Cargo.lock").write_text(
            f'version = 4\n\n[[package]]\nname = "{package}"\nversion = "0.1.0"\n', encoding="utf-8")
        (workspace / "rust-toolchain.toml").write_text(
            '[toolchain]\nchannel = "1.97.0"\nprofile = "minimal"\n', encoding="utf-8")
        (workspace / "src" / "main.rs").write_text(
            'fn main() { println!("{}|{}", std::env::current_dir().unwrap().display(), '
            'cfg!(panic = "abort")); }\n', encoding="utf-8")
        (provider / "Cargo.toml").write_text(
            '[package]\nname="unused"\nversion="0.1.0"\nedition="2024"\n', encoding="utf-8")
        (provider / "src" / "lib.rs").write_text('pub fn value() -> u8 { 1 }\n', encoding="utf-8")
        (root / ".cargo" / "config.toml").write_text(
            '[build]\ntarget-dir="target"\n[profile.dev]\npanic="abort"\n'
            '[patch.crates-io]\nunused={path="provider"}\n', encoding="utf-8")
        original_root, original_tools = atlas_stack.ROOT, atlas_stack.TOOL_ROOT
        atlas_stack.ROOT, atlas_stack.TOOL_ROOT = root, root / "tools"
        self.addCleanup(setattr, atlas_stack, "ROOT", original_root)
        self.addCleanup(setattr, atlas_stack, "TOOL_ROOT", original_tools)
        before = (workspace / "Cargo.lock").read_bytes()
        target = Path(os.environ.get("CARGO_TARGET_DIR", root / "target")).resolve()
        process_tree = atlas_stack.load_sibling(
            "atlas_real_process_tree", SCRIPT.parent / "process_tree.py"
        )
        inherited = process_tree.run(
            ["cargo", "metadata", "--locked", "--format-version", "1"],
            cwd=workspace,
            env={**os.environ, "RUSTUP_TOOLCHAIN": "1.97.0", "CARGO_NET_OFFLINE": "true",
                 "CARGO_TARGET_DIR": str(target)},
            timeout=60,
            output_mode=process_tree.OutputMode.CAPTURE,
        )
        self.assertNotEqual(inherited.returncode, 0)
        self.assertIn(b"lock file", inherited.stderr)
        self.assertEqual((workspace / "Cargo.lock").read_bytes(), before)
        for _ in range(2):
            result = atlas_stack.run_tool(
                "probe", [], capture_output=True, encoding="utf-8", timeout=120,
                env={**os.environ, "CARGO_NET_OFFLINE": "true", "CARGO_TARGET_DIR": str(target)},
            )
            self.assertEqual((result.returncode, result.stderr), (0, ""))
            self.assertEqual(result.stdout.strip(), f"{workspace}|true")
        self.assertEqual((workspace / "Cargo.lock").read_bytes(), before)
        binary = package + (".exe" if os.name == "nt" else "")
        executable = target / "debug" / binary
        self.assertEqual(executable.resolve().parent, (target / "debug").resolve())
        self.assertTrue(executable.is_file())


if __name__ == "__main__":
    unittest.main()
