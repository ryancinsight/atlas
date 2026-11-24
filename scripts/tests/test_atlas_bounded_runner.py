"""Oracle: the bounded runner retires the whole tree at its deadline.

At the limit the exit is 124 and names the limit and the stage, the grandchild
process no longer exists, and the end file records the deadline outcome. A
completing command keeps its status and output. A run the runner cannot start
or cannot clean up, or whose tag it cannot create, exits 125 with its stage named, and only a run whose tree
cannot survive gets an end file, and any session string tags a run inside the
store.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import atlas_bounded_runner
from process_tree import ProcessTreeCleanupError, ProcessTreeTimeout
from process_tree_support import EXPIRY_HOLD_SECONDS, HANG_GUARD_SECONDS, is_running

SCRIPTS = Path(__file__).resolve().parents[1]
RUNNER = SCRIPTS / "atlas_bounded_runner.py"
RUN = ("run", "--deadline", str(HANG_GUARD_SECONDS), "--session", "s", "--", "x")
EXITS_WITH_FIVE = (sys.executable, "-c", "raise SystemExit(5)")

# Runs the runner's entry point with its deadline clock started at the
# grandchild's readiness report, so no machine speed changes the outcome.
HELPER = (
    "import os, socket, sys\n"
    f"sys.path[:0] = [{str(SCRIPTS)!r}, {str(Path(__file__).resolve().parent)!r}]\n"
    "import atlas_bounded_runner\n"
    "from process_tree_support import HANG_GUARD_SECONDS, budget_from_readiness\n"
    "listener = socket.create_server(('127.0.0.1', 0))\n"
    "listener.settimeout(HANG_GUARD_SECONDS)\n"
    "os.environ['ATLAS_TEST_READY_PORT'] = str(listener.getsockname()[1])\n"
    "with listener, budget_from_readiness(listener):\n"
    "    raise SystemExit(atlas_bounded_runner.main(sys.argv[1:]))\n"
)
GRANDCHILD = (
    "import os, pathlib, socket, sys, threading\n"
    "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n"
    "socket.create_connection(('127.0.0.1', int(os.environ['ATLAS_TEST_READY_PORT']))).close()\n"
    "threading.Event().wait()\n"
)
PARENT = (
    "import subprocess, sys, threading\n"
    "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]])\n"
    "threading.Event().wait()\n"
)


def scratch(test: unittest.TestCase) -> Path:
    directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    test.addCleanup(directory.cleanup)
    return Path(directory.name)


def run_runner(target: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "CARGO_TARGET_DIR": str(target)}
    return subprocess.run([sys.executable, str(RUNNER), *arguments], capture_output=True, text=True,
                          timeout=HANG_GUARD_SECONDS, env=environment)


def run_in_process(target: Path, *arguments: str, run: mock.Mock | None = None) -> int:
    with contextlib.ExitStack() as patches:
        patches.enter_context(mock.patch.dict(os.environ, {"CARGO_TARGET_DIR": str(target)}))
        if run is not None:
            patches.enter_context(mock.patch.object(atlas_bounded_runner.process_tree, "run", run))
        return atlas_bounded_runner.main(list(arguments))


def store_of(target: Path) -> Path:
    return target / ".atlas" / "bounded-runner"


def read_tags(target: Path) -> list[dict[str, object]]:
    """Each run's tag with its end file, when it has one, merged in."""
    tags = []
    for path in sorted(store_of(target).glob("*[0-9].json")):
        tag = json.loads(path.read_text(encoding="utf-8"))
        end = path.with_suffix(".end.json")
        if end.exists():
            tag.update(json.loads(end.read_text(encoding="utf-8")))
        tags.append(tag)
    return tags


class RunTests(unittest.TestCase):
    def test_deadline_retires_the_tree_and_closes_the_tag(self) -> None:
        root = scratch(self)
        pid_file = root / "grandchild.pid"
        with (root / "stdout").open("wb") as stdout, (root / "stderr").open("wb") as stderr:
            # Files, not pipes: a surviving descendant holds no pipe the test waits on.
            result = subprocess.run(
                [sys.executable, "-c", HELPER, "run", "--deadline", str(EXPIRY_HOLD_SECONDS),
                 "--session", "oracle:deadline", "--item", "ITEM-1",
                 "--", sys.executable, "-c", PARENT, GRANDCHILD, str(pid_file)],
                stdout=stdout, stderr=stderr, timeout=HANG_GUARD_SECONDS, check=False,
                env={**os.environ, "CARGO_TARGET_DIR": str(root / "target")},
            )
        grandchild = int(pid_file.read_text(encoding="utf-8"))

        def reap() -> None:
            if is_running(grandchild):
                os.kill(grandchild, signal.SIGTERM)

        self.addCleanup(reap)
        stderr_text = (root / "stderr").read_text(encoding="utf-8", errors="replace")
        self.assertEqual(result.returncode, 124, stderr_text)
        self.assertIn(f"stage: deadline: {EXPIRY_HOLD_SECONDS} s exceeded", stderr_text)
        self.assertFalse(is_running(grandchild), "no descendant survives the deadline")
        [tag] = read_tags(root / "target")
        self.assertEqual((tag["session"], tag["item"]), ("oracle:deadline", "ITEM-1"))
        self.assertEqual((tag["deadline"], tag["outcome"]), (EXPIRY_HOLD_SECONDS, "deadline"))

    def test_exit_status_and_output_pass_through(self) -> None:
        target = scratch(self) / "target"
        command = (sys.executable, "-c", "print('payload'); raise SystemExit(3)")
        result = run_runner(target, "run", "--deadline", "30", "--session", "oracle:ok", "--", *command)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout.strip(), "payload")
        [tag] = read_tags(target)
        self.assertEqual((tag["outcome"], tag["returncode"]), ("exit", 3))

    def test_missing_command_is_refused(self) -> None:
        result = run_runner(scratch(self) / "target", "run", "--deadline", "1", "--session", "s")
        self.assertEqual(result.returncode, 2)
        self.assertIn("a command is required", result.stderr)

    def test_any_session_string_tags_the_run_inside_the_store(self) -> None:
        sessions = ("claude:cf2e0cbc/1072", "a\\b", "..", "../../escape", "has space", "x:y/../z")
        for session in sessions:
            with self.subTest(session=session):
                target = scratch(self) / "target"
                arguments = ("run", "--deadline", "30", "--session", session, "--", *EXITS_WITH_FIVE)
                self.assertEqual(run_in_process(target, *arguments), 5)
                written = [path for path in target.rglob("*") if path.is_file()]
                self.assertEqual({path.parent for path in written}, {store_of(target)})
                for path in written:
                    self.assertRegex(path.name, r"^\d+-\d+(\.end)?\.json$")
                [tag] = read_tags(target)
                self.assertEqual(tag["session"], session)

    def test_an_invalid_deadline_is_refused_before_any_tag_is_written(self) -> None:
        for deadline in ("0", "-1", "nan", "inf", "-inf", "abc"):
            with self.subTest(deadline=deadline):
                target = scratch(self) / "target"
                arguments = ("run", f"--deadline={deadline}", "--session", "s", "--", "x")
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    with self.assertRaises(SystemExit) as refused:
                        run_in_process(target, *arguments)
                self.assertEqual(refused.exception.code, 2)
                self.assertIn("--deadline", stderr.getvalue())
                self.assertFalse(target.exists(), "no tag store is created")


class FaultTests(unittest.TestCase):
    def test_a_command_that_cannot_start_exits_125_with_its_end_file(self) -> None:
        target = scratch(self) / "target"
        result = run_runner(target, "run", "--deadline", "30", "--session", "s", "--", "no-such-command-xyz")
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertIn("stage: launch", result.stderr)
        [tag] = read_tags(target)
        self.assertEqual(tag["outcome"], "launch")

    def test_an_end_file_is_written_unless_a_tree_may_survive(self) -> None:
        survivor = RuntimeError("boom")
        survivor.add_note("process-tree cleanup failed: pid 7")
        cases = (  # error, status (None: re-raised), stderr text, end-file outcome (None: no end file)
            (ProcessTreeCleanupError("pid 7"), 125, "stage: cleanup", None),
            (ProcessTreeTimeout(["x"], 1.0, None, None, "pid 7"), 125, "stage: cleanup", None),
            (survivor, 125, "process-tree cleanup failed: pid 7", None),
            (RuntimeError("boom"), 125, "stage: launch", "launch"),
            (KeyboardInterrupt(), None, "", "interrupted"),
        )
        for error, status, text, outcome in cases:
            with self.subTest(error=repr(error)):
                target = scratch(self) / "target"
                run = mock.Mock(side_effect=error)
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    if status is None:
                        with self.assertRaises(KeyboardInterrupt):
                            run_in_process(target, *RUN, run=run)
                    else:
                        self.assertEqual(run_in_process(target, *RUN, run=run), status)
                self.assertIn(text, stderr.getvalue())
                [tag] = read_tags(target)
                self.assertEqual(tag.get("outcome"), outcome)

    def test_a_store_that_cannot_be_created_stops_the_run_before_the_command(self) -> None:
        root = scratch(self)
        (root / "file").write_text("x", encoding="utf-8")
        marker = root / "ran"
        command = (sys.executable, "-c", f"open({str(marker)!r}, 'w')")
        result = run_runner(root / "file", "run", "--deadline", "30", "--session", "s", "--", *command)
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertIn("stage: store", result.stderr)
        self.assertFalse(marker.exists(), "the command did not run")


if __name__ == "__main__":
    unittest.main()
