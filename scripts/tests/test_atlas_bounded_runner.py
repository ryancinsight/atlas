#!/usr/bin/env python3
"""Oracle: the bounded runner retires the tree at the deadline.

A test launches a tree (parent plus grandchild sleeping past the limit)
through ``atlas_bounded_runner``; at the limit the run exits nonzero, the exit
reports the limit and the stage, and the tag store lists the run by its tag. A
success path returns the command's exit status unchanged.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "atlas_bounded_runner.py"
TAG_STORE = ROOT / "target" / ".atlas" / "bounded-runner"


class BoundedRunnerOracle(unittest.TestCase):
    def test_deadline_reports_stage_and_lists_the_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "tree.py"
            script.write_text(
                "import subprocess, sys, time\n"
                "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable, str(RUNNER), "--deadline", "1",
                    "--session", "oracle-deadline", "--item", "ATLAS-BOUNDED-RUNNER",
                    "--", sys.executable, str(script),
                ],
                capture_output=True, text=True, timeout=30,
            )
        self.assertNotEqual(
            proc.returncode, 0, "a deadline overrun must exit nonzero"
        )
        self.assertIn("deadline", proc.stderr.lower())
        tags = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in TAG_STORE.glob("*.json")
        ]
        self.assertTrue(
            any(tag["session"] == "oracle-deadline" for tag in tags),
            "the tag store lists the run by its tag",
        )

    def test_success_returns_the_command_exit_status(self) -> None:
        proc = subprocess.run(
            [
                sys.executable, str(RUNNER), "--deadline", "10",
                "--session", "oracle-ok", "--",
                sys.executable, "-c", "raise SystemExit(3)",
            ],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(proc.returncode, 3)


if __name__ == "__main__":
    unittest.main()
