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
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

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

    def commit_tooling(self, files: dict[str, str]) -> None:
        def git(*arguments: str) -> None:
            subprocess.run(
                ["git", "-C", str(self.tool), "-c", "user.name=Test",
                 "-c", "user.email=test@example.invalid", *arguments],
                check=True, capture_output=True, timeout=30,
            )

        git("init", "-q")
        for relpath, text in files.items():
            path = self.tool / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
        git("add", "--all")
        git("commit", "-qm", "tooling")

    def run_revision(self, rev: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = guard.main(["--root", str(self.tool), "--rev", rev])
        return status, stdout.getvalue(), stderr.getvalue()

    def test_a_revision_is_judged_by_its_committed_content(self) -> None:
        # The hook judges the commit being pushed: a violation committed and
        # then cleaned only in the working tree still fails, and the scan
        # finds it under a path Git would quote (a space and a non-ASCII name).
        refspec = "+main:" + "refs/" + "remotes/origin/main"
        self.commit_tooling({
            "scripts/ä sweep.py": f"git(fetch, url, {refspec!r})\n",
            "scripts/clean.py": "print('fine')\n",
            "docs/notes.py": f"{refspec!r}\n",
        })
        (self.tool / "scripts" / "ä sweep.py").write_text("print('cleaned')\n", encoding="utf-8")
        self.assertEqual(self.run_check(self.tool)[0], 0)
        status, output, _ = self.run_revision("HEAD")
        self.assertEqual(status, 1, output)
        self.assertIn(f"scripts/ä sweep.py:1 `{refspec}`", output)
        self.assertNotIn("docs/notes.py", output)

    def test_a_revision_is_read_in_two_git_processes(self) -> None:
        # One listing and one batch read, however many tooling files the
        # tree holds, and every file is read.
        files = {f"scripts/tool{index:02}.py": f"print({index})\n" for index in range(12)}
        files["scripts/zz.py"] = "git(fetch, url, '+main:" + "refs/" + "remotes/origin/main')\n"
        self.commit_tooling(files)
        real_run = subprocess.run
        commands: list[list[str]] = []

        def counting_run(command, *arguments, **options):
            commands.append(command)
            return real_run(command, *arguments, **options)

        with patch.object(guard.subprocess, "run", side_effect=counting_run):
            status, output, _ = self.run_revision("HEAD")
        self.assertEqual([command[3] for command in commands], ["ls-tree", "cat-file"])
        self.assertEqual(status, 1, output)
        self.assertIn("scripts/zz.py:1", output)
        self.assertEqual(len(guard.committed_tooling(self.tool, "HEAD")), 13)

    def test_an_unreadable_revision_fails_instead_of_passing(self) -> None:
        # A revision the guard cannot list judges nothing, so it must not
        # report the clean verdict.
        self.commit_tooling({"scripts/clean.py": "print('fine')\n"})
        status, output, errors = self.run_revision("no-such-revision")
        self.assertEqual(status, 2, output)
        self.assertNotIn("no committed tool writes", output)
        self.assertIn("refspec-guard: ERROR", errors)

    def test_a_tree_naming_an_absent_blob_fails_instead_of_passing(self) -> None:
        # `cat-file --batch` answers `<id> missing` for a blob the object
        # store lacks (a partial clone, a damaged store). The guard judged
        # nothing for that file, so it reports the unreadable revision.
        self.commit_tooling({"scripts/clean.py": "print('fine')\n"})

        def git(*arguments: str, stdin: str | None = None) -> str:
            # Bytes in, so Windows text mode cannot turn a record's newline
            # into the carriage return that would end its file name.
            return subprocess.run(
                ["git", "-C", str(self.tool), "-c", "user.name=Test",
                 "-c", "user.email=test@example.invalid", *arguments],
                input=None if stdin is None else stdin.encode("utf-8"),
                check=True, capture_output=True, timeout=30,
            ).stdout.decode("utf-8").strip()

        absent = git("hash-object", "--stdin", stdin="never stored\n")
        scripts = git("mktree", "--missing", stdin=f"100644 blob {absent}\tgone.py\n")
        tree = git("mktree", stdin=f"040000 tree {scripts}\tscripts\n")
        broken = git("commit-tree", tree, "-m", "absent blob")
        status, output, errors = self.run_revision(broken)
        self.assertEqual(status, 2, output)
        self.assertNotIn("no committed tool writes", output)
        self.assertIn("refspec-guard: ERROR -- git cat-file --batch answered", errors)
        self.assertIn("scripts/gone.py", errors)

    def test_committed_tooling_scan_is_zero(self) -> None:
        """Criterion 3: this repository's own tooling carries no violation."""
        status, output = self.run_check(ROOT)
        self.assertEqual(status, 0, output)
        self.assertIn("no committed tool writes", output)


if __name__ == "__main__":
    unittest.main()