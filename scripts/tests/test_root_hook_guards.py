"""Pin the root hook guards against silent removal.

`.githooks/pre-push` carries the pin-advance debt gate beside the coherence
report, and `.githooks/pre-commit` references the detector-parity rationale
that justifies its strict dead-link gate. Both were once dropped from the
working tree without a board item; these cases fail on that state.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
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
        "atlas_stale_side_basis.py", "atlas_git_process.py", "process_tree.py",
        "windows_process.py",
        "stale-side-waivers.json",
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
                cwd=lane, env=environment, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(pre_commit.returncode, 0, pre_commit.stdout + pre_commit.stderr)

            commit = subprocess.run(
                ["git", "-C", str(lane), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "advance"],
                env=environment, capture_output=True, text=True, timeout=30,
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
                    capture_output=True, text=True, timeout=180,
                )
            self.assertTrue(built_auditor.is_file(), "the real coherence auditor must be built for this hook test")
            shutil.copy2(built_auditor, auditor)
            self.assertFalse((lane / "repos" / "demo" / ".git").exists())
            pre_push = subprocess.run(
                ["bash", str(worktree / ".githooks" / "pre-push")],
                cwd=lane, env=environment, input="", capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(pre_push.returncode, 0, pre_push.stdout + pre_push.stderr)
            self.assertNotIn("building it now", pre_push.stderr)
            self.assertFalse((lane / "target" / "release").exists())

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
                encoding="utf-8", timeout=30,
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
        function = re.search(r"(?ms)^debt_gate\(\) \{\n.*?^\}\n", PRE_PUSH.read_text(encoding="utf-8"))
        self.assertIsNotNone(function, "debt_gate() is missing from .githooks/pre-push")
        log = repo.parent / "checker.log"
        script = (
            function.group(0)
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
            timeout=60,
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

    def test_debt_gate_refuses_an_invalid_comparison_range(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, _, tip = self._debt_gate_stack(temporary)
            invalid_base = "not-a-revision"

            result, log = self._run_debt_gate(
                repo, environment, invalid_base, tip, 0,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(log, "", "the checker ran after the diff failed")
            self.assertIn("could not compare pushed tip", result.stderr)
            self.assertIn(invalid_base, result.stderr)

    def test_debt_gate_skips_a_pin_the_default_branch_records(self) -> None:
        # A branch merging main in carries main's own pin advance; main's
        # ratchet measured it, so the gate does not measure it again against
        # the branch's older baseline.
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, base, tip = self._debt_gate_stack(temporary)
            subprocess.run(
                ["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", tip],
                env=environment, check=True, capture_output=True, timeout=30,
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
                    env=environment, check=True, capture_output=True, timeout=30,
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
