#!/usr/bin/env python3
"""Behavioral tests for the recorded Atlas pin compile gate."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-pin-compile.py"
SPEC = importlib.util.spec_from_file_location("atlas_pin_compile", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
pin_compile = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pin_compile
SPEC.loader.exec_module(pin_compile)
from atlas_git_process import execute as execute_git

ROOT = SCRIPT.parents[1]
BROKEN_AEQUITAS = "b05c2ac7072a220450b7add288d6d6f2ae160a34"
RENAMED_EUNOMIA = "87a6a4a8182c231d88e6934794fc1aab64c64a7e"
IDENT = ("-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false")


class PinCompileTestCase(unittest.TestCase):
    """Compile exact member snapshots with a shared disposable target."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory(prefix="atlas-pin-compile-test-")
        cls.root = Path(cls._temporary.name)
        cls.target = cls.root / "target"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temporary.cleanup()

    def git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *IDENT, *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=pin_compile.clean_process_env(),
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def member_state(self, member: str) -> tuple[str, str]:
        repo = ROOT / "repos" / member
        return self.git(repo, "rev-parse", "HEAD"), self.git(repo, "status", "--porcelain")

    def meta_with_pins(self, consumer: str, provider: str) -> Path:
        meta = self.root / f"meta-{consumer[:10]}-{provider[:10]}"
        meta.mkdir()
        self.git(meta, "init", "-b", "main", "--quiet")
        for member in (pin_compile.CONSUMER, pin_compile.PROVIDER):
            destination = meta / "repos" / member
            destination.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--shared",
                    "--quiet",
                    "--no-checkout",
                    str(ROOT / "repos" / member),
                    str(destination),
                ],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=pin_compile.clean_process_env(),
                timeout=60,
                check=True,
            )
            origin = self.git(ROOT / "repos" / member, "remote", "get-url", "origin")
            self.git(destination, "remote", "set-url", "origin", origin)
            self.git(destination, "config", "remote.origin.promisor", "true")
            self.git(
                destination,
                "config",
                "remote.origin.partialclonefilter",
                "blob:none",
            )
        (meta / ".gitmodules").write_text(
            "".join(
                f'[submodule "repos/{member}"]\n'
                f"\tpath = repos/{member}\n"
                f"\turl = https://github.com/ryancinsight/{member}\n"
                for member in (pin_compile.CONSUMER, pin_compile.PROVIDER)
            ),
            encoding="utf-8",
        )
        self.git(meta, "add", ".gitmodules")
        for member, revision in (
            (pin_compile.CONSUMER, consumer),
            (pin_compile.PROVIDER, provider),
        ):
            self.git(
                meta,
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{revision},repos/{member}",
            )
        self.git(meta, "commit", "--quiet", "-m", "record fixture pins")
        return meta

    def compile(self, meta: Path, name: str) -> tuple[int, str]:
        return pin_compile.compile_recorded_pair(
            meta, self.root / name, self.target
        )

    @pytest.mark.slow
    def test_current_recorded_pair_compiles_without_mutating_member_checkouts(self) -> None:
        before = {
            member: self.member_state(member)
            for member in (pin_compile.CONSUMER, pin_compile.PROVIDER)
        }
        status, output = self.compile(ROOT, "current")
        self.assertEqual(status, 0, output)
        self.assertIn("PIN COMPILE OK:", output)
        for member, state in before.items():
            self.assertEqual(self.member_state(member), state)

    @pytest.mark.slow
    def test_historical_rename_pair_fails_and_names_the_api(self) -> None:
        meta = self.meta_with_pins(BROKEN_AEQUITAS, RENAMED_EUNOMIA)
        status, output = self.compile(meta, "historical")
        self.assertEqual(status, 1, output)
        self.assertIn(f"aequitas@{BROKEN_AEQUITAS}", output)
        self.assertIn(f"eunomia@{RENAMED_EUNOMIA}", output)
        self.assertIn("scale_by_f64", output)

    def test_missing_recorded_object_is_unavailable_not_compile_failure(self) -> None:
        absent = "f" * 40
        meta = self.meta_with_pins(BROKEN_AEQUITAS, absent)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = pin_compile.main(["--repo", str(meta)])
        output = stream.getvalue()
        self.assertEqual(status, 2, output)
        self.assertIn(f"eunomia@{absent}", output)
        self.assertIn("PIN COMPILE UNAVAILABLE:", output)

    def test_non_repository_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-pin-compile-invalid-") as directory:
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                status = pin_compile.main(["--repo", directory])
        output = stream.getvalue()
        self.assertEqual(status, 2, output)
        self.assertIn("aequitas@<missing>", output)
        self.assertIn("eunomia@<missing>", output)

    def test_archive_ignores_ambient_git_repository_selection(self) -> None:
        source = self.root / "archive-source"
        other = self.root / "archive-other"
        source.mkdir()
        other.mkdir()
        self.git(source, "init", "-b", "main", "--quiet")
        self.git(other, "init", "-b", "main", "--quiet")
        (source / "member.txt").write_text("member\n", encoding="utf-8")
        (other / "other.txt").write_text("other\n", encoding="utf-8")
        self.git(source, "add", "member.txt")
        self.git(other, "add", "other.txt")
        self.git(source, *IDENT, "commit", "--quiet", "-m", "source")
        self.git(other, *IDENT, "commit", "--quiet", "-m", "other")
        destination = self.root / "archive-output"
        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": str((other / ".git").resolve()),
                "GIT_WORK_TREE": str(other.resolve()),
            },
        ):
            payload = pin_compile.archive(source, "HEAD", timeout=60)
        pin_compile.extract_archive(payload, destination)
        self.assertEqual(
            (destination / "member.txt").read_text(encoding="utf-8"), "member\n"
        )
        self.assertFalse((destination / "other.txt").exists())

    def test_process_timeout_terminates_descendants(self) -> None:
        pid_file = self.root / "timeout-child.pid"
        script = (
            "import subprocess, sys, time; "
            "child = subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(60)']); "
            f"open({str(pid_file)!r}, 'w', encoding='utf-8').write(str(child.pid)); "
            "time.sleep(60)"
        )
        with self.assertRaises(pin_compile.GitProcessError) as raised:
            pin_compile.execute_process(
                [sys.executable, "-c", script],
                timeout=2,
            )
        self.assertTrue(raised.exception.timed_out)
        child_pid = int(pid_file.read_text(encoding="utf-8"))
        if os.name == "nt":
            listing = subprocess.run(
                ["tasklist", "/FI", f"PID eq {child_pid}", "/NH", "/FO", "CSV"],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
            )
            self.assertNotIn(f'"{child_pid}"', listing.stdout)
        else:
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)

    def test_explicit_git_index_is_preserved(self) -> None:
        repo = self.root / "private-index"
        repo.mkdir()
        self.git(repo, "init", "-b", "main", "--quiet")
        (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        self.git(repo, "add", "tracked.txt")
        self.git(repo, *IDENT, "commit", "--quiet", "-m", "tracked")
        (repo / "private.txt").write_text("private\n", encoding="utf-8")
        other = self.root / "ambient-other"
        other.mkdir()
        self.git(other, "init", "-b", "main", "--quiet")
        (other / "other.txt").write_text("other\n", encoding="utf-8")
        self.git(other, "add", "other.txt")
        self.git(other, *IDENT, "commit", "--quiet", "-m", "other")
        index = self.root / "private.index"
        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": str((other / ".git").resolve()),
                "GIT_WORK_TREE": str(other.resolve()),
            },
        ):
            environment = dict(os.environ)
            environment["GIT_INDEX_FILE"] = str(index)
            added = execute_git(
                repo, ("add", "private.txt"), env=environment, timeout=60
            )
            self.assertEqual(added.returncode, 0, added.stderr)
            selected = execute_git(
                repo, ("ls-files",), env=environment, timeout=60
            )
        normal = execute_git(repo, ("ls-files",), timeout=60)
        self.assertNotIn("private.txt", normal.stdout.decode("utf-8"))
        self.assertIn("private.txt", selected.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
