#!/usr/bin/env python3
"""Regression tests for shared-cache source identity."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "atlas_build_identity.py"
SPEC = importlib.util.spec_from_file_location("atlas_build_identity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
sys.path.insert(0, str(SCRIPT.parent))
import atlas_build_artifacts as artifacts
import atlas_build_lease as lease_module
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    LeaseHeldError,
    OwnerLease,
    package_target_lease_path,
    peek_owner,
)

identity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = identity
SPEC.loader.exec_module(identity)


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.stdout.strip()


def init_repo(root: Path, source: str) -> None:
    root.mkdir(parents=True)
    (root / "Cargo.toml").write_text(
        "[package]\nname = \"demo\"\nversion = \"0.1.0\"\n", encoding="utf-8"
    )
    (root / "Cargo.lock").write_text(
        "version = 4\n\n[[package]]\nname = \"demo\"\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (root / "src").mkdir()
    (root / "src/lib.rs").write_text(source, encoding="utf-8")
    git(root, "init", "-q")
    git(root, "config", "user.name", "Atlas test")
    git(root, "config", "user.email", "atlas-test@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "source")


def write_script(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


HOLDER = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': 'holder-root', 'revision': 'holder-revision',"
    " 'package': 'demo', 'target_dir': sys.argv[3]}, int(sys.argv[4]))\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "time.sleep(float(sys.argv[5]))\n"
    "lease.__exit__(None, None, None)\n"
)


def hold_lease(
    test: unittest.TestCase, lock: Path, target: Path, lease_seconds: int, hold_seconds: float
) -> subprocess.Popen:
    """Hold `lock` from a separate process until `hold_seconds` pass."""
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            HOLDER,
            str(SCRIPT.parent),
            str(lock),
            target.as_posix(),
            str(lease_seconds),
            str(hold_seconds),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    test.addCleanup(holder.wait, 60)
    test.addCleanup(holder.kill)
    test.addCleanup(holder.stdout.close)
    test.assertEqual(holder.stdout.readline().strip(), "held")
    return holder


MODE_HOLDER = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': sys.argv[5], 'revision': 'holder-revision',"
    " 'package': 'dep'}, 600, mode=sys.argv[3])\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "time.sleep(float(sys.argv[4]))\n"
    "lease.__exit__(None, None, None)\n"
)

# The lock call of every checker before lease modes: an exclusive lock on
# byte 0, `msvcrt.locking` on Windows and `flock` on POSIX.
LEGACY_LOCKER = (
    "import os, sys, time\n"
    "handle = open(sys.argv[1], 'a+b')\n"
    "handle.seek(0)\n"
    "try:\n"
    "    if os.name == 'nt':\n"
    "        import msvcrt\n"
    "        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)\n"
    "    else:\n"
    "        import fcntl\n"
    "        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
    "except OSError:\n"
    "    print('refused', flush=True)\n"
    "    sys.exit(0)\n"
    "print('held', flush=True)\n"
    "if sys.argv[2] == 'hold':\n"
    "    time.sleep(60)\n"
)


def start_holder(
    test: unittest.TestCase, lock: Path, mode: str, hold_seconds: float, name: str = "holder-root"
) -> subprocess.Popen:
    """Hold `lock` in `mode` from a separate process for `hold_seconds`."""
    holder = subprocess.Popen(
        [sys.executable, "-c", MODE_HOLDER, str(SCRIPT.parent), str(lock), mode, str(hold_seconds), name],
        stdout=subprocess.PIPE,
        text=True,
    )
    test.addCleanup(holder.wait, 60)
    test.addCleanup(holder.kill)
    test.addCleanup(holder.stdout.close)
    test.assertEqual(holder.stdout.readline().strip(), "held")
    return holder


def legacy_lock(test: unittest.TestCase, lock: Path, hold: bool) -> tuple[str, subprocess.Popen]:
    """Take `lock` the way a pre-mode checker does; report `held` or `refused`."""
    process = subprocess.Popen(
        [sys.executable, "-c", LEGACY_LOCKER, str(lock), "hold" if hold else "probe"],
        stdout=subprocess.PIPE,
        text=True,
    )
    test.addCleanup(process.wait, 60)
    test.addCleanup(process.kill)
    test.addCleanup(process.stdout.close)
    return process.stdout.readline().strip(), process


def request(lock: Path, mode: str) -> str:
    lease = OwnerLease(lock, {"root": "requester", "revision": "r"}, 60, mode=mode)
    try:
        lease.__enter__()
    except LeaseHeldError:
        return "refused"
    lease.__exit__(None, None, None)
    return "granted"


class LeaseModeTestCase(unittest.TestCase):
    """Shared and exclusive leases, across processes and across checker versions."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-lease-mode-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()

    def lock(self, name: str) -> Path:
        path = self.base / name / "scope.lock"
        path.parent.mkdir(parents=True)
        return path

    def test_shared_holders_share_and_exclude_writers(self) -> None:
        for held, requested, expected in (
            (SHARED, SHARED, "granted"),
            (SHARED, EXCLUSIVE, "refused"),
            (EXCLUSIVE, SHARED, "refused"),
            (EXCLUSIVE, EXCLUSIVE, "refused"),
        ):
            with self.subTest(held=held, requested=requested):
                lock = self.lock(f"{held}-{requested}")
                holder = start_holder(self, lock, held, 60)
                self.assertEqual(request(lock, requested), expected)
                holder.kill()
                holder.wait(60)
                self.assertEqual(request(lock, requested), "granted")

    def test_legacy_and_moded_holders_exclude_each_other(self) -> None:
        for mode in (SHARED, EXCLUSIVE):
            with self.subTest(legacy="holds", requested=mode):
                lock = self.lock(f"legacy-holds-{mode}")
                state, legacy = legacy_lock(self, lock, hold=True)
                self.assertEqual(state, "held")
                self.assertEqual(request(lock, mode), "refused")
                legacy.kill()
                legacy.wait(60)
                self.assertEqual(request(lock, mode), "granted")
            with self.subTest(moded=mode, requested="legacy"):
                lock = self.lock(f"moded-holds-{mode}")
                holder = start_holder(self, lock, mode, 60)
                self.assertEqual(legacy_lock(self, lock, hold=False)[0], "refused")
                holder.kill()
                holder.wait(60)
                self.assertEqual(legacy_lock(self, lock, hold=False)[0], "held")

    def test_concurrent_takers_see_contention_never_a_fault(self) -> None:
        # Truncating the record to zero bytes let a concurrent opener see an
        # empty file and write into the locked byte: PermissionError on Windows.
        lock = self.lock("storm")
        storm = (
            "import sys, time\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from atlas_build_lease import OwnerLease, LeaseHeldError\n"
            "faults = 0\n"
            "end = time.monotonic() + 3\n"
            "while time.monotonic() < end:\n"
            "    lease = OwnerLease(Path(sys.argv[2]), {'root': 'storm', 'revision': 'r'}, 60)\n"
            "    try:\n"
            "        lease.__enter__()\n"
            "    except LeaseHeldError:\n"
            "        continue\n"
            "    except Exception as error:\n"
            "        faults += 1\n"
            "        continue\n"
            "    lease.__exit__(None, None, None)\n"
            "print(faults, flush=True)\n"
        )
        workers = [
            subprocess.Popen(
                [sys.executable, "-c", storm, str(SCRIPT.parent), str(lock)],
                stdout=subprocess.PIPE,
                text=True,
            )
            for _ in range(6)
        ]
        faults = [int(worker.communicate(timeout=60)[0].strip()) for worker in workers]
        self.assertEqual(faults, [0] * 6)

    def test_a_rewritten_record_never_empties_the_lease_for_legacy_openers(self) -> None:
        # Earlier checkers open with append and write a byte into a file they
        # find empty; a record cut to zero bytes before it was rewritten sent
        # that write into a holder's locked byte.
        lock = self.lock("legacy-openers")
        OwnerLease(lock, {"root": "first", "revision": "r"}, 60).__enter__().__exit__(None, None, None)
        opener = (
            "import sys, time\n"
            "faults = 0\n"
            "end = time.monotonic() + 3\n"
            "while time.monotonic() < end:\n"
            "    try:\n"
            "        with open(sys.argv[1], 'a+b') as handle:\n"
            "            handle.seek(0, 2)\n"
            "            if handle.tell() == 0:\n"
            "                handle.write(b'\\0')\n"
            "                handle.flush()\n"
            "    except OSError:\n"
            "        faults += 1\n"
            "print(faults, flush=True)\n"
        )
        taker = (
            "import sys, time\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "from atlas_build_lease import OwnerLease, LeaseHeldError\n"
            "end = time.monotonic() + 3\n"
            "while time.monotonic() < end:\n"
            "    lease = OwnerLease(Path(sys.argv[2]), {'root': 'taker', 'revision': 'r'}, 60)\n"
            "    try:\n"
            "        lease.__enter__()\n"
            "    except LeaseHeldError:\n"
            "        continue\n"
            "    lease.__exit__(None, None, None)\n"
        )
        takers = [
            subprocess.Popen([sys.executable, "-c", taker, str(SCRIPT.parent), str(lock)])
            for _ in range(3)
        ]
        openers = [
            subprocess.Popen(
                [sys.executable, "-c", opener, str(lock)], stdout=subprocess.PIPE, text=True
            )
            for _ in range(3)
        ]
        faults = [int(process.communicate(timeout=60)[0].strip()) for process in openers]
        for process in takers:
            process.wait(60)
        self.assertEqual(faults, [0] * 3)

    @unittest.skipUnless(os.name == "nt", "LockFileEx error codes are Windows-only")
    def test_lock_failures_other_than_contention_are_raised(self) -> None:
        # A pipe cannot be byte-range locked: that is a fault, not a holder.
        read, write = os.pipe()
        self.addCleanup(os.close, write)
        with os.fdopen(read, "rb") as pipe:
            with self.assertRaises(OSError) as caught:
                lease_module._try_lock(pipe, SHARED)
            self.assertNotEqual(caught.exception.winerror, 33)
        lock = self.lock("unlocked")
        with lease_module._open_lease(lock) as handle:
            with self.assertRaises(OSError) as caught:
                lease_module._unlock(handle)
        # ERROR_NOT_LOCKED, carried as the Windows error, not in the errno slot.
        self.assertEqual(caught.exception.winerror, 158)


class BuildIdentityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-")
        self.addCleanup(self.temp.cleanup)
        # Resolved: run_build canonicalizes the target, and an 8.3 short TEMP
        # (RYANCL~1) otherwise names a different lease path than the fixture.
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "source-a"
        self.target = self.base / "shared-target"
        self.artifact = self.target / "debug" / "deps" / "libdemo-abcdef.rlib"
        self.artifact.parent.mkdir(parents=True)
        self.clean_log = self.base / "clean.log"
        self.build_script = self.base / "build.py"
        self.clean_script = self.base / "clean.py"
        write_script(
            self.build_script,
            "import os\n"
            "from pathlib import Path\n"
            "path = Path(os.environ['ARTIFACT'])\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text(os.environ['SOURCE_TOKEN'], encoding='utf-8')\n"
            "mutate = os.environ.get('MUTATE_SOURCE')\n"
            "if mutate:\n"
            "    Path(mutate).write_text('changed during build\\n', encoding='utf-8')\n",
        )
        write_script(
            self.clean_script,
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['CLEAN_LOG']).write_text('cleaned\\n', encoding='utf-8')\n"
            "Path(os.environ['ARTIFACT']).unlink(missing_ok=True)\n",
        )

    def build(
        self,
        root: Path | None = None,
        source_token: str = "source-a",
        **options: object,
    ) -> identity.BuildResult:
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": source_token,
                    "CLEAN_LOG": str(self.clean_log),
                },
            ),
        ):
            return identity.run_build(
                root or self.root,
                (root or self.root) / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                **options,
            )

    def test_source_transition_cleans_once_and_rebuilds_the_affected_package(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        first = self.build(source_token="revision-a")
        self.assertEqual(first.status, "rebuilt")
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "revision-a")
        self.assertTrue(self.clean_log.exists())

        (self.root / "src/lib.rs").write_text("fn main() { println!(\"b\"); }\n", encoding="utf-8")
        git(self.root, "add", "src/lib.rs")
        git(self.root, "commit", "-q", "-m", "source-b")
        self.clean_log.unlink()
        unrelated = self.target / "debug" / "deps" / "libcontrol-abcdef.rlib"
        unrelated.write_text("control", encoding="utf-8")

        second = self.build(source_token="revision-b")
        self.assertEqual(second.status, "rebuilt")
        self.assertEqual(self.clean_log.read_text(encoding="utf-8"), "cleaned\n")
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "revision-b")
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "control")

    def test_matching_source_reuses_the_recorded_artifact(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        first = self.build(source_token="same")
        self.clean_log.unlink()
        second = self.build(source_token="same")
        self.assertEqual(first.record_path, second.record_path)
        self.assertEqual(second.status, "reused")
        self.assertFalse(second.cleaned)
        self.assertFalse(self.clean_log.exists())
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            code, value = identity.check_record(
                self.root,
                "demo",
                self.target,
                artifact_paths=[self.artifact],
                command=[sys.executable, str(self.build_script)],
            )
        self.assertEqual(code, 0)
        self.assertEqual(value["status"], "match")

    def test_a_different_source_root_is_a_different_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.build(source_token="a")
        other = self.base / "source-b"
        init_repo(other, "fn main() {}\n")
        self.clean_log.unlink()
        result = self.build(root=other, source_token="b")
        self.assertEqual(result.status, "rebuilt")
        self.assertTrue(self.clean_log.exists())
        record = json.loads(result.record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["source"]["root"], other.resolve().as_posix())

    def test_an_active_owner_blocks_cleaning_and_preserves_the_artifact(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.build(source_token="owner")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lease = identity.OwnerLease(
            lock,
            {"root": "other-source", "revision": "other-revision", "package": "demo"},
            60,
        )
        lease.__enter__()
        try:
            self.clean_log.unlink()
            with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
                code, value = identity.check_record(
                    self.root,
                    "demo",
                    self.target,
                    artifact_paths=[self.artifact],
                    manifest=self.root / "Cargo.toml",
                )
            self.assertEqual(code, 3)
            self.assertEqual(value["status"], "owned")
            with self.assertRaises(identity.IdentityError):
                self.build(source_token="intruder")
            self.assertEqual(self.artifact.read_text(encoding="utf-8"), "owner")
            self.assertFalse(self.clean_log.exists())
        finally:
            lease.__exit__(None, None, None)

    def test_a_dependency_owner_blocks_cleaning(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        snapshot = {
            "root": "demo",
            "packages": [],
            "edges": [],
            "clean_packages": ["demo", "dep"],
            "digest": "dependency-digest",
        }
        lock = package_target_lease_path("dep", self.target)
        owner = OwnerLease(
            lock,
            {"root": str(self.root), "revision": "dependency", "package": "dep"},
            60,
        )
        owner.__enter__()
        try:
            self.clean_log.unlink(missing_ok=True)
            with (
                patch.object(identity, "_dependency_data", return_value=snapshot),
                patch.object(
                    identity,
                    "artifact_identity",
                    return_value={
                        "files": {"debug/deps/libdemo-abcdef.rlib": "digest"},
                        "digest": "artifact",
                    },
                ),
                patch.object(identity, "_run_checked"),
            ):
                with self.assertRaises(identity.IdentityError):
                    identity.run_build(
                        self.root,
                        self.root / "Cargo.toml",
                        "demo",
                        self.target,
                        [sys.executable, str(self.build_script)],
                        artifact_paths=(),
                    )
            self.assertFalse(self.clean_log.exists())
        finally:
            owner.__exit__(None, None, None)

    def test_an_expired_owner_is_recovered(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(
            json.dumps(
                {
                    "root": "stale",
                    "revision": "stale",
                    "package": "demo",
                    "target_dir": str(self.target),
                    "token": "stale-token",
                    "expires_ns": 0,
                }
            ),
            encoding="utf-8",
        )
        result = self.build(source_token="recovered")
        self.assertEqual(result.status, "rebuilt")
        self.assertFalse(identity.lease_is_held(lock))

    def test_an_unlocked_malformed_owner_is_reclaimed(self) -> None:
        # The OS lock is the ownership authority: an unlocked record cannot
        # name a live owner, and a writer killed mid-record leaves one partial.
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("not-json", encoding="utf-8")
        self.assertFalse(identity.lease_is_held(lock))
        result = self.build(source_token="reclaimed")
        self.assertEqual(result.status, "rebuilt")
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "reclaimed")

    def test_an_unlocked_owner_without_expiry_is_reclaimed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text(
            json.dumps(
                {
                    "root": "probe",
                    "revision": "probe",
                    "package": "demo",
                    "target_dir": str(self.target),
                    "token": "probe-token",
                }
            ),
            encoding="utf-8",
        )
        self.assertFalse(identity.lease_is_held(lock))
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            code, value = identity.check_record(
                self.root,
                "demo",
                self.target,
                artifact_paths=[self.artifact],
                manifest=self.root / "Cargo.toml",
            )
        self.assertEqual((code, value["status"]), (2, "missing"))
        result = self.build(source_token="reclaimed")
        self.assertEqual(result.status, "rebuilt")

    def test_a_held_owner_is_named_to_another_process(self) -> None:
        lock = package_target_lease_path("demo", self.target)
        hold_lease(self, lock, self.target, 60, 60)
        self.assertTrue(identity.lease_is_held(lock))
        second = OwnerLease(lock, {"root": "second", "revision": "second", "package": "demo"}, 60)
        with self.assertRaises(identity.IdentityError) as caught:
            second.__enter__()
        self.assertIn("owned by holder-root at holder-revision", str(caught.exception))

    def test_a_record_from_before_the_offset_is_still_read(self) -> None:
        # Holders that predate RECORD_OFFSET wrote the record at byte 0.
        lock = package_target_lease_path("demo", self.target)
        lock.parent.mkdir(parents=True, exist_ok=True)
        record = {"root": "legacy-root", "revision": "legacy-revision"}
        lock.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(peek_owner(lock), record)
        lock.write_text(" " + json.dumps(record), encoding="utf-8")
        self.assertEqual(peek_owner(lock), record)
        lock.write_text("{partial", encoding="utf-8")
        self.assertIsNone(peek_owner(lock))

    def test_a_check_reads_beside_a_shared_holder(self) -> None:
        # A check only reads, so a shared holder does not make it "owned".
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        start_holder(self, identity.lease_path(spec), SHARED, 60)
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            code, value = identity.check_record(
                self.root,
                "demo",
                self.target,
                artifact_paths=[self.artifact],
                manifest=self.root / "Cargo.toml",
            )
        self.assertEqual((code, value["status"]), (2, "missing"))

    def test_toolchain_identity_runs_in_the_source_root(self) -> None:
        completed = subprocess.CompletedProcess(["rustc"], 0, "rustc 1.95.0\n", "")
        with patch.object(identity.subprocess, "run", return_value=completed) as run:
            self.assertEqual(identity.toolchain_identity(self.root), "rustc 1.95.0")
        self.assertEqual(run.call_args.kwargs["cwd"], self.root)

    def test_command_cwd_is_used_without_changing_record_scope(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        execution_root = self.base / "execution"
        execution_root.mkdir()
        cwd_marker = self.base / "command-cwd.txt"
        command_script = self.base / "record-cwd.py"
        write_script(
            command_script,
            "import os\n"
            "from pathlib import Path\n"
            f"Path({str(cwd_marker)!r}).write_text(os.getcwd(), encoding='utf-8')\n"
            f"Path({str(self.artifact)!r}).write_text('built\\n', encoding='utf-8')\n",
        )
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            result = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(command_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, "-c", "pass"],
                command_cwd=execution_root,
            )
        record = json.loads(result.record_path.read_text(encoding="utf-8"))
        self.assertNotIn("command_cwd", record["build"])
        self.assertEqual(cwd_marker.read_text(encoding="utf-8"), str(execution_root.resolve()))

    def test_a_dirty_tree_is_not_identified_by_revision_alone(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = identity.source_identity(self.root)
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        after = identity.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)

    def test_ignored_source_files_are_hashed_and_can_be_explicitly_excluded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        (self.root / ".gitignore").write_text("generated.rs\n", encoding="utf-8")
        git(self.root, "add", ".gitignore")
        git(self.root, "commit", "-q", "-m", "ignore generated source")
        clean = identity.source_identity(self.root)
        (self.root / "generated.rs").write_text("first\n", encoding="utf-8")
        before = identity.source_identity(self.root)
        (self.root / "generated.rs").write_text("second\n", encoding="utf-8")
        after = identity.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)
        excluded = identity.source_identity(
            self.root, ignored_paths=(self.root / "generated.rs",)
        )
        self.assertFalse(excluded.dirty)
        self.assertEqual(excluded.tree_digest, clean.tree_digest)

    def test_target_files_do_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = identity.source_identity(self.root)
        target = self.root / "target"
        target.mkdir()
        (target / "artifact.rlib").write_text("generated", encoding="utf-8")
        identity_value = identity.source_identity(self.root, (target,))
        self.assertFalse(identity_value.dirty)
        self.assertEqual(identity_value.tree_digest, before.tree_digest)
        with self.assertRaises(identity.IdentityError):
            identity.build_spec(self.root, "demo", self.root, "debug", "host", "")

    def test_explicit_ignored_lockfile_does_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        lock = self.root / "Cargo.lock"
        lock.write_text("version = 4\n", encoding="utf-8")
        git(self.root, "add", "Cargo.lock")
        git(self.root, "commit", "-q", "-m", "lock")
        before = identity.source_identity(self.root)
        lock.write_text("version = 4\nchanged\n", encoding="utf-8")
        after = identity.source_identity(self.root, ignored_paths=(lock,))
        self.assertEqual(after.tree_digest, before.tree_digest)
        self.assertFalse(after.dirty)

    def test_build_environment_changes_change_the_record_scope(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=0"}):
                first = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=2"}):
                second = identity.build_spec(self.root, "demo", self.target, "debug", "host", "")
        self.assertNotEqual(first.environment_digest, second.environment_digest)
        self.assertNotEqual(identity.record_path(first), identity.record_path(second))

    def test_source_changes_during_build_are_not_recorded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        changed = self.root / "src/lib.rs"
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": "during",
                    "CLEAN_LOG": str(self.clean_log),
                    "MUTATE_SOURCE": str(changed),
                },
            ),
            self.assertRaises(identity.IdentityError),
        ):
            identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
            )
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                [sys.executable, str(self.build_script)],
            )
        self.assertFalse(identity.record_path(spec).exists())

    def test_discovery_uses_target_triple_and_exact_package_name(self) -> None:
        deps = self.target / "x86_64-unknown-linux-gnu" / "debug" / "deps"
        deps.mkdir(parents=True)
        wanted = deps / "libdemo-111.rlib"
        similar = deps / "libdemo-tools-222.rlib"
        executable = deps / "demo-333.exe"
        for path in (wanted, similar, executable):
            path.write_bytes(path.name.encode())
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={
                "demo": frozenset({"demo"}),
                "demo-tools": frozenset({"demo_tools"}),
            },
        ):
            paths = identity.discover_artifacts(
                self.target,
                "demo",
                "debug",
                "x86_64-unknown-linux-gnu",
                self.root / "Cargo.toml",
            )
        self.assertEqual(set(paths), {wanted.resolve(), executable.resolve()})

    def test_discovery_normalizes_target_names_and_fingerprint_layout(self) -> None:
        deps = self.target / "debug" / "deps"
        fingerprint = self.target / "debug" / ".fingerprint" / "my-pkg-123"
        deps.mkdir(parents=True, exist_ok=True)
        fingerprint.mkdir(parents=True, exist_ok=True)
        artifact = deps / "libcustom_target-111.rlib"
        output = fingerprint / "output"
        artifact.write_bytes(b"artifact")
        output.write_bytes(b"output")
        with patch.object(
            artifacts,
            "_workspace_artifact_owners",
            return_value={"my-pkg": frozenset({"custom_target", "my_pkg"})},
        ):
            paths = artifacts.discover_artifacts(
                self.target, "my-pkg", "debug", manifest=self.root / "Cargo.toml"
            )
        self.assertEqual(set(paths), {artifact.resolve(), output.resolve()})

    def test_dependency_snapshot_tracks_reachable_path_sources(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        dependency_root = self.base / "dependency"
        dependency_root.mkdir()
        (dependency_root / "Cargo.toml").write_text("[package]\nname = \"dep\"\n", encoding="utf-8")
        metadata = {
            "packages": [
                {
                    "id": "root 0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((self.root / "Cargo.toml").resolve()),
                },
                {
                    "id": "path+dep 0.1.0",
                    "name": "dep",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((dependency_root / "Cargo.toml").resolve()),
                },
            ],
            "workspace_members": ["root 0.1.0"],
            "resolve": {
                "nodes": [
                    {"id": "root 0.1.0", "deps": [{"pkg": "path+dep 0.1.0", "dep_kinds": []}]},
                    {"id": "path+dep 0.1.0", "deps": []},
                ]
            },
        }
        with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
            first = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "b"},
            )
        self.assertNotEqual(first["digest"], second["digest"])
        self.assertEqual(first["clean_packages"], ["demo", "dep"])

    def test_registry_package_content_changes_change_the_dependency_snapshot(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        registry_root = self.base / "registry"
        (registry_root / "src").mkdir(parents=True)
        (registry_root / "Cargo.toml").write_text(
            "[package]\nname = \"dep\"\nversion = \"0.1.0\"\n", encoding="utf-8"
        )
        source = registry_root / "src" / "lib.rs"
        source.write_text("pub fn value() -> u8 { 1 }\n", encoding="utf-8")
        metadata = {
            "packages": [
                {
                    "id": "root 0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "source": None,
                    "manifest_path": str((self.root / "Cargo.toml").resolve()),
                },
                {
                    "id": "registry dep",
                    "name": "dep",
                    "version": "0.1.0",
                    "source": "registry+https://example.invalid/dep",
                    "manifest_path": str((registry_root / "Cargo.toml").resolve()),
                },
            ],
            "workspace_members": ["root 0.1.0"],
            "resolve": {
                "nodes": [
                    {"id": "root 0.1.0", "deps": [{"pkg": "registry dep", "dep_kinds": []}]},
                    {"id": "registry dep", "deps": []},
                ]
            },
        }
        with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
            first = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
            source.write_text("pub fn value() -> u8 { 2 }\n", encoding="utf-8")
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
            )
        self.assertNotEqual(first["digest"], second["digest"])
        first_registry = next(
            package for package in first["packages"] if package["name"] == "dep"
        )
        second_registry = next(
            package for package in second["packages"] if package["name"] == "dep"
        )
        self.assertNotEqual(
            first_registry["content_digest"],
            second_registry["content_digest"],
        )

    def test_outside_artifact_is_rejected_before_cleaning(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        outside = self.base / "outside.rlib"
        outside.write_text("outside", encoding="utf-8")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            with self.assertRaises(identity.IdentityError):
                identity.run_build(
                    self.root,
                    self.root / "Cargo.toml",
                    "demo",
                    self.target,
                    [sys.executable, str(self.build_script)],
                    artifact_paths=[outside],
                    clean_command=[sys.executable, str(self.clean_script)],
                )
        self.assertFalse(self.clean_log.exists())

    def test_dependency_transition_cleans_the_reachable_path_packages(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        snapshot = {
            "root": "demo",
            "packages": [],
            "edges": [],
            "clean_packages": ["demo", "dep"],
            "digest": "dependency-digest",
        }
        artifact = self.target / "debug" / "deps" / "libdemo-123.rlib"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        commands: list[tuple[str, ...]] = []

        def run_command(command: tuple[str, ...], root: Path, environment: dict[str, str]) -> None:
            commands.append(command)
            if len(command) < 2 or command[1] != "clean":
                artifact.write_text("built", encoding="utf-8")

        artifact_value = {"files": {"debug/deps/libdemo-123.rlib": "digest"}, "digest": "artifact"}
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.object(identity, "dependency_snapshot", return_value=snapshot),
            patch.object(identity, "artifact_identity", return_value=artifact_value),
            patch.object(identity, "_run_checked", side_effect=run_command),
        ):
            first = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, "-c", "pass"],
            )
            second = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, "-c", "pass"],
            )
        self.assertEqual(first.status, "rebuilt")
        self.assertEqual(second.status, "reused")
        clean_commands = [command for command in commands if list(command[1:3]) == ["clean", "-p"]]
        self.assertEqual([command[3] for command in clean_commands], ["demo", "dep"])

    def test_older_record_versions_are_stale(self) -> None:
        record = self.base / "old-record.json"
        for version in (1, 2):
            record.write_text(json.dumps({"version": version}), encoding="utf-8")
            self.assertIsNone(identity.read_record(record))

    def test_malformed_records_fail_closed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            spec = identity.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                [sys.executable, str(self.build_script)],
            )
            record = identity.record_path(spec)
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text('{"version": true}', encoding="utf-8")
            with self.assertRaises(identity.IdentityError):
                identity.check_record(
                    self.root,
                    "demo",
                    self.target,
                    artifact_paths=[self.artifact],
                    manifest=self.root / "Cargo.toml",
                    command=[sys.executable, str(self.build_script)],
                )

    def test_artifact_paths_must_stay_inside_the_shared_target(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        outside = self.base / "outside.rlib"
        outside.write_text("outside", encoding="utf-8")
        with self.assertRaises(identity.IdentityError):
            identity.artifact_identity(
                self.root,
                self.target,
                "demo",
                "debug",
                [outside],
            )

    def test_command_keys_keep_separate_records_over_one_source(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        clippy = self.build(source_token="same", command_key="clippy")
        self.assertTrue(clippy.cleaned)
        self.clean_log.unlink()
        tests = self.build(source_token="same", command_key="tests")
        self.assertNotEqual(clippy.record_path, tests.record_path)
        # The tests step builds the source clippy just built: nothing foreign
        # to clean, so the clippy artifacts survive.
        self.assertFalse(tests.cleaned)
        self.assertFalse(self.clean_log.exists())

    def test_a_new_command_key_after_a_source_change_still_cleans(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.build(source_token="a", command_key="clippy")
        (self.root / "src/lib.rs").write_text("fn main() { let _b = 1; }\n", encoding="utf-8")
        git(self.root, "commit", "-qam", "source-b")
        self.clean_log.unlink()
        result = self.build(source_token="b", command_key="tests")
        self.assertTrue(result.cleaned)
        self.assertTrue(self.clean_log.exists())

    def test_an_ignored_path_does_not_change_the_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        lock = self.root / "Cargo.lock"
        lock.write_text("# committed\n", encoding="utf-8")
        git(self.root, "add", "Cargo.lock")
        git(self.root, "commit", "-qm", "lock")
        before = identity.source_identity(self.root)
        lock.write_text("# rewritten by the gate\n", encoding="utf-8")
        self.assertEqual(identity.source_identity(self.root, ignored_paths=(lock,)), before)
        self.assertTrue(identity.source_identity(self.root).dirty)
        (self.root / "src/lib.rs").write_text("fn main() { let _c = 1; }\n", encoding="utf-8")
        self.assertTrue(identity.source_identity(self.root, ignored_paths=(lock,)).dirty)

    def test_an_ignored_path_outside_the_source_tree_is_rejected(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with self.assertRaises(identity.IdentityError):
            identity.source_identity(
                self.root, ignored_paths=(self.base / "elsewhere.lock",)
            )

    def test_commands_run_in_the_requested_directory(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        elsewhere = self.base / "gate-cwd"
        elsewhere.mkdir()
        marker = self.base / "cwd.txt"
        record_cwd = self.base / "record_cwd.py"
        write_script(
            record_cwd,
            "import os, sys\n"
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text(os.getcwd(), encoding='utf-8')\n"
            f"exec(open({str(self.build_script)!r}).read())\n",
        )
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {"ARTIFACT": str(self.artifact), "SOURCE_TOKEN": "cwd", "CLEAN_LOG": str(self.clean_log)},
            ),
        ):
            identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(record_cwd)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                command_cwd=elsewhere,
            )
        self.assertEqual(Path(marker.read_text(encoding="utf-8")).resolve(), elsewhere.resolve())


class CommandLineTestCase(unittest.TestCase):
    """The entry point accepts the exact argument shape the member pre-push passes."""

    _run_checked = staticmethod(identity._run_checked)

    def _skip_cargo_clean(self, command, cwd, environment) -> None:
        # The CLI cannot inject a clean command; keep the test off real Cargo.
        if list(command[:2]) == ["cargo", "clean"]:
            return
        self._run_checked(command, cwd, environment)

    def setUp(self) -> None:
        cli_path = Path(__file__).resolve().parents[1] / "atlas-build-identity.py"
        cli_spec = importlib.util.spec_from_file_location("atlas_build_identity_cli", cli_path)
        assert cli_spec is not None and cli_spec.loader is not None
        self.cli = importlib.util.module_from_spec(cli_spec)
        cli_spec.loader.exec_module(self.cli)
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-cli-")
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.root = base / "member"
        init_repo(self.root, "fn main() {}\n")
        self.target = base / "target"
        self.artifact = self.target / "debug" / "deps" / "libdemo-cli.rlib"
        self.build = base / "build.py"
        write_script(
            self.build,
            "from pathlib import Path\n"
            f"path = Path({str(self.artifact)!r})\n"
            "path.parent.mkdir(parents=True, exist_ok=True)\n"
            "path.write_text('built', encoding='utf-8')\n",
        )

    def pre_push(self, *options: str) -> int:
        """Run the entry point with the member pre-push hook's exact arguments."""
        root = self.root
        with (
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.object(identity, "_run_checked", side_effect=self._skip_cargo_clean),
        ):
            return self.cli.main([
                "run",
                "--root", str(root),
                "--package", "demo",
                "--target-dir", str(self.target),
                "--profile", "debug",
                "--target", "host",
                "--manifest", str(root / "Cargo.toml"),
                "--command-cwd", str(root),
                "--command-key", "atlas-pre-push:demo",
                "--ignore-path", str(root / "Cargo.lock"),
                "--manifest", str(root / "Cargo.toml"),
                *options,
                "--",
                sys.executable, str(self.build),
            ])

    def test_the_pre_push_invocation_parses_and_runs(self) -> None:
        with patch.object(self.cli, "run_build", wraps=identity.run_build) as run_build:
            code = self.pre_push()
        self.assertEqual(code, 0)
        kwargs = run_build.call_args.kwargs
        self.assertEqual(kwargs["command_key"], "atlas-pre-push:demo")
        self.assertEqual(kwargs["command_cwd"], self.root)
        self.assertEqual(kwargs["ignore_paths"], [self.root / "Cargo.lock"])
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "built")

    def test_the_pre_push_waits_for_a_live_owner_to_release(self) -> None:
        lock = package_target_lease_path("demo", identity._canonical(self.target))
        started = time.monotonic()
        hold_lease(self, lock, self.target, 60, 2)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = self.pre_push()
        self.assertEqual(code, 0, stderr.getvalue())
        self.assertGreaterEqual(time.monotonic() - started, 2)
        self.assertIn("held by holder-root at holder-revision", stderr.getvalue())
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "built")

    def test_the_pre_push_waits_out_an_owner_past_its_expiry(self) -> None:
        # A 1 s lease held for 4 s: the lock, not the recorded expiry, says
        # the owner is alive, so the waiter keeps waiting and then proceeds.
        lock = package_target_lease_path("demo", identity._canonical(self.target))
        started = time.monotonic()
        hold_lease(self, lock, self.target, 1, 4)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = self.pre_push()
        self.assertEqual(code, 0, stderr.getvalue())
        self.assertGreaterEqual(time.monotonic() - started, 4)
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "built")

    def test_the_pre_push_wait_ends_at_the_wait_bound(self) -> None:
        lock = package_target_lease_path("demo", identity._canonical(self.target))
        hold_lease(self, lock, self.target, 600, 60)
        started = time.monotonic()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = self.pre_push("--lease-wait-seconds", "2")
        elapsed = time.monotonic() - started
        self.assertEqual(code, 1)
        self.assertGreaterEqual(elapsed, 2)
        # The holder's 600 s lease and 60 s hold both outlast the bound.
        self.assertLess(elapsed, 30)
        self.assertIn(
            "still held by holder-root at holder-revision after waiting 2 s (--lease-wait-seconds)",
            stderr.getvalue(),
        )
        self.assertFalse(self.artifact.exists())

if __name__ == "__main__":
    unittest.main()
