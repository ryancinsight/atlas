#!/usr/bin/env python3
"""The arrival order of lease requests is strict and total, whatever the modes."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_build_queue as queue_module
from atlas_build_lease import (
    EXCLUSIVE,
    SHARED,
    LeaseHeldError,
    OwnerLease,
    lease_is_held,
    package_target_lease_path,
)
from atlas_build_queue import Ticket, conflicting, place_of

FIRST_RUN = "1" * 32
SECOND_RUN = "2" * 32


class QueueOrderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="atlas-queue-"))
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    def lease_path(self, package: str) -> Path:
        return package_target_lease_path(package, self.base / "target")

    def ticket(self, package: str, mode: str, arrival: int, run: str) -> Ticket:
        ticket = Ticket(self.lease_path(package), mode, {"root": run}, arrival, run)
        self.addCleanup(ticket.close)
        return ticket

    def crossed_tickets(self, first_run: str, second_run: str):
        """Two runs of one arrival, `a` exclusive and `b` shared against the reverse."""
        first = [self.ticket("a", EXCLUSIVE, 7, first_run), self.ticket("b", SHARED, 7, first_run)]
        second = [self.ticket("a", SHARED, 7, second_run), self.ticket("b", EXCLUSIVE, 7, second_run)]
        return first, second

    def test_a_tie_of_crossed_modes_is_ordered_by_run_at_every_lease(self) -> None:
        # The lower run id is ahead at both leases, though its mode letter sorts
        # before the other's at one and after it at the other.
        first, second = self.crossed_tickets(FIRST_RUN, SECOND_RUN)
        for ticket in first:
            self.assertEqual(ticket.ahead(ticket.mode), [])
        self.assertEqual([path.name.split("-")[1:3] for path in second[0].ahead(SHARED)], [["x", FIRST_RUN]])
        self.assertEqual([path.name.split("-")[1:3] for path in second[1].ahead(EXCLUSIVE)], [["s", FIRST_RUN]])

    def test_the_order_of_a_tie_follows_the_run_not_the_mode(self) -> None:
        # The same two runs with their run ids swapped: the other goes first.
        first, second = self.crossed_tickets(SECOND_RUN, FIRST_RUN)
        for ticket in second:
            self.assertEqual(ticket.ahead(ticket.mode), [])
        for ticket in first:
            self.assertEqual(len(ticket.ahead(ticket.mode)), 1)

    def test_conflicting_and_ahead_agree_on_every_ticket_of_a_tie(self) -> None:
        first, second = self.crossed_tickets(FIRST_RUN, SECOND_RUN)
        for tickets, runs in ((first, "first"), (second, "second")):
            for ticket in tickets:
                before, after = conflicting(ticket.lease, ticket.mode, ticket.place, ticket.path)
                self.assertEqual(before, ticket.ahead(ticket.mode), runs)
                self.assertEqual(len(before) + len(after), 1, runs)

    def test_a_ticket_of_the_requests_own_run_conflicts_with_nothing(self) -> None:
        # A shared ticket re-filed beside the exclusive one it replaces, or a
        # re-created ticket, carries the same place and is the request itself.
        exclusive = self.ticket("a", EXCLUSIVE, 7, FIRST_RUN)
        self.ticket("a", SHARED, 7, FIRST_RUN)
        self.assertEqual(conflicting(exclusive.lease, EXCLUSIVE, exclusive.place, exclusive.path), ([], []))
        self.assertEqual(exclusive.ahead(EXCLUSIVE), [])

    def test_a_ticket_name_gives_its_place_and_an_older_checkers_ties_with_nothing(self) -> None:
        new = f"{7:020d}-x-{FIRST_RUN}-4242-{'a' * 32}.ticket"
        old = f"{7:020d}-s-4242-{'b' * 32}.ticket"
        self.assertEqual(place_of(new), (7, FIRST_RUN))
        self.assertEqual(place_of(old), (7, f"4242-{'b' * 32}"))
        self.assertNotEqual(place_of(old), place_of(f"{7:020d}-s-4243-{'b' * 32}.ticket"))
        self.assertTrue(queue_module._is_exclusive(new))
        self.assertFalse(queue_module._is_exclusive(old))

    def test_a_lease_keeps_its_place_when_it_gives_the_lock_back(self) -> None:
        path = self.lease_path("a")
        held = OwnerLease(path, {"root": "held"}, 60, EXCLUSIVE, 5, FIRST_RUN)
        self.addCleanup(held.__exit__, None, None, None)
        held.attempt()
        self.assertTrue(lease_is_held(path))
        held.unhold()
        self.assertFalse(lease_is_held(path))
        self.assertIsNotNone(held.ticket)
        self.assertTrue(held.ticket.path.exists())
        # A later request is still queued behind the place the lock was given up from.
        later = OwnerLease(path, {"root": "later"}, 60, EXCLUSIVE, 6, SECOND_RUN)
        self.addCleanup(later.dequeue)
        with self.assertRaisesRegex(LeaseHeldError, "queued behind held"):
            later.attempt()
        held.unhold()

    def test_reserving_twice_keeps_the_first_place(self) -> None:
        lease = OwnerLease(self.lease_path("a"), {"root": "run"}, 60, EXCLUSIVE, 5, FIRST_RUN)
        self.addCleanup(lease.dequeue)
        lease.reserve()
        first = lease.ticket
        lease.arrival = 99
        lease.reserve()
        self.assertIs(lease.ticket, first)
        self.assertEqual(lease.ticket.place, (5, FIRST_RUN))


if __name__ == "__main__":
    unittest.main()
