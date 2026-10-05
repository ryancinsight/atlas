#!/usr/bin/env python3
"""Regression tests for shared-cache source identity."""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "atlas_build_identity.py"
SPEC = importlib.util.spec_from_file_location("atlas_build_identity", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
sys.path.insert(0, str(SCRIPT.parent))
import atlas_build_artifacts as artifacts
import atlas_build_check as check
import atlas_build_inputs as build_inputs
import atlas_build_lease as lease_module
import atlas_build_lock as lock_module
import atlas_build_package_source as package_source
import atlas_build_queue as queue_module
import atlas_build_records as build_records
import atlas_build_snapshot as build_snapshot
import atlas_build_source as build_source
import atlas_build_stamps as build_stamps
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    BuildIdentityError,
    LeaseHeldError,
    OwnerLease,
    acquire_claim,
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
    init_git(root)
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "source")


def init_git(root: Path, name: str = "Atlas test", email: str = "atlas-test@example.invalid") -> None:
    """`git init` with the fixture's committer and no background maintenance.

    No detached `gc --auto` or maintenance may write into `.git` while the
    fixture's temporary directory is removed (a Linux runner failed teardown
    with `Directory not empty: .git`). The settings are appended to
    `.git/config` rather than set by one `git config` process each: process
    creation dominates this suite's runtime on Windows.
    """
    git(root, "init", "-q")
    with (root / ".git" / "config").open("a", encoding="utf-8", newline="\n") as config:
        config.write(
            f"[user]\n\tname = {name}\n\temail = {email}\n"
            "[gc]\n\tauto = 0\n[maintenance]\n\tauto = false\n"
        )


def gate_export(source: Path, export: Path) -> str:
    """Export `source`'s HEAD the way the pre-push gate does; return its revision.

    A repository borrowing the source's objects, its files and index written
    by `read-tree -u --reset` run in the source, `HEAD` set to the revision.
    """
    revision = git(source, "rev-parse", "HEAD")
    export.mkdir(parents=True)
    init_git(export)
    objects = git(source, "rev-parse", "--path-format=absolute", "--git-common-dir") + "/objects"
    (export / ".git" / "objects" / "info" / "alternates").write_bytes(objects.encode() + b"\n")
    subprocess.run(
        ["git", "read-tree", "-u", "--reset", revision], cwd=source, check=True, timeout=60,
        env=dict(os.environ, GIT_WORK_TREE=str(export), GIT_INDEX_FILE=str(export / ".git" / "index")),
    )
    git(export, "update-ref", "HEAD", revision)
    return revision


def index_stat_data(root: Path) -> dict[str, tuple[int, int]]:
    """Each index entry's recorded modification time (whole seconds) and size."""
    entries: dict[str, tuple[int, int]] = {}
    path = None
    mtime = None
    for line in git(root, "ls-files", "--debug").splitlines():
        field, _, value = line.strip().partition(":")
        if not line.startswith((" ", "\t")):
            path = line
        elif field == "mtime":
            mtime = int(value.strip().split(":")[0])
        elif field == "size":
            assert path is not None and mtime is not None
            entries[path] = (mtime, int(value.split()[0]))
    return entries


def write_script(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


class RecordedClock:
    """The `time` module, remembering what each `monotonic_ns` read returned.

    Patched over `identity.time`, whose only use is the single read that
    fixes a run's lease deadline: the first value recorded is the instant the
    deadline is measured from.
    """

    def __init__(self) -> None:
        self.reads: list[int] = []

    def monotonic_ns(self) -> int:
        self.reads.append(time.monotonic_ns())
        return self.reads[-1]

    def __getattr__(self, name: str):
        return getattr(time, name)


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


def acquire_lease(lease: OwnerLease, wait_seconds: float) -> OwnerLease:
    """Take one lease as a claim of its own; the caller releases it with `__exit__`."""
    acquire_claim((lease,), wait_seconds)
    return lease


MODE_HOLDER = (
    "import sys, threading, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "import atlas_build_lease as module\n"
    "from atlas_build_lease import OwnerLease\n"
    "orphaned = threading.Event()\n"
    "if sys.argv[8]:\n"
    "    threading.Thread(target=lambda: (sys.stdin.read(), orphaned.set()), daemon=True).start()\n"
    "for _ in range(int(sys.argv[6])):\n"
    "    lease = OwnerLease(Path(sys.argv[2]), {'root': sys.argv[5], 'revision': 'holder-revision',"
    " 'package': 'dep'}, 600, mode=sys.argv[3])\n"
    "    if hasattr(module, 'acquire_claim'):\n"
    "        module.acquire_claim([lease], 120)\n"
    "    else:\n"
    "        module.acquire_waiting(lease, 120)\n"
    "    if sys.argv[7]:\n"
    "        with open(sys.argv[7], 'ab') as rounds:\n"
    "            rounds.write(b'.')\n"
    "    print('held', flush=True)\n"
    "    if sys.argv[8]:\n"
    "        while not Path(sys.argv[8]).exists() and not orphaned.is_set():\n"
    "            time.sleep(0.01)\n"
    "    else:\n"
    "        time.sleep(float(sys.argv[4]))\n"
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
    rounds: Path | None = None,
    stop: Path | None = None,
) -> subprocess.Popen:
    """Hold `lock` in `mode` from a separate process, `repeat` times back to back.

    Each round waits its turn, holds for `hold_seconds`, releases, and asks
    again at once: the pattern of a push hook re-running its steps. When
    `rounds` names a file, each round appends one byte to it as it takes the
    lease, so the file's size counts the rounds taken. When `stop` names a
    file, each round holds until that file exists or the test process ends,
    with no clock, and `hold_seconds` is not used.
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
            str(rounds or ""),
            str(stop or ""),
        ],
        stdin=subprocess.PIPE if stop else None,
        stdout=subprocess.PIPE,
        text=True,
    )
    test.addCleanup(holder.wait, 60)
    test.addCleanup(holder.kill)
    test.addCleanup(holder.stdout.close)
    if stop:
        test.addCleanup(holder.stdin.close)
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


def cleaned_names(command: list[str]) -> list[str] | None:
    """The packages a `cargo clean` names, `<whole target>` when it names none."""
    if len(command) < 2 or command[1] != "clean":
        return None
    return [command[i + 1] for i, value in enumerate(command) if value == "-p"] or ["<whole target>"]


def path_records(*names: str) -> list[dict[str, object]]:
    """Snapshot path records for `names`, each in an unchanging repository."""
    return [
        {"id": f"workspace:{name}#{name}@0.1.0", "name": name, "version": "0.1.0",
         "features": [], "kind": "path", "identity": {"revision": name}}
        for name in names
    ]


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

    def take_and_release(self, lock: Path, mode: str) -> None:
        """Wait for `lock` in `mode`, then release it: a refusal past the wait bound raises."""
        acquire_lease(
            OwnerLease(lock, {"root": "waiter", "revision": "r"}, 60, mode=mode), 60
        ).__exit__(None, None, None)

    def rounds_taken_while_queued(self, lock: Path, mode: str, *counts: Path) -> int:
        """The rounds the holders counted in `counts` take between this request's
        place in line and its grant.

        A request is served after every request that arrived before it, so
        of a holder that releases and asks again only the round already
        running when this request queued can come first. A round counted just
        after the request queued, having taken the lease before it, is that
        same round: at most one round per holder is taken while queued,
        whatever the host's speed.
        """

        def taken() -> int:
            return sum(path.stat().st_size for path in counts)

        lease = OwnerLease(lock, {"root": "waiter", "revision": "r"}, 60, mode=mode)
        self.addCleanup(lease.dequeue)
        lease.reserve()
        queued = taken()
        acquire_claim((lease,), 60)
        granted = taken()
        lease.__exit__(None, None, None)
        return granted - queued

    def test_a_repeating_exclusive_holder_does_not_starve_a_waiter(self) -> None:
        # Twelve back-to-back 1 s holds: without arrival order the holder asks
        # again the instant it releases and the polling waiter never gets in,
        # so it sees the holder take round after round.
        for mode in (EXCLUSIVE, SHARED):
            with self.subTest(waiter=mode):
                lock = self.lock(f"repeat-{mode}")
                rounds = self.base / f"repeat-{mode}.rounds"
                holder = start_holder(self, lock, EXCLUSIVE, 1, repeat=12, rounds=rounds)
                # A waiting reader also holds back the writer's next round.
                self.assertLessEqual(self.rounds_taken_while_queued(lock, mode, rounds), 1)
                holder.kill()
                holder.wait(60)

    def test_a_stream_of_shared_readers_does_not_starve_a_writer(self) -> None:
        # Two readers overlap, so the lease is never free of a shared holder.
        lock = self.lock("stream")
        counts = [self.base / "stream-a.rounds", self.base / "stream-b.rounds"]
        # The second reader starts while the first holds, which keeps their
        # rounds overlapping; each is then running a round when the writer
        # queues, and neither starts another before the writer is served.
        start_holder(self, lock, SHARED, 1, name="reader-a", repeat=12, rounds=counts[0])
        start_holder(self, lock, SHARED, 1, name="reader-b", repeat=12, rounds=counts[1])
        self.assertLessEqual(self.rounds_taken_while_queued(lock, EXCLUSIVE, *counts), 2)

    def test_a_crashed_holder_or_waiter_gives_up_its_place(self) -> None:
        lock = self.lock("crash")
        holder = start_holder(self, lock, SHARED, 0, stop=self.base / "release-crash")
        # The waiter reports once it is queued behind the holder: both
        # tickets are live, so neither is collected before the kills.
        waiter = start_script(self, QUEUED_WAITER, str(lock), ready="queued")
        queue = lock.with_name(f"{lock.stem}.queue")
        self.assertEqual(len(list(queue.glob("*.ticket"))), 2)
        for process in (waiter, holder):
            process.kill()
            process.wait(60)
        # Both processes have exited, so their tickets are dead and the very
        # first request collects them and is granted: nothing waits on a
        # place whose requester has crashed.
        self.assertEqual(request(lock, SHARED), "granted")
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
        # collects the dead shared ones, including those after its own. No
        # process holds anything, so the first attempt is granted.
        self.assertEqual(request(lock, SHARED), "granted")
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
            "sys.stdin.read()\n"
        )
        ticket_locks = []

        def contended(handle, mode=EXCLUSIVE):
            if str(handle.name).endswith(".ticket") and mode == EXCLUSIVE:
                ticket_locks.append(handle.name)
            if len(ticket_locks) == 1 and not probes:
                process = subprocess.Popen(
                    [sys.executable, "-c", probe, str(SCRIPT.parent), str(handle.name)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    text=True,
                )
                self.addCleanup(process.wait, 60)
                self.addCleanup(process.kill)
                self.addCleanup(process.stdout.close)
                self.addCleanup(process.stdin.close)
                self.assertEqual(process.stdout.readline().strip(), "held")
                probes.append(process)
                # The probe holds the ticket until it is told to let go, so
                # the requester's lock is refused however long the host takes.
                locked = real_try_lock(handle, mode)
                process.stdin.close()
                self.assertFalse(locked)
                return locked
            return real_try_lock(handle, mode)

        with patch.object(queue_module, "_try_lock", side_effect=contended):
            self.take_and_release(lock, EXCLUSIVE)
        self.assertEqual(len(probes), 1)
        # The refused lock is retried under a new name, which is then locked.
        self.assertGreaterEqual(len(ticket_locks), 2)
        probes[0].wait(60)
        self.take_and_release(lock, SHARED)
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
            "queue, stop = Path(sys.argv[2]), Path(sys.argv[3])\n"
            "print('probing', flush=True)\n"
            "while not stop.exists():\n"
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
        stop = self.base / "stop-probing"
        self.addCleanup(stop.write_text, "stop", encoding="utf-8")
        probers = []
        for _ in range(3):
            process = subprocess.Popen(
                [sys.executable, "-c", prober, str(SCRIPT.parent), str(queue), str(stop)],
                stdout=subprocess.PIPE,
                text=True,
            )
            self.addCleanup(process.wait, 60)
            self.addCleanup(process.kill)
            self.addCleanup(process.stdout.close)
            self.assertEqual(process.stdout.readline().strip(), "probing")
            probers.append(process)
        # The probers run until told to stop, so every request is made
        # under probing, however long the host takes to make them.
        for _ in range(30):
            self.take_and_release(lock, EXCLUSIVE)
        stop.write_text("stop", encoding="utf-8")
        for process in probers:
            process.wait(60)
        # A release a probe held open stays behind, dead, for the next request.
        self.take_and_release(lock, SHARED)
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
# a record names, writing each in slow chunks so a hash can catch it half done,
# until the file argv[4] names exists or its standard input closes, which
# happens when the test process ends however it ends. It prints `writing`
# once its first variant is under way.
VARIANT_WRITER = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': 'variant-writer', 'revision': 'r'}, 600, mode='shared')\n"
    "lease.__enter__()\n"
    "print('held', flush=True)\n"
    "deps = Path(sys.argv[3])\n"
    "stop = Path(sys.argv[4])\n"
    "import threading\n"
    "orphaned = threading.Event()\n"
    "threading.Thread(target=lambda: (sys.stdin.read(), orphaned.set()), daemon=True).start()\n"
    "variant = 0\n"
    "while not stop.exists() and not orphaned.is_set():\n"
    "    variant += 1\n"
    "    with (deps / f'libdep-variant{variant}.rlib').open('wb') as stream:\n"
    "        for _ in range(20):\n"
    "            stream.write(b'x' * 65536)\n"
    "            stream.flush()\n"
    "            if variant == 1 and _ == 0:\n"
    "                print('writing', flush=True)\n"
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


# A wait for a step takes this many times the step's start-up, measured once
# per test process the first time a script starts. The factor covers the host
# slowing after that measurement: an interpreter that imports the lease module
# took 0.104 s on a quiet 24-CPU host and 0.711 s with 30 busy loops beside
# it, a ratio of about 6.8, and 15 is more than twice that. It is a measured
# constant that ends a hang, not an assertion bound derived from a property,
# and a larger factor would cost nothing but a slower failure.
HOST_SLOWDOWN_MARGIN = 15


@functools.cache
def child_startup_seconds() -> float:
    """Seconds a fresh interpreter takes to import the lease module, measured once.

    That is the work a helper script does before it first prints (the
    imports, then taking a lease). The measure is taken per test process, the
    first time a script is started, and reused for the rest of the process.
    """
    started = time.monotonic()
    subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import atlas_build_lease",
         str(SCRIPT.parent)],
        check=True,
        timeout=120,
    )
    return time.monotonic() - started


def next_line_within(test: unittest.TestCase, process: subprocess.Popen, seconds: float) -> str:
    """The next line `process` prints, or a test failure once `seconds` pass.

    Nothing else ends a wait for a line a process that keeps running never
    prints: the test is the one waiting. The line is read on a thread so the
    wait has a deadline. At it the process is killed and reaped, which also
    ends the thread's read and lets the test's cleanups close the pipe, and
    then the test fails.
    """
    line: queue.Queue[str] = queue.Queue()
    reader = threading.Thread(target=lambda: line.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        return line.get(timeout=seconds).strip()
    except queue.Empty:
        process.kill()
        process.wait(60)
        reader.join(60)
        test.fail(f"the process printed no line within {seconds:.1f} s")


def start_script(
    test: unittest.TestCase, script: str, *arguments: str, ready: str = "held"
) -> subprocess.Popen:
    """Start `script` and wait, under a deadline, for the line `ready` it prints."""
    # Standard input stays open for the script's life, so a script can tell
    # the test process ended by reading it to end of file.
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(SCRIPT.parent), *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    test.addCleanup(process.wait, 60)
    test.addCleanup(process.kill)
    test.addCleanup(process.stdout.close)
    test.addCleanup(process.stdin.close)
    test.assertEqual(
        next_line_within(test, process, HOST_SLOWDOWN_MARGIN * child_startup_seconds()), ready
    )
    return process


# A request that queues behind a holder of the lease and waits there, its
# ticket live until the process is killed. It prints `queued` once queued.
QUEUED_WAITER = (
    "import sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import LeaseHeldError, OwnerLease\n"
    "lease = OwnerLease(Path(sys.argv[2]), {'root': 'waiter', 'revision': 'r'}, 60)\n"
    "try:\n"
    "    lease.attempt()\n"
    "except LeaseHeldError:\n"
    "    print('queued', flush=True)\n"
    "    sys.stdin.read()\n"
)

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
            patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"),
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
                ("demo",),
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                **options,
            )[0]

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
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            code, value = check.check_record(
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

    def test_a_fresh_gate_exports_index_records_each_files_stat_data(self) -> None:
        """The export's index carries each file's size and modification time,
        and the export is identified clean at its revision.

        `git diff HEAD` can skip re-hashing an entry only when its recorded
        size and modification time match the file's, and a read-tree index
        with no stat data re-hashed kwavers for 348 s. That match is a
        necessary condition, not a sufficient one: all 19 of this fixture's
        entries carry the whole second its index was written in, which Git
        treats as racily clean and re-reads whatever they record. The test
        checks the condition, not the speed.
        """
        init_repo(self.root, "fn main() {}\n")
        bulk = self.root / "data"
        bulk.mkdir()
        for index in range(16):
            (bulk / f"part-{index:04}.txt").write_text(f"{index}\n" * 64, encoding="utf-8")
        git(self.root, "add", "data")
        git(self.root, "commit", "-qm", "bulk")
        export = self.base / "export" / "member"
        revision = gate_export(self.root, export)
        entries = index_stat_data(export)
        self.assertEqual(len(entries), 19)
        for path, (mtime_seconds, size) in entries.items():
            status = (export / path).stat()
            self.assertEqual(size, status.st_size, path)
            self.assertEqual(mtime_seconds, status.st_mtime_ns // 1_000_000_000, path)
        calls: list[tuple[str, ...]] = []
        real_git = build_source._git

        def recording_git(root: Path, *arguments: str) -> bytes:
            calls.append(arguments)
            return real_git(root, *arguments)

        with patch.object(build_source, "_git", side_effect=recording_git):
            found = build_source.source_identity(export)
        self.assertIn("diff", [arguments[0] for arguments in calls])
        self.assertEqual(found.revision, revision)
        self.assertFalse(found.dirty)

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
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            spec = build_inputs.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lease = OwnerLease(
            lock,
            {"root": "other-source", "revision": "other-revision", "package": "demo"},
            60,
        )
        lease.__enter__()
        try:
            self.clean_log.unlink()
            with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
                code, value = check.check_record(
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
            "packages": path_records("demo", "dep"),
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
                patch.object(identity, "_dependency_data", return_value={"demo": snapshot}),
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
                        ("demo",),
                        self.target,
                        [sys.executable, str(self.build_script)],
                        artifact_paths=(),
                    )[0]
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
        owners: dict[str, frozenset[str]] | None = None,
    ) -> identity.BuildResult:
        """Build `demo`, whose clean closure holds a path dependency `dep`."""
        snapshot = snapshot or {
            "root": "demo",
            "packages": path_records("demo", "dep"),
            "edges": [],
            "clean_packages": ["demo", "dep"],
            "digest": "dependency-digest",
        }
        owners = owners or {"demo": frozenset({"demo"}), "dep": frozenset({"dep"})}
        with (
            patch.object(identity, "_dependency_data", return_value={"demo": snapshot}),
            patch.object(artifacts, "_workspace_artifact_owners", return_value=owners),
            patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"),
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
                ("demo",),
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=() if discover else [self.artifact],
                clean_command=[sys.executable, str(self.clean_script)] if clean else None,
                lease_wait_seconds=wait,
            )[0]

    def dep_lock(self, package: str = "dep") -> Path:
        return package_target_lease_path(package, build_source._canonical(self.target))

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

    def test_a_wait_for_a_line_that_never_comes_ends_at_its_deadline(self) -> None:
        silent = subprocess.Popen(
            [sys.executable, "-c", "import sys; sys.stdin.read()"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(silent.wait, 60)
        self.addCleanup(silent.kill)
        self.addCleanup(silent.stdout.close)
        self.addCleanup(silent.stdin.close)
        with self.assertRaises(AssertionError) as caught:
            next_line_within(self, silent, 0.5)
        self.assertIn("no line within 0.5 s", str(caught.exception))
        # The silent process was killed and reaped, not left running.
        self.assertIsNotNone(silent.poll())

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
        stop = self.base / "stop-variants"
        writer = start_script(self, VARIANT_WRITER, str(self.dep_lock()), str(deps), str(stop))
        self.addCleanup(stop.write_text, "stop", encoding="utf-8")
        # The rounds start only once a variant is being written. That takes
        # one 64 KiB write, which measured 1.5 ms against a start-up (the
        # interpreter, the imports, the lease) of 0.13 to 0.7 s across idle
        # and loaded hosts, so the wait the margin gives it is a deadline no
        # healthy writer nears.
        self.assertEqual(
            next_line_within(self, writer, HOST_SLOWDOWN_MARGIN * child_startup_seconds()),
            "writing",
        )
        self.clean_log.unlink(missing_ok=True)
        for _ in range(3):
            self.assertEqual(self.dependency_build("first", wait=2, discover=True).status, "reused")
        # The writer was writing before the first round and stops only when
        # told to, so it wrote through every round.
        self.assertIsNone(writer.poll())
        stop.write_text("stop", encoding="utf-8")
        self.assertEqual(writer.wait(60), 0)
        self.assertTrue(any(deps.glob("libdep-variant*.rlib")))
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
        # Twice the reads a one-second budget allows: a reader that ignored
        # its deadline exhausts them and fails at once instead of hanging.
        reads = iter(range(2 * (2 + round(1.0 / artifacts._SETTLE_INTERVAL))))
        settle = artifacts.settled_digest

        def unsettled(path, deadline_ns):
            if path.name != "libdep-0ecdeded.rlib":
                return settle(path, deadline_ns)
            with patch.object(artifacts, "_file_digest", side_effect=lambda _: f"read-{next(reads)}"):
                return settle(path, deadline_ns)

        with patch.object(artifacts, "settled_digest", side_effect=unsettled):
            result = self.dependency_build("first", wait=3, discover=True)
        files = json.loads(result.record_path.read_text(encoding="utf-8"))["artifact"]["files"]
        self.assertEqual(files["debug/deps/libdep-0ecdeded.rlib"], artifacts.UNVERIFIED)
        # Two reads are made whatever the budget left; how many more depends
        # on the time the run has left, which the next test pins.
        self.assertGreaterEqual(next(reads), 2)

    def test_a_file_that_never_reads_the_same_twice_is_read_until_its_budget_ends(self) -> None:
        # Under a clock that moves only when the reader sleeps, a file that
        # never agrees is read once, confirmed at once, then re-read after
        # each `_SETTLE_INTERVAL` sleep until the one-second budget is spent:
        # 2 + 1.0 / 0.02 reads.
        # `reads` is rebound per case; the digest lambda reads it at call time.
        target = self.base / "unsettled.rlib"
        target.write_bytes(b"artifact")
        clock = [0]

        class Clock:
            @staticmethod
            def monotonic_ns() -> int:
                return clock[0]

            @staticmethod
            def sleep(seconds: float) -> None:
                clock[0] += round(seconds * 1_000_000_000)

        for deadline_ns, expected_reads in (
            (1_000_000_000, 2 + round(1.0 / artifacts._SETTLE_INTERVAL)),
            # A budget already spent still gets its two reads.
            (-1, 2),
        ):
            with self.subTest(deadline_ns=deadline_ns):
                clock[0] = 0
                # Twice the most this case can read, so a reader that ignored
                # its deadline exhausts them and fails at once.
                reads = iter(range(2 * (2 + round(1.0 / artifacts._SETTLE_INTERVAL))))
                with (
                    patch.object(artifacts, "time", Clock),
                    patch.object(
                        artifacts, "_file_digest", side_effect=lambda _: f"read-{next(reads)}"
                    ),
                ):
                    digest = artifacts.settled_digest(target, deadline_ns)
                self.assertEqual(digest, artifacts.UNVERIFIED)
                self.assertEqual(next(reads), expected_reads)

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
        self,
        source_token: str,
        snapshot: dict[str, object] | None = None,
        owners: dict[str, frozenset[str]] | None = None,
        clean: bool = False,
    ) -> list[str]:
        """Rebuild through `cargo clean -p`, recording the packages instead of running Cargo.

        With `clean`, the run also has a custom clean command, which runs.
        """
        packages: list[str] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if (names := cleaned_names(command)) is not None:
                packages.extend(names)
                return
            run_checked(command, cwd, environment)

        with patch.object(identity, "_run_checked", side_effect=recording):
            self.dependency_build(
                source_token, discover=True, clean=clean, snapshot=snapshot, owners=owners
            )
        return sorted(packages)

    def test_a_registry_content_change_alone_cleans_nothing(self) -> None:
        # The record mismatches on the registry record's digest alone, so the
        # run is stale with nothing to clean; a `cargo clean` naming no
        # package would empty the whole shared target.
        init_repo(self.root, "fn main() {}\n")

        def snapshot(content_digest: str) -> dict[str, object]:
            registry = {
                "id": "registry+https://example.invalid#r@1.0.0", "name": "r", "version": "1.0.0",
                "features": [], "kind": "registry",
                "source": "registry+https://example.invalid", "content_digest": content_digest,
            }
            return {
                "root": "demo",
                "packages": [*path_records("demo", "dep"), registry],
                "edges": [],
                "clean_packages": ["demo", "dep"],
                "digest": f"digest-{content_digest}",
            }

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=snapshot("one"))
        self.assertEqual(self.cleaned_packages("first", snapshot=snapshot("two")), [])
        self.assertEqual(
            self.dependency_build("first", discover=True, snapshot=snapshot("two")).status, "reused"
        )

    def test_an_unattributable_changed_file_cleans_every_path_package(self) -> None:
        # `dep`'s recorded file changed, but no package in scope owns its stem
        # any more, so the change cannot be narrowed to one package.
        init_repo(self.root, "fn main() {}\n")
        recorded = self.artifact.parent / "libdep-0ecdeded.rlib"
        recorded.write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        recorded.write_bytes(b"rebuilt from another path")
        self.assertEqual(
            self.cleaned_packages(
                "first", owners={"demo": frozenset({"demo"}), "dep": frozenset({"renamed"})}
            ),
            ["demo", "dep"],
        )

    def test_a_moved_root_revision_alone_cleans_the_root(self) -> None:
        # An empty commit moves the root's source identity, not its files.
        init_repo(self.root, "fn main() {}\n")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        git(self.root, "commit", "-q", "--allow-empty", "-m", "empty")
        self.assertEqual(self.cleaned_packages("first"), ["demo"])

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

    def build_directory(self) -> build_stamps.BuildDirectory:
        return build_stamps.BuildDirectory(build_source._canonical(self.target), "debug", "host")

    def git_stamp(self, revision: str) -> Path:
        return self.build_directory().stamp(self.path_and_git_snapshot(revision)["packages"][1])

    def stamped(self, revision: str) -> str | None:
        return build_stamps._git_stamp(
            self.build_directory(), self.path_and_git_snapshot(revision)["packages"][1]
        )

    def test_an_unstamped_git_package_is_trusted_and_stamped(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.assertEqual(
            self.cleaned_packages("first", snapshot=self.path_and_git_snapshot(revision)), ["demo"]
        )
        self.assertEqual(self.stamped(revision), "stable-content")

    def test_a_failed_command_leaves_its_git_packages_stale(self) -> None:
        # A run that cleans `dep` and fails after Cargo rebuilt it leaves
        # the target holding what it built; the stamp must not keep naming
        # the content the old artifacts were built from.
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=self.path_and_git_snapshot(revision))
        self.git_stamp(revision).write_text('{"content_digest": "edited-content"}', encoding="utf-8")
        run_checked = identity._run_checked

        def failing(command, cwd, environment):
            if cleaned_names(command) is not None:
                return
            if str(self.build_script) in command:
                raise identity.IdentityError("command failed with exit code 1")
            run_checked(command, cwd, environment)

        with patch.object(identity, "_run_checked", side_effect=failing):
            with self.assertRaises(identity.IdentityError):
                self.dependency_build(
                    "first", discover=True, clean=False, snapshot=self.path_and_git_snapshot(revision)
                )
        self.assertEqual(self.stamped(revision), build_stamps._BUILDING)
        self.assertEqual(
            self.cleaned_packages("first", snapshot=self.path_and_git_snapshot(revision)), ["dep"]
        )
        self.assertEqual(self.stamped(revision), "stable-content")

    def test_a_custom_clean_still_cleans_the_stale_git_packages(self) -> None:
        # A caller's clean command is opaque: the stale Git package is
        # cleaned by Cargo as well before it is stamped.
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=self.path_and_git_snapshot(revision))
        self.git_stamp(revision).write_text('{"content_digest": "edited-content"}', encoding="utf-8")
        self.assertEqual(
            self.cleaned_packages(
                "first", snapshot=self.path_and_git_snapshot(revision), clean=True
            ),
            ["dep"],
        )
        self.assertEqual(self.stamped(revision), "stable-content")

    def test_a_git_package_stamped_from_other_content_is_cleaned_under_a_matching_record(
        self,
    ) -> None:
        # The record matches, but another record's run built `dep` from other
        # content since: the stamp, not the record, says what is on disk.
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=self.path_and_git_snapshot(revision))
        self.git_stamp(revision).write_text('{"content_digest": "edited-content"}', encoding="utf-8")
        self.assertEqual(
            self.cleaned_packages("first", snapshot=self.path_and_git_snapshot(revision)), ["dep"]
        )
        self.assertEqual(self.stamped(revision), "stable-content")

    def path_and_git_snapshot(self, revision: str) -> dict[str, object]:
        """`demo` (a path record whose identity moves with its own source)
        depending on `dep` (an unedited git checkout whose content is
        independent of it): a source-only change disagrees on `demo`'s path
        record while `dep`'s record stays byte-identical.
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

    def test_a_repeat_push_after_a_partial_clean_reuses_the_record(self) -> None:
        # A partial clean's record must be internally consistent: an
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

    def test_a_shape_change_cleans_every_path_package(self) -> None:
        # `dep`'s own record differs only in `features`, a shape field.
        # Which variants a shape change renamed cannot be read from the
        # snapshot (`cargo metadata` unifies features across `cfg` tables),
        # so every path package is cleaned and rediscovered under the name
        # the build uses.
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
        self.assertEqual(self.cleaned_packages("second", snapshot=snapshot(["f"])), ["demo", "dep"])

    def test_a_removed_dependency_cleans_its_former_dependents(self) -> None:
        # `dep` leaves the closure, so `demo` is renamed: Cargo's metadata
        # hash for `demo` no longer folds in `dep`'s.
        init_repo(self.root, "fn main() {}\n")
        edge = {"from": "workspace:demo#demo@0.1.0", "to": "workspace:dep#dep@0.1.0", "dep_kinds": [None]}
        before = {
            "root": "demo", "packages": path_records("demo", "dep"), "edges": [edge],
            "clean_packages": ["demo", "dep"], "digest": "before",
        }
        after = {
            "root": "demo", "packages": path_records("demo"), "edges": [],
            "clean_packages": ["demo"], "digest": "after",
        }
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=before)
        self.assertEqual(self.cleaned_packages("first", snapshot=after), ["demo"])

    def test_a_git_dependency_content_change_cleans_that_dependency(self) -> None:
        # `dep`'s checkout content changed while `demo`'s source did not.
        # Cargo never re-reads a git checkout, so `dep`'s artifacts may
        # predate the change and `dep` alone is cleaned.
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
        self.assertEqual(self.cleaned_packages("second", snapshot=snapshot("v2")), ["dep"])

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

    def test_a_changed_root_package_id_cleans_only_the_changed_packages(self) -> None:
        # A version bump renames the root package. Cargo rebuilds every unit
        # whose metadata hash that moves, so only `demo`, whose source
        # changed, is cleaned; the unedited git dependency is not.
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
            ["demo"],
        )

    def added_git_package(self) -> list[str]:
        """Add the git package `extra` beside a source change; return the cleaned packages."""
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
                "clean_packages": ["demo", "dep", "extra"] if include_extra else ["demo", "dep"],
            }
            value["digest"] = f"digest-{include_extra}-{revision}"
            return value

        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True, snapshot=snapshot(False, first_revision))
        second_revision = self.commit_source_change("fn main() { changed(); }\n", "change source")
        return self.cleaned_packages("second", snapshot=snapshot(True, second_revision))

    def test_an_added_git_package_is_not_cleaned(self) -> None:
        # A ritk-codecs push adding two dependencies cleaned all 35 packages
        # of its closure and held them exclusive through its command; 34
        # were git checkouts no one had edited. No stamp says `extra` was
        # built from other content, so only `demo`, whose source moved, is
        # cleaned.
        self.assertEqual(self.added_git_package(), ["demo"])

    def test_the_widen_loop_reaches_packages_the_first_read_missed(self) -> None:
        # `_stale_packages`'s first read may name fewer packages than a
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

        with patch.object(identity, "_stale_packages", side_effect=staged):
            cleaned = self.cleaned_packages("second")
        self.assertEqual(cleaned, ["demo", "dep"])
        self.assertGreaterEqual(calls["n"], 2)

    def test_a_partial_clean_discovers_only_the_packages_it_cleaned(self) -> None:
        # After a partial clean, artifact recording must discover only the
        # packages this run held exclusive -- never the whole closure, which
        # would walk a dependency directory a peer holds only shared.
        init_repo(self.root, "fn main() {}\n")
        (self.artifact.parent / "libdep-0ecdeded.rlib").write_bytes(b"dependency")
        self.dependency_build("first", discover=True)
        (self.root / "src" / "lib.rs").write_text("fn main() { changed(); }\n", encoding="utf-8")
        related_packages_seen: list[tuple[str, ...]] = []
        real_discover = artifacts.discover_artifacts
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
            patch.object(artifacts, "discover_artifacts", side_effect=spy_discover),
            patch.object(identity, "_run_checked", side_effect=skip_real_clean),
        ):
            result = self.dependency_build("second", discover=True, clean=False)
        self.assertEqual(result.status, "rebuilt")
        self.assertTrue(related_packages_seen)
        self.assertNotIn("dep", related_packages_seen[-1])

    def test_a_sibling_repository_identity_change_cleans_that_package(self) -> None:
        # `dep`'s own identity changed (its repository moved) while
        # `demo`'s did not: `_stale_packages` must still clean `dep`,
        # attributed through the path-record union -- `changed_packages`
        # alone has no recorded artifact-byte difference to find yet, since
        # `dep` has not been rebuilt from the new revision at all.
        init_repo(self.root, "fn main() {}\n")
        revision = git(self.root, "rev-parse", "HEAD")
        dep_repo = self.base / "dep-repo"
        dep_repo.mkdir()
        (dep_repo / "file.txt").write_text("a\n", encoding="utf-8")
        init_git(dep_repo, "t", "t@e.invalid")
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

    def test_a_root_manifest_change_cleans_only_its_own_package(self) -> None:
        # `demo`'s own repository changes only its Cargo.toml (a profile
        # edit here). Cargo builds the git dependency under the new profile
        # itself, as a new variant or in place, from its unedited checkout,
        # so only `demo`, whose source moved, is cleaned.
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
            ["demo"],
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
        # Both leases are held when the run asks for them. `demo` is released
        # once the run has been refused it, so the claim is still blocked at
        # `dep`, which stays held for the whole run. The run fixes one
        # deadline when it starts waiting, and its one claim waits against
        # it: a bound per lease would start a fresh 3 s at `dep`.
        init_repo(self.root, "fn main() {}\n")
        demo_lock, dep_lock = self.dep_lock("demo"), self.dep_lock("dep")
        release_dep = self.base / "release-dep"
        release_demo = self.base / "release-demo"
        demo_holder = start_holder(self, demo_lock, EXCLUSIVE, 0, stop=release_demo)
        dep_holder = start_holder(self, dep_lock, EXCLUSIVE, 0, stop=release_dep)
        requested: list[int | None] = []
        refusals: dict[Path, int] = {demo_lock: 0, dep_lock: 0}
        real_acquire = identity.acquire_claim
        real_blocker = lease_module._blocker

        clock = RecordedClock()

        def recording_acquire(leases, wait_seconds, deadline_ns=None, *args, **kwargs):
            requested.append(deadline_ns)
            # The run fixes its deadline once, when it starts: exactly the
            # 3 s bound after its one clock read. A deadline of any other
            # length fails whatever the host's speed, and it fails here,
            # before the run waits it out against the held `dep`.
            self.assertEqual(len(clock.reads), 1)
            self.assertEqual(deadline_ns, clock.reads[0] + 3_000_000_000)
            return real_acquire(leases, wait_seconds, deadline_ns, *args, **kwargs)

        def counting_blocker(lease):
            found = real_blocker(lease)
            if found is not None:
                refusals[lease.path] += 1
                if lease.path == demo_lock and demo_holder.poll() is None:
                    # Releasing the holder frees its OS lock and its place:
                    # the claim is next blocked at `dep` alone, with no timer
                    # to release `demo`.
                    release_demo.write_text("release", encoding="utf-8")
                    self.assertEqual(demo_holder.wait(60), 0)
            return found

        with (
            patch.object(identity, "acquire_claim", side_effect=recording_acquire),
            patch.object(identity, "time", clock),
            patch.object(lease_module, "_blocker", side_effect=counting_blocker),
        ):
            with self.assertRaises(identity.IdentityError) as caught:
                self.dependency_build("first", wait=3)
        refused_ns = time.monotonic_ns()
        self.assertIn("after waiting 3 s", str(caught.exception))
        # One claim, one deadline, and the run gave up only once it had passed.
        self.assertEqual(len(requested), 1)
        self.assertIsNotNone(requested[0])
        self.assertGreaterEqual(refused_ns, requested[0])
        # Each lease was held when asked for: the claim was refused at `demo`
        # before it was released, and at `dep` until the deadline.
        self.assertGreaterEqual(refusals[demo_lock], 1)
        self.assertGreaterEqual(refusals[dep_lock], 1)
        # `dep` was held with no clock: it lets go when told, not when a
        # timer runs out.
        self.assertIsNone(dep_holder.poll())
        release_dep.write_text("release", encoding="utf-8")
        self.assertEqual(dep_holder.wait(60), 0)

    def test_a_held_lease_is_refused_at_its_deadline(self) -> None:
        # Under a clock that moves only when the waiter sleeps, a claim whose
        # lease stays held is refused exactly at the deadline: each sleep is
        # cut to the time left, so no wait runs past it.
        clock = [0]

        class Clock:
            @staticmethod
            def monotonic_ns() -> int:
                return clock[0]

            @staticmethod
            def sleep(seconds: float) -> None:
                clock[0] += round(seconds * 1_000_000_000)

        # Sleeps of 0.1, 0.2, 0.4, 0.8 s, then the 1.5 s left: five waits
        # between six attempts, the last refused. A wait that never reached
        # its deadline would sleep for no time and ask again for ever, so the
        # claim allows twice those attempts and fails the test past them.
        analytic_attempts = 6
        attempts = [0]
        lease = OwnerLease(self.base / "held.lock", {"root": "waiter", "revision": "r"}, 60)

        def refuse(leases):
            attempts[0] += 1
            if attempts[0] > 2 * analytic_attempts:
                raise AssertionError(
                    f"the wait asked {attempts[0]} times without reaching its deadline"
                )
            return leases[0], LeaseHeldError("held", {"root": "holder", "revision": "r"})

        deadline_ns = 3_000_000_000
        with (
            patch.object(lease_module, "time", Clock),
            patch.object(lease_module, "_try_claim", side_effect=refuse),
            redirect_stderr(io.StringIO()),
            self.assertRaises(lease_module.BuildIdentityError) as caught,
        ):
            acquire_claim((lease,), 3, deadline_ns)
        self.assertEqual(clock[0], deadline_ns)
        self.assertIn("after waiting 3 s", str(caught.exception))
        self.assertEqual(attempts[0], analytic_attempts)

    def test_an_expired_owner_is_recovered(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            spec = build_inputs.build_spec(self.root, "demo", self.target, "debug", "host", "")
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
        self.assertFalse(lease_module.lease_is_held(lock))

    def test_an_unlocked_malformed_owner_is_reclaimed(self) -> None:
        # The OS lock is the ownership authority: an unlocked record cannot
        # name a live owner, and a writer killed mid-record leaves one partial.
        init_repo(self.root, "fn main() {}\n")
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            spec = build_inputs.build_spec(self.root, "demo", self.target, "debug", "host", "")
        lock = identity.lease_path(spec)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("not-json", encoding="utf-8")
        self.assertFalse(lease_module.lease_is_held(lock))
        result = self.build(source_token="reclaimed")
        self.assertEqual(result.status, "rebuilt")
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "reclaimed")

    def test_an_unlocked_owner_without_expiry_is_reclaimed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            spec = build_inputs.build_spec(self.root, "demo", self.target, "debug", "host", "")
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
        self.assertFalse(lease_module.lease_is_held(lock))
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            code, value = check.check_record(
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
        self.assertTrue(lease_module.lease_is_held(lock))
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
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            spec = build_inputs.build_spec(self.root, "demo", self.target, "debug", "host", "")
        start_holder(self, identity.lease_path(spec), SHARED, 60)
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            code, value = check.check_record(
                self.root,
                "demo",
                self.target,
                artifact_paths=[self.artifact],
                manifest=self.root / "Cargo.toml",
            )
        self.assertEqual((code, value["status"]), (2, "missing"))

    def test_toolchain_identity_runs_in_the_source_root(self) -> None:
        completed = subprocess.CompletedProcess(["rustc"], 0, "rustc 1.95.0\n", "")
        with patch.object(build_source.subprocess, "run", return_value=completed) as run:
            self.assertEqual(build_source.toolchain_identity(self.root), "rustc 1.95.0")
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
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            result = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                ("demo",),
                self.target,
                [sys.executable, str(command_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, "-c", "pass"],
                command_cwd=execution_root,
            )[0]
        record = json.loads(result.record_path.read_text(encoding="utf-8"))
        self.assertNotIn("command_cwd", record["build"])
        self.assertEqual(cwd_marker.read_text(encoding="utf-8"), str(execution_root.resolve()))

    def test_a_dirty_tree_is_not_identified_by_revision_alone(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = build_source.source_identity(self.root)
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        after = build_source.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)

    def test_untracked_and_ignored_files_are_listed_as_ls_files_lists_them(self) -> None:
        # The digest frames each untracked and ignored file in this order, so
        # one `git status` must list exactly what the two `ls-files --others`
        # listings it replaced list, in the same order, or every dirty tree's
        # identity changes.
        init_repo(self.root, "fn main() {}\n")
        # Rename detection on whatever the host configures, so the staged
        # rename below is reported as one.
        git(self.root, "config", "status.renames", "true")
        (self.root / ".gitignore").write_text("*.log\nbuild/\n/top-only\n!keep.log\n", encoding="utf-8")
        (self.root / "src" / ".gitignore").write_text("local.tmp\n", encoding="utf-8")
        # A staged rename reports its original path as a field of its own,
        # which `! orig.rs` would make read as an ignored file.
        (self.root / "! orig.rs").write_text("renamed whole\n", encoding="utf-8")
        git(self.root, "add", ".gitignore", "src/.gitignore", "! orig.rs")
        git(self.root, "commit", "-q", "-m", "ignore rules")
        git(self.root, "mv", "src/lib.rs", "src/moved.rs")
        git(self.root, "mv", "! orig.rs", "renamed.rs")
        (self.root / "Cargo.toml").write_text("[package]\nname = \"edited\"\n", encoding="utf-8")
        for name in (
            "new file.txt", "Zeta", "alpha", "ä-unicode.rs", "a.log", "keep.log", "top-only",
            "src/top-only", "src/local.tmp", "src/new.rs", "src/a-b", "src/a/b", "src/a.b",
            "build/out.o", "build/deep/x.o", "untracked/one.rs", "untracked/two.log",
            "untracked/build/y.o",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name, encoding="utf-8")
        (self.root / "nested").mkdir()
        git(self.root / "nested", "init", "-q")
        (self.root / "nested" / "inner.rs").write_text("inner", encoding="utf-8")
        listed = tuple(
            (marker, [path for path in build_source._git(self.root, *arguments).split(b"\0") if path])
            for marker, arguments in (
                (b"untracked", ("ls-files", "--others", "--exclude-standard", "-z")),
                (b"ignored", ("ls-files", "--others", "--ignored", "--exclude-standard", "-z")),
            )
        )
        self.assertIn(b"nested/", listed[0][1])
        self.assertIn(b"untracked/build/y.o", listed[1][1])
        self.assertNotIn(b"orig.rs", listed[1][1])
        self.assertEqual(build_source._untracked_paths(self.root.resolve()), listed)

    def test_a_top_level_path_holding_a_newline_is_read_whole(self) -> None:
        # POSIX allows a newline in a directory name, so the revision is
        # taken from the last line and the path from everything before it.
        revision = "0123456789abcdef0123456789abcdef01234567"
        cases = {
            "newline": (b"/srv/line\nbreak\n" + revision.encode() + b"\n", "line\nbreak"),
            "trailing newline": (b"/srv/line\n\n" + revision.encode() + b"\n", "line\n"),
            "trailing space": (b"/srv/trail \n" + revision.encode() + b"\n", "trail "),
            "plain": (b"/srv/plain\n" + revision.encode() + b"\n", "plain"),
        }
        for name, (printed, leaf) in cases.items():
            with self.subTest(name), patch.object(build_source, "_git", return_value=printed):
                top, found = build_source.repository_head(self.base)
            self.assertEqual(top.name, leaf)
            self.assertEqual(found, revision)
        for name, printed in {
            "no path": revision.encode() + b"\n",
            "no revision": b"/srv/plain\n\n",
        }.items():
            with self.subTest(name), patch.object(build_source, "_git", return_value=printed):
                with self.assertRaises(build_source.BuildIdentityError):
                    build_source.repository_head(self.base)

    def test_each_repository_is_identified_once_per_dependency_pass(self) -> None:
        # Every path package of one repository has that repository's
        # identity, so a pass computes it once, however many packages, and
        # however many of the selection's snapshots, share it.
        init_repo(self.root, "fn main() {}\n")
        (self.root / "member" / "src").mkdir(parents=True)
        (self.root / "untracked.rs").write_text("dirty\n", encoding="utf-8")
        sibling = self.base / "sibling"
        init_repo(sibling, "pub fn sibling() {}\n")
        identified: list[Path] = []
        real_worktree_identity = build_inputs.worktree_identity

        def counting_worktree_identity(top, *arguments):
            identified.append(top)
            return real_worktree_identity(top, *arguments)

        def snapshot(metadata, manifest, package, identify_source, content_digest):
            return {
                "identities": [
                    identify_source(path)
                    for path in (self.root, self.root / "member", self.root / "src", sibling)
                ]
            }

        with (
            patch.object(build_inputs, "worktree_identity", side_effect=counting_worktree_identity),
            patch.object(build_inputs, "dependency_snapshot", side_effect=snapshot),
            patch.object(build_inputs, "_cargo_metadata", return_value={}),
        ):
            data = build_inputs._dependency_data(
                self.root / "Cargo.toml", ("demo", "other"), self.target, self.root, (), False
            )
        self.assertEqual(identified, [self.root.resolve(), sibling.resolve()])
        self.assertEqual(sorted(data), ["demo", "other"])
        self.assertEqual(data["demo"]["identities"], data["other"]["identities"])
        root_identity, member_identity, source_identity, sibling_identity = data["demo"]["identities"]
        expected_root = build_records._content(
            build_source.source_identity(self.root, (self.target,)).as_dict()
        )
        self.assertTrue(expected_root["dirty"])
        self.assertEqual(root_identity, expected_root)
        self.assertEqual(member_identity, expected_root)
        self.assertEqual(source_identity, expected_root)
        self.assertEqual(
            sibling_identity,
            build_records._content(build_source.source_identity(sibling, (self.target,)).as_dict()),
        )
        self.assertNotEqual(sibling_identity, expected_root)

    def test_ignored_source_files_are_hashed_and_can_be_explicitly_excluded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        (self.root / ".gitignore").write_text("generated.rs\n", encoding="utf-8")
        git(self.root, "add", ".gitignore")
        git(self.root, "commit", "-q", "-m", "ignore generated source")
        clean = build_source.source_identity(self.root)
        (self.root / "generated.rs").write_text("first\n", encoding="utf-8")
        before = build_source.source_identity(self.root)
        (self.root / "generated.rs").write_text("second\n", encoding="utf-8")
        after = build_source.source_identity(self.root)
        self.assertTrue(after.dirty)
        self.assertNotEqual(before.tree_digest, after.tree_digest)
        excluded = build_source.source_identity(
            self.root, ignored_paths=(self.root / "generated.rs",)
        )
        self.assertFalse(excluded.dirty)
        self.assertEqual(excluded.tree_digest, clean.tree_digest)

    def test_target_files_do_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        before = build_source.source_identity(self.root)
        target = self.root / "target"
        target.mkdir()
        (target / "artifact.rlib").write_text("generated", encoding="utf-8")
        identity_value = build_source.source_identity(self.root, (target,))
        self.assertFalse(identity_value.dirty)
        self.assertEqual(identity_value.tree_digest, before.tree_digest)
        with self.assertRaises(identity.IdentityError):
            build_inputs.build_spec(self.root, "demo", self.root, "debug", "host", "")

    def test_explicit_ignored_lockfile_does_not_change_source_identity(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        lock = self.root / "Cargo.lock"
        lock.write_text("version = 4\n", encoding="utf-8")
        git(self.root, "add", "Cargo.lock")
        git(self.root, "commit", "-q", "-m", "lock")
        before = build_source.source_identity(self.root)
        lock.write_text("version = 4\nchanged\n", encoding="utf-8")
        after = build_source.source_identity(self.root, ignored_paths=(lock,))
        self.assertEqual(after.tree_digest, before.tree_digest)
        self.assertFalse(after.dirty)

    def test_build_environment_changes_change_the_record_scope(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=0"}):
                first = build_inputs.build_spec(self.root, "demo", self.target, "debug", "host", "")
            with patch.dict(os.environ, {"RUSTFLAGS": "-C debuginfo=2"}):
                second = build_inputs.build_spec(self.root, "demo", self.target, "debug", "host", "")
        self.assertNotEqual(first.environment_digest, second.environment_digest)
        self.assertNotEqual(build_records.record_path(first), build_records.record_path(second))

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
            with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
                first = build_inputs.build_spec(
                    self.root, "demo", self.target, "debug", "host", "",
                    command=["cargo", "check", "--config", "ci.toml"],
                    execution_root=execution_root,
                )
                config.write_text("[profile.dev]\nopt-level = 3\n", encoding="utf-8")
                second = build_inputs.build_spec(
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
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            first = build_inputs.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTFLAGS=-C debuginfo=0", "cargo", "build"],
            )
            second = build_inputs.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTFLAGS=-C debuginfo=2", "cargo", "build"],
            )
        self.assertNotEqual(first.environment_digest, second.environment_digest)

    def test_a_cargo_alias_environment_variable_changes_the_digest(self) -> None:
        # A `[alias]` table entry set as `CARGO_ALIAS_<NAME>` env can itself
        # carry compile-affecting flags (e.g. an alias that bakes in
        # `--config build.rustflags=[...]`); it must not be invisible to
        # this digest merely because it is not one of the fixed variables or
        # the other prefixes.
        base = build_source.environment_digest({})
        changed = build_source.environment_digest(
            {"CARGO_ALIAS_CLIPPY": 'check --config build.rustflags=["--cfg", "foo"]'}
        )
        self.assertNotEqual(base, changed)

    def test_a_build_directory_cleans_with_its_cargo_profile_and_target(self) -> None:
        # Cargo names the `debug/` directory's profile `dev`; every other
        # profile directory carries its profile's name, and a cross build
        # lives under its triple.
        target = Path("target")
        cases = {
            ("debug", "host"): ["--profile", "dev"],
            ("release", "host"): ["--profile", "release"],
            ("ci", "host"): ["--profile", "ci"],
            ("debug", "x86_64-unknown-linux-gnu"): [
                "--profile", "dev", "--target", "x86_64-unknown-linux-gnu"
            ],
        }
        for (profile, triple), expected in cases.items():
            with self.subTest(profile=profile, target=triple):
                self.assertEqual(
                    build_stamps.BuildDirectory(target, profile, triple).clean_arguments(), expected
                )
        record = {"name": "d", "source": "git+https://example.invalid/d#0"}
        stamps = {
            build_stamps.BuildDirectory(target, profile, triple).stamp(record) for profile, triple in cases
        }
        self.assertEqual(len(stamps), len(cases))

    def test_the_default_lib_metadata_variable_changes_the_digest(self) -> None:
        # Cargo folds `__CARGO_DEFAULT_LIB_METADATA` into every unit's
        # metadata hash, renaming every artifact a record names.
        base = build_source.environment_digest({})
        self.assertNotEqual(
            build_source.environment_digest({"__CARGO_DEFAULT_LIB_METADATA": "stable"}), base
        )

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
        # confirmed by a real run), so excluding a rustdoc-only flag here is
        # not "rustdoc's output is untracked" -- it is that Cargo's own
        # per-unit fingerprint for a `doc` unit already incorporates that
        # unit's effective rustdoc flags, so `cargo doc` unconditionally
        # re-invokes rustdoc (rewriting those fingerprint files) whenever
        # the flags differ, before this identity scheme ever reads the
        # result; `run_build`'s matched branch then adopts whatever bytes
        # Cargo just wrote into the record rather than checking them
        # against a prior expectation, because Cargo already enforced
        # freshness. Splitting the shared record here made a real
        # three-step push clean the whole closure on every push instead of
        # once.
        init_repo(self.root, "fn main() {}\n")
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            clippy = build_inputs.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["cargo", "clippy"], command_key="shared",
            )
            doc_a = build_inputs.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTDOCFLAGS=-D warnings", "cargo", "doc"], command_key="shared",
            )
            doc_b = build_inputs.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", "RUSTDOCFLAGS=--cfg docsrs", "cargo", "doc"], command_key="shared",
            )
        self.assertEqual(clippy.environment_digest, doc_a.environment_digest)
        self.assertEqual(doc_a.environment_digest, doc_b.environment_digest)
        self.assertEqual(build_records.record_path(clippy), build_records.record_path(doc_a))

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
        arguments = build_inputs._config_arguments(["cargo", "check", "--config", 'include=["x.toml"]'])
        first = build_source.cargo_config_digest(execution_root, arguments)
        included.write_text('[build]\nrustflags = ["--cfg", "bar"]\n', encoding="utf-8")
        second = build_source.cargo_config_digest(execution_root, arguments)
        self.assertNotEqual(first, second)

    def test_a_bom_prefixed_config_include_is_followed(self) -> None:
        # Cargo's own config parser accepts a leading UTF-8 BOM; this digest
        # must strip it before parsing rather than treating a BOM-only
        # config as unparseable and silently dropping its `include`.
        execution_root = self.base / "execution-bom"
        (execution_root / ".cargo").mkdir(parents=True)
        included = execution_root / ".cargo" / "included.toml"
        included.write_text("[profile.dev]\nopt-level = 0\n", encoding="utf-8")
        (execution_root / ".cargo" / "config.toml").write_bytes(
            b"\xef\xbb\xbf" + b'include = ["included.toml"]\n'
        )
        first = build_source.cargo_config_digest(execution_root)
        included.write_text("[profile.dev]\nopt-level = 3\n", encoding="utf-8")
        second = build_source.cargo_config_digest(execution_root)
        self.assertNotEqual(first, second)

    def test_a_config_tomllib_cannot_parse_fails_closed(self) -> None:
        # Cargo's TOML grammar is looser than `tomllib`'s strict TOML 1.0 in
        # several ways -- a trailing comma after an inline table's last
        # element, an inline table split across lines, and the TOML 1.1
        # string escapes `\e`/`\xHH` are all accepted by Cargo and rejected
        # by `tomllib`. Silently returning on that parse failure would
        # under-hash a config whose `include` this digest can no longer see;
        # it must instead fail closed by raising, naming the offending file.
        # The pre-push hook's `classify_gate_step` routes the raised
        # `atlas-build-identity:`-prefixed error through its *identity*
        # branch ("source identity blocked ... no artifact was accepted"),
        # never its *environment* branch -- the two are classified
        # differently and this is not the latter.
        for label, text in (
            ("trailing comma", b'include = [{ path = "extra.toml", },]\n'),
            (
                "multi-line inline table",
                b'include = [\n  { path = "extra.toml",\n    optional = true },\n]\n',
            ),
        ):
            with self.subTest(label):
                execution_root = self.base / f"execution-unparseable-{label.replace(' ', '-')}"
                (execution_root / ".cargo").mkdir(parents=True)
                (execution_root / ".cargo" / "extra.toml").write_text(
                    "[profile.dev]\nopt-level = 0\n", encoding="utf-8"
                )
                config_path = execution_root / ".cargo" / "config.toml"
                config_path.write_bytes(text)
                with self.assertRaises(identity.IdentityError) as raised:
                    build_source.cargo_config_digest(execution_root)
                self.assertIn(str(config_path), str(raised.exception))

    def test_an_inline_env_cargo_home_is_used_for_the_home_config(self) -> None:
        # `env CARGO_HOME=<h> cargo ...` changes which `config.toml` Cargo
        # reads for its home configuration; `build_spec` must resolve
        # `CARGO_HOME` from that same inline prefix, not only `os.environ`,
        # or an override the command itself sets is invisible to the
        # configuration digest.
        init_repo(self.root, "fn main() {}\n")
        home = self.base / "cargo-home"
        (home).mkdir(parents=True)
        (home / "config.toml").write_text(
            '[build]\nrustflags = ["--cfg", "foo"]\n', encoding="utf-8"
        )
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            first = build_inputs.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", f"CARGO_HOME={home}", "cargo", "check"],
                execution_root=self.root,
            )
            (home / "config.toml").write_text(
                '[build]\nrustflags = ["--cfg", "foo", "--cfg", "bar"]\n', encoding="utf-8"
            )
            second = build_inputs.build_spec(
                self.root, "demo", self.target, "debug", "host", "",
                command=["env", f"CARGO_HOME={home}", "cargo", "check"],
                execution_root=self.root,
            )
        self.assertNotEqual(first.cargo_config_digest, second.cargo_config_digest)

    def test_an_included_config_cycle_does_not_hang(self) -> None:
        # An included file naming its own includer, directly or through a
        # chain, must not recurse forever. `seen` also guards the digest
        # itself: the second time `config.toml` is reached (through the
        # cycle back from `b.toml`), its content must contribute a `seen`
        # marker, not its bytes again -- the content is hashed exactly once
        # per file regardless of how many times the walk reaches it.
        execution_root = self.base / "execution-cycle"
        (execution_root / ".cargo").mkdir(parents=True)
        # `newline=""` (not the default `write_text`) so the bytes on disk
        # are exactly `config_bytes` on every platform -- this test compares
        # raw bytes fed to the digest, and Windows' universal-newline
        # translation would otherwise turn `\n` into `\r\n` on write,
        # silently breaking the byte-for-byte comparison below.
        config_bytes = b'include = ["b.toml"]\n'
        (execution_root / ".cargo" / "config.toml").write_bytes(config_bytes)
        (execution_root / ".cargo" / "b.toml").write_bytes(
            b'include = ["config.toml"]\n'
        )
        fed: list[bytes] = []
        original = build_source._feed_framed

        def spy(digest: object, chunk: bytes) -> None:
            fed.append(bytes(chunk))
            original(digest, chunk)

        with patch.object(build_source, "_feed_framed", side_effect=spy):
            digest = build_source.cargo_config_digest(execution_root)
        self.assertEqual(len(digest), 64)
        self.assertEqual(fed.count(config_bytes), 1)

    def test_source_changes_during_build_are_not_recorded(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        changed = self.root / "src/lib.rs"
        with (
            patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"),
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
                ("demo",),
                self.target,
                [sys.executable, str(self.build_script)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
            )[0]
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            spec = build_inputs.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                [sys.executable, str(self.build_script)],
            )
        self.assertFalse(build_records.record_path(spec).exists())

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
            paths = artifacts.discover_artifacts(
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
        with patch.object(build_snapshot, "_cargo_metadata", return_value=metadata):
            first = build_snapshot.dependency_snapshot(
                build_snapshot._cargo_metadata(self.root / "Cargo.toml", self.root, no_deps=False), self.root / "Cargo.toml", "demo",
                lambda path: {"root": path.as_posix(), "revision": "a"},
                package_source.package_source_digest,
            )
            second = build_snapshot.dependency_snapshot(
                build_snapshot._cargo_metadata(self.root / "Cargo.toml", self.root, no_deps=False), self.root / "Cargo.toml", "demo",
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
            (workspace / "Cargo.toml").write_text(
                "[workspace]\nmembers = [\"crates/*\"]\n", encoding="utf-8"
            )
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
            with patch.object(build_snapshot, "_cargo_metadata", return_value=metadata):
                snapshots.append(build_snapshot.dependency_snapshot(
                    build_snapshot._cargo_metadata(workspace / "Cargo.toml", workspace, no_deps=False), workspace / "Cargo.toml", "demo",
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
        with patch.object(build_snapshot, "_cargo_metadata", return_value=metadata):
            first = build_snapshot.dependency_snapshot(
                build_snapshot._cargo_metadata(self.root / "Cargo.toml", self.root, no_deps=False), self.root / "Cargo.toml", "demo",
                lambda path: {"root": path.as_posix(), "revision": "a"},
                package_source.package_source_digest,
            )
            source.write_text("pub fn value() -> u8 { 2 }\n", encoding="utf-8")
            second = build_snapshot.dependency_snapshot(
                build_snapshot._cargo_metadata(self.root / "Cargo.toml", self.root, no_deps=False), self.root / "Cargo.toml", "demo",
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
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            with self.assertRaises(identity.IdentityError):
                identity.run_build(
                    self.root,
                    self.root / "Cargo.toml",
                    ("demo",),
                    self.target,
                    [sys.executable, str(self.build_script)],
                    artifact_paths=[outside],
                    clean_command=[sys.executable, str(self.clean_script)],
                )[0]
        self.assertFalse(self.clean_log.exists())

    def test_dependency_transition_cleans_the_reachable_path_packages(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        snapshot = {
            "root": "demo",
            "packages": path_records("demo", "dep"),
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
            patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"),
            patch.object(build_inputs, "dependency_snapshot", return_value=snapshot),
            patch.object(identity, "artifact_identity", return_value=artifact_value),
            patch.object(artifacts, "recorded_artifact_identity", return_value=artifact_value),
            patch.object(build_records, "recorded_artifact_identity", return_value=artifact_value),
            patch.object(identity, "_run_checked", side_effect=run_command),
        ):
            first = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                ("demo",),
                self.target,
                [sys.executable, "-c", "pass"],
            )[0]
            second = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                ("demo",),
                self.target,
                [sys.executable, "-c", "pass"],
            )[0]
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
        for version in (1, 2, 3, 4, 5):
            record.write_text(json.dumps({"version": version}), encoding="utf-8")
            self.assertIsNone(build_records.read_record(record))

    def test_malformed_records_fail_closed(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"):
            spec = build_inputs.build_spec(
                self.root,
                "demo",
                self.target,
                "debug",
                "host",
                "",
                [sys.executable, str(self.build_script)],
            )
            record = build_records.record_path(spec)
            record.parent.mkdir(parents=True, exist_ok=True)
            record.write_text('{"version": true}', encoding="utf-8")
            with self.assertRaises(identity.IdentityError):
                check.check_record(
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
            artifacts.artifact_identity(
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
        before = build_source.source_identity(self.root)
        lock.write_text("# rewritten by the gate\n", encoding="utf-8")
        self.assertEqual(build_source.source_identity(self.root, ignored_paths=(lock,)), before)
        self.assertTrue(build_source.source_identity(self.root).dirty)
        (self.root / "src/lib.rs").write_text("fn main() { let _c = 1; }\n", encoding="utf-8")
        self.assertTrue(build_source.source_identity(self.root, ignored_paths=(lock,)).dirty)

    def test_an_ignored_path_outside_the_source_tree_is_rejected(self) -> None:
        init_repo(self.root, "fn main() {}\n")
        with self.assertRaises(identity.IdentityError):
            build_source.source_identity(
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
            patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"),
            patch.dict(
                os.environ,
                {"ARTIFACT": str(self.artifact), "SOURCE_TOKEN": "cwd", "CLEAN_LOG": str(self.clean_log)},
            ),
        ):
            identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                ("demo",),
                self.target,
                [sys.executable, str(record_cwd)],
                artifact_paths=[self.artifact],
                clean_command=[sys.executable, str(self.clean_script)],
                command_cwd=elsewhere,
            )[0]
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


# Run as the build command: records how each named lease answers a request
# from another process while run_build holds its leases around the command.
LEASE_PROBE = (
    "import json, sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from atlas_build_lease import LeaseHeldError, OwnerLease\n"
    "answers = {}\n"
    "for name, lock, mode in json.loads(sys.argv[3]):\n"
    "    lease = OwnerLease(Path(lock), {'root': 'probe', 'revision': 'r'}, 60, mode=mode)\n"
    "    try:\n"
    "        lease.__enter__()\n"
    "    except LeaseHeldError:\n"
    "        answers[f'{name}:{mode}'] = 'refused'\n"
    "        continue\n"
    "    lease.__exit__(None, None, None)\n"
    "    answers[f'{name}:{mode}'] = 'granted'\n"
    "Path(sys.argv[2]).write_text(json.dumps(answers, sort_keys=True), encoding='utf-8')\n"
)


# Asks for the exclusive lock and blocks until the kernel grants it, then
# reports whether the holder had already marked its release.
BLOCKED_WRITER = (
    "import os, sys\n"
    "from pathlib import Path\n"
    "handle = open(sys.argv[1], 'r+b')\n"
    "if os.name == 'nt':\n"
    "    import ctypes, msvcrt\n"
    "    from ctypes import wintypes\n"
    "    class Overlapped(ctypes.Structure):\n"
    "        _fields_ = [('Internal', ctypes.c_void_p), ('InternalHigh', ctypes.c_void_p),\n"
    "                    ('Offset', wintypes.DWORD), ('OffsetHigh', wintypes.DWORD),\n"
    "                    ('hEvent', wintypes.HANDLE)]\n"
    "    kernel = ctypes.WinDLL('kernel32', use_last_error=True)\n"
    "    overlapped = Overlapped()\n"
    "    assert kernel.LockFileEx(wintypes.HANDLE(msvcrt.get_osfhandle(handle.fileno())),\n"
    "                             2, 0, 1, 0, ctypes.byref(overlapped))\n"
    "else:\n"
    "    import fcntl\n"
    "    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)\n"
    "print('after release' if Path(sys.argv[2]).exists() else 'while held', flush=True)\n"
)


class LeaseDowngradeTestCase(unittest.TestCase):
    """A held exclusive lease becomes shared without leaving its place in the queue."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-lease-downgrade-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.lock = self.base / "scope" / "scope.lock"
        self.lock.parent.mkdir(parents=True)

    def hold(self) -> OwnerLease:
        holder = acquire_lease(
            OwnerLease(self.lock, {"root": "holder", "revision": "r"}, 60, mode=EXCLUSIVE), 60
        )
        self.addCleanup(holder.__exit__, None, None, None)
        return holder

    def test_the_downgrade_never_frees_the_lease(self) -> None:
        # A writer without a ticket blocks in the kernel for the exclusive
        # lock: the kernel grants it at the first instant the lease is free,
        # so it must find the holder's release marker already written.
        holder = self.hold()
        released = self.base / "released"
        prober = subprocess.Popen(
            [sys.executable, "-c", BLOCKED_WRITER, str(self.lock), str(released)],
            stdout=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(prober.kill)
        # Let the writer reach its blocking request; one that has not yet
        # made it only lowers this test's power, never its verdict.
        time.sleep(0.5)
        holder.downgrade()
        time.sleep(0.2)
        released.write_text("", encoding="utf-8")
        holder.__exit__(None, None, None)
        output, _ = prober.communicate(timeout=30)
        self.assertEqual(output.strip(), "after release")

    def test_a_collected_ticket_is_filed_again_before_the_conversion(self) -> None:
        # The ticket is what makes a POSIX racer back off, so one a peer's
        # collection removed is filed again before the lock converts.
        holder = self.hold()
        original = holder.ticket.path
        names = queue_module._names
        asked = []

        def collected_once(path, handle) -> bool:
            if not asked:
                asked.append(path)
                return False
            return names(path, handle)

        converted_under = []

        def converting(handle) -> None:
            converted_under.append(holder.ticket.path)
            lock_module._downgrade(handle)

        with (
            patch.object(queue_module, "_names", side_effect=collected_once),
            patch.object(lease_module, "_downgrade", side_effect=converting),
        ):
            holder.downgrade()
        self.assertEqual(asked, [original])
        self.assertEqual(len(converted_under), 1)
        self.assertNotEqual(converted_under[0], original)
        self.assertIn("-x-", converted_under[0].name)

    def test_a_failed_conversion_holds_and_reports_nothing(self) -> None:
        holder = self.hold()
        with patch.object(
            lease_module, "_downgrade", side_effect=BuildIdentityError("lost the lease")
        ):
            with self.assertRaises(BuildIdentityError):
                holder.downgrade()
        self.assertEqual((holder.held, holder.handle), (False, None))
        holder.__exit__(None, None, None)
        taker = acquire_lease(
            OwnerLease(self.lock, {"root": "next", "revision": "r"}, 60, mode=EXCLUSIVE), 0
        )
        self.addCleanup(taker.__exit__, None, None, None)
        self.assertTrue(taker.held)

    def test_a_downgraded_lease_admits_readers_and_still_excludes_writers(self) -> None:
        holder = self.hold()
        self.assertEqual(request(self.lock, SHARED), "refused")
        holder.downgrade()
        self.assertEqual(holder.mode, SHARED)
        self.assertEqual(request(self.lock, SHARED), "granted")
        self.assertEqual(request(self.lock, EXCLUSIVE), "refused")
        holder.__exit__(None, None, None)
        self.assertEqual(request(self.lock, EXCLUSIVE), "granted")

    def test_a_writer_queued_before_the_downgrade_stays_behind_the_holder(self) -> None:
        holder = self.hold()
        writer = OwnerLease(self.lock, {"root": "writer", "revision": "r"}, 60, mode=EXCLUSIVE)
        self.addCleanup(writer.__exit__, None, None, None)
        with self.assertRaises(LeaseHeldError):
            writer.attempt()
        holder.downgrade()
        with self.assertRaises(LeaseHeldError):
            writer.attempt()
        # A reader arriving after the queued writer waits behind it.
        self.assertEqual(request(self.lock, SHARED), "refused")
        holder.__exit__(None, None, None)
        self.assertIs(writer.attempt(), writer)
        self.assertTrue(writer.held)

    def test_a_shared_lease_is_left_as_it_is(self) -> None:
        reader = acquire_lease(
            OwnerLease(self.lock, {"root": "reader", "revision": "r"}, 60, mode=SHARED), 60
        )
        self.addCleanup(reader.__exit__, None, None, None)
        ticket = reader.ticket
        reader.downgrade()
        self.assertIs(reader.ticket, ticket)
        self.assertEqual(request(self.lock, SHARED), "granted")


class CommandLeaseModeTestCase(unittest.TestCase):
    """Which scopes run_build holds exclusive while the build command runs."""

    PACKAGES = ("demo", "dep", "dep2")

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-command-lease-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.root = self.base / "source"
        self.target = self.base / "shared-target"
        deps = self.target / "debug" / "deps"
        deps.mkdir(parents=True)
        self.artifacts = {name: deps / f"lib{name}-abcdef.rlib" for name in self.PACKAGES}
        for name, path in self.artifacts.items():
            path.write_text(name, encoding="utf-8")
        self.answers = self.base / "answers.json"
        self.probe = self.base / "probe.py"
        self.clean = self.base / "clean.py"
        write_script(self.probe, LEASE_PROBE)
        write_script(
            self.clean,
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['ARTIFACT']).write_text('rebuilt', encoding='utf-8')\n"
            "if os.environ.get('RETIRE'):\n"
            "    Path(os.environ['RETIRE']).unlink()\n"
            "    Path(os.environ['REPLACEMENT']).write_text('renamed', encoding='utf-8')\n",
        )
        init_repo(self.root, "fn main() {}\n")

    def build(
        self,
        command_key: str,
        *,
        declared: bool = True,
        clean_command: list[str] | None = None,
        unreadable: Path | None = None,
        torn_first_read: bool = False,
    ) -> dict[str, str]:
        """Run one gate step whose command asks for each lease; return the answers.

        `declared` passes the root artifact as the record's only path; without
        it the closure's artifacts are found by `discover_artifacts`.
        `unreadable` names a file every hash of which fails once the command
        has run, as a Windows reader sees one a peer's rustc holds open for
        writing. `torn_first_read` makes the shared first read of the record's
        artifacts see a peer's rewrite in flight, so the run retakes its leases
        exclusive and reads again.
        """
        requests = [
            [name, str(package_target_lease_path(name, self.target)), SHARED]
            for name in self.PACKAGES
        ]
        requests.append(["dep", str(package_target_lease_path("dep", self.target)), EXCLUSIVE])
        snapshot = {
            "root": "demo",
            "packages": path_records(*self.PACKAGES),
            "edges": [],
            "clean_packages": list(self.PACKAGES),
            "digest": "closure",
        }
        owners = {name: frozenset({name}) for name in self.PACKAGES}
        file_digest = artifacts._file_digest

        def digest(path: Path) -> str:
            if unreadable is not None and Path(path) == unreadable and self.answers.exists():
                raise BuildIdentityError(f"cannot hash artifact {path}: Permission denied")
            return file_digest(path)

        recorded_artifact = identity._recorded_artifact
        reads = []

        def artifact_read(existing, target_dir, paths):
            reads.append(None)
            if torn_first_read and len(reads) == 1:
                return {"files": {}, "digest": "torn"}
            return recorded_artifact(existing, target_dir, paths)

        self.answers.unlink(missing_ok=True)
        with (
            patch.object(identity, "_recorded_artifact", side_effect=artifact_read),
            patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"),
            patch.object(identity, "_dependency_data", return_value={"demo": snapshot}),
            patch.object(artifacts, "_workspace_artifact_owners", return_value=owners),
            patch.object(artifacts, "_file_digest", side_effect=digest),
            patch.object(identity, "_cargo_command", return_value=(sys.executable, str(self.clean))),
            patch.dict(os.environ, {"ARTIFACT": str(self.artifacts["demo"])}),
        ):
            self.result = identity.run_build(
                self.root,
                self.root / "Cargo.toml",
                ("demo",),
                self.target,
                [
                    sys.executable,
                    str(self.probe),
                    str(SCRIPT.parent),
                    str(self.answers),
                    json.dumps(requests),
                ],
                artifact_paths=[self.artifacts["demo"]] if declared else [],
                clean_command=clean_command,
                command_key=command_key,
                lease_wait_seconds=0,
            )[0]
        return json.loads(self.answers.read_text(encoding="utf-8"))

    def recorded(self) -> dict[str, str]:
        record = json.loads(self.result.record_path.read_text(encoding="utf-8"))
        return {
            relative.rsplit("/", 1)[-1]: digest
            for relative, digest in record["artifact"]["files"].items()
        }

    def test_cleaned_dependencies_stay_exclusive_through_the_command(self) -> None:
        # No record and no sibling: the whole closure is cleaned and rebuilt.
        self.assertEqual(
            self.build("clippy", declared=False),
            {
                "demo:shared": "refused",
                "dep2:shared": "refused",
                "dep:exclusive": "refused",
                "dep:shared": "refused",
            },
        )

    def test_a_custom_clean_keeps_every_scope_exclusive(self) -> None:
        # What a custom clean deletes is unknown, so nothing is only read.
        self.build("clippy", declared=False)
        self.assertEqual(
            self.build(
                "nextest",
                declared=False,
                clean_command=[sys.executable, str(self.clean)],
            )["dep:shared"],
            "granted",
        )
        self.artifacts["dep"].write_text("changed", encoding="utf-8")
        self.assertEqual(
            self.build(
                "nextest",
                declared=False,
                clean_command=[sys.executable, str(self.clean)],
            ),
            {
                "demo:shared": "refused",
                "dep2:shared": "refused",
                "dep:exclusive": "refused",
                "dep:shared": "refused",
            },
        )

    def test_uncleaned_dependencies_are_shared_while_the_command_runs(self) -> None:
        self.build("clippy", declared=False)
        # A second step's key has no record of its own but a matching sibling:
        # it cleans nothing, so only its own package stays exclusive.
        self.assertEqual(
            self.build("nextest", declared=False),
            {
                "demo:shared": "refused",
                "dep2:shared": "granted",
                "dep:exclusive": "refused",
                "dep:shared": "granted",
            },
        )

    def test_an_exact_match_after_the_exclusive_retake_shares_the_dependencies(self) -> None:
        # The shared read caught a peer mid-rewrite; the exclusive retake finds
        # the record matching, so nothing is cleaned and the rest is only read.
        self.build("clippy", declared=False)
        self.assertEqual(
            self.build("clippy", declared=False, torn_first_read=True),
            {
                "demo:shared": "refused",
                "dep2:shared": "granted",
                "dep:exclusive": "refused",
                "dep:shared": "granted",
            },
        )
        self.assertEqual(self.result.status, "reused")

    def test_declared_artifact_paths_keep_every_scope_exclusive(self) -> None:
        # A record of declared paths names none of the closure's files, so a
        # sibling of it cannot name what the shared packages hold.
        self.build("clippy")
        self.assertEqual(self.build("nextest")["dep:shared"], "refused")

    def test_a_partial_clean_shares_the_packages_it_left_alone(self) -> None:
        self.build("clippy", declared=False)
        # Only dep2's bytes changed, so only dep2 is cleaned and rebuilt.
        self.artifacts["dep2"].write_text("changed", encoding="utf-8")
        self.assertEqual(
            self.build("clippy", declared=False),
            {
                "demo:shared": "refused",
                "dep2:shared": "refused",
                "dep:exclusive": "refused",
                "dep:shared": "granted",
            },
        )

    def test_a_partial_rebuild_records_its_new_names_only(self) -> None:
        self.build("clippy", declared=False)
        self.artifacts["dep2"].write_text("changed", encoding="utf-8")
        replacement = self.artifacts["dep2"].with_name("libdep2-fedcba.rlib")
        with patch.dict(
            os.environ,
            {"RETIRE": str(self.artifacts["dep2"]), "REPLACEMENT": str(replacement)},
        ):
            self.build("clippy", declared=False)
        self.assertEqual(
            sorted(self.recorded()),
            ["libdemo-abcdef.rlib", "libdep-abcdef.rlib", "libdep2-fedcba.rlib"],
        )

    def test_a_sibling_naming_a_retired_file_keeps_the_closure_exclusive(self) -> None:
        # A peer's clean and rebuild of dep under another variant retired the
        # name the sibling lists, so the sibling cannot name dep's files.
        self.build("clippy", declared=False)
        replacement = self.artifacts["dep"].with_name("libdep-111111.rlib")
        self.artifacts["dep"].unlink()
        replacement.write_text("variant", encoding="utf-8")
        self.assertEqual(self.build("nextest", declared=False)["dep:shared"], "refused")
        self.assertEqual(
            sorted(self.recorded()),
            ["libdemo-abcdef.rlib", "libdep-111111.rlib", "libdep2-abcdef.rlib"],
        )

    def test_a_shared_dependency_a_peer_is_writing_keeps_its_recorded_digest(self) -> None:
        # A peer admitted to dep's shared lease rewrites libdep while this
        # run records: dep is found by the sibling's name and keeps the
        # sibling's digest, and the run completes instead of failing.
        self.build("clippy", declared=False)
        sibling = self.recorded()
        self.build("nextest", declared=False, unreadable=self.artifacts["dep"])
        self.assertEqual(self.result.status, "reused")
        self.assertEqual(self.recorded()["libdep-abcdef.rlib"], sibling["libdep-abcdef.rlib"])
        self.assertEqual(
            self.recorded()["libdep2-abcdef.rlib"],
            hashlib.sha256(b"dep2").hexdigest(),
        )


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
        init_git(self.source)
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
            if (names := cleaned_names(command)) is not None:
                cleaned[-1].extend(names)
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
                    ("p",),
                    self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"],
                    command_cwd=export,
                )[0]
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
        init_git(self.d)
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
        init_git(self.source)
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(self, pushes: int, *, reconfigure_before: int, mode: str) -> list[identity.BuildResult]:
        # No source edit at `reconfigure_before`: before any partial clean existed,
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
                        export, export / "Cargo.toml", ("p",), self.base / "target",
                        ["cargo", "check", "-p", "p", "-q", "--offline"], command_cwd=export,
                    )[0]
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
            "[workspace]\n\n[features]\nf = []\n",
            "src/lib.rs": "pub fn d() -> u32 {\n    1\n}\n",
        }.items():
            (self.drepo / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.drepo / relative).write_text(text, encoding="utf-8")
        init_git(self.drepo)
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
        init_git(self.source)
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(
        self,
        pushes: int,
        *,
        change_p_before: int | None = None,
        change_d_before: int | None = None,
        p_manifest_before: tuple[int, str] | None = None,
        d_manifest_before: tuple[int, str] | None = None,
    ) -> list[list[str]]:
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if (names := cleaned_names(command)) is not None:
                cleaned[-1].extend(names)
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
                if p_manifest_before is not None and push == p_manifest_before[0]:
                    (self.source / "Cargo.toml").write_bytes(p_manifest_before[1].encode())
                    git(self.source, "commit", "-qam", "change p's manifest")
                if d_manifest_before is not None and push == d_manifest_before[0]:
                    (self.drepo / "Cargo.toml").write_bytes(d_manifest_before[1].encode())
                    git(self.drepo, "commit", "-qam", "change d's manifest")
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
                    ("p",),
                    self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"],
                    command_cwd=export,
                )[0]
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

    def p_manifest(self, tail: str) -> str:
        return (
            '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n'
            f'[workspace]\n\n[dependencies]\nd = {{ path = "{self.drepo.as_posix()}" }}\n{tail}'
        )

    def assert_record_names_the_d_on_disk(self) -> None:
        # The record names exactly the `d` variant the target holds: a
        # renamed `d` left unrecorded would sit beside the recorded one.
        record = json.loads(self.last_result.record_path.read_text(encoding="utf-8"))
        named_d = {
            Path(relative).name
            for relative in record["artifact"]["files"]
            if Path(relative).name.startswith(("libd-", "d-"))
        }
        deps_dir = self.base / "target" / "debug" / "deps"
        on_disk_d = {path.name for path in deps_dir.iterdir() if path.name.startswith(("libd-", "d-"))}
        self.assertTrue(named_d)
        self.assertEqual(named_d, on_disk_d)

    def test_a_feature_moved_out_of_a_never_true_cfg_table_cleans_d(self) -> None:
        # `cargo metadata` unifies `d`'s features across `cfg` tables, so
        # `d`'s record lists `f` both before and after; only `p`'s resolved
        # manifest moves, and Cargo renames `d`, now built with `f`.
        never = "\n[target.'cfg(any())'.dependencies]\nd = { path = \"%s\", features = [\"f\"] }\n" % (
            self.drepo.as_posix()
        )
        (self.source / "Cargo.toml").write_bytes(self.p_manifest(never).encode())
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "commit", "-qam", "d's feature under a never-true cfg")
        plain = (
            '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n'
            f'[workspace]\n\n[dependencies]\nd = {{ path = "{self.drepo.as_posix()}", features = ["f"] }}\n'
        )
        cleaned = self.push(3, p_manifest_before=(2, plain))
        self.assertEqual(cleaned, [["d", "p"], [], ["d", "p"]])
        self.assert_record_names_the_d_on_disk()

    def test_a_feature_moved_in_a_dependency_manifest_cleans_every_path_package(self) -> None:
        # `d`'s manifest, not the workspace's, moves a feature of `e` (a
        # third repository) out of a never-true `cfg` table. `e`'s record
        # lists `f` both times, its repository never moves, and the edge's
        # kinds are unchanged, so only `d`'s resolved manifest says `e` was
        # renamed.
        erepo = self.base / "erepo"
        for relative, text in {
            "Cargo.toml": '[package]\nname = "e"\nversion = "0.1.0"\nedition = "2021"\n'
            "[workspace]\n\n[features]\nf = []\n",
            "src/lib.rs": "pub fn e() -> u32 {\n    2\n}\n",
        }.items():
            (erepo / relative).parent.mkdir(parents=True, exist_ok=True)
            (erepo / relative).write_text(text, encoding="utf-8")
        init_git(erepo)
        git(erepo, "add", ".")
        git(erepo, "commit", "-q", "-m", "e")

        def d_manifest(e_table: str) -> str:
            return (
                '[package]\nname = "d"\nversion = "0.1.0"\nedition = "2021"\n'
                f"[workspace]\n\n[features]\nf = []\n\n[dependencies]\n{e_table}"
            )

        e = erepo.as_posix()
        (self.drepo / "Cargo.toml").write_bytes(
            d_manifest(
                f'e = {{ path = "{e}" }}\n\n'
                f"[target.'cfg(any())'.dependencies]\n"
                f'e = {{ path = "{e}", features = ["f"] }}\n'
            ).encode()
        )
        git(self.drepo, "commit", "-qam", "d depends on e")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "commit", "-qam", "lock e")
        # Both tables keep their entry, so the edge's kinds stay as they were.
        moved = d_manifest(
            f'e = {{ path = "{e}", features = ["f"] }}\n\n'
            f"[target.'cfg(any())'.dependencies]\n"
            f'e = {{ path = "{e}" }}\n'
        )
        cleaned = self.push(3, d_manifest_before=(2, moved))
        self.assertEqual(cleaned, [["d", "e", "p"], [], ["d", "e", "p"]])
        record = json.loads(self.last_result.record_path.read_text(encoding="utf-8"))
        named_e = {
            Path(relative).name
            for relative in record["artifact"]["files"]
            if Path(relative).name.startswith(("libe-", "e-"))
        }
        deps_dir = self.base / "target" / "debug" / "deps"
        on_disk_e = {path.name for path in deps_dir.iterdir() if path.name.startswith(("libe-", "e-"))}
        self.assertTrue(named_e)
        self.assertEqual(named_e, on_disk_e)

    def test_a_root_profile_edit_cleans_d(self) -> None:
        # The workspace manifest's `[profile]` tables enter every unit's
        # metadata hash and no package entry, so `d` is renamed too.
        profile = "\n[profile.dev]\ndebug-assertions = false\n"
        cleaned = self.push(3, p_manifest_before=(2, self.p_manifest(profile)))
        self.assertEqual(cleaned, [["d", "p"], [], ["d", "p"]])
        self.assert_record_names_the_d_on_disk()

    def test_a_partial_clean_of_a_dependency_names_its_rediscovered_files(self) -> None:
        # `d`'s own source changes (not `p`'s): the partial clean this time
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
        init_git(self.source)
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
                    export, export / "Cargo.toml", ("a",), self.base / "target", command,
                    command_cwd=export, command_key="atlas-pre-push:a",
                )[0]
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
class MultiPackageRunTestCase(unittest.TestCase):
    """One `run_build` for a gate step's whole package set: `a` (which
    depends on `b`) and the independent `c`. The step runs one cargo command
    naming both, keeps one record per package, and cleans only what a stale
    package's own rule names -- a package whose record matched is never
    cleaned because a sibling in the same run went stale.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-multi-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        self.source = self.base / "src_repo"
        for relative, text in {
            "Cargo.toml": '[workspace]\nmembers = ["a", "b", "c"]\nresolver = "2"\n',
            "a/Cargo.toml": (
                '[package]\nname = "a"\nversion = "0.1.0"\nedition = "2021"\n'
                "[dependencies]\nb = { path = \"../b\" }\n"
            ),
            "a/src/lib.rs": "//! a\n/// a\npub fn a() -> u32 { b::b() + 1 }\n",
            "b/Cargo.toml": '[package]\nname = "b"\nversion = "0.1.0"\nedition = "2021"\n',
            "b/src/lib.rs": "//! b\n/// b\npub fn b() -> u32 { 1 }\n",
            "c/Cargo.toml": '[package]\nname = "c"\nversion = "0.1.0"\nedition = "2021"\n',
            "c/src/lib.rs": "//! c\n/// c\npub fn c() -> u32 { 3 }\n",
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
        # Every cargo the checker starts, the build command included, is
        # logged one argv per line before it runs.
        self.log = self.base / "cargo.log"
        self.wrapper = self.base / "cargo_log.py"
        self.wrapper.write_text(
            "import json, subprocess, sys\n"
            f"with open({str(self.log)!r}, 'a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(['cargo', *sys.argv[1:]]) + '\\n')\n"
            "raise SystemExit(subprocess.run(['cargo', *sys.argv[1:]]).returncode)\n",
            encoding="utf-8",
        )

    def push(
        self,
        gate: Path,
        command: list[str] | None = None,
        packages: tuple[str, ...] = ("a", "c"),
        record: tuple[str, ...] = (),
    ):
        """One clippy step building `packages` and recording `record` (default:
        all of them), in the gate's export, cloned from the source when new."""
        export = gate / "nested" / "ws"
        export.parent.mkdir(parents=True, exist_ok=True)
        if not export.exists():
            subprocess.run(["git", "clone", "-q", str(self.source), str(export)], check=True)
        manifest = str(export / "Cargo.toml")
        self.log.unlink(missing_ok=True)
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_cargo_command", return_value=(sys.executable, str(self.wrapper))),
        ):
            return identity.run_build(
                export,
                export / "Cargo.toml",
                record or packages,
                self.base / "target",
                command
                or ["cargo", "clippy", "-q", "--manifest-path", manifest, "--locked", "--offline",
                    *(argument for package in packages for argument in ("-p", package))],
                command_cwd=export,
                command_key="atlas-pre-push",
                selection=packages,
            )

    def invocations(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def records(self) -> list[Path]:
        return sorted((self.base / "target" / ".atlas" / "source-identity").glob("*.json"))

    def test_one_command_and_one_record_per_package(self) -> None:
        first = self.push(self.base / "gate1")
        self.assertEqual(len(first), 2)
        self.assertEqual(len({result.record_path for result in first}), 2)
        clippy = [argv for argv in self.invocations() if argv[1] == "clippy"]
        self.assertEqual(len(clippy), 1, self.invocations())
        self.assertEqual(clippy[0][-4:], ["-p", "a", "-p", "c"])
        second = self.push(self.base / "gate2")
        self.assertEqual([result.status for result in second], ["reused", "reused"])
        self.assertEqual([result.record_path for result in second], [result.record_path for result in first])
        self.assertEqual([cleaned_names(argv) for argv in self.invocations() if argv[1] == "clean"], [])

    def test_a_matched_package_is_not_cleaned_beside_a_stale_one(self) -> None:
        first = self.push(self.base / "gate1")
        # The same step and commit with `c`'s record gone: `a` still matches.
        first[1].record_path.unlink()
        second = self.push(self.base / "gate2")
        self.assertEqual([result.status for result in second], ["reused", "rebuilt"])
        self.assertEqual([result.cleaned for result in second], [False, True])
        cleans = [cleaned_names(argv) for argv in self.invocations() if argv[1] == "clean"]
        # `c` alone: never `a`, nor `b`, which only `a`'s matched record names.
        self.assertEqual(cleans, [["c"]])

    def test_a_stand_in_for_any_named_package_is_rebuilt(self) -> None:
        """A record is matched against its own package's artifacts, whichever
        package that is: with `c`'s recorded rmeta and rlib files holding other
        bytes, `c` is rebuilt, and `a`, whose files are intact, is reused and
        never cleaned. Matching only the first package's artifacts, and taking
        the others' record as it stands, leaves `c` reused."""
        self.push(self.base / "gate1")
        deps = self.base / "target" / "debug" / "deps"
        replaced = [
            path
            for path in sorted(deps.iterdir())
            if re.fullmatch(r"libc-[0-9a-f]+[.](rmeta|rlib)", path.name)
        ]
        self.assertTrue(replaced, sorted(path.name for path in deps.iterdir()))
        for path in replaced:
            path.write_bytes(b"a stand-in for " + path.name.encode())
        second = self.push(self.base / "gate2")
        self.assertEqual([result.status for result in second], ["reused", "rebuilt"])
        cleans = [cleaned_names(argv) for argv in self.invocations() if argv[1] == "clean"]
        self.assertEqual(cleans, [["c"]])

    def test_a_matched_package_another_rule_cleaned_reports_rebuilt(self) -> None:
        first = self.push(self.base / "gate1", packages=("a", "b"))
        # `a`'s record gone: its rule cleans its closure, `b` with it, though
        # `b`'s own record still matches.
        first[0].record_path.unlink()
        second = self.push(self.base / "gate2", packages=("a", "b"))
        cleans = [cleaned_names(argv) for argv in self.invocations() if argv[1] == "clean"]
        self.assertEqual(cleans, [["a", "b"]])
        self.assertEqual(
            [(result.status, result.cleaned) for result in second],
            [("rebuilt", True), ("rebuilt", True)],
        )

    def test_check_finds_a_batched_record_under_its_selection(self) -> None:
        self.push(self.base / "gate1")
        export = self.base / "gate1" / "nested" / "ws"
        manifest = str(export / "Cargo.toml")

        def checked(selection: tuple[str, ...]) -> tuple[int, str]:
            with (
                patch.dict(os.environ, self.environment, clear=True),
                patch.object(identity, "_cargo_command", return_value=(sys.executable, str(self.wrapper))),
            ):
                code, value = check.check_record(
                    export, "c", self.base / "target", manifest=export / "Cargo.toml",
                    command=["cargo", "clippy", "-q", "--manifest-path", manifest, "--locked", "--offline",
                             "-p", "a", "-p", "c"],
                    command_cwd=export, command_key="atlas-pre-push", selection=selection,
                )
            return code, str(value["status"])

        self.assertEqual(checked(("c", "a")), (0, "match"))
        # `c` alone is another selection, whose record no run wrote.
        self.assertEqual(checked(()), (2, "missing"))

    def test_a_record_of_another_selection_never_matches(self) -> None:
        self.push(self.base / "gate1", packages=("a",))
        second = self.push(self.base / "gate2")
        # `a` was recorded under `-p a`; `-p a -p c` may build other variants
        # of its dependencies, so its record is not this step's.
        self.assertEqual([result.status for result in second], ["rebuilt", "rebuilt"])

    def test_a_commit_cleans_the_union_of_the_per_package_rules_once(self) -> None:
        self.push(self.base / "gate1")
        (self.source / "c" / "src" / "lib.rs").write_text(
            "//! c\n/// c\npub fn c() -> u32 { 4 }\n", encoding="utf-8"
        )
        git(self.source, "commit", "-q", "-am", "edit c")
        second = self.push(self.base / "gate2")
        self.assertEqual([result.status for result in second], ["rebuilt", "rebuilt"])
        # A path package's identity is its repository's, so the commit moves
        # `a`'s and `b`'s records too: one run per package (68a1c4364)
        # cleaned `-p a -p b`, then `-p c`. The batch names that union once.
        cleans = [cleaned_names(argv) for argv in self.invocations() if argv[1] == "clean"]
        self.assertEqual(cleans, [["a", "b", "c"]])

    def test_every_package_is_leased_and_each_member_held_exclusive(self) -> None:
        self.push(self.base / "gate1")
        target = self.base / "target"
        lock = {name: str(package_target_lease_path(name, target)) for name in ("a", "b", "c")}
        answers = self.base / "answers.json"
        probe = self.base / "probe.py"
        write_script(
            probe,
            LEASE_PROBE + "import subprocess\n"
            "raise SystemExit(subprocess.run(sys.argv[4:]).returncode)\n",
        )
        requests = [
            ["a", lock["a"], SHARED], ["c", lock["c"], SHARED],
            ["b", lock["b"], SHARED], ["b", lock["b"], EXCLUSIVE],
        ]
        manifest = str(self.base / "gate2" / "nested" / "ws" / "Cargo.toml")
        second = self.push(
            self.base / "gate2",
            [sys.executable, str(probe), str(SCRIPT.parent), str(answers), json.dumps(requests),
             "cargo", "clippy", "-q", "--manifest-path", manifest, "--locked", "--offline",
             "-p", "a", "-p", "c"],
        )
        self.assertEqual([result.status for result in second], ["reused", "reused"])
        # Both members are written by the command: exclusive. `b`, which only
        # `a`'s closure names, is read: shared, so a peer may read it too.
        self.assertEqual(
            json.loads(answers.read_text(encoding="utf-8")),
            {"a:shared": "refused", "c:shared": "refused",
             "b:shared": "granted", "b:exclusive": "refused"},
        )

    def test_each_record_names_its_own_package_artifacts(self) -> None:
        """`c` named first: every later package's record lists its own files,
        both when the push builds (exclusive) and when it reuses (shared)."""

        def packages_named(result) -> set[str]:
            return {
                match.group(1)
                for path in result.artifact_files
                for part in path.parts
                if (match := re.match(r"^(?:lib)?([abc])-[0-9a-f]+", part))
            }

        for gate, status in (("gate1", "rebuilt"), ("gate2", "reused")):
            with self.subTest(gate=gate):
                c, a = self.push(self.base / gate, packages=("c", "a"))
                self.assertEqual([c.status, a.status], [status, status])
                self.assertEqual(packages_named(c), {"c"})
                self.assertEqual(packages_named(a), {"a", "b"})

    def test_cargo_metadata_reads_do_not_grow_with_the_package_count(self) -> None:
        """One owners read and one snapshot read per pass, whatever the
        package count: a record loop that read the metadata for each
        package (5 reads for two packages, 7 for four) fails this."""
        real = subprocess.run

        def reads(gate: str, packages: tuple[str, ...]) -> int:
            count = 0

            def counting(args, *rest, **options):
                nonlocal count
                if isinstance(args, (list, tuple)) and "metadata" in map(str, args):
                    count += 1
                return real(args, *rest, **options)

            with patch.object(subprocess, "run", counting):
                self.push(self.base / gate, packages=packages)
            return count

        for phase, (one, three) in {
            "building": (("one1", ("a",)), ("three1", ("a", "b", "c"))),
            "reusing": (("one2", ("a",)), ("three2", ("a", "b", "c"))),
        }.items():
            with self.subTest(phase=phase):
                self.assertEqual(reads(*one), reads(*three))

    def test_steps_of_one_selection_share_their_records(self) -> None:
        """A push's steps build one package set, whatever each records: `c`
        writes no artifact in the middle step, as a package with no test
        target writes none for tests. The middle step reuses the record the
        first wrote and the last reuses both, so the push cleans once when
        its commit moved and never when it did not (steps naming `-p a -p c`,
        then `-p a`, then `-p a -p c` cleaned on each of the three)."""
        steps = [("a", "c"), ("a",), ("a", "c")]

        def push(gate: str) -> list[list[str]]:
            cleans: list[list[str]] = []
            for record in steps:
                self.push(self.base / gate, packages=("a", "c"), record=record)
                cleans.extend(
                    cleaned_names(argv) for argv in self.invocations() if argv[1] == "clean"
                )
            return cleans

        self.assertEqual(push("gate1"), [["a", "b", "c"]])
        self.assertEqual(push("gate2"), [])
        (self.source / "c" / "src" / "lib.rs").write_text(
            "//! c\n/// c\npub fn c() -> u32 { 4 }\n", encoding="utf-8"
        )
        git(self.source, "commit", "-q", "-am", "edit c")
        self.assertEqual(push("gate3"), [["a", "b", "c"]])
        self.assertEqual(push("gate4"), [])

    def test_a_package_outside_the_selection_is_refused(self) -> None:
        with self.assertRaisesRegex(identity.IdentityError, "not all in the selection"):
            identity.run_build(
                self.source,
                self.source / "Cargo.toml",
                ("a", "c"),
                self.base / "target",
                ["cargo", "clippy"],
                selection=("a",),
            )

    def test_every_phase_of_a_run_claims_all_its_scopes_under_one_arrival(self) -> None:
        claims: list[tuple[list[str], int | None, str | None]] = []
        real = identity.acquire_claim

        def recording(leases, wait, deadline, arrival, run):
            claims.append(([str(lease.owner["package"]) for lease in leases], arrival, run))
            return real(leases, wait, deadline, arrival, run)

        with patch.object(identity, "acquire_claim", side_effect=recording):
            self.push(self.base / "gate1", packages=("c", "a"))
        # A first push has no record: one claim to read it, one to clean and
        # build. Each takes every scope, whatever order the packages were
        # named in, and the second keeps the first's place, `(arrival, run)`,
        # in every queue.
        self.assertGreaterEqual(len(claims), 2)
        self.assertTrue(all(names == ["a", "b", "c"] for names, _, _ in claims))
        self.assertEqual(len({arrival for _, arrival, _ in claims}), 1)
        self.assertEqual(len({run for _, _, run in claims}), 1)
        self.assertIsNotNone(claims[0][1])
        self.assertIsNotNone(claims[0][2])

    def test_a_dependency_change_in_any_package_refuses_the_record(self) -> None:
        marker = self.base / "built"
        real = identity._dependency_data

        def moving(*args, **kwargs):
            snapshots = real(*args, **kwargs)
            if marker.exists():
                # After the command: the last package's closure moved.
                snapshots = {**snapshots, "c": {**snapshots["c"], "digest": "moved"}}
            return snapshots

        with patch.object(identity, "_dependency_data", side_effect=moving):
            with self.assertRaisesRegex(identity.IdentityError, "dependency graph changed"):
                self.push(
                    self.base / "gate1",
                    [sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"],
                )
        self.assertEqual(self.records(), [])

    def test_git_stamps_are_written_for_every_package(self) -> None:
        stamped: list[tuple[str, bool]] = []
        real = identity._write_git_stamps

        def recording(dependencies, directory, names, building):
            stamped.append((str(dependencies["root"]), building))
            return real(dependencies, directory, names, building)

        with patch.object(identity, "_write_git_stamps", side_effect=recording):
            self.push(self.base / "gate1")
        a, c = "workspace:a#a@0.1.0", "workspace:c#c@0.1.0"
        self.assertEqual(sorted(stamped), [(a, False), (a, True), (c, False), (c, True)])

    def test_a_failing_command_writes_no_record(self) -> None:
        with self.assertRaisesRegex(identity.IdentityError, "exit code 3"):
            self.push(self.base / "gate1", [sys.executable, "-c", "raise SystemExit(3)"])
        self.assertEqual(self.records(), [])


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class SelectionVariantTestCase(unittest.TestCase):
    """`a` uses `d` without features and `b` with `extra`, which changes
    `d::value()`. Built together, Cargo unifies `d` to its `extra` variant;
    built alone, `a` links `d`'s plain variant, under another file name. A
    record written by a `-p a -p b` step names only the unified variant, so it
    must not stand in for a later `-p a` step: a peer's plain `cargo build -p
    a` of other `d` source in between would be linked unseen.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-selection-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        self.source = self.base / "src_repo"
        self.write_workspace(self.source, value="1")
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=self.source, env=self.environment, check=True, capture_output=True, timeout=120,
        )
        git(self.source, "init", "-q")
        git(self.source, "config", "user.name", "Atlas test")
        git(self.source, "config", "user.email", "atlas-test@example.invalid")
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")
        # One export reused in place, as the hook reuses its checkout path.
        self.export = self.base / "gate" / "nested" / "ws"
        self.export.parent.mkdir(parents=True)
        subprocess.run(["git", "clone", "-q", str(self.source), str(self.export)], check=True)
        self.target = self.base / "target"

    @staticmethod
    def write_workspace(root: Path, value: str) -> None:
        for relative, text in {
            "Cargo.toml": '[workspace]\nmembers = ["a", "b", "d"]\nresolver = "2"\n',
            "a/Cargo.toml": (
                '[package]\nname = "a"\nversion = "0.1.0"\nedition = "2021"\n'
                '[dependencies]\nd = { path = "../d" }\n'
            ),
            "a/src/main.rs": 'fn main() { println!("{}", d::value()); }\n',
            "b/Cargo.toml": (
                '[package]\nname = "b"\nversion = "0.1.0"\nedition = "2021"\n'
                '[dependencies]\nd = { path = "../d", features = ["extra"] }\n'
            ),
            "b/src/lib.rs": "pub fn b() -> u32 { d::value() }\n",
            "d/Cargo.toml": (
                '[package]\nname = "d"\nversion = "0.1.0"\nedition = "2021"\n'
                "[features]\nextra = []\n"
            ),
            "d/src/lib.rs": (
                f"pub fn value() -> u32 {{ if cfg!(feature = \"extra\") {{ 100 + {value} }} else {{ {value} }} }}\n"
            ),
        }.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text, encoding="utf-8")

    def gate(self, packages: tuple[str, ...]) -> list[list[str] | None]:
        """One build step over `packages`; the packages each `cargo clean` named."""
        log = self.base / "cargo.log"
        log.unlink(missing_ok=True)
        wrapper = self.base / "cargo_log.py"
        wrapper.write_text(
            "import json, subprocess, sys\n"
            f"with open({str(log)!r}, 'a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(['cargo', *sys.argv[1:]]) + '\\n')\n"
            "raise SystemExit(subprocess.run(['cargo', *sys.argv[1:]]).returncode)\n",
            encoding="utf-8",
        )
        manifest = str(self.export / "Cargo.toml")
        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_cargo_command", return_value=(sys.executable, str(wrapper))),
        ):
            identity.run_build(
                self.export, self.export / "Cargo.toml", packages, self.target,
                ["cargo", "build", "-q", "--manifest-path", manifest, "--offline",
                 *(argument for package in packages for argument in ("-p", package))],
                command_cwd=self.export, command_key="atlas-pre-push",
            )
        return [
            cleaned_names(argv)
            for argv in map(json.loads, log.read_text(encoding="utf-8").splitlines())
            if argv[1] == "clean"
        ]

    def run_a(self) -> str:
        binary = self.target / "debug" / ("a.exe" if os.name == "nt" else "a")
        return subprocess.run([str(binary)], capture_output=True, text=True, check=True).stdout.strip()

    def test_a_record_of_one_selection_does_not_stand_in_for_another(self) -> None:
        self.gate(("a", "b"))
        # The unified variant: `a` built beside `b` links `d` with `extra`.
        self.assertEqual(self.run_a(), "101")
        peer = self.base / "peer"
        subprocess.run(["git", "clone", "-q", str(self.source), str(peer)], check=True)
        self.write_workspace(peer, value="2")
        built = subprocess.run(
            ["cargo", "build", "-q", "--offline", "--manifest-path", str(peer / "Cargo.toml"), "-p", "a"],
            cwd=peer, env={**self.environment, "CARGO_TARGET_DIR": str(self.target)},
            capture_output=True, text=True, timeout=300,
        )
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(self.run_a(), "2")
        cleans = self.gate(("a",))
        # No record names `-p a`'s variant of `d`, so the closure is cleaned
        # and rebuilt from this checkout's source.
        self.assertEqual(cleans, [["a", "d"]])
        self.assertEqual(self.run_a(), "1")
        # The `-p a` record now exists: the same step again cleans nothing.
        self.assertEqual(self.gate(("a",)), [])


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class PathDependencyFeatureChangeTestCase(unittest.TestCase):
    """`p` depends on `v` and `x`, each a separate repository; `v` also
    depends on `x`. Enabling `x`'s feature `f` from `p`'s manifest changes
    `x`'s resolved feature set, and so `v`'s variant, while `x`'s and `v`'s
    repositories stay unchanged. Any difference in a path record cleans
    that package.
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
            init_git(root)
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
            if (names := cleaned_names(command)) is not None:
                cleaned[-1].extend(names)
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
                    export, export / "Cargo.toml", ("p",), self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"], command_cwd=export,
                )[0]
        return cleaned

    def test_enabling_a_dependency_feature_cleans_it_and_its_dependents(self) -> None:
        # Push 2 enables x's feature from p's manifest: p's repository moved
        # and x's record differs in `features`. Cargo then builds `v` under a
        # new metadata hash, folding in x's, so `v` is cleaned with them and
        # its record names the variant the build uses; a repeat push reuses
        # the record.
        self.assertEqual(
            self.push(4, enable_feature_before=2), [["p", "v", "x"], [], ["p", "v", "x"], []]
        )


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class DependencyAdditionTestCase(unittest.TestCase):
    """`p` depends on `v`, `v` on `x`, each a separate repository; `w`, also
    depending on `x`, is not yet in the closure. Adding a dependency cleans
    the path packages whose repositories moved and the new path package `w`,
    which no record describes; `x`, unchanged and shared with `w`, keeps its
    artifacts and is held shared.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-addition-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }

        def repo(root: Path, files: dict[str, str]) -> None:
            for relative, text in files.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, encoding="utf-8")
            init_git(root)
            self.lock(root)
            git(root, "add", ".")
            git(root, "commit", "-q", "-m", "init")

        self.x = self.base / "xrepo"
        self.w = self.base / "wrepo"
        self.v = self.base / "vrepo"
        self.source = self.base / "source"
        repo(self.x, {
            "Cargo.toml": '[package]\nname = "x"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n',
            "src/lib.rs": "pub fn x() -> u32 {\n    1\n}\n",
        })
        repo(self.w, {
            "Cargo.toml": (
                '[package]\nname = "w"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n[dependencies]\n'
                f'x = {{ path = "{self.x.as_posix()}" }}\n'
            ),
            "src/lib.rs": "pub fn w() -> u32 { x::x() + 1 }\n",
        })
        self.v_manifest = lambda with_w: (
            '[package]\nname = "v"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n[dependencies]\n'
            f'x = {{ path = "{self.x.as_posix()}" }}\n'
            + (f'w = {{ path = "{self.w.as_posix()}" }}\n' if with_w else "")
        )
        repo(self.v, {"Cargo.toml": self.v_manifest(False), "src/lib.rs": "pub fn v() -> u32 { x::x() }\n"})
        self.p_manifest = lambda with_w: (
            '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n[dependencies]\n'
            f'v = {{ path = "{self.v.as_posix()}" }}\n'
            + (f'w = {{ path = "{self.w.as_posix()}" }}\n' if with_w else "")
        )
        repo(self.source, {"Cargo.toml": self.p_manifest(False), "src/lib.rs": "pub fn p() -> u32 { v::v() }\n"})

    def lock(self, root: Path) -> None:
        subprocess.run(
            ["cargo", "generate-lockfile", "--offline"],
            cwd=root, env=self.environment, check=True, capture_output=True, timeout=120,
        )

    def commit(self, root: Path, manifest: str, message: str) -> None:
        (root / "Cargo.toml").write_text(manifest, encoding="utf-8")
        self.lock(root)
        git(root, "add", ".")
        git(root, "commit", "-q", "-m", message)

    def push(self, pushes: int, edits: dict[int, tuple[Path, str]]) -> list[list[str]]:
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if (names := cleaned_names(command)) is not None:
                cleaned[-1].extend(names)
            run_checked(command, cwd, environment)

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_run_checked", side_effect=recording),
        ):
            for push in range(pushes):
                if push in edits:
                    repository, manifest = edits[push]
                    self.commit(repository, manifest, f"edit before push {push}")
                    if repository != self.source:
                        self.lock(self.source)
                        git(self.source, "commit", "-qam", f"relock before push {push}")
                export = self.base / f"export-{push}"
                if export.exists():
                    _clear_readonly_tree(export)
                shutil.copytree(self.source, export, copy_function=shutil.copy)
                cleaned.append([])
                identity.run_build(
                    export, export / "Cargo.toml", ("p",), self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"], command_cwd=export,
                )[0]
        return cleaned

    def test_adding_a_dependency_to_the_root_cleans_every_path_package(self) -> None:
        # Push 2 adds `w` to p: p's repository moved, so every path package
        # is cleaned and rediscovered, `w` among them.
        cleaned = self.push(3, {2: (self.source, self.p_manifest(True))})
        self.assertEqual(cleaned, [["p", "v", "x"], [], ["p", "v", "w", "x"]])

    def test_adding_a_dependency_to_a_middle_package_cleans_every_path_package(self) -> None:
        # Push 2 adds `w` to v: v's repository and p's lockfile moved.
        cleaned = self.push(3, {2: (self.v, self.v_manifest(True))})
        self.assertEqual(cleaned, [["p", "v", "x"], [], ["p", "v", "w", "x"]])

    def test_a_repeat_push_after_an_addition_reuses_the_record(self) -> None:
        cleaned = self.push(4, {2: (self.source, self.p_manifest(True))})
        self.assertEqual(cleaned, [["p", "v", "x"], [], ["p", "v", "w", "x"], []])


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class GitDependencyTestCase(unittest.TestCase):
    """`p` depends on the git package `d`; push 2 adds the git package `e`.

    A git package is cleaned only when the target's stamp says its artifacts
    were built from other content than its Cargo checkout holds now. `q`, a
    second workspace, shares that checkout and the target.
    """

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-build-identity-git-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        self.environment["CARGO_HOME"] = str(self.base / "cargo-home")
        self.repositories = {name: self.base / f"{name}repo" for name in ("d", "e")}
        for name, root in self.repositories.items():
            for relative, text in {
                "Cargo.toml": f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n',
                "src/lib.rs": f"pub fn {name}() -> u32 {{ 1 }}\n",
            }.items():
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text(text, encoding="utf-8")
            init_git(root)
            self.cargo(root, "generate-lockfile", "--offline")
            git(root, "add", ".")
            git(root, "commit", "-q", "-m", name)
        self.source = self.base / "source"
        for relative, text in {
            "Cargo.toml": self.manifest(("d",)), "src/lib.rs": "pub fn p() -> u32 { d::d() }\n"
        }.items():
            (self.source / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.source / relative).write_text(text, encoding="utf-8")
        self.cargo(self.source, "generate-lockfile")
        init_git(self.source)
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")
        self.second = self.base / "second"
        for relative, text in {
            "Cargo.toml": self.manifest(("d",)).replace('name = "p"', 'name = "q"'),
            "src/lib.rs": "pub fn q() -> u32 { d::d() }\n",
        }.items():
            (self.second / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.second / relative).write_text(text, encoding="utf-8")
        self.cargo(self.second, "generate-lockfile")
        init_git(self.second)
        git(self.second, "add", ".")
        git(self.second, "commit", "-q", "-m", "second")

    def cargo(self, root: Path, *arguments: str) -> None:
        subprocess.run(
            ["cargo", *arguments],
            cwd=root, env=self.environment, check=True, capture_output=True, timeout=120,
        )

    def manifest(self, names: tuple[str, ...]) -> str:
        return (
            '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\n[dependencies]\n'
            + "".join(f'{name} = {{ git = "{self.repositories[name].as_uri()}" }}\n' for name in names)
        )

    def checkout_source(self) -> Path:
        (checkout,) = (self.base / "cargo-home" / "git" / "checkouts").glob("drepo-*/*")
        return checkout / "src" / "lib.rs"

    def push(
        self,
        pushes: int,
        before: dict[int, object],
        keys: dict[int, str] | None = None,
        second: frozenset[int] = frozenset(),
        release: frozenset[int] = frozenset(),
        killed: frozenset[int] = frozenset(),
        custom_clean: frozenset[int] = frozenset(),
    ) -> list[list[str]]:
        """Push the source (or `q`, for `second`) once per push, recording each clean.

        A `release` push builds `--release` into `release/`; a `killed` push
        is stopped after its command ran, before the run finished; a
        `custom_clean` push passes a clean command that cleans nothing.
        """
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked
        state = {"push": 0}

        def recording(command, cwd, environment):
            if (names := cleaned_names(command)) is not None:
                cleaned[-1].extend(names)
            run_checked(command, cwd, environment)
            if state["push"] in killed and names is None and "build" in command:
                raise KeyboardInterrupt("stopped after the command ran")

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_run_checked", side_effect=recording),
        ):
            for push in range(pushes):
                if push in before:
                    before[push]()
                export = self.base / f"export-{push}"
                if export.exists():
                    _clear_readonly_tree(export)
                root, package = (self.second, "q") if push in second else (self.source, "p")
                shutil.copytree(root, export, copy_function=shutil.copy)
                cleaned.append([])
                state["push"] = push
                profile = "release" if push in release else "debug"
                command = (
                    ["cargo", "build", "-p", package, "-q", "--release"]
                    if push in release
                    else ["cargo", "build", "-p", package, "-q"]
                    if push in killed
                    else ["cargo", "check", "-p", package, "-q"]
                )
                try:
                    identity.run_build(
                        export, export / "Cargo.toml", (package,), self.base / "target",
                        command, command_cwd=export, profile=profile,
                        command_key=(keys or {}).get(push, profile),
                        clean_command=[sys.executable, "-c", "pass"] if push in custom_clean else None,
                    )[0]
                except KeyboardInterrupt:
                    self.assertIn(push, killed)
        return [sorted(packages) for packages in cleaned]

    def add_e(self) -> None:
        (self.source / "Cargo.toml").write_text(self.manifest(("d", "e")), encoding="utf-8")
        self.cargo(self.source, "generate-lockfile")
        git(self.source, "commit", "-qam", "add e")

    def edit_checkout_once(self) -> dict[str, object]:
        source = self.checkout_source
        original: dict[str, bytes] = {}

        def edit() -> None:
            original["text"] = source().read_bytes()
            source().write_bytes(original["text"] + b"// edited\n")

        def restore() -> None:
            source().write_bytes(original["text"])

        return {"edit": edit, "restore": restore}

    def test_an_edit_seen_by_another_profile_cleans_this_profile(self) -> None:
        # Push 0 builds `d` into `release/`. Push 1, a debug build, sees the
        # edited checkout and builds `d` into `debug/`; its clean reaches
        # only `debug/`. Push 2, back in `release/`, must still clean `d`:
        # a stamp spanning the target would name the edit and vouch for the
        # release artifact push 0 built from the original.
        checkout = self.edit_checkout_once()
        release = self.base / "target" / "release" / "deps"
        before: dict[str, int] = {}

        def remember() -> None:
            before.update({path.name: path.stat().st_mtime_ns for path in release.glob("libd-*.rlib")})

        cleaned = self.push(3, {1: checkout["edit"], 2: remember}, release=frozenset({0, 2}))
        self.assertEqual(cleaned, [["p"], ["p"], ["d"]])
        # The clean reached `release/`: Cargo, which never re-reads a Git
        # checkout, rebuilt `d` there instead of keeping push 0's artifact.
        after = {path.name: path.stat().st_mtime_ns for path in release.glob("libd-*.rlib")}
        self.assertEqual(len(before), 1)
        self.assertEqual(after.keys(), before.keys())
        self.assertNotEqual(after, before)

    def test_a_run_stopped_after_its_command_leaves_d_stale(self) -> None:
        # Push 1 cleans `d`, builds it from the edit, and is stopped before
        # its stamp names that content. Push 2, the checkout restored, must
        # clean `d` again: the target holds what push 1 built.
        checkout = self.edit_checkout_once()
        cleaned = self.push(
            3, {1: checkout["edit"], 2: checkout["restore"]}, killed=frozenset({1})
        )
        self.assertEqual(cleaned, [["p"], ["d"], ["d"]])

    def test_a_custom_clean_still_cleans_an_edited_checkout(self) -> None:
        checkout = self.edit_checkout_once()
        cleaned = self.push(2, {1: checkout["edit"]}, custom_clean=frozenset({1}))
        self.assertEqual(cleaned, [["p"], ["d"]])

    def test_an_added_git_dependency_cleans_only_the_root(self) -> None:
        self.assertEqual(self.push(4, {2: self.add_e}), [["p"], [], ["p"], []])

    def test_an_edited_checkout_cleans_its_package_until_restored(self) -> None:
        source = self.checkout_source
        original: dict[str, bytes] = {}

        def edit() -> None:
            original["text"] = source().read_bytes()
            source().write_bytes(original["text"] + b"// edited\n")

        def restore() -> None:
            source().write_bytes(original["text"])

        # Push 2 sees the edit and cleans `d`; push 3 matches the record push
        # 2 wrote from the edited checkout; push 4 sees the checkout
        # restored, whose content no longer matches that record.
        self.assertEqual(
            self.push(6, {2: edit, 4: restore}), [["p"], [], ["d"], [], ["d"], []]
        )

    def test_a_restored_checkout_is_rebuilt_under_every_record(self) -> None:
        # Records `a` and `b` share one target. `b` builds `d` from an edit;
        # once the checkout is restored, `a`'s record still describes its
        # pristine `d`, but the artifact on disk is `b`'s: `a` cleans `d`, and
        # `p`, whose recorded bytes `b` rebuilt against the edit, once.
        source = self.checkout_source
        original: dict[str, bytes] = {}

        def edit() -> None:
            original["text"] = source().read_bytes()
            source().write_bytes(original["text"] + b"// edited\n")

        def restore() -> None:
            source().write_bytes(original["text"])

        self.assertEqual(
            self.push(4, {1: edit, 2: restore}, keys={0: "a", 1: "b", 2: "a", 3: "a"}),
            [["p"], ["d", "p"], ["d", "p"], []],
        )

    def test_a_restored_checkout_is_rebuilt_under_a_sibling_record(self) -> None:
        # `c` has no record but a sibling, `a`, describes its build, and `p`'s
        # artifacts are still `a`'s. The sibling stands in for the path
        # packages, never for `d`, which the second workspace `q` built from
        # the edit.
        source = self.checkout_source
        original: dict[str, bytes] = {}

        def edit() -> None:
            original["text"] = source().read_bytes()
            source().write_bytes(original["text"] + b"// edited\n")

        def restore() -> None:
            source().write_bytes(original["text"])

        self.assertEqual(
            self.push(
                4, {1: edit, 2: restore}, keys={0: "a", 2: "c", 3: "c"}, second=frozenset({1})
            ),
            [["p"], ["d", "q"], ["d"], []],
        )

    def test_an_edit_written_back_after_another_workspace_built_is_cleaned(self) -> None:
        # `p` builds `d` from a first edit, `q` from a second; writing the
        # first edit back makes `p`'s record match again, while the artifact
        # on disk is `q`'s.
        source = self.checkout_source
        texts: dict[str, bytes] = {}

        def first_edit() -> None:
            texts["original"] = source().read_bytes()
            texts["first"] = texts["original"] + b"// first edit\n"
            source().write_bytes(texts["first"])

        def second_edit() -> None:
            source().write_bytes(texts["original"] + b"// second edit\n")

        def first_again() -> None:
            source().write_bytes(texts["first"])

        self.assertEqual(
            self.push(5, {1: first_edit, 2: second_edit, 3: first_again}, second=frozenset({2})),
            [["p"], ["d"], ["d", "q"], ["d"], []],
        )


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class GitManifestEditTestCase(unittest.TestCase):
    """`p` depends on the path member `m`, which depends on the Git package `g`;
    `g`'s workspace member `h` is a Git package too.

    Push 2 edits the Cargo checkout of `g`'s manifest, moving `h`'s feature
    `f` out of a never-true `cfg` table. `cargo metadata` lists `f` for `h`
    both times and no edge kind changes, so only `g`'s resolved manifest
    says that `h`, `g` and with them `m` and `p` were renamed.
    """

    G_MANIFEST = (
        '[package]\nname = "g"\nversion = "0.1.0"\nedition = "2021"\n[workspace]\nmembers = ["h"]\n'
        "[dependencies]\n{plain}\n[target.'cfg(any())'.dependencies]\n{never}\n"
    )

    def setUp(self) -> None:
        # A short prefix: Cargo's Git checkout paths under it near MAX_PATH.
        temp = tempfile.TemporaryDirectory(prefix="aig-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.environment = {
            key: value for key, value in os.environ.items() if key != "CARGO_TARGET_DIR"
        }
        self.environment["CARGO_HOME"] = str(self.base / "ch")
        self.grepo = self.base / "g"
        self.write(self.grepo, {
            "Cargo.toml": self.G_MANIFEST.format(
                plain='h = { path = "h" }', never='h = { path = "h", features = ["f"] }'
            ),
            "src/lib.rs": "pub fn g() -> u32 { h::V }\n",
            "h/Cargo.toml": '[package]\nname = "h"\nversion = "0.1.0"\nedition = "2021"\n[features]\nf = []\n',
            "h/src/lib.rs": '#[cfg(feature = "f")]\npub const V: u32 = 2;\n'
            '#[cfg(not(feature = "f"))]\npub const V: u32 = 1;\n',
        })
        self.commit(self.grepo, lock=True)
        self.source = self.base / "s"
        self.write(self.source, {
            "Cargo.toml": '[package]\nname = "p"\nversion = "0.1.0"\nedition = "2021"\n'
            '[workspace]\nmembers = ["crates/m"]\n[dependencies]\nm = { path = "crates/m" }\n',
            "src/lib.rs": "pub fn p() -> u32 { m::m() }\n",
            "crates/m/Cargo.toml": '[package]\nname = "m"\nversion = "0.1.0"\nedition = "2021"\n'
            f'[dependencies]\ng = {{ git = "{self.grepo.as_uri()}" }}\n',
            "crates/m/src/lib.rs": "pub fn m() -> u32 { g::g() }\n",
        })
        self.commit(self.source, lock=True)

    @staticmethod
    def write(root: Path, files: dict[str, str]) -> None:
        for relative, text in files.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_bytes(text.encode())

    def commit(self, root: Path, lock: bool) -> None:
        if lock:
            subprocess.run(
                ["cargo", "generate-lockfile"],
                cwd=root, env=self.environment, check=True, capture_output=True, timeout=120,
            )
        init_git(root)
        git(root, "add", ".")
        git(root, "commit", "-q", "-m", "init")

    def edit_checkout(self, unstamp: bool) -> None:
        (checkout,) = (self.base / "ch" / "git" / "checkouts").glob("g-*/*")
        if unstamp:
            for stamp in (self.base / "t" / ".atlas" / "source-identity" / "git-build").glob("*"):
                stamp.unlink()
        (checkout / "Cargo.toml").write_bytes(self.G_MANIFEST.format(
            plain='h = { path = "h", features = ["f"] }', never='h = { path = "h" }'
        ).encode())

    def push(self, unstamp: bool) -> list[list[str]]:
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if (names := cleaned_names(command)) is not None:
                cleaned[-1].extend(names)
            run_checked(command, cwd, environment)

        with (
            patch.dict(os.environ, self.environment, clear=True),
            patch.object(identity, "_run_checked", side_effect=recording),
        ):
            for push in range(4):
                if push == 2:
                    self.edit_checkout(unstamp)
                export = self.base / f"e{push}"
                shutil.copytree(self.source, export, copy_function=shutil.copy)
                cleaned.append([])
                self.result = identity.run_build(
                    export, export / "Cargo.toml", ("p",), self.base / "t",
                    ["cargo", "check", "-p", "p", "-q"], command_cwd=export,
                )[0]
        return [sorted(packages) for packages in cleaned]

    def assert_record_names_the_m_on_disk(self) -> None:
        record = json.loads(self.result.record_path.read_text(encoding="utf-8"))
        named = {
            Path(relative).name
            for relative in record["artifact"]["files"]
            if Path(relative).name.startswith(("libm-", "m-"))
        }
        on_disk = {
            path.name
            for path in (self.base / "t" / "debug" / "deps").iterdir()
            if path.name.startswith(("libm-", "m-"))
        }
        self.assertTrue(named)
        self.assertEqual(named, on_disk)

    def test_a_stamped_checkout_manifest_edit_cleans_g_and_every_path_package(self) -> None:
        self.assertEqual(self.push(unstamp=False), [["m", "p"], [], ["g", "m", "p"], []])
        self.assert_record_names_the_m_on_disk()

    def test_an_unstamped_checkout_manifest_edit_cleans_every_path_package(self) -> None:
        # `g` is trusted, the documented bound for builds outside this
        # checker; `m` is renamed all the same and must be rediscovered.
        self.assertEqual(self.push(unstamp=True), [["m", "p"], [], ["m", "p"], []])
        self.assert_record_names_the_m_on_disk()


@pytest.mark.slow
@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class RootProfileChangeTestCase(unittest.TestCase):
    """A root manifest edit that only adds a `[profile.dev]` table changes
    how the git dependency `d` compiles while its checkout stays unedited:
    Cargo rebuilds `d` under the new profile itself, so only `p`, whose
    source moved, is cleaned, and a repeat push reuses the record.
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
        init_git(self.d)
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
        init_git(self.source)
        git(self.source, "add", ".")
        git(self.source, "commit", "-q", "-m", "source")

    def push(self, pushes: int, *, profile_before: int) -> list[list[str]]:
        cleaned: list[list[str]] = []
        run_checked = identity._run_checked

        def recording(command, cwd, environment):
            if (names := cleaned_names(command)) is not None:
                cleaned[-1].extend(names)
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
                    export, export / "Cargo.toml", ("p",), self.base / "target",
                    ["cargo", "check", "-p", "p", "-q", "--offline"], command_cwd=export,
                )[0]
        return cleaned

    def test_a_profile_edit_cleans_only_the_root(self) -> None:
        self.assertEqual(self.push(4, profile_before=2), [["p"], [], ["p"], []])




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
            patch.object(build_inputs, "toolchain_identity", return_value="rustc-test"),
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
                "--command-key", "atlas-pre-push",
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
        self.assertEqual(run_build.call_args.args[2], ("demo",))
        self.assertEqual(kwargs["command_key"], "atlas-pre-push")
        self.assertEqual(kwargs["command_cwd"], self.root)
        self.assertEqual(kwargs["ignore_paths"], [self.root / "Cargo.lock"])
        self.assertEqual(self.artifact.read_text(encoding="utf-8"), "built")

    def test_each_package_gets_its_own_output_line(self) -> None:
        results = tuple(
            identity.BuildResult(status, self.target / f"{name}.json", status == "rebuilt", ())
            for name, status in (("demo", "reused"), ("other", "rebuilt"))
        )
        stdout = io.StringIO()
        with (
            patch.object(self.cli, "run_build", return_value=results) as run_build,
            redirect_stdout(stdout),
        ):
            code = self.cli.main([
                "run", "--root", str(self.root), "--package", "demo", "--package", "demo",
                "--package", "other",
                "--target-dir", str(self.target), "--manifest", str(self.root / "Cargo.toml"),
                "--", sys.executable, str(self.build),
            ])
        self.assertEqual(code, 0)
        # `run_build` returns one result for the repeated `demo`.
        self.assertEqual(run_build.call_args.args[2], ("demo", "demo", "other"))
        lines = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(
            [(line["package"], line["status"], line["cleaned"]) for line in lines],
            [("demo", "reused", False), ("other", "rebuilt", True)],
        )

    def test_run_passes_the_selection_through(self) -> None:
        results = (identity.BuildResult("reused", self.target / "demo.json", False, ()),)
        with (
            patch.object(self.cli, "run_build", return_value=results) as run_build,
            redirect_stdout(io.StringIO()),
        ):
            code = self.cli.main([
                "run", "--root", str(self.root), "--package", "demo",
                "--selection", "demo", "--selection", "other",
                "--target-dir", str(self.target), "--manifest", str(self.root / "Cargo.toml"),
                "--", sys.executable, str(self.build),
            ])
        self.assertEqual(code, 0)
        self.assertEqual(run_build.call_args.args[2], ("demo",))
        self.assertEqual(run_build.call_args.kwargs["selection"], ["demo", "other"])

    def test_check_passes_the_selection_through(self) -> None:
        stdout = io.StringIO()
        with (
            patch.object(self.cli, "check_record", return_value=(0, {"status": "match"})) as check_record,
            redirect_stdout(stdout),
        ):
            code = self.cli.main([
                "check", "--root", str(self.root), "--package", "demo",
                "--selection", "demo", "--selection", "other",
                "--target-dir", str(self.target), "--manifest", str(self.root / "Cargo.toml"),
            ])
        self.assertEqual((code, json.loads(stdout.getvalue())), (0, {"status": "match"}))
        self.assertEqual(check_record.call_args.args[-1], ["demo", "other"])

    def pre_push_released(self, lease_seconds: int, held_on: float) -> tuple[int, str]:
        """Run the pre-push entry point against a holder that releases only after
        the run has printed its waiting line and `held_on` more seconds pass."""
        lock = package_target_lease_path("demo", build_source._canonical(self.target))
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
        lock = package_target_lease_path("demo", build_source._canonical(self.target))
        holder = hold_lease(self, lock, self.target, 600, 600)
        requested: list[int | None] = []
        real_acquire = identity.acquire_claim
        clock = RecordedClock()

        def recording_acquire(leases, wait_seconds, deadline_ns=None, *args, **kwargs):
            requested.append(deadline_ns)
            # The run fixes its deadline once, when it starts: exactly the
            # 2 s bound after its one clock read. A deadline of any other
            # length fails whatever the host's speed, and it fails here,
            # before the run waits it out against the holder.
            self.assertEqual(len(clock.reads), 1)
            self.assertEqual(deadline_ns, clock.reads[0] + 2_000_000_000)
            return real_acquire(leases, wait_seconds, deadline_ns, *args, **kwargs)

        stderr = io.StringIO()
        with (
            redirect_stderr(stderr),
            patch.object(identity, "acquire_claim", side_effect=recording_acquire),
            patch.object(identity, "time", clock),
        ):
            code = self.pre_push("--lease-wait-seconds", "2")
        refused_ns = time.monotonic_ns()
        self.assertEqual(code, 1)
        # The refusal came only after that deadline.
        self.assertGreaterEqual(refused_ns, requested[0])
        # The run gave up at its bound with the holder still holding: it did
        # not wait the holder out, however long the host took to give up.
        self.assertIsNone(holder.poll())
        self.assertIn(
            "still held by holder-root at holder-revision after waiting 2 s (--lease-wait-seconds)",
            stderr.getvalue(),
        )
        self.assertFalse(self.artifact.exists())

if __name__ == "__main__":
    unittest.main()
