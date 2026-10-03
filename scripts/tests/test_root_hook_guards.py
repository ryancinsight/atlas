"""Pin the root hook guards against silent removal.

`.githooks/pre-push` carries the pin-advance debt gate beside the coherence
report, and `.githooks/pre-commit` references the detector-parity rationale
that justifies its strict dead-link gate. Both were once dropped from the
working tree without a board item; these cases fail on that state.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from root_hook_support import FIXTURE_PROCESS_TIMEOUT_SECONDS, PRE_COMMIT, PRE_PUSH, ROOT, install_hook


# The git processes one lane commit of a staged gitlink starts, from
# `GIT_TRACE2_EVENT`, measured on git 2.53 (the pre-optimization hook started
# 36): the commit (1), the pre-commit hook's own reads (13: top level, staged
# paths, raw delta, MERGE_HEAD, staged gitlinks, the staged entry, the common
# directory, four member probes, the recorded pin, the file-change list), the
# stale-side guard's (13: HEAD, staged files, index, tree, remote ref, current
# branch twice -- the check and the basis each read it -- branches, ancestry,
# diff, git directory, two shared-index lookups)
# and git's own post-commit `maintenance run --auto` (1). A ceiling, so a
# commit may start fewer and any added process fails the count.
LANE_COMMIT_GIT_PROCESSES = 28


def git_processes(trace: Path) -> list[list[str]]:
    """The argv of every git process a `GIT_TRACE2_EVENT` trace records."""
    events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line]
    return [event["argv"] for event in events if event.get("event") == "start"]


def install_interpreter_shims(shims: Path, launches_log: Path) -> None:
    """`python3` and `python` shims that log their arguments, then run this interpreter.

    Put `shims` first on a hook's PATH: the log then holds one line per
    interpreter launch, the probe included.
    """
    shims.mkdir()
    for name in ("python3", "python"):
        shim = shims / name
        shim.write_text(
            "#!/bin/sh\n"
            f'printf \'%s\\n\' "$*" >> "{launches_log.as_posix()}"\n'
            f'exec "{Path(sys.executable).as_posix()}" "$@"\n',
            encoding="utf-8", newline="\n",
        )
        shim.chmod(0o755)


class RootHookGuardTests(unittest.TestCase):
    def test_provider_config_change_runs_without_book_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

            def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["git", "-C", str(repo), "-c", "user.name=Test",
                     "-c", "user.email=test@example.invalid", *arguments],
                    env=environment, check=check, capture_output=True,
                    text=True, encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            git("init", "-q", "-b", "main")
            git("commit", "--allow-empty", "-qm", "Initial")
            install_hook(repo)
            git("config", "core.hooksPath", ".githooks")
            modules = repo / ".gitmodules"
            invalid = '[submodule "repos/tyche"]\nactive = false\n'
            valid = (ROOT / ".gitmodules").read_text(encoding="utf-8")
            modules.write_text(invalid, encoding="utf-8")
            git("add", ".gitmodules")
            modules.write_text(valid, encoding="utf-8")
            result = git("commit", "-qm", "Disable provider", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("provider-integration-audit: FAIL", result.stdout + result.stderr)
            self.assertIn("repos/tyche missing `active = true`", result.stdout + result.stderr)
            self.assertEqual(git("rev-list", "--count", "HEAD").stdout.strip(), "1")
            git("add", ".gitmodules")
            modules.write_text(invalid, encoding="utf-8")
            result = git("commit", "-qm", "Activate providers", check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(git("show", "HEAD:.gitmodules").stdout, valid)
            self.assertEqual(modules.read_text(encoding="utf-8"), invalid)

    def test_path_limited_commit_checks_its_selected_content(self) -> None:
        for stale_selected, selected_name in ((False, "selected.txt"), (True, "selected.txt"), (False, "backlog.md")):
            with self.subTest(stale_selected=stale_selected, selected_name=selected_name), tempfile.TemporaryDirectory() as temporary:
                repo = Path(temporary)
                environment = {
                    key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_")
                }
                environment.update(
                    GIT_CONFIG_NOSYSTEM="1",
                    GIT_CONFIG_GLOBAL=str(repo / "gitconfig"),
                )
                (repo / "gitconfig").write_text("", encoding="utf-8")

                def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
                    return subprocess.run(
                        ["git", "-C", str(repo), "-c", "user.name=Test",
                         "-c", "user.email=test@example.invalid", *arguments],
                        env=environment, check=check, capture_output=True,
                        text=True, encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                    )

                git("init", "-q", "-b", "main")
                git("config", "core.autocrlf", "false")
                for version in ("old\n", "current\n"):
                    for name in (selected_name, "other.txt"):
                        (repo / name).write_text(version, encoding="utf-8")
                    git("add", selected_name, "other.txt")
                    git("commit", "-qm", version.strip())
                git("switch", "-qc", "fix/selected-content")
                install_hook(repo)
                git("config", "core.hooksPath", ".githooks")

                selected = repo / selected_name
                if stale_selected:
                    selected.write_text("novel\n", encoding="utf-8")
                    git("add", selected_name)
                    selected.write_text("old\n", encoding="utf-8")
                else:
                    (repo / "other.txt").write_text("old\n", encoding="utf-8")
                    git("add", "other.txt")
                    selected.write_text("novel\n", encoding="utf-8")
                result = git("commit", "--only", "-qm", "Selected change", "--", selected_name, check=False)
                if stale_selected:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("STALE SIDE", result.stdout + result.stderr)
                    self.assertIn(selected_name, result.stdout + result.stderr)
                    self.assertEqual(git("show", f"HEAD:{selected_name}").stdout, "current\n")
                else:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(git("show", f"HEAD:{selected_name}").stdout, "novel\n")
                    self.assertEqual(git("show", ":other.txt").stdout, "old\n")
                    self.assertEqual(git("show", "HEAD:other.txt").stdout, "current\n")

    def test_path_limited_gitlink_commit_ignores_other_staged_content(self) -> None:
        """The member probes run without this commit's index and then restore it.

        `git commit --only` hands the hook a temporary index holding just the
        selected paths. A stale file staged in the repository's own index is
        not part of that commit, so a hook that kept probing the member
        without it, and let every later check read the repository's index,
        would refuse the commit for content it does not carry.
        """
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "atlas"
            member = repo / "repos" / "demo"
            member.mkdir(parents=True)
            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith("GIT_")
            }
            environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

            def git(path: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["git", "-C", str(path), "-c", "user.name=Test",
                     "-c", "user.email=test@example.invalid", *arguments],
                    env=environment, check=check, capture_output=True,
                    text=True, encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            git(member, "init", "-q", "-b", "main")
            commits = []
            for value in ("first", "second"):
                (member / "value.txt").write_text(f"{value}\n", encoding="utf-8")
                git(member, "add", "value.txt")
                git(member, "commit", "-qm", value)
                commits.append(git(member, "rev-parse", "HEAD").stdout.strip())
            git(member, "update-ref", "refs/remotes/origin/main", commits[1])
            git(member, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

            git(repo, "init", "-q", "-b", "main")
            git(repo, "config", "core.autocrlf", "false")
            for version in ("old\n", "current\n"):
                (repo / "a.txt").write_text(version, encoding="utf-8")
                git(repo, "add", "a.txt")
                git(repo, "commit", "-qm", version.strip())
            install_hook(repo)
            (repo / ".gitmodules").write_text(
                '[submodule "repos/demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n',
                encoding="utf-8",
            )
            git(repo, "add", ".githooks", "scripts", ".gitmodules")
            git(repo, "update-index", "--add", "--cacheinfo", f"160000,{commits[0]},repos/demo")
            git(repo, "commit", "-qm", "Record demo")
            git(repo, "config", "core.hooksPath", ".githooks")

            # Stage the historical content of a.txt, then restore the file:
            # only the repository's index carries the stale side.
            (repo / "a.txt").write_text("old\n", encoding="utf-8")
            git(repo, "add", "a.txt")
            (repo / "a.txt").write_text("current\n", encoding="utf-8")

            result = git(repo, "commit", "--only", "-qm", "Advance demo", "--", "repos/demo", check=False)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("STALE SIDE", result.stdout + result.stderr)
            self.assertIn(
                f"160000 commit {commits[1]}\trepos/demo",
                git(repo, "ls-tree", "HEAD", "repos/demo").stdout,
            )
            self.assertEqual(git(repo, "show", "HEAD:a.txt").stdout, "current\n")
            self.assertEqual(git(repo, "show", ":a.txt").stdout, "old\n")

    def test_linked_lane_uses_the_canonical_member_checkout_for_gitlinks(self) -> None:
        """An uninitialized lane must validate its staged gitlink from main."""
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "atlas"
            member = repo / "repos" / "demo"
            lane = Path(temporary) / "lane"
            repo.mkdir()
            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith("GIT_")
            }
            environment.update(
                GIT_CONFIG_NOSYSTEM="1",
                GIT_CONFIG_GLOBAL=str(repo / "gitconfig"),
            )
            (repo / "gitconfig").write_text("", encoding="utf-8")

            def git(path: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
                return subprocess.run(
                    [
                        "git", "-C", str(path), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", *arguments,
                    ],
                    env=environment, check=check, capture_output=True,
                    text=True, encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            git(repo, "init", "-q", "-b", "main")
            git(repo, "config", "core.autocrlf", "false")
            member.mkdir(parents=True)
            git(member, "init", "-q", "-b", "main")
            (member / "value.txt").write_text("first\n", encoding="utf-8")
            book = member / "docs" / "book"
            book.mkdir(parents=True)
            (book / "SUMMARY.md").write_text(
                "# Summary\n\n[Chapter](chapter.md)\n", encoding="utf-8",
            )
            (book / "chapter.md").write_text("# Chapter\n", encoding="utf-8")
            git(member, "add", "value.txt")
            git(member, "add", "docs")
            git(member, "commit", "-qm", "first")
            first = git(member, "rev-parse", "HEAD").stdout.strip()
            git(member, "update-ref", "refs/remotes/origin/main", first)
            git(member, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

            install_hook(repo)
            (repo / ".gitmodules").write_text(
                '[submodule "repos/demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n',
                encoding="utf-8",
            )
            git(repo, "add", ".githooks", "scripts", ".gitmodules")
            git(repo, "update-index", "--add", "--cacheinfo", f"160000,{first},repos/demo")
            git(repo, "commit", "-qm", "Record demo")
            git(repo, "config", "core.hooksPath", ".githooks")
            git(repo, "worktree", "add", "-q", "-b", "fix/lane", str(lane))
            (lane / "repos" / "demo").mkdir(parents=True, exist_ok=True)

            (member / "value.txt").write_text("second\n", encoding="utf-8")
            git(member, "add", "value.txt")
            git(member, "commit", "-qm", "second")
            second = git(member, "rev-parse", "HEAD").stdout.strip()
            git(member, "update-ref", "refs/remotes/origin/main", second)
            git(lane, "update-index", "--cacheinfo", f"160000,{second},repos/demo")
            shims = Path(temporary) / "shims"
            launches_log = Path(temporary) / "interpreter.log"
            install_interpreter_shims(shims, launches_log)
            trace = Path(temporary) / "advance.trace.json"
            environment.pop("PYTHON", None)
            environment["GIT_TRACE2_EVENT"] = str(trace)
            environment["PATH"] = f"{shims}{os.pathsep}{environment['PATH']}"
            result = git(lane, "commit", "-qm", "Advance demo", check=False)
            del environment["GIT_TRACE2_EVENT"]
            environment["PATH"] = environment["PATH"].split(os.pathsep, 1)[1]

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Each process costs seconds on a loaded Windows host: the hook
            # resolves the canonical stack root once per commit, not once per
            # member query (an uninitialized lane member made it five times),
            # and reads each fact once.
            processes = git_processes(trace)
            self.assertEqual(
                sum("--git-common-dir" in argv for argv in processes), 1, processes,
            )
            self.assertLessEqual(len(processes), LANE_COMMIT_GIT_PROCESSES, processes)
            # The commit probes for an interpreter once and runs the stale-side
            # guard once, check and basis together.
            self.assertEqual(
                launches_log.read_text(encoding="utf-8").splitlines(),
                ["-c import sys", "scripts/atlas-stale-side-guard.py check basis --staged"],
            )
            launches_log.unlink()
            self.assertIn(
                f"160000 commit {second}\trepos/demo",
                git(lane, "ls-tree", "HEAD", "repos/demo").stdout,
            )

            shutil.rmtree(member / "docs")
            checker = lane / "scripts" / "check_mdbook_links.py"
            checker.write_text(
                checker.read_text(encoding="utf-8") + "\n# exercise linked-lane docs check\n",
                encoding="utf-8",
            )
            git(lane, "add", "scripts/check_mdbook_links.py")
            docs_guard = git(lane, "commit", "-qm", "Run docs guard", check=False)
            self.assertEqual(docs_guard.returncode, 0, docs_guard.stdout + docs_guard.stderr)

            (member / "value.txt").write_text("third\n", encoding="utf-8")
            git(member, "add", "value.txt")
            git(member, "commit", "-qm", "third")
            third = git(member, "rev-parse", "HEAD").stdout.strip()
            member.rename(member.with_name("demo.missing"))
            git(lane, "update-index", "--cacheinfo", f"160000,{third},repos/demo")
            missing_member = git(lane, "commit", "-qm", "Reject missing member", check=False)
            self.assertNotEqual(missing_member.returncode, 0)
            self.assertIn("canonical member checkout is absent", missing_member.stdout + missing_member.stderr)

    def test_separate_git_dir_resolves_the_canonical_worktree_root(self) -> None:
        """Both hooks follow Git metadata in a nested separate-dir layout."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worktree = root / "checkouts" / "canonical"
            metadata = root / "metadata" / "repo.git"
            metadata.parent.mkdir()
            worktree.parent.mkdir()
            subprocess.run(
                ["git", "init", "-q", "-b", "main", "--separate-git-dir", str(metadata), str(worktree)],
                check=True, capture_output=True, text=True,
            )
            install_hook(worktree)
            shutil.copytree(ROOT / "scripts", worktree / "scripts", dirs_exist_ok=True)
            shutil.copyfile(PRE_PUSH, worktree / ".githooks" / "pre-push")
            (worktree / ".githooks" / "pre-push").chmod(0o755)
            shutil.copytree(
                ROOT / "tools" / "gitlink-coherence", worktree / "tools" / "gitlink-coherence",
                ignore=shutil.ignore_patterns("target"),
            )
            member = worktree / "repos" / "demo"
            member.mkdir(parents=True)
            subprocess.run(
                ["git", "init", "-q", "-b", "main", str(member)],
                check=True, capture_output=True, text=True,
            )
            (member / "value.txt").write_text("first\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(member), "add", "value.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(member), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "first"],
                check=True, capture_output=True, text=True,
            )
            first = subprocess.run(
                ["git", "-C", str(member), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(member), "update-ref", "refs/remotes/origin/main", first],
                check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "-C", str(member), "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
                check=True, capture_output=True, text=True,
            )
            (worktree / ".gitmodules").write_text(
                '[submodule "repos/demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n',
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "-C", str(worktree), "add", ".githooks", "scripts", "tools", ".gitmodules"],
                check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "-C", str(worktree), "update-index", "--add", "--cacheinfo", f"160000,{first},repos/demo"],
                check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "-C", str(worktree), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "root"],
                check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "-C", str(worktree), "config", "core.hooksPath", ".githooks"],
                check=True, capture_output=True, text=True,
            )
            lane = root / "lane"
            subprocess.run(
                ["git", "-C", str(worktree), "worktree", "add", "-q", "-b", "lane", str(lane)],
                check=True, capture_output=True, text=True,
            )
            shutil.copyfile(PRE_COMMIT, worktree / ".githooks" / "pre-commit")
            shutil.copyfile(PRE_COMMIT, lane / ".githooks" / "pre-commit")
            common = subprocess.run(
                ["git", "-C", str(lane), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            self.assertTrue(common.endswith("repo.git"))
            configured = subprocess.run(
                ["git", "--git-dir", common, "config", "--get", "core.worktree"],
                capture_output=True, text=True,
            )
            self.assertEqual(configured.stdout, "")

            (member / "value.txt").write_text("second\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(member), "add", "value.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(member), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "second"],
                check=True, capture_output=True, text=True,
            )
            second = subprocess.run(
                ["git", "-C", str(member), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(member), "update-ref", "refs/remotes/origin/main", second],
                check=True, capture_output=True, text=True,
            )
            subprocess.run(
                ["git", "-C", str(lane), "update-index", "--add", "--cacheinfo", f"160000,{second},repos/demo"],
                check=True, capture_output=True, text=True,
            )
            self.assertIn("repos/demo", subprocess.run(
                ["git", "-C", str(lane), "diff", "--cached", "--name-only"],
                check=True, capture_output=True, text=True,
            ).stdout)

            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith("GIT_")
            }
            environment["_ATLAS_HOOK_TRAMPOLINE_DEFERRED"] = "1"
            pre_commit = subprocess.run(
                ["bash", str(lane / ".githooks" / "pre-commit")],
                cwd=lane, env=environment, capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(pre_commit.returncode, 0, pre_commit.stdout + pre_commit.stderr)

            commit = subprocess.run(
                ["git", "-C", str(lane), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "advance"],
                env=environment, capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(commit.returncode, 0, commit.stdout + commit.stderr)

            subprocess.run(
                ["git", "-C", str(lane), "update-ref", "refs/remotes/origin/main", "HEAD"],
                check=True, capture_output=True, text=True,
            )
            # The hook runs the auditor built from origin's
            # tools/gitlink-coherence, cached under the git directory by that
            # tree; nothing is placed in target/release, which it no longer reads.
            auditor_tree = subprocess.run(
                ["git", "-C", str(lane), "rev-parse", "origin/main:tools/gitlink-coherence"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            auditor_name = "gitlink-coherence.exe" if os.name == "nt" else "gitlink-coherence"
            auditor = Path(common) / "atlas-auditor" / auditor_tree / auditor_name
            auditor.parent.mkdir(parents=True)
            built_auditor = ROOT / "target" / "release" / auditor_name
            if not built_auditor.is_file():
                build_environment = dict(os.environ, CARGO_TARGET_DIR=str(ROOT / "target"))
                subprocess.run(
                    ["cargo", "build", "--release", "--locked", "--manifest-path", str(ROOT / "tools/gitlink-coherence/Cargo.toml")],
                    cwd=Path.home(), env=build_environment, check=True,
                    capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )
            self.assertTrue(built_auditor.is_file(), "the real coherence auditor must be built for this hook test")
            shutil.copy2(built_auditor, auditor)
            self.assertFalse((lane / "repos" / "demo" / ".git").exists())
            # Shims log every interpreter launch, so the run shows how often
            # the hook probes for one and which gates it ran.
            shims = root / "shims"
            launches_log = root / "interpreter.log"
            install_interpreter_shims(shims, launches_log)
            trace = root / "push.trace.json"
            push_environment = dict(environment, GIT_TRACE2_EVENT=str(trace))
            push_environment.pop("PYTHON", None)
            push_environment["PATH"] = f"{shims}{os.pathsep}{environment['PATH']}"
            pre_push = subprocess.run(
                ["bash", str(worktree / ".githooks" / "pre-push")],
                cwd=lane, env=push_environment, input="", capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(pre_push.returncode, 0, pre_push.stdout + pre_push.stderr)
            self.assertNotIn("building it now", pre_push.stderr)
            self.assertFalse((lane / "target" / "release").exists())
            # Each process costs seconds on a loaded Windows host: the hook
            # probes for an interpreter once, lists the gate scripts the tip
            # carries in one git process, and still runs all three gates.
            launches = launches_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(launches.count("-c import sys"), 1, launches)
            self.assertEqual(sum(launch.startswith("- check --root") for launch in launches), 3, launches)
            processes = git_processes(trace)
            self.assertEqual(
                sum("--batch-check=%(objecttype) %(rest)" in argv for argv in processes), 1, processes,
            )
            self.assertEqual(
                [argv for argv in processes if "-e" in argv and any(":scripts/" in arg for arg in argv)],
                [], processes,
            )

            # A pushed tip that predates the gate scripts has nothing to run:
            # the hook still probes once but launches no gate.
            def plumbing(*arguments: str, index: Path) -> str:
                return subprocess.run(
                    ["git", "-C", str(lane), "-c", "user.name=Test",
                     "-c", "user.email=test@example.invalid", *arguments],
                    env=dict(environment, GIT_INDEX_FILE=str(index)),
                    check=True, capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                ).stdout.strip()

            gate_scripts = (
                "scripts/atlas-artifact-budget.py",
                "scripts/atlas-secret-scan.py",
                "scripts/atlas-refspec-guard.py",
            )
            index = root / "bare.index"
            plumbing("read-tree", "HEAD", index=index)
            plumbing("update-index", "--force-remove", *gate_scripts, index=index)
            bare_tree = plumbing("write-tree", index=index)
            head = plumbing("rev-parse", "HEAD", index=index)
            bare_tip = plumbing("commit-tree", bare_tree, "-p", head, "-m", "Drop the gate scripts", index=index)
            self.assertEqual(
                plumbing("ls-tree", "--name-only", bare_tip, "scripts/atlas-secret-scan.py", index=index), "",
            )
            launches_log.unlink()
            trace = root / "bare.trace.json"
            push_environment["GIT_TRACE2_EVENT"] = str(trace)
            bare_push = subprocess.run(
                ["bash", str(worktree / ".githooks" / "pre-push")],
                cwd=lane, env=push_environment, capture_output=True,
                # Bytes, so Windows text mode cannot end each ref update in a
                # carriage return that git's own protocol lacks.
                input=f"refs/heads/bare {bare_tip} refs/heads/bare {head}\n".encode("utf-8"),
                timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(
                bare_push.returncode, 0, (bare_push.stdout + bare_push.stderr).decode("utf-8", "replace"),
            )
            self.assertEqual(launches_log.read_text(encoding="utf-8").splitlines(), ["-c import sys"])
            self.assertEqual(
                sum("--batch-check=%(objecttype) %(rest)" in argv for argv in git_processes(trace)), 1,
            )

    def _separate_git_dir_lane(self, root: Path) -> tuple[Path, Path, dict[str, str]]:
        """A canonical worktree whose `.git` file points at its metadata, and a lane of it.

        Returns the canonical worktree, the lane and an environment free of
        `GIT_*` variables. The metadata sits beside the worktree's parent, so
        only a scan of ancestor directories can name the canonical worktree
        from the lane.
        """
        worktree = root / "checkouts" / "canonical"
        metadata = root / "metadata" / "repo.git"
        metadata.parent.mkdir()
        worktree.parent.mkdir()
        environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

        def git(path: Path, *arguments: str) -> None:
            subprocess.run(
                ["git", "-C", str(path), "-c", "user.name=Test",
                 "-c", "user.email=test@example.invalid", *arguments],
                env=environment, check=True, capture_output=True, text=True,
                timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )

        subprocess.run(
            ["git", "init", "-q", "-b", "main", "--separate-git-dir", str(metadata), str(worktree)],
            env=environment, check=True, capture_output=True, text=True,
            timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
        )
        install_hook(worktree)
        git(worktree, "add", ".githooks", "scripts")
        git(worktree, "commit", "-qm", "root")
        lane = root / "lane"
        git(worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
        return worktree, lane, environment

    def test_unreadable_canonical_worktree_is_reported_without_git_noise(self) -> None:
        """A `core.worktree` naming a missing directory fails quietly, as before."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worktree, lane, environment = self._separate_git_dir_lane(root)
            subprocess.run(
                ["git", "--git-dir", str(root / "metadata" / "repo.git"), "config", "core.worktree",
                 str(root / "gone")],
                env=environment, check=True, capture_output=True, text=True,
                timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            (lane / "repos" / "demo").mkdir(parents=True)
            subprocess.run(
                ["git", "-C", str(lane), "update-index", "--add", "--cacheinfo",
                 f"160000,{'1' * 40},repos/demo"],
                env=environment, check=True, capture_output=True, text=True,
                timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            result = subprocess.run(
                ["bash", str(lane / ".githooks" / "pre-commit")],
                cwd=lane, env=environment, capture_output=True, text=True,
                timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("canonical member checkout is absent", result.stderr)
            self.assertNotIn("fatal:", result.stdout + result.stderr)

    def test_gate_script_listing_treats_only_a_missing_object_as_absent(self) -> None:
        """A script path holding a tree still runs its gate, which then fails as before."""
        hook = PRE_PUSH.read_text(encoding="utf-8")
        listing = re.search(r'(?ms)^tip_scripts=""\n.*?^tip_has_script\(\) \{\n.*?^\}\n', hook)
        self.assertIsNotNone(listing, "the gate script listing is missing from .githooks/pre-push")
        scripts = (
            "scripts/atlas-artifact-budget.py",
            "scripts/atlas-secret-scan.py",
            "scripts/atlas-refspec-guard.py",
        )
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

            def git(*arguments: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(repo), "-c", "user.name=Test",
                     "-c", "user.email=test@example.invalid", *arguments],
                    env=environment, check=True, capture_output=True, text=True,
                    timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                ).stdout.strip()

            def commit(message: str, layout: dict[str, str]) -> str:
                for path in git("ls-files").splitlines():
                    git("rm", "-q", "-r", "-f", "--", path)
                for path, text in layout.items():
                    (repo / path).parent.mkdir(parents=True, exist_ok=True)
                    (repo / path).write_text(text, encoding="utf-8")
                git("add", "--all")
                git("commit", "-q", "--allow-empty", "-m", message)
                return git("rev-parse", "HEAD")

            git("init", "-q", "-b", "main")
            git("config", "core.autocrlf", "false")
            complete = commit("complete", {path: "print()\n" for path in scripts})
            # The secret scan's path is a directory, the budget script is gone.
            shadowed = commit("shadowed", {
                scripts[1] + "/inner.py": "print()\n",
                scripts[2]: "print()\n",
            })
            driver = (
                'atlas_root="$1"\n' + listing.group(0)
                + 'list_gate_scripts "$2" || exit 7\n'
                + f'for script in {" ".join(scripts)}; do\n'
                + '    if tip_has_script "$script"; then echo "present $script"; else echo "absent $script"; fi\n'
                + 'done\n'
            )

            def verdicts(root: Path, tip: str) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["bash", "-c", driver, "listing", str(root), tip],
                    env=environment, capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            result = verdicts(repo, complete)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [f"present {script}" for script in scripts])
            result = verdicts(repo, shadowed)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.splitlines(),
                [f"absent {scripts[0]}", f"present {scripts[1]}", f"present {scripts[2]}"],
            )
            # A listing that cannot run judges nothing: the hook blocks.
            result = verdicts(repo / "missing", complete)
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            self.assertIn("could not list the gate scripts", result.stderr)

    def test_a_failing_gate_script_listing_blocks_the_push(self) -> None:
        """The hook's own dispatch runs no gate for a tip whose listing fails.

        The dispatch is the hook's `case "$status"` block, extracted whole,
        with the four gates replaced by stubs that log their calls, so the
        listing, the `|| exit 1` after it and the order of the gates are the
        hook's own.
        """
        hook = PRE_PUSH.read_text(encoding="utf-8")
        listing = re.search(r'(?ms)^tip_scripts=""\n.*?^tip_has_script\(\) \{\n.*?^\}\n', hook)
        self.assertIsNotNone(listing, "the gate script listing is missing from .githooks/pre-push")
        dispatch = re.search(r'(?ms)^case "\$status" in\n.*?^esac\n', hook)
        self.assertIsNotNone(dispatch, 'the `case "$status"` dispatch is missing from .githooks/pre-push')
        gates = ("debt_gate", "budget_gate", "secret_gate", "refspec_gate")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)

            def git(*arguments: str) -> str:
                return subprocess.run(
                    ["git", "-C", str(repo), "-c", "user.name=Test",
                     "-c", "user.email=test@example.invalid", *arguments],
                    env=environment, check=True, capture_output=True, text=True,
                    timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                ).stdout.strip()

            git("init", "-q", "-b", "main")
            git("commit", "--allow-empty", "-qm", "root")
            tip = git("rev-parse", "HEAD")
            calls = root / "gates.log"
            driver = root / "dispatch.sh"
            driver.write_bytes((
                'atlas_root="$1"\nstatus=0\npushed_tips=("$2")\npushed_bases=("$2")\n'
                'gate_base_for() { echo "$2"; }\n'
                + "".join(f'{gate}() {{ echo "{gate}" >> "{calls.as_posix()}"; }}\n' for gate in gates)
                + listing.group(0) + dispatch.group(0)
            ).encode("utf-8"))

            def dispatch_push(atlas_root: Path) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["bash", str(driver), str(atlas_root), tip],
                    env=environment, capture_output=True, text=True,
                    timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            # Control: a listing that runs lets the four gates run in order.
            result = dispatch_push(repo)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(calls.read_text(encoding="utf-8").splitlines(), list(gates))
            calls.unlink()

            result = dispatch_push(root / "missing")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("could not list the gate scripts", result.stderr)
            self.assertFalse(calls.exists(), "a gate ran for a tip whose gate scripts could not be listed")

    def test_merge_allows_inherited_board_and_gitlink_changes_only(self) -> None:
        """A real merge may combine independently valid board and pin commits."""
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "atlas"
            member = repo / "repos" / "demo"
            repo.mkdir()
            environment = {
                key: value for key, value in os.environ.items()
                if not key.startswith("GIT_")
            }
            environment.update(
                GIT_CONFIG_NOSYSTEM="1",
                GIT_CONFIG_GLOBAL=str(repo / "gitconfig"),
            )
            (repo / "gitconfig").write_text("", encoding="utf-8")

            def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
                return subprocess.run(
                    [
                        "git", "-C", str(repo), "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", *arguments,
                    ],
                    env=environment, check=check, capture_output=True,
                    text=True, encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            git("init", "-q", "-b", "main")
            git("config", "core.autocrlf", "false")
            member.mkdir(parents=True)
            git("-C", str(member), "init", "-q", "-b", "main")
            (member / "value.txt").write_text("first\n", encoding="utf-8")
            git("-C", str(member), "add", "value.txt")
            git("-C", str(member), "commit", "-qm", "first")
            first = git("-C", str(member), "rev-parse", "HEAD").stdout.strip()
            git("-C", str(member), "update-ref", "refs/remotes/origin/main", first)
            git("-C", str(member), "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

            install_hook(repo)
            (repo / ".gitmodules").write_text(
                '[submodule "repos/demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n',
                encoding="utf-8",
            )
            (repo / "backlog.md").write_text("base\n", encoding="utf-8")
            git("add", ".githooks", "scripts", ".gitmodules", "backlog.md")
            git("update-index", "--add", "--cacheinfo", f"160000,{first},repos/demo")
            git("commit", "-qm", "Record demo")

            git("switch", "-qc", "fix/pin")
            (member / "value.txt").write_text("second\n", encoding="utf-8")
            git("-C", str(member), "add", "value.txt")
            git("-C", str(member), "commit", "-qm", "second")
            second = git("-C", str(member), "rev-parse", "HEAD").stdout.strip()
            git("-C", str(member), "update-ref", "refs/remotes/origin/main", second)
            git("update-index", "--cacheinfo", f"160000,{second},repos/demo")
            self.assertEqual(git("commit", "-qm", "Advance demo").returncode, 0)

            git("switch", "-q", "main")
            git("config", "core.hooksPath", ".githooks")
            (repo / "backlog.md").write_text("main\n", encoding="utf-8")
            git("add", "backlog.md")
            self.assertEqual(git("commit", "-qm", "Update board").returncode, 0)
            conflict = git("merge", "--no-commit", "fix/pin", check=False)
            self.assertEqual(conflict.returncode, 0, conflict.stdout + conflict.stderr)
            stack_script = repo / "scripts" / "atlas_stack.py"
            stack_script.write_text(stack_script.read_text(encoding="utf-8") + "\n# peer edit\n", encoding="utf-8")
            unstaged = git("commit", "-qm", "Reject unstaged merge content", check=False)
            self.assertNotEqual(unstaged.returncode, 0)
            self.assertIn("unstaged tracked content", unstaged.stdout + unstaged.stderr)
            # Restore through git, not write_text: on Windows write_text writes CRLF,
            # which leaves the file dirty and refuses the next commit for the
            # wrong reason.
            git("restore", "--source=HEAD", "--worktree", "--", "scripts/atlas_stack.py")
            self.assertEqual(git("status", "--porcelain", "--", "scripts/atlas_stack.py").stdout, "")
            (repo / "unrelated.txt").write_text("new\n", encoding="utf-8")
            git("add", "unrelated.txt")
            unrelated = git("commit", "-qm", "Reject unrelated merge content", check=False)
            self.assertNotEqual(unrelated.returncode, 0)
            self.assertRegex(unrelated.stdout + unrelated.stderr, r"R[23]")
            git("update-index", "--force-remove", "unrelated.txt")
            (repo / "unrelated.txt").unlink()
            merged = git("commit", "-qm", "Merge pin", check=False)
            self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)

            (member / "value.txt").write_text("third\n", encoding="utf-8")
            git("-C", str(member), "add", "value.txt")
            git("-C", str(member), "commit", "-qm", "third")
            third = git("-C", str(member), "rev-parse", "HEAD").stdout.strip()
            git("-C", str(member), "update-ref", "refs/remotes/origin/main", third)
            (repo / "backlog.md").write_text("ordinary\n", encoding="utf-8")
            git("add", "backlog.md")
            git("update-index", "--cacheinfo", f"160000,{third},repos/demo")
            ordinary = git("commit", "-qm", "Mix board and pin", check=False)
            self.assertNotEqual(ordinary.returncode, 0)
            self.assertIn("R2", ordinary.stdout + ordinary.stderr)

    def test_pre_push_runs_the_pin_advance_debt_gate(self) -> None:
        text = PRE_PUSH.read_text(encoding="utf-8")
        self.assertIn("debt_gate()", text)
        # Both gates judge each pushed tip, never HEAD (a peer's branch in a
        # shared tree), so the guarded form carries the tip argument.
        self.assertIn('debt_gate "$tip" || exit 1', text)
        self.assertIn('budget_gate "$tip" || exit 1', text)
        self.assertIn('secret_gate "$tip" || exit 1', text)

    def _debt_gate_stack(self, temporary: str) -> tuple[Path, dict[str, str], str, str]:
        """An atlas repository whose checkout and origin disagree on the checker.

        origin/main's checker records `origin` and exits with the status in
        `CHECKER_STATUS`; the checkout's copy records `checkout` and fails.
        Returns the repository, its environment, the base and the pushed tip,
        which advances the one member's gitlink.
        """
        repo = Path(temporary) / "atlas"
        member = repo / "repos" / "demo"
        member.mkdir(parents=True)
        environment = {
            key: value for key, value in os.environ.items() if not key.startswith("GIT_")
        }
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(Path(temporary) / "gitconfig"))
        (Path(temporary) / "gitconfig").write_text("", encoding="utf-8")

        def git(path: Path, *arguments: str) -> str:
            return subprocess.run(
                ["git", "-C", str(path), "-c", "user.name=Test",
                 "-c", "user.email=test@example.invalid", *arguments],
                env=environment, check=True, capture_output=True, text=True,
                encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            ).stdout.strip()

        git(member, "init", "-q", "-b", "main")
        commits = []
        for value in ("first", "second"):
            (member / "value.txt").write_text(value + "\n", encoding="utf-8")
            git(member, "add", "value.txt")
            git(member, "commit", "-qm", value)
            commits.append(git(member, "rev-parse", "HEAD"))

        git(repo, "init", "-q", "-b", "main")
        checker = repo / "scripts" / "atlas-conformance.py"
        checker.parent.mkdir()
        checker.write_text(
            "import os, pathlib, sys\n"
            "pathlib.Path(os.environ['CHECKER_LOG']).write_text('origin ' + ' '.join(sys.argv[1:]))\n"
            "sys.exit(int(os.environ['CHECKER_STATUS']))\n",
            encoding="utf-8",
        )
        git(repo, "add", "scripts")
        git(repo, "update-index", "--add", "--cacheinfo", f"160000,{commits[0]},repos/demo")
        git(repo, "commit", "-qm", "Record demo")
        base = git(repo, "rev-parse", "HEAD")
        git(repo, "update-ref", "refs/remotes/origin/main", base)
        git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        git(repo, "update-index", "--cacheinfo", f"160000,{commits[1]},repos/demo")
        git(repo, "commit", "-qm", "Advance demo")
        tip = git(repo, "rev-parse", "HEAD")
        # The shared checkout's copy: a peer's uncommitted checker change.
        checker.write_text(
            "import os, pathlib, sys\n"
            "pathlib.Path(os.environ['CHECKER_LOG']).write_text('checkout')\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        return repo, environment, base, tip

    def _run_debt_gate(
        self, repo: Path, environment: dict[str, str], base: str, tip: str, status: int,
    ) -> tuple[subprocess.CompletedProcess, str]:
        hook = PRE_PUSH.read_text(encoding="utf-8")
        function = re.search(r"(?ms)^debt_gate\(\) \{\n.*?^\}\n", hook)
        self.assertIsNotNone(function, "debt_gate() is missing from .githooks/pre-push")
        probe = re.search(r"(?ms)^python_bin=\"\"\n.*?^resolve_python\(\) \{\n.*?^\}\n", hook)
        self.assertIsNotNone(probe, "resolve_python() is missing from .githooks/pre-push")
        log = repo.parent / "checker.log"
        script = (
            probe.group(0)
            + function.group(0)
            + 'atlas_root="$1"; member_root="$1"; gate_base="$2"\n'
            + 'debt_gate "$3"\n'
        )
        run_environment = dict(
            environment, PYTHON=sys.executable, CHECKER_LOG=str(log),
            CHECKER_STATUS=str(status),
        )
        result = subprocess.run(
            ["bash", "-c", script, "debt_gate", repo.as_posix(), base, tip],
            env=run_environment, capture_output=True, text=True, encoding="utf-8",
            timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
        )
        return result, log.read_text(encoding="utf-8") if log.is_file() else ""

    def test_debt_gate_runs_origins_checker_not_the_checkouts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, base, tip = self._debt_gate_stack(temporary)

            passed, log = self._run_debt_gate(repo, environment, base, tip, 0)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertTrue(log.startswith("origin check --repo demo"), log)

            failed, log = self._run_debt_gate(repo, environment, base, tip, 1)
            self.assertEqual(failed.returncode, 1, failed.stderr)
            self.assertTrue(log.startswith("origin "), log)
            self.assertIn("advancing demo raises a debt class", failed.stderr)
            git_dir = repo / ".git"
            self.assertEqual(list(git_dir.glob("atlas-debt-checker.*")), [],
                             "the extracted checker outlives the run")

    def test_debt_gate_skips_a_pin_the_default_branch_records(self) -> None:
        # A branch merging main in carries main's own pin advance; main's
        # ratchet measured it, so the gate does not measure it again against
        # the branch's older baseline.
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, base, tip = self._debt_gate_stack(temporary)
            subprocess.run(
                ["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", tip],
                env=environment, check=True, capture_output=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )

            result, log = self._run_debt_gate(repo, environment, base, tip, 1)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log, "", "a pin the default branch records was measured again")

    def test_debt_gate_without_an_origin_default_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, base, tip = self._debt_gate_stack(temporary)
            for ref in ("refs/remotes/origin/HEAD", "refs/remotes/origin/main"):
                subprocess.run(
                    ["git", "-C", str(repo), "update-ref", "--no-deref", "-d", ref],
                    env=environment, check=True, capture_output=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            result, log = self._run_debt_gate(repo, environment, base, tip, 0)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(log, "", "a checker ran with no origin default")
            self.assertIn("origin names no default branch", result.stderr)

    def test_pre_commit_cites_the_detector_parity_rationale(self) -> None:
        text = PRE_COMMIT.read_text(encoding="utf-8")
        self.assertIn("docs/mdbook/detector-parity.md", text)
        self.assertNotIn("MDBOOK_DETECTOR_PARITY.md", text)


if __name__ == "__main__":
    unittest.main()
