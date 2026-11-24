"""Oracle: the bounded runner retires the whole tree at its deadline.

At the limit the exit is 124 and names the limit and the stage, no descendant
survives, and the end file records the outcome. A completing command keeps its
status and output. A run the runner cannot start, tag or clean up exits 125 with
its stage named, and a tree that may survive gets no end file. A tag that a
reader holds open or that cannot be closed leaves the command's status, a taken
tag name is never overwritten, and any session string tags a run inside the store.
``overdue`` lists runs with no end file past their deadline, skips an unreadable
file or one without finite numeric ``started`` and ``deadline`` with a warning
that never hides another run, and reads each tag file once.
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
from process_tree import ProcessTreeCleanupError, ProcessTreeTimeout
from process_tree_support import EXPIRY_HOLD_SECONDS, HANG_GUARD_SECONDS, is_running

SCRIPTS = Path(__file__).resolve().parents[1]
LIMIT = str(HANG_GUARD_SECONDS)
RUN = ("run", "--deadline", LIMIT, "--session", "s", "--", "x")
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
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "atlas_bounded_runner.py"), *arguments], capture_output=True,
        text=True, timeout=HANG_GUARD_SECONDS, env={**os.environ, "CARGO_TARGET_DIR": str(target)},
    )


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
        tags.append({**tag, **json.loads(end.read_text(encoding="utf-8"))} if end.exists() else tag)
    return tags


def exits(status: int) -> mock.Mock:
    return mock.Mock(return_value=subprocess.CompletedProcess(["x"], status))


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
        self.addCleanup(lambda: is_running(grandchild) and os.kill(grandchild, signal.SIGTERM))
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
        result = run_runner(target, "run", "--deadline", LIMIT, "--session", "ok", "--", *command)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout.strip(), "payload")
        [tag] = read_tags(target)
        self.assertEqual((tag["outcome"], tag["returncode"]), ("exit", 3))

    def test_the_runners_own_exit_2_prints_no_stage_and_writes_no_tag(self) -> None:
        target = scratch(self) / "target"
        refused = [("run", f"--deadline={deadline}", "--session", "s", "--", "x")
                   for deadline in ("0", "-1", "nan", "inf", "-inf", "abc")]
        refused.append(("run", "--deadline", LIMIT, "--session", "s"))
        for arguments in refused:
            with self.subTest(arguments=arguments):
                result = run_runner(target, *arguments)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("stage:", result.stderr)
        self.assertFalse(target.exists(), "no tag store is created")

    def test_any_session_string_tags_the_run_inside_the_store(self) -> None:
        for session in ("claude:cf2e0cbc/1072", "a\\b", "..", "../../escape", "has space"):
            with self.subTest(session=session):
                target = scratch(self) / "target"
                arguments = ("run", "--deadline", LIMIT, "--session", session, "--", "x")
                self.assertEqual(run_in_process(target, *arguments, run=exits(5)), 5)
                written = [path for path in target.rglob("*") if path.is_file()]
                self.assertEqual({path.parent for path in written}, {store_of(target)})
                for path in written:
                    self.assertRegex(path.name, r"^\d+-\d+(\.end)?\.json$")
                self.assertEqual([tag["session"] for tag in read_tags(target)], [session])


class FaultTests(unittest.TestCase):
    def test_a_command_that_cannot_start_exits_125_with_its_end_file(self) -> None:
        target = scratch(self) / "target"
        result = run_runner(target, "run", "--deadline", LIMIT, "--session", "s", "--", "no-such-xyz")
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertIn("stage: launch", result.stderr)
        [tag] = read_tags(target)
        self.assertEqual(tag["outcome"], "launch")

    def test_an_end_file_is_written_unless_a_tree_may_survive(self) -> None:
        survivor, interrupted = RuntimeError("boom"), KeyboardInterrupt()
        for error in (survivor, interrupted):
            error.add_note("process-tree cleanup failed: pid 7")
        cases = (  # error, status (None: re-raised), stderr text, end-file outcome (None: no end file)
            (ProcessTreeCleanupError("pid 7"), 125, "stage: cleanup", None),
            (ProcessTreeTimeout(["x"], 1.0, None, None, "pid 7"), 125, "stage: cleanup", None),
            (survivor, 125, "process-tree cleanup failed: pid 7", None),
            (RuntimeError("boom"), 125, "stage: launch", "launch"),
            (KeyboardInterrupt(), None, "", "interrupted"),
            (interrupted, None, "", None),
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
        result = run_runner(root / "file", "run", "--deadline", LIMIT, "--session", "s", "--", *command)
        self.assertEqual(result.returncode, 125, result.stderr)
        self.assertIn("stage: store", result.stderr)
        self.assertFalse(marker.exists(), "the command did not run")

    def test_a_tag_that_cannot_be_closed_leaves_the_exit_status(self) -> None:
        target = scratch(self) / "target"

        def run(*arguments: object, **options: object) -> subprocess.CompletedProcess[str]:
            [opened] = store_of(target).glob("*.json")
            opened.with_suffix(".end.json").write_text("{}", encoding="utf-8")
            return subprocess.CompletedProcess(["x"], 9)

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(run_in_process(target, *RUN, run=mock.Mock(side_effect=run)), 9)
        self.assertIn("stage: store: could not close", stderr.getvalue())

    def test_a_reader_holding_a_tag_open_leaves_the_exit_status_and_the_tag(self) -> None:
        target = scratch(self) / "target"
        held = []

        def run(*arguments: object, **options: object) -> subprocess.CompletedProcess[str]:
            [opened] = store_of(target).glob("*.json")
            held.append((opened, opened.read_text(encoding="utf-8")))
            self.addCleanup(opened.open(encoding="utf-8").close)
            return subprocess.CompletedProcess(["x"], 9)

        self.assertEqual(run_in_process(target, *RUN, run=mock.Mock(side_effect=run)), 9)
        [(opened, before)] = held
        self.assertEqual(opened.read_text(encoding="utf-8"), before, "closing never rewrites a tag")
        [tag] = read_tags(target)
        self.assertEqual((tag["outcome"], tag["returncode"]), ("exit", 9))

    def test_a_taken_tag_name_is_never_overwritten(self) -> None:
        target = scratch(self) / "target"
        taken = store_of(target) / f"100-{os.getpid()}.json"
        taken.parent.mkdir(parents=True)
        taken.write_text("{}", encoding="utf-8")
        with mock.patch.object(atlas_bounded_runner.time, "time_ns", return_value=100):
            self.assertEqual(run_in_process(target, *RUN, run=exits(0)), 0)
        self.assertEqual(taken.read_text(encoding="utf-8"), "{}")
        names = sorted(path.name for path in taken.parent.iterdir())
        self.assertEqual(names, [taken.name, f"101-{os.getpid()}.end.json", f"101-{os.getpid()}.json"])


class OverdueTests(unittest.TestCase):
    def test_a_foreign_file_is_skipped_and_never_hides_a_late_run(self) -> None:
        store = scratch(self)
        files = {
            "late.json": '{"id": "late", "started": 1.0, "deadline": 1.0}',
            "huge.json": '{"id": "huge", "started": 1' + "0" * 400 + ', "deadline": 1.0}',
            "deep.json": "[" * 200000 + "]" * 200000,
            "bool.json": '{"id": "bool", "started": true, "deadline": 1}',
            "nan.json": '{"id": "nan", "started": 1.0, "deadline": NaN}',
            "infinite.json": '{"id": "infinite", "started": 1.0, "deadline": Infinity}',
            "text.json": '{"id": "text", "started": "1", "deadline": 1}',
            "broken.json": "{", "list.json": "[]", "foreign.json": '{"id": "x"}',
            "7-7.json.part": "{", "8-8.end.json": "{",
        }
        for name, text in files.items():
            (store / name).write_text(text, encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as warnings:
            found = atlas_bounded_runner.overdue_tags(store, now=100.0)
        self.assertEqual([tag["id"] for tag in found], ["late"])
        for name in files.keys() - {"late.json", "7-7.json.part", "8-8.end.json"}:
            self.assertIn(f"skipped {name}", warnings.getvalue())
        for leftover in ("7-7", "8-8"):
            self.assertNotIn(leftover, warnings.getvalue())

    def test_each_tag_file_is_read_once_and_end_files_never(self) -> None:
        store = scratch(self)
        for name in ("1-1.json", "1-1.end.json", "2-2.json"):
            (store / name).write_text('{"id": "t", "started": 1.0, "deadline": 1.0}', encoding="utf-8")
        read, original = [], Path.read_text

        def recording(path: Path, *arguments: object, **options: object) -> str:
            read.append(path.name)
            return original(path, *arguments, **options)

        with mock.patch.object(Path, "read_text", recording):
            found = atlas_bounded_runner.overdue_tags(store, now=100.0)
        self.assertEqual(read, ["1-1.json", "2-2.json"])
        self.assertEqual(len(found), 1)

    def test_the_command_prints_each_open_late_tag_beside_a_foreign_file(self) -> None:
        target = scratch(self) / "target"
        store = store_of(target)
        store.mkdir(parents=True)
        now = time.time()
        tags = {
            "1-1": {"id": "late", "started": now - 100.0, "deadline": 10.0},
            "2-2": {"id": "in-time", "started": now, "deadline": 3600.0},
            "3-3": {"id": "closed", "started": now - 100.0, "deadline": 10.0},
        }
        for stem, tag in tags.items():
            (store / f"{stem}.json").write_text(json.dumps(tag), encoding="utf-8")
        (store / "3-3.end.json").write_text('{"id": "closed", "outcome": "exit"}', encoding="utf-8")
        (store / "4-4.json").write_text('{"started": 1' + "0" * 400 + ', "deadline": 1.0}', encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as listing, contextlib.redirect_stderr(io.StringIO()):
            status = run_in_process(target, "overdue")
        self.assertEqual(status, 0)
        self.assertEqual([json.loads(line)["id"] for line in listing.getvalue().splitlines()], ["late"])


class TagStoreTests(unittest.TestCase):
    def test_the_store_falls_back_to_the_shared_target_when_unconfigured(self) -> None:
        shared = scratch(self) / "shared"
        lookup = mock.patch.object(
            atlas_bounded_runner.atlas_target_dir, "shared_target_for", return_value=shared
        )
        with mock.patch.dict(os.environ), lookup as shared_target_for:
            os.environ.pop("CARGO_TARGET_DIR", None)
            store = atlas_bounded_runner.tag_store()
        self.assertEqual(store, store_of(shared))
        shared_target_for.assert_called_once_with(SCRIPTS.parent)

    def test_overdue_reports_an_unresolvable_store_as_a_runner_fault(self) -> None:
        lookup = mock.patch.object(
            atlas_bounded_runner.atlas_target_dir, "shared_target_for", side_effect=RuntimeError("no checkout")
        )
        with mock.patch.dict(os.environ), lookup, contextlib.redirect_stderr(io.StringIO()) as stderr:
            os.environ.pop("CARGO_TARGET_DIR", None)
            status = atlas_bounded_runner.main(["overdue"])
        self.assertEqual(status, 125)
        self.assertIn("stage: store", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
