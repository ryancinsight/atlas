#!/usr/bin/env python3
"""Windows sharing violations on build-identity records, stamps and queue tickets."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import atlas_build_lock as lock_module
import atlas_build_queue as queue_module
import atlas_build_records as records
import atlas_build_stamps as stamps

REAL_REPLACE = os.replace
REAL_READ_TEXT = Path.read_text
REAL_UNLINK = Path.unlink

REFUSAL = PermissionError(13, "Access is denied")


def refusing(real, refusals, error=REFUSAL):
    """`real` wrapped to raise `error` for its first `refusals` calls, counting every call."""
    calls = []

    def wrapper(*args, **kwargs):
        calls.append(args)
        if len(calls) <= refusals:
            raise error
        return real(*args, **kwargs)

    wrapper.calls = calls
    return wrapper


def minimal_record() -> dict[str, object]:
    return {
        "version": records.VERSION,
        "source": {"root": "r", "revision": "abc", "tree_digest": "d", "dirty": False},
        "build": {
            key: "x"
            for key in (
                "package",
                "profile",
                "target",
                "features",
                "toolchain",
                "target_dir",
                "command_key",
                "selection",
                "environment_digest",
                "cargo_config_digest",
                "dependency_digest",
            )
        },
        "artifact": {"files": {"debug/deps/libdep.rlib": "h"}, "digest": "d"},
        "inputs": {},
        "dependencies": {
            "root": "r",
            "digest": "d",
            "packages": [],
            "edges": [],
            "clean_packages": [],
        },
    }


class StampDirectory:
    def __init__(self, stamp: Path) -> None:
        self._stamp = stamp

    def stamp(self, record: dict[str, object]) -> Path:
        return self._stamp


class SharingViolationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.path = self.directory / "record.json"
        sleep = patch.object(lock_module.time, "sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)

    def test_a_replace_refused_twice_then_allowed_writes_the_record(self) -> None:
        replace = refusing(REAL_REPLACE, 2)
        value = {"version": records.VERSION, "answer": 42}
        with patch.object(records.os, "replace", replace):
            records._write_atomic(self.path, value)
        self.assertEqual(len(replace.calls), 3)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), value)
        self.assertEqual(self.sleep.call_count, 2)
        self.assertEqual([p.name for p in self.directory.iterdir()], [self.path.name])

    def test_a_replace_refused_past_the_bound_names_the_path_and_leaves_no_temporary(self) -> None:
        self.path.write_text('{"old": true}\n', encoding="utf-8")
        replace = refusing(REAL_REPLACE, 10**9)
        with patch.object(records.os, "replace", replace):
            with self.assertRaises(lock_module.BuildIdentityError) as raised:
                records._write_atomic(self.path, {"new": True})
        self.assertIn(str(self.path), str(raised.exception))
        error: BaseException | None = raised.exception
        while error is not None and error is not REFUSAL:
            error = error.__cause__
        self.assertIs(error, REFUSAL)
        self.assertEqual(len(replace.calls), lock_module.SHARING_RETRY_ATTEMPTS)
        self.assertEqual(self.sleep.call_count, lock_module.SHARING_RETRY_ATTEMPTS - 1)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), {"old": True})
        self.assertEqual([p.name for p in self.directory.iterdir()], [self.path.name])

    def test_an_error_other_than_a_refusal_is_not_retried(self) -> None:
        other = OSError(28, "No space left on device")
        replace = refusing(REAL_REPLACE, 10**9, other)
        with patch.object(records.os, "replace", replace):
            with self.assertRaises(lock_module.BuildIdentityError) as raised:
                records._write_atomic(self.path, {"new": True})
        self.assertIs(raised.exception.__cause__, other)
        self.assertEqual(len(replace.calls), 1)
        self.assertEqual(self.sleep.call_count, 0)
        self.assertFalse(self.path.exists())

    def test_a_read_refused_once_then_allowed_returns_the_record(self) -> None:
        value = minimal_record()
        self.path.write_text(json.dumps(value), encoding="utf-8")
        read = refusing(REAL_READ_TEXT, 1)
        with patch.object(Path, "read_text", read):
            self.assertEqual(records.read_record(self.path), value)
        self.assertEqual(len(read.calls), 2)
        self.assertEqual(self.sleep.call_count, 1)

    def test_a_read_refused_past_the_bound_is_not_reported_as_a_malformed_record(self) -> None:
        self.path.write_text(json.dumps(minimal_record()), encoding="utf-8")
        read = refusing(REAL_READ_TEXT, 10**9)
        with patch.object(Path, "read_text", read):
            with self.assertRaises(lock_module.BuildIdentityError) as raised:
                records.read_record(self.path)
        self.assertIn(str(self.path), str(raised.exception))
        self.assertNotIn("malformed", str(raised.exception))
        self.assertEqual(len(read.calls), lock_module.SHARING_RETRY_ATTEMPTS)

    def test_a_missing_record_is_not_retried(self) -> None:
        read = refusing(REAL_READ_TEXT, 0)
        with patch.object(Path, "read_text", read):
            self.assertIsNone(records.read_record(self.path))
            with self.assertRaises(FileNotFoundError):
                records.read_record_text(self.path)
        self.assertEqual(len(read.calls), 1)
        self.assertEqual(self.sleep.call_count, 0)

    def test_a_stamp_read_refused_once_then_allowed_returns_its_digest(self) -> None:
        stamp = self.directory / "stamp"
        stamp.write_text(json.dumps({"content_digest": "deadbeef"}), encoding="utf-8")
        read = refusing(REAL_READ_TEXT, 1)
        with patch.object(Path, "read_text", read):
            digest = stamps._git_stamp(StampDirectory(stamp), {"name": "dep"})
        self.assertEqual(digest, "deadbeef")
        self.assertEqual(len(read.calls), 2)

    def test_a_ticket_unlink_refused_twice_then_allowed_removes_the_ticket(self) -> None:
        ticket = self.directory / "1.ticket"
        ticket.write_bytes(b"")
        unlink = refusing(REAL_UNLINK, 2)
        with patch.object(Path, "unlink", unlink):
            queue_module._unlink(ticket, lock_module.SHARING_RETRY_ATTEMPTS)
        self.assertEqual(len(unlink.calls), 3)
        self.assertFalse(ticket.exists())

    def test_a_single_attempt_unlink_leaves_a_refused_ticket_for_the_next_scan(self) -> None:
        ticket = self.directory / "1.ticket"
        ticket.write_bytes(b"")
        unlink = refusing(REAL_UNLINK, 10**9)
        with patch.object(Path, "unlink", unlink):
            queue_module._unlink(ticket)
        self.assertEqual(len(unlink.calls), 1)
        self.assertEqual(self.sleep.call_count, 0)
        self.assertTrue(ticket.exists())

    def test_a_ticket_unlink_refused_past_the_bound_is_left_for_the_next_scan(self) -> None:
        ticket = self.directory / "1.ticket"
        ticket.write_bytes(b"")
        unlink = refusing(REAL_UNLINK, 10**9)
        with patch.object(Path, "unlink", unlink):
            queue_module._unlink(ticket, lock_module.SHARING_RETRY_ATTEMPTS)
        self.assertEqual(len(unlink.calls), lock_module.SHARING_RETRY_ATTEMPTS)
        self.assertTrue(ticket.exists())


HOLDER = (
    "import sys, time\n"
    "with open(sys.argv[1], 'rb') as handle:\n"
    "    print('held', flush=True)\n"
    "    time.sleep(float(sys.argv[2]))\n"
)


@unittest.skipUnless(os.name == "nt", "a sharing violation is a Windows file semantic")
class OpenHandleTestCase(unittest.TestCase):
    """The refusal from a real handle another process holds open, with the real clock."""

    def test_a_replace_waits_for_a_peer_to_close_the_record(self) -> None:
        hold_seconds = 0.4
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "record.json"
            path.write_text('{"old": true}\n', encoding="utf-8")
            holder = subprocess.Popen(
                [sys.executable, "-c", HOLDER, str(path), str(hold_seconds)],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertEqual(holder.stdout.readline().strip(), "held")
                probe = path.with_name("probe.tmp")
                probe.write_text("{}", encoding="utf-8")
                with self.assertRaises(PermissionError):
                    REAL_REPLACE(probe, path)
                probe.unlink()
                started = time.monotonic()
                records._write_atomic(path, {"new": True})
                waited = time.monotonic() - started
            finally:
                holder.wait(timeout=30)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"new": True})
            self.assertGreater(waited, 0.1)


if __name__ == "__main__":
    unittest.main()
