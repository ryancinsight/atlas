"""Verify the Git wrapper delegates process ownership without changing semantics."""

from __future__ import annotations

import json
import math
import os
import pathlib
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch


SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import atlas_git_process  # noqa: E402
import process_tree  # noqa: E402
from process_tree_support import HANG_GUARD_SECONDS  # noqa: E402


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
            [sys.executable, "-c", command],
            stdin=b"input\x00",
            timeout=HANG_GUARD_SECONDS,
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

    def test_repository_selection_never_reaches_the_child(self):
        keys = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
        child = (
            "import json, os; "
            f"print(json.dumps({{key: os.environ.get(key) for key in {keys!r}}}))"
        )
        inherited = dict.fromkeys(keys, "inherited")
        explicit = {**os.environ, **dict.fromkeys(keys, "explicit")}
        command = [sys.executable, "-c", child]

        with patch.dict(os.environ, inherited):
            from_process = atlas_git_process.execute_process(
                command, timeout=HANG_GUARD_SECONDS
            )
        from_argument = atlas_git_process.execute_process(
            command, env=explicit, timeout=HANG_GUARD_SECONDS
        )

        self.assertEqual(json.loads(from_process.stdout), dict.fromkeys(keys))
        self.assertEqual(
            json.loads(from_argument.stdout),
            {"GIT_DIR": None, "GIT_WORK_TREE": None, "GIT_INDEX_FILE": "explicit"},
        )

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
        self.assertEqual(
            str(raised.exception), "process timed out after 3s: git status"
        )
        self.assertIs(raised.exception.__cause__, timeout)

    def test_timeout_carries_the_cleanup_failure_in_message_and_cause(self):
        timeout = process_tree.ProcessTreeTimeout(
            ["git", "status"], 3, b"partial", b"", "job did not drain"
        )
        with (
            patch.object(process_tree, "run", side_effect=timeout),
            self.assertRaises(atlas_git_process.GitProcessError) as raised,
        ):
            atlas_git_process.execute_process(["git", "status"], timeout=3)

        self.assertTrue(raised.exception.timed_out)
        self.assertEqual(
            str(raised.exception),
            "process timed out after 3s: git status; "
            "process-tree cleanup failed: job did not drain",
        )
        self.assertIs(raised.exception.__cause__, timeout)
        self.assertEqual(raised.exception.__cause__.cleanup_error, "job did not drain")

    def test_missing_executable_is_a_typed_launch_failure(self):
        command = f"atlas-no-such-executable-{uuid.uuid4().hex}"

        with self.assertRaises(atlas_git_process.GitProcessError) as raised:
            atlas_git_process.execute_process([command], timeout=HANG_GUARD_SECONDS)

        error = raised.exception
        self.assertFalse(error.timed_out)
        self.assertTrue(str(error).startswith(f"cannot run {command}: "), str(error))
        self.assertIn(str(error.__cause__), str(error))
        if os.name == "nt":
            self.assertIsInstance(error.__cause__, FileNotFoundError)
        else:
            self.assertIsInstance(error.__cause__, RuntimeError)
            self.assertIn("FileNotFoundError", str(error.__cause__))

    def test_launch_failure_keeps_its_cause_whatever_the_host_raises(self):
        for cause in (
            FileNotFoundError(2, "No such file or directory"),
            PermissionError(13, "Permission denied"),
            RuntimeError("process supervisor could not launch command"),
        ):
            with self.subTest(cause=type(cause).__name__):
                with (
                    patch.object(process_tree, "run", side_effect=cause),
                    self.assertRaises(atlas_git_process.GitProcessError) as raised,
                ):
                    atlas_git_process.execute_process(["git", "status"], timeout=3)

                self.assertIs(raised.exception.__cause__, cause)
                self.assertEqual(str(raised.exception), f"cannot run git: {cause}")
                self.assertFalse(raised.exception.timed_out)

    def test_cleanup_failure_after_a_normal_exit_does_not_claim_the_launch_failed(self):
        cleanup = process_tree.ProcessTreeCleanupError("job did not drain")
        with (
            patch.object(process_tree, "run", side_effect=cleanup),
            self.assertRaises(atlas_git_process.GitProcessError) as raised,
        ):
            atlas_git_process.execute_process(["git", "status"], timeout=3)

        self.assertIs(raised.exception.__cause__, cleanup)
        self.assertEqual(
            str(raised.exception),
            "git ran but its process-tree cleanup failed: job did not drain",
        )
        self.assertFalse(raised.exception.timed_out)

    def test_expired_deadline_is_a_typed_timeout_and_launches_nothing(self):
        for timeout in (0, -1, 0.0, -0.5):
            with self.subTest(timeout=timeout):
                with (
                    patch.object(process_tree, "run") as run,
                    self.assertRaises(atlas_git_process.GitProcessError) as raised,
                ):
                    atlas_git_process.execute_process(["git", "status"], timeout=timeout)

                self.assertTrue(raised.exception.timed_out)
                self.assertEqual(
                    str(raised.exception), f"process timed out after {timeout}s: git status"
                )
                run.assert_not_called()

    def test_a_deadline_that_is_no_finite_number_is_a_typed_error_not_a_timeout(self):
        for timeout in (math.nan, math.inf, -math.inf, None, "5", True):
            with self.subTest(timeout=timeout):
                with (
                    patch.object(process_tree, "run") as run,
                    self.assertRaises(atlas_git_process.GitProcessError) as raised,
                ):
                    atlas_git_process.execute_process(["git", "status"], timeout=timeout)

                self.assertFalse(raised.exception.timed_out)
                self.assertEqual(
                    str(raised.exception),
                    "process deadline must be a finite number of seconds, "
                    f"got {timeout!r}: git status",
                )
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
