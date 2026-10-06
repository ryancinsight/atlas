#!/usr/bin/env python3
"""The member `pre-commit` hook runs the stack's lockfile checker.

A member carries no `scripts/lockfile.py`: the hook extracts the checker from
the stack's fetched default branch and runs `--check-staged` against the
member's index. These tests run the hook script itself, with the stack's real
checker, in fixture repositories. Inside a stack every failure to produce a
verdict refuses the commit; only a clone with no stack above it passes
unchecked, and says so.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
HOOK = SCRIPTS / "git-hooks" / "pre-commit"
PRE_PUSH = SCRIPTS / "git-hooks" / "pre-push"
CHECKER = SCRIPTS / "lockfile.py"

IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]
FIRST_PARTY = (
    '[[package]]\nname = "provider"\nversion = "0.1.0"\n'
    'source = "git+https://github.com/ryancinsight/provider.git?branch=main#abc123"\n'
)
FLATTENED = '[[package]]\nname = "provider"\nversion = "0.1.0"\n'
DECLARES = (
    '[package]\nname = "member"\nversion = "0.1.0"\n\n[dependencies]\n'
    'provider = { git = "https://github.com/ryancinsight/provider", version = "0.1" }\n'
)
REGISTRY = '[submodule "member"]\n\tpath = repos/member\n\turl = ./member\n'


def git(repo: Path, *args: str, **env: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *IDENT, *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )
    return completed.stdout.strip()


def publish_stack(stack: Path, with_checker: bool, fetched: bool = True) -> None:
    """Make a commit of the stack's `scripts/` its fetched default.

    The stack registers its members in `.gitmodules`, which is how the hook
    recognises it; `fetched=False` leaves it without a remote-tracking default.
    """
    stack.mkdir(parents=True, exist_ok=True)
    git(stack, "init", "-q")
    (stack / ".gitmodules").write_text(REGISTRY, encoding="utf-8", newline="\n")
    (stack / "scripts").mkdir(parents=True)
    if with_checker:
        shutil.copyfile(CHECKER, stack / "scripts" / "lockfile.py")
    else:
        (stack / "scripts" / "other.py").write_text("pass\n", encoding="utf-8")
    git(stack, "add", ".gitmodules", "scripts")
    git(stack, "commit", "-q", "-m", "stack")
    if fetched:
        git(stack, "update-ref", "refs/remotes/origin/main", git(stack, "rev-parse", "HEAD"))


def make_member(root: Path) -> Path:
    root.mkdir(parents=True)
    git(root, "init", "-q")
    (root / "Cargo.toml").write_text(DECLARES, encoding="utf-8", newline="\n")
    (root / "Cargo.lock").write_text(FIRST_PARTY, encoding="utf-8", newline="\n")
    git(root, "add", "Cargo.toml", "Cargo.lock")
    git(root, "commit", "-q", "-m", "seed")
    return root


def add_worktree(member: Path, where: Path) -> Path:
    """A linked worktree of `member` at `where`, as a lane or a harness makes one."""
    where.parent.mkdir(parents=True, exist_ok=True)
    git(member, "worktree", "add", "-q", "-b", where.name, str(where))
    return where


def stage_lock(member: Path, text: str, name: str = "Cargo.lock") -> None:
    path = member / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    git(member, "add", name)


def run_hook(member: Path, **env: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.update(env)
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=member,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def function_text(hook: Path, name: str) -> str:
    text = hook.read_bytes().decode("utf-8")
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", text, re.S | re.M)
    assert match is not None, f"{hook.name} defines no {name}"
    return match.group(0)


class PreCommitLockfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="atlas-pre-commit-")
        self.addCleanup(self.directory.cleanup)
        self.stack = Path(self.directory.name)

    def member_in_stack(
        self,
        with_checker: bool = True,
        fetched: bool = True,
        below: tuple[str, ...] = ("repos", "member"),
        stack: Path | None = None,
    ) -> Path:
        """The registered member `repos/member` of a stack, or, when `below`
        names another place, a linked worktree of that member there."""
        stack = self.stack if stack is None else stack
        publish_stack(stack, with_checker, fetched)
        member = make_member(stack / "repos" / "member")
        if below == ("repos", "member"):
            return member
        return add_worktree(member, stack.joinpath(*below))

    def test_a_member_without_a_lockfile_copy_commits_a_sound_lock(self) -> None:
        member = self.member_in_stack()
        self.assertFalse((member / "scripts" / "lockfile.py").exists())
        stage_lock(member, FIRST_PARTY + "# touched\n")
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_the_stack_checker_refuses_a_flattened_staged_lock(self) -> None:
        member = self.member_in_stack()
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(
            "LOCK FORM VIOLATION (staged): Cargo.lock: `provider` locked without a git source",
            completed.stderr,
        )

    def test_a_staged_nested_lock_reaches_the_checker(self) -> None:
        """The hook's own test of what is staged covers every lock, not only
        the root's, or a flattened `fuzz/Cargo.lock` never meets the checker."""
        member = self.member_in_stack()
        (member / "fuzz").mkdir()
        (member / "fuzz" / "Cargo.toml").write_text(DECLARES, encoding="utf-8", newline="\n")
        git(member, "add", "fuzz/Cargo.toml")
        stage_lock(member, FLATTENED, "fuzz/Cargo.lock")
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("fuzz/Cargo.lock", completed.stderr)

    def test_a_member_copy_is_never_the_checker_that_runs(self) -> None:
        """A copy that accepts every lock cannot overrule the stack's verdict."""
        member = self.member_in_stack()
        (member / "scripts").mkdir()
        (member / "scripts" / "lockfile.py").write_text(
            "import sys\nsys.exit(0)\n", encoding="utf-8"
        )
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 1, completed.stderr)

    def test_the_skip_variable_cannot_hide_the_refusal(self) -> None:
        member = self.member_in_stack()
        stage_lock(member, FLATTENED)
        completed = run_hook(member, SKIP_LOCKFILE_CHECK="1")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("SKIP_LOCKFILE_CHECK is no longer honoured", completed.stderr)

    def test_a_commit_that_stages_no_lock_never_reaches_the_stack(self) -> None:
        """The stack default lacks the checker, and the commit still passes."""
        member = self.member_in_stack(with_checker=False)
        (member / "notes.txt").write_text("x", encoding="utf-8")
        git(member, "add", "notes.txt")
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_a_stack_default_without_the_checker_refuses_a_staged_lock(self) -> None:
        member = self.member_in_stack(with_checker=False)
        stage_lock(member, FIRST_PARTY + "# touched\n")
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("carry no lockfile.py", completed.stderr)

    def test_a_stack_with_no_fetched_default_refuses_a_staged_lock(self) -> None:
        """Inside a stack the checker is owed: a stack that has neither
        `origin/HEAD` nor `origin/main` is not a clone outside any stack."""
        member = self.member_in_stack(fetched=False)
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("neither origin/HEAD nor origin/main", completed.stderr)
        self.assertNotIn("not verified here", completed.stderr)

    def test_a_checkout_deep_below_the_stack_is_still_inside_it(self) -> None:
        """A harness worktree sits at `repos/<member>/.claude/worktrees/<name>`,
        three levels further down than a member, and a lane at
        `worktrees/<name>`, one fewer."""
        for index, below in enumerate((
            ("repos", "member", ".claude", "worktrees", "lane"),
            ("worktrees", "member-lane"),
        )):
            with self.subTest(below=below):
                member = self.member_in_stack(below=below, stack=self.stack / f"stack{index}")
                stage_lock(member, FLATTENED)
                completed = run_hook(member)
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertIn("LOCK FORM VIOLATION (staged)", completed.stderr)

    def git_processes_for(self, name: str, fillers: int = 11) -> int:
        """Git processes one hook run starts for member `name`, registered
        among `fillers` other members (git's own trace2 event log counts
        one `version` event per process)."""
        stack = self.stack / f"stack-{name}"
        publish_stack(stack, with_checker=True)
        names = sorted([name, *(f"filler{index:02d}" for index in range(fillers))])
        (stack / ".gitmodules").write_text(
            "".join(f'[submodule "repos/{n}"]\n\tpath = repos/{n}\n\turl = ./{n}\n' for n in names),
            encoding="utf-8",
            newline="\n",
        )
        for filler in names:
            if filler != name:
                (stack / "repos" / filler).mkdir(parents=True)
                git(stack / "repos" / filler, "init", "-q")
        member = make_member(stack / "repos" / name)
        stage_lock(member, FIRST_PARTY + "# touched\n")
        trace = self.stack / f"{name}.trace2"
        completed = run_hook(member, GIT_TRACE2_EVENT=str(trace))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return trace.read_text(encoding="utf-8").count('"event":"version"')

    def test_the_git_work_does_not_depend_on_the_members_position_in_the_registry(self) -> None:
        """The member is resolved from its object store, not found by probing
        every registered member in turn."""
        first = self.git_processes_for("aaa")
        last = self.git_processes_for("zzz")
        self.assertEqual(first, last)

    def git_processes_for_submodule_lane(self, name: str, fillers: int = 11) -> int:
        """Git processes one hook run starts in a lane of member `name`, a real
        submodule (its gitdir sits in the stack's `.git/modules`), registered
        among `fillers` other members before or after it."""
        stack = self.stack / f"submodule-{name}"
        publish_stack(stack, with_checker=True)
        filler_names = [f"filler{index:02d}" for index in range(fillers)]
        entries = "".join(
            f'[submodule "repos/{n}"]\n\tpath = repos/{n}\n\turl = ./{n}\n' for n in filler_names
        )
        modules = stack / ".gitmodules"
        for filler in filler_names:
            (stack / "repos" / filler).mkdir(parents=True)
            git(stack / "repos" / filler, "init", "-q")
        source = make_member(self.stack / f"source-{name}")
        if name < filler_names[0]:
            modules.write_text("", encoding="utf-8", newline="\n")
        else:
            modules.write_text(entries, encoding="utf-8", newline="\n")
        subprocess.run(
            ["git", "-c", "protocol.file.allow=always", "-C", str(stack),
             "submodule", "add", "-q", str(source), f"repos/{name}"],
            check=True, capture_output=True,
        )
        if name < filler_names[0]:
            with modules.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(entries)
        member = stack / "repos" / name
        self.assertTrue((member / ".git").is_file(), "a submodule keeps its gitdir in the stack")
        lane = add_worktree(member, stack / "worktrees" / f"{name}-lane")
        stage_lock(lane, FIRST_PARTY + "# touched\n")
        trace = self.stack / f"{name}.trace2"
        completed = run_hook(lane, GIT_TRACE2_EVENT=str(trace))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return trace.read_text(encoding="utf-8").count('"event":"version"')

    def test_the_git_work_for_a_submodule_lane_does_not_depend_on_its_position(self) -> None:
        first = self.git_processes_for_submodule_lane("aaa")
        last = self.git_processes_for_submodule_lane("zzz")
        self.assertEqual(first, last)

    def distrusting_environment(self) -> dict[str, str]:
        """Git as it behaves when another account owns every checkout and only
        what the hook itself trusts is readable: no global or system config
        (a user's `safe.directory = *` would hide the case)."""
        empty = self.stack / "empty.gitconfig"
        empty.write_text("", encoding="utf-8")
        return {
            "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1",
            "GIT_CONFIG_GLOBAL": str(empty),
            "GIT_CONFIG_NOSYSTEM": "1",
        }

    def test_a_stack_git_cannot_read_refuses_instead_of_passing_as_no_stack(self) -> None:
        """The hook trusts the checkout it runs in and nothing above it, so a
        stack owned by another account is unreadable to the git calls aimed at
        it. That is a stack the checker is owed by, not the absence of one."""
        member = self.member_in_stack()
        stage_lock(member, FLATTENED)
        completed = run_hook(member, **self.distrusting_environment())
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("registers members but git cannot read it", completed.stderr)
        self.assertIn("safe.directory", completed.stderr)
        self.assertNotIn("no Atlas stack above this clone", completed.stderr)

    def test_the_checker_comes_from_the_fetched_default_not_the_stack_working_tree(self) -> None:
        """A stack checkout may sit on any peer's branch, with any copy of the
        script; the checker that runs is the one the fetched default carries."""
        member = self.member_in_stack()
        permissive = "import sys\nsys.exit(0)\n"
        (self.stack / "scripts" / "lockfile.py").write_text(permissive, encoding="utf-8")
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("LOCK FORM VIOLATION (staged)", completed.stderr)

    def test_the_checker_comes_from_the_fetched_default_not_the_stack_head(self) -> None:
        member = self.member_in_stack()
        (self.stack / "scripts" / "lockfile.py").write_text(
            "import sys\nsys.exit(0)\n", encoding="utf-8"
        )
        git(self.stack, "commit", "-q", "-am", "a peer's unmerged checker")
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("LOCK FORM VIOLATION (staged)", completed.stderr)

    def test_a_gitmodules_planted_in_a_member_does_not_capture_its_worktrees(self) -> None:
        """A harness worktree below a member would otherwise meet the member's
        own `.gitmodules` first and run the member's permissive checker."""
        publish_stack(self.stack, with_checker=True)
        member = make_member(self.stack / "repos" / "member")
        (member / "scripts").mkdir()
        (member / "scripts" / "lockfile.py").write_text(
            "import sys\nsys.exit(0)\n", encoding="utf-8"
        )
        (member / ".gitmodules").write_text(
            '[submodule "x"]\n\tpath = repos/x\n\turl = ./x\n', encoding="utf-8", newline="\n"
        )
        git(member, "add", "scripts", ".gitmodules")
        git(member, "commit", "-q", "-m", "planted")
        worktree = add_worktree(member, member / ".claude" / "worktrees" / "lane")
        stage_lock(worktree, FLATTENED)
        completed = run_hook(worktree)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("LOCK FORM VIOLATION (staged)", completed.stderr)

    def test_a_directory_that_is_not_a_repository_root_is_not_a_stack(self) -> None:
        """A `.gitmodules` registering the member in a directory git does not
        treat as a repository root owns nothing."""
        (self.stack / ".gitmodules").write_text(REGISTRY, encoding="utf-8", newline="\n")
        member = make_member(self.stack / "repos" / "member")
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("no Atlas stack above this clone", completed.stderr)

    def test_only_members_registered_under_repos_make_a_stack(self) -> None:
        publish_stack(self.stack, with_checker=True)
        (self.stack / ".gitmodules").write_text(
            '[submodule "member"]\n\tpath = vendor/member\n\turl = ./member\n',
            encoding="utf-8",
            newline="\n",
        )
        git(self.stack, "commit", "-q", "-am", "vendor only")
        member = make_member(self.stack / "vendor" / "member")
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("no Atlas stack above this clone", completed.stderr)

    def assert_named_as_not_a_member(self, completed: subprocess.CompletedProcess[str]) -> None:
        """The clone is passed, with a message that says a stack is above it and
        does not register it, never that no stack is."""
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("inside the Atlas stack at", completed.stderr)
        self.assertIn("not one of its registered members", completed.stderr)
        self.assertIn("is not verified here", completed.stderr)
        self.assertNotIn("no Atlas stack above this clone", completed.stderr)
        self.assertNotIn("--locked CI", completed.stderr)

    def test_a_checkout_the_stack_does_not_register_is_not_gated_and_says_so(self) -> None:
        """An unrelated repository below the stack shares no member's store: the
        stack does not claim it, so no checker is owed to it."""
        publish_stack(self.stack, with_checker=True)
        make_member(self.stack / "repos" / "member")
        other = make_member(self.stack / "repos" / "other")
        stage_lock(other, FLATTENED)
        self.assert_named_as_not_a_member(run_hook(other))

    def test_a_shared_or_referenced_clone_below_the_stack_is_not_a_member(self) -> None:
        """A `--shared`, `--reference` or alternates clone of a member keeps its
        own object store, so it is not the member whose objects it borrows."""
        publish_stack(self.stack, with_checker=True)
        member = make_member(self.stack / "repos" / "member")
        for index, flag in enumerate(("--shared", "--reference")):
            with self.subTest(flag=flag):
                clone = self.stack / "scratch" / f"clone{index}"
                clone.parent.mkdir(exist_ok=True)
                arguments = [flag, str(member)] if flag == "--reference" else [flag]
                subprocess.run(
                    ["git", "clone", "-q", *arguments, str(member), str(clone)],
                    check=True, capture_output=True,
                )
                stage_lock(clone, FLATTENED)
                self.assert_named_as_not_a_member(run_hook(clone))

    def test_a_candidate_stack_inside_a_repository_git_cannot_read_is_refused(self) -> None:
        """The superproject query prints nothing for a candidate whose
        enclosing repository git cannot read, as it does for one with none, so
        a member carrying its own `.gitmodules` would be taken for the stack.
        An unreadable enclosing repository is unknown, and unknown refuses."""
        publish_stack(self.stack, with_checker=True)
        member = make_member(self.stack / "repos" / "member")
        (member / ".gitmodules").write_text(
            '[submodule "y"]\n\tpath = repos/y\n\turl = ./y\n', encoding="utf-8", newline="\n"
        )
        git(member, "add", ".gitmodules")
        git(member, "commit", "-q", "-m", "planted")
        git(self.stack, "add", "repos/member")
        git(self.stack, "commit", "-q", "-m", "register the member")
        add_worktree(member, member / "repos" / "y")
        lane = add_worktree(member, member / ".claude" / "worktrees" / "lane")
        stage_lock(lane, FLATTENED)
        trusting_the_member = self.stack / "trusting.gitconfig"
        trusting_the_member.write_text(
            f"[safe]\n\tdirectory = {member.resolve().as_posix()}\n", encoding="utf-8"
        )
        environment = self.distrusting_environment()
        environment["GIT_CONFIG_GLOBAL"] = str(trusting_the_member)
        completed = run_hook(lane, **environment)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("cannot be told apart from a submodule", completed.stderr)
        self.assertIn("safe.directory", completed.stderr)

    def test_a_member_that_is_a_submodule_is_never_taken_for_the_stack(self) -> None:
        """A member carrying its own `.gitmodules`, with a worktree of itself at
        the path it registers, would otherwise match its own harness worktree
        and run the member's checker. A candidate with a superproject is a
        submodule, not a stack."""
        publish_stack(self.stack, with_checker=True)
        member = make_member(self.stack / "repos" / "member")
        (member / ".gitmodules").write_text(
            '[submodule "y"]\n\tpath = repos/y\n\turl = ./y\n', encoding="utf-8", newline="\n"
        )
        git(member, "add", ".gitmodules")
        git(member, "commit", "-q", "-m", "planted")
        git(self.stack, "add", "repos/member")
        git(self.stack, "commit", "-q", "-m", "register the member")
        add_worktree(member, member / "repos" / "y")
        lane = add_worktree(member, member / ".claude" / "worktrees" / "lane")
        stage_lock(lane, FLATTENED)
        completed = run_hook(lane)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("LOCK FORM VIOLATION (staged)", completed.stderr)

    def test_a_missing_python_refuses_a_staged_lock(self) -> None:
        """Python that resolves and then fails to run is what the Windows Store
        stub is; with none usable the lock cannot be judged, and the commit is
        refused."""
        member = self.member_in_stack()
        stage_lock(member, FIRST_PARTY + "# touched\n")
        shims = self.stack / "no-python"
        shims.mkdir()
        for name in ("python3", "python"):
            shim = shims / name
            shim.write_text("#!/bin/sh\nexit 127\n", encoding="utf-8", newline="\n")
            shim.chmod(shim.stat().st_mode | stat.S_IXUSR)
        completed = run_hook(
            member, PYTHON="", PATH=str(shims) + os.pathsep + os.environ["PATH"]
        )
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("no python interpreter found", completed.stderr)

    def test_the_index_git_hands_the_hook_is_the_one_judged(self) -> None:
        """A commit may stage through a private `GIT_INDEX_FILE` that the shared
        index knows nothing of; the checker must read it, not the shared one."""
        member = self.member_in_stack()
        index = member / ".git" / "private-index"
        git(member, "read-tree", "HEAD", GIT_INDEX_FILE=str(index))
        blob = subprocess.run(
            ["git", "-C", str(member), "hash-object", "-w", "--stdin"],
            input=FLATTENED,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        git(
            member, "update-index", "--cacheinfo", f"100644,{blob},Cargo.lock",
            GIT_INDEX_FILE=str(index),
        )
        completed = run_hook(member, GIT_INDEX_FILE=str(index))
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("LOCK FORM VIOLATION (staged)", completed.stderr)
        self.assertEqual(run_hook(member).returncode, 0, "the shared index stages nothing")

    def test_a_clone_outside_a_stack_says_the_lock_is_unverified(self) -> None:
        member = make_member(self.stack / "member")
        stage_lock(member, FLATTENED)
        completed = run_hook(member)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("no Atlas stack above this clone", completed.stderr)
        self.assertIn("not verified here", completed.stderr)
        self.assertNotIn("lockfile-guard", completed.stderr)

    def test_the_extracted_checker_is_removed_after_the_run(self) -> None:
        member = self.member_in_stack()
        stage_lock(member, FIRST_PARTY + "# touched\n")
        scratch = self.stack / "tmp"
        scratch.mkdir()
        completed = run_hook(member, TMPDIR=scratch.as_posix())
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(list(scratch.iterdir()), [])


class StackLocatorTests(unittest.TestCase):
    def test_both_hooks_carry_the_same_stack_locator(self) -> None:
        """The hooks deploy as separate files, so the locator is repeated; one
        edit to a single copy would make the two disagree about where a stack is."""
        self.assertEqual(
            function_text(HOOK, "locate_stack"), function_text(PRE_PUSH, "locate_stack")
        )


if __name__ == "__main__":
    unittest.main()
