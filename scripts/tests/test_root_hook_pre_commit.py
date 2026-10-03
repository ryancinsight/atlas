"""Pin what `.githooks/pre-commit` refuses and allows."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from root_hook_support import (
    PRE_COMMIT, ROOT, advance_demo_member, demo_member, fixture_environment, git_runner,
    init_superproject, install_hook, record_demo_member, repo_git_runner, set_gitlink,
)


class RootHookGuardTests(unittest.TestCase):
    def test_provider_config_change_runs_without_book_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            git = repo_git_runner(repo)

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
                environment = fixture_environment()
                git = repo_git_runner(repo, environment)

                init_superproject(environment, repo)
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
            environment = fixture_environment()
            git = git_runner(environment)
            commits = demo_member(environment, member, "first", "second")

            init_superproject(environment, repo)
            for version in ("old\n", "current\n"):
                (repo / "a.txt").write_text(version, encoding="utf-8")
                git(repo, "add", "a.txt")
                git(repo, "commit", "-qm", version.strip())
            record_demo_member(environment, repo, commits[0])
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

    def test_merge_allows_inherited_board_and_gitlink_changes_only(self) -> None:
        """A real merge may combine independently valid board and pin commits."""
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "atlas"
            member = repo / "repos" / "demo"
            environment = fixture_environment()
            git = repo_git_runner(repo, environment)

            init_superproject(environment, repo)
            first = demo_member(environment, member, "first")[0]
            (repo / "backlog.md").write_text("base\n", encoding="utf-8")
            record_demo_member(environment, repo, first, "backlog.md")

            git("switch", "-qc", "fix/pin")
            set_gitlink(environment, repo, advance_demo_member(environment, member, "second"))
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

            third = advance_demo_member(environment, member, "third")
            (repo / "backlog.md").write_text("ordinary\n", encoding="utf-8")
            git("add", "backlog.md")
            set_gitlink(environment, repo, third)
            ordinary = git("commit", "-qm", "Mix board and pin", check=False)
            self.assertNotEqual(ordinary.returncode, 0)
            self.assertIn("R2", ordinary.stdout + ordinary.stderr)

    def test_pre_commit_cites_the_detector_parity_rationale(self) -> None:
        text = PRE_COMMIT.read_text(encoding="utf-8")
        self.assertIn("docs/mdbook/detector-parity.md", text)
        self.assertNotIn("MDBOOK_DETECTOR_PARITY.md", text)


if __name__ == "__main__":
    unittest.main()
