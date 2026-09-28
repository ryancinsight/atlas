#!/usr/bin/env python3
"""Tests for the build identity command line."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from atlas_build_identity_test_support import (
    BuildIdentityFixture,
    build_workflow,
    identity,
    init_repo,
    write_script,
)


class CommandLineTestCase(BuildIdentityFixture):
    """The entry point accepts the exact argument shape the member pre-push passes."""

    _run_checked = staticmethod(build_workflow._run_checked)

    def _skip_cargo_clean(self, command, cwd, environment, target_root) -> None:
        # The CLI cannot inject a clean command; keep the test off real Cargo.
        if list(command[:2]) == ["cargo", "clean"]:
            return
        self._run_checked(command, cwd, environment, target_root)

    def test_the_pre_push_invocation_parses_and_runs(self) -> None:
        cli_path = Path(__file__).resolve().parents[1] / "atlas-build-identity.py"
        cli_spec = importlib.util.spec_from_file_location("atlas_build_identity_cli", cli_path)
        assert cli_spec is not None and cli_spec.loader is not None
        cli = importlib.util.module_from_spec(cli_spec)
        cli_spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory(prefix="atlas-build-identity-cli-") as temp:
            base = Path(temp)
            root = base / "member"
            init_repo(root, "fn main() {}\n")
            target = base / "target"
            artifact = target / "debug" / "deps" / "libdemo.rlib"
            build = base / "build.py"
            write_script(
                build,
                "from pathlib import Path\n"
                f"path = Path({str(artifact)!r})\n"
                "path.parent.mkdir(parents=True, exist_ok=True)\n"
                "path.write_text('built', encoding='utf-8')\n",
            )
            with (
                patch.object(cli, "run_build", wraps=build_workflow.run_build) as run_build,
                patch.object(identity, "toolchain_identity", return_value="rustc-test"),
                patch.object(build_workflow, "_run_checked", side_effect=self._skip_cargo_clean),
            ):
                code = cli.main([
                    "run",
                    "--root", str(root),
                    "--package", "demo",
                    "--target-dir", str(target),
                    "--profile", "debug",
                    "--target", "host",
                    "--manifest", str(root / "Cargo.toml"),
                    "--command-cwd", str(root),
                    "--command-key", "atlas-pre-push:demo",
                    "--ignore-path", str(root / "Cargo.lock"),
                    "--manifest", str(root / "Cargo.toml"),
                    "--",
                    sys.executable, str(build),
                ])
            self.assertEqual(code, 0)
            kwargs = run_build.call_args.kwargs
            self.assertEqual(kwargs["command_key"], "atlas-pre-push:demo")
            self.assertEqual(kwargs["command_cwd"], root)
            self.assertEqual(kwargs["ignore_paths"], [root / "Cargo.lock"])
            self.assertEqual(artifact.read_text(encoding="utf-8"), "built")


    def test_command_cwd_is_used_without_changing_record_scope(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        execution_root = self.base / "execution"
        execution_root.mkdir()
        cwd_marker = self.base / "command-cwd.txt"
        command_script = self.base / "record-cwd.py"
        write_script(
            command_script,
            "import os\n"
            "from pathlib import Path\n"
            f"Path({str(cwd_marker)!r}).write_text(os.getcwd(), encoding='utf-8')\n"
            f"Path({str(self.artifact)!r}).write_text('built\\n', encoding='utf-8')\n",
        )
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            result = build_workflow.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(command_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, "-c", "pass"],
                command_cwd=execution_root,
            )
        record = json.loads(result.record_path.read_text(encoding="utf-8"))
        self.assertNotIn("command_cwd", record["build"])
        self.assertEqual(cwd_marker.read_text(encoding="utf-8"), str(execution_root.resolve()))

    def test_commands_run_in_the_requested_directory(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        elsewhere = self.base / "gate-cwd"
        elsewhere.mkdir()
        marker = self.base / "cwd.txt"
        record_cwd = self.base / "record_cwd.py"
        write_script(
            record_cwd,
            "import os, sys\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text(os.getcwd(), encoding='utf-8')\n"
            f"exec(open({str(self.build_script)!r}).read())\n",
        )
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {"ARTIFACT": str(self.artifact), "SOURCE_TOKEN": "cwd", "CLEAN_LOG": str(self.clean_log)},
            ),
        ):
            build_workflow.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(record_cwd)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                command_cwd=elsewhere,
            )
        self.assertEqual(Path(marker.read_text(encoding="utf-8")).resolve(), elsewhere.resolve())

