"""Pin both root hooks in linked lanes and separate-git-dir layouts."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from root_hook_support import (
    FIXTURE_PROCESS_TIMEOUT_SECONDS, GATE_SCRIPTS, PRE_PUSH, ROOT, advance_demo_member,
    build_coherence_auditor, fixture_environment, git, git_processes, git_runner, init_demo_member, init_superproject,
    publish_as_origin_default, record_demo_member, record_launches, separate_git_dir_lane,
    set_gitlink, stage_demo_gitlink,
)

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


class RootHookGuardTests(unittest.TestCase):
    def test_linked_lane_uses_the_canonical_member_checkout_for_gitlinks(self) -> None:
        """An uninitialized lane must validate its staged gitlink from main."""
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "atlas"
            member = repo / "repos" / "demo"
            lane = Path(temporary) / "lane"
            environment = fixture_environment()
            git = git_runner(environment)

            init_superproject(environment, repo)
            init_demo_member(environment, member)
            book = member / "docs" / "book"
            book.mkdir(parents=True)
            (book / "SUMMARY.md").write_text(
                "# Summary\n\n[Chapter](chapter.md)\n", encoding="utf-8",
            )
            (book / "chapter.md").write_text("# Chapter\n", encoding="utf-8")
            first = advance_demo_member(environment, member, "first")

            record_demo_member(environment, repo, first)
            git(repo, "config", "core.hooksPath", ".githooks")
            git(repo, "worktree", "add", "-q", "-b", "fix/lane", str(lane))
            (lane / "repos" / "demo").mkdir(parents=True, exist_ok=True)

            second = advance_demo_member(environment, member, "second")
            set_gitlink(environment, lane, second)
            recorded, launches_log, trace = record_launches(environment, Path(temporary), "advance")
            result = git_runner(recorded)(lane, "commit", "-qm", "Advance demo", check=False)

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

            third = advance_demo_member(environment, member, "third")
            member.rename(member.with_name("demo.missing"))
            set_gitlink(environment, lane, third)
            missing_member = git(lane, "commit", "-qm", "Reject missing member", check=False)
            self.assertNotEqual(missing_member.returncode, 0)
            self.assertIn("canonical member checkout is absent", missing_member.stdout + missing_member.stderr)

    def test_separate_git_dir_resolves_the_canonical_worktree_root(self) -> None:
        """Both hooks follow Git metadata in a nested separate-dir layout."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def add_member_and_tooling(worktree: Path, environment: dict[str, str]) -> None:
                shutil.copytree(ROOT / "scripts", worktree / "scripts", dirs_exist_ok=True)
                shutil.copyfile(PRE_PUSH, worktree / ".githooks" / "pre-push")
                (worktree / ".githooks" / "pre-push").chmod(0o755)
                shutil.copytree(
                    ROOT / "tools" / "gitlink-coherence", worktree / "tools" / "gitlink-coherence",
                    ignore=shutil.ignore_patterns("target"),
                )
                member = worktree / "repos" / "demo"
                init_demo_member(environment, member)
                first = advance_demo_member(environment, member, "first")
                git(environment, worktree, "add", "tools")
                stage_demo_gitlink(environment, worktree, first)

            worktree, lane, environment = separate_git_dir_lane(root, add_member_and_tooling)
            member = worktree / "repos" / "demo"
            git(environment, worktree, "config", "core.hooksPath", ".githooks")
            common = git(environment, lane, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
            self.assertTrue(common.endswith("repo.git"))
            configured = git(environment, lane, "--git-dir", common, "config", "--get", "core.worktree", check=False)
            self.assertEqual(configured.stdout, "")

            set_gitlink(environment, lane, advance_demo_member(environment, member, "second"))
            self.assertIn("repos/demo", git(environment, lane, "diff", "--cached", "--name-only").stdout)

            environment = dict(environment, _ATLAS_HOOK_TRAMPOLINE_DEFERRED="1")
            pre_commit = subprocess.run(
                ["bash", str(lane / ".githooks" / "pre-commit")],
                cwd=lane, env=environment, capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(pre_commit.returncode, 0, pre_commit.stdout + pre_commit.stderr)

            commit = git(environment, lane, "commit", "-qm", "advance", check=False)
            self.assertEqual(commit.returncode, 0, commit.stdout + commit.stderr)

            publish_as_origin_default(environment, lane, "HEAD")
            # The hook runs the auditor built from origin's
            # tools/gitlink-coherence, cached under the git directory by that
            # tree; nothing is placed in target/release, which it no longer reads.
            auditor_tree = git(environment, lane, "rev-parse", "origin/main:tools/gitlink-coherence").stdout.strip()
            auditor_name = "gitlink-coherence.exe" if os.name == "nt" else "gitlink-coherence"
            auditor = Path(common) / "atlas-auditor" / auditor_tree / auditor_name
            auditor.parent.mkdir(parents=True)
            built_auditor = build_coherence_auditor()
            self.assertTrue(built_auditor.is_file(), "the real coherence auditor must be built for this hook test")
            shutil.copy2(built_auditor, auditor)
            self.assertFalse((lane / "repos" / "demo" / ".git").exists())
            # The shims log every interpreter launch, so the run shows how
            # often the hook probes for one and which gates it ran.
            push_environment, launches_log, trace = record_launches(environment, root, "push")
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
            plumbing = git_runner(dict(environment, GIT_INDEX_FILE=str(root / "bare.index")))
            plumbing(lane, "read-tree", "HEAD")
            plumbing(lane, "update-index", "--force-remove", *GATE_SCRIPTS)
            bare_tree = plumbing(lane, "write-tree").stdout.strip()
            head = plumbing(lane, "rev-parse", "HEAD").stdout.strip()
            bare_tip = plumbing(
                lane, "commit-tree", bare_tree, "-p", head, "-m", "Drop the gate scripts",
            ).stdout.strip()
            self.assertEqual(
                plumbing(lane, "ls-tree", "--name-only", bare_tip, GATE_SCRIPTS[1]).stdout, "",
            )
            bare_environment, launches_log, trace = record_launches(environment, root, "bare")
            bare_push = subprocess.run(
                ["bash", str(worktree / ".githooks" / "pre-push")],
                cwd=lane, env=bare_environment, capture_output=True,
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

    def test_unreadable_canonical_worktree_is_reported_without_git_noise(self) -> None:
        """A `core.worktree` naming a missing directory fails quietly, as before."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worktree, lane, environment = separate_git_dir_lane(root)
            git(
                environment, lane, "--git-dir", str(root / "metadata" / "repo.git"),
                "config", "core.worktree", str(root / "gone"),
            )
            (lane / "repos" / "demo").mkdir(parents=True)
            set_gitlink(environment, lane, "1" * 40)
            result = subprocess.run(
                ["bash", str(lane / ".githooks" / "pre-commit")],
                cwd=lane, env=environment, capture_output=True, text=True,
                timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("canonical member checkout is absent", result.stderr)
            self.assertNotIn("fatal:", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
