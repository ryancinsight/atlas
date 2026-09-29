#!/usr/bin/env python3
"""Executable behavior tests for the rescue pre-push exception."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts" / "git-hooks" / "rescue-push"
SCANNER = ROOT / "scripts" / "atlas-secret-scan.py"
ROOT_HOOK = ROOT / ".githooks" / "pre-push"
MEMBER_HOOK = ROOT / "scripts" / "git-hooks" / "pre-push"
ZERO = "0" * 40
IDENTITY = ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid")


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def commit(root: Path, message: str) -> str:
    git(root, *IDENTITY, "add", "-A")
    git(root, *IDENTITY, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


class RescueFixture:
    """An Atlas root and one registered member with fetched default refs."""

    def __init__(self, directory: str) -> None:
        self.stack = Path(directory) / "atlas"
        self.member = self.stack / "repos" / "demo"
        self.member.mkdir(parents=True)
        git(self.stack, "init", "-q", "-b", "main")
        for source, relative in (
            (HELPER, "scripts/git-hooks/rescue-push"),
            (SCANNER, "scripts/atlas-secret-scan.py"),
            (ROOT_HOOK, ".githooks/pre-push"),
        ):
            target = self.stack / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        self.stack_base = commit(self.stack, "trusted stack tools")
        self._trust_default(self.stack, self.stack_base)

        git(self.member, "init", "-q", "-b", "main")
        (self.member / "README.md").write_text("base\n", encoding="utf-8")
        self.member_base = commit(self.member, "member base")
        self._trust_default(self.member, self.member_base)

    @staticmethod
    def _trust_default(root: Path, revision: str) -> None:
        git(root, "update-ref", "refs/remotes/origin/main", revision)
        git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

    def rescue_tip(self, root: Path | None = None) -> str:
        repo = root or self.member
        git(repo, "switch", "-qc", "rescue/work", "main")
        (repo / "work.txt").write_text("unfinished\n", encoding="utf-8")
        return commit(repo, "rescue work")

    def run_helper(self, *updates: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash", str(HELPER), str(self.member), str(self.stack),
                self.stack_base, self.member_base, *updates,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHON": os.environ.get("PYTHON", "python")},
        )

    @staticmethod
    def run_hook(
        script: Path,
        cwd: Path,
        update: str,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        hook_environment = dict(os.environ)
        if environment is not None:
            hook_environment.update(environment)
        return subprocess.run(
            ["bash", str(script)],
            cwd=cwd,
            input=(update + "\n").encode(),
            capture_output=True,
            env=hook_environment,
        )


class RescuePushTests(unittest.TestCase):
    def test_destination_classification_accepts_every_source_shape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-rescue-") as directory:
            fixture = RescueFixture(directory)
            tip = fixture.rescue_tip()
            for source in ("HEAD", "refs/heads/wip", tip):
                with self.subTest(source=source):
                    result = fixture.run_helper(
                        f"{source} {tip} refs/heads/rescue/work {ZERO}"
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("no credential", result.stdout)

    def test_updates_mixed_pushes_and_deletions_use_the_normal_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-rescue-") as directory:
            fixture = RescueFixture(directory)
            tip = fixture.rescue_tip()
            cases = (
                (f"HEAD {tip} refs/heads/rescue/work {fixture.member_base}",),
                (f"(delete) {ZERO} refs/heads/rescue/work {fixture.member_base}",),
                (
                    f"HEAD {tip} refs/heads/rescue/work {ZERO}",
                    f"HEAD {tip} refs/heads/ordinary {ZERO}",
                ),
            )
            for updates in cases:
                with self.subTest(updates=updates):
                    self.assertEqual(fixture.run_helper(*updates).returncode, 3)

    def test_pushed_allowlist_cannot_hide_its_credential(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-rescue-") as directory:
            fixture = RescueFixture(directory)
            git(fixture.member, "switch", "-qc", "rescue/work", "main")
            value = "ci" + "o" + "A" * 32
            (fixture.member / "secret.txt").write_text(value + "\n", encoding="utf-8")
            fingerprint = hashlib.sha256(value.encode()).hexdigest()
            (fixture.member / ".secret-scan-allowlist").write_text(
                fingerprint + "\n", encoding="utf-8"
            )
            tip = commit(fixture.member, "self allowlist")
            result = fixture.run_helper(
                f"HEAD {tip} refs/heads/rescue/work {ZERO}"
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn(fingerprint[:12], result.stdout)

    def test_both_hooks_dispatch_initial_rescue_to_the_shared_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-rescue-") as directory:
            fixture = RescueFixture(directory)
            member_tip = fixture.rescue_tip()
            member = fixture.run_hook(
                MEMBER_HOOK,
                fixture.member,
                f"HEAD {member_tip} refs/heads/rescue/work {ZERO}",
                {
                    "GIT_DIR": str(fixture.member / ".git"),
                    "GIT_WORK_TREE": str(fixture.member),
                },
            )
            self.assertEqual(member.returncode, 0, member.stderr.decode())

            stack_tip = fixture.rescue_tip(fixture.stack)
            root = fixture.run_hook(
                ROOT_HOOK,
                fixture.stack,
                f"{stack_tip} {stack_tip} refs/heads/rescue/work {ZERO}",
            )
            self.assertEqual(root.returncode, 0, root.stderr.decode())


if __name__ == "__main__":
    unittest.main()
