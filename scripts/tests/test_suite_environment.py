"""The suite runs with no inherited repository selection."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REDIRECTS = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"}


class SuiteEnvironmentTests(unittest.TestCase):
    def test_no_repository_redirect_reaches_a_test(self) -> None:
        self.assertEqual(REDIRECTS & os.environ.keys(), set())

    def test_a_caller_s_redirect_is_dropped_before_the_tests_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            caller = Path(directory)
            env = dict(os.environ, GIT_DIR=str(caller / "caller.git"), GIT_WORK_TREE=str(caller),
                       GIT_INDEX_FILE=str(caller / "index"))
            node = (f"{Path(__file__).resolve()}::SuiteEnvironmentTests::"
                    "test_no_repository_redirect_reaches_a_test")
            result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", node],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
