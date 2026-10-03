#!/usr/bin/env python3
"""The hook's `claim_lock`: one live holder at a time, and a refusal only for a live holder.

The ref lock of a gate and the export a checkout builds in take a lock
directory naming its holder. A dead holder's lock is replaced exactly once
however many waiters find it; a lock is refused only on a live holder, named;
a filesystem step that fails once is retried, and one that keeps failing, or a
lock with no pid, is reported as no holder rather than as a phantom one.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import time
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "git-hooks" / "pre-push"
# The most a test waits for one subprocess: four times the slowest test here,
# 7.21 s measured under `-n 4` beside the claim and identity suites (the
# race test, two bash waiters through a lockstep).
WAIT = 30
# The most a waiter blocks on a peer's event that never comes, in a run that has
# already failed: twice that slowest whole test, and half of WAIT, so the
# waiter's own message arrives before the test's timeout. The race test's
# rendezvous kept within it in the run of the stack's eight suites at `-n 4` on
# the same host, with peer gates running (2026-10-03: all of this file's tests
# passed).
BOUND = WAIT // 2


def lock_functions() -> str:
    """The hook's lock functions, from the first helper to the end of `claim_lock`."""
    source = SCRIPT.read_text(encoding="utf-8")
    start = source.index("process_start_token() {")
    end = source.index("\nclaim_lock() {")
    return source[start : source.index("\n}\n", end) + 3]


def run(body: str, *args: str) -> subprocess.Popen:
    """A bash running the lock functions, then `body`."""
    program = "run_temps=()\n" + lock_functions() + body
    return subprocess.Popen(
        ["bash", "-c", program, "bash", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def outcome(body: str, *args: str) -> dict[str, str]:
    """`claim_lock`'s status and `lock_holder`, as the body printed them."""
    child = run(body, *args)
    stdout, stderr = child.communicate(timeout=WAIT)
    assert child.returncode == 0, stderr.decode("utf-8", errors="replace")
    return dict(
        line.split("=", 1) for line in stdout.decode().replace("\r", "").splitlines() if "=" in line
    )


CLAIM = 'claim_lock "$1" note && status=0 || status=$?\necho "status=$status"\necho "holder=$lock_holder"\n'

# Two waiters that read one dead holder, run in lockstep by blocking reads on
# FIFOs, never by polling. Each, once its own check finds the pid dead, goes on
# only when the other has found it dead too (`ab` and `ba` are the two halves
# of the rendezvous). The one whose `rm -rf` of the lock comes second then goes
# on only after the first has claimed the lock (`won`), so replacing a dead
# holder's lock by read, remove and install gives both a win; with one
# reclaimer at a time the second never reaches the `rm`, finds a live holder
# and reports it (`refused`). The winner stays alive, as a holder must, until
# the other is refused; a second winner releases it at once. `patience` bounds
# a defect, never a step: every wait ends at an event, and one that does not
# arrive in `BOUND` seconds ends the run with status 3 and a message.
RACE = """LOCK="$1"
BOUND="$2"
exec 7<>"$LOCK.won"
patience() { read -t "$BOUND" -r _ < "$1" || { echo "no event on $1 within $BOUND s" >&2; exit 3; }; }
checked=0
kill() {
  builtin kill "$@" && return 0
  if [ "$checked" -eq 0 ]; then
    checked=1
    if mkdir "$LOCK.first" 2>/dev/null; then
      echo checked > "$LOCK.ab"
      patience "$LOCK.ba"
    else
      patience "$LOCK.ab"
      echo checked > "$LOCK.ba"
    fi
  fi
  return 1
}
rm() {
  if [ "$1" = -rf ] && [ "$2" = "$LOCK" ] && ! mkdir "$LOCK.turn" 2>/dev/null; then
    patience "$LOCK.won"
  fi
  command rm "$@"
}
if claim_lock "$LOCK" note; then
  echo won
  echo won >&7
  if mkdir "$LOCK.winner" 2>/dev/null; then
    patience "$LOCK.refused"
  else
    echo refused > "$LOCK.refused"
  fi
else
  echo refused > "$LOCK.refused"
fi
"""

# The first three moves of the lock into place fail; the fourth works.
FLAKY = """count=0
mv() {
  count=$((count + 1))
  [ "$count" -gt 3 ] || return 1
  command mv "$@"
}
"""


class ClaimLockTestCase(unittest.TestCase):
    def lock_dir(self) -> pathlib.Path:
        temp = tempfile.TemporaryDirectory(prefix="atlas-lock-")
        self.addCleanup(temp.cleanup)
        return pathlib.Path(temp.name)

    def dead_pid(self) -> str:
        return subprocess.run(
            ["bash", "-c", "echo $$"], capture_output=True, text=True, check=True
        ).stdout.strip()

    def live_pid(self) -> tuple[subprocess.Popen, str]:
        """A running bash and the pid its own shell calls it by."""
        holder = subprocess.Popen(
            ["bash", "-c", "echo $$; read -r _"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        self.addCleanup(holder.wait, WAIT)
        self.addCleanup(holder.kill)
        pid = holder.stdout.readline().decode().strip()
        self.assertTrue(pid)
        return holder, pid

    def lock(
        self, base: pathlib.Path, pid: str | None, *, children: tuple[str, ...] = ()
    ) -> pathlib.Path:
        lock = base / "lock"
        lock.mkdir()
        if pid is not None:
            (lock / "pid").write_text(pid + "\n", encoding="utf-8")
        (lock / "note").write_text("held\n", encoding="utf-8")
        if children:
            (lock / "children").write_text("".join(c + "\n" for c in children), encoding="utf-8")
        return lock

    def start_waiters(self, base: pathlib.Path, name: str) -> list[subprocess.Popen]:
        """Two waiters for the lock `name`, held by a dead pid, with their FIFOs made."""
        lock = base / name
        lock.mkdir()
        (lock / "pid").write_text(self.dead_pid() + "\n", encoding="utf-8")
        (lock / "note").write_text("dead\n", encoding="utf-8")
        fifos = [f"{lock.as_posix()}.{suffix}" for suffix in ("ab", "ba", "won", "refused")]
        subprocess.run(["mkfifo", *fifos], check=True)
        waiters = [run(RACE, lock.as_posix(), str(BOUND)) for _ in range(2)]
        for waiter in waiters:
            self.addCleanup(waiter.wait, WAIT)
            self.addCleanup(waiter.kill)
        return waiters

    def test_two_waiters_for_a_dead_holders_lock_install_one(self) -> None:
        base = self.lock_dir()
        for number in range(2):
            waiters = self.start_waiters(base, f"lock{number}")
            results = [waiter.communicate(timeout=WAIT) for waiter in waiters]
            for waiter, (_, stderr) in zip(waiters, results):
                self.assertEqual(waiter.returncode, 0, stderr.decode(errors="replace"))
            won = sum(stdout.decode().count("won") for stdout, _ in results)
            self.assertEqual(won, 1, f"round {number}: {won} waiters installed the lock")

    def test_a_reclaimer_that_read_a_dead_holder_leaves_the_lock_a_peer_replaced(self) -> None:
        # The stale read: this waiter read the dead pid, a peer then replaced
        # the lock, and only now does this waiter take the mutex the peer
        # released. Under the mutex it reads the holder again, finds the
        # peer's live pid and removes nothing.
        base = self.lock_dir()
        holder, pid = self.live_pid()
        lock = self.lock(base, pid)
        staged = base / "staged"
        staged.mkdir()
        (staged / "pid").write_text("mine\n", encoding="utf-8")
        result = outcome(
            'reclaim_lock "$1" "$2" "$3" && status=0 || status=$?\necho "status=$status"',
            lock.as_posix(),
            staged.as_posix(),
            self.dead_pid(),
        )
        self.assertEqual(result, {"status": "1"})
        self.assertEqual((lock / "pid").read_text(encoding="utf-8").strip(), pid)
        self.assertTrue(staged.exists(), "the staged lock was installed over a live holder's")
        self.assertFalse((base / "lock.reclaim").exists(), "the mutex was left held")

    def test_a_reclaimer_whose_read_still_holds_installs_its_lock(self) -> None:
        base = self.lock_dir()
        dead = self.dead_pid()
        lock = self.lock(base, dead)
        staged = base / "staged"
        staged.mkdir()
        (staged / "pid").write_text("mine\n", encoding="utf-8")
        result = outcome(
            'reclaim_lock "$1" "$2" "$3" && status=0 || status=$?\necho "status=$status"',
            lock.as_posix(),
            staged.as_posix(),
            dead,
        )
        self.assertEqual(result, {"status": "0"})
        self.assertEqual((lock / "pid").read_text(encoding="utf-8").strip(), "mine")
        self.assertFalse((base / "lock.reclaim").exists(), "the mutex was left held")

    def test_a_waiter_that_finds_the_mutex_held_names_no_holder(self) -> None:
        # Another reclaimer holds the mutex for the whole budget. The dead pid
        # this waiter read is no holder, so the answer is "could not be taken",
        # status 2 with no holder, and never a refusal naming the dead pid.
        base = self.lock_dir()
        lock = self.lock(base, self.dead_pid())
        (base / "lock.reclaim").mkdir()
        body = "lock_attempts=3\n" + CLAIM
        result = outcome(body, lock.as_posix())
        self.assertEqual(result, {"status": "2", "holder": ""})
        self.assertTrue((base / "lock.reclaim").exists(), "a fresh mutex was cleared")

    def test_a_waiter_goes_on_when_the_mutex_is_released(self) -> None:
        # The peer releases the mutex while this waiter sleeps between steps;
        # the waiter's next step reclaims the lock.
        base = self.lock_dir()
        lock = self.lock(base, self.dead_pid())
        mutex = base / "lock.reclaim"
        mutex.mkdir()
        body = 'MUTEX="$1.reclaim"\nsleep() { rmdir "$MUTEX"; }\n' + CLAIM
        result = outcome(body, lock.as_posix())
        self.assertEqual(result, {"status": "0", "holder": ""})

    def test_a_mutex_its_owner_died_holding_is_cleared_after_its_age_bound(self) -> None:
        # A reclaimer that died holding the mutex left it behind. The bound is
        # `lock_mutex_seconds`, 5 s: four times the 1.21 s worst hold measured
        # for a live reclaimer (see the hook), not a minute, which would make
        # every claim in that time return status 2 and gate without the lock.
        base = self.lock_dir()
        lock = self.lock(base, self.dead_pid())
        mutex = base / "lock.reclaim"
        mutex.mkdir()
        self.age(mutex, 10)
        body = "lock_attempts=3\n" + CLAIM
        result = outcome(body, lock.as_posix())
        self.assertEqual(result, {"status": "0", "holder": ""})
        self.assertFalse(mutex.exists(), "the stale mutex was left in place")

    def test_a_mutex_younger_than_its_age_bound_is_kept(self) -> None:
        # The same mutex, 10 s old, under a bound of 1000 s: kept, and the
        # claim reports status 2 with no holder, never the dead reclaimer's pid.
        base = self.lock_dir()
        lock = self.lock(base, self.dead_pid())
        mutex = base / "lock.reclaim"
        mutex.mkdir()
        self.age(mutex, 10)
        body = "lock_attempts=3\nlock_mutex_seconds=1000\n" + CLAIM
        result = outcome(body, lock.as_posix())
        self.assertEqual(result, {"status": "2", "holder": ""})
        self.assertTrue(mutex.exists(), "a mutex inside its bound was cleared")

    def age(self, path: pathlib.Path, seconds: float) -> None:
        """Set `path`'s modification time `seconds` before now."""
        moment = time.time() - seconds
        os.utime(path, (moment, moment))

    def test_a_live_holder_is_refused_and_named(self) -> None:
        base = self.lock_dir()
        holder, pid = self.live_pid()
        self.lock(base, pid)
        result = outcome(CLAIM, (base / "lock").as_posix())
        self.assertEqual(result, {"status": "1", "holder": pid})

    def test_a_dead_holder_with_a_live_step_is_refused_and_the_step_named(self) -> None:
        base = self.lock_dir()
        step, step_pid = self.live_pid()
        self.lock(base, self.dead_pid(), children=(step_pid,))
        result = outcome(CLAIM, (base / "lock").as_posix())
        self.assertEqual(result, {"status": "1", "holder": step_pid})
        # The step ends: the lock is the dead holder's alone and is replaced.
        step.stdin.write(b"\n")
        step.stdin.close()
        step.wait(WAIT)
        result = outcome(CLAIM, (base / "lock").as_posix())
        self.assertEqual(result["status"], "0")

    def token(self, pid: str) -> str:
        """The start token of the live process `pid`, as the hook computes it."""
        token = outcome('echo "token=$(process_start_token "$1")"', pid)["token"]
        self.assertTrue(token, "this platform gives no process start token")
        return token

    def test_a_reused_pid_is_not_the_holder(self) -> None:
        # The lock names a pid with the token of the process that held it. The
        # process now running under that pid has another token: a stranger
        # that reused the pid, so the lock is replaced, not held for it.
        base = self.lock_dir()
        stranger, pid = self.live_pid()
        lock = self.lock(base, f"{pid} {self.token(pid)}1")
        result = outcome(CLAIM, lock.as_posix())
        self.assertEqual(result, {"status": "0", "holder": ""})

    def test_a_reused_pid_in_the_step_list_is_not_the_holder(self) -> None:
        base = self.lock_dir()
        stranger, pid = self.live_pid()
        lock = self.lock(base, self.dead_pid(), children=(f"{pid} {self.token(pid)}1",))
        result = outcome(CLAIM, lock.as_posix())
        self.assertEqual(result, {"status": "0", "holder": ""})

    def test_a_pid_with_its_own_token_is_the_holder(self) -> None:
        base = self.lock_dir()
        holder, pid = self.live_pid()
        lock = self.lock(base, f"{pid} {self.token(pid)}")
        result = outcome(CLAIM, lock.as_posix())
        self.assertEqual(result, {"status": "1", "holder": pid})

    def test_a_pid_with_no_token_is_trusted_on_its_liveness(self) -> None:
        # A lock written where the platform gave no token, or before tokens.
        base = self.lock_dir()
        holder, pid = self.live_pid()
        lock = self.lock(base, pid)
        result = outcome(CLAIM, lock.as_posix())
        self.assertEqual(result, {"status": "1", "holder": pid})

    def test_a_claim_records_its_pid_and_start_token(self) -> None:
        # Run under a stand-in `process_start_token` so the expected line is
        # known without reading the same process twice.
        base = self.lock_dir()
        lock = base / "lock"
        body = (
            'process_start_token() { echo "token-of-$1"; }\n'
            + CLAIM
            + 'echo "pid=$$"\n'
            + 'cat "$1/pid"\n'
        )
        child = run(body, lock.as_posix())
        stdout, stderr = child.communicate(timeout=WAIT)
        self.assertEqual(child.returncode, 0, stderr.decode("utf-8", errors="replace"))
        lines = stdout.decode().replace("\r", "").splitlines()
        pid = next(line.split("=", 1)[1] for line in lines if line.startswith("pid="))
        self.assertEqual(lines[-1], f"{pid} token-of-{pid}")

    def test_a_process_start_token_is_its_own_and_stable(self) -> None:
        holder, pid = self.live_pid()
        first = self.token(pid)
        self.assertEqual(self.token(pid), first)
        self.assertEqual(outcome('echo "token=$(process_start_token "$1")"', self.dead_pid())["token"], "")

    def test_a_dead_holder_is_replaced(self) -> None:
        base = self.lock_dir()
        self.lock(base, self.dead_pid(), children=(self.dead_pid(),))
        result = outcome(CLAIM, (base / "lock").as_posix())
        self.assertEqual(result, {"status": "0", "holder": ""})

    def test_a_filesystem_step_that_fails_for_a_moment_is_retried(self) -> None:
        base = self.lock_dir()
        result = outcome(FLAKY + CLAIM, (base / "lock").as_posix())
        self.assertEqual(result, {"status": "0", "holder": ""})

    def test_a_step_that_keeps_failing_names_no_holder(self) -> None:
        base = self.lock_dir()
        body = "lock_attempts=3\nmv() { return 1; }\n" + CLAIM
        result = outcome(body, (base / "lock").as_posix())
        self.assertEqual(result, {"status": "2", "holder": ""})

    def test_a_lock_with_no_pid_is_replaced_after_the_grace(self) -> None:
        base = self.lock_dir()
        self.lock(base, None)
        body = "lock_pidless_grace=3\nlock_attempts=20\n" + CLAIM
        result = outcome(body, (base / "lock").as_posix())
        self.assertEqual(result, {"status": "0", "holder": ""})

    def test_a_lock_with_no_pid_inside_the_grace_names_no_holder(self) -> None:
        base = self.lock_dir()
        self.lock(base, None)
        body = "lock_pidless_grace=1000\nlock_attempts=3\n" + CLAIM
        result = outcome(body, (base / "lock").as_posix())
        self.assertEqual(result, {"status": "2", "holder": ""})


if __name__ == "__main__":
    unittest.main()
