"""Oracle: the bounded runner retires the whole tree at its deadline.

A parent and a grandchild that outlive the limit are launched through the
runner. At the limit the exit is 124 and names the limit and the stage, no
descendant keeps running, and the run's tag is closed with the deadline
outcome. A completing command keeps its exit status and output, a run whose
tag is never closed is listed once past its deadline, and a tag closed in time
is not.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import atlas_bounded_runner

RUNNER = Path(__file__).resolve().parents[1] / "atlas_bounded_runner.py"

# The grandchild must be beating before the deadline fires. On POSIX the chain is
# four interpreter starts (runner, supervisor, parent, grandchild); at the 0.118 s
# idle start and the 15x CI-to-host factor recorded beside
# process_tree_support.HANG_GUARD_SECONDS that is 4 x 0.118 x 15 = 7.1 s, rounded up
# to 8 s. The Windows chain of five starts measured 2.108 s loaded is below it.
DEADLINE_SECONDS = 8.0

# Hang guard for the runner process itself: the deadline plus the tree cleanup
# budget, rounded up.
RUNNER_GUARD_SECONDS = 60

HEARTBEAT_PERIOD_SECONDS = 0.05
# A live grandchild beats once per period; four periods bound a scheduling
# stall, so a beat inside this window after the runner exited is a survivor.
QUIET_WINDOW_SECONDS = 4 * HEARTBEAT_PERIOD_SECONDS

GRANDCHILD = (
    "import sys, time\n"
    "while True:\n"
    "    with open(sys.argv[1], 'a') as beats:\n"
    "        beats.write('.')\n"
    f"    time.sleep({HEARTBEAT_PERIOD_SECONDS})\n"
)
PARENT = (
    "import subprocess, sys, threading\n"
    "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]])\n"
    "threading.Event().wait()\n"
)


def run_runner(target: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "CARGO_TARGET_DIR": str(target)}
    return subprocess.run(
        [sys.executable, str(RUNNER), *arguments],
        capture_output=True,
        text=True,
        timeout=RUNNER_GUARD_SECONDS,
        env=environment,
    )


def read_tags(target: Path) -> list[dict[str, object]]:
    store = target / ".atlas" / "bounded-runner"
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(store.glob("*.json"))]


class DeadlineTests(unittest.TestCase):
    def test_deadline_retires_the_tree_and_closes_the_tag(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            beats = root / "beats"
            result = run_runner(
                root / "target", "run", "--deadline", str(DEADLINE_SECONDS),
                "--session", "oracle:deadline", "--item", "ATLAS-BOUNDED-RUNNER",
                "--", sys.executable, "-c", PARENT, GRANDCHILD, str(beats),
            )
            self.assertEqual(result.returncode, atlas_bounded_runner.EXIT_DEADLINE, result.stderr)
            self.assertIn("stage: deadline", result.stderr)
            self.assertIn(f"{DEADLINE_SECONDS} s", result.stderr)
            beaten = beats.stat().st_size
            self.assertGreater(beaten, 0, "the grandchild ran before the deadline")
            time.sleep(QUIET_WINDOW_SECONDS)
            self.assertEqual(beats.stat().st_size, beaten, "no descendant survives the deadline")
            [tag] = read_tags(root / "target")
            self.assertEqual(tag["session"], "oracle:deadline")
            self.assertEqual(tag["item"], "ATLAS-BOUNDED-RUNNER")
            self.assertEqual(tag["deadline"], DEADLINE_SECONDS)
            self.assertEqual(tag["outcome"], "deadline")
            self.assertIn("ended", tag)


class CompletionTests(unittest.TestCase):
    def test_exit_status_and_output_pass_through(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch) / "target"
            result = run_runner(
                target, "run", "--deadline", str(DEADLINE_SECONDS),
                "--session", "oracle:ok", "--",
                sys.executable, "-c", "print('payload'); raise SystemExit(3)",
            )
            self.assertEqual(result.returncode, 3)
            self.assertEqual(result.stdout.strip(), "payload")
            [tag] = read_tags(target)
            self.assertEqual((tag["outcome"], tag["returncode"]), ("exit", 3))

    def test_missing_command_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            result = run_runner(
                Path(scratch) / "target", "run", "--deadline", "1", "--session", "oracle:none",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("a command is required", result.stderr)


class OverdueTests(unittest.TestCase):
    def test_lists_only_open_tags_past_their_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            store = Path(scratch)
            started = 1_000.0
            tags = {
                "open-late": {"started": started, "deadline": 10.0},
                "open-in-time": {"started": started, "deadline": 100.0},
                "closed-late": {"started": started, "deadline": 10.0, "ended": started + 5.0},
            }
            for name, fields in tags.items():
                (store / f"{name}.json").write_text(
                    json.dumps({"id": name, **fields}), encoding="utf-8"
                )
            found = atlas_bounded_runner.overdue_tags(store, now=started + 50.0)
            self.assertEqual([tag["id"] for tag in found], ["open-late"])


if __name__ == "__main__":
    unittest.main()
