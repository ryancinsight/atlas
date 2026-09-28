#!/usr/bin/env python3
"""Regression tests for shared-cache source identity."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "atlas_build_identity.py"
SPEC = importlib.util.spec_from_file_location("atlas_build_identity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
sys.path.insert(0, str(SCRIPT.parent))
import atlas_build_artifacts as artifacts
import atlas_build_lease as lease_module
import atlas_build_lock as lock_module
import atlas_build_package_source as package_source
import atlas_build_queue as queue_module
import atlas_build_source as build_source
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    LeaseHeldError,
    OwnerLease,
    acquire_waiting,
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
    disable_maintenance(root)
    git(root, "config", "user.name", "Atlas test")
    git(root, "config", "user.email", "atlas-test@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "source")


def disable_maintenance(root: Path) -> None:
    """No detached `gc --auto` or maintenance may write into `.git` while the
    fixture's temporary directory is removed (a Linux runner failed teardown
    with `Directory not empty: .git`)."""
    git(root, "config", "gc.auto", "0")
    git(root, "config", "maintenance.auto", "false")


def gate_export(source: Path, export: Path) -> str:
    """Export `source`'s HEAD the way the pre-push gate does; return its revision.

    A repository borrowing the source's objects, its files and index written
    by `read-tree -u --reset` run in the source, `HEAD` set to the revision.
    """
    revision = git(source, "rev-parse", "HEAD")
    export.mkdir(parents=True)
    git(export, "init", "-q")
    disable_maintenance(export)
    objects = git(source, "rev-parse", "--path-format=absolute", "--git-common-dir") + "/objects"
    (export / ".git" / "objects" / "info" / "alternates").write_bytes(objects.encode() + b"\n")
    subprocess.run(
        ["git", "read-tree", "-u", "--reset", revision], cwd=source, check=True, timeout=60,
        env=dict(os.environ, GIT_WORK_TREE=str(export), GIT_INDEX_FILE=str(export / ".git" / "index")),
    )
    git(export, "update-ref", "HEAD", revision)
    return revision


def write_script(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


# Holds until argv[6] exists, or for argv[5] seconds without one. A hold
# timed from the holder's own start raced the waiter's metadata reads: on a
# loaded host the waiter reached the lease after it was free and never waited.
HOLDER = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': 'holder-root', 'revision': 'holder-revision',"
    " 'package': 'demo', 'target_dir': sys.argv[3]}, int(sys.argv[4]))\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "release = Path(sys.argv[6]) if len(sys.argv) > 6 else None\n"
    "end = time.monotonic() + float(sys.argv[5])\n"
    "while time.monotonic() < end and not (release and release.exists()):\n"
    "    time.sleep(0.01)\n"
    "lease.__exit__(None, None, None)\n"
)


def hold_lease(
    test: unittest.TestCase,
    lock: Path,
    target: Path,
    lease_seconds: int,
    hold_seconds: float,
    release: Path | None = None,
) -> subprocess.Popen:
    """Hold `lock` from a separate process until `release` exists or `hold_seconds` pass."""
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
            *([str(release)] if release else []),
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
    "from atlas_build_lease import OwnerLease, acquire_waiting\n"
    "for _ in range(int(sys.argv[6])):\n"
    "    lease = OwnerLease(Path(sys.argv[2]), {'root': sys.argv[5], 'revision': 'holder-revision',"
    " 'package': 'dep'}, 600, mode=sys.argv[3])\n"
    "    acquire_waiting(lease, 120)\n"
    "    print('held', flush=True)\n"
    "    time.sleep(float(sys.argv[4]))\n"
    "    lease.__exit__(None, None, None)\n"
)

# The lease module as every checker ran it before lease modes (atlas
# f96b218, byte for byte): the fleet's hooks keep running it until they fetch.
# Remove it, and the interop tests that load it, once every member's pinned
# atlas checker is at or past #320: no hook then runs the pre-mode protocol.
LEASE_WITHOUT_MODES = Path(__file__).resolve().parent / "fixtures" / "lease_without_modes.py"
LEGACY_TAKER = (
    "import importlib.util, sys, time\n"
    "from pathlib import Path\n"
    "spec = importlib.util.spec_from_file_location('lease_without_modes', sys.argv[1])\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(module)\n"
    "lease = module.OwnerLease(Path(sys.argv[2]), {'root': 'legacy', 'revision': 'r'}, 60)\n"
    "try:\n"
    "    lease.__enter__()\n"
    "except module.LeaseHeldError:\n"
    "    print('refused', flush=True)\n"
    "    sys.exit(0)\n"
    "print('held', flush=True)\n"
    "if sys.argv[3] == 'hold':\n"
    "    time.sleep(60)\n"
)


def start_holder(
    test: unittest.TestCase,
    lock: Path,
    mode: str,
    hold_seconds: float,
    name: str = "holder-root",
    repeat: int = 1,
    wait_until_held: bool = True,
) -> subprocess.Popen:
    """Hold `lock` in `mode` from a separate process, `repeat` times back to back.

    Each round waits its turn, holds for `hold_seconds`, releases, and asks
    again at once: the pattern of a push hook re-running its steps.
    """
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            MODE_HOLDER,
            str(SCRIPT.parent),
            str(lock),
            mode,
            str(hold_seconds),
            name,
            str(repeat),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    test.addCleanup(holder.wait, 60)
    test.addCleanup(holder.kill)
    test.addCleanup(holder.stdout.close)
    if wait_until_held:
        test.assertEqual(holder.stdout.readline().strip(), "held")
    return holder


def legacy_lock(test: unittest.TestCase, lock: Path, hold: bool) -> tuple[str, subprocess.Popen]:
    """Take `lock` with the pre-mode lease module; `held`, `refused`, or '' if it crashed."""
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            LEGACY_TAKER,
            str(LEASE_WITHOUT_MODES),
            str(lock),
            "hold" if hold else "probe",
        ],
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
        # Five takers running this module and one running the pre-mode module
        # (which faults against a second copy of itself) race on one lease.
        # A record cut to zero bytes before it was rewritten, or a new lease
        # left empty while held, let an opener write into the locked byte.
        lock = self.lock("storm")
        storm = (
            "import importlib.util, sys, time\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(sys.argv[1]).parent))\n"
            "spec = importlib.util.spec_from_file_location('taker', sys.argv[1])\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "faults = 0\n"
            "end = time.monotonic() + 3\n"
            "while time.monotonic() < end:\n"
            "    lease = module.OwnerLease(Path(sys.argv[2]), {'root': 'storm', 'revision': 'r'}, 60)\n"
            "    try:\n"
            "        lease.__enter__()\n"
            "    except module.LeaseHeldError:\n"
            "        continue\n"
            "    except Exception:\n"
            "        faults += 1\n"
            "        continue\n"
            "    lease.__exit__(None, None, None)\n"
            "print(faults, flush=True)\n"
        )
        workers = [
            subprocess.Popen(
                [sys.executable, "-c", storm, str(module), str(lock)],
                stdout=subprocess.PIPE,
                text=True,
            )
            for module in (*[SCRIPT.parent / "atlas_build_lease.py"] * 5, LEASE_WITHOUT_MODES)
        ]
        faults = [int(worker.communicate(timeout=60)[0].strip()) for worker in workers]
        self.assertEqual(faults, [0] * 6)

    def waited(self, lock: Path, mode: str) -> float:
        started = time.monotonic()
        lease = acquire_waiting(OwnerLease(lock, {"root": "waiter", "revision": "r"}, 60, mode=mode), 60)
        elapsed = time.monotonic() - started
        lease.__exit__(None, None, None)
        return elapsed

    def test_a_repeating_exclusive_holder_does_not_starve_a_waiter(self) -> None:
        # Twelve back-to-back 1 s holds: without arrival order the holder asks
        # again the instant it releases and the polling waiter never gets in.
        for mode in (EXCLUSIVE, SHARED):
            with self.subTest(waiter=mode):
                lock = self.lock(f"repeat-{mode}")
                holder = start_holder(self, lock, EXCLUSIVE, 1, repeat=12)
                # A waiting reader also holds back the writer's next round.
                self.assertLess(self.waited(lock, mode), 6)
                holder.kill()
                holder.wait(60)

    def test_a_stream_of_shared_readers_does_not_starve_a_writer(self) -> None:
        # Two readers overlap, so the lease is never free of a shared holder.
        lock = self.lock("stream")
        start_holder(self, lock, SHARED, 1, name="reader-a", repeat=12)
        time.sleep(0.5)
        start_holder(self, lock, SHARED, 1, name="reader-b", repeat=12)
        self.assertLess(self.waited(lock, EXCLUSIVE), 6)

    def test_a_crashed_holder_or_waiter_gives_up_its_place(self) -> None:
        lock = self.lock("crash")
        holder = start_holder(self, lock, SHARED, 60)
        waiter = start_holder(self, lock, EXCLUSIVE, 60, name="waiter", wait_until_held=False)
        queue = lock.with_name(f"{lock.stem}.queue")
        deadline = time.monotonic() + 30
        while len(list(queue.glob("*.ticket"))) < 2:
            self.assertLess(time.monotonic(), deadline, "the waiter never queued")
            time.sleep(0.05)
        for process in (waiter, holder):
            process.kill()
            process.wait(60)
        self.assertLess(self.waited(lock, SHARED), 2)
        self.assertEqual(list(queue.glob("*.ticket")), [])

    def test_dead_tickets_of_every_mode_are_collected(self) -> None:
        lock = self.lock("collect")
        queue = lock.with_name(f"{lock.stem}.queue")
        queue.mkdir()
        now = time.monotonic_ns()
        for index in range(20):
            mode = "x" if index % 2 else "s"
            arrival = now + (index - 10) * 1_000_000_000
            (queue / f"{arrival:020d}-{mode}-1-dead{index}.ticket").write_bytes(b" {}")
        # A shared request, which only waits on exclusive tickets, still
        # collects the dead shared ones, including those after its own.
        self.assertLess(self.waited(lock, SHARED), 2)
        self.assertEqual(list(queue.glob("*.ticket")), [])

    @unittest.skipIf(os.name == "nt", "Windows cannot delete a file its requester holds open")
    def test_a_waiting_ticket_removed_by_a_peer_is_recreated_in_its_place(self) -> None:
        # A peer that saw the ticket unlocked just before its requester locked
        # it can still unlink it on POSIX; the requester's next attempt puts
        # it back with its original arrival.
        lock = self.lock("unlinked")
        start_holder(self, lock, EXCLUSIVE, 60)
        waiter = OwnerLease(lock, {"root": "waiter", "revision": "r"}, 60)
        with self.assertRaises(LeaseHeldError):
            waiter.attempt()
        self.addCleanup(waiter.dequeue)
        arrival = waiter.ticket.path.name.split("-", 1)[0]
        os.unlink(waiter.ticket.path)
        with self.assertRaises(LeaseHeldError):
            waiter.attempt()
        names = [path.name for path in lock.with_name(f"{lock.stem}.queue").glob("*.ticket")]
        self.assertIn(waiter.ticket.path.name, names)
        self.assertTrue(waiter.ticket.path.name.startswith(f"{arrival}-x-"))

    def test_a_ticket_no_longer_named_by_its_path_is_recreated_in_its_place(self) -> None:
        # The POSIX race above, through the seam that detects it, so Windows,
        # which cannot unlink an open file, exercises the re-creation too.
        lock = self.lock("renamed")
        start_holder(self, lock, EXCLUSIVE, 60)
        waiter = OwnerLease(lock, {"root": "waiter", "revision": "r"}, 60)
        with self.assertRaises(LeaseHeldError):
            waiter.attempt()
        self.addCleanup(waiter.dequeue)
        first = waiter.ticket.path
        real_names = queue_module._names
        with patch.object(
            queue_module,
            "_names",
            side_effect=lambda path, handle: path != first and real_names(path, handle),
        ):
            with self.assertRaises(LeaseHeldError):
                waiter.attempt()
        self.assertNotEqual(waiter.ticket.path, first)
        self.assertEqual(waiter.ticket.path.name.split("-", 1)[0], first.name.split("-", 1)[0])
        names = [path.name for path in lock.with_name(f"{lock.stem}.queue").glob("*.ticket")]
        self.assertIn(waiter.ticket.path.name, names)

    def test_a_ticket_locked_by_a_peer_before_its_requester_is_retried(self) -> None:
        # The window between creating a ticket and locking it is too short to
        # hit by chance, so a real peer process takes its probe lock inside it.
        lock = self.lock("race")
        real_try_lock = queue_module._try_lock
        probes: list[subprocess.Popen] = []
        probe = (
            "import sys, time\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import atlas_build_lease as lease\n"
            "handle = open(sys.argv[2], 'rb')\n"
            "assert lease._try_lock(handle, 'shared')\n"
            "print('held', flush=True)\n"
            "time.sleep(0.3)\n"
        )

        def contended(handle, mode=EXCLUSIVE):
            if not probes and str(handle.name).endswith(".ticket") and mode == EXCLUSIVE:
                process = subprocess.Popen(
                    [sys.executable, "-c", probe, str(SCRIPT.parent), str(handle.name)],
                    stdout=subprocess.PIPE,
                    text=True,
                )
                self.addCleanup(process.wait, 60)
                self.addCleanup(process.kill)
                self.addCleanup(process.stdout.close)
                self.assertEqual(process.stdout.readline().strip(), "held")
                probes.append(process)
            return real_try_lock(handle, mode)

        with patch.object(queue_module, "_try_lock", side_effect=contended):
            self.assertLess(self.waited(lock, EXCLUSIVE), 5)
        self.assertEqual(len(probes), 1)
        probes[0].wait(60)
        self.waited(lock, SHARED)
        self.assertEqual(list(lock.with_name(f"{lock.stem}.queue").glob("*.ticket")), [])

    def test_a_ticket_survives_peers_probing_it_as_it_is_created(self) -> None:
        # A peer's liveness check can lock a ticket between its creation and
        # its requester's lock; the requester must retry, not fail.
        lock = self.lock("probed")
        queue = lock.with_name(f"{lock.stem}.queue")
        queue.mkdir()
        prober = (
            "import sys, time\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import atlas_build_lease as lease\n"
            "queue = Path(sys.argv[2])\n"
            "print('probing', flush=True)\n"
            "end = time.monotonic() + 4\n"
            "while time.monotonic() < end:\n"
            "    for path in queue.glob('*.ticket'):\n"
            "        try:\n"
            "            handle = path.open('rb')\n"
            "        except OSError:\n"
            "            continue\n"
            "        try:\n"
            "            if lease._try_lock(handle, 'shared'):\n"
            "                time.sleep(0.002)\n"
            "                lease._unlock(handle)\n"
            "        finally:\n"
            "            handle.close()\n"
        )
        probers = []
        for _ in range(3):
            process = subprocess.Popen(
                [sys.executable, "-c", prober, str(SCRIPT.parent), str(queue)],
                stdout=subprocess.PIPE,
                text=True,
            )
            self.addCleanup(process.wait, 60)
            self.addCleanup(process.kill)
            self.addCleanup(process.stdout.close)
            self.assertEqual(process.stdout.readline().strip(), "probing")
            probers.append(process)
        end = time.monotonic() + 3
        taken = 0
        while time.monotonic() < end:
            self.assertLess(self.waited(lock, EXCLUSIVE), 2)
            taken += 1
        self.assertGreater(taken, 10)
        for process in probers:
            process.wait(60)
        # A release a probe held open stays behind, dead, for the next request.
        self.waited(lock, SHARED)
        self.assertEqual(list(queue.glob("*.ticket")), [])

    @unittest.skipUnless(os.name == "nt", "only Windows refuses to delete an open file")
    def test_a_failing_lock_call_closes_its_handle(self) -> None:
        lock = self.lock("fault")
        fault = OSError(1, "injected lock fault")
        with patch.object(lock_module, "_try_lock", side_effect=fault):
            for take in (
                lambda: OwnerLease(lock, {"root": "r", "revision": "r"}, 60, mode=SHARED).__enter__(),
                lambda: lease_module.LeaseProbe(lock).__enter__(),
            ):
                lock.parent.mkdir(exist_ok=True)
                with self.assertRaises(OSError):
                    take()
                # The exception keeps its frame, and so any leaked handle,
                # alive; Windows refuses to remove a directory holding one.
                shutil.rmtree(lock.parent)

    @unittest.skipUnless(os.name == "nt", "only Windows refuses to delete an open file")
    def test_a_failing_release_closes_its_handle(self) -> None:
        for mode, take in (
            (EXCLUSIVE, lambda lock: OwnerLease(lock, {"root": "r", "revision": "r"}, 60)),
            (SHARED, lambda lock: lease_module.LeaseProbe(lock)),
        ):
            with self.subTest(mode=mode):
                lock = self.lock(f"release-{mode}")
                held = take(lock)
                held.__enter__()
                with patch.object(lock_module, "_unlock", side_effect=OSError(158, "injected")):
                    # The lease's ticket is released through the same failing call.
                    with self.assertRaises((identity.IdentityError, OSError)):
                        held.__exit__(None, None, None)
                shutil.rmtree(lock.parent)

    @unittest.skipUnless(os.name == "nt", "LockFileEx error codes are Windows-only")
    def test_lock_failures_other_than_contention_are_raised(self) -> None:
        # A pipe cannot be byte-range locked: that is a fault, not a holder.
        read, write = os.pipe()
        self.addCleanup(os.close, write)
        with os.fdopen(read, "rb") as pipe:
            with self.assertRaises(OSError) as caught:
                lock_module._try_lock(pipe, SHARED)
            self.assertNotEqual(caught.exception.winerror, 33)
        lock = self.lock("unlocked")
        with lock_module._open_lease(lock) as handle:
            with self.assertRaises(OSError) as caught:
                lock_module._unlock(handle)
        # ERROR_NOT_LOCKED, carried as the Windows error, not in the errno slot.
        self.assertEqual(caught.exception.winerror, 158)


# A shared reader of `dep` that builds new variants of it beside the ones
# a record names, writing each in slow chunks so a hash can catch it half done.
VARIANT_WRITER = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': 'variant-writer', 'revision': 'r'}, 600, mode='shared')\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "deps = Path(sys.argv[3])\n"
    "end = time.monotonic() + float(sys.argv[4])\n"
    "variant = 0\n"
    "while time.monotonic() < end:\n"
    "    variant += 1\n"
    "    with (deps / f'libdep-variant{variant}.rlib').open('wb') as stream:\n"
    "        for _ in range(20):\n"
    "            stream.write(b'x' * 65536)\n"
    "            stream.flush()\n"
    "            time.sleep(0.005)\n"
    "lease.__exit__(None, None, None)\n"
)

# A shared reader of `dep` that, once a writer queues for `dep`, rebuilds the
# artifact to match the record and releases: the rebuild a re-check must see.
REBUILDING_READER = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lock = Path(sys.argv[2])\n"
    "lease = OwnerLease(lock, {'root': 'rebuilding-reader', 'revision': 'r'}, 600, mode='shared')\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "queue = lock.with_name(lock.stem + '.queue')\n"
    "end = time.monotonic() + 60\n"
    "while time.monotonic() < end and not any('-x-' in path.name for path in queue.glob('*.ticket')):\n"
    "    time.sleep(0.02)\n"
    "Path(sys.argv[3]).write_text(sys.argv[4], encoding='utf-8')\n"
    "lease.__exit__(None, None, None)\n"
)


def start_script(test: unittest.TestCase, script: str, *arguments: str) -> subprocess.Popen:
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(SCRIPT.parent), *arguments],
        stdout=subprocess.PIPE,
        text=True,
    )
    test.addCleanup(process.wait, 60)
    test.addCleanup(process.kill)
    test.addCleanup(process.stdout.close)
    test.assertEqual(process.stdout.readline().strip(), "held")
    return process


# A shared reader of `dep` whose build, once the run's own command signals,
# rewrites a recorded dependency file in place: it opens the file with no
# read sharing, which is how rustc's rewrite makes a concurrent hash fail
# with PermissionError on Windows, and holds it past the run's recording.
IN_PLACE_REWRITER = (
    "import ctypes, sys, time\n"
    "from ctypes import wintypes\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': 'in-place-rewriter', 'revision': 'r'}, 600, mode='shared')\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "trigger = Path(sys.argv[4])\n"
    "while not trigger.exists():\n"
    "    time.sleep(0.01)\n"
    "kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)\n"
    "kernel32.CreateFileW.restype = wintypes.HANDLE\n"
    "handle = kernel32.CreateFileW(sys.argv[3], 0xC0000000, 0, None, 3, 0x80, None)\n"
    "assert handle != wintypes.HANDLE(-1).value, ctypes.get_last_error()\n"
    "Path(str(trigger) + '.ack').write_text('writing', encoding='utf-8')\n"
    "time.sleep(3)\n"
    "kernel32.CloseHandle(handle)\n"
    "lease.__exit__(None, None, None)\n"
)


# A shared reader of `dep` whose build, once the run's own command signals,
# rewrites a named dependency file while the run re-hashes it: it holds the
# file with no read sharing while it writes the new bytes in chunks, as
# rustc's in-place rewrite does.
PEER_REWRITER = (
    "import ctypes, sys, time\n"
    "from ctypes import wintypes\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': 'peer-rewriter', 'revision': 'r'}, 600, mode='shared')\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "target, trigger = Path(sys.argv[3]), Path(sys.argv[4])\n"
    "while not trigger.exists():\n"
    "    time.sleep(0.01)\n"
    "kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)\n"
    "kernel32.CreateFileW.restype = wintypes.HANDLE\n"
    "kernel32.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_char_p, wintypes.DWORD,"
    " ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]\n"
    "handle = kernel32.CreateFileW(str(target), 0x40000000, 0, None, 2, 0x80, None)\n"
    "assert handle != wintypes.HANDLE(-1).value, ctypes.get_last_error()\n"
    "Path(str(trigger) + '.ack').write_text('writing', encoding='utf-8')\n"
    "written = wintypes.DWORD()\n"
    "for chunk in range(10):\n"
    "    kernel32.WriteFile(handle, b'rebuilt-%d;' % chunk, 10, ctypes.byref(written), None)\n"
    "    time.sleep(0.05)\n"
    "kernel32.CloseHandle(handle)\n"
    "lease.__exit__(None, None, None)\n"
)


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
            "    Path(mutate).write_text('changed during build\\n', encoding='utf-8')\n"
            "trigger = os.environ.get('PEER_TRIGGER')\n"
            "if trigger:\n"
            "    import time\n"
            "    Path(trigger).write_text('go', encoding='utf-8')\n"
            "    while not Path(trigger + '.ack').exists():\n"
            "        time.sleep(0.01)\n",
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

    def test_the_same_revision_at_another_root_reuses_and_cleans_nothing(self) -> None:
        """Each pre-push run exports the pushed revision to a new temporary path.

        A record keyed on that path was stale on every run, so every push
        cleaned the whole non-registry closure (101 packages for kwavers) and
        re-pushing one sha cleaned again. The revision decides, not the path.
        """
        init_repo(self.root, "fn main() {}\n")
        first_export = self.base / "export-1" / "member"
        second_export = self.base / "export-2" / "member"
        revision = gate_export(self.root, first_export)
        self.assertEqual(gate_export(self.root, second_export), revision)
        first = self.build(root=first_export, source_token="same")
        self.assertEqual(first.status, "rebuilt")
        self.clean_log.unlink()
        second = self.build(root=second_export, source_token="same")
        self.assertEqual(second.status, "reused")
        self.assertFalse(second.cleaned)
        self.assertFalse(self.clean_log.exists())
        record = json.loads(second.record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["source"]["revision"], revision)
        self.assertEqual(record["source"]["root"], second_export.resolve().as_posix())

    def test_a_fresh_gate_export_is_identified_without_rehashing_it(self) -> None:
        """The export's index carries stat data, so `git diff HEAD` compares
        stats: a read-tree index without it re-hashed kwavers for 348 s."""
        init_repo(self.root, "fn main() {}\n")
        bulk = self.root / "data"
        bulk.mkdir()
        for index in range(2000):
            (bulk / f"part-{index:04}.txt").write_text(f"{index}\n" * 64, encoding="utf-8")
        git(self.root, "add", "data")
        git(self.root, "commit", "-qm", "bulk")
        export = self.base / "export" / "member"
        revision = gate_export(self.root, export)
        calls: list[tuple[str, ...]] = []
        real_git = build_source._git

        def recording_git(root: Path, *arguments: str) -> bytes:
            calls.append(arguments)
            return real_git(root, *arguments)

        with patch.object(build_source, "_git", side_effect=recording_git):
            started = time.monotonic()
            found = build_source.source_identity(export)
            elapsed = time.monotonic() - started
        self.assertIn("diff", [arguments[0] for arguments in calls])
        self.assertEqual(found.revision, revision)
        self.assertFalse(found.dirty)
        self.assertLess(elapsed, 30.0)

    def test_an_edited_export_is_dirty_whatever_its_index_holds(self) -> None:
        """An index read from `HEAD` and never stat'ed proves nothing about
        the files: a modified file and a deleted one are still dirty."""
        init_repo(self.root, "fn main() {}\n")
        export = self.base / "export" / "member"
        revision = gate_export(self.root, export)
        git(export, "read-tree", "HEAD")
        (export / "src/lib.rs").write_text("fn main() { edited(); }\n", encoding="utf-8")
        (export / "Cargo.lock").unlink()
        found = build_source.source_identity(export)
        self.assertEqual(found.revision, revision)
        self.assertTrue(found.dirty)

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

    def dependency_build(
        self,
        source_token: str,
        wait: float = 0,
        discover: bool = False,
        environment: dict[str, str] | None = None,
        clean: bool = True,
        snapshot: dict[str, object] | None = None,
    ) -> identity.BuildResult:
        """Build `demo`, whose clean closure holds a path dependency `dep`."""
        snapshot = snapshot or {
            "root": "demo",
            "packages": [],
            "edges": [],
            "clean_packages": ["demo", "dep"],
            "digest": "dependency-digest",
        }
        owners = {"demo": frozenset({"demo"}), "dep": frozenset({"dep"})}
        with (
            patch.object(identity, "_dependency_data", return_value=snapshot),
            patch.object(artifacts, "_workspace_artifact_owners", return_value=owners),
            patch.object(identity, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {
                    "ARTIFACT": str(self.artifact),
                    "SOURCE_TOKEN": source_token,
                    "CLEAN_LOG": str(self.clean_log),
                    **(environment or {}),
                },
            ),
        ):
            return identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                "demo",
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=() if discover else [self.artifact],
                clean_command=[sys.executable, str(self.clean_script)] if clean else None,
                lease_wait_seconds=wait,
            )

    def dep_lock(self, package: str = "dep") -> Path:
        return package_target_lease_path(package, identity._canonical(self.target))

    def test_shared_readers_of_a_built_dependency_proceed_together(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.assertEqual(self.dependency_build("first").status, "rebuilt")
        start_holder(self, self.dep_lock(), SHARED, 60)
        self.clean_log.unlink(missing_ok=True)
        self.assertEqual(self.dependency_build("first").status, "reused")
        self.assertFalse(self.clean_log.exists())

    def test_a_shared_reader_blocks_cleaning_its_dependency(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        self.assertEqual(self.dependency_build("first").status, "rebuilt")
        self.artifact.write_text("changed elsewhere", encoding="utf-8")
        start_holder(self, self.dep_lock(), SHARED, 60)
        self.clean_log.unlink(missing_ok=True)
        with self.assertRaises(identity.IdentityError) as caught:
            self.dependency_build("intruder")
        self.assertIn("holder-root", str(caught.exception))
        self.assertFalse(self.clean_log.exists())
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "changed elsewhere")

    def test_a_reader_writing_new_variants_does_not_tear_another_readers_check(self) -> None:
        # Cargo can write new variants of a dependency under a shared lease.
        # A reader compares only the files its record names, so a variant
        # written, even half written, beside them neither makes it stale
        # (which would need the exclusive lease the writer blocks) nor fails
        # its hash.
        init_repo(self.root, "fn main() {}\n")
        deps = self.artifact.parent
        (deps / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.assertEqual(self.dependency_build("first", discover=True).status, "rebuilt")
        start_script(self, VARIANT_WRITER, str(self.dep_lock()), str(deps), "6")
        self.clean_log.unlink(missing_ok=True)
        end = time.monotonic() + 4
        rounds = 0
        while time.monotonic() < end:
            self.assertEqual(self.dependency_build("first", wait=2, discover=True).status, "reused")
            rounds += 1
        self.assertGreater(rounds, 2)
        self.assertFalse(self.clean_log.exists())

    @unittest.skipUnless(os.name == "nt", "only Windows refuses reads during a rewrite")
    def rewritten_during_the_rehash(self, script: str, *arguments: str) -> dict[str, str]:
        """Record `dep` while a peer rewrites its named file; return the recorded digests."""
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        self.assertEqual(self.dependency_build("first", discover=True).status, "rebuilt")
        trigger = self.base / "rewrite"
        start_script(self, script, str(self.dep_lock()), str(recorded), str(trigger), *arguments)
        result = self.dependency_build(
            "first", wait=10, discover=True, environment={"PEER_TRIGGER": str(trigger)}
        )
        self.assertEqual(result.status, "reused")
        return json.loads(result.record_path.read_text(encoding="utf-8"))["artifact"]["files"]

    @unittest.skipUnless(os.name == "nt", "only Windows refuses reads during a rewrite")
    def test_a_rewrite_that_refuses_reads_for_part_of_the_window_is_recorded_settled(self) -> None:
        files = self.rewritten_during_the_rehash(PEER_REWRITER)
        final = b"".join(b"rebuilt-%d;" % chunk for chunk in range(10))
        self.assertEqual(
            files["debug/deps/libdep-0ecdeded.rlib"], hashlib.sha256(final).hexdigest()
        )

    def test_a_file_that_never_reads_the_same_twice_is_recorded_unverified(self) -> None:
        # Every read of the named file after the command gives a new digest,
        # as a file rewritten throughout the budget does; a real rewriter
        # cannot be timed to defeat every pair of reads.
        init_repo(self.root, "fn main() {}\n")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.assertEqual(self.dependency_build("first", discover=True).status, "rebuilt")
        reads = iter(range(1_000_000))
        settle = artifacts.settled_digest

        def unsettled(path, deadline_ns):
            if path.name != "libdep-0ecdeded.rlib":
                return settle(path, deadline_ns)
            with patch.object(artifacts, "_file_digest", side_effect=lambda _: f"read-{next(reads)}"):
                return settle(path, deadline_ns)

        with patch.object(identity, "settled_digest", side_effect=unsettled):
            result = self.dependency_build("first", wait=3, discover=True)
        files = json.loads(result.record_path.read_text(encoding="utf-8"))["artifact"]["files"]
        self.assertEqual(files["debug/deps/libdep-0ecdeded.rlib"], artifacts.UNVERIFIED)
        self.assertGreater(next(reads), 2)

    def test_an_unverified_file_cleans_only_its_package(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        first = self.dependency_build("first", discover=True)
        record = json.loads(first.record_path.read_text(encoding="utf-8"))
        record["artifact"]["files"]["debug/deps/libdep-0ecdeded.rlib"] = artifacts.UNVERIFIED
        record["artifact"]["digest"] = artifacts.artifact_digest(record["artifact"]["files"])
        first.record_path.write_text(json.dumps(record), encoding="utf-8")
        self.assertEqual(self.cleaned_packages("first"), ["dep"])

    @unittest.skipUnless(os.name == "nt", "only Windows refuses reads during a rewrite")
    def test_a_file_that_cannot_be_read_at_all_keeps_its_verified_digest(self) -> None:
        # Cargo rewrites a dependency's recorded files under the same name
        # whenever it rebuilds it. A reader whose re-hash met a rewrite that
        # never let it read failed a build that had succeeded ("cannot hash
        # artifact"); it now keeps the digest verified before the command.
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        first = self.dependency_build("first", discover=True)
        self.assertEqual(first.status, "rebuilt")
        verified = json.loads(first.record_path.read_text(encoding="utf-8"))["artifact"]["files"]
        trigger = self.base / "rewrite"
        start_script(self, IN_PLACE_REWRITER, str(self.dep_lock()), str(recorded), str(trigger))
        result = self.dependency_build(
            "first", wait=2, discover=True, environment={"PEER_TRIGGER": str(trigger)}
        )
        self.assertEqual(result.status, "reused")
        self.assertTrue(Path(f"{trigger}.ack").exists())
        files = json.loads(result.record_path.read_text(encoding="utf-8"))["artifact"]["files"]
        self.assertEqual(
            files["debug/deps/libdep-0ecdeded.rlib"], verified["debug/deps/libdep-0ecdeded.rlib"]
        )

    def cleaned_packages(
        self, source_token: str, snapshot: dict[str, object] | None = None
    ) -> list[str]:
        """Rebuild through `cargo clean -p`, recording the packages instead of running Cargo."""
        packages: list[str] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if list(command[1:3]) == ["clean", "-p"]:
                packages.extend(command[i + 1] for i, value in enumerate(command) if value == "-p")
                return
            run_checked(command, cwd, environment)

        with patch.object(identity, "_run_checked", side_effect=recording):
            self.dependency_build(source_token, discover=True, clean=False, snapshot=snapshot)
        return sorted(packages)

    def test_changed_dependency_bytes_clean_only_that_dependency(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        recorded.write_bytes(b"rebuilt from another path")
        self.assertEqual(self.cleaned_packages("first"), ["dep"])

    def test_a_changed_source_cleans_its_package_and_changed_dependencies(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        (self.root / "src" / "lib.rs").write_text("fn main() { changed(); }\n", encoding="utf-8")
        recorded.write_bytes(b"rebuilt from another path")
        self.assertEqual(self.cleaned_packages("second"), ["demo", "dep"])

    def test_a_changed_source_alone_cleans_only_its_own_package(self) -> None:
        # With the dependency closure unchanged, a new source for `demo`
        # cannot alter `dep`'s artifacts, so `dep` is neither cleaned nor
        # rebuilt. Cleaning the closure here rebuilt every first-party
        # dependency on each push.
        init_repo(self.root, "fn main() {}\n")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        (self.root / "src" / "lib.rs").write_text("fn main() { changed(); }\n", encoding="utf-8")
        self.assertEqual(self.cleaned_packages("second"), ["demo"])

    def test_a_changed_source_alone_reads_its_dependencies_shared(self) -> None:
        # A peer holding `dep` shared does not block a run whose only change
        # is its own source: the run holds `dep` shared too. Taking the whole
        # closure exclusive on every source change serialized every gate that
        # shared a dependency.
        init_repo(self.root, "fn main() {}\n")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        (self.root / "src" / "lib.rs").write_text("fn main() { changed(); }\n", encoding="utf-8")
        start_holder(self, self.dep_lock(), SHARED, 60)
        self.assertEqual(self.cleaned_packages("second"), ["demo"])

    def path_and_git_snapshot(self, revision: str) -> dict[str, object]:
        """`demo` (a path record whose identity moves with its own source)
        depending on `dep` (a git record whose content is independent of it).

        `packages: []` never exercised the narrowing at all: with no path
        record in the snapshot, a source-only change always compared the
        whole `dependencies` dict equal, matched, and never reached
        `_narrowed_clean`. A first-party dependency patched to a local
        checkout under the development overlay is reported by cargo as a
        path record too, so a real dependency snapshot always carries at
        least the run's own root package as one; this fixture is the
        minimal one that lets a source-only change disagree on a path
        record while a git dependency's record, unaffected by it, stays
        byte-identical. `revision` must be a real commit of `self.root`:
        the identity-only narrowing path now proves its safety with an
        actual `git diff` between the recorded and current revisions, so a
        fabricated revision string is correctly refused as unresolvable.
        """
        value = {
            "root": "demo",
            "packages": [
                {
                    "id": "workspace:.#demo@0.1.0",
                    "name": "demo",
                    "version": "0.1.0",
                    "features": [],
                    "kind": "path",
                    "identity": {"revision": revision, "tree_digest": f"tree-{revision}", "dirty": False},
                },
                {
                    "id": "git+https://example.invalid/dep#0.1.0",
                    "name": "dep",
                    "version": "0.1.0",
                    "features": [],
                    "kind": "git",
                    "source": "git+https://example.invalid/dep#0.1.0",
                    "content_digest": "stable-content",
                },
            ],
            "edges": [],
            "clean_packages": ["demo", "dep"],
        }
        value["digest"] = f"digest-{revision}"
        return value

    def commit_source_change(self, text: str, message: str) -> str:
        (self.root / "src" / "lib.rs").write_text(text, encoding="utf-8")
        git(self.root, "commit", "-qam", message)
        return git(self.root, "rev-parse", "HEAD")

    def test_a_changed_path_record_alone_cleans_only_its_own_package(self) -> None:
        # `demo`'s own path record moves with its source; `dep`'s git record
        # does not. Comparing the whole snapshot for equality treated the
        # differing root record as reaching the closure and cleaned `dep` on
        # every push, serializing every gate sharing a first-party
        # dependency the overlay patches in as a path record.
        init_repo(self.root, "fn main() {}\n")
        first_revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=self.path_and_git_snapshot(first_revision))
        second_revision = self.commit_source_change(
            "fn main() { changed(); }\n", "change source"
        )
        self.assertEqual(
            self.cleaned_packages("second", snapshot=self.path_and_git_snapshot(second_revision)),
            ["demo"],
        )

    def test_a_changed_path_record_alone_reads_the_git_dependency_shared(self) -> None:
        # The run holding `dep` shared while cleaning only `demo` proceeds
        # beside a peer that also holds `dep` shared; the whole-snapshot
        # comparison this replaces held `dep` exclusive and would refuse
        # here.
        init_repo(self.root, "fn main() {}\n")
        first_revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=self.path_and_git_snapshot(first_revision))
        second_revision = self.commit_source_change(
            "fn main() { changed(); }\n", "change source"
        )
        start_holder(self, self.dep_lock(), SHARED, 60)
        self.assertEqual(
            self.cleaned_packages("second", snapshot=self.path_and_git_snapshot(second_revision)),
            ["demo"],
        )

    def test_a_repeat_push_after_a_narrowed_push_reuses_the_record(self) -> None:
        # A narrowed clean's record must be internally consistent: an
        # identical repeat push (no further change) matches it exactly and
        # reuses, exactly like a repeat of an ordinary whole-closure push.
        init_repo(self.root, "fn main() {}\n")
        first_revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=self.path_and_git_snapshot(first_revision))
        second_revision = self.commit_source_change(
            "fn main() { changed(); }\n", "change source"
        )
        second_snapshot = self.path_and_git_snapshot(second_revision)
        self.assertEqual(self.cleaned_packages("second", snapshot=second_snapshot), ["demo"])
        third = self.dependency_build("second", discover=True, snapshot=second_snapshot)
        self.assertEqual(third.status, "reused")
        self.assertFalse(third.cleaned)

    def test_a_path_dependency_feature_change_forces_the_whole_closure(self) -> None:
        # `dep`'s own record differs only in `features` (feature unification
        # from an edit to a different manifest, e.g. enabling a feature on
        # it from the root's Cargo.toml): a real-Cargo counterexample showed
        # this can leave a sibling's rebuilt variant unrecorded when
        # narrowed, so only `identity` may differ for a path record.
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")

        def snapshot(features: list[str]) -> dict[str, object]:
            value = {
                "root": "demo",
                "packages": [
                    {
                        "id": "workspace:.#demo@0.1.0",
                        "name": "demo",
                        "version": "0.1.0",
                        "features": [],
                        "kind": "path",
                        "identity": {"revision": revision, "tree_digest": "tree", "dirty": False},
                    },
                    {
                        "id": "path+file:///dep#0.1.0",
                        "name": "dep",
                        "version": "0.1.0",
                        "features": features,
                        "kind": "path",
                        "identity": {"revision": "dep-revision", "tree_digest": "dep-tree", "dirty": False},
                    },
                ],
                "edges": [],
                "clean_packages": ["demo", "dep"],
            }
            value["digest"] = f"digest-{features}"
            return value

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=snapshot([]))
        self.assertEqual(
            self.cleaned_packages("second", snapshot=snapshot(["f"])),
            ["demo", "dep"],
        )

    def test_a_git_dependency_content_change_forces_the_whole_closure(self) -> None:
        # `dep`'s content changed (a new commit at the pinned git ref) while
        # `demo`'s own identity did not: the disagreement is not confined to
        # a path record at all, so the whole closure cleans exactly as
        # before this change.
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")

        def snapshot(content_digest: str) -> dict[str, object]:
            value = {
                "root": "demo",
                "packages": [
                    {
                        "id": "workspace:.#demo@0.1.0",
                        "name": "demo",
                        "version": "0.1.0",
                        "features": [],
                        "kind": "path",
                        "identity": {"revision": revision, "tree_digest": "tree", "dirty": False},
                    },
                    {
                        "id": "git+https://example.invalid/dep#0.1.0",
                        "name": "dep",
                        "version": "0.1.0",
                        "features": [],
                        "kind": "git",
                        "source": "git+https://example.invalid/dep#0.1.0",
                        "content_digest": content_digest,
                    },
                ],
                "edges": [],
                "clean_packages": ["demo", "dep"],
            }
            value["digest"] = f"digest-{content_digest}"
            return value

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=snapshot("v1"))
        self.assertEqual(
            self.cleaned_packages("second", snapshot=snapshot("v2")),
            ["demo", "dep"],
        )

    def demo_and_git_dep_records(self, revision: str) -> tuple[dict[str, object], dict[str, object]]:
        return (
            {
                "id": "workspace:.#demo@0.1.0",
                "name": "demo",
                "version": "0.1.0",
                "features": [],
                "kind": "path",
                "identity": {"revision": revision, "tree_digest": "tree", "dirty": False},
            },
            {
                "id": "git+https://example.invalid/dep#0.1.0",
                "name": "dep",
                "version": "0.1.0",
                "features": [],
                "kind": "git",
                "source": "git+https://example.invalid/dep#0.1.0",
                "content_digest": "stable-content",
            },
        )

    def test_a_changed_root_package_id_forces_the_whole_closure(self) -> None:
        # A snapshot's own `root` field names the package the closure is
        # rooted at; a build whose record disagrees there is not describing
        # the same package graph at all, whatever its path records show. A
        # source edit accompanies the id change so a guard-less run would
        # otherwise find a legitimate, narrowable `demo` difference: without
        # it, both the guarded and unguarded runs land on the same "nothing
        # attributable" `None`, and the test cannot tell them apart.
        init_repo(self.root, "fn main() {}\n")
        first_revision = git(self.root, "rev-parse", "HEAD")
        _, dep = self.demo_and_git_dep_records(first_revision)

        def snapshot(root: str, revision: str) -> dict[str, object]:
            demo, _ = self.demo_and_git_dep_records(revision)
            value = {
                "root": root,
                "packages": [demo, dep],
                "edges": [],
                "clean_packages": ["demo", "dep"],
            }
            value["digest"] = f"digest-{root}-{revision}"
            return value

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build(
            "first", discover=True, snapshot=snapshot("workspace:.#demo@0.1.0", first_revision)
        )
        second_revision = self.commit_source_change("fn main() { changed(); }\n", "change source")
        self.assertEqual(
            self.cleaned_packages(
                "second", snapshot=snapshot("workspace:.#demo@0.2.0", second_revision)
            ),
            ["demo", "dep"],
        )

    def test_a_changed_clean_package_set_forces_the_whole_closure(self) -> None:
        # `clean_packages` is the closure narrowing may hold exclusive at
        # most; a build whose record disagrees there describes a different
        # closure, never a subset safe to narrow within. `demo`'s source
        # also changes so an unguarded run would otherwise narrow to a
        # legitimate `{"demo"}`, not fall out to `None` for unrelated
        # reasons the way an all-else-unchanged fixture would.
        init_repo(self.root, "fn main() {}\n")
        first_revision = git(self.root, "rev-parse", "HEAD")
        _, dep = self.demo_and_git_dep_records(first_revision)

        def snapshot(clean_packages: list[str], revision: str) -> dict[str, object]:
            demo, _ = self.demo_and_git_dep_records(revision)
            value = {
                "root": "workspace:.#demo@0.1.0",
                "packages": [demo, dep],
                "edges": [],
                "clean_packages": clean_packages,
            }
            value["digest"] = f"digest-{clean_packages}-{revision}"
            return value

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build(
            "first", discover=True, snapshot=snapshot(["demo", "dep"], first_revision)
        )
        second_revision = self.commit_source_change("fn main() { changed(); }\n", "change source")
        self.assertEqual(
            self.cleaned_packages(
                "second", snapshot=snapshot(["demo", "dep", "extra"], second_revision)
            ),
            ["demo", "dep", "extra"],
        )

    def test_a_changed_package_id_set_forces_the_whole_closure(self) -> None:
        # A package added to (or removed from) the reachable graph is a
        # structural disagreement the per-record loop cannot classify: it
        # has no prior record to compare against at all. `demo`'s source
        # also changes so an unguarded run's loop -- which only ever visits
        # `existing`'s ids -- would otherwise narrow to a legitimate
        # `{"demo"}` while silently never accounting for `extra` at all.
        init_repo(self.root, "fn main() {}\n")
        first_revision = git(self.root, "rev-parse", "HEAD")
        _, dep = self.demo_and_git_dep_records(first_revision)
        extra = {
            "id": "git+https://example.invalid/extra#0.1.0",
            "name": "extra",
            "version": "0.1.0",
            "features": [],
            "kind": "git",
            "source": "git+https://example.invalid/extra#0.1.0",
            "content_digest": "extra-content",
        }

        def snapshot(include_extra: bool, revision: str) -> dict[str, object]:
            demo, _ = self.demo_and_git_dep_records(revision)
            packages = [demo, dep, extra] if include_extra else [demo, dep]
            value = {
                "root": "workspace:.#demo@0.1.0",
                "packages": packages,
                "edges": [],
                # Held constant across both calls so only the package id set
                # -- never `clean_packages` (M4's own guard) -- differs.
                "clean_packages": ["demo", "dep", "extra"],
            }
            value["digest"] = f"digest-{include_extra}-{revision}"
            return value

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=snapshot(False, first_revision))
        second_revision = self.commit_source_change("fn main() { changed(); }\n", "change source")
        self.assertEqual(
            self.cleaned_packages("second", snapshot=snapshot(True, second_revision)),
            ["demo", "dep", "extra"],
        )

    def test_the_widen_loop_reaches_packages_the_first_read_missed(self) -> None:
        # `_narrowed_clean`'s first read may name fewer packages than a
        # second read reveals (a peer finishing a build between reads, or
        # here, a staged mock standing in for that race): the loop must
        # keep widening until it converges, never commit to the first guess.
        init_repo(self.root, "fn main() {}\n")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        (self.root / "src" / "lib.rs").write_text("fn main() { changed(); }\n", encoding="utf-8")
        calls = {"n": 0}

        def staged(*args: object, **kwargs: object) -> tuple[str, ...]:
            calls["n"] += 1
            return ("demo",) if calls["n"] == 1 else ("demo", "dep")

        with patch.object(identity, "_narrowed_clean", side_effect=staged):
            cleaned = self.cleaned_packages("second")
        self.assertEqual(cleaned, ["demo", "dep"])
        self.assertGreaterEqual(calls["n"], 2)

    def test_a_narrowed_clean_discovers_only_the_packages_it_cleaned(self) -> None:
        # After a narrowed clean, artifact recording must discover only the
        # packages this run held exclusive -- never the whole closure, which
        # would walk a dependency directory a peer holds only shared.
        init_repo(self.root, "fn main() {}\n")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        (self.root / "src" / "lib.rs").write_text("fn main() { changed(); }\n", encoding="utf-8")
        related_packages_seen: list[tuple[str, ...]] = []
        real_discover = identity.discover_artifacts
        run_checked = identity._run_checked

        def spy_discover(*args: object, **kwargs: object):
            related = args[6] if len(args) > 6 else kwargs.get("related_packages", ())
            related_packages_seen.append(tuple(related))
            return real_discover(*args, **kwargs)

        def skip_real_clean(command, cwd, environment):
            # A real `cargo clean -p demo` here can rewrite the fixture's
            # stub Cargo.lock, which the source-identity re-check at the
            # end of `run_build` then reads as a change during the build;
            # `cleaned_packages` avoids this the same way.
            if list(command[1:3]) == ["clean", "-p"]:
                return
            run_checked(command, cwd, environment)

        with (
            patch.object(identity, "discover_artifacts", side_effect=spy_discover),
            patch.object(identity, "_run_checked", side_effect=skip_real_clean),
        ):
            result = self.dependency_build("second", discover=True, clean=False)
        self.assertEqual(result.status, "rebuilt")
        self.assertTrue(related_packages_seen)
        self.assertNotIn("dep", related_packages_seen[-1])

    def test_a_sibling_repository_identity_change_cleans_that_package(self) -> None:
        # `dep`'s own identity changed (its repository moved) while
        # `demo`'s did not: `_narrowed_clean` must still clean `dep`,
        # attributed through the path-record union -- `changed_packages`
        # alone has no recorded artifact-byte difference to find yet, since
        # `dep` has not been rebuilt from the new revision at all.
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")
        dep_repo = self.base / "dep-repo"
        dep_repo.mkdir()
        (dep_repo / "file.txt").write_text("a\n", encoding="utf-8")
        git(dep_repo, "init", "-q")
        git(dep_repo, "config", "user.name", "t")
        git(dep_repo, "config", "user.email", "t@e.invalid")
        git(dep_repo, "add", ".")
        git(dep_repo, "commit", "-q", "-m", "dep a")
        dep_revision_a = git(dep_repo, "rev-parse", "HEAD")

        def snapshot(dep_revision: str) -> dict[str, object]:
            value = {
                "root": "demo",
                "packages": [
                    {
                        "id": "workspace:.#demo@0.1.0",
                        "name": "demo",
                        "version": "0.1.0",
                        "features": [],
                        "kind": "path",
                        "identity": {"revision": revision, "tree_digest": "tree", "dirty": False},
                    },
                    {
                        "id": f"path+file://{dep_repo.as_posix()}#dep@0.1.0",
                        "name": "dep",
                        "version": "0.1.0",
                        "features": [],
                        "kind": "path",
                        "identity": {
                            "revision": dep_revision,
                            "tree_digest": f"dep-tree-{dep_revision}",
                            "dirty": False,
                        },
                    },
                ],
                "edges": [],
                "clean_packages": ["demo", "dep"],
            }
            value["digest"] = f"digest-{dep_revision}"
            return value

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=snapshot(dep_revision_a))
        (dep_repo / "file.txt").write_text("b\n", encoding="utf-8")
        git(dep_repo, "commit", "-qam", "dep b")
        dep_revision_b = git(dep_repo, "rev-parse", "HEAD")
        self.assertEqual(
            self.cleaned_packages("first", snapshot=snapshot(dep_revision_b)),
            ["dep"],
        )

    def test_a_root_manifest_change_forces_the_whole_closure(self) -> None:
        # `demo`'s own repository changes only its Cargo.toml (a profile
        # edit here, a feature or dependency edit in general): a real-Cargo
        # counterexample showed this can silently reconfigure how a git
        # dependency compiles without that dependency's own recorded
        # content moving at all, so an identity-only change is safe to
        # narrow on only when its actual diff touches no build-config file.
        init_repo(self.root, "fn main() {}\n")
        first_revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=self.path_and_git_snapshot(first_revision))
        manifest = self.root / "Cargo.toml"
        manifest.write_text(manifest.read_text(encoding="utf-8") + "\n[profile.dev]\nopt-level = 1\n", encoding="utf-8")
        git(self.root, "add", "Cargo.toml")
        git(self.root, "commit", "-qm", "profile opt-level 1")
        second_revision = git(self.root, "rev-parse", "HEAD")
        self.assertEqual(
            self.cleaned_packages("second", snapshot=self.path_and_git_snapshot(second_revision)),
            ["demo", "dep"],
        )

    def test_a_stale_run_rechecks_after_taking_its_leases_exclusive(self) -> None:
        # Between releasing its shared leases and taking them exclusive, a
        # peer rebuilt the dependency to match the record: no clean is due.
        init_repo(self.root, "fn main() {}\n")
        self.assertEqual(self.dependency_build("first").status, "rebuilt")
        self.artifact.write_text("tampered", encoding="utf-8")
        start_script(
            self, REBUILDING_READER, str(self.dep_lock()), str(self.artifact), "first"
        )
        self.clean_log.unlink(missing_ok=True)
        result = self.dependency_build("first", wait=30)
        self.assertEqual(result.status, "reused")
        self.assertFalse(self.clean_log.exists())

    def test_the_wait_bound_covers_every_lease_of_a_run(self) -> None:
        # `demo` frees after 2 s and `dep` never: with a 3 s bound per lease
        # the run would wait 5 s, but the bound is for the run.
        init_repo(self.root, "fn main() {}\n")
        start_holder(self, self.dep_lock("demo"), EXCLUSIVE, 2)
        start_holder(self, self.dep_lock("dep"), EXCLUSIVE, 60)
        started = time.monotonic()
        with self.assertRaises(identity.IdentityError) as caught:
            self.dependency_build("first", wait=3)
        elapsed = time.monotonic() - started
        self.assertIn("after waiting 3 s", str(caught.exception))
        self.assertGreaterEqual(elapsed, 2.9)
        self.assertLess(elapsed, 4.2)

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

    def test_a_relative_config_argument_resolves_against_the_execution_root(self) -> None:
        # Cargo resolves a relative `--config <path>` against its own `cwd`
        # (the execution root `--command-cwd` names), never against this
        # process's own working directory -- which the pre-push hook always
        # leaves at the checkout, not the export Cargo actually builds in.
        init_repo(self.root, "fn main() {}\n")
        execution_root = self.base / "execution"
        execution_root.mkdir()
        config = execution_root / "ci.toml"
        config.write_text("[profile.dev]\nopt-level = 0\n", encoding="utf-8")
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        previous_cwd = os.getcwd()
        os.chdir(elsewhere)
        try:
            with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
                first = identity.build_spec(
                    self.root, "demo", self.target, "debug", "host", "",
                    command=["cargo", "check", "--config", "ci.toml"],
                    execution_root=execution_root,
                )
                config.write_text("[profile.dev]\nopt-level = 3\n", encoding="utf-8")
                second = identity.build_spec(
                    self.root, "demo", self.target, "debug", "host", "",
                    command=["cargo", "check", "--config", "ci.toml"],
                    execution_root=execution_root,
                )
        finally:
            os.chdir(previous_cwd)
        self.assertNotEqual(first.cargo_config_digest, second.cargo_config_digest)

    def test_a_command_env_prefix_changes_the_record_scope(self) -> None:
        # `env RUSTFLAGS=... cargo build` sets a variable no ambient
        # `os.environ` snapshot carries; only parsing the leading `env`
        # prefix lets the record see a *compile-affecting* variable move.
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            first = identity.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTFLAGS=-C debuginfo=0", "cargo", "build"],
            )
            second = identity.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTFLAGS=-C debuginfo=2", "cargo", "build"],
            )
        self.assertNotEqual(first.environment_digest, second.environment_digest)

    def test_cargo_build_prefixed_rustdoc_inputs_are_also_excluded(self) -> None:
        # `CARGO_BUILD_RUSTDOCFLAGS`/`CARGO_BUILD_RUSTDOC` are the
        # `CARGO_BUILD_*`-prefixed spellings of the rustdoc-only inputs
        # excluded by their bare names; the prefix match must not let them
        # back in.
        base = build_source.environment_digest({})
        for key in ("CARGO_BUILD_RUSTDOCFLAGS", "CARGO_BUILD_RUSTDOC"):
            with self.subTest(key=key):
                self.assertEqual(build_source.environment_digest({key: "x"}), base)
        self.assertNotEqual(build_source.environment_digest({"CARGO_BUILD_RUSTFLAGS": "x"}), base)

    def test_an_inline_rustdocflags_does_not_split_a_shared_record(self) -> None:
        # The pre-push hook runs clippy, nextest, and `env RUSTDOCFLAGS=...
        # cargo doc` under one shared `command_key` for one package, so
        # `_sibling_matches` (which ignores only the command key) expects
        # them to compare equal. The record does name doc-unit fingerprint
        # files (`doc-lib-*`/`output-doc-lib-*` alongside the compile-unit
        # ones in a package's `.fingerprint/<pkg>-<hash>/` directory,
        # confirmed by a real run), so excluding a rustdoc-only flag here
        # is not "rustdoc's output is untracked" -- it is that the flag is
        # not a pre-emptive build dimension: a run whose record otherwise
        # matches still re-verifies every named file's current bytes, and
        # rustdoc rewriting its own fingerprint files under a changed flag
        # is exactly such a mismatch, cleaning on the next run rather than
        # silently accepting a stale doc artifact. Splitting the shared
        # record here made a real three-step push clean the whole closure
        # on every push instead of once.
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            clippy = identity.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["cargo", "clippy"], command_key="shared",
            )
            doc_a = identity.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTDOCFLAGS=-D warnings", "cargo", "doc"], command_key="shared",
            )
            doc_b = identity.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTDOCFLAGS=--cfg docsrs", "cargo", "doc"], command_key="shared",
            )
        self.assertEqual(clippy.environment_digest, doc_a.environment_digest)
        self.assertEqual(doc_a.environment_digest, doc_b.environment_digest)
        self.assertEqual(identity.record_path(clippy), identity.record_path(doc_a))

    def test_an_included_config_file_change_is_detected(self) -> None:
        # Cargo 1.97 stable accepts `include` as a list of strings or a list
        # of tables (each optionally carrying `optional = true`) -- never a
        # bare string, which Cargo itself rejects ("expected a list of
        # strings or a list of tables"). Both accepted forms are exercised
        # here; either resolves relative to the file that names it and
        # merges the included file's own settings, so an edit confined to
        # the included file changes the build without changing the
        # including file's own bytes at all.
        for include_line, label in (
            ('include = ["included.toml"]\n', "list-of-strings"),
            ('include = [{ path = "included.toml", optional = true }]\n', "list-of-tables"),
        ):
            with self.subTest(label):
                execution_root = self.base / f"execution-{label}"
                (execution_root / ".cargo").mkdir(parents=True)
                included = execution_root / ".cargo" / "included.toml"
                included.write_text("[profile.dev]\nopt-level = 0\n", encoding="utf-8")
                (execution_root / ".cargo" / "config.toml").write_text(
                    include_line, encoding="utf-8"
                )
                first = build_source.cargo_config_digest(execution_root)
                included.write_text("[profile.dev]\nopt-level = 3\n", encoding="utf-8")
                second = build_source.cargo_config_digest(execution_root)
                self.assertNotEqual(first, second)

    def test_a_bare_string_include_is_not_followed(self) -> None:
        # Cargo rejects `include = "path"` outright; this digest must not
        # treat it as a one-element list either, so an edit to the file it
        # would have named goes undetected exactly as Cargo's own refusal
        # to build implies (there is no valid build to compare against).
        execution_root = self.base / "execution-bare-string"
        (execution_root / ".cargo").mkdir(parents=True)
        named = execution_root / ".cargo" / "named.toml"
        named.write_text("[profile.dev]\nopt-level = 0\n", encoding="utf-8")
        (execution_root / ".cargo" / "config.toml").write_text(
            'include = "named.toml"\n', encoding="utf-8"
        )
        first = build_source.cargo_config_digest(execution_root)
        named.write_text("[profile.dev]\nopt-level = 3\n", encoding="utf-8")
        second = build_source.cargo_config_digest(execution_root)
        self.assertEqual(first, second)

    def test_an_inline_config_arguments_include_is_followed(self) -> None:
        # `--config 'include=["x.toml"]'` is inline TOML text with no file
        # of its own; its own `include` resolves against the execution
        # root, matching Cargo's resolution for a command-line `--config`
        # value.
        execution_root = self.base / "execution-inline-include"
        execution_root.mkdir(parents=True)
        included = execution_root / "x.toml"
        included.write_text('[build]\nrustflags = ["--cfg", "foo"]\n', encoding="utf-8")
        arguments = identity._config_arguments(["cargo", "check", "--config", 'include=["x.toml"]'])
        first = build_source.cargo_config_digest(execution_root, arguments)
        included.write_text('[build]\nrustflags = ["--cfg", "bar"]\n', encoding="utf-8")
        second = build_source.cargo_config_digest(execution_root, arguments)
        self.assertNotEqual(first, second)

    def test_an_included_config_cycle_does_not_hang(self) -> None:
        # An included file naming its own includer, directly or through a
        # chain, must not recurse forever.
        execution_root = self.base / "execution-cycle"
        (execution_root / ".cargo").mkdir(parents=True)
        (execution_root / ".cargo" / "config.toml").write_text(
            'include = ["b.toml"]\n', encoding="utf-8"
        )
        (execution_root / ".cargo" / "b.toml").write_text(
            'include = ["config.toml"]\n', encoding="utf-8"
        )
        digest = build_source.cargo_config_digest(execution_root)
        self.assertEqual(len(digest), 64)

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
                package_source.package_source_digest,
            )
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "b"},
                package_source.package_source_digest,
            )
        self.assertNotEqual(first["digest"], second["digest"])
        self.assertEqual(first["clean_packages"], ["demo", "dep"])

    def test_an_artifact_belongs_to_the_target_it_names_exactly(self) -> None:
        """`mnemosyne-memory`'s library is `mnemosyne`, a prefix of
        `mnemosyne_build_util`; a prefix match claimed that artifact twice."""
        owners = {
            "mnemosyne-memory": frozenset({"mnemosyne_memory", "mnemosyne"}),
            "mnemosyne-build-util": frozenset({"mnemosyne_build_util"}),
        }
        cases = {
            "libmnemosyne_build_util-0123456789abcdef.rlib": "mnemosyne-build-util",
            "mnemosyne-build-util-0123456789abcdef": "mnemosyne-build-util",
            "libmnemosyne-0123456789abcdef.rmeta": "mnemosyne-memory",
            "mnemosyne_memory-0123456789abcdef.d": "mnemosyne-memory",
            "libmnemosyne_extra-0123456789abcdef.rlib": None,
        }
        for filename, owner in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(artifacts._artifact_owner(filename, owners, "mnemosyne-build-util"), owner)

    def test_dependency_snapshot_is_independent_of_the_export_path(self) -> None:
        """Cargo spells a path package's ID with its absolute directory."""
        snapshots = []
        for name in ("export-1", "export-2"):
            workspace = (self.base / name / "member").resolve()
            member = workspace / "crates" / "demo"
            member.mkdir(parents=True)
            (member / "Cargo.toml").write_text("[package]\nname = \"demo\"\n", encoding="utf-8")
            helper = workspace / "crates" / "helper"
            helper.mkdir(parents=True)
            (helper / "Cargo.toml").write_text("[package]\nname = \"helper\"\n", encoding="utf-8")
            demo_id = f"path+file:///{member.as_posix()}#demo@0.1.0"
            helper_id = f"path+file:///{helper.as_posix()}#helper@0.1.0"
            metadata = {
                "workspace_root": str(workspace),
                "packages": [
                    {"id": demo_id, "name": "demo", "version": "0.1.0", "source": None,
                     "manifest_path": str(member / "Cargo.toml")},
                    {"id": helper_id, "name": "helper", "version": "0.1.0", "source": None,
                     "manifest_path": str(helper / "Cargo.toml")},
                ],
                "workspace_members": [demo_id, helper_id],
                "resolve": {"nodes": [
                    {"id": demo_id, "deps": [{"pkg": helper_id, "dep_kinds": []}]},
                    {"id": helper_id, "deps": []},
                ]},
            }
            with patch.object(artifacts, "_cargo_metadata", return_value=metadata):
                snapshots.append(artifacts.dependency_snapshot(
                    workspace / "Cargo.toml", "demo", workspace,
                    lambda path: {"revision": "same"},
                    package_source.package_source_digest,
                ))
        self.assertEqual(snapshots[0]["digest"], snapshots[1]["digest"])
        self.assertEqual(snapshots[0]["root"], "workspace:crates/demo#demo@0.1.0")

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
                package_source.package_source_digest,
            )
            source.write_text("pub fn value() -> u8 { 2 }\n", encoding="utf-8")
            second = artifacts.dependency_snapshot(
                self.root / "Cargo.toml",
                "demo",
                self.root,
                lambda path: {"root": path.as_posix(), "revision": "a"},
                package_source.package_source_digest,
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
            patch.object(identity, "recorded_artifact_identity", return_value=artifact_value),
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
        clean_commands = [command for command in commands if list(command[1:2]) == ["clean"]]
        # One walk of the shared target for the whole closure, not one per package.
        self.assertEqual(len(clean_commands), 1, clean_commands)
        packages = [
            clean_commands[0][index + 1]
            for index, argument in enumerate(clean_commands[0])
            if argument == "-p"
        ]
        self.assertEqual(packages, ["demo", "dep"])

    def test_older_record_versions_are_stale(self) -> None:
        # Version 3 predates `cargo_config_digest`: a record at that version
        # is gracefully stale, never a hard failure for the field it cannot
        # have.
        record = self.base / "old-record.json"
        for version in (1, 2, 3):
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


def _clear_readonly_tree(path: Path) -> None:
    """Remove a tree whose entries may be read-only (the gate's exports).

    `shutil.rmtree(onexc=)` is 3.12+ and the hosted runners hold 3.11, so the
    entries are made writable first and removed with the version-agnostic
    plain form.
    """
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        for name in (root, *(os.path.join(root, entry) for entry in dirs + files)):
            os.chmod(name, 0o700)
    shutil.rmtree(path)


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class RepeatedExportPushTestCase(unittest.TestCase):
    """Pushes of one commit, each from a fresh export, as the pre-push gate runs them."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-exports-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.source = self.base / "source"
        for relative, text in {
            "Cargo.toml": '[workspace]\nmembers = ["d", "p"]\nresolver = "2"\n',
            "d/Cargo.toml": '[package]\nname = "d"\nversion = "0.1.0"\nedition = "2021"\n',
            "d/src/lib.rs": "pub fn d() -> u32 {\n    1\n}\n",
            "p/Cargo.toml": '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n\n'
            '[dependencies]\nd = { path = "../d" }\n',
            "p/src/lib.rs": "pub fn p() -> u32 {\n    d::d()\n}\n",
        }.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Atlas test")
        git(self.source, "config", "user.email", "atlas-test@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(self, pushes: int, stable_path: bool) -> list[list[str]]:
        """Build `p` once per push from a fresh copy (fresh mtimes) of the commit.

        Returns, per push, the packages it cleaned. A stable path reuses one
        export directory, as the gate does per member; otherwise every push
        gets a new one.
        """
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if list(command[1:3]) == ["clean", "-p"]:
                cleaned[-1].extend(command[i + 1] for i, value in enumerate(command) if value == "-p")
            run_checked(command, cwd, environment)

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_run_checked", side_effect=recording),
        ):
            for push in range(pushes):
                export = self.base / ("export" if stable_path else f"export-{push}")
                if export.exists():
                    _clear_readonly_tree(export)
                shutil.copytree(self.source, export, copy_function=shutil.copy)
                cleaned.append([])
                identity.run_build(
                    export,
                    export / "Cargo.toml",
                    "p",
                    self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"],
                    command_cwd=export,
                )
        return cleaned

    def test_pushes_from_one_export_path_clean_only_the_first(self) -> None:
        # With the path fixed, Cargo's in-place rebuild of the dependency
        # (fresh mtimes) writes the bytes it wrote before.
        self.assertEqual(self.push(4, stable_path=True), [["d", "p"], [], [], []])

    def test_pushes_from_new_export_paths_clean_only_the_first(self) -> None:
        # The gate as members run it today: a new export path per push, which
        # rustc embeds in the dependency's bytes. The run re-hashes what its
        # command rebuilt, so the next push finds its record true.
        self.assertEqual(self.push(4, stable_path=False), [["d", "p"], [], [], []])

    def test_a_committed_cargo_config_does_not_go_stale_across_export_paths(self) -> None:
        # `cargo_config_digest` frames a directory config by its depth from
        # the execution root and its filename, never its absolute path.
        # Framing the absolute path instead would make a `.cargo/config.toml`
        # committed inside the repository -- present at the same relative
        # position on every push -- look like a new config every push (a new
        # export path is a new absolute path), reintroducing the every-push
        # staleness this identity scheme exists to remove.
        (self.source / ".cargo").mkdir()
        (self.source / ".cargo" / "config.toml").write_text(
            "[build]\njobs = 1\n", encoding="utf-8"
        )
        git(self.source, "add", ".cargo/config.toml")
        git(self.source, "commit", "-qm", "commit cargo config")
        self.assertEqual(self.push(4, stable_path=False), [["d", "p"], [], [], []])


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class EffectiveCargoConfigurationTestCase(unittest.TestCase):
    """A `.cargo/config.toml` one directory *above* the export (exactly
    where the pre-push hook mirrors the stack's shared config, outside the
    exported repository) or a `CARGO_BUILD_*` environment variable can
    reconfigure how a git dependency compiles -- a different profile, a
    different `RUSTFLAGS` -- while every repository's git history stays
    untouched and the run's own source does not change either. Before
    `cargo_config_digest`/the widened `environment_digest`, an *exact-match*
    run (source, dependency closure, and prior build dimensions all
    unchanged) reused its existing record and artifact even though Cargo
    itself recompiled the dependency under the new configuration: this
    class asserts the record can no longer match across that change.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-cargo-config-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if key not in ("CARGO_TARGET_DIR", "RUSTFLAGS", "CARGO_BUILD_RUSTFLAGS")
        }
        self.environment["CARGO_HOME"] = str(self.base / "cargo-home")

        self.d = self.base / "drepo"
        for relative, text in {
            "Cargo.toml": '[package]\nname = "d"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n',
            "src/lib.rs": "pub fn d() -> u32 { 1 }\n",
        }.items():
            (self.d / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.d / relative).write_text(text, encoding="utf-8")
        git(self.d, "init", "-q")
        git(self.d, "config", "user.name", "Atlas test")
        git(self.d, "config", "user.email", "atlas-test@example.invalid")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.d, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.d, "add", ".")
        git(self.d, "commit", "-q", "-m", "d")

        # The exported repository lives one level below `stack/`, mirroring
        # the pre-push hook writing the stack config to `$gate_parent/.cargo`.
        self.stack = self.base / "stack"
        self.source = self.stack / "source"
        for relative, text in {
            "Cargo.toml": (
                '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n'
                f'[dependencies]\nd = {{ git = "{self.d.as_uri()}" }}\n'
            ),
            "src/lib.rs": "pub fn p() -> u32 { d::d() }\n",
        }.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        subprocess.run(
            ["cargo", "generate-lockfile"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Atlas test")
        git(self.source, "config", "user.email", "atlas-test@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(self, pushes: int, *, reconfigure_before: int, mode: str) -> list[identity.BuildResult]:
        # No source edit at `reconfigure_before`: on main (no narrowing),
        # a source edit alone already forces a whole-closure rebuild and
        # would mask exactly the bug this class exists to catch -- an
        # otherwise *exact-match* push that only Cargo's own configuration
        # changed.
        results: list[identity.BuildResult] = []
        with patch.dict(os.environ, self.environment, clear=True):
            for push in range(pushes):
                if push == reconfigure_before:
                    if mode == "profile":
                        (self.stack / ".cargo").mkdir(exist_ok=True)
                        (self.stack / ".cargo" / "config.toml").write_text(
                            '[profile.dev.package."*"]\nopt-level = 1\n', encoding="utf-8"
                        )
                    else:
                        os.environ["CARGO_BUILD_RUSTFLAGS"] = "-Cdebug-assertions=off"
                export = self.stack / f"export-{push}"
                if export.exists():
                    _clear_readonly_tree(export)
                shutil.copytree(self.source, export, copy_function=shutil.copy)
                results.append(
                    identity.run_build(
                        export, export / "Cargo.toml", "p", self.base / "target",
                        ["cargo", "check", "-p", "p", "-q", "--offline"], command_cwd=export,
                    )
                )
        return results

    def assert_reconfiguration_is_never_silently_reused(self, mode: str) -> None:
        results = self.push(3, reconfigure_before=2, mode=mode)
        self.assertEqual([r.status for r in results], ["rebuilt", "reused", "rebuilt"])
        self.assertNotEqual(results[1].record_path, results[2].record_path)

    def test_a_stack_config_profile_change_is_never_silently_reused(self) -> None:
        self.assert_reconfiguration_is_never_silently_reused("profile")

    def test_a_build_rustflags_change_is_never_silently_reused(self) -> None:
        self.assert_reconfiguration_is_never_silently_reused("env")


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class CrossRepositoryPathDependencyTestCase(unittest.TestCase):
    """`p` depends on `d`, a *separate* repository patched in as a path
    dependency, the shape the development overlay gives every first-party
    dependency. `d`'s own repository never changes, so its path record's
    identity -- `source_identity` of `d`'s own repository -- never changes
    either, even while `p`'s repository does on every push. A record that
    compared the whole dependency snapshot for equality never noticed that:
    `p`'s own path record moved with `p`'s repository regardless, so the
    whole snapshot compared unequal and cleaned `d` on every push that
    changed only `p` -- the exclusive lease on `d` that serialized every
    other gate building it.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-cross-repo-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }

        self.drepo = self.base / "drepo"
        for relative, text in {
            "Cargo.toml": '[package]\nname = "d"\nversion = "0.1.0"\nedition = "2021"\n'
            "[workspace]\n",
            "src/lib.rs": "pub fn d() -> u32 {\n    1\n}\n",
        }.items():
            (self.drepo / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.drepo / relative).write_text(text, encoding="utf-8")
        git(self.drepo, "init", "-q")
        git(self.drepo, "config", "user.name", "Atlas test")
        git(self.drepo, "config", "user.email", "atlas-test@example.invalid")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.drepo, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.drepo, "add", ".")
        git(self.drepo, "commit", "-q", "-m", "d")

        self.source = self.base / "source"
        for relative, text in {
            "Cargo.toml": (
                '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n'
                "[workspace]\n\n[dependencies]\n"
                f'd = {{ path = "{self.drepo.as_posix()}" }}\n'
            ),
            "src/lib.rs": "pub fn p() -> u32 {\n    d::d()\n}\n",
        }.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Atlas test")
        git(self.source, "config", "user.email", "atlas-test@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(
        self,
        pushes: int,
        *,
        change_p_before: int | None = None,
        change_d_before: int | None = None,
    ) -> list[list[str]]:
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if list(command[1:3]) == ["clean", "-p"]:
                cleaned[-1].extend(command[i + 1] for i, value in enumerate(command) if value == "-p")
            run_checked(command, cwd, environment)

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_run_checked", side_effect=recording),
        ):
            for push in range(pushes):
                if push == change_p_before:
                    (self.source / "src/lib.rs").write_text(
                        "pub fn p() -> u32 {\n    d::d() + 1\n}\n", encoding="utf-8"
                    )
                    git(self.source, "commit", "-qam", "change p only")
                if push == change_d_before:
                    (self.drepo / "src/lib.rs").write_text(
                        "pub fn d() -> u32 {\n    7\n}\n", encoding="utf-8"
                    )
                    git(self.drepo, "commit", "-qam", "change d only")
                export = self.base / f"export-{push}"
                if export.exists():
                    _clear_readonly_tree(export)
                shutil.copytree(self.source, export, copy_function=shutil.copy)
                cleaned.append([])
                result = identity.run_build(
                    export,
                    export / "Cargo.toml",
                    "p",
                    self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"],
                    command_cwd=export,
                )
                self.last_result = result
        return cleaned

    def test_a_push_that_changes_only_p_cleans_only_p(self) -> None:
        # Push 0 builds fresh (cleans both: nothing recorded yet). Push 1
        # repeats the same commit from a fresh export (reused: Cargo's
        # in-place rebuild writes the bytes it wrote before, as the
        # single-repo case above already proves). Push 2 changes only `p`'s
        # source; `d`'s repository, and so its path record's identity, does
        # not move, so only `p` -- never `d` -- is due for cleaning.
        self.assertEqual(self.push(3, change_p_before=2), [["d", "p"], [], ["p"]])

    def test_a_narrowed_clean_of_a_dependency_names_its_rediscovered_files(self) -> None:
        # `d`'s own source changes (not `p`'s): the narrowed clean this time
        # holds and cleans `d`, never `p`. The record written afterward must
        # still name `d`'s rediscovered files -- every `libd-*`/`d-*` path
        # this build actually produced -- rather than recording an empty
        # attribution for the one package this run held exclusive
        # (`M9_no_held_discovery`'s failure mode: passing an empty related-
        # packages tuple to discovery never looks for `d` at all).
        cleaned = self.push(2, change_d_before=1)
        self.assertEqual(cleaned, [["d", "p"], ["d"]])
        record = json.loads(self.last_result.record_path.read_text(encoding="utf-8"))
        named_d = {
            Path(relative).name
            for relative in record["artifact"]["files"]
            if Path(relative).name.startswith(("libd-", "d-"))
        }
        self.assertTrue(named_d)
        deps_dir = self.base / "target" / "debug" / "deps"
        on_disk_d = {path.name for path in deps_dir.iterdir() if path.name.startswith(("libd-", "d-"))}
        self.assertEqual(named_d, on_disk_d)


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class SharedCommandKeyThreeStepTestCase(unittest.TestCase):
    """The pre-push hook's exact sequence for one package: clippy, nextest,
    then `env RUSTDOCFLAGS=... cargo doc`, all under one `command_key` so
    they read one shared record. A rustdoc-only environment variable must
    not split that record into two mutually-stale halves -- a real run of
    exactly this sequence measured the whole dependency closure (94 files,
    4.5 MiB) being cleaned on every push instead of once, because the doc
    step's inline `env` prefix gave it a different `environment_digest`
    from the clippy and test steps' plain invocations.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-shared-key-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        self.source = self.base / "src_repo"
        for relative, text in {
            "Cargo.toml": '[workspace]\nmembers = ["a", "b"]\nresolver = "2"\n',
            "a/Cargo.toml": (
                '[package]\nname = "a"\nversion = "0.1.0"\nedition = "2021"\n'
                "[dependencies]\nb = { path = \"../b\" }\n"
            ),
            "a/src/lib.rs": (
                "//! a\n/// a\npub fn a() -> u32 { b::b() + 1 }\n"
                "#[test]\nfn t() { assert_eq!(a(), 2); }\n"
            ),
            "b/Cargo.toml": '[package]\nname = "b"\nversion = "0.1.0"\nedition = "2021"\n',
            "b/src/lib.rs": "//! b\n/// b\npub fn b() -> u32 { 1 }\n",
        }.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Atlas test")
        git(self.source, "config", "user.email", "atlas-test@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(
        self, gate: Path, environment: dict[str, str] | None = None
    ) -> list[tuple[str, str, str]]:
        """Run the hook's exact three steps for package `a` under one export."""
        (gate / ".cargo").mkdir(parents=True, exist_ok=True)
        (gate / ".cargo" / "config.toml").write_text(
            '[profile.dev]\ndebug = "line-tables-only"\n', encoding="utf-8"
        )
        export = gate / "nested" / "ws"
        if not export.exists():
            export.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "-q", str(self.source), str(export)], check=True)
        manifest = str(export / "Cargo.toml")
        steps = [
            (
                "clippy",
                ["cargo", "clippy", "-q", "--manifest-path", manifest, "-p", "a",
                 "--all-targets", "--locked", "--offline"],
            ),
            (
                "tests",
                ["cargo", "nextest", "run", "--manifest-path", manifest, "-p", "a",
                 "--locked", "--offline", "--no-tests=pass",
                 "--status-level", "none", "--final-status-level", "none"],
            ),
            (
                "rustdoc",
                ["env", "RUSTDOCFLAGS=-D warnings", "cargo", "doc", "-q", "--no-deps",
                 "--manifest-path", manifest, "-p", "a", "--locked", "--offline"],
            ),
        ]
        results = []
        with patch.dict(os.environ, {**self.environment, **(environment or {})}, clear=True):
            for name, command in steps:
                result = identity.run_build(
                    export, export / "Cargo.toml", "a", self.base / "target", command,
                    command_cwd=export, command_key="atlas-pre-push:a",
                )
                results.append((name, result.status, result.record_path.name))
        return results

    def test_the_three_steps_share_one_record_across_pushes(self) -> None:
        first = self.push(self.base / "gate1")
        second = self.push(self.base / "gate2")
        third = self.push(self.base / "gate3")
        # Every step of push 1 shares one record path (clippy/tests/doc are
        # never split); push 2 and push 3 repeat the same commit and must
        # reuse it with nothing rebuilt.
        self.assertEqual(len({record for _, _, record in first}), 1)
        self.assertEqual([status for _, status, _ in second], ["reused", "reused", "reused"])
        self.assertEqual([status for _, status, _ in third], ["reused", "reused", "reused"])
        self.assertEqual(
            {record for _, _, record in second}, {record for _, _, record in first}
        )

    def test_a_rustflags_change_is_still_detected_under_the_shared_key(self) -> None:
        first = self.push(self.base / "gate1")
        second = self.push(
            self.base / "gate2", environment={"CARGO_BUILD_RUSTFLAGS": "-Cdebug-assertions=off"}
        )
        self.assertEqual([status for _, status, _ in second], ["rebuilt", "reused", "reused"])
        self.assertNotEqual(
            {record for _, _, record in first}, {record for _, _, record in second}
        )


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class PathDependencyFeatureChangeTestCase(unittest.TestCase):
    """`p` depends on `v` and `x`, each a separate repository; `v` also
    depends on `x`. Enabling `x`'s feature `f` from `p`'s manifest changes
    `x`'s resolved feature set -- and so `v`'s rebuilt variant -- without
    `x`'s own path record necessarily disagreeing on `identity` alone: a
    judge's real-Cargo counterexample showed the old identity-only
    comparison narrowed here and left `v`'s new variant unrecorded. Only a
    path record whose *entire* non-identity content (name, version,
    features, kind) still agrees may narrow.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-feature-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }

        def repo(root: Path, files: dict[str, str]) -> None:
            for relative, text in files.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, encoding="utf-8")
            git(root, "init", "-q")
            git(root, "config", "user.name", "Atlas test")
            git(root, "config", "user.email", "atlas-test@example.invalid")
            subprocess.run(
                ["cargo", "generate-lockfile", "--offline"],
                cwd=root, env=self.environment, check=True, capture_output=True, timeout=120,
            )
            git(root, "add", ".")
            git(root, "commit", "-q", "-m", "init")

        self.x = self.base / "xrepo"
        self.v = self.base / "vrepo"
        self.source = self.base / "source"
        repo(self.x, {
            "Cargo.toml": (
                '[package]\nname = "x"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n'
                '[features]\nf = []\n'
            ),
            "src/lib.rs": "pub fn x() -> u32 {\n    1\n}\n",
        })
        repo(self.v, {
            "Cargo.toml": (
                '[package]\nname = "v"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n[dependencies]\n'
                f'x = {{ path = "{self.x.as_posix()}" }}\n'
            ),
            "src/lib.rs": "pub fn v() -> u32 { x::x() }\n",
        })

        def p_manifest(feature: bool) -> str:
            extra = ', features = ["f"]' if feature else ""
            return (
                '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n[dependencies]\n'
                f'v = {{ path = "{self.v.as_posix()}" }}\n'
                f'x = {{ path = "{self.x.as_posix()}"{extra} }}\n'
            )

        self.p_manifest = p_manifest
        repo(
            self.source,
            {"Cargo.toml": p_manifest(False), "src/lib.rs": "pub fn p() -> u32 { v::v() + x::x() }\n"},
        )

    def push(self, pushes: int, *, enable_feature_before: int) -> list[list[str]]:
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if list(command[1:3]) == ["clean", "-p"]:
                cleaned[-1].extend(command[i + 1] for i, value in enumerate(command) if value == "-p")
            run_checked(command, cwd, environment)

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_run_checked", side_effect=recording),
        ):
            for push in range(pushes):
                if push == enable_feature_before:
                    (self.source / "Cargo.toml").write_text(self.p_manifest(True), encoding="utf-8")
                    git(self.source, "commit", "-qam", "enable x/f")
                export = self.base / f"export-{push}"
                if export.exists():
                    _clear_readonly_tree(export)
                shutil.copytree(self.source, export, copy_function=shutil.copy)
                cleaned.append([])
                identity.run_build(
                    export, export / "Cargo.toml", "p", self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"], command_cwd=export,
                )
        return cleaned

    def test_enabling_a_dependency_feature_cleans_the_whole_closure(self) -> None:
        # Push 2 enables x's feature from p's manifest: x's snapshot record
        # differs in `features`, so narrowing must not apply.
        self.assertEqual(self.push(3, enable_feature_before=2), [["p", "v", "x"], [], ["p", "v", "x"]])


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class RootProfileChangeTestCase(unittest.TestCase):
    """A root manifest edit that only adds a `[profile.dev]` table still
    reconfigures how a *git* dependency compiles, even though the
    dependency's own recorded content never moves: a judge's real-Cargo
    counterexample showed the old identity-only comparison narrowed here
    (only the root's own path record disagreed) and left the dependency's
    rebuilt variant unrecorded. Only a revision-to-revision diff provably
    untouched by any build-configuration file may narrow.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-profile-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        self.environment["CARGO_HOME"] = str(self.base / "cargo-home")

        self.d = self.base / "drepo"
        for relative, text in {
            "Cargo.toml": '[package]\nname = "d"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n',
            "src/lib.rs": "pub fn d() -> u32 { 1 }\n",
        }.items():
            (self.d / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.d / relative).write_text(text, encoding="utf-8")
        git(self.d, "init", "-q")
        git(self.d, "config", "user.name", "Atlas test")
        git(self.d, "config", "user.email", "atlas-test@example.invalid")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.d, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.d, "add", ".")
        git(self.d, "commit", "-q", "-m", "d")

        def manifest(profile: bool) -> str:
            extra = "\n[profile.dev]\nopt-level = 1\n" if profile else ""
            return (
                '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n[dependencies]\n'
                f'd = {{ git = "{self.d.as_uri()}" }}\n' + extra
            )

        self.manifest = manifest
        self.source = self.base / "source"
        for relative, text in {
            "Cargo.toml": manifest(False), "src/lib.rs": "pub fn p() -> u32 { d::d() }\n"
        }.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        subprocess.run(
            ["cargo", "generate-lockfile"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Atlas test")
        git(self.source, "config", "user.email", "atlas-test@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(self, pushes: int, *, profile_before: int) -> list[list[str]]:
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if list(command[1:3]) == ["clean", "-p"]:
                cleaned[-1].extend(command[i + 1] for i, value in enumerate(command) if value == "-p")
            run_checked(command, cwd, environment)

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_run_checked", side_effect=recording),
        ):
            for push in range(pushes):
                if push == profile_before:
                    (self.source / "Cargo.toml").write_text(self.manifest(True), encoding="utf-8")
                    git(self.source, "commit", "-qam", "profile opt-level 1")
                export = self.base / f"export-{push}"
                if export.exists():
                    _clear_readonly_tree(export)
                shutil.copytree(self.source, export, copy_function=shutil.copy)
                cleaned.append([])
                identity.run_build(
                    export, export / "Cargo.toml", "p", self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"], command_cwd=export,
                )
        return cleaned

    def test_a_profile_edit_cleans_the_whole_closure(self) -> None:
        self.assertEqual(self.push(3, profile_before=2), [["d", "p"], [], ["d", "p"]])




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
        self.artifact = self.target / "debug" / "deps" / "libdemo-c1ab.rlib"
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

    def pre_push_released(self, lease_seconds: int, held_on: float) -> tuple[int, str]:
        """Run the pre-push entry point against a holder that releases only after
        the run has printed its waiting line and `held_on` more seconds pass."""
        lock = package_target_lease_path("demo", identity._canonical(self.target))
        release = self.target.parent / "release-holder"
        hold_lease(self, lock, self.target, lease_seconds, 120, release)
        stderr = io.StringIO()
        result: list[int] = []
        with redirect_stderr(stderr):
            run = threading.Thread(target=lambda: result.append(self.pre_push()))
            run.start()
            deadline = time.monotonic() + 60
            while "atlas-build-identity waiting:" not in stderr.getvalue():
                self.assertTrue(run.is_alive(), stderr.getvalue())
                self.assertLess(time.monotonic(), deadline, "the run never waited")
                time.sleep(0.01)
            time.sleep(held_on)
            self.assertTrue(run.is_alive(), "the run stopped waiting while the lease was held")
            release.write_text("release", encoding="utf-8")
            run.join(120)
        return result[0], stderr.getvalue()

    def test_the_pre_push_waits_for_a_live_owner_to_release(self) -> None:
        code, stderr = self.pre_push_released(60, 0.5)
        self.assertEqual(code, 0, stderr)
        self.assertIn("held by holder-root at holder-revision", stderr)
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "built")

    def test_the_pre_push_waits_out_an_owner_past_its_expiry(self) -> None:
        # A 1 s lease still held 2 s after the run began waiting: the lock,
        # not the recorded expiry, says the owner is alive, so the run keeps
        # waiting and then proceeds.
        code, stderr = self.pre_push_released(1, 2)
        self.assertEqual(code, 0, stderr)
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
