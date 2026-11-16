"""Exports of a revision are stamped with the time they are made, not the commit date.

`git archive <commit>` stamps every member with the commit date. A build that
extracts an older revision into a path already built against a shared target
directory then sees sources older than the build output, and Cargo reuses the
stale artifacts. `git archive <tree>` has no date to inherit, and the helper
restamps each extracted file at nanosecond precision, because tar member times
are whole seconds and an export in the second a build finished would otherwise
read as not newer. Each exporter that feeds a build is pinned here for the
stamp: the shared helper, the locked SemVer export, and the lock sweep's member
export. The cargo case below re-exports one path after an aged build; the order
in which the locked SemVer comparison exports both sides before building either
is pinned in test_atlas_semver_locked.py, not here.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import atlas_git_process  # noqa: E402


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


semver_locked = load("atlas_semver_locked", "atlas_semver_locked.py")
lock_sweep = load("atlas_lock_sweep_mtime", "atlas-lock-sweep.py")

OLD_DATE = "2000-01-01T00:00:00+0000"
BIN = "mtimeprobe"


def git(repo: Path, *arguments: str, date: str | None = None) -> str:
    env = dict(os.environ)
    if date is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    done = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        env=env, capture_output=True, check=True, text=True,
    )
    return done.stdout.strip()


def commit_program(repo: Path, answer: int, date: str) -> str:
    """Commit a one-binary crate printing `answer`, dated `date`."""
    (repo / "src").mkdir(exist_ok=True)
    (repo / "Cargo.toml").write_text(
        f'[package]\nname = "{BIN}"\nversion = "0.0.0"\nedition = "2021"\n',
        encoding="utf-8", newline="\n",
    )
    (repo / "src" / "main.rs").write_text(
        f'fn main() {{ println!("{answer}"); }}\n', encoding="utf-8", newline="\n",
    )
    git(repo, "add", "Cargo.toml", "src/main.rs")
    git(repo, "commit", "-m", f"program {answer}", date=date)
    return git(repo, "rev-parse", "HEAD")


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Export test")
    git(repo, "config", "commit.gpgsign", "false")
    return repo


def member_mtimes(root: Path) -> list[tuple[str, float]]:
    return [
        (str(path.relative_to(root)), path.stat().st_mtime)
        for path in sorted(root.rglob("*")) if path.is_file()
    ]


def export_with_helper(repo: Path, revision: str, destination: Path) -> Path:
    destination.mkdir()
    atlas_git_process.extract_archive(
        atlas_git_process.archive(repo, revision, timeout=60), destination
    )
    return destination


def export_with_semver(repo: Path, revision: str, destination: Path) -> Path:
    semver_locked.export(repo, revision, destination, dict(os.environ))
    return destination


def export_with_sweep(repo: Path, revision: str, destination: Path) -> Path:
    destination.mkdir()
    lock_sweep.export_tree(repo, revision, destination)
    return destination / "tree"


EXPORTERS = (
    ("archive helper", export_with_helper),
    ("locked semver export", export_with_semver),
    ("lock sweep member export", export_with_sweep),
)


class ExportTimestamps(unittest.TestCase):
    def test_every_member_is_stamped_with_the_export_time(self):
        for label, exporter in EXPORTERS:
            with self.subTest(exporter=label), tempfile.TemporaryDirectory() as root:
                repo = make_repo(Path(root))
                revision = commit_program(repo, 1, OLD_DATE)
                started = int(time.time())

                exported = exporter(repo, revision, Path(root) / "export")

                stamps = member_mtimes(exported)
                self.assertEqual(
                    sorted(name.replace("\\", "/") for name, _ in stamps),
                    ["Cargo.toml", "src/main.rs"],
                )
                for name, stamp in stamps:
                    self.assertGreaterEqual(
                        stamp, started, f"{name} carries the commit date, not the export time"
                    )

    def test_export_made_right_after_a_write_is_newer_than_that_write(self):
        with tempfile.TemporaryDirectory() as root:
            repo = make_repo(Path(root))
            revision = commit_program(repo, 1, OLD_DATE)
            for label, exporter in EXPORTERS:
                marker = Path(root) / f"built-{len(label)}"
                marker.write_text("build output", encoding="utf-8")
                exported = exporter(repo, revision, Path(root) / f"export-{len(label)}")
                for path in sorted(exported.rglob("*")):
                    if path.is_file():
                        self.assertGreater(
                            path.stat().st_mtime_ns, marker.stat().st_mtime_ns,
                            f"{label}: {path.name} is not newer than the preceding write",
                        )

    def test_archive_peels_every_revision_form_to_the_same_tree(self):
        with tempfile.TemporaryDirectory() as root:
            repo = make_repo(Path(root))
            revision = commit_program(repo, 1, OLD_DATE)
            tree = git(repo, "rev-parse", f"{revision}^{{tree}}")
            contents = []
            for index, form in enumerate(("HEAD", revision, "main", tree, f"{revision}^{{tree}}")):
                destination = Path(root) / f"form{index}"
                export_with_helper(repo, form, destination)
                contents.append((destination / "src" / "main.rs").read_bytes())
            self.assertEqual(len(set(contents)), 1)
            self.assertIn(b'println!("1")', contents[0])

    def test_archive_path_selection_survives_the_tree_peel(self):
        with tempfile.TemporaryDirectory() as root:
            repo = make_repo(Path(root))
            revision = commit_program(repo, 1, OLD_DATE)
            destination = Path(root) / "export"
            destination.mkdir()
            atlas_git_process.extract_archive(
                atlas_git_process.archive(repo, revision, paths=("Cargo.toml",), timeout=60),
                destination,
            )
            self.assertEqual([path.name for path in destination.rglob("*") if path.is_file()],
                             ["Cargo.toml"])

    def test_unknown_revision_is_a_typed_error(self):
        with tempfile.TemporaryDirectory() as root:
            repo = make_repo(Path(root))
            commit_program(repo, 1, OLD_DATE)
            with self.assertRaises(atlas_git_process.GitProcessError):
                atlas_git_process.archive(repo, "no-such-revision", timeout=60)


@pytest.mark.slow
class CargoRebuildAfterExport(unittest.TestCase):
    """The failure class: a shared target built earlier, then an older-dated revision."""

    def build(self, source: Path, target: Path) -> str:
        env = dict(os.environ, CARGO_TARGET_DIR=str(target), CARGO_INCREMENTAL="0")
        env.pop("RUSTC_WRAPPER", None)
        # Cargo discovers configuration from the working directory, so run
        # beside the temporary target to stay outside the stack's patch overlay.
        subprocess.run(
            ["cargo", "build", "--offline", "--quiet",
             "--manifest-path", str(source / "Cargo.toml")],
            env=env, cwd=target.parent, capture_output=True, check=True, timeout=120,
        )
        binary = target / "debug" / (BIN + (".exe" if os.name == "nt" else ""))
        return subprocess.run(
            [str(binary)], capture_output=True, check=True, text=True, timeout=30
        ).stdout.strip()

    def age(self, target: Path) -> None:
        """Make the build output an hour old, as one left by an earlier session."""
        past = time.time() - 3600
        for path in target.rglob("*"):
            if path.is_file():
                os.utime(path, (past, past))

    def test_second_export_of_an_older_dated_revision_rebuilds(self):
        for label, exporter in EXPORTERS:
            with self.subTest(exporter=label), tempfile.TemporaryDirectory() as root:
                repo = make_repo(Path(root))
                first = commit_program(repo, 1, OLD_DATE)
                second = commit_program(repo, 2, "2000-01-02T00:00:00+0000")
                destination, target = Path(root) / "source", Path(root) / "target"

                self.assertEqual(self.build(exporter(repo, first, destination), target), "1")
                self.age(target)

                shutil.rmtree(destination)
                self.assertEqual(self.build(exporter(repo, second, destination), target), "2")


if __name__ == "__main__":
    unittest.main()
