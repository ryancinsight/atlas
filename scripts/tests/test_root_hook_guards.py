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
        "atlas-provider-integration-audit.py", "atlas_stack.py",
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

    def test_pre_push_runs_the_pin_advance_debt_gate(self) -> None:
        text = PRE_PUSH.read_text(encoding="utf-8")
        self.assertIn("debt_gate()", text)
        # Both gates judge each pushed tip, never HEAD (a peer's branch in a
        # shared tree), so the guarded form carries the tip argument.
        self.assertIn('debt_gate "$tip" || exit 1', text)
        self.assertIn('budget_gate "$tip" || exit 1', text)

    def test_pre_commit_cites_the_detector_parity_rationale(self) -> None:
        text = PRE_COMMIT.read_text(encoding="utf-8")
        self.assertIn("docs/mdbook/detector-parity.md", text)
        self.assertNotIn("MDBOOK_DETECTOR_PARITY.md", text)


if __name__ == "__main__":
    unittest.main()
