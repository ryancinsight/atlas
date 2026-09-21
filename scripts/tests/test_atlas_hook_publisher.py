#!/usr/bin/env python3
"""Regression tests for bounded, idempotent stack hook publication."""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lock-form.py"
_SPEC = importlib.util.spec_from_file_location("atlas_lock_form_publisher", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_lock_form = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_lock_form)


class HookBranchPushTestCase(unittest.TestCase):
    def _git(self, repo: Path, *args: str) -> str:
        return subprocess.run(
            [
                "git", "-C", str(repo), "-c", "user.email=t@t",
                "-c", "user.name=t", *args,
            ],
            check=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout.strip()

    def _commit(self, repo: Path, value: str) -> str:
        (repo / "value.txt").write_text(f"{value}\n", encoding="utf-8")
        self._git(repo, "add", "value.txt")
        self._git(repo, "commit", "-q", "-m", value)
        return self._git(repo, "rev-parse", "HEAD")

    def test_push_uses_absent_and_fresh_remote_tip_leases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-lease-") as temp:
            root = Path(temp)
            repo = root / "member"
            remote = root / "remote.git"
            repo.mkdir()
            self._git(repo, "init", "-q", "-b", "main")
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            base = self._commit(repo, "base")
            self._git(repo, "remote", "add", "origin", str(remote))
            self._git(repo, "push", "-q", "origin", "main")
            branch = "ci/sync-stack-hooks"
            ref = f"refs/heads/{branch}"

            self._git(repo, "update-ref", f"refs/remotes/origin/{branch}", base)
            first = self._commit(repo, "first")
            _lock_form.push_hook_branch(repo, first, branch)
            self.assertEqual(self._git(remote, "rev-parse", ref), first)

            remote_tip = self._commit(repo, "remote-tip")
            self._git(repo, "push", "-q", "origin", f"{remote_tip}:{ref}")
            self._git(repo, "update-ref", f"refs/remotes/origin/{branch}", base)
            self._git(repo, "switch", "-q", "-c", "desired", first)
            desired = self._commit(repo, "desired")
            _lock_form.push_hook_branch(repo, desired, branch)

            self.assertEqual(self._git(remote, "rev-parse", ref), desired)

    def test_concurrent_remote_advance_rejects_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-race-") as temp:
            root = Path(temp)
            repo = root / "member"
            remote = root / "remote.git"
            repo.mkdir()
            self._git(repo, "init", "-q", "-b", "main")
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            base = self._commit(repo, "base")
            self._git(repo, "remote", "add", "origin", str(remote))
            self._git(repo, "push", "-q", "origin", "main")
            branch = "ci/sync-stack-hooks"
            ref = f"refs/heads/{branch}"
            observed = self._commit(repo, "observed")
            self._git(repo, "push", "-q", "origin", f"{observed}:{ref}")
            concurrent = self._commit(repo, "concurrent")
            self._git(repo, "push", "-q", "origin", f"{concurrent}:refs/heads/race")
            self._git(repo, "switch", "-q", "-c", "desired", base)
            desired = self._commit(repo, "desired")
            real_git_bytes = _lock_form.git_bytes

            def advance_after_observation(path: Path, *args: str, **kwargs) -> bytes:
                result = real_git_bytes(path, *args, **kwargs)
                if args[:3] == ("ls-remote", "--heads", "origin"):
                    self._git(remote, "update-ref", ref, concurrent)
                return result

            with patch.object(
                _lock_form, "git_bytes", side_effect=advance_after_observation
            ):
                with self.assertRaisesRegex(RuntimeError, "stale info"):
                    _lock_form.push_hook_branch(repo, desired, branch)

            self.assertEqual(self._git(remote, "rev-parse", ref), concurrent)

    def test_push_uses_exact_ref_and_observed_oid(self) -> None:
        ref = "refs/heads/ci/sync-stack-hooks"
        observed = "a" * 40
        with (
            patch.object(
                _lock_form,
                "git_bytes",
                return_value=f"{observed}\t{ref}\n".encode("ascii"),
            ),
            patch.object(_lock_form, "git_in", return_value="") as git_in,
        ):
            _lock_form.push_hook_branch(
                Path("member"), "commit", "ci/sync-stack-hooks"
            )

        self.assertEqual(
            git_in.call_args.args[1:],
            (
                "push", "-q", f"--force-with-lease={ref}:{observed}",
                "origin", f"commit:{ref}",
            ),
        )

        with (
            patch.object(_lock_form, "git_bytes", return_value=b""),
            patch.object(_lock_form, "git_in", return_value="") as git_in,
        ):
            _lock_form.push_hook_branch(
                Path("member"), "commit", "ci/sync-stack-hooks"
            )
        self.assertEqual(
            git_in.call_args.args[3],
            f"--force-with-lease={ref}:",
        )

    def test_push_rejects_untrusted_remote_ref_output(self) -> None:
        ref = "refs/heads/ci/sync-stack-hooks"
        malformed = (
            f"abc123\t{ref}\n".encode("ascii"),
            f"{'g' * 40}\t{ref}\n".encode("ascii"),
            f"{'a' * 40}\n".encode("ascii"),
            f"{'a' * 40}\trefs/heads/other\n".encode("ascii"),
            f"{'a' * 40}\t{ref}\n{'b' * 40}\t{ref}\n".encode("ascii"),
            f"{'a' * 40}\t{ref}\n\n".encode("ascii"),
            b" ",
            b"\n",
            b"\n\n",
            b"\xff",
        )
        for listing in malformed:
            with self.subTest(listing=listing):
                with (
                    patch.object(
                        _lock_form, "git_bytes", return_value=listing
                    ) as git_bytes,
                    patch.object(
                        _lock_form,
                        "git_in",
                        side_effect=AssertionError("push must not run"),
                    ) as git_in,
                ):
                    with self.assertRaisesRegex(RuntimeError, "git ls-remote returned"):
                        _lock_form.push_hook_branch(
                            Path("member"), "commit", "ci/sync-stack-hooks"
                        )
                git_in.assert_not_called()
                git_bytes.assert_called_once_with(
                    Path("member"), "ls-remote", "--heads", "origin", ref
                )


class PullRequestCommandTestCase(unittest.TestCase):
    def test_existing_pull_request_is_reused_and_enqueued(self) -> None:
        repo = Path("member")
        url = "https://github.com/example/member/pull/7"
        responses = [
            subprocess.CompletedProcess([], 0, stdout=f"{url}\n", stderr=""),
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ]
        with patch.object(_lock_form.subprocess, "run", side_effect=responses) as run:
            found, created = _lock_form.pull_request_for(
                repo, "ci/sync-stack-hooks", "main", "subject", "body"
            )
            _lock_form.enqueue_pull_request(repo, found)

        self.assertEqual((found, created), (url, False))
        self.assertEqual(
            run.call_args_list[0].args[0],
            [
                "gh", "pr", "list", "--head", "ci/sync-stack-hooks",
                "--base", "main", "--state", "open", "--json", "url",
                "--jq", ".[0].url",
            ],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["gh", "pr", "merge", url, "--merge", "--auto"],
        )
        self.assertEqual(
            run.call_args_list[1].kwargs["timeout"],
            _lock_form.HOSTING_DEADLINE_SECONDS,
        )

    def test_new_pull_request_enqueue_failure_is_propagated(self) -> None:
        url = "https://github.com/example/member/pull/8"
        responses = [
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            subprocess.CompletedProcess([], 0, stdout=f"{url}\n", stderr=""),
            subprocess.CompletedProcess([], 1, stdout="", stderr="auto merge refused"),
        ]
        with patch.object(_lock_form.subprocess, "run", side_effect=responses) as run:
            found, created = _lock_form.pull_request_for(
                Path("member"), "ci/sync-stack-hooks", "main", "subject", "body"
            )
            with self.assertRaisesRegex(RuntimeError, "auto merge refused"):
                _lock_form.enqueue_pull_request(Path("member"), found)

        self.assertEqual((found, created), (url, True))
        self.assertEqual(
            run.call_args_list[1].args[0],
            [
                "gh", "pr", "create", "--head", "ci/sync-stack-hooks",
                "--base", "main", "--title", "subject", "--body", "body",
            ],
        )

    def test_hosting_timeout_is_reported_as_failure(self) -> None:
        timeout = subprocess.TimeoutExpired(["gh", "pr", "list"], 30)
        with patch.object(_lock_form.subprocess, "run", side_effect=timeout):
            with self.assertRaisesRegex(RuntimeError, "timed out after 30s"):
                _lock_form.hosting_in(Path("member"), "pr", "list")

    def test_git_deadline_and_timeout_are_forwarded(self) -> None:
        result = SimpleNamespace(returncode=0, stdout=b"ok\n", stderr=b"")
        with patch.object(_lock_form, "execute_git", return_value=result) as execute:
            self.assertEqual(_lock_form.git_in(Path("member"), "status"), "ok")
        self.assertEqual(
            execute.call_args.kwargs["timeout"], _lock_form.GIT_DEADLINE_SECONDS
        )

        error = _lock_form.GitProcessError(
            "git command timed out after 90s", timed_out=True
        )
        with patch.object(_lock_form, "execute_git", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "timed out after 90s"):
                _lock_form.git_in(Path("member"), "status")


class PublisherScopeTestCase(unittest.TestCase):
    def test_cli_accepts_named_members(self) -> None:
        captured: list[Namespace] = []
        with (
            patch.object(
                sys,
                "argv",
                ["atlas-lock-form.py", "publish-hooks", "alpha", "beta", "--push"],
            ),
            patch.object(
                _lock_form,
                "cmd_publish_hooks",
                side_effect=lambda args: captured.append(args) or 0,
            ),
        ):
            self.assertEqual(_lock_form.main(), 0)

        self.assertEqual(captured[0].members, ["alpha", "beta"])
        self.assertTrue(captured[0].push)

    def test_unknown_member_is_rejected_before_external_commands(self) -> None:
        args = Namespace(members=["../other"], push=True)
        with (
            patch.object(_lock_form, "registered_member_names", return_value=["alpha"]),
            patch.object(_lock_form, "git_in", side_effect=AssertionError("git must not run")),
        ):
            self.assertEqual(_lock_form.cmd_publish_hooks(args), 2)

    def test_hosting_stage_failures_make_the_member_and_command_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-failure-") as temp:
            root = Path(temp)
            (root / "repos" / "alpha").mkdir(parents=True)
            args = Namespace(members=["alpha"], push=True)
            for failed_stage in ("list", "create", "merge"):
                with self.subTest(failed_stage=failed_stage):
                    git_results = iter(
                        ["", "origin/main", "5ddb629c2", "", "origin/main", "base"]
                    )

                    def host(_repo: Path, *command: str) -> str:
                        stage = command[1]
                        if stage == failed_stage:
                            raise RuntimeError(f"{stage} refused")
                        if stage == "list":
                            return ""
                        if stage == "create":
                            return "https://github.com/example/alpha/pull/1"
                        return ""

                    output = io.StringIO()
                    with (
                        patch.object(_lock_form, "ROOT", root),
                        patch.object(_lock_form, "REPOS", root / "repos"),
                        patch.object(
                            _lock_form, "member_scope", return_value=("alpha",)
                        ),
                        patch.object(
                            _lock_form,
                            "git_in",
                            side_effect=lambda *_args: next(git_results),
                        ),
                        patch.object(_lock_form, "committed_hooks", return_value=[]),
                        patch.object(_lock_form, "hook_commit", return_value="commit"),
                        patch.object(_lock_form, "push_hook_branch"),
                        patch.object(_lock_form, "hosting_in", side_effect=host),
                        redirect_stdout(output),
                    ):
                        self.assertEqual(_lock_form.cmd_publish_hooks(args), 1)

                    self.assertIn(f"FAILED: {failed_stage} refused", output.getvalue())
                    self.assertNotIn("published:", output.getvalue())
                    self.assertNotIn("reused:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
