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
    ) -> identity.BuildResult:
        """Build `demo`, whose clean closure holds a path dependency `dep`."""
        snapshot = {
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

    def cleaned_packages(self, source_token: str) -> list[str]:
        """Rebuild through `cargo clean -p`, recording the packages instead of running Cargo."""
        packages: list[str] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if list(command[1:3]) == ["clean", "-p"]:
                packages.extend(command[i + 1] for i, value in enumerate(command) if value == "-p")
                return
            run_checked(command, cwd, environment)

        with patch.object(identity, "_run_checked", side_effect=recording):
            self.dependency_build(source_token, discover=True, clean=False)
        return sorted(packages)

    def test_changed_dependency_bytes_clean_only_that_dependency(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        recorded.write_bytes(b"rebuilt from another path")
        self.assertEqual(self.cleaned_packages("first"), ["dep"])

    def test_a_changed_source_cleans_the_whole_closure_whatever_changed_on_disk(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        (self.root / "src" / "lib.rs").write_text("fn main() { changed(); }\n", encoding="utf-8")
        recorded.write_bytes(b"rebuilt from another path")
        self.assertEqual(self.cleaned_packages("second"), ["demo", "dep"])

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
        # `env RUSTDOCFLAGS=... cargo doc` sets a variable no ambient
        # `os.environ` snapshot carries; only parsing the leading `env`
        # prefix lets the record see it move.
        init_repo(self.root, "fn main() {}\n")
        with patch.object(identity, "toolchain_identity", return_value="rustc-test"):
            first = identity.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTDOCFLAGS=-Dwarnings", "cargo", "doc"],
            )
            second = identity.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTDOCFLAGS=--cfg docsrs", "cargo", "doc"],
            )
        self.assertNotEqual(first.environment_digest, second.environment_digest)

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
