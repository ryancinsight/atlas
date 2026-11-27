#!/usr/bin/env python3
"""The per-ref push lock of `scripts/git-hooks/pre-push`: refusal, reclaim, release.

The real hook runs on planted lock directories; the deadline case runs the
real supervisor with a shortened wall bound.
"""

from __future__ import annotations

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from test_atlas_pre_push_gate import (
    SCRIPT,
    WATCHDOG_SECONDS,
    GateFixture,
    _publish_stack_scripts,
    _stacked_fixture,
    _write,
)

import pre_push_gate
from test_atlas_stale_reclaim import dead_pid, live_pid

REF = "refs/heads/copy"
# The deadline case asserts the hook claimed its lock within this bound.
SHORT_DEADLINE_SECONDS = 40
MSYS_HOST = os.name == "nt"  # Git Bash pids are reused: its locks record an identity.


def _lock_directory(fixture: GateFixture) -> pathlib.Path:
    key = subprocess.run(
        ["git", "hash-object", "--stdin"], input=REF.encode("utf-8"),
        capture_output=True, check=True,
    ).stdout.decode("ascii").strip()[:16]
    return fixture.root / ".git" / "atlas-push-locks" / key


def _plant_lock(fixture: GateFixture, pid: str) -> pathlib.Path:
    lock = _lock_directory(fixture)
    lock.mkdir(parents=True)
    (lock / "pid").write_bytes(pid.encode("ascii"))
    return lock


def _push(fixture: GateFixture) -> tuple[int, str]:
    line = fixture.push_line_new_branch("main").replace("refs/heads/main", REF)
    return fixture.run_hook(line, {"SKIP_LOCAL_GATE": "1"})


class PushLockReclaimTestCase(unittest.TestCase):
    """A lock is reclaimed only when its owner provably is not running."""

    def test_a_lock_whose_owner_has_exited_is_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            lock = _plant_lock(fixture, f"{dead_pid()}\n")

            code, stderr = _push(fixture)

            self.assertEqual(code, 0, stderr)
            self.assertIn("local gate skipped by SKIP_LOCAL_GATE", stderr)
            self.assertNotIn("already running", stderr)
            self.assertFalse(lock.exists(), "the run left its own lock behind")

    def test_a_lock_whose_owner_is_alive_is_retained_and_refuses(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            pid = live_pid(self)
            lock = _plant_lock(fixture, f"{pid}\n")

            code, stderr = _push(fixture)

            self.assertEqual(code, 1, stderr)
            self.assertIn(
                f"pre-push: BLOCKED -- another push of {REF} is already running\n"
                f"(pid {pid}). A second concurrent gate of the same ref would\n",
                stderr,
            )
            self.assertEqual((lock / "pid").read_bytes(), f"{pid}\n".encode("ascii"))

    def test_an_unreadable_owner_record_is_retained(self) -> None:
        cases = (("", "unknown"), ("not-a-pid\n", "not-a-pid"), ("0\n", "0"), ("-1\n", "-1"))
        for content, shown in cases:
            with self.subTest(content), tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
                fixture = _stacked_fixture(temp)
                lock = _plant_lock(fixture, content)

                code, stderr = _push(fixture)

                self.assertEqual(code, 1, stderr)
                self.assertIn(f"is already running\n(pid {shown}).", stderr)
                self.assertEqual((lock / "pid").read_bytes(), content.encode("ascii"))


class PushLockDeadlineTestCase(unittest.TestCase):
    """The supervisor releases the lock of the owner it retires."""

    def test_the_deadline_leaves_no_lock_behind(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            lock = _lock_directory(fixture)
            claimed = pathlib.Path(temp) / "claimed.txt"
            # The credential scan runs after the lock is claimed. This stand-in
            # records the lock it finds, then never returns.
            _write(
                fixture.stack / "scripts" / "atlas-secret-scan.py",
                "import pathlib, threading\n"
                f"lock = pathlib.Path({str(lock)!r})\n"
                "start = lock / 'start'\n"
                f"pathlib.Path({str(claimed)!r}).write_text(\n"
                "    (lock / 'pid').read_text() + '|'\n"
                "    + (start.read_text() if start.exists() else ''))\n"
                "threading.Event().wait()\n",
            )
            _publish_stack_scripts(fixture.stack)
            driver = (
                "import sys\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "import pre_push_gate\n"
                "pre_push_gate.DEADLINE_SECONDS = int(sys.argv[2])\n"
                "sys.argv = ['pre_push_gate.py', 'direct', 'push', sys.argv[3], 'origin', 'fixture']\n"
                "raise SystemExit(pre_push_gate.main())\n"
            )
            env = dict(os.environ)
            env["PATH"] = str(fixture.bin) + os.pathsep + env.get("PATH", "")
            env["CARGO"] = str(fixture.cargo_launcher)
            env["TMPDIR"] = fixture.tmp.as_posix()
            line = fixture.push_line_new_branch("main").replace("refs/heads/main", REF)

            result = subprocess.run(
                [sys.executable, "-I", "-c", driver, str(SCRIPT.parents[1]),
                 str(SHORT_DEADLINE_SECONDS), str(SCRIPT)],
                input=line.encode("utf-8"), cwd=str(fixture.root), env=env,
                capture_output=True, timeout=WATCHDOG_SECONDS,
            )

            stderr = result.stderr.decode("utf-8", errors="replace")
            self.assertEqual(result.returncode, 124, stderr)
            self.assertIn(
                f"phase exceeded {SHORT_DEADLINE_SECONDS} seconds; its process tree was retired",
                stderr,
            )
            self.assertTrue(claimed.is_file(), "the deadline fired before the lock was claimed")
            self.assertFalse(lock.exists(), "the retired owner's lock survived")
            self.assertFalse(lock.with_name(lock.name + ".reclaim").exists())
            held_pid, held_start = claimed.read_text(encoding="utf-8").split("|", 1)
            self.assertRegex(held_pid, r"^[1-9][0-9]*\n$")
            self.assertRegex(held_start, r"^[^|]+[|][1-9][0-9]*\n$" if MSYS_HOST else r"^$")


class ReleasePushLockTestCase(unittest.TestCase):
    """The supervisor's release removes only the lock its record names."""

    @staticmethod
    def _record(root: pathlib.Path, lock: str, pid: str, start: str) -> pathlib.Path:
        progress = root / "progress"
        progress.mkdir(exist_ok=True)
        (progress / pre_push_gate.PUSH_LOCK_RECORD).write_bytes(
            f"{lock}\n{pid}\n{start}\n".encode("ascii")
        )
        return progress

    def test_a_lock_claimed_by_another_owner_is_untouched(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-") as temp:
            root = pathlib.Path(temp)
            lock = root / "atlas-push-locks" / "0123456789abcdef"
            lock.mkdir(parents=True)
            (lock / "pid").write_bytes(b"222\n")
            (lock / "start").write_bytes(b"9\n")
            guard = lock.with_name(lock.name + ".reclaim")
            for pid, start in (("111", "9"), ("222", "8"), ("222", "")):
                with self.subTest(pid=pid, start=start):
                    pre_push_gate._release_push_lock(self._record(root, lock.as_posix(), pid, start))

                    self.assertEqual((lock / "pid").read_bytes(), b"222\n")
                    self.assertEqual((lock / "start").read_bytes(), b"9\n")
                    self.assertFalse(guard.exists(), "the guard was left behind")

    def test_an_existing_guard_is_never_reaped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-") as temp:
            root = pathlib.Path(temp)
            lock = root / "atlas-push-locks" / "0123456789abcdef"
            lock.mkdir(parents=True)
            (lock / "pid").write_bytes(b"222\n")
            guard = lock.with_name(lock.name + ".reclaim")
            guard.mkdir()

            pre_push_gate._release_push_lock(self._record(root, lock.as_posix(), "222", ""))

            self.assertTrue(guard.is_dir())
            self.assertEqual((lock / "pid").read_bytes(), b"222\n")

    def test_the_recorded_owner_is_released_and_a_missing_lock_is_quiet(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-") as temp:
            root = pathlib.Path(temp)
            lock = root / "atlas-push-locks" / "0123456789abcdef"
            lock.mkdir(parents=True)
            (lock / "pid").write_bytes(b"222\n")
            (lock / "start").write_bytes(b"9\n")
            progress = self._record(root, lock.as_posix(), "222", "9")

            pre_push_gate._release_push_lock(progress)
            pre_push_gate._release_push_lock(progress)

            self.assertEqual(list(lock.parent.iterdir()), [])

    def test_a_record_naming_no_lock_directory_is_reported_and_ignored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-lock-") as temp:
            root = pathlib.Path(temp)
            elsewhere = root / "elsewhere" / "0123456789abcdef"
            elsewhere.mkdir(parents=True)
            (elsewhere / "pid").write_bytes(b"222\n")
            for named in ("", "/", "locks/0123456789abcdef", elsewhere.as_posix()):
                with self.subTest(named=named), contextlib.redirect_stderr(io.StringIO()) as stderr:
                    pre_push_gate._release_push_lock(self._record(root, named, "222", ""))

                    self.assertIn(f"ignored a push-lock record outside atlas-push-locks: {named!r}", stderr.getvalue())
                    self.assertEqual((elsewhere / "pid").read_bytes(), b"222\n")


if __name__ == "__main__":
    unittest.main()
