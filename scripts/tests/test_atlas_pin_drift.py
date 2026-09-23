#!/usr/bin/env python3
"""Tests for the gitlink pin-drift guard.

Every case builds throwaway repositories in a tempdir -- a "published" member
repository, a meta repository recording a gitlink for it, and a member clone --
and drives the guard through its `main`. What the guard measures is a relation
between three repositories, so a mocked `git` would assert the mock rather than
the behaviour; the local paths stand in for remote URLs, which is exactly what
`ls-remote` reads.

The cases that matter most are the ones that must not pass: a pin ahead of the
default branch, and an unreachable remote. Either one silently reported as
clean would defeat the guard, so both assert the exit status *and* the member
named in the report.
"""

from __future__ import annotations

import contextlib
import importlib.util
import inspect
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-pin-drift.py"
SPEC = importlib.util.spec_from_file_location("atlas_pin_drift", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)

IDENT = ("-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false")
MEMBER = "demo"


class PinDriftTestCase(unittest.TestCase):
    """A published member, a meta repository pinning it, and a member clone."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-pin-drift-")
        self.root = Path(self._tmp.name)
        self.environment = os.environ.copy()
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            self.environment.pop(key, None)
        # A private global config, so the developer's own aliases and
        # `init.defaultBranch` cannot change what these repositories do.
        self.environment["GIT_CONFIG_GLOBAL"] = str(self.root / "gitconfig")
        self.environment["GIT_CONFIG_NOSYSTEM"] = "1"
        (self.root / "gitconfig").write_text("", encoding="utf-8")
        self._env = mock.patch.dict(os.environ, self.environment, clear=True)
        self._env.start()
        self.addCleanup(self._env.stop)
        self.addCleanup(self._tmp.cleanup)

        self.waivers = self.root / "waivers.json"
        self.meta = self.root / "meta"
        self.published = self.root / "published"

    # -- fixture construction -------------------------------------------------

    def git(self, repo: Path, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(repo), *IDENT, *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=self.environment,
        )
        self.assertEqual(proc.returncode, 0, f"git {args}: {proc.stderr}")
        return proc.stdout.strip()

    def publish(self, commits: int = 2, branch: str = "main") -> None:
        """Create the member repository the guard will read as a remote."""
        self.published.mkdir()
        self.git(self.published, "init", "-b", branch, "--quiet")
        for index in range(commits):
            self.commit_to(self.published, index)

    def commit_to(self, repo: Path, index: int) -> str:
        (repo / "file.txt").write_text(f"revision {index}\n", encoding="utf-8")
        self.git(repo, "add", "file.txt")
        self.git(repo, "commit", "--quiet", "-m", f"commit {index}")
        return self.git(repo, "rev-parse", "HEAD")

    def clone_member(self) -> Path:
        clone = self.meta / "repos" / MEMBER
        clone.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            ["git", "clone", "--quiet", self.published.as_posix(), str(clone)],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=self.environment,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return clone

    def build_meta(self, url: str | None = None) -> None:
        """Create the meta repository whose `.gitmodules` registers the member."""
        self.meta.mkdir(exist_ok=True)
        self.git(self.meta, "init", "-b", "main", "--quiet")
        (self.meta / ".gitmodules").write_text(
            f'[submodule "repos/{MEMBER}"]\n'
            f"\tpath = repos/{MEMBER}\n"
            f"\turl = {self.published.as_posix() if url is None else url}\n",
            encoding="utf-8",
        )
        self.git(self.meta, "add", ".gitmodules")
        self.git(self.meta, "commit", "--quiet", "-m", "register member")

    def pin(self, sha: str) -> None:
        """Record `sha` as the member's gitlink in a new meta commit."""
        self.git(
            self.meta, "update-index", "--add", "--cacheinfo", f"160000,{sha},repos/{MEMBER}"
        )
        self.git(self.meta, "commit", "--quiet", "-m", f"pin {sha[:10]}")

    def write_waivers(self, entries: list[dict]) -> None:
        import json

        self.waivers.write_text(json.dumps({"waivers": entries}), encoding="utf-8")

    # -- driving the guard ----------------------------------------------------

    def run_guard(self, *extra: str) -> tuple[int, str]:
        argv = [
            "--repo", str(self.meta),
            "--waivers", str(self.waivers),
            "--timeout", "120",
            *extra,
        ]
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = guard.main(argv)
        return status, stream.getvalue()

    # -- cases ----------------------------------------------------------------

    def test_pin_at_the_default_tip_is_clean(self) -> None:
        self.publish(commits=2)
        tip = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        self.pin(tip)
        status, output = self.run_guard()
        self.assertEqual(status, 0, output)
        # The tip, not the `ref: refs/heads/...` line `ls-remote --symref`
        # answers with first: reading that as the tip printed `@ ref: refs/`
        # for every member and would have hidden a wrong tip behind a right count.
        self.assertIn(f"ok: {MEMBER} -- 0 behind main @ {tip[:10]}", output)
        self.assertIn("atlas-pin-drift: OK", output)

    def test_one_commit_behind_is_within_the_sweep_allowance(self) -> None:
        self.publish(commits=2)
        pinned = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        self.commit_to(self.published, 2)
        self.pin(pinned)
        status, output = self.run_guard()
        self.assertEqual(status, 0, output)
        self.assertIn(f"ok: {MEMBER} -- 1 behind main", output)
        self.assertNotIn("PIN DRIFT", output)

    def test_behind_past_the_threshold_fails_and_names_the_member(self) -> None:
        self.publish(commits=2)
        pinned = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        for index in range(2, 5):
            self.commit_to(self.published, index)
        self.pin(pinned)
        status, output = self.run_guard()
        self.assertEqual(status, 1, output)
        self.assertIn(f"PIN DRIFT: {MEMBER} -- 3 commit(s) behind main", output)
        self.assertIn("atlas-pin-drift: FAIL - 1 member(s) drifted or off-default", output)

    def test_threshold_is_configurable(self) -> None:
        self.publish(commits=2)
        pinned = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        for index in range(2, 5):
            self.commit_to(self.published, index)
        self.pin(pinned)
        status, output = self.run_guard("--max-behind", "3")
        self.assertEqual(status, 0, output)
        self.assertIn(f"ok: {MEMBER} -- 3 behind main", output)

    def test_pin_ahead_of_the_default_is_reported_as_off_default(self) -> None:
        """A pin naming a commit the member never published is its own failure."""
        self.publish(commits=2)
        self.build_meta()
        clone = self.clone_member()
        unpublished = self.commit_to(clone, 99)
        self.pin(unpublished)
        status, output = self.run_guard()
        self.assertEqual(status, 1, output)
        self.assertIn(f"OFF-DEFAULT: {MEMBER}", output)
        self.assertIn("1 commit(s) of the pin are absent from the default branch", output)
        self.assertNotIn("PIN DRIFT", output)

    def test_waiver_does_not_excuse_an_off_default_pin(self) -> None:
        self.publish(commits=2)
        self.build_meta()
        clone = self.clone_member()
        unpublished = self.commit_to(clone, 99)
        self.pin(unpublished)
        self.write_waivers(
            [{"member": MEMBER, "reason": "held deliberately", "reopen": "never"}]
        )
        status, output = self.run_guard()
        self.assertEqual(status, 1, output)
        self.assertIn(f"OFF-DEFAULT: {MEMBER}", output)
        self.assertNotIn("waived:", output)

    def test_waiver_explains_drift(self) -> None:
        self.publish(commits=2)
        pinned = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        for index in range(2, 6):
            self.commit_to(self.published, index)
        self.pin(pinned)
        self.write_waivers(
            [
                {
                    "member": MEMBER,
                    "reason": "ATLAS-EXAMPLE-1: advancing re-imports a ratchet regression",
                    "reopen": "member PR #7 merges",
                }
            ]
        )
        status, output = self.run_guard()
        self.assertEqual(status, 0, output)
        self.assertIn(f"waived: {MEMBER} -- 4 behind main", output)
        self.assertIn("re-open: member PR #7 merges", output)
        self.assertIn("1 waived", output)

    def test_waiver_missing_the_reopen_trigger_fails(self) -> None:
        self.publish(commits=2)
        tip = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        self.pin(tip)
        self.write_waivers([{"member": MEMBER, "reason": "because"}])
        status, output = self.run_guard()
        self.assertEqual(status, 1, output)
        self.assertIn("WAIVER PROBLEM", output)
        self.assertIn("`member`, `reason`, `reopen`", output)
        self.assertIn("1 malformed waiver(s)", output)

    def test_waiver_with_a_blank_reason_fails(self) -> None:
        self.publish(commits=2)
        tip = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        self.pin(tip)
        self.write_waivers([{"member": MEMBER, "reason": "   ", "reopen": "a trigger"}])
        status, output = self.run_guard()
        self.assertEqual(status, 1, output)
        self.assertIn("WAIVER PROBLEM", output)

    def test_unreachable_remote_reports_unavailable_not_a_pass(self) -> None:
        """The offline case: no measurement, so no clean verdict."""
        self.publish(commits=2)
        pinned = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta(url=(self.root / "absent").as_posix())
        self.clone_member()
        self.pin(pinned)
        status, output = self.run_guard()
        self.assertEqual(status, 2, output)
        self.assertIn(f"UNAVAILABLE: {MEMBER}", output)
        self.assertIn("Not measured, so not clean", output)
        self.assertNotIn("atlas-pin-drift: OK", output)

    def test_drift_outranks_unavailability_in_the_exit_status(self) -> None:
        """A definite defect must not be masked by an unmeasured sibling."""
        self.publish(commits=2)
        pinned = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        for index in range(2, 6):
            self.commit_to(self.published, index)
        self.pin(pinned)
        absent = self.root / "absent"
        (self.meta / ".gitmodules").write_text(
            f'[submodule "repos/{MEMBER}"]\n'
            f"\tpath = repos/{MEMBER}\n"
            f"\turl = {self.published.as_posix()}\n"
            '[submodule "repos/ghost"]\n'
            "\tpath = repos/ghost\n"
            f"\turl = {absent.as_posix()}\n",
            encoding="utf-8",
        )
        self.git(self.meta, "add", ".gitmodules")
        self.git(
            self.meta, "update-index", "--add", "--cacheinfo", f"160000,{pinned},repos/ghost"
        )
        self.git(self.meta, "commit", "--quiet", "-m", "register a second member")
        status, output = self.run_guard()
        self.assertEqual(status, 1, output)
        self.assertIn(f"PIN DRIFT: {MEMBER}", output)
        self.assertIn("UNAVAILABLE: ghost", output)

    def test_waiver_for_an_unscanned_member_is_noted(self) -> None:
        self.publish(commits=2)
        tip = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        self.pin(tip)
        self.write_waivers(
            [{"member": "absent-member", "reason": "stale entry", "reopen": "a trigger"}]
        )
        status, output = self.run_guard()
        self.assertEqual(status, 0, output)
        self.assertIn("note: waiver for absent-member explains nothing in this scan", output)

    def test_non_main_default_branch_is_read_from_the_remote(self) -> None:
        """hephaestus publishes `master`; the default may not be assumed."""
        self.publish(commits=2, branch="master")
        pinned = self.git(self.published, "rev-parse", "HEAD")
        self.build_meta()
        self.clone_member()
        for index in range(2, 5):
            self.commit_to(self.published, index)
        self.pin(pinned)
        status, output = self.run_guard()
        self.assertEqual(status, 1, output)
        self.assertIn(f"PIN DRIFT: {MEMBER} -- 3 commit(s) behind master", output)


class PinDriftWaiverFileTestCase(unittest.TestCase):
    """The committed waiver file is itself part of the contract."""

    def test_committed_waivers_parse_and_declare_every_required_field(self) -> None:
        path = Path(guard.WAIVERS)
        waivers, problems = guard.load_waivers(path)
        self.assertEqual(problems, [], f"committed waiver file is malformed: {problems}")
        for member, entry in waivers.items():
            for field in guard.WAIVER_FIELDS:
                self.assertTrue(entry.get(field, "").strip(), f"{member} lacks {field}")


class FetchRefspecTestCase(unittest.TestCase):
    """The refspec `distance` passes to `git fetch` never targets a
    remote-tracking ref.

    ATLAS-ORIGIN-REF-CLOBBER-2026-09-21: a sweep force-fetching five
    different members' `main` -- each measured against a non-atlas (member)
    URL -- landed every one of them, in turn, in Atlas's own shared
    `refs/remotes/origin/main`. `distance()` measures against `url`, which
    is always a member's URL, never atlas's own, so every refspec this tool
    ever constructs is exercised here.
    """

    def test_every_refspec_targets_the_scratch_prefix(self) -> None:
        self.assertTrue(guard.FETCH_REFSPECS, "no refspecs to check")
        for spec in guard.FETCH_REFSPECS:
            self.assertTrue(spec.startswith("+"), f"refspec {spec!r} must force-update")
            _, _, dest = spec.partition(":")
            self.assertTrue(
                dest.startswith(guard.SCRATCH_REF_PREFIX),
                f"refspec {spec!r} destination {dest!r} must live under "
                f"{guard.SCRATCH_REF_PREFIX!r}",
            )

    def test_fetch_refspec_never_targets_remote_tracking_namespace(self) -> None:
        for branch in ("main", "master", "refs/heads/main", "release/2026.09"):
            spec = guard.fetch_refspec(branch)
            _, _, dest = spec.partition(":")
            self.assertFalse(
                dest.startswith("refs/remotes/"),
                f"fetch_refspec({branch!r}) = {spec!r} targets a remote-tracking ref",
            )

    def test_distance_reads_the_scratch_ref_not_fetch_head(self) -> None:
        """`distance()` must query `SCRATCH_HEAD_REF`, not `FETCH_HEAD` --
        `FETCH_HEAD` is itself a shared, ambient ref this process does not
        own exclusively, which is the same class of scratch-space misuse
        this item closes."""
        source = inspect.getsource(guard.distance)
        self.assertIn("SCRATCH_HEAD_REF", source)
        self.assertNotIn("FETCH_HEAD", source)


if __name__ == "__main__":
    unittest.main()
