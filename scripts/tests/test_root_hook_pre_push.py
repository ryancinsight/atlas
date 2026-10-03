"""Pin what `.githooks/pre-push` gates and the gate scripts it reads."""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from root_hook_support import (
    FIXTURE_PROCESS_TIMEOUT_SECONDS, GATE_SCRIPTS, PRE_PUSH, demo_member, fixture_environment,
    git_runner, init_superproject, publish_as_origin_default, repo_git_runner, set_gitlink,
)

# The listing block of the hook: the gate script list and its two functions.
GATE_SCRIPT_LISTING = r'(?ms)^tip_scripts=""\n.*?^tip_has_script\(\) \{\n.*?^\}\n'


class RootHookGuardTests(unittest.TestCase):
    def test_gate_script_listing_treats_only_a_missing_object_as_absent(self) -> None:
        """A script path holding a tree still runs its gate, which then fails as before."""
        hook = PRE_PUSH.read_text(encoding="utf-8")
        listing = re.search(GATE_SCRIPT_LISTING, hook)
        self.assertIsNotNone(listing, "the gate script listing is missing from .githooks/pre-push")
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            environment = fixture_environment()
            git = repo_git_runner(repo, environment)

            def commit(message: str, layout: dict[str, str]) -> str:
                for path in git("ls-files").stdout.splitlines():
                    git("rm", "-q", "-r", "-f", "--", path)
                for path, text in layout.items():
                    (repo / path).parent.mkdir(parents=True, exist_ok=True)
                    (repo / path).write_text(text, encoding="utf-8")
                git("add", "--all")
                git("commit", "-q", "--allow-empty", "-m", message)
                return git("rev-parse", "HEAD").stdout.strip()

            init_superproject(environment, repo)
            complete = commit("complete", {path: "print()\n" for path in GATE_SCRIPTS})
            # The secret scan's path is a directory, the budget script is gone.
            shadowed = commit("shadowed", {
                GATE_SCRIPTS[1] + "/inner.py": "print()\n",
                GATE_SCRIPTS[2]: "print()\n",
            })
            driver = (
                'atlas_root="$1"\n' + listing.group(0)
                + 'list_gate_scripts "$2" || exit 7\n'
                + f'for script in {" ".join(GATE_SCRIPTS)}; do\n'
                + '    if tip_has_script "$script"; then echo "present $script"; else echo "absent $script"; fi\n'
                + 'done\n'
            )

            def verdicts(root: Path, tip: str) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["bash", "-c", driver, "listing", str(root), tip],
                    env=environment, capture_output=True, text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            result = verdicts(repo, complete)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [f"present {script}" for script in GATE_SCRIPTS])
            result = verdicts(repo, shadowed)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout.splitlines(),
                [f"absent {GATE_SCRIPTS[0]}", f"present {GATE_SCRIPTS[1]}", f"present {GATE_SCRIPTS[2]}"],
            )
            # A listing that cannot run judges nothing: the hook blocks.
            result = verdicts(repo / "missing", complete)
            self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
            self.assertIn("could not list the gate scripts", result.stderr)

    def test_a_failing_gate_script_listing_blocks_the_push(self) -> None:
        """The hook's own dispatch runs no gate for a tip whose listing fails.

        The dispatch is the hook's `case "$status"` block, extracted whole,
        with the four gates replaced by stubs that log their calls, so the
        listing, the `|| exit 1` after it and the order of the gates are the
        hook's own.
        """
        hook = PRE_PUSH.read_text(encoding="utf-8")
        listing = re.search(GATE_SCRIPT_LISTING, hook)
        self.assertIsNotNone(listing, "the gate script listing is missing from .githooks/pre-push")
        dispatch = re.search(r'(?ms)^case "\$status" in\n.*?^esac\n', hook)
        self.assertIsNotNone(dispatch, 'the `case "$status"` dispatch is missing from .githooks/pre-push')
        gates = ("debt_gate", "budget_gate", "secret_gate", "refspec_gate")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            git = repo_git_runner(repo)
            git("init", "-q", "-b", "main")
            git("commit", "--allow-empty", "-qm", "root")
            tip = git("rev-parse", "HEAD").stdout.strip()
            calls = root / "gates.log"
            driver = root / "dispatch.sh"
            driver.write_bytes((
                'atlas_root="$1"\nstatus=0\npushed_tips=("$2")\npushed_bases=("$2")\n'
                'gate_base_for() { echo "$2"; }\n'
                + "".join(f'{gate}() {{ echo "{gate}" >> "{calls.as_posix()}"; }}\n' for gate in gates)
                + listing.group(0) + dispatch.group(0)
            ).encode("utf-8"))

            def dispatch_push(atlas_root: Path) -> subprocess.CompletedProcess:
                return subprocess.run(
                    ["bash", str(driver), str(atlas_root), tip],
                    env=fixture_environment(), capture_output=True, text=True,
                    timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
                )

            # Control: a listing that runs lets the four gates run in order.
            result = dispatch_push(repo)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(calls.read_text(encoding="utf-8").splitlines(), list(gates))
            calls.unlink()

            result = dispatch_push(root / "missing")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("could not list the gate scripts", result.stderr)
            self.assertFalse(calls.exists(), "a gate ran for a tip whose gate scripts could not be listed")

    def test_pre_push_runs_the_pin_advance_debt_gate(self) -> None:
        text = PRE_PUSH.read_text(encoding="utf-8")
        self.assertIn("debt_gate()", text)
        # Both gates judge each pushed tip, never HEAD (a peer's branch in a
        # shared tree), so the guarded form carries the tip argument.
        self.assertIn('debt_gate "$tip" || exit 1', text)
        self.assertIn('budget_gate "$tip" || exit 1', text)
        self.assertIn('secret_gate "$tip" || exit 1', text)

    def _debt_gate_stack(self, temporary: str) -> tuple[Path, dict[str, str], str, str]:
        """An atlas repository whose checkout and origin disagree on the checker.

        origin/main's checker records `origin` and exits with the status in
        `CHECKER_STATUS`; the checkout's copy records `checkout` and fails.
        Returns the repository, its environment, the base and the pushed tip,
        which advances the one member's gitlink.
        """
        repo = Path(temporary) / "atlas"
        environment = fixture_environment()
        git = git_runner(environment)
        commits = demo_member(environment, repo / "repos" / "demo", "first", "second")

        git(repo, "init", "-q", "-b", "main")
        checker = repo / "scripts" / "atlas-conformance.py"
        checker.parent.mkdir()
        checker.write_text(
            "import os, pathlib, sys\n"
            "pathlib.Path(os.environ['CHECKER_LOG']).write_text('origin ' + ' '.join(sys.argv[1:]))\n"
            "sys.exit(int(os.environ['CHECKER_STATUS']))\n",
            encoding="utf-8",
        )
        git(repo, "add", "scripts")
        set_gitlink(environment, repo, commits[0])
        git(repo, "commit", "-qm", "Record demo")
        base = git(repo, "rev-parse", "HEAD").stdout.strip()
        publish_as_origin_default(environment, repo, base)
        set_gitlink(environment, repo, commits[1])
        git(repo, "commit", "-qm", "Advance demo")
        tip = git(repo, "rev-parse", "HEAD").stdout.strip()
        # The shared checkout's copy: a peer's uncommitted checker change.
        checker.write_text(
            "import os, pathlib, sys\n"
            "pathlib.Path(os.environ['CHECKER_LOG']).write_text('checkout')\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        return repo, environment, base, tip

    def _run_debt_gate(
        self, repo: Path, environment: dict[str, str], base: str, tip: str, status: int,
    ) -> tuple[subprocess.CompletedProcess, str]:
        hook = PRE_PUSH.read_text(encoding="utf-8")
        function = re.search(r"(?ms)^debt_gate\(\) \{\n.*?^\}\n", hook)
        self.assertIsNotNone(function, "debt_gate() is missing from .githooks/pre-push")
        probe = re.search(r"(?ms)^python_bin=\"\"\n.*?^resolve_python\(\) \{\n.*?^\}\n", hook)
        self.assertIsNotNone(probe, "resolve_python() is missing from .githooks/pre-push")
        log = repo.parent / "checker.log"
        script = (
            probe.group(0)
            + function.group(0)
            + 'atlas_root="$1"; member_root="$1"; gate_base="$2"\n'
            + 'debt_gate "$3"\n'
        )
        run_environment = dict(
            environment, PYTHON=sys.executable, CHECKER_LOG=str(log),
            CHECKER_STATUS=str(status),
        )
        result = subprocess.run(
            ["bash", "-c", script, "debt_gate", repo.as_posix(), base, tip],
            env=run_environment, capture_output=True, text=True, encoding="utf-8",
            timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
        )
        return result, log.read_text(encoding="utf-8") if log.is_file() else ""

    def test_debt_gate_runs_origins_checker_not_the_checkouts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, base, tip = self._debt_gate_stack(temporary)

            passed, log = self._run_debt_gate(repo, environment, base, tip, 0)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertTrue(log.startswith("origin check --repo demo"), log)

            failed, log = self._run_debt_gate(repo, environment, base, tip, 1)
            self.assertEqual(failed.returncode, 1, failed.stderr)
            self.assertTrue(log.startswith("origin "), log)
            self.assertIn("advancing demo raises a debt class", failed.stderr)
            git_dir = repo / ".git"
            self.assertEqual(list(git_dir.glob("atlas-debt-checker.*")), [],
                             "the extracted checker outlives the run")

    def test_debt_gate_skips_a_pin_the_default_branch_records(self) -> None:
        # A branch merging main in carries main's own pin advance; main's
        # ratchet measured it, so the gate does not measure it again against
        # the branch's older baseline.
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, base, tip = self._debt_gate_stack(temporary)
            git_runner(environment)(repo, "update-ref", "refs/remotes/origin/main", tip)

            result, log = self._run_debt_gate(repo, environment, base, tip, 1)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log, "", "a pin the default branch records was measured again")

    def test_debt_gate_without_an_origin_default_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo, environment, base, tip = self._debt_gate_stack(temporary)
            git = git_runner(environment)
            for ref in ("refs/remotes/origin/HEAD", "refs/remotes/origin/main"):
                git(repo, "update-ref", "--no-deref", "-d", ref)

            result, log = self._run_debt_gate(repo, environment, base, tip, 0)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(log, "", "a checker ran with no origin default")
            self.assertIn("origin names no default branch", result.stderr)


if __name__ == "__main__":
    unittest.main()
