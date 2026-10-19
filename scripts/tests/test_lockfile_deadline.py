#!/usr/bin/env python3
"""The overlay-escaping cargo runner owns a deadline and a whole process tree.

`subprocess.run(timeout=...)` kills the launcher only. `cargo metadata` starts
rustc and git fetches, and a hung fetch that outlives the launcher still holds
the network and the lock, so the runner launches the command itself, kills the
tree at the deadline, and reports a typed timeout rather than a return code.

The stand-ins are Python scripts: this file has to run on hosts that cannot
create a `cargo` shim next to the real one, and the runner's command is a seam
for exactly that.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
SCRIPT = SCRIPTS / "lockfile.py"
SPEC = importlib.util.spec_from_file_location("atlas_lockfile_deadline", SCRIPT)
lockfile = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lockfile
SPEC.loader.exec_module(lockfile)

NO_DEPENDENCIES = '[package]\nname = "tool"\nversion = "0.1.0"\n'
SERDE = (
    '[[package]]\nname = "serde"\nversion = "1.0.219"\n'
    'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
)

# A launcher that starts a descendant, then sleeps past the deadline. The
# descendant writes the marker only if it survives, which is the assertion: a
# runner that killed the launcher alone leaves the marker behind.
SLOW_SHIM = """\
import pathlib, subprocess, sys, time

marker = pathlib.Path(sys.argv[1])
subprocess.Popen([
    sys.executable, "-c",
    "import pathlib, sys, time; time.sleep(2.0); "
    "pathlib.Path(sys.argv[1]).write_text('alive')",
    str(marker),
])
print("metadata", flush=True)
time.sleep(2.0)
"""

QUICK_SHIM = """\
import sys

print("metadata")
print("note", file=sys.stderr)
"""


class BoundedRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-lockfile-deadline-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.manifest = self.root / "Cargo.toml"
        self.manifest.write_text(NO_DEPENDENCIES, encoding="utf-8", newline="\n")
        self.marker = self.root / "descendant-alive"
        self.original_command = lockfile.CARGO_COMMAND
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        lockfile.CARGO_COMMAND = self.original_command

    def _stand_in(self, source: str, name: str) -> None:
        script = self.root / name
        script.write_text(source, encoding="utf-8", newline="\n")
        lockfile.CARGO_COMMAND = (sys.executable, str(script), str(self.marker))

    def test_a_run_that_outlives_its_deadline_is_a_typed_timeout(self) -> None:
        self._stand_in(SLOW_SHIM, "slow_cargo.py")
        started = time.monotonic()
        with self.assertRaises(lockfile.CargoDeadlineExceeded) as caught:
            lockfile.run_outside_the_overlay(
                ["metadata", "--locked"], manifest=self.manifest, deadline=0.5
            )
        elapsed = time.monotonic() - started

        self.assertEqual(caught.exception.timeout, 0.5)
        self.assertIn("did not finish within 0.5s", caught.exception.stderr or "")
        self.assertIn("metadata", caught.exception.output or "")
        self.assertLess(elapsed, 5.0, "the deadline is not the bound")

        # Past the instant the descendant would have written the marker had it
        # outlived the kill: the whole tree, not just the launcher, was stopped.
        time.sleep(2.2)
        self.assertFalse(self.marker.exists(), "a descendant survived the tree kill")

    def test_a_finished_run_returns_its_output_and_status(self) -> None:
        self._stand_in(QUICK_SHIM, "quick_cargo.py")
        completed = lockfile.run_outside_the_overlay(
            ["metadata"], manifest=self.manifest
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "metadata\n")
        self.assertEqual(completed.stderr, "note\n")

    def test_the_default_deadline_is_bounded(self) -> None:
        self.assertGreater(lockfile.CARGO_DEADLINE_SECONDS, 0)
        self.assertLessEqual(lockfile.CARGO_DEADLINE_SECONDS, 600)


class DeadlineReportingTests(unittest.TestCase):
    """`--check` names an expired deadline apart from a flattened lock."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="atlas-lockfile-report-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "Cargo.toml").write_text(NO_DEPENDENCIES, encoding="utf-8", newline="\n")
        (self.root / "Cargo.lock").write_text(SERDE, encoding="utf-8", newline="\n")
        self.original = (
            lockfile.run_outside_the_overlay,
            lockfile.REPOSITORY,
            lockfile.LOCKFILE,
            lockfile.SCRIPT_CHECKOUT,
        )
        self.addCleanup(self._restore)
        lockfile.REPOSITORY = self.root
        lockfile.LOCKFILE = self.root / "Cargo.lock"
        lockfile.SCRIPT_CHECKOUT = self.root / "elsewhere"

        def expired(*_arguments, **_kwargs):
            raise lockfile.CargoDeadlineExceeded(
                ("cargo", "metadata"), 600, output="", stderr="fetch stalled"
            )

        lockfile.run_outside_the_overlay = expired

    def _restore(self) -> None:
        (
            lockfile.run_outside_the_overlay,
            lockfile.REPOSITORY,
            lockfile.LOCKFILE,
            lockfile.SCRIPT_CHECKOUT,
        ) = self.original

    def test_check_reports_a_stalled_resolution_not_a_flattened_lock(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = lockfile.check()
        message = stderr.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("did not finish within 600s", message)
        self.assertIn("not a flattened lock", message)
        self.assertIn("fetch stalled", message)


class OneRunnerTests(unittest.TestCase):
    def test_the_drift_scan_has_no_cargo_runner_of_its_own(self) -> None:
        source = (SCRIPTS / "atlas-published-drift.py").read_text(encoding="utf-8")
        self.assertNotIn("run_cargo_metadata", source)
        self.assertIn("run_outside_the_overlay", source)


if __name__ == "__main__":
    unittest.main()
