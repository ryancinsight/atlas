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

    def test_corrected_publication_reconciles_default_and_hook_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-base-") as temp:
            repo = Path(temp)
            base = self._commit_after_init(repo)
            self._git(repo, "switch", "-q", "-c", "publication", base)
            hook = repo / ".githooks" / "pre-push"
            hook.parent.mkdir()
            hook.write_bytes(b"old\n")
            self._git(repo, "add", ".githooks/pre-push")
            self._git(repo, "commit", "-q", "-m", "old hook")
            published = self._git(repo, "rev-parse", "HEAD")
            self._git(repo, "switch", "-q", "main")
            (repo / "README.md").write_text("current default\n", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-q", "-m", "default advance")
            default = self._git(repo, "rev-parse", "HEAD")
            self._git(
                repo,
                "update-ref",
                "refs/remotes/origin/ci/sync-stack-hooks",
                published,
            )

            (repo / "index-only.txt").write_text("preserve\n", encoding="utf-8")
            self._git(repo, "add", "index-only.txt")
            head_before = self._git(repo, "rev-parse", "HEAD")
            index_before = self._git(repo, "diff", "--cached", "--binary")

            selected = _lock_form.hook_publication_base(
                repo, default, [("pre-push", b"new\n")], ()
            )
            candidate = _lock_form.hook_commit(
                repo,
                selected,
                [("pre-push", b"new\n")],
                "corrected hook\n",
            )
            landed = _lock_form.hook_landing_tree(
                repo, default, candidate, [("pre-push", b"new\n")], ()
            )

            self.assertEqual(selected, published)
            self.assertEqual(
                self._git(repo, "show", "-s", "--format=%P", candidate),
                published,
            )
            self.assertEqual(
                self._git(repo, "show", f"{landed}:README.md"), "current default"
            )
            self.assertEqual(
                self._git(repo, "show", f"{landed}:.githooks/pre-push"), "new"
            )
            self.assertEqual(
                self._git(repo, "diff", "--name-only", default, landed),
                ".githooks/pre-push",
            )
            self.assertEqual(
                self._git(repo, "diff", "--name-only", published, candidate),
                ".githooks/pre-push",
            )
            self.assertTrue(
                self._git(repo, "ls-tree", landed, ".githooks/pre-push").startswith(
                    "100755 blob "
                )
            )
            self.assertEqual(self._git(repo, "rev-parse", "HEAD"), head_before)
            self.assertEqual(self._git(repo, "diff", "--cached", "--binary"), index_before)

            self._git(
                repo,
                "update-ref",
                "refs/remotes/origin/ci/sync-stack-hooks",
                candidate,
            )
            selected = _lock_form.hook_publication_base(
                repo, default, [("pre-push", b"new\n")], ()
            )
            self.assertEqual(selected, candidate)
            self.assertIsNone(
                _lock_form.hook_commit(
                    repo, selected, [("pre-push", b"new\n")], "corrected hook\n"
                )
            )
            self.assertEqual(
                _lock_form.hook_landing_tree(
                    repo, default, selected, [("pre-push", b"new\n")], ()
                ),
                landed,
            )

    def test_corrected_publication_refuses_non_hook_branch_work(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-base-unique-") as temp:
            repo = Path(temp)
            base = self._commit_after_init(repo)
            self._git(repo, "switch", "-q", "-c", "publication", base)
            hook = repo / ".githooks" / "pre-push"
            hook.parent.mkdir()
            hook.write_bytes(b"old\n")
            (repo / "unique.txt").write_text("preserve\n", encoding="utf-8")
            self._git(repo, "add", ".githooks/pre-push", "unique.txt")
            self._git(repo, "commit", "-q", "-m", "unique work")
            published = self._git(repo, "rev-parse", "HEAD")
            self._git(repo, "switch", "-q", "main")
            default = self._commit(repo, "default advance")
            self._git(
                repo,
                "update-ref",
                "refs/remotes/origin/ci/sync-stack-hooks",
                published,
            )

            with self.assertRaisesRegex(RuntimeError, "unique.txt"):
                _lock_form.hook_publication_base(
                    repo, default, [("pre-push", b"new\n")], ()
                )

    def test_corrected_publication_refuses_a_non_hook_renamed_to_a_hook(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-base-rename-") as temp:
            repo = Path(temp)
            self._commit_after_init(repo)
            (repo / "README.md").write_text("member documentation\n", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-q", "-m", "member documentation")
            base = self._git(repo, "rev-parse", "HEAD")
            self._git(repo, "switch", "-q", "-c", "publication", base)
            (repo / ".githooks").mkdir()
            self._git(repo, "mv", "README.md", ".githooks/pre-push")
            self._git(repo, "commit", "-q", "-m", "hide non-hook deletion")
            published = self._git(repo, "rev-parse", "HEAD")
            self._git(repo, "switch", "-q", "main")
            default = self._commit(repo, "default advance")
            self._git(
                repo,
                "update-ref",
                "refs/remotes/origin/ci/sync-stack-hooks",
                published,
            )

            self.assertEqual(
                self._git(
                    repo,
                    "diff",
                    "-M",
                    "--name-status",
                    f"{default}...{published}",
                ),
                "R100\tREADME.md\t.githooks/pre-push",
            )
            with self.assertRaisesRegex(RuntimeError, "README.md"):
                _lock_form.hook_publication_base(
                    repo,
                    default,
                    [("pre-push", b"member documentation\n")],
                    (),
                )

    def test_publication_refuses_conflicting_or_combined_hook_merges(self) -> None:
        for default_hook, published_hook, error in (
            (b"other\n", b"new\n", "conflict"),
            (
                b"a\nb\nc\nd\ne\nf\nchanged\n",
                b"new\nb\nc\nd\ne\nf\ng\n",
                "differs",
            ),
        ):
            with self.subTest(default_hook=default_hook):
                with tempfile.TemporaryDirectory(prefix="atlas-publish-merge-") as temp:
                    repo = Path(temp)
                    self._commit_after_init(repo)
                    hook = repo / ".githooks" / "pre-push"
                    hook.parent.mkdir()
                    hook.write_bytes(b"a\nb\nc\nd\ne\nf\ng\n")
                    self._git(repo, "add", ".githooks/pre-push")
                    self._git(repo, "commit", "-q", "-m", "shared hook")
                    base = self._git(repo, "rev-parse", "HEAD")
                    candidate = _lock_form.hook_commit(
                        repo, base, [("pre-push", published_hook)], "publication\n"
                    )
                    hook.write_bytes(default_hook)
                    self._git(repo, "add", ".githooks/pre-push")
                    self._git(repo, "commit", "-q", "-m", "default hook advance")
                    default = self._git(repo, "rev-parse", "HEAD")
                    with self.assertRaisesRegex(RuntimeError, error):
                        _lock_form.hook_landing_tree(
                            repo, default, candidate, [("pre-push", published_hook)], ()
                        )
                    self.assertEqual(self._git(repo, "rev-parse", "HEAD"), default)
                    self.assertEqual(hook.read_bytes(), default_hook)
                    self.assertEqual(self._git(repo, "status", "--porcelain"), "")

    def test_current_publication_still_runs_the_real_landing_guard(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-current-") as temp:
            scratch = Path(temp)
            root = scratch / "atlas"
            root.mkdir()
            self._commit_after_init(root)
            owned = root / "scripts" / "git-hooks" / "pre-push"
            owned.parent.mkdir(parents=True)
            hook = b"#!/bin/sh\nexit 0\n"
            owned.write_bytes(hook)
            self._git(root, "add", "scripts/git-hooks/pre-push")
            self._git(root, "commit", "-q", "-m", "owned hook")
            atlas_remote = scratch / "atlas.git"
            subprocess.run(["git", "init", "-q", "--bare", str(atlas_remote)], check=True)
            self._git(root, "remote", "add", "origin", str(atlas_remote))
            self._git(root, "push", "-q", "origin", "main")
            self._git(root, "remote", "set-head", "origin", "main")

            member = root / "repos" / "alpha"
            member.mkdir(parents=True)
            self._commit_after_init(member)
            installed = member / ".githooks" / "pre-push"
            installed.parent.mkdir()
            installed.write_bytes(hook)
            self._git(member, "add", ".githooks/pre-push")
            self._git(member, "update-index", "--chmod=+x", ".githooks/pre-push")
            self._git(member, "commit", "-q", "-m", "installed hook")
            default = self._git(member, "rev-parse", "HEAD")
            member_remote = scratch / "member.git"
            subprocess.run(["git", "init", "-q", "--bare", str(member_remote)], check=True)
            self._git(member, "remote", "add", "origin", str(member_remote))
            self._git(member, "push", "-q", "origin", "main")
            self._git(member, "remote", "set-head", "origin", "main")

            args = Namespace(members=["alpha"], push=True, source_ref=None)
            output = io.StringIO()
            with (
                patch.object(_lock_form, "ROOT", root),
                patch.object(_lock_form, "REPOS", root / "repos"),
                patch.object(_lock_form, "member_scope", return_value=("alpha",)),
                patch.object(
                    _lock_form,
                    "hook_landing_tree",
                    wraps=_lock_form.hook_landing_tree,
                ) as landing_guard,
                patch.object(_lock_form, "push_hook_branch") as push_hook_branch,
                redirect_stdout(output),
            ):
                self.assertEqual(_lock_form.cmd_publish_hooks(args), 0)

            landing_guard.assert_called_once_with(
                member, default, default, [("pre-push", hook)], ()
            )
            push_hook_branch.assert_not_called()
            self.assertIn("current: alpha", output.getvalue())

    def _commit_after_init(self, repo: Path) -> str:
        self._git(repo, "init", "-q", "-b", "main")
        self._git(repo, "config", "user.email", "t@t")
        self._git(repo, "config", "user.name", "t")
        return self._commit(repo, "base")

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

    def test_committed_hooks_ignore_replacement_objects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-replacements-") as temporary:
            repo = Path(temporary)
            self._commit_after_init(repo)
            hook = repo / "scripts" / "git-hooks" / "pre-push"
            hook.parent.mkdir(parents=True)
            hook.write_bytes(b"#!/bin/sh\nexit 7\n")
            self._git(repo, "add", "scripts/git-hooks/pre-push")
            self._git(repo, "commit", "-qm", "Trusted hook")
            trusted = self._git(repo, "rev-parse", "HEAD")
            hook.write_bytes(b"#!/bin/sh\nexit 0\n")
            self._git(repo, "add", "scripts/git-hooks/pre-push")
            self._git(repo, "commit", "-qm", "Replacement hook")
            replacement = self._git(repo, "rev-parse", "HEAD")
            self._git(repo, "replace", trusted, replacement)
            self.assertEqual(_lock_form.committed_hooks(repo, trusted),
                             [("pre-push", b"#!/bin/sh\nexit 7\n")])

    def test_push_materializes_and_runs_the_committed_process_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-runtime-") as temporary:
            root = Path(temporary)
            atlas, member, remote = root / "atlas", root / "member", root / "remote.git"
            atlas.mkdir()
            member.mkdir()
            self._commit_after_init(atlas)
            self._commit_after_init(member)
            for name in ("pre_push_gate.py", "atlas_build_lock.py", "process_tree.py", "windows_process.py", "darwin_process.py"):
                target = atlas / "scripts" / name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes((SCRIPT.parent / name).read_bytes())
                self._git(atlas, "add", "scripts/" + name)
            self._git(atlas, "commit", "-qm", "Process owner")
            source = self._git(atlas, "rev-parse", "HEAD")
            self._git(root, "init", "-q", "--bare", str(remote))
            self._git(member, "remote", "add", "origin", str(remote))
            self._git(member, "push", "-q", "origin", "main")
            desired = self._commit(member, "published")
            hook = b"""#!/bin/sh
if [ "${1:-}" = --bounded-entry ]; then
  shift
  cat > hook-stdin.txt
  printf '%s\\n' "$ATLAS_PRE_PUSH_RUNTIME" > runtime-path.txt
  exit 0
fi
exec "$ATLAS_PRE_PUSH_PYTHON" -I "$ATLAS_PRE_PUSH_RUNTIME/pre_push_gate.py" direct push "$0" "$@"
"""
            with patch.object(_lock_form, "ROOT", atlas):
                _lock_form.push_hook_branch(member, desired, "ci/sync-stack-hooks", hook, source)
            self.assertEqual(self._git(remote, "rev-parse", "refs/heads/ci/sync-stack-hooks"), desired)
            self.assertEqual((member / "hook-stdin.txt").read_text().split(),
                             [desired, desired, "refs/heads/ci/sync-stack-hooks", "0" * 40])
            runtime = Path((member / "runtime-path.txt").read_text().strip())
            self.assertEqual(runtime.name, source)
            self.assertFalse(runtime.exists(), "publication runtime was not retired")

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
                patch.object(
                    _lock_form,
                    "hook_publication_base",
                    side_effect=lambda _repo, default, *_args: default,
                ),
                patch.object(_lock_form, "hook_commit", return_value="built") as hook_commit,
                patch.object(
                    _lock_form, "hook_landing_tree", return_value="landing"
                ) as landing_guard,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(_lock_form.cmd_publish_hooks(args), 0)
            self.assertEqual(hook_commit.call_args.kwargs["retired"], ("scripts/lockfile.py",))
            self.assertIn("`scripts/lockfile.py`", hook_commit.call_args.args[3])
            landing_guard.assert_called_once_with(
                root / "repos" / "alpha",
                "b" * 40,
                "built",
                self.HOOK,
                ("scripts/lockfile.py",),
            )


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
            publication_events: list[str] = []

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
                patch.object(
                    _lock_form,
                    "hook_publication_base",
                    side_effect=lambda _repo, default, *_args: default,
                ),
                patch.object(
                    _lock_form,
                    "hook_landing_tree",
                    side_effect=lambda *_args: publication_events.append("landing"),
                ) as landing_guard,
                patch.object(
                    _lock_form,
                    "push_hook_branch",
                    side_effect=lambda *_args: publication_events.append("push"),
                ) as push_hook_branch,
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
            landing_guard.assert_called_once_with(
                member_root / "alpha",
                "b" * 40,
                "built",
                [hook_bytes[1]],
                (),
            )
            push_hook_branch.assert_called_once_with(
                member_root / "alpha", "built", "ci/sync-stack-hooks",
                hook_bytes[1][1], source_commit,
            )
            self.assertEqual(publication_events, ["landing", "push"])
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
                patch.object(
                    _lock_form,
                    "hook_publication_base",
                    side_effect=lambda _repo, default, *_args: default,
                ),
                patch.object(_lock_form, "hook_commit", return_value="built"),
                patch.object(
                    _lock_form, "hook_landing_tree", return_value="landing"
                ) as landing_guard,
                patch.object(_lock_form, "push_hook_branch"),
                patch.object(
                    _lock_form, "pull_request_for", return_value=("url", True)
                ) as pull_request_for,
                patch.object(_lock_form, "enqueue_pull_request") as enqueue,
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(_lock_form.cmd_publish_hooks(args), 0)

            landing_guard.assert_called_once_with(
                member_root / "alpha",
                "b" * 40,
                "built",
                hook_bytes,
                (),
            )
            self.assertTrue(pull_request_for.call_args.kwargs["draft"])
            enqueue.assert_not_called()

    def test_landing_guard_refusal_stops_before_push_and_hosting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hook-landing-refusal-") as temp:
            root = Path(temp)
            member_root = root / "repos"
            (member_root / "alpha").mkdir(parents=True)
            source_commit = "a" * 40
            hooks = [("pre-push", b"#!/bin/sh\nexit 0\n")]
            args = Namespace(
                members=["alpha"],
                push=True,
                source_ref="refs/remotes/origin/pr/286",
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
            output = io.StringIO()
            with (
                patch.object(_lock_form, "ROOT", root),
                patch.object(_lock_form, "REPOS", member_root),
                patch.object(_lock_form, "member_scope", return_value=("alpha",)),
                patch.object(
                    _lock_form, "git_in", side_effect=lambda *_args: next(git_results)
                ),
                patch.object(_lock_form, "committed_hooks", return_value=hooks),
                patch.object(
                    _lock_form,
                    "hook_publication_base",
                    side_effect=lambda _repo, default, *_args: default,
                ),
                patch.object(_lock_form, "hook_commit", return_value="built"),
                patch.object(
                    _lock_form,
                    "hook_landing_tree",
                    side_effect=RuntimeError("publication merge conflict"),
                ) as landing_guard,
                patch.object(_lock_form, "push_hook_branch") as push_hook_branch,
                patch.object(_lock_form, "hosting_in") as hosting_in,
                redirect_stdout(output),
            ):
                self.assertEqual(_lock_form.cmd_publish_hooks(args), 1)

            landing_guard.assert_called_once_with(
                member_root / "alpha", "b" * 40, "built", hooks, ()
            )
            push_hook_branch.assert_not_called()
            hosting_in.assert_not_called()
            self.assertIn("FAILED: publication merge conflict", output.getvalue())

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
                        patch.object(
                            _lock_form,
                            "hook_publication_base",
                            side_effect=lambda _repo, default, *_args: default,
                        ),
                        patch.object(_lock_form, "hook_commit", return_value="commit"),
                        patch.object(
                            _lock_form, "hook_landing_tree", return_value="landing"
                        ) as landing_guard,
                        patch.object(_lock_form, "push_hook_branch"),
                        patch.object(_lock_form, "hosting_in", side_effect=host),
                        redirect_stdout(output),
                    ):
                        self.assertEqual(_lock_form.cmd_publish_hooks(args), 1)

                    landing_guard.assert_called_once_with(
                        root / "repos" / "alpha",
                        "base",
                        "commit",
                        [("pre-push", b"#!/bin/sh\nexit 0\n")],
                        (),
                    )
                    self.assertIn(f"FAILED: {failed_stage} refused", output.getvalue())
                    self.assertNotIn("published:", output.getvalue())
                    self.assertNotIn("reused:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
