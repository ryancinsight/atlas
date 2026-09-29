"""Verify the Git wrapper delegates process ownership without changing semantics."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import atlas_git_process  # noqa: E402
import process_tree  # noqa: E402


class GitProcessTests(unittest.TestCase):
    def test_clean_environment_removes_repository_selection(self):
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "GIT_DIR": "other.git",
            "GIT_WORK_TREE": "other-tree",
            "GIT_INDEX_FILE": "other-index",
        }

        cleaned = atlas_git_process.clean_process_env(environment)

        self.assertEqual(cleaned, {"PATH": environment["PATH"]})
        self.assertEqual(environment["GIT_DIR"], "other.git")

    def test_execute_process_preserves_binary_streams_and_status(self):
        command = (
            "import sys; payload=sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(payload); "
            "sys.stderr.buffer.write(b'error'); raise SystemExit(19)"
        )

        result = atlas_git_process.execute_process(
            [sys.executable, "-c", command], stdin=b"input\x00", timeout=5
        )

        self.assertEqual(result.command, (sys.executable, "-c", command))
        self.assertEqual(result.returncode, 19)
        self.assertEqual(result.stdout, b"input\x00")
        self.assertEqual(result.stderr, b"error")

    def test_explicit_private_index_is_preserved(self):
        completed = subprocess.CompletedProcess(
            ["git", "status"], 0, stdout=b"", stderr=b""
        )
        with patch.object(process_tree, "run", return_value=completed) as run:
            atlas_git_process.execute_process(
                ["git", "status"],
                env={"GIT_INDEX_FILE": "private-index"},
                timeout=5,
            )

        self.assertEqual(run.call_args.kwargs["env"]["GIT_INDEX_FILE"], "private-index")

    def test_timeout_maps_to_typed_git_error(self):
        timeout = process_tree.ProcessTreeTimeout(
            ["git", "status"], 3, b"partial", b"", None
        )
        with (
            patch.object(process_tree, "run", side_effect=timeout),
            self.assertRaises(atlas_git_process.GitProcessError) as raised,
        ):
            atlas_git_process.execute_process(["git", "status"], timeout=3)

        self.assertTrue(raised.exception.timed_out)
        self.assertIn("git status", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
