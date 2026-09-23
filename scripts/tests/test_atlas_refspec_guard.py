#!/usr/bin/env python3
"""Tests for the refspec guard (ATLAS-ORIGIN-REF-CLOBBER-2026-09-21).

The guard's contract is the acceptance oracle of its item:

1. a committed sweep tool writes its fetched refs into `refs/scratch/`
   exclusively -- never into the remote-tracking namespace;
2. a refspec mapping a non-atlas branch onto a `refs/remotes/` destination
   fails the policy;
3. scanning this repository's committed tooling reports zero violations, the
   machine-readable form of "the incident literal stays out of tooling".

The clobber refspecs a case plants are built at runtime from fragments, so
the committed test source never carries a `src:refs/...` token that would
trip the guard's own scan of `scripts/tests/` as tooling (criterion 3).
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-refspec-guard.py"
SPEC = importlib.util.spec_from_file_location("atlas_refspec_guard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

ROOT = Path(__file__).resolve().parents[2]


class RefSpecPolicyTestCase(unittest.TestCase):
    """The destination rule is the discriminator (acceptance clause 2)."""

    def test_non_atlas_branch_mapped_onto_a_tracking_ref_fails(self) -> None:
        for branch in ("main", "master", "release/2.0", "refs/heads/main"):
            reason = guard.refspec_outcome(branch, "refs/remotes/origin/main")
            self.assertIsNotNone(reason, f"{branch} -> refs/remotes/origin/main")
            self.assertIn("remote-tracking", reason)
            self.assertIn("refs/scratch", reason)

    def test_any_refs_remotes_destination_from_a_branch_fails(self) -> None:
        for dst in ("refs/remotes/origin/main", "refs/remotes/member/master"):
            self.assertIsNotNone(
                guard.refspec_outcome("main", dst), f"main -> {dst}"
            )

    def test_own_origin_wildcard_mirror_is_sanctioned(self) -> None:
        self.assertIsNone(
            guard.refspec_outcome("refs/heads/*", "refs/remotes/origin/*")
        )

    def test_scratch_destination_is_sanctioned(self) -> None:
        reason = guard.refspec_outcome("main", "refs/scratch/member/2026-09-21/main")
        self.assertIsNone(reason)

    def test_tag_and_local_head_destinations_are_not_tracked_writes(self) -> None:
        self.assertIsNone(guard.refspec_outcome("refs/tags/*", "refs/tags/*"))
        self.assertIsNone(guard.refspec_outcome("refs/heads/main", "refs/heads/main"))


class RefSpecScanTestCase(unittest.TestCase):
    """The committed-tree scan, in both its passing and failing directions."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-refspec-guard-")
        self.tool = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_check(self, root: Path) -> tuple[int, str]:
        from contextlib import redirect_stdout
        import io

        stream = io.StringIO()
        with redirect_stdout(stream):
            status = guard.main(["--root", str(root)])
        return status, stream.getvalue()

    def test_planted_sweep_tool_with_a_tracking_refwrite_fails(self) -> None:
        script_dir = self.tool / "scripts"
        script_dir.mkdir()
        branch, namespace, tracked = "main", "refs/" + "remotes/origin/", "main"
        # The clobber shape, assembled at runtime so the committed source
        # holds no `src:refs/remotes/` token for the guard to trip itself on.
        refspec = f"+{branch}:{namespace}{tracked}"
        (script_dir / "sweep.py").write_text(
            f"def sync(url):\n    git(fetch, url, {refspec!r})\n",
            encoding="utf-8",
        )
        status, output = self.run_check(self.tool)
        self.assertEqual(status, 1, output)
        self.assertIn(f"sweep.py:2 `{refspec}`", output)
        self.assertIn("remote-tracking", output)

    def test_scratch_only_sweep_tool_passes(self) -> None:
        script_dir = self.tool / "scripts"
        script_dir.mkdir()
        scratch = "refs/" + "scratch/member/main"
        (script_dir / "sweep.py").write_text(
            f"def sync(url):\n    git(fetch, url, '+main:{scratch}')\n",
            encoding="utf-8",
        )
        status, output = self.run_check(self.tool)
        self.assertEqual(status, 0, output)

    def test_sanctioned_self_mirror_and_tag_mirror_pass(self) -> None:
        wf = self.tool / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "conformance.yml").write_text(
            "run: git fetch --prune --no-tags origin "
            "'+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*'\n",
            encoding="utf-8",
        )
        status, output = self.run_check(self.tool)
        self.assertEqual(status, 0, output)

    def test_docs_and_boards_are_not_tooling(self) -> None:
        # The incident literal lives in the item file (evidence), which is
        # prose, not tooling; the scan must not read it as a violation.
        backlog = self.tool / "backlog"
        backlog.mkdir()
        (backlog / "atlas-origin-ref-clobber-2026-09-21.md").write_text(
            "refspec: " + "+main:" + "refs/" + "remotes/origin/main\n",
            encoding="utf-8",
        )
        status, output = self.run_check(self.tool)
        self.assertEqual(status, 0, output)

    def test_committed_tooling_scan_is_zero(self) -> None:
        """Criterion 3: this repository's own tooling carries no violation."""
        status, output = self.run_check(ROOT)
        self.assertEqual(status, 0, output)
        self.assertIn("no committed tool writes", output)


if __name__ == "__main__":
    unittest.main()