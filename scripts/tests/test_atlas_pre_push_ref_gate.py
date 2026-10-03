#!/usr/bin/env python3
"""One gate per ref of a repository: a second push of a ref a live gate is running is refused.

The stack's identity checker is replaced by one that blocks the first step of
each revision on a socket the test holds, so a gate is "running" exactly while
the test has not released it. Gates of different refs are not held back by one
another; a gate whose hook was killed outright still counts as running while
the identity step it started does.

Every wait ends at an event on one queue: a step announces itself, a gate
reports its end, and a step's end is its socket's close. A wait takes the
event it expects and fails at once on any other: a gate that ends before its
step announced, or a step that announces while the test waits for its gate to
end (a gate that should have been refused). `WAIT` bounds a failure only.
"""

from __future__ import annotations

import json
import os
import pathlib
import queue
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest

from atlas_git_process import _terminate_process_tree
from test_atlas_pre_push_gate import (
    GateFixture,
    _IDENT,
    _git,
    _publish_stack_scripts,
    _write,
)

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "git-hooks" / "pre-push"
# The longest the test waits on an event that has not come, in a run that has
# already failed. A whole test, which runs one or two gates to their end, took
# 201.32 s at the worst of this file's gate tests when run with the stack's
# eight suites at `-n 4` on the development host with peer gates running
# (2026-10-03: 333 passed, 18.5 min; 72.11 s in the same run without the claim
# and sharing suites, 37 s to 46.65 s in runs of the file alone); the bound is
# four times that, rounded up, as the sharing retry's is (atlas_build_lock.py).
# No passing test waits on it, and a failure is reported at the event that
# broke it, not at this bound.
WAIT = 810

# The first identity step of a revision announces itself on the test's socket
# and waits for a byte back; every later step of that revision runs at once.
# The socket stays open until the step ends, so its close is the step's end.
_BLOCKING_IDENTITY = (
    "import os, pathlib, socket, subprocess, sys\n"
    "argv = sys.argv[1:]\n"
    "root = argv[argv.index('--root') + 1]\n"
    "cwd = argv[argv.index('--command-cwd') + 1]\n"
    "rev = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],\n"
    "                     capture_output=True, text=True).stdout.strip()\n"
    "seen = pathlib.Path(os.environ['IDENTITY_SEEN'])\n"
    "seen.mkdir(exist_ok=True)\n"
    "try:\n"
    "    (seen / rev).touch(exist_ok=False)\n"
    "except FileExistsError:\n"
    "    pass\n"
    "else:\n"
    "    peer = socket.create_connection(('127.0.0.1', int(os.environ['IDENTITY_PORT'])))\n"
    "    peer.sendall(rev.encode() + b'\\n')\n"
    "    peer.recv(1)\n"
    "command = [os.environ.get('CARGO', 'cargo') if value == 'cargo' else value\n"
    "           for value in argv[argv.index('--') + 1:]]\n"
    "raise SystemExit(subprocess.run(command, cwd=cwd).returncode)\n"
)


class Gate:
    """A running hook: its stderr in a file, and its end reported on the test's queue."""

    def __init__(
        self, process: subprocess.Popen, stderr: pathlib.Path, events: queue.Queue
    ) -> None:
        self.process = process
        self.stderr_path = stderr
        self.exit_expected = threading.Event()
        self.ended = threading.Event()
        threading.Thread(target=self._report_exit, args=(events,), daemon=True).start()

    def _report_exit(self, events: queue.Queue) -> None:
        self.process.wait()
        self.ended.set()
        events.put(("ended", self, None))

    def stderr(self) -> str:
        return self.stderr_path.read_text(encoding="utf-8", errors="replace")


class RefGateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="atlas-gate-")
        self.addCleanup(temp.cleanup)
        self.stack = pathlib.Path(temp.name)
        _write(self.stack / "scripts" / "atlas-build-identity.py", _BLOCKING_IDENTITY)
        _write(self.stack / "scripts" / "atlas-conformance.py", "raise SystemExit(0)\n")
        _write(self.stack / "scripts" / "atlas_stack.py", "ROOT = None\n")
        _publish_stack_scripts(self.stack)
        self.fixture = GateFixture(self.stack / "repos" / "member")
        metadata = json.loads((self.fixture.bin / "metadata.json").read_text(encoding="utf-8"))
        metadata["target_directory"] = str(self.stack / "target")
        _write(self.fixture.bin / "metadata.json", json.dumps(metadata))
        self.revisions = {branch: self.commit_branch(branch) for branch in ("feat", "other")}
        self.events: queue.Queue = queue.Queue()
        self.peers: list[socket.socket] = []
        self.addCleanup(lambda: [peer.close() for peer in self.peers])
        self.listener = socket.socket()
        self.addCleanup(self.listener.close)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        threading.Thread(target=self._accept_announcements, daemon=True).start()
        self.env = {
            "IDENTITY_PORT": str(self.listener.getsockname()[1]),
            "IDENTITY_SEEN": str(self.stack / "seen"),
        }
        self.gates: list[Gate] = []

    def _accept_announcements(self) -> None:
        """Queue each step's announcement, with the connection that holds the step."""
        while True:
            try:
                peer, _ = self.listener.accept()
            except OSError:
                return
            self.peers.append(peer)
            peer.settimeout(WAIT)
            try:
                line = peer.recv(64).decode().strip()
            except OSError:
                return
            self.events.put(("announced", line, peer))

    def next_event(self, waiting_for: str) -> tuple[str, object, object]:
        try:
            return self.events.get(timeout=WAIT)
        except queue.Empty:
            self.fail(f"no event within the wait bound while waiting for {waiting_for}:\n{self.stderrs()}")

    def stderrs(self) -> str:
        return "\n".join(gate.stderr() for gate in self.gates)

    def commit_branch(self, branch: str) -> str:
        root = self.fixture.root
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", branch, "main"], check=True
        )
        (root / "crates" / "foo" / "src" / "lib.rs").write_text(f"pub fn f() {{}}\n// {branch}\n")
        subprocess.run(["git", "-C", str(root), *_IDENT, "commit", "-q", "-am", branch], check=True)
        return _git(root, "rev-parse", branch)

    def own_temp_base(self) -> str:
        """A temporary base no other gate of the test shares."""
        base = tempfile.mkdtemp(prefix="atlas-gate-tmp-")
        self.addCleanup(shutil.rmtree, base, ignore_errors=True)
        return pathlib.Path(base).as_posix()

    def start(
        self,
        branch: str,
        remote: str | None = None,
        extra_env: dict[str, str] | None = None,
        expect_exit: bool = False,
    ) -> Gate:
        """Start the hook for `branch`'s tip as a push of a new `remote` branch (`branch` by default).

        A gate that ends before its step announced fails the wait, unless the
        test expects it to end (a refused one).
        """
        sha = self.revisions[branch]
        number = len(self.gates) + 1
        stdin = self.stack / f"push-{number}.txt"
        stdin.write_text(
            f"refs/heads/{branch} {sha} refs/heads/{remote or branch} {'0' * 40}\n", encoding="utf-8"
        )
        stderr = self.stack / f"stderr-{number}.txt"
        options = {"start_new_session": True} if os.name != "nt" else {}
        with open(stdin, "rb") as pushed, open(stderr, "wb") as errors:
            process = subprocess.Popen(
                ["bash", str(SCRIPT)],
                stdin=pushed,
                stderr=errors,
                cwd=str(self.fixture.root),
                env=self.fixture.hook_environment({**self.env, **(extra_env or {})}),
                **options,
            )
        gate = Gate(process, stderr, self.events)
        if expect_exit:
            gate.exit_expected.set()
        self.gates.append(gate)
        # The gate's whole process tree dies with the test: the hook's children
        # hold its stdin file open, and Windows refuses to delete an open file.
        self.addCleanup(_terminate_process_tree, process)
        return gate

    def running(self, revision: str) -> socket.socket:
        """The connection of the identity step that announced `revision`.

        A gate that ends instead, unless its end was expected, fails the test at
        once, with every gate's stderr; so does an announcement of another revision.
        """
        while True:
            kind, subject, peer = self.next_event(f"{revision} to announce")
            if kind == "announced":
                self.assertEqual(subject, revision)
                return peer
            if not subject.exit_expected.is_set():
                code = subject.process.returncode
                self.fail(f"a gate ended ({code}) before its step announced {revision}:\n{self.stderrs()}")

    def output(self, gate: Gate) -> str:
        """The gate's stderr once it has ended.

        The gate ends of its own accord here: a step that announces meanwhile
        is a gate that was not refused and now waits for a byte this test will
        not send, so it fails the test at once instead of at the wait bound.
        """
        gate.exit_expected.set()
        while not gate.ended.is_set():
            kind, subject, _ = self.next_event("the gate to end")
            if kind == "announced":
                self.fail(f"a step announced {subject} while its gate was expected to end:\n{self.stderrs()}")
            if subject is not gate and not subject.exit_expected.is_set():
                self.fail(f"another gate ended ({subject.process.returncode}):\n{self.stderrs()}")
        return gate.stderr()

    def finish(self, gate: Gate, peer: socket.socket) -> tuple[int, str]:
        gate.exit_expected.set()
        peer.sendall(b"1")
        stderr = self.output(gate)
        return gate.process.returncode, stderr

    def holder(self, refusal: str) -> str:
        """The pid a refusal names."""
        line = next(line for line in refusal.splitlines() if "is already gating" in line)
        return line.split("pre-push: pid ", 1)[1].split(" ", 1)[0]

    def recorded_pids(self, name: str) -> list[str]:
        """The pids the one ref lock's `name` file lists, each line's first field."""
        common = _git(self.fixture.root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        (lock,) = pathlib.Path(common, "atlas-gate").glob("ref-*.lock")
        text = (lock / name).read_text(encoding="utf-8")
        return [line.split()[0] for line in text.splitlines() if line.strip()]

    def test_a_second_gate_of_the_same_ref_is_refused(self) -> None:
        first = self.start("feat")
        peer = self.running(self.revisions["feat"])
        (held,) = self.recorded_pids("pid")
        second = self.start("feat", expect_exit=True)
        refused = self.output(second)
        self.assertEqual(second.process.returncode, 1, refused)
        # The refusal names the pid the first gate wrote in its lock, not the
        # refusing gate's own.
        self.assertEqual(self.holder(refused), held)
        self.assertIn(f"pid {held} is already gating refs/heads/feat", refused)
        self.assertIn(self.revisions["feat"], refused)
        code, stderr = self.finish(first, peer)
        self.assertEqual(code, 0, stderr)

    def test_a_second_gate_of_the_same_ref_is_refused_across_temporary_bases(self) -> None:
        # The lock is the repository's, not the temporary base's: a second
        # gate with a base of its own finds the first one.
        first = self.start("feat")
        peer = self.running(self.revisions["feat"])
        (held,) = self.recorded_pids("pid")
        second = self.start("feat", extra_env={"TMPDIR": self.own_temp_base()}, expect_exit=True)
        refused = self.output(second)
        self.assertEqual(second.process.returncode, 1, refused)
        self.assertIn(f"pid {held} is already gating refs/heads/feat", refused)
        code, stderr = self.finish(first, peer)
        self.assertEqual(code, 0, stderr)

    def test_a_gate_of_another_ref_is_not_held_back(self) -> None:
        # The first gate's step is running when the second ref's step starts:
        # both announce themselves before either is released. A second gate
        # that is refused instead ends, and `running` fails at that moment.
        first = self.start("feat")
        first_peer = self.running(self.revisions["feat"])
        second = self.start("other")
        second_peer = self.running(self.revisions["other"])
        code, stderr = self.finish(second, second_peer)
        self.assertEqual(code, 0, stderr)
        code, stderr = self.finish(first, first_peer)
        self.assertEqual(code, 0, stderr)

    def test_the_lock_is_keyed_by_the_ref_pushed_to_not_the_local_one(self) -> None:
        # Two local branches pushed to one remote ref repeat each other's gate;
        # one local branch pushed to two remote refs does not.
        first = self.start("feat", remote="release")
        peer = self.running(self.revisions["feat"])
        second = self.start("other", remote="release", expect_exit=True)
        refused = self.output(second)
        self.assertEqual(second.process.returncode, 1, refused)
        self.assertIn("is already gating refs/heads/release", refused)
        third = self.start("feat", remote="elsewhere")
        # `feat`'s revision is already seen, so the third gate runs through
        # without announcing; it must end 0, not refused.
        stderr = self.output(third)
        self.assertEqual(third.process.returncode, 0, stderr)
        code, stderr = self.finish(first, peer)
        self.assertEqual(code, 0, stderr)

    def test_a_finished_gates_lock_does_not_hold_the_ref(self) -> None:
        first = self.start("feat")
        code, stderr = self.finish(first, self.running(self.revisions["feat"]))
        self.assertEqual(code, 0, stderr)
        second = self.start("feat", expect_exit=True)
        stderr = self.output(second)
        self.assertEqual(second.process.returncode, 0, stderr)

    def test_a_lock_that_cannot_be_taken_gates_without_it_and_says_so(self) -> None:
        # A file where the lock directory belongs: every step of taking the
        # lock fails, and no live gate holds anything. The gate runs, naming
        # no holder, and a second gate of the ref is not refused either.
        common = _git(self.fixture.root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        pathlib.Path(common, "atlas-gate").write_text("not a directory\n", encoding="utf-8")
        # Three attempts of the lock's 0.1 s retry, not its default fifty.
        env = {"lock_attempts": "3"}
        first = self.start("feat", extra_env=env)
        peer = self.running(self.revisions["feat"])
        second = self.start("feat", extra_env=env, expect_exit=True)
        stderr = self.output(second)
        self.assertEqual(second.process.returncode, 0, stderr)
        self.assertIn("could not be taken and no gate holds it; gating without it", stderr)
        self.assertNotIn("is already gating", stderr)
        code, stderr = self.finish(first, peer)
        self.assertEqual(code, 0, stderr)
        self.assertIn("could not be taken and no gate holds it; gating without it", stderr)

    def test_a_gate_whose_hook_was_killed_holds_its_ref_while_its_step_runs(self) -> None:
        first = self.start("feat", expect_exit=True)
        orphan = self.running(self.revisions["feat"])
        (hook_pid,) = self.recorded_pids("pid")
        (step_pid,) = self.recorded_pids("children")
        self.assertNotEqual(step_pid, hook_pid)
        # Only the hook's own process dies; the identity step it started keeps
        # running, so the ref stays held, and the refusal names the step.
        first.process.kill()
        first.process.wait(WAIT)
        second = self.start("feat", expect_exit=True)
        refused = self.output(second)
        self.assertEqual(second.process.returncode, 1, refused)
        self.assertIn(f"pid {step_pid} is already gating refs/heads/feat", refused)
        # The step ends and its socket closes with it; the lock is the dead
        # hook's alone, and the next gate of the ref runs.
        orphan.sendall(b"1")
        self.assertEqual(orphan.recv(1), b"", "the orphaned step sent more than its end")
        third = self.start("feat", expect_exit=True)
        stderr = self.output(third)
        self.assertEqual(third.process.returncode, 0, stderr)


def function_source(name: str) -> str:
    """One shell function of the hook, from its opening line to its closing brace."""
    source = SCRIPT.read_text(encoding="utf-8")
    start = source.index(f"\n{name}() {{") + 1
    return source[start : source.index("\n}\n", start) + 3]


class RecordedStepTestCase(unittest.TestCase):
    """`run_recorded`: the step is the shell's foreground child, and its entry is in the lock."""

    def run_step(self, lock: str, *command: str) -> subprocess.CompletedProcess:
        functions = "".join(
            function_source(name) for name in ("process_start_token", "process_entry", "run_recorded")
        )
        program = f'gate_ref_lock="$1"; shift\n{functions}run_recorded "$@"\n'
        return subprocess.run(
            ["bash", "-c", program, "bash", lock, *command],
            capture_output=True,
            timeout=WAIT,
            check=False,
        )

    def lock(self) -> pathlib.Path:
        temp = tempfile.TemporaryDirectory(prefix="atlas-recorded-")
        self.addCleanup(temp.cleanup)
        return pathlib.Path(temp.name)

    def test_the_step_keeps_the_default_interrupt_disposition(self) -> None:
        # A step started with `&` by a non-interactive shell ignores SIGINT,
        # and the disposition survives exec: Ctrl-C would end the hook and
        # remove the lock while the step went on building.
        lock = self.lock()
        result = self.run_step(lock.as_posix(), "bash", "-c", "trap -p INT; echo done")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("SIGINT", result.stdout.decode())
        self.assertIn("done", result.stdout.decode())

    def test_the_steps_own_pid_and_start_token_are_listed_in_the_lock(self) -> None:
        # The step prints its pid and the token the hook's own function gives
        # for it; the lock lists exactly that entry.
        lock = self.lock()
        token = function_source("process_start_token")
        result = self.run_step(
            lock.as_posix(), "bash", "-c", f'{token}echo "$$"; process_start_token "$$"'
        )
        pid, *start = result.stdout.decode().split()
        self.assertTrue(pid)
        self.assertEqual((lock / "children").read_text(encoding="utf-8").split(), [pid, *start])

    def test_the_steps_status_is_the_commands(self) -> None:
        lock = self.lock()
        self.assertEqual(self.run_step(lock.as_posix(), "bash", "-c", "exit 7").returncode, 7)

    def test_without_a_ref_lock_the_step_runs_unlisted(self) -> None:
        result = self.run_step("", "bash", "-c", "echo ran")
        self.assertEqual((result.returncode, result.stdout.decode().strip()), (0, "ran"))


if __name__ == "__main__":
    unittest.main()
