#!/usr/bin/env python3
"""A run takes its build-scope leases together, and waits holding none."""

from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_build_lease as lease_module
import atlas_build_queue as queue_module
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    BuildIdentityError,
    LeaseHeldError,
    OwnerLease,
    acquire_claim,
    lease_is_held,
    package_target_lease_path,
)

WAIT = 30


class ClaimTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="atlas-claim-"))
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.target = self.base / "target"
        self.holders: list[OwnerLease] = []

    def lease(self, package: str, mode: str, root: str = "run") -> OwnerLease:
        owner = {"root": root, "revision": f"{root}-revision", "package": package}
        return OwnerLease(package_target_lease_path(package, self.target), owner, 60, mode)

    def hold(self, package: str, mode: str, root: str, arrival: int) -> OwnerLease:
        lease = self.lease(package, mode, root)
        lease.arrival = arrival
        lease.attempt()
        self.holders.append(lease)
        self.addCleanup(lease.__exit__, None, None, None)
        return lease

    def queued(self, package: str) -> tuple[list[Path], list[Path]]:
        path = package_target_lease_path(package, self.target)
        return queue_module.conflicting(path, EXCLUSIVE, (2**62, ""))

    def blocked_claim(
        self, leases: list[OwnerLease], arrival_ns: int | None = None, run_id: str | None = None
    ):
        """Start a claim that must wait; returns once it has paused, with its outcome list."""
        paused, proceed = threading.Event(), threading.Event()

        def pause(seconds: float) -> None:
            # Released once, the claim looks again; a second wait ends it, so
            # a test that leaves a holder in place does not wait out the bound.
            if proceed.is_set():
                raise RuntimeError("the claim waited again")
            paused.set()
            proceed.wait(WAIT)

        outcome: list[object] = []

        def run() -> None:
            try:
                outcome.append(acquire_claim(leases, WAIT, arrival_ns=arrival_ns, run_id=run_id))
            except BaseException as error:  # reported to the test thread
                outcome.append(error)

        patcher = patch.object(lease_module, "_pause", pause)
        patcher.start()
        self.addCleanup(patcher.stop)
        thread = threading.Thread(target=run)
        thread.start()
        self.addCleanup(thread.join, WAIT)
        self.addCleanup(proceed.set)
        self.assertTrue(paused.wait(WAIT), "the claim never waited")
        return outcome, proceed, thread

    def test_a_blocked_run_holds_no_lock_an_earlier_request_could_use(self) -> None:
        # The reader needs `a` and `m` shared and `m` is held exclusive. Its
        # wait at `m` holds no lock on `a`: a request that arrived before it
        # takes `a` exclusive at once.
        holder = acquire_claim([self.lease("m", EXCLUSIVE, "holder")], 0)
        reader = [self.lease("a", SHARED, "reader"), self.lease("m", SHARED, "reader")]
        outcome, proceed, thread = self.blocked_claim(reader)
        self.assertFalse(lease_is_held(package_target_lease_path("a", self.target)))
        earlier = acquire_claim([self.lease("a", EXCLUSIVE, "earlier")], 0, arrival_ns=1)
        earlier.close()
        self.assertEqual(outcome, [])
        holder.close()
        proceed.set()
        thread.join(WAIT)
        self.assertEqual(len(outcome), 1)
        self.assertEqual([lease.held for lease in reader], [True, True])
        outcome[0].close()

    def test_a_blocked_run_keeps_its_place_at_every_lease_of_its_claim(self) -> None:
        # Blocked at `m`, free at `a`: the run waits in both queues, so a
        # later writer cannot take `a` from under it.
        holder = acquire_claim([self.lease("m", EXCLUSIVE, "holder")], 0)
        reader = [self.lease("a", SHARED, "reader"), self.lease("m", SHARED, "reader")]
        _, _, _ = self.blocked_claim(reader)
        before, after = self.queued("a")
        self.assertEqual(len(before) + len(after), 1)
        with self.assertRaisesRegex(LeaseHeldError, "queued behind reader"):
            acquire_claim([self.lease("a", EXCLUSIVE, "later")], 0)
        before, after = self.queued("m")
        self.assertEqual(len(before) + len(after), 2)
        holder.close()

    def test_a_blocked_run_keeps_its_place_at_every_lease_it_is_blocked_at(self) -> None:
        # Each holder arrived before the run. The run is blocked at both
        # leases and waits in both queues, so neither holder's successor can
        # pass it at either.
        self.hold("a", EXCLUSIVE, "first", arrival=1)
        self.hold("b", EXCLUSIVE, "second", arrival=1)
        _, _, _ = self.blocked_claim([self.lease("a", SHARED, "run"), self.lease("b", SHARED, "run")])
        for package in ("a", "b"):
            before, after = self.queued(package)
            self.assertEqual(len(before) + len(after), 2, package)

    def test_a_later_arrival_never_overtakes_a_multi_lease_writer(self) -> None:
        # The writer needs `a` and `b` exclusive and waits for the holder of
        # `b`. Readers arriving later and alternating between `b` and `a` must
        # queue behind it at both, round after round; once the holder is gone
        # the writer, not a reader, takes both.
        self.hold("b", EXCLUSIVE, "holder", arrival=5)
        writer = [self.lease("a", EXCLUSIVE, "writer"), self.lease("b", EXCLUSIVE, "writer")]
        outcome, proceed, thread = self.blocked_claim(writer, arrival_ns=10)
        for round_number in range(20):
            package = "ba"[round_number % 2]
            # At `b` the holder, queued first, is what the reader is named
            # behind; at `a` only the writer's place stands in its way.
            with self.assertRaisesRegex(LeaseHeldError, "queued behind " + ("holder" if package == "b" else "writer")):
                acquire_claim(
                    [self.lease(package, SHARED, f"reader{round_number}")], 0, arrival_ns=20 + round_number
                )
        self.assertFalse(lease_is_held(package_target_lease_path("a", self.target)))
        self.assertEqual(outcome, [])
        self.holders[0].__exit__(None, None, None)
        proceed.set()
        thread.join(WAIT)
        self.assertEqual([isinstance(item, ExitStack) for item in outcome], [True])
        self.assertEqual([lease.held for lease in writer], [True, True])
        with self.assertRaisesRegex(LeaseHeldError, "queued behind writer"):
            acquire_claim([self.lease("a", SHARED, "after")], 0, arrival_ns=99)
        outcome[0].close()
        acquire_claim([self.lease("a", SHARED, "after")], 0, arrival_ns=99).close()

    def crossed_runs(self, first_run: str, second_run: str):
        """Two runs of one arrival with crossed modes, each queued at both leases.

        `first` needs `a` exclusive and `b` shared, `second` the reverse. Both
        have filed their tickets before either looks, the state the earlier
        order, which let the mode letter decide a tie, blocked both runs in.
        """
        first = [self.lease("a", EXCLUSIVE, "first"), self.lease("b", SHARED, "first")]
        second = [self.lease("a", SHARED, "second"), self.lease("b", EXCLUSIVE, "second")]
        for leases, run in ((first, first_run), (second, second_run)):
            for lease in leases:
                lease.arrival, lease.run = 7, run
                lease.reserve()
                self.addCleanup(lease.__exit__, None, None, None)
        return first, second

    def test_runs_of_one_arrival_with_crossed_modes_go_in_run_order(self) -> None:
        first, second = self.crossed_runs("1" * 32, "2" * 32)
        self.assertIsNone(lease_module._try_claim(first))
        blocked, error = lease_module._try_claim(second)
        self.assertIn("queued behind first", str(error))
        for lease in first:
            lease.__exit__(None, None, None)
        self.assertIsNone(lease_module._try_claim(second))
        self.assertEqual([lease.held for lease in second], [True, True])

    def test_the_run_order_of_a_tie_is_not_the_mode_order(self) -> None:
        # The same two runs with their run identifiers swapped: the other run
        # goes first. Ordering by mode would pick one of them whatever the ids.
        first, second = self.crossed_runs("2" * 32, "1" * 32)
        self.assertIsNone(lease_module._try_claim(second))
        blocked, error = lease_module._try_claim(first)
        self.assertIn("queued behind second", str(error))
        for lease in second:
            lease.__exit__(None, None, None)
        self.assertIsNone(lease_module._try_claim(first))

    def filed_places(self, package: str) -> list[tuple[int, str]]:
        """The places of the tickets filed at `package`'s lease, from the queue directory itself."""
        directory = queue_module._queue_dir(package_target_lease_path(package, self.target))
        return sorted(queue_module.place_of(path.name) for path in directory.glob("*.ticket"))

    def test_every_lease_of_a_claim_is_queued_under_its_one_arrival_and_run(self) -> None:
        # A claim that is given its arrival and run files every ticket of
        # the claim under them, so the order of two runs is the same at every
        # lease; a run id drawn per lease would order two crossed runs
        # differently at their two leases and deadlock them on a tie.
        run = "9" * 32
        claim = acquire_claim(
            [self.lease("a", EXCLUSIVE, "run"), self.lease("b", SHARED, "run")],
            0,
            arrival_ns=7,
            run_id=run,
        )
        self.addCleanup(claim.close)
        self.assertEqual(self.filed_places("a"), [(7, run)])
        self.assertEqual(self.filed_places("b"), [(7, run)])

    def test_every_lease_of_a_claim_without_a_run_id_shares_one(self) -> None:
        claim = acquire_claim(
            [self.lease("a", EXCLUSIVE, "run"), self.lease("b", EXCLUSIVE, "run")], 0, arrival_ns=7
        )
        self.addCleanup(claim.close)
        (at_a,), (at_b,) = self.filed_places("a"), self.filed_places("b")
        self.assertEqual(at_a, at_b)
        self.assertEqual(at_a[0], 7)

    def test_two_crossed_runs_of_one_arrival_each_claim_through_acquire_claim(self) -> None:
        # The tie probe through the public entry point: the first run holds
        # both leases, the second, with crossed modes, queues behind it at
        # both and takes them when the first closes.
        first = acquire_claim(
            [self.lease("a", EXCLUSIVE, "first"), self.lease("b", SHARED, "first")],
            0,
            arrival_ns=7,
            run_id="1" * 32,
        )
        second = [self.lease("a", SHARED, "second"), self.lease("b", EXCLUSIVE, "second")]
        outcome, proceed, thread = self.blocked_claim(second, arrival_ns=7, run_id="2" * 32)
        self.assertEqual(self.filed_places("a"), [(7, "1" * 32), (7, "2" * 32)])
        self.assertEqual(self.filed_places("b"), [(7, "1" * 32), (7, "2" * 32)])
        first.close()
        proceed.set()
        thread.join(WAIT)
        self.assertEqual([lease.held for lease in second], [True, True])
        outcome[0].close()

    def test_a_waiting_writer_holds_back_a_later_reader(self) -> None:
        # An earlier shared holder keeps the writer waiting; a reader that
        # arrives after the writer must not slip past it and starve it.
        first = acquire_claim([self.lease("a", SHARED, "first")], 0)
        writer = self.lease("a", EXCLUSIVE, "writer")
        outcome, proceed, thread = self.blocked_claim([writer])
        with self.assertRaisesRegex(LeaseHeldError, "queued behind writer"):
            acquire_claim([self.lease("a", SHARED, "later")], 0)
        first.close()
        proceed.set()
        thread.join(WAIT)
        self.assertTrue(writer.held)
        outcome[0].close()

    def test_a_waiting_request_does_not_hold_back_an_earlier_one(self) -> None:
        # A later request that only waits is not ahead of an earlier one.
        later = self.lease("a", EXCLUSIVE, "later")
        later.arrival = 2
        later.reserve()
        self.addCleanup(later.dequeue)
        earlier = acquire_claim([self.lease("a", EXCLUSIVE, "earlier")], 0, arrival_ns=1)
        self.assertTrue(lease_is_held(package_target_lease_path("a", self.target)))
        earlier.close()
        with self.assertRaisesRegex(LeaseHeldError, "queued behind later"):
            acquire_claim([self.lease("a", EXCLUSIVE, "after")], 0, arrival_ns=3)

    def test_a_later_holder_blocks_an_earlier_request(self) -> None:
        self.hold("a", EXCLUSIVE, "holder", arrival=5)
        with self.assertRaisesRegex(LeaseHeldError, "owned by holder"):
            acquire_claim([self.lease("a", EXCLUSIVE, "early")], 0, arrival_ns=1)

    def test_a_run_blocked_by_a_later_holder_takes_none_of_its_leases(self) -> None:
        # The look finds `b` held, so `a`, free, is not even taken and given
        # back: a transient take would still keep a peer from `a`.
        self.hold("b", EXCLUSIVE, "holder", arrival=5)
        real_take = lease_module._take
        taken: list[str] = []

        def recording(path, mode):
            taken.append(path.name)
            return real_take(path, mode)

        a_name = package_target_lease_path("a", self.target).name
        with patch.object(lease_module, "_take", recording):
            with self.assertRaisesRegex(LeaseHeldError, "owned by holder"):
                acquire_claim(
                    [self.lease("a", EXCLUSIVE, "early"), self.lease("b", EXCLUSIVE, "early")],
                    0,
                    arrival_ns=1,
                )
        self.assertNotIn(a_name, taken)

    def test_a_request_blocked_by_a_later_holder_keeps_its_place(self) -> None:
        # The earlier writer waits for the later holder; it must stay queued
        # so that no reader arriving meanwhile can keep it waiting.
        self.hold("a", EXCLUSIVE, "holder", arrival=5)
        _, _, _ = self.blocked_claim([self.lease("a", EXCLUSIVE, "early")], arrival_ns=1)
        before, after = self.queued("a")
        self.assertEqual(len(before) + len(after), 2)

    def test_a_later_shared_holder_does_not_block_an_earlier_reader(self) -> None:
        self.hold("a", SHARED, "holder", arrival=5)
        stack = acquire_claim([self.lease("a", SHARED, "early")], 0, arrival_ns=1)
        stack.close()

    def test_a_dead_requests_ticket_blocks_nobody(self) -> None:
        # A requester killed while it waited leaves its ticket unlocked.
        path = package_target_lease_path("a", self.target)
        queue = queue_module._queue_dir(path)
        queue.mkdir(parents=True, exist_ok=True)
        dead = queue / "00000000000000000001-x-1-dead.ticket"
        dead.write_text("{}", encoding="utf-8")
        claim = acquire_claim([self.lease("a", EXCLUSIVE, "run")], 0, arrival_ns=5)
        claim.close()
        self.assertFalse(dead.exists())

    def test_a_refused_claim_leaves_nothing_held_or_queued(self) -> None:
        # `b` is held by a holder that takes no ticket, so only the take finds
        # it; `a`, taken first, must be given back.
        lock = package_target_lease_path("b", self.target)
        handle = lease_module._take(lock, EXCLUSIVE)
        self.addCleanup(lease_module._release, handle, True)
        with self.assertRaisesRegex(LeaseHeldError, "owned by"):
            acquire_claim([self.lease("a", EXCLUSIVE), self.lease("b", EXCLUSIVE)], 0)
        self.assertFalse(lease_is_held(package_target_lease_path("a", self.target)))
        self.assertEqual(self.queued("a"), ([], []))
        self.assertEqual(self.queued("b"), ([], []))

    def test_a_take_lost_to_a_peer_is_retried_from_nothing(self) -> None:
        # `b` is held by a holder that takes no ticket, so the look finds it
        # free and only the take fails, after `a` was taken. The claim gives
        # `a` back, waits, and takes both once `b` is released.
        handle = lease_module._take(package_target_lease_path("b", self.target), EXCLUSIVE)
        leases = [self.lease("a", EXCLUSIVE, "run"), self.lease("b", EXCLUSIVE, "run")]
        outcome, proceed, thread = self.blocked_claim(leases)
        self.assertFalse(lease_is_held(package_target_lease_path("a", self.target)))
        lease_module._release(handle, True)
        proceed.set()
        thread.join(WAIT)
        self.assertEqual([isinstance(item, ExitStack) for item in outcome], [True])
        self.assertEqual([lease.held for lease in leases], [True, True])
        outcome[0].close()

    def test_the_deadline_refuses_the_claim_without_taking_a_lease(self) -> None:
        holder = self.hold("b", EXCLUSIVE, "holder", arrival=1)
        leases = [self.lease("a", EXCLUSIVE), self.lease("b", EXCLUSIVE)]
        with self.assertRaisesRegex(BuildIdentityError, "still held by holder at holder-revision after waiting 0.3 s"):
            acquire_claim(leases, 0.3)
        self.assertFalse(lease_is_held(package_target_lease_path("a", self.target)))
        self.assertTrue(holder.held)
        self.assertEqual(self.queued("a"), ([], []))

    def test_a_second_phase_with_the_runs_arrival_goes_before_a_waiter(self) -> None:
        # The run's shared phase ended and a peer queued for the lease; asking
        # again exclusive with the run's own arrival must not queue behind it.
        run = acquire_claim([self.lease("a", SHARED, "run")], 0, arrival_ns=10)
        waiter = self.lease("a", EXCLUSIVE, "waiter")
        waiter.arrival = 20
        waiter.reserve()
        self.addCleanup(waiter.dequeue)
        run.close()
        again = acquire_claim([self.lease("a", EXCLUSIVE, "run")], 0, arrival_ns=10)
        again.close()

    def test_claims_listing_their_leases_in_opposite_orders_both_finish(self) -> None:
        held: dict[str, str] = {}
        guard = threading.Lock()
        failures: list[str] = []
        start = threading.Barrier(2)

        def run(name: str, order: tuple[str, str]) -> None:
            start.wait(WAIT)
            for _ in range(5):
                stack = acquire_claim([self.lease(package, EXCLUSIVE, name) for package in order], WAIT)
                with guard:
                    for package in order:
                        if package in held:
                            failures.append(f"{package} held by {held[package]} and {name}")
                        held[package] = name
                # The work done under the leases, long enough for a second
                # holder to be seen.
                sum(range(200_000))
                with guard:
                    for package in order:
                        del held[package]
                stack.close()

        workers = [
            threading.Thread(target=run, args=("first", ("a", "b"))),
            threading.Thread(target=run, args=("second", ("b", "a"))),
        ]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(WAIT)
        self.assertEqual([worker.is_alive() for worker in workers], [False, False])
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
