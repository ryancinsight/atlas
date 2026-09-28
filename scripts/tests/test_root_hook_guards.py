"""Pin the root hook guards against silent removal.

`.githooks/pre-push` carries the pin-advance debt gate beside the coherence
report, and `.githooks/pre-commit` references the detector-parity rationale
that justifies its strict dead-link gate. Both were once dropped from the
working tree without a board item; these cases fail on that state.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRE_PUSH = ROOT / ".githooks" / "pre-push"
PRE_COMMIT = ROOT / ".githooks" / "pre-commit"


def install_hook(repo: Path) -> None:
    (repo / "scripts").mkdir()
    for name in (
        "atlas-stale-side-guard.py", "atlas_stale_side_git.py",
        "atlas_stale_side_basis.py", "atlas_git_process.py", "stale-side-waivers.json",
        "atlas-provider-integration-audit.py", "atlas_stack.py", "check_mdbook_links.py",
    ):
        shutil.copyfile(ROOT / "scripts" / name, repo / "scripts" / name)
    (repo / ".githooks").mkdir()
    shutil.copyfile(PRE_COMMIT, repo / ".githooks" / "pre-commit")
    (repo / ".githooks" / "pre-commit").chmod(0o755)


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
                    text=True, encoding="utf-8", timeout=30,
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
                        text=True, encoding="utf-8", timeout=30,
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
                    text=True, encoding="utf-8", timeout=30,
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
            result = git(lane, "commit", "-qm", "Advance demo", check=False)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
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

    def test_separate_git_dir_resolves_the_configured_worktree_root(self) -> None:
        """Canonical discovery follows Git's separate worktree metadata."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worktree = root / "canonical"
            metadata = root / "metadata.git"
            subprocess.run(
                ["git", "init", "-q", "-b", "main", "--separate-git-dir", str(metadata), str(worktree)],
                check=True, capture_output=True, text=True,
            )
            common = subprocess.run(
                ["git", "-C", str(worktree), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            resolved = subprocess.run(
                ["git", "-C", str(worktree), "rev-parse", "--show-toplevel"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            self.assertEqual(Path(resolved).resolve(), worktree.resolve())

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
                    text=True, encoding="utf-8", timeout=30,
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

    def test_pre_commit_cites_the_detector_parity_rationale(self) -> None:
        text = PRE_COMMIT.read_text(encoding="utf-8")
        self.assertIn("docs/mdbook/detector-parity.md", text)
        self.assertNotIn("MDBOOK_DETECTOR_PARITY.md", text)


if __name__ == "__main__":
    unittest.main()
