"""Oracle: the bounded runner retires the whole tree at its deadline.

At the limit the exit is 124 and names the limit and the stage, the grandchild
process no longer exists, and the tag is closed with the deadline outcome. A
completing command keeps its status and output; a run that cannot start exits 125
with its tag closed; any session string tags a run inside the store; ``overdue``
lists open tags past their deadline and no closed one.
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
import time
import unittest
from pathlib import Path
from unittest import mock

import atlas_bounded_runner
from process_tree import ProcessTreeCleanupError
from process_tree_support import EXPIRY_HOLD_SECONDS, HANG_GUARD_SECONDS, is_running

SCRIPTS = Path(__file__).resolve().parents[1]
RUNNER = SCRIPTS / "atlas_bounded_runner.py"

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
EXITS_WITH_FIVE = [sys.executable, "-c", "raise SystemExit(5)"]


def scratch(test: unittest.TestCase) -> Path:
    directory = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    test.addCleanup(directory.cleanup)
    return Path(directory.name)


def run_runner(target: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "CARGO_TARGET_DIR": str(target)}
    return subprocess.run([sys.executable, str(RUNNER), *arguments], capture_output=True, text=True,
                          timeout=HANG_GUARD_SECONDS, env=environment)


def run_in_process(target: Path, *arguments: str) -> int:
    with mock.patch.dict(os.environ, {"CARGO_TARGET_DIR": str(target)}):
        return atlas_bounded_runner.main(list(arguments))


def store_of(target: Path) -> Path:
    return target / ".atlas" / "bounded-runner"


def read_tags(target: Path) -> list[dict[str, object]]:
    paths = sorted(store_of(target).glob("*.json"))
    return [json.loads(path.read_text(encoding="utf-8")) for path in paths]


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
        self.assertIn("ended", tag)

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
                [written] = [path for path in target.rglob("*") if path.is_file()]
                self.assertEqual(written.parent, store_of(target))
                self.assertRegex(written.name, r"^\d+-\d+\.json$")
                [tag] = read_tags(target)
                self.assertEqual(tag["session"], session)

    def assert_closed(self, target: Path, outcome: str) -> None:
        [tag] = read_tags(target)
        self.assertEqual(tag["outcome"], outcome)
        self.assertEqual(run_runner(target, "overdue").stdout, "", "no run is left open")

    def test_a_command_that_cannot_start_exits_125_with_its_tag_closed(self) -> None:
        target = scratch(self) / "target"
        result = run_runner(target, "run", "--deadline", "1", "--session", "s:1", "--", "no-such-command-xyz")
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertIn("stage: launch", result.stderr)
        self.assert_closed(target, "launch")

    def test_a_cleanup_failure_exits_125_with_its_tag_closed(self) -> None:
        target = scratch(self) / "target"
        failure = ProcessTreeCleanupError("a descendant survived")
        with mock.patch.object(atlas_bounded_runner.process_tree, "run", side_effect=failure):
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                status = run_in_process(target, "run", "--deadline", "1", "--session", "s:2", "--", "x")
        self.assertEqual(status, 125)
        self.assertIn("stage: cleanup", stderr.getvalue())
        self.assert_closed(target, "cleanup")

    def test_an_invalid_deadline_is_refused_before_any_tag_is_written(self) -> None:
        for deadline in ("0", "-1", "nan", "inf", "-inf", "abc"):
            with self.subTest(deadline=deadline):
                target = scratch(self) / "target"
                arguments = ("run", f"--deadline={deadline}", "--session", "s:3", "--", "x")
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    with self.assertRaises(SystemExit) as refused:
                        run_in_process(target, *arguments)
                self.assertEqual(refused.exception.code, 2)
                self.assertIn("--deadline", stderr.getvalue())
                self.assertFalse(target.exists(), "no tag store is created")


class TagStoreTests(unittest.TestCase):
    def test_unreadable_files_are_skipped_with_a_warning(self) -> None:
        store = scratch(self)
        (store / "late.json").write_text('{"id": "late", "started": 1.0, "deadline": 1.0}', encoding="utf-8")
        skipped = {"broken.json": "{", "list.json": "[]", "foreign.json": '{"id": "x"}'}
        for name, text in skipped.items():
            (store / name).write_text(text, encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as warnings:
            found = atlas_bounded_runner.overdue_tags(store, now=100.0)
        self.assertEqual([tag["id"] for tag in found], ["late"])
        for name in skipped:
            self.assertIn(f"skipped {name}", warnings.getvalue())

    def test_the_command_prints_each_open_late_tag(self) -> None:
        target = scratch(self) / "target"
        now = time.time()
        for tag in (
            {"id": "late", "started": now - 100.0, "deadline": 10.0},
            {"id": "in-time", "started": now, "deadline": 3600.0},
            {"id": "closed", "started": now - 100.0, "deadline": 10.0, "ended": now - 95.0},
        ):
            atlas_bounded_runner._write_tag(store_of(target), tag)
        with contextlib.redirect_stdout(io.StringIO()) as listing:
            status = run_in_process(target, "overdue")
        self.assertEqual(status, 0)
        self.assertEqual([json.loads(line)["id"] for line in listing.getvalue().splitlines()], ["late"])

    def test_the_store_falls_back_to_the_shared_target_when_unconfigured(self) -> None:
        shared = scratch(self) / "shared"
        lookup = mock.patch.object(
            atlas_bounded_runner.atlas_target_dir, "shared_target_for", return_value=shared
        )
        with mock.patch.dict(os.environ), lookup as shared_target_for:
            del os.environ["CARGO_TARGET_DIR"]
            store = atlas_bounded_runner.tag_store()
        self.assertEqual(store, store_of(shared))
        shared_target_for.assert_called_once_with(SCRIPTS.parent)

    def test_a_tag_is_replaced_whole_and_leaves_no_partial_file(self) -> None:
        store = scratch(self)
        observed = []
        replace = os.replace

        def observing_replace(partial: str, final: str) -> None:
            replaced = Path(final).exists() and json.loads(Path(final).read_text(encoding="utf-8"))
            observed.append((json.loads(Path(partial).read_text(encoding="utf-8")), replaced))
            replace(partial, final)

        with mock.patch.object(atlas_bounded_runner.os, "replace", observing_replace):
            atlas_bounded_runner._write_tag(store, {"id": "t", "n": 1})
            atlas_bounded_runner._write_tag(store, {"id": "t", "n": 2})
        first, second = {"id": "t", "n": 1}, {"id": "t", "n": 2}
        self.assertEqual(observed, [(first, False), (second, first)])
        self.assertEqual([path.name for path in store.iterdir()], ["t.json"])


if __name__ == "__main__":
    unittest.main()
