#!/usr/bin/env python3
"""`lockfile.py --regenerate` repairs a flattened lock and advances no pin.

Run against real cargo and real git repositories: two provider crates served
from `file://` repositories, a consumer locking both at their first commit, and
a lock flattened the way the overlay flattens one (one source dropped, residue
appended) after one provider has moved on. Repair has to restore the dropped
source and discard the residue while leaving the other provider at the revision
the lock pinned; `cargo generate-lockfile`, which re-resolves everything, moves
it to the new tip. Nothing needs a registry or a network.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "lockfile.py"
IDENT = ["-c", "user.name=t", "-c", "user.email=t@example.invalid"]


def git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *IDENT, *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def provider(root: Path, name: str) -> Path:
    """A one-crate git repository, committed once."""
    repository = root / name
    (repository / "src").mkdir(parents=True)
    (repository / "Cargo.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2021"\n',
        encoding="utf-8",
        newline="\n",
    )
    (repository / "src" / "lib.rs").write_text("pub fn first() {}\n", encoding="utf-8", newline="\n")
    git(repository, "init", "-q", "-b", "main")
    git(repository, "add", "-A")
    git(repository, "commit", "-q", "-m", "first")
    return repository


def sources(lock_text: str) -> dict[str, str | None]:
    return {
        package["name"]: package.get("source")
        for package in tomllib.loads(lock_text)["package"]
    }


@unittest.skipUnless(shutil.which("cargo") and shutil.which("git"), "needs cargo and git")
class RegenerateAdvancesNoPinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="atlas-lock-regenerate-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.environment = {**os.environ, "CARGO_HOME": str(self.root / "cargo-home")}
        self.environment.pop("CARGO_TARGET_DIR", None)
        self.stable = provider(self.root, "stable")
        self.moving = provider(self.root, "moving")
        self.consumer = self.root / "consumer"
        (self.consumer / "src").mkdir(parents=True)
        (self.consumer / "src" / "lib.rs").write_text("", encoding="utf-8", newline="\n")
        (self.consumer / "Cargo.toml").write_text(
            '[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2021"\n\n'
            "[dependencies]\n"
            f'stable = {{ git = "{self.stable.as_uri()}" }}\n'
            f'moving = {{ git = "{self.moving.as_uri()}" }}\n',
            encoding="utf-8",
            newline="\n",
        )
        self.cargo("generate-lockfile")
        self.pinned = git(self.moving, "rev-parse", "HEAD")
        (self.moving / "src" / "lib.rs").write_text(
            "pub fn first() {}\npub fn second() {}\n", encoding="utf-8", newline="\n"
        )
        git(self.moving, "commit", "-q", "-am", "second")
        self.tip = git(self.moving, "rev-parse", "HEAD")

    def cargo(self, *arguments: str) -> None:
        subprocess.run(
            ["cargo", *arguments, "--manifest-path", str(self.consumer / "Cargo.toml")],
            cwd=self.root,
            env=self.environment,
            check=True,
            capture_output=True,
        )

    def flatten(self) -> None:
        """Drop one provider's source and append residue, as the overlay does."""
        lock = self.consumer / "Cargo.lock"
        text = lock.read_text(encoding="utf-8")
        kept = []
        in_stable = False
        for line in text.splitlines():
            if line.startswith("name = "):
                in_stable = line == 'name = "stable"'
            if in_stable and line.startswith("source = "):
                continue
            kept.append(line)
        lock.write_text(
            "\n".join(kept) + '\n\n[[patch.unused]]\nname = "stable"\nversion = "0.1.0"\n',
            encoding="utf-8",
            newline="\n",
        )

    def run_script(self, mode: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), mode, "--manifest-path", str(self.consumer / "Cargo.toml")],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_the_fixture_is_flattened_before_it_is_repaired(self) -> None:
        self.flatten()
        completed = self.run_script("--check")
        self.assertEqual(completed.returncode, 1, completed.stdout)
        self.assertIn("`stable` locked without a git source", completed.stderr)
        self.assertIn("overlay residue", completed.stderr)

    def test_a_flattened_lock_is_repaired_and_the_other_pin_stays(self) -> None:
        self.flatten()
        completed = self.run_script("--regenerate")
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        text = (self.consumer / "Cargo.lock").read_text(encoding="utf-8")
        locked = sources(text)
        self.assertTrue(locked["stable"] and locked["stable"].startswith("git+"), locked)
        self.assertNotIn("[[patch.unused]]", text)
        self.assertTrue(locked["moving"].endswith("#" + self.pinned), locked["moving"])
        self.assertFalse(locked["moving"].endswith("#" + self.tip), "the pin advanced")


if __name__ == "__main__":
    unittest.main()
