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
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lock-form.py"
_SPEC = importlib.util.spec_from_file_location("atlas_lock_form_publisher", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_lock_form = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_lock_form)


class HookBranchPushTestCase(unittest.TestCase):
    ACCEPTING_HOOK = b"#!/bin/sh\ncat > hook-stdin.txt\n"

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

    def test_push_uses_absent_and_ancestral_remote_tip_leases(self) -> None:
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
            _lock_form.push_hook_branch(repo, first, branch, self.ACCEPTING_HOOK)
            self.assertEqual(self._git(remote, "rev-parse", ref), first)

            remote_tip = self._commit(repo, "remote-tip")
            self._git(repo, "push", "-q", "origin", f"{remote_tip}:{ref}")
            self._git(repo, "update-ref", f"refs/remotes/origin/{branch}", base)
            self._git(repo, "switch", "-q", "-c", "desired", remote_tip)
            desired = self._commit(repo, "desired")
            _lock_form.push_hook_branch(repo, desired, branch, self.ACCEPTING_HOOK)

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
            self._git(repo, "switch", "-q", "-c", "desired", observed)
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
                    _lock_form.push_hook_branch(repo, desired, branch, self.ACCEPTING_HOOK)

            self.assertEqual(self._git(remote, "rev-parse", ref), concurrent)

    def test_push_runs_supplied_hook_instead_of_configured_checkout_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-hook-") as temp:
            root = Path(temp)
            repo = root / "member"
            remote = root / "remote.git"
            repo.mkdir()
            self._git(repo, "init", "-q", "-b", "main")
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            base = self._commit(repo, "base")
            self._git(repo, "remote", "add", "origin", str(remote))
            self._git(repo, "push", "-q", "origin", "main")
            old_hooks = repo / "old-hooks"
            old_hooks.mkdir()
            old_hook = old_hooks / "pre-push"
            old_hook.write_text("#!/bin/sh\ntouch old-hook-ran\nexit 71\n", encoding="utf-8")
            old_hook.chmod(0o755)
            self._git(repo, "config", "core.hooksPath", "old-hooks")
            desired = self._commit(repo, "published")

            _lock_form.push_hook_branch(
                repo, desired, "ci/sync-stack-hooks", self.ACCEPTING_HOOK
            )

            self.assertEqual(
                self._git(remote, "rev-parse", "refs/heads/ci/sync-stack-hooks"),
                desired,
            )
            hook_input = (repo / "hook-stdin.txt").read_text(encoding="utf-8")
            self.assertEqual(
                hook_input.split(),
                [
                    desired,
                    desired,
                    "refs/heads/ci/sync-stack-hooks",
                    "0" * 40,
                ],
            )
            self.assertFalse((repo / "old-hook-ran").exists())
            self.assertEqual(self._git(repo, "config", "core.hooksPath"), "old-hooks")
            self.assertNotEqual(base, desired)

    def test_rejected_supplied_hook_does_not_update_remote(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-reject-") as temp:
            root = Path(temp)
            repo = root / "member"
            remote = root / "remote.git"
            repo.mkdir()
            self._git(repo, "init", "-q", "-b", "main")
            subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
            self._commit(repo, "base")
            self._git(repo, "remote", "add", "origin", str(remote))
            self._git(repo, "push", "-q", "origin", "main")
            desired = self._commit(repo, "published")

            rejecting_hook = (
                b"#!/bin/sh\nprintf 'ran\\n' > rejected-hook-ran.txt\nexit 1\n"
            )
            with self.assertRaisesRegex(RuntimeError, "git .* push"):
                _lock_form.push_hook_branch(
                    repo, desired, "ci/sync-stack-hooks", rejecting_hook
                )

            self.assertEqual(
                (repo / "rejected-hook-ran.txt").read_text(encoding="utf-8"),
                "ran\n",
            )
            listing = _lock_form.git_bytes(
                repo, "ls-remote", "--heads", "origin", "refs/heads/ci/sync-stack-hooks"
            )
            self.assertEqual(listing, b"")

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
                Path("member"), "commit", "ci/sync-stack-hooks", self.ACCEPTING_HOOK,
                "b" * 40,
            )

        self.assertEqual(git_in.call_args.args[1], "-c")
        self.assertTrue(git_in.call_args.args[2].startswith("core.hooksPath="))
        self.assertEqual(
            git_in.call_args.args[3:],
            (
                "-c", f"atlas.preparedTools={'b' * 40}",
                "push", "-q", f"--force-with-lease={ref}:{observed}",
                "origin", f"commit:{ref}",
            ),
        )

        with (
            patch.object(_lock_form, "git_bytes", return_value=b""),
            patch.object(_lock_form, "git_in", return_value="") as git_in,
        ):
            _lock_form.push_hook_branch(
                Path("member"), "commit", "ci/sync-stack-hooks", self.ACCEPTING_HOOK,
                "b" * 40,
            )
        self.assertEqual(
            git_in.call_args.args[3:],
            (
                "-c", f"atlas.preparedTools={'b' * 40}",
                "push", "-q", f"--force-with-lease={ref}:",
                "origin", f"commit:{ref}",
            ),
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
                            Path("member"), "commit", "ci/sync-stack-hooks", self.ACCEPTING_HOOK
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
            subprocess.CompletedProcess([], 0, stdout=f"{url}\tfalse\n", stderr=""),
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
                "--base", "main", "--state", "open", "--json", "url,isDraft",
                "--jq", ".[0] | select(. != null) | [.url, .isDraft] | @tsv",
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

    def test_new_draft_pull_request_is_created_as_draft(self) -> None:
        url = "https://github.com/example/member/pull/9"
        responses = [
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            subprocess.CompletedProcess([], 0, stdout=f"{url}\n", stderr=""),
        ]
        with patch.object(_lock_form.subprocess, "run", side_effect=responses) as run:
            found, created = _lock_form.pull_request_for(
                Path("member"),
                "ci/sync-stack-hooks",
                "main",
                "subject",
                "body",
                draft=True,
            )

        self.assertEqual((found, created), (url, True))
        self.assertEqual(
            run.call_args_list[1].args[0],
            [
                "gh", "pr", "create", "--head", "ci/sync-stack-hooks",
                "--base", "main", "--title", "subject", "--body", "body",
                "--draft",
            ],
        )

    def test_draft_refuses_an_existing_ready_pull_request(self) -> None:
        url = "https://github.com/example/member/pull/10"
        response = subprocess.CompletedProcess(
            [], 0, stdout=f"{url}\tfalse\n", stderr=""
        )
        with patch.object(_lock_form.subprocess, "run", return_value=response) as run:
            with self.assertRaisesRegex(RuntimeError, "is ready; refusing --draft"):
                _lock_form.pull_request_for(
                    Path("member"),
                    "ci/sync-stack-hooks",
                    "main",
                    "subject",
                    "body",
                    draft=True,
                )

        self.assertEqual(run.call_count, 1)

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


class RetiredPathTestCase(unittest.TestCase):
    """`--retire` deletes a file the hooks no longer read, with the sync."""

    HOOK = [("pre-push", b"#!/bin/sh\nexit 0\n")]

    def setUp(self) -> None:
        """`commit-tree` reads the identity from the environment, which a CI
        runner does not configure."""
        identity = {
            f"GIT_{role}_{field}": value
            for role in ("AUTHOR", "COMMITTER")
            for field, value in (("NAME", "t"), ("EMAIL", "t@t"))
        }
        patcher = patch.dict("os.environ", identity)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _member(self, root: Path, files: dict[str, str]) -> tuple[Path, str]:
        repo = root / "member"
        repo.mkdir()
        run = lambda *args: subprocess.run(  # noqa: E731
            ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True,
            capture_output=True,
            encoding="utf-8",
        ).stdout.strip()
        run("init", "-q", "-b", "main")
        for name, text in files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text, encoding="utf-8")
            run("add", name)
        run("commit", "-q", "-m", "base")
        self.run_git = run
        return repo, run("rev-parse", "HEAD")

    def _tree_files(self, repo: Path, commit: str) -> set[str]:
        return set(self.run_git("ls-tree", "-r", "--name-only", commit).splitlines())

    def test_a_retired_file_leaves_the_commit_and_the_hook_arrives(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-retire-") as temp:
            repo, base = self._member(
                Path(temp), {"scripts/lockfile.py": "x\n", "scripts/other.py": "y\n"}
            )
            commit = _lock_form.hook_commit(
                repo, base, self.HOOK, "sync", retired=("scripts/lockfile.py",)
            )
            self.assertEqual(
                self._tree_files(repo, commit),
                {".githooks/pre-push", "scripts/other.py"},
            )

    def test_a_retired_file_already_absent_leaves_a_current_member_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-retire-") as temp:
            repo, base = self._member(Path(temp), {"scripts/other.py": "y\n"})
            current = _lock_form.hook_commit(repo, base, self.HOOK, "sync")
            self.assertIsNotNone(current)
            self.assertIsNone(
                _lock_form.hook_commit(
                    repo, current, self.HOOK, "sync", retired=("scripts/lockfile.py",)
                )
            )

    def test_only_a_retirement_makes_a_current_member_publishable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-retire-") as temp:
            repo, base = self._member(
                Path(temp), {"scripts/lockfile.py": "x\n", "scripts/other.py": "y\n"}
            )
            current = _lock_form.hook_commit(repo, base, self.HOOK, "sync")
            commit = _lock_form.hook_commit(
                repo, current, self.HOOK, "sync", retired=("scripts/lockfile.py",)
            )
            self.assertIsNotNone(commit)
            self.assertNotIn("scripts/lockfile.py", self._tree_files(repo, commit))

    def test_unsafe_retired_paths_are_refused(self) -> None:
        for path in ("/etc/passwd", "../x", "a/../b", "", "a//b", "a\\b"):
            with redirect_stderr(io.StringIO()):
                self.assertIsNone(_lock_form.retired_member_paths([path]), path)
        self.assertEqual(
            _lock_form.retired_member_paths(["scripts/lockfile.py"]), ["scripts/lockfile.py"]
        )
        self.assertEqual(_lock_form.retired_member_paths(None), [])

    def test_the_cli_carries_each_retired_path_and_the_message_names_them(self) -> None:
        captured: list[Namespace] = []
        with (
            patch.object(
                sys,
                "argv",
                [
                    "atlas-lock-form.py", "publish-hooks", "alpha", "--push",
                    "--retire", "scripts/lockfile.py", "--retire", "scripts/b.py",
                ],
            ),
            patch.object(
                _lock_form,
                "cmd_publish_hooks",
                side_effect=lambda args: captured.append(args) or 0,
            ),
        ):
            self.assertEqual(_lock_form.main(), 0)
        self.assertEqual(captured[0].retire, ["scripts/lockfile.py", "scripts/b.py"])

    def test_publication_passes_the_retired_paths_and_names_them_in_the_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-retire-") as temp:
            root = Path(temp)
            (root / "repos" / "alpha").mkdir(parents=True)
            args = Namespace(
                members=["alpha"], push=False, hook="pre-push", source_ref=None,
                retire=["scripts/lockfile.py"],
            )
            git_results = iter(
                ["", "refs/remotes/origin/main", "a" * 40, "aaaaaaaa", "", "origin/main", "b" * 40]
            )
            with (
                patch.object(_lock_form, "ROOT", root),
                patch.object(_lock_form, "REPOS", root / "repos"),
                patch.object(_lock_form, "member_scope", return_value=("alpha",)),
                patch.object(_lock_form, "git_in", side_effect=lambda *_args: next(git_results)),
                patch.object(_lock_form, "committed_hooks", return_value=self.HOOK),
                patch.object(_lock_form, "hook_commit", return_value="built") as hook_commit,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(_lock_form.cmd_publish_hooks(args), 0)
            self.assertEqual(hook_commit.call_args.kwargs["retired"], ("scripts/lockfile.py",))
            self.assertIn("`scripts/lockfile.py`", hook_commit.call_args.args[3])


class PublisherScopeTestCase(unittest.TestCase):
    def test_cli_accepts_named_members(self) -> None:
        captured: list[Namespace] = []
        with (
            patch.object(
                sys,
                "argv",
                [
                    "atlas-lock-form.py",
                    "publish-hooks",
                    "alpha",
                    "beta",
                    "--push",
                    "--hook",
                    "pre-push",
                    "--source-ref",
                    "refs/remotes/origin/pr/286",
                    "--item",
                    "ATLAS-HOOK-ROLLOUT-2026-10-06",
                    "--draft",
                ],
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
        self.assertEqual(captured[0].hook, "pre-push")
        self.assertEqual(captured[0].source_ref, "refs/remotes/origin/pr/286")
        self.assertEqual(captured[0].item, "ATLAS-HOOK-ROLLOUT-2026-10-06")
        self.assertTrue(captured[0].draft)

    def test_invalid_item_is_rejected_before_external_commands(self) -> None:
        for item in ("", "ATLAS-HOOK\nInjected: value", "ATLAS-HOOK-\x1fVALUE"):
            with self.subTest(item=repr(item)):
                args = Namespace(
                    members=["alpha"], push=True, source_ref=None, item=item
                )
                with (
                    patch.object(_lock_form, "member_scope") as member_scope,
                    patch.object(_lock_form, "git_in") as git_in,
                    redirect_stderr(io.StringIO()) as error_output,
                ):
                    self.assertEqual(_lock_form.cmd_publish_hooks(args), 2)
                member_scope.assert_not_called()
                git_in.assert_not_called()
                self.assertIn("invalid item", error_output.getvalue())

    def test_unknown_member_is_rejected_before_external_commands(self) -> None:
        args = Namespace(members=["../other"], push=True, source_ref=None)
        with (
            patch.object(_lock_form, "registered_member_names", return_value=["alpha"]),
            patch.object(_lock_form, "git_in", side_effect=AssertionError("git must not run")),
        ):
            self.assertEqual(_lock_form.cmd_publish_hooks(args), 2)

    def test_committed_source_ref_is_resolved_before_member_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-source-") as temp:
            root = Path(temp)
            member_root = root / "repos"
            (member_root / "alpha").mkdir(parents=True)
            source_commit = "a" * 40
            hook_bytes = [
                ("pre-commit", b"#!/bin/sh\nexit 0\n"),
                ("pre-push", b"#!/bin/sh\nexit 0\n"),
            ]
            args = Namespace(
                members=["alpha"],
                push=True,
                hook="pre-push",
                source_ref="refs/remotes/origin/pr/286",
                item="ATLAS-HOOK-ROLLOUT-2026-10-06",
            )
            git_results = iter(
                [
                    "",  # fetch Atlas
                    "refs/remotes/origin/main",  # Atlas default
                    source_commit,  # resolve the requested source ref
                    "aaaaaaaa",  # source abbreviation for the PR message
                    "",  # fetch member
                    "origin/main",  # member default
                    "b" * 40,  # member base
                ]
            )

            with (
                patch.object(_lock_form, "ROOT", root),
                patch.object(_lock_form, "REPOS", member_root),
                patch.object(_lock_form, "member_scope", return_value=("alpha",)),
                patch.object(
                    _lock_form, "git_in", side_effect=lambda *_args: next(git_results)
                ) as git_in,
                patch.object(
                    _lock_form, "committed_hooks", return_value=hook_bytes
                ) as committed_hooks,
                patch.object(
                    _lock_form, "hook_commit", return_value="built"
                ) as hook_commit,
                patch.object(_lock_form, "push_hook_branch") as push_hook_branch,
                patch.object(
                    _lock_form, "pull_request_for", return_value=("url", True)
                ) as pull_request_for,
                patch.object(_lock_form, "enqueue_pull_request") as enqueue,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(_lock_form.cmd_publish_hooks(args), 0)

            self.assertEqual(
                git_in.call_args_list[2].args[1:],
                (
                    "rev-parse",
                    "--verify",
                    "--end-of-options",
                    "refs/remotes/origin/pr/286^{commit}",
                ),
            )
            committed_hooks.assert_called_once_with(root, source_commit)
            self.assertEqual(hook_commit.call_args.args[2], [hook_bytes[1]])
            self.assertEqual(hook_commit.call_args.args[1], "b" * 40)
            push_hook_branch.assert_called_once_with(
                member_root / "alpha", "built", "ci/sync-stack-hooks",
                hook_bytes[1][1], source_commit,
            )
            expected_message = (
                "ci: Sync the stack-owned git hooks\n\n"
                "Deploys atlas `scripts/git-hooks` at aaaaaaaa, the single\n"
                "source every member's `.githooks/` copies; a copy that differs is the\n"
                "gate-version drift the conformance scan counts.\n\n"
                "Item: ATLAS-HOOK-ROLLOUT-2026-10-06\n"
            )
            self.assertEqual(hook_commit.call_args.args[3], expected_message)
            pull_request_for.assert_called_once_with(
                member_root / "alpha",
                "ci/sync-stack-hooks",
                "main",
                "ci: Sync the stack-owned git hooks",
                expected_message,
                draft=False,
            )
            enqueue.assert_called_once_with(member_root / "alpha", "url")

    def test_draft_publication_skips_enqueue(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-draft-") as temp:
            root = Path(temp)
            member_root = root / "repos"
            (member_root / "alpha").mkdir(parents=True)
            source_commit = "a" * 40
            hook_bytes = [("pre-push", b"#!/bin/sh\nexit 0\n")]
            args = Namespace(
                members=["alpha"],
                push=True,
                hook="pre-push",
                source_ref="refs/remotes/origin/pr/286",
                draft=True,
            )
            git_results = iter(
                [
                    "",
                    "refs/remotes/origin/main",
                    source_commit,
                    "aaaaaaaa",
                    "",
                    "origin/main",
                    "b" * 40,
                ]
            )
            with (
                patch.object(_lock_form, "ROOT", root),
                patch.object(_lock_form, "REPOS", member_root),
                patch.object(_lock_form, "member_scope", return_value=("alpha",)),
                patch.object(
                    _lock_form, "git_in", side_effect=lambda *_args: next(git_results)
                ),
                patch.object(_lock_form, "committed_hooks", return_value=hook_bytes),
                patch.object(_lock_form, "hook_commit", return_value="built"),
                patch.object(_lock_form, "push_hook_branch"),
                patch.object(
                    _lock_form, "pull_request_for", return_value=("url", True)
                ) as pull_request_for,
                patch.object(_lock_form, "enqueue_pull_request") as enqueue,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(_lock_form.cmd_publish_hooks(args), 0)

            self.assertTrue(pull_request_for.call_args.kwargs["draft"])
            enqueue.assert_not_called()

    def test_unknown_hook_filter_stops_before_member_publication(self) -> None:
        args = Namespace(
            members=["alpha"],
            push=True,
            hook="pre-push",
            source_ref="refs/remotes/origin/pr/286",
        )
        error_output = io.StringIO()
        git_results = iter(
            [
                "",
                "refs/remotes/origin/main",
                "a" * 40,
                "aaaaaaaa",
            ]
        )
        with (
            patch.object(_lock_form, "member_scope", return_value=("alpha",)),
            patch.object(
                _lock_form, "git_in", side_effect=lambda *_args: next(git_results)
            ),
            patch.object(
                _lock_form,
                "committed_hooks",
                return_value=[("pre-commit", b"#!/bin/sh\nexit 0\n")],
            ),
            patch.object(_lock_form, "hook_commit") as hook_commit,
            redirect_stderr(error_output),
        ):
            self.assertEqual(_lock_form.cmd_publish_hooks(args), 2)
        hook_commit.assert_not_called()
        self.assertIn("has no pre-push", error_output.getvalue())

        args = Namespace(
            members=["alpha"], push=True, source_ref="refs/remotes/origin/missing"
        )
        output = io.StringIO()
        error_output = io.StringIO()
        with (
            patch.object(_lock_form, "member_scope", return_value=("alpha",)),
            patch.object(_lock_form, "git_in") as git_in,
            patch.object(_lock_form, "committed_hooks") as committed_hooks,
            patch.object(_lock_form, "hook_commit") as hook_commit,
            patch.object(_lock_form, "push_hook_branch") as push_hook_branch,
            redirect_stdout(output),
            redirect_stderr(error_output),
        ):
            # The third call resolves the missing ref after Atlas fetch/default.
            git_in.side_effect = [
                "",
                "refs/remotes/origin/main",
                RuntimeError("bad object"),
            ]
            self.assertEqual(_lock_form.cmd_publish_hooks(args), 2)

        self.assertEqual(git_in.call_count, 3)
        committed_hooks.assert_not_called()
        hook_commit.assert_not_called()
        push_hook_branch.assert_not_called()
        self.assertNotIn("published:", output.getvalue())
        self.assertIn("invalid committed hook source", error_output.getvalue())

    def test_empty_source_ref_is_not_defaulted(self) -> None:
        args = Namespace(members=["alpha"], push=True, source_ref="")
        error_output = io.StringIO()
        with (
            patch.object(_lock_form, "member_scope", return_value=("alpha",)),
            patch.object(_lock_form, "git_in") as git_in,
            patch.object(_lock_form, "committed_hooks") as committed_hooks,
            patch.object(_lock_form, "hook_commit") as hook_commit,
            patch.object(_lock_form, "push_hook_branch") as push_hook_branch,
            redirect_stderr(error_output),
        ):
            self.assertEqual(_lock_form.cmd_publish_hooks(args), 2)

        git_in.assert_not_called()
        committed_hooks.assert_not_called()
        hook_commit.assert_not_called()
        push_hook_branch.assert_not_called()
        self.assertIn("reference is empty", error_output.getvalue())

    def test_hosting_stage_failures_make_the_member_and_command_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-failure-") as temp:
            root = Path(temp)
            (root / "repos" / "alpha").mkdir(parents=True)
            args = Namespace(members=["alpha"], push=True, source_ref=None)
            for failed_stage in ("list", "create", "merge"):
                with self.subTest(failed_stage=failed_stage):
                    git_results = iter(
                        [
                            "",
                            "refs/remotes/origin/main",
                            "5" * 40,
                            "55555555",
                            "",
                            "origin/main",
                            "base",
                        ]
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
                        patch.object(
                            _lock_form, "committed_hooks",
                            return_value=[("pre-push", b"#!/bin/sh\nexit 0\n")],
                        ),
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
