#!/usr/bin/env python3
"""Tests for what `atlas-lock-form.py` keeps: `status`, `restore` and the hook publisher.

The rule that judges a lock, the committed sweep, the staged check and
regeneration live in `lockfile.py` and are tested in `test_lockfile_form.py`
and `test_lockfile_check_staged.py`. What remains here acts on the stack as a
whole: it must find every tracked lock of the registered members and the
superproject, restore only locks the overlay alone rewrote, and publish hooks
without touching a checkout.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import time
import tempfile
import textwrap
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-lock-form.py"
_SPEC = importlib.util.spec_from_file_location("atlas_lock_form", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_lock_form = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_lock_form)


STANDALONE = textwrap.dedent(
    """\
    version = 4

    [[package]]
    name = "member"
    version = "0.1.0"
    dependencies = ["eunomia"]

    [[package]]
    name = "eunomia"
    version = "0.8.0"
    source = "git+https://github.com/ryancinsight/eunomia#abc123"
    """
)

STRIPPED = textwrap.dedent(
    """\
    version = 4

    [[package]]
    name = "member"
    version = "0.1.0"
    dependencies = ["eunomia"]

    [[package]]
    name = "eunomia"
    version = "0.8.0"

    [[patch.unused]]
    name = "themis-topology"
    version = "0.3.0"
    """
)


class RestoreGuardTestCase(unittest.TestCase):
    def test_transitively_stripped_sibling_is_restorable(self) -> None:
        """Patching one crate to a path makes its whole workspace resolve by
        path, so siblings the `[patch]` table never names lose their source
        too. Eligibility follows the committed source, not the patch keys."""
        head = STANDALONE + (
            '\n[[package]]\nname = "eunomia-macros"\nversion = "0.8.0"\n'
            'source = "git+https://github.com/ryancinsight/eunomia#abc123"\n'
        )
        work = STRIPPED + (
            '\n[[package]]\nname = "eunomia-macros"\nversion = "0.8.0"\n'
        )
        self.assertTrue(_lock_form._strip_only(head, work))

    def test_moved_git_rev_is_not_restorable(self) -> None:
        """A first-party package repinned to a different rev is a real
        re-resolve, not the overlay dropping a source."""
        work = STANDALONE.replace("#abc123", "#deadbee")
        self.assertFalse(_lock_form._strip_only(STANDALONE, work))

    def test_pure_overlay_strip_is_restorable(self) -> None:
        self.assertTrue(_lock_form._strip_only(STANDALONE, STRIPPED))

    def test_patched_package_ahead_in_the_local_tree_is_restorable(self) -> None:
        """The local tree is routinely ahead of the pinned rev, so a patched
        package's version moves too. That is still pure churn."""
        ahead = STRIPPED.replace('version = "0.8.0"', 'version = "0.9.0"')
        self.assertTrue(_lock_form._strip_only(STANDALONE, ahead))

    def test_untouched_package_version_change_is_not_restorable(self) -> None:
        """A package the overlay does not patch changing version is a real
        re-resolve; restore must never discard it."""
        head = STANDALONE + '\n[[package]]\nname = "rand"\nversion = "0.8.0"\n'
        work = STRIPPED + '\n[[package]]\nname = "rand"\nversion = "0.9.0"\n'
        self.assertFalse(_lock_form._strip_only(head, work))

    def test_gained_source_is_not_restorable(self) -> None:
        """Churn only ever drops sources. A source the committed lock never
        carried means the working copy re-resolved for real."""
        work = STRIPPED.replace(
            'name = "eunomia"\nversion = "0.8.0"',
            'name = "eunomia"\nversion = "0.8.0"\n'
            'source = "git+https://github.com/ryancinsight/eunomia#deadbee"',
        )
        self.assertFalse(_lock_form._strip_only(STANDALONE, work))

    def test_residue_removal_is_not_restorable(self) -> None:
        """A working copy that repairs a residue-carrying committed lock must
        survive `restore`; churn only ever adds residue, never removes it."""
        self.assertFalse(_lock_form._strip_only(STRIPPED, STANDALONE))

    def test_added_untouched_package_is_not_restorable(self) -> None:
        added = STRIPPED + '\n[[package]]\nname = "rand"\nversion = "0.9.0"\n'
        self.assertFalse(_lock_form._strip_only(STANDALONE, added))


class HookCommitTestCase(unittest.TestCase):
    """`publish-hooks` builds on the default branch and touches no tree."""

    def _git(self, repo: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True, capture_output=True, encoding="utf-8",
        ).stdout.strip()

    def test_commit_carries_the_hooks_and_leaves_the_checkout_alone(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-") as temp:
            root = Path(temp)
            repo = root / "member"
            repo.mkdir()
            self._git(repo, "init", "-q", "-b", "main")
            self._git(repo, "config", "core.autocrlf", "false")
            # `hook_commit` runs `commit-tree` without the `-c` identity this
            # helper passes; a CI runner has no global identity to fall back on.
            self._git(repo, "config", "user.email", "t@t")
            self._git(repo, "config", "user.name", "t")
            (repo / "lib.rs").write_text("one\n", encoding="utf-8")
            self._git(repo, "add", "lib.rs")
            self._git(repo, "commit", "-q", "-m", "seed")
            base = self._git(repo, "rev-parse", "HEAD")
            # A peer mid-edit: an unrelated branch checked out, dirt, and staging.
            self._git(repo, "switch", "-q", "-c", "peer")
            (repo / "lib.rs").write_text("peer dirt\n", encoding="utf-8")
            (repo / "staged.rs").write_text("staged\n", encoding="utf-8")
            self._git(repo, "add", "staged.rs")
            status_before = self._git(repo, "status", "--porcelain")
            hooks = root / "hooks"
            hooks.mkdir()
            (hooks / "pre-push").write_bytes(b"#!/bin/sh\r\nexit 0\n")

            commit = _lock_form.hook_commit(
                repo, base, [("pre-push", (hooks / "pre-push").read_bytes())], "ci: sync\n"
            )

            self.assertIsNotNone(commit)
            self.assertEqual(self._git(repo, "rev-parse", f"{commit}^"), base)
            listing = self._git(repo, "ls-tree", commit, ".githooks/pre-push")
            self.assertTrue(listing.startswith("100755 blob "), listing)
            blob = subprocess.run(
                ["git", "-C", str(repo), "cat-file", "blob", f"{commit}:.githooks/pre-push"],
                check=True, capture_output=True,
            ).stdout
            self.assertEqual(blob, b"#!/bin/sh\r\nexit 0\n", "bytes, not a re-encoded copy")
            self.assertEqual(self._git(repo, "ls-tree", "--name-only", commit, "lib.rs"), "lib.rs")
            self.assertEqual(self._git(repo, "show", f"{commit}:lib.rs"), "one")
            self.assertEqual(self._git(repo, "status", "--porcelain"), status_before)
            self.assertEqual(self._git(repo, "rev-parse", "--abbrev-ref", "HEAD"), "peer")

    def test_publish_reads_the_committed_hooks_not_the_checkout(self) -> None:
        """A peer's uncommitted edit to the hook in a shared atlas checkout must
        not be what reaches the members."""
        with tempfile.TemporaryDirectory(prefix="atlas-publish-") as temp:
            atlas = Path(temp) / "atlas"
            hook = atlas / "scripts" / "git-hooks" / "pre-push"
            hook.parent.mkdir(parents=True)
            self._git(atlas, "init", "-q", "-b", "main")
            self._git(atlas, "config", "core.autocrlf", "false")
            hook.write_bytes(b"#!/bin/sh\nexit 0\n")
            self._git(atlas, "add", ".")
            self._git(atlas, "commit", "-q", "-m", "hooks")
            hook.write_bytes(b"#!/bin/sh\necho peer edit\n")

            hooks = _lock_form.committed_hooks(atlas, "main")

            self.assertEqual(hooks, [("pre-push", b"#!/bin/sh\nexit 0\n")])

    def test_a_member_already_carrying_the_hooks_needs_no_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-publish-") as temp:
            root = Path(temp)
            repo = root / "member"
            (repo / ".githooks").mkdir(parents=True)
            self._git(repo, "init", "-q", "-b", "main")
            (repo / ".githooks" / "pre-push").write_bytes(b"#!/bin/sh\nexit 0\n")
            self._git(repo, "add", ".githooks/pre-push")
            self._git(repo, "update-index", "--chmod=+x", ".githooks/pre-push")
            self._git(repo, "commit", "-q", "-m", "seed")
            hooks = root / "hooks"
            hooks.mkdir()
            (hooks / "pre-push").write_bytes(b"#!/bin/sh\nexit 0\n")

            commit = _lock_form.hook_commit(
                repo,
                self._git(repo, "rev-parse", "HEAD"),
                [("pre-push", (hooks / "pre-push").read_bytes())],
                "ci: sync\n",
            )

            self.assertIsNone(commit)

class HookDeploymentTestCase(unittest.TestCase):
    def test_selected_members_receive_exact_owned_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hooks-") as temp:
            repos = Path(temp)
            for member in ("alpha", "beta"):
                (repos / member / ".githooks").mkdir(parents=True)
                (repos / member / ".githooks/pre-push").write_bytes(b"previous\n")
            with patch.object(_lock_form, "REPOS", repos), patch.object(
                _lock_form, "registered_member_names", return_value=["alpha", "beta"]
            ):
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(Namespace(members=["alpha"], check=False)), 0
                )
                source = SCRIPT.parent / "git-hooks/pre-push"
                self.assertEqual(
                    (repos / "alpha/.githooks/pre-push").read_bytes(), source.read_bytes()
                )
                self.assertEqual(
                    (repos / "beta/.githooks/pre-push").read_bytes(), b"previous\n"
                )
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(Namespace(members=["alpha"], check=True)), 0
                )
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(Namespace(members=[], check=True)), 1
                )
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(Namespace(members=[], check=False)), 0
                )
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(Namespace(members=[], check=True)), 0
                )

    def test_selected_hook_does_not_touch_other_owned_hooks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hooks-") as temp:
            repos = Path(temp)
            (repos / "alpha" / ".githooks").mkdir(parents=True)
            (repos / "alpha" / ".githooks" / "pre-push").write_bytes(b"previous\n")
            (repos / "alpha" / ".githooks" / "pre-commit").write_bytes(b"commit\n")
            with patch.object(_lock_form, "REPOS", repos), patch.object(
                _lock_form, "registered_member_names", return_value=["alpha"]
            ):
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(
                        Namespace(members=["alpha"], check=False, hook="pre-push")
                    ),
                    0,
                )
                self.assertEqual(
                    (repos / "alpha/.githooks/pre-push").read_bytes(),
                    (SCRIPT.parent / "git-hooks/pre-push").read_bytes(),
                )
                self.assertEqual(
                    (repos / "alpha/.githooks/pre-commit").read_bytes(), b"commit\n"
                )
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(
                        Namespace(members=["alpha"], check=False, hook="missing")
                    ),
                    2,
                )

    def test_unknown_member_is_rejected_before_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-hooks-") as temp:
            repos = Path(temp)
            with patch.object(_lock_form, "REPOS", repos), patch.object(
                _lock_form, "registered_member_names", return_value=["alpha"]
            ):
                self.assertEqual(
                    _lock_form.cmd_sync_hooks(Namespace(members=["../other"], check=False)),
                    2,
                )
                self.assertEqual(list(repos.iterdir()), [])


def owned_hook(label: str) -> bytes:
    """A pre-push that reports its label, each argument and its first stdin line."""
    return (
        "#!/usr/bin/env bash\n"
        "read -r line\n"
        f"printf '%s argc=%s' '{label}' \"$#\"\n"
        "printf ' [%s]' \"$@\"\n"
        "printf ' <%s>\\n' \"$line\"\n"
    ).encode()


# The stalled-write fixture's bound: twice the 60 s each run is given to
# finish, so it never releases early on a loaded host.
STALL_SECONDS = 120


def reap(run: subprocess.Popen) -> None:
    """Stop a shim run a failed test left behind, so none outlives the suite."""
    if run.poll() is None:
        run.kill()
    run.communicate(timeout=60)


class HookInstallTestCase(unittest.TestCase):
    """Members run the owned hooks as committed at the Atlas `origin/main`."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-hooks-")
        # First registered, so it runs last: after every run is reaped.
        self.addCleanup(self._tmp.cleanup)
        # A quote, a `$`, a backtick and a space: the shim names this path in bash.
        self.atlas = Path(self._tmp.name) / "at'l$as `x` y"
        self.repos = self.atlas / "repos"
        subprocess.run(["git", "init", "-q", str(self.atlas)], check=True)

    def git(self, repo: Path, *args: str, **kwargs) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, check=True, **kwargs,
        ).stdout.strip()

    def publish(self, hooks: dict[str, bytes]) -> None:
        """Move origin/main to a commit whose `scripts/git-hooks` is `hooks`.

        Built through a private index, so the checkout's branch, index and
        files stay where the test left them -- as a peer's would."""
        index = Path(self._tmp.name) / "publish-index"
        environment = {**os.environ, "GIT_INDEX_FILE": str(index)}
        index.unlink(missing_ok=True)
        for name, content in hooks.items():
            source = Path(self._tmp.name) / "publish-blob"
            source.write_bytes(content)
            blob = self.git(self.atlas, "hash-object", "-w", "--no-filters", str(source))
            self.git(
                self.atlas, "update-index", "--add", "--cacheinfo",
                f"100755,{blob},scripts/git-hooks/{name}", env=environment,
            )
        tree = self.git(self.atlas, "write-tree", env=environment)
        commit = self.git(
            self.atlas, "-c", "user.name=t", "-c", "user.email=t@t",
            "commit-tree", tree, "-m", "publish",
        )
        self.git(self.atlas, "update-ref", "refs/remotes/origin/main", commit)

    def member(self, name: str, hooks_path: str | None = None) -> Path:
        repo = self.repos / name
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        if hooks_path is not None:
            self.git(repo, "config", "core.hooksPath", hooks_path)
        return repo

    def shim_dir(self) -> Path:
        common = self.git(self.atlas, "rev-parse", "--path-format=absolute", "--git-common-dir")
        return Path(common) / "atlas-hooks"

    def submodule_member(self, name: str) -> Path:
        """A member as the stack holds one: a submodule of the Atlas repository,
        its git directory under the Atlas `.git/modules`."""
        source = Path(self._tmp.name) / f"{name}-source"
        subprocess.run(["git", "init", "-q", str(source)], check=True)
        for file in ("a.txt", "b.txt"):
            (source / file).write_bytes(b"seed\n")
        self.git(source, "add", "a.txt", "b.txt")
        self.git(source, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "seed")
        self.git(self.atlas, "-c", "protocol.file.allow=always",
                 "submodule", "add", "-q", str(source), f"repos/{name}")
        return self.repos / name

    def hook_context(self, tree: Path, *command: str, git_dir: Path | None = None) -> dict[str, str]:
        """What the context hook saw when `command` ran in `tree`, with
        `git_dir` named explicitly when it cannot be found from `tree`."""
        location = ["-C", str(tree)]
        if git_dir is not None:
            location += [f"--git-dir={git_dir}", "--work-tree=."]
        result = subprocess.run(
            ["git", *location, "-c", "user.name=t", "-c", "user.email=t@t", *command],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        seen = dict(
            line[len("hook-"):].split("=", 1)
            for line in result.stderr.splitlines() if line.startswith("hook-")
        )
        self.assertEqual(sorted(seen), ["gitdir", "marker", "staged"], result.stderr)
        return seen

    def test_a_git_directory_named_only_by_git_reaches_the_hook(self) -> None:
        """`--git-dir` names a repository the work tree cannot find: the hook
        finds it only through the `GIT_DIR` git exports to it."""
        context = (
            b"#!/usr/bin/env bash\n"
            b"printf 'hook-gitdir=%s\\n' \"$(git rev-parse --absolute-git-dir)\" >&2\n"
            b"printf 'hook-marker=%s\\n' \"$(cat .member-marker 2>/dev/null || echo none)\" >&2\n"
            b"printf 'hook-staged=%s\\n' \"$(git diff --cached --name-only | tr '\\n' ,)\" >&2\n"
        )
        self.publish({"pre-commit": context})
        shims = _lock_form.write_hook_shims(self.atlas)
        source = self.submodule_member("alpha")
        detached = Path(self._tmp.name) / "detached.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(source), str(detached)], check=True)
        self.git(detached, "config", "core.bare", "false")
        self.git(detached, "config", "core.hooksPath", shims.as_posix())
        tree = Path(self._tmp.name) / "detached-tree"
        tree.mkdir()
        subprocess.run(
            ["git", "-C", str(tree), f"--git-dir={detached}", "--work-tree=.", "checkout", "-q", "-f", "HEAD"],
            check=True,
        )
        (tree / ".member-marker").write_text("detached", encoding="utf-8")
        (tree / "a.txt").write_bytes(b"detached\n")
        seen = self.hook_context(tree, "commit", "-q", "-a", "-m", "detached", git_dir=detached)
        self.assertTrue(Path(seen["gitdir"]).samefile(detached), seen)
        self.assertEqual((seen["marker"], seen["staged"]), ("detached", "a.txt,"))

    def test_a_swapped_object_refuses_rather_than_runs(self) -> None:
        """`cat-file` reads whatever the object file holds; the shim hashes the
        copy it wrote, so a refusing hook whose object was replaced by a
        passing one refuses."""
        refusing = b"#!/usr/bin/env bash\necho refused >&2\nexit 3\n"
        self.publish({"pre-push": refusing})
        shims = _lock_form.write_hook_shims(self.atlas)
        blob = self.git(self.atlas, "rev-parse", "refs/remotes/origin/main:scripts/git-hooks/pre-push")
        passing = Path(self._tmp.name) / "passing"
        passing.write_bytes(b"#!/usr/bin/env bash\necho PASSED\n")
        other = self.git(self.atlas, "hash-object", "-w", "--no-filters", str(passing))
        objects = Path(self.git(self.atlas, "rev-parse", "--path-format=absolute", "--git-common-dir")) / "objects"
        target = objects / blob[:2] / blob[2:]
        target.chmod(0o644)
        target.write_bytes((objects / other[:2] / other[2:]).read_bytes())
        run = self.run_shim(shims)
        out, _ = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, out.decode()), (1, ""))
        self.assertEqual([p.name for p in (shims / "blobs").iterdir()], [])

    def test_a_replace_ref_does_not_redirect_the_hook(self) -> None:
        refusing = b"#!/usr/bin/env bash\necho refused >&2\nexit 3\n"
        self.publish({"pre-push": refusing})
        owned = self.git(self.atlas, "rev-parse", "refs/remotes/origin/main")
        self.publish({"pre-push": b"#!/usr/bin/env bash\necho PASSED\n"})
        passing = self.git(self.atlas, "rev-parse", "refs/remotes/origin/main")
        self.git(self.atlas, "update-ref", "refs/remotes/origin/main", owned)
        self.git(self.atlas, "replace", owned, passing)
        shims = _lock_form.write_hook_shims(self.atlas)
        run = self.run_shim(shims, GIT_REPLACE_REF_BASE="refs/replace/")
        out, err = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, out.decode(), err.decode().strip()), (3, "", "refused"))

    def test_a_branch_named_like_the_source_ref_is_never_used(self) -> None:
        """With origin/main gone, `rev-parse` would resolve a local branch named
        `refs/remotes/origin/main`; the shim refuses instead."""
        self.publish({"pre-push": b"#!/usr/bin/env bash\necho refused >&2\nexit 3\n"})
        shims = _lock_form.write_hook_shims(self.atlas)
        self.publish({"pre-push": b"#!/usr/bin/env bash\necho PASSED\n"})
        passing = self.git(self.atlas, "rev-parse", "refs/remotes/origin/main")
        self.git(self.atlas, "update-ref", "-d", "refs/remotes/origin/main")
        self.git(self.atlas, "update-ref", "refs/heads/refs/remotes/origin/main", passing)
        run = self.run_shim(shims)
        out, err = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, out.decode()), (1, ""), err.decode())
        self.assertIn("has no scripts/git-hooks/pre-push", err.decode())

    def test_an_exported_shellopts_reaches_the_hook_unchanged(self) -> None:
        """Bash re-exports an inherited SHELLOPTS with its current options, so
        the hook sees the caller's options -- neither the shim's own
        `set -euo pipefail` nor a reset of them -- and the caller's
        `noclobber` cannot stop the shim writing its cache."""
        hook = b'#!/usr/bin/env bash\necho "$-|$SHELLOPTS" >&2\nexit 3\n'
        self.publish({"pre-push": hook})
        shims = _lock_form.write_hook_shims(self.atlas)
        direct_file = Path(self._tmp.name) / "direct-hook"
        direct_file.write_bytes(hook)
        for exported in (
            "braceexpand:hashall:interactive-comments",
            "braceexpand:errexit:hashall:interactive-comments:noclobber:nounset:pipefail",
        ):
            with self.subTest(exported=exported):
                # Each run fetches the blob afresh, so `noclobber` meets the
                # write into the shim's temporary file.
                shutil.rmtree(shims / "blobs", ignore_errors=True)
                options = {"SHELLOPTS": exported}
                direct = subprocess.run(
                    ["bash", str(direct_file)], capture_output=True, env={**os.environ, **options},
                )
                run = self.run_shim(shims, **options)
                _, err = run.communicate(b"", timeout=60)
                self.assertEqual((direct.returncode, run.returncode), (3, 3))
                self.assertEqual(err.decode().strip(), direct.stderr.decode().strip())
                self.assertEqual("errexit" in err.decode(), "errexit" in exported)

    def test_allexport_does_not_leak_the_shims_variables_into_the_hook(self) -> None:
        """With `allexport` inherited, every assignment the shim makes and its
        lookup function would reach the hook's environment; the hook
        still sees the option itself."""
        self.publish({"pre-push": b"#!/usr/bin/env bash\nenv >&2\nexit 3\n"})
        shims = _lock_form.write_hook_shims(self.atlas)
        run = self.run_shim(shims, SHELLOPTS="allexport:braceexpand:hashall:interactive-comments")
        _, err = run.communicate(b"", timeout=60)
        self.assertEqual(run.returncode, 3, err.decode())
        seen = dict(
            line.split("=", 1) for line in err.decode().splitlines() if "=" in line
        )
        leaked = {name for name in seen if "__atlas_shim_" in name}
        self.assertEqual(leaked, set())
        self.assertIn("allexport", seen["SHELLOPTS"].split(":"))

    def test_a_caller_variable_named_like_a_shim_variable_reaches_the_hook_unchanged(self) -> None:
        self.publish({"pre-push": b"#!/usr/bin/env bash\nenv >&2\nexit 3\n"})
        shims = _lock_form.write_hook_shims(self.atlas)
        caller = {
            "cache": "c", "commit": "m", "blob": "b", "partial": "p",
            "caller_options": "o", "atlas_git": "g",
        }
        run = self.run_shim(shims, **caller)
        _, err = run.communicate(b"", timeout=60)
        self.assertEqual(run.returncode, 3, err.decode())
        seen = dict(line.split("=", 1) for line in err.decode().splitlines() if "=" in line)
        self.assertEqual({name: seen.get(name) for name in caller}, caller)

    def test_a_callers_exported_function_named_atlas_reaches_the_hook(self) -> None:
        self.publish({"pre-push": b"#!/usr/bin/env bash\natlas >&2\nexit 3\n"})
        shims = _lock_form.write_hook_shims(self.atlas)
        run = self.run_shim(shims, **{"BASH_FUNC_atlas%%": "() { echo caller-atlas; }"})
        _, err = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, err.decode().strip()), (3, "caller-atlas"))

    def test_an_inherited_xtrace_traces_the_hook_and_not_the_shim(self) -> None:
        hook = b"#!/usr/bin/env bash\necho hook-ran >&2\nexit 3\n"
        self.publish({"pre-push": hook})
        shims = _lock_form.write_hook_shims(self.atlas)
        direct_file = Path(self._tmp.name) / "direct-hook"
        direct_file.write_bytes(hook)
        options = {"SHELLOPTS": "braceexpand:hashall:interactive-comments:xtrace"}
        direct = subprocess.run(
            ["bash", str(direct_file)], capture_output=True, env={**os.environ, **options},
        )
        run = self.run_shim(shims, **options)
        _, err = run.communicate(b"", timeout=60)
        self.assertEqual((direct.returncode, run.returncode), (3, 3))
        direct_lines = direct.stderr.decode().splitlines()
        self.assertIn("+ echo hook-ran", direct_lines)
        # The hook's trace is the direct run's; the shim adds only its exec.
        extra = [line for line in err.decode().splitlines() if line not in direct_lines]
        self.assertEqual(len(extra), 1, extra)
        self.assertTrue(extra[0].startswith("+ exec "), extra)
        self.assertEqual([line for line in err.decode().splitlines() if line in direct_lines], direct_lines)

    def test_a_crlf_cache_copy_is_rewritten_under_autocrlf(self) -> None:
        """`core.autocrlf` hashes a CRLF file as its LF blob; the cache check
        hashes raw bytes, so the converted copy is rewritten before it runs."""
        self.git(self.atlas, "config", "core.autocrlf", "true")
        refusing = b"#!/usr/bin/env bash\necho refused >&2\nexit 3\n"
        self.publish({"pre-push": refusing})
        shims = _lock_form.write_hook_shims(self.atlas)
        run = self.run_shim(shims)
        run.communicate(b"", timeout=60)
        (cached,) = (shims / "blobs").iterdir()
        cached.write_bytes(refusing.replace(b"\n", b"\r\n"))
        run = self.run_shim(shims)
        _, err = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, err.decode().strip()), (3, "refused"))
        self.assertEqual(cached.read_bytes(), refusing)

    def test_a_hook_holding_a_carriage_return_runs_under_autocrlf(self) -> None:
        """A blob whose bytes hold CRLF hashes to its own id only unfiltered;
        a filtered hash would refuse every run of that hook."""
        self.git(self.atlas, "config", "core.autocrlf", "true")
        hook = b"#!/usr/bin/env bash\n# written on Windows\r\necho refused >&2\nexit 3\n"
        self.publish({"pre-push": hook})
        shims = _lock_form.write_hook_shims(self.atlas)
        run = self.run_shim(shims)
        _, err = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, err.decode().strip()), (3, "refused"))
        (cached,) = (shims / "blobs").iterdir()
        self.assertEqual(cached.read_bytes(), hook)

    def test_a_shim_held_open_is_replaced_once_the_reader_lets_go(self) -> None:
        self.publish({"pre-push": owned_hook("owned")})
        shim = _lock_form.write_hook_shims(self.atlas) / "pre-push"
        refusals = [PermissionError("in use")] * 3
        real_replace = os.replace

        def busy(source, target):
            if refusals:
                raise refusals.pop()
            real_replace(source, target)

        with patch.object(_lock_form, "HOOK_SHIM", _lock_form.HOOK_SHIM + "# reinstalled\n"), \
                patch.object(_lock_form, "SHIM_REPLACE_BACKOFF_SECONDS", 0), \
                patch.object(_lock_form.os, "replace", side_effect=busy):
            _lock_form.write_hook_shims(self.atlas)
        self.assertEqual(refusals, [])
        self.assertTrue(shim.read_bytes().endswith(b"# reinstalled\n"))

    @unittest.skipIf(os.name == "nt", "Windows has no execute bit")
    def test_a_shim_that_lost_its_execute_bit_is_rewritten(self) -> None:
        self.publish({"pre-push": owned_hook("owned")})
        shim = _lock_form.write_hook_shims(self.atlas) / "pre-push"
        shim.chmod(0o644)
        _lock_form.write_hook_shims(self.atlas)
        self.assertTrue(shim.stat().st_mode & 0o100)

    def run_shim(self, shims: Path, *, path: str | None = None, **extra: str):
        environment = {**os.environ, **extra}
        if path is not None:
            environment["PATH"] = path + os.pathsep + environment["PATH"]
        run = subprocess.Popen(
            ["bash", str(shims / "pre-push"), "origin", "url"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=environment,
        )
        self.addCleanup(reap, run)
        return run

    def test_a_refusing_hook_refuses_through_its_shim(self) -> None:
        self.publish({"pre-push": b"#!/usr/bin/env bash\necho refused >&2\nexit 3\n"})
        shims = _lock_form.write_hook_shims(self.atlas)
        run = self.run_shim(shims)
        _, err = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, err.decode().strip()), (3, "refused"))

    def test_a_cache_being_written_is_never_visible_or_run(self) -> None:
        """A first run stalls mid-write; the cache path stays absent, and a
        second run executes the whole hook rather than the part written."""
        self.publish({"pre-push": owned_hook("owned")})
        shims = _lock_form.write_hook_shims(self.atlas)
        fake = Path(self._tmp.name) / "fake-bin"
        fake.mkdir()
        stalled, release = Path(self._tmp.name) / "stalled", Path(self._tmp.name) / "release"
        # The stalled write waits on `release` for at most STALL_SECONDS of
        # wall-clock time (bash's `SECONDS`, not an iteration count, which
        # `sleep` and process start cost stretch many times over); a failing
        # assertion releases it at cleanup, so no run outlives the test.
        real = shutil.which("git")
        (fake / "git").write_bytes(
            (
                "#!/usr/bin/env bash\n"
                f"real={_lock_form._shell_word(Path(real).as_posix())}\n"
                'if [[ " $* " == *" cat-file "* ]]; then\n'
                '  "$real" "$@" | head -c 40\n'
                f"  : > {_lock_form._shell_word(stalled.as_posix())}\n"
                f"  until=$((SECONDS + {STALL_SECONDS}))\n"
                f"  while [ $SECONDS -lt $until ] && [ ! -f {_lock_form._shell_word(release.as_posix())} ]; do\n"
                "    sleep 0.05\n"
                "  done\n"
                '  "$real" "$@" | tail -c +41\n'
                "  exit 0\n"
                "fi\n"
                'exec "$real" "$@"\n'
            ).encode()
        )
        (fake / "git").chmod(0o755)
        first = self.run_shim(shims, path=fake.as_posix())
        self.addCleanup(release.write_text, "go", encoding="utf-8")
        deadline = time.monotonic() + 60
        while not stalled.exists():
            self.assertIsNone(first.poll(), "the first run ended before its write stalled")
            self.assertLess(time.monotonic(), deadline, "the first run never reached its write")
            time.sleep(0.02)
        blob = self.git(self.atlas, "rev-parse", "refs/remotes/origin/main:scripts/git-hooks/pre-push")
        blob_dir = shims / "blobs"
        # The part-written copy sits beside the cache, in the same directory,
        # so the rename that publishes it is one directory-entry swap.
        (partial,) = blob_dir.iterdir()
        self.assertTrue(partial.name.startswith(f"{blob}."), partial.name)
        partial_id = partial.stat().st_ino
        second = self.run_shim(shims)
        out, err = second.communicate(b"line\n", timeout=60)
        self.assertEqual((second.returncode, out.decode().strip()),
                         (0, "owned argc=2 [origin] [url] <line>"), err.decode())
        release.write_text("go", encoding="utf-8")
        out, err = first.communicate(b"line\n", timeout=60)
        self.assertEqual((first.returncode, out.decode().strip()),
                         (0, "owned argc=2 [origin] [url] <line>"), err.decode())
        (cached,) = blob_dir.iterdir()
        self.assertEqual(cached.read_bytes(), owned_hook("owned"))
        # The first run's file was renamed into place, not copied: a copy
        # writes the cache path in place, visible part-written.
        self.assertEqual((cached.name, cached.stat().st_ino), (blob, partial_id))

    def test_a_failed_write_runs_nothing_and_leaves_no_partial(self) -> None:
        """origin/main names a hook blob the object store lacks, and the cache
        holds a corrupt copy: the shim refuses without running either."""
        missing = "1" * 40

        def mktree(entry: str) -> str:
            # Bytes, so Windows text mode does not end each name in a CR.
            return subprocess.run(
                ["git", "-C", str(self.atlas), "mktree", "--missing"],
                input=entry.encode(), capture_output=True, check=True,
            ).stdout.decode().strip()

        hooks = mktree(f"100755 blob {missing}\tpre-push\n")
        scripts = mktree(f"040000 tree {hooks}\tgit-hooks\n")
        top = mktree(f"040000 tree {scripts}\tscripts\n")
        commit = self.git(
            self.atlas, "-c", "user.name=t", "-c", "user.email=t@t", "commit-tree", top, "-m", "gone",
        )
        self.git(self.atlas, "update-ref", "refs/remotes/origin/main", commit)
        shims = _lock_form.write_hook_shims(self.atlas)
        corrupt = shims / "blobs" / missing
        corrupt.parent.mkdir()
        corrupt.write_bytes(b"#!/usr/bin/env bash\necho CORRUPT-CACHE-RAN\n")
        run = self.run_shim(shims)
        out, _ = run.communicate(b"", timeout=60)
        self.assertEqual((run.returncode, out.decode()), (1, ""))
        self.assertEqual(sorted(p.name for p in (shims / "blobs").iterdir()), [missing])

    def test_an_exported_common_dir_does_not_redirect_the_lookup(self) -> None:
        self.publish({"pre-push": owned_hook("owned")})
        shims = _lock_form.write_hook_shims(self.atlas)
        member = self.member("alpha")
        run = self.run_shim(
            shims, GIT_COMMON_DIR=str(member / ".git"), GIT_OBJECT_DIRECTORY=str(member / ".git" / "objects"),
        )
        out, err = run.communicate(b"line\n", timeout=60)
        self.assertEqual((run.returncode, out.decode().strip()),
                         (0, "owned argc=2 [origin] [url] <line>"), err.decode())

    def test_a_reinstall_never_exposes_a_partial_shim(self) -> None:
        """Rewriting the shims while a refusing hook runs must never let a run pass."""
        self.publish({"pre-push": b"#!/usr/bin/env bash\nexit 3\n"})
        shims = _lock_form.write_hook_shims(self.atlas)
        shim = shims / "pre-push"
        content = shim.read_bytes()
        with patch.object(_lock_form, "HOOK_SHIM", _lock_form.HOOK_SHIM + "# reinstalled\n"):
            replaced = []
            real_replace = os.replace

            def observe(source, target):
                # The target still holds the whole previous shim when the
                # rename happens: nothing truncated it first.
                replaced.append(Path(target).read_bytes())
                real_replace(source, target)

            with patch.object(_lock_form.os, "replace", side_effect=observe):
                _lock_form.write_hook_shims(self.atlas)
            self.assertEqual(replaced, [content])
            self.assertTrue(shim.read_bytes().endswith(b"# reinstalled\n"))
            # A second install with unchanged bytes writes nothing.
            with patch.object(_lock_form.os, "replace", side_effect=AssertionError("rewrote")):
                _lock_form.write_hook_shims(self.atlas)
        self.assertEqual([p.name for p in shims.iterdir() if p.name.startswith(".")], [])

    def test_a_missing_owned_hook_refuses_rather_than_passing(self) -> None:
        self.publish({"pre-push": owned_hook("owned")})
        shims = _lock_form.write_hook_shims(self.atlas)
        self.publish({"pre-commit": b"#!/usr/bin/env bash\n"})
        result = subprocess.run(["bash", str(shims / "pre-push")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("has no scripts/git-hooks/pre-push", result.stderr)

    def test_concurrent_first_runs_each_execute_the_whole_hook(self) -> None:
        # Large enough that a cache written in place is caught part-written.
        padding = b"".join(b"# %06d padding\n" % line for line in range(20000))
        hook = owned_hook("owned") + padding
        self.publish({"pre-push": hook})
        shims = _lock_form.write_hook_shims(self.atlas)
        runs = [self.run_shim(shims) for _ in range(24)]
        outcomes = [run.communicate(b"line\n", timeout=120) for run in runs]
        self.assertEqual(
            [(run.returncode, out.decode().strip()) for run, (out, _) in zip(runs, outcomes)],
            [(0, "owned argc=2 [origin] [url] <line>")] * len(runs),
            [err.decode() for _, err in outcomes],
        )
        (cached,) = (shims / "blobs").iterdir()
        self.assertEqual(cached.read_bytes(), hook)

    def test_member_copies_retarget_to_owned_hooks_and_custom_paths_stay(self) -> None:
        owned = (SCRIPT.parent / "git-hooks").as_posix()
        initial = {"unset": None, "copy": ".githooks", "custom": "D:/elsewhere/hooks"}
        with tempfile.TemporaryDirectory(prefix="atlas-hooks-") as temp:
            repos = Path(temp)
            for member, value in initial.items():
                subprocess.run(
                    ["git", "init", "-q", str(repos / member)], check=True
                )
                if value is not None:
                    subprocess.run(
                        ["git", "-C", str(repos / member), "config", "core.hooksPath", value],
                        check=True,
                    )
            with patch.object(_lock_form, "REPOS", repos), patch.object(
                _lock_form, "registered_member_names", return_value=list(initial)
            ):
                self.assertEqual(_lock_form.cmd_install_hooks(Namespace()), 0)
            configured = {
                member: subprocess.run(
                    ["git", "-C", str(repos / member), "config", "--local", "--get",
                     "core.hooksPath"],
                    capture_output=True, text=True, check=True,
                ).stdout.strip()
                for member in initial
            }
        self.assertEqual(
            configured,
            {"unset": owned, "copy": owned, "custom": "D:/elsewhere/hooks"},
        )


class PublishRequestTests(unittest.TestCase):
    """One member, one hook request, and a re-run that reuses it."""

    def test_publish_hooks_takes_no_branch_of_its_own(self) -> None:
        """A 14:47 run named `ci/sync-stack-hooks-20260921` and a 16:03 run the
        default, leaving thirteen members two open requests that deployed
        different hook revisions -- and a date marker on a ref."""
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("--branch", source)
        self.assertIn("branch = PUBLISH_BRANCH", source)

    def test_an_open_request_is_the_idempotent_case(self) -> None:
        """A re-run force-pushes the same branch, so `gh pr create` refuses; the
        request it names already points at the commit just pushed. Raising there
        skipped the `--auto` enqueue for exactly the members that needed it."""
        self.assertTrue(_lock_form.request_already_open(
            1, 'a pull request for branch "ci/sync-stack-hooks" already exists:\n'))

    def test_any_other_refusal_still_fails(self) -> None:
        self.assertFalse(
            _lock_form.request_already_open(1, "could not resolve to a Repository"))

    def test_a_created_request_is_not_mistaken_for_an_existing_one(self) -> None:
        self.assertFalse(_lock_form.request_already_open(0, ""))


if __name__ == "__main__":
    unittest.main()


class LockUnitsTestCase(unittest.TestCase):
    """`status` and `restore` act on every tracked lock at HEAD, members and
    superproject alike."""

    MANIFEST = textwrap.dedent(
        """\
        [package]
        name = "member"
        version = "0.1.0"

        [dependencies]
        eunomia = { version = "0.8", git = "https://github.com/ryancinsight/eunomia" }
        """
    )

    def _git(self, repo: Path, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
            check=True,
            capture_output=True,
        )

    def _commit(self, repo: Path, files: dict[str, str]) -> None:
        repo.mkdir(parents=True, exist_ok=True)
        self._git(repo, "init", "-q", "-b", "main")
        for name, text in files.items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        self._git(repo, "add", "-A")
        self._git(repo, "commit", "-q", "-m", "seed")

    @contextlib.contextmanager
    def _stack(self, member_lock: str, tool_lock: str):
        with tempfile.TemporaryDirectory(prefix="atlas-lock-units-") as temp:
            root = Path(temp)
            self._commit(root / "repos" / "synthetic", {"Cargo.toml": self.MANIFEST, "Cargo.lock": member_lock})
            self._commit(
                root,
                {"tools/t/Cargo.toml": self.MANIFEST, "tools/t/Cargo.lock": tool_lock},
            )
            with (
                patch.object(_lock_form, "REPOS", root / "repos"),
                patch.object(_lock_form, "ROOT", root),
                patch.object(_lock_form, "registered_member_names", lambda: {"synthetic"}),
            ):
                yield root

    def test_every_tracked_lock_of_the_members_and_the_superproject_is_a_unit(self) -> None:
        with self._stack(STANDALONE, STRIPPED):
            units = _lock_form.lock_units()
        self.assertEqual(
            [(unit.label, unit.lock) for unit in units],
            [("synthetic", "Cargo.lock"), ("atlas", "tools/t/Cargo.lock")],
        )
        self.assertEqual(units[0].committed, STANDALONE)
        self.assertEqual(units[0].facts.git_dependencies, {"eunomia"})
        self.assertEqual(units[1].facts.local, {"member"})

    def test_restore_reverts_a_lock_only_the_overlay_rewrote(self) -> None:
        with self._stack(STANDALONE, STANDALONE) as root:
            lock = root / "repos" / "synthetic" / "Cargo.lock"
            lock.write_text(STRIPPED, encoding="utf-8", newline="\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                _lock_form.cmd_restore(None)
            self.assertEqual(lock.read_text(encoding="utf-8"), STANDALONE)
        self.assertIn("restored overlay churn: synthetic/Cargo.lock", output.getvalue())

    def test_restore_leaves_a_real_change_alone(self) -> None:
        repinned = STANDALONE.replace("#abc123", "#feedface")
        with self._stack(STANDALONE, STANDALONE) as root:
            lock = root / "repos" / "synthetic" / "Cargo.lock"
            lock.write_text(repinned, encoding="utf-8", newline="\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                _lock_form.cmd_restore(None)
            self.assertEqual(lock.read_text(encoding="utf-8"), repinned)
        self.assertIn("kept: synthetic/Cargo.lock (real change, left alone)", output.getvalue())

    def test_restore_leaves_a_working_copy_alone_when_the_committed_lock_violates(self) -> None:
        """The working copy may be the repair, and reverting it would restore the
        defect; `lockfile.py --regenerate` is the route for such a lock."""
        with self._stack(STRIPPED, STANDALONE) as root:
            lock = root / "repos" / "synthetic" / "Cargo.lock"
            lock.write_text(STANDALONE, encoding="utf-8", newline="\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                _lock_form.cmd_restore(None)
            self.assertEqual(lock.read_text(encoding="utf-8"), STANDALONE)
        self.assertIn("committed lock itself violates", output.getvalue())

    def test_a_unit_is_the_committed_lock_not_the_staged_one(self) -> None:
        with self._stack(STANDALONE, STANDALONE) as root:
            member = root / "repos" / "synthetic"
            (member / "Cargo.lock").write_text(STRIPPED, encoding="utf-8", newline="\n")
            self._git(member, "add", "Cargo.lock")
            units = _lock_form.lock_units()
        self.assertEqual(units[0].committed, STANDALONE)

    def test_status_reports_the_committed_and_working_verdicts(self) -> None:
        with self._stack(STANDALONE, STRIPPED) as root:
            (root / "repos" / "synthetic" / "Cargo.lock").write_text(STRIPPED, encoding="utf-8", newline="\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                _lock_form.cmd_status(None)
        rows = {line.split()[0]: line.split()[1:] for line in output.getvalue().splitlines()[1:]}
        self.assertEqual(rows["synthetic/Cargo.lock"], ["ok", "STRIPPED"])
        self.assertEqual(rows["atlas/tools/t/Cargo.lock"], ["STRIPPED", "STRIPPED"])


# The tree is ended by a kill and a drain of the pipes it held, which the
# runner bounds at a few seconds each; the margin also absorbs host load. The
# child outlives any deadline plus this margin, so a call that waited for it
# would exceed it.
TEARDOWN_MARGIN_SECONDS = 20
STALL_DEADLINE_SECONDS = 5


STALLED_TREE = textwrap.dedent(
    """\
    import os, subprocess, sys, time

    beat = os.environ["FAKE_HEARTBEAT"]
    if sys.argv[1:2] == ["--child"]:
        # Holds the pipes the parent was given, beating until told to stop or
        # for 80 s, so a test that fails to end it cannot leave it behind.
        for count in range(400):
            if os.path.exists(beat + ".stop"):
                break
            with open(beat, "w") as handle:
                handle.write(str(count))
            time.sleep(0.2)
        sys.exit(0)
    subprocess.Popen([sys.executable, __file__, "--child"])
    time.sleep(80)
    """
)

# The tree is ended by a kill and a drain of the pipes it held, which the
# runner bounds at a few seconds each; the margin also absorbs host load. The
# child outlives any deadline plus this margin, so a call that waited for it
# would exceed it.
TEARDOWN_MARGIN_SECONDS = 20
STALL_DEADLINE_SECONDS = 5


class TreeDeadlineTestCase(unittest.TestCase):
    """A command that outlives its deadline is ended together with its child.

    A parent killed alone leaves a descendant holding the output pipes, and
    reading them then blocks until the descendant exits."""

    def _assert_tree_ended(self, call) -> object:
        with tempfile.TemporaryDirectory(prefix="atlas-tree-") as tmp:
            script = Path(tmp) / "stalled_tree.py"
            script.write_text(STALLED_TREE, encoding="utf-8")
            beat = Path(tmp) / "beat"
            try:
                with patch.dict(os.environ, {"FAKE_HEARTBEAT": str(beat)}):
                    started = time.monotonic()
                    outcome = call(script)
                    elapsed = time.monotonic() - started
                self.assertLess(elapsed, STALL_DEADLINE_SECONDS + TEARDOWN_MARGIN_SECONDS)
                self.assertTrue(beat.exists(), "the child never started")
                first = int(beat.read_text(encoding="utf-8") or "0")
                time.sleep(1.0)
                # Five beats would have passed had the child survived.
                self.assertEqual(int(beat.read_text(encoding="utf-8") or "0"), first)
            finally:
                Path(str(beat) + ".stop").write_text("stop", encoding="utf-8")
            return outcome

    def test_a_command_whose_child_outlives_the_deadline_is_ended_with_its_tree(self) -> None:
        def call(script: Path) -> None:
            with patch.object(_lock_form, "GIT_DEADLINE_SECONDS", STALL_DEADLINE_SECONDS):
                with self.assertRaisesRegex(RuntimeError, "timed out"):
                    _lock_form.run(sys.executable, str(script))

        self._assert_tree_ended(call)
