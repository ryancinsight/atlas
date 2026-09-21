#!/usr/bin/env python3
"""Tests for the stale-side guard.

Every case builds a throwaway repository in a tempdir and drives the guard
through its `main`. That is the only honest way to test it: what the guard
measures is a property of a working tree *together with* its history, so a
mocked `git` would assert the mock rather than the behaviour.

The cases that matter most are the negatives. A guard that fires on real work
is worse than no guard, so several cases pin that a genuine edit, an untracked
file, a deletion, a gitlink, and a CRLF checkout are all left alone.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import atlas_git_process as git_process  # noqa: E402
import atlas_stale_side_git as guard_git  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-stale-side-guard.py"
SPEC = importlib.util.spec_from_file_location("atlas_stale_side_guard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)

IDENT = ("-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false")


class StaleSideGuardTestCase(unittest.TestCase):
    """A temp repository, its waiver file, and a helper to run the guard."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.waivers = root / "waivers.json"
        self.environment = os.environ.copy()
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            self.environment.pop(key, None)
        # A private global config, so the developer's own `core.autocrlf` and
        # aliases cannot change what these repositories do. Same shape as
        # `fixtures/overlay_resolution.py`.
        self.environment["GIT_CONFIG_GLOBAL"] = str(root / "gitconfig")
        self.environment["GIT_CONFIG_NOSYSTEM"] = "1"
        (root / "gitconfig").write_text("", encoding="utf-8")
        self.git("init", "-q", "-b", "main")
        self.git("config", "core.autocrlf", "false")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- harness -----------------------------------------------------------

    def git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *IDENT, *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=self.environment,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def exhaustive_revisions(self, path: str) -> dict[str, guard_git.Revision]:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                *IDENT,
                "log",
                "--full-history",
                "-m",
                "-z",
                "--format=COMMIT:%H",
                "--raw",
                "--no-abbrev",
                "--no-renames",
                "HEAD",
                "--",
                path,
            ],
            capture_output=True,
            env=self.environment,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        width = 40
        revisions: dict[str, list] = {}
        commit = None
        records = iter(record for record in proc.stdout.split(b"\0") if record)
        for record in records:
            normalized = record.lstrip(b"\n")
            if normalized.startswith(b"COMMIT:"):
                commit = normalized.removeprefix(b"COMMIT:").decode("ascii")
                continue
            self.assertTrue(normalized.startswith(b":"), normalized)
            fields = normalized.split()
            label = os.fsdecode(next(records))
            self.assertEqual(label, path)
            self.assertIsNotNone(commit)
            self.assertGreaterEqual(len(fields), 4)
            blob = fields[3].decode("ascii")
            if blob == "0" * width:
                continue
            slot = revisions.get(blob)
            if slot is None:
                revisions[blob] = [commit, {commit}]
            else:
                slot[1].add(commit)
        return {
            blob: guard_git.Revision(slot[0], len(slot[1]))
            for blob, slot in revisions.items()
        }

    def write(self, name: str, text: str) -> None:
        """Write bytes verbatim -- `newline=""` keeps CRLF tests honest."""
        (self.repo / name).write_text(text, encoding="utf-8", newline="")

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def waive(self, *entries: dict) -> None:
        self.waivers.write_text(
            json.dumps({"waivers": list(entries)}), encoding="utf-8"
        )

    def check(self, *extra: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = guard.main(
                ["check", "--repo", str(self.repo), "--waivers", str(self.waivers), *extra]
            )
        return code, out.getvalue()

    def status(self, *extra: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = guard.main(
                ["status", "--repo", str(self.repo), "--waivers", str(self.waivers), *extra]
            )
        return code, out.getvalue()

    def basis(self, *extra: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = guard.main(
                ["basis", "--repo", str(self.repo), "--waivers", str(self.waivers), *extra]
            )
        return code, out.getvalue()

    def one_commit_then_a_revert(self) -> str:
        """`f.txt` reverts to its first revision; return that revision."""
        self.write("f.txt", "old\n")
        first = self.commit("one")
        self.write("f.txt", "new\n")
        self.commit("two")
        self.write("f.txt", "old\n")
        return first

    # -- the defect --------------------------------------------------------

    def test_flags_content_equal_to_an_older_revision(self) -> None:
        first = self.one_commit_then_a_revert()
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("STALE SIDE: f.txt", out)
        # The report has to name the revision the content came from: that is
        # the whole actionable content of the finding.
        self.assertIn(first[:10], out)
        self.assertIn("one", out)
        self.assertIn("1 revision(s)", out)

    def test_reports_the_newest_matching_revision(self) -> None:
        self.write("f.txt", "a\n")
        self.commit("one")
        self.write("f.txt", "b\n")
        self.commit("two")
        self.write("f.txt", "a\n")
        third = self.commit("three")
        self.write("f.txt", "c\n")
        self.commit("four")
        self.write("f.txt", "a\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        # Two revisions carry this content; the newest is the one to name.
        self.assertIn(third[:10], out)
        self.assertIn("2 revision(s)", out)

    def test_merge_parent_revision_remains_the_newest_match(self) -> None:
        self.write("f.txt", "base\n")
        self.commit("base")
        self.git("checkout", "-q", "-b", "side")
        self.write("f.txt", "side\n")
        self.commit("side")
        self.git("checkout", "-q", "main")
        self.write("f.txt", "kept\n")
        self.commit("main change")
        self.git("merge", "-q", "--no-ff", "-s", "ours", "side", "-m", "merge")
        merge = self.git("rev-parse", "HEAD").strip()
        self.write("f.txt", "new\n")
        self.commit("after merge")
        exhaustive = self.exhaustive_revisions("f.txt")
        targeted = guard_git.historical_blobs(
            self.repo, {"f.txt": set(exhaustive)}, False
        )["f.txt"]
        self.assertEqual(targeted, exhaustive)
        self.write("f.txt", "kept\n")

        code, out = self.check()

        self.assertEqual(code, 1, out)
        self.assertIn(merge[:10], out)
        self.assertIn("2 revision(s)", out)

    def test_deletion_is_not_counted_as_a_revision_carrying_content(self) -> None:
        self.write("f.txt", "old\n")
        first = self.commit("one")
        (self.repo / "f.txt").unlink()
        self.commit("delete")
        self.write("f.txt", "new\n")
        self.commit("replace")
        self.write("f.txt", "old\n")

        code, out = self.check()

        self.assertEqual(code, 1, out)
        self.assertIn(first[:10], out)
        self.assertIn("1 revision(s)", out)

    def test_mode_only_change_remains_a_post_image_revision(self) -> None:
        self.write("f.txt", "old\n")
        self.commit("one")
        old_blob = self.git("rev-parse", "HEAD:f.txt").strip()
        self.git("update-index", "--chmod=+x", "f.txt")
        self.git("commit", "-q", "-m", "executable")
        mode_change = self.git("rev-parse", "HEAD").strip()
        self.write("f.txt", "new\n")
        self.commit("replace")
        exhaustive = self.exhaustive_revisions("f.txt")
        targeted = guard_git.historical_blobs(
            self.repo, {"f.txt": {old_blob}}, False
        )["f.txt"]
        self.assertEqual(targeted[old_blob], exhaustive[old_blob])
        self.write("f.txt", "old\n")

        code, out = self.check()

        self.assertEqual(code, 1, out)
        self.assertIn(mode_change[:10], out)
        self.assertIn("2 revision(s)", out)

    def test_history_query_tracks_multiple_candidate_blobs(self) -> None:
        self.write("f.txt", "first\n")
        self.write("g.txt", "alpha\n")
        first = self.commit("one")
        first_f = self.git("rev-parse", f"{first}:f.txt").strip()
        first_g = self.git("rev-parse", f"{first}:g.txt").strip()
        self.write("f.txt", "second\n")
        self.write("g.txt", "beta\n")
        second = self.commit("two")
        second_f = self.git("rev-parse", f"{second}:f.txt").strip()

        history = guard_git.historical_blobs(
            self.repo,
            {"f.txt": {first_f, second_f}, "g.txt": {first_g}},
            False,
        )

        self.assertEqual(history["f.txt"][first_f], guard_git.Revision(first, 1))
        self.assertEqual(history["f.txt"][second_f], guard_git.Revision(second, 1))
        self.assertEqual(history["g.txt"][first_g], guard_git.Revision(first, 1))

    def test_candidate_queries_do_not_cross_contaminate_revisions(self) -> None:
        contents = ["candidate one\n", "candidate two\n"]
        self.write("f.txt", contents[0])
        first_blob = self.git("hash-object", "f.txt").strip()
        self.write("f.txt", contents[1])
        second_blob = self.git("hash-object", "f.txt").strip()
        early_blob, later_blob = sorted((first_blob, second_blob))
        early_content = contents[0] if early_blob == first_blob else contents[1]
        later_content = contents[1] if later_blob == second_blob else contents[0]

        self.write("f.txt", early_content)
        early = self.commit("early")
        self.write("f.txt", later_content)
        self.commit("transition")
        self.write("f.txt", "other\n")
        self.commit("away")
        self.write("f.txt", later_content)
        latest = self.commit("latest")

        history = guard_git.historical_blobs(
            self.repo, {"f.txt": {early_blob, later_blob}}, False
        )["f.txt"]

        self.assertEqual(history[early_blob], guard_git.Revision(early, 1))
        self.assertEqual(history[later_blob], guard_git.Revision(latest, 2))

    def test_staged_mode_reads_the_index_not_the_worktree(self) -> None:
        self.one_commit_then_a_revert()
        self.git("add", "f.txt")
        code, out = self.check("--staged")
        self.assertEqual(code, 1)
        self.assertIn("[index]", out)

        # A working copy restored to HEAD while the index still holds the old
        # revision is exactly what `--staged` exists for: the plain scan reads
        # the file on disk, which is no longer a change against HEAD, so it
        # reports nothing and only the staged view sees the revert.
        self.write("f.txt", "new\n")
        self.assertEqual(self.git("diff", "HEAD", "--name-only").strip(), "")
        self.assertEqual(self.check()[0], 0)
        self.assertEqual(self.check("--staged")[0], 1)

    def test_detects_a_binary_revert(self) -> None:
        (self.repo / "b.bin").write_bytes(bytes(range(256)) * 4)
        self.commit("one")
        (self.repo / "b.bin").write_bytes(b"\x00\x01\x02")
        self.commit("two")
        (self.repo / "b.bin").write_bytes(bytes(range(256)) * 4)
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("STALE SIDE: b.bin", out)

    def test_unicode_path_with_spaces_is_matched_losslessly(self) -> None:
        path = "café archive.txt"
        self.write(path, "old\n")
        self.commit("one")
        self.write(path, "new\n")
        self.commit("two")
        self.write(path, "old\n")
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn(f"STALE SIDE: {path}", out)
        self.git("add", "--", path)
        code, out = self.check("--staged")
        self.assertEqual(code, 1, out)
        self.assertIn(f"STALE SIDE: {path}", out)

    # -- negatives: real work must not be reported -------------------------

    def test_accepts_a_genuinely_new_edit(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.write("f.txt", "two\n")
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_ignores_a_clean_worktree(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.assertEqual(self.check()[0], 0)

    def test_ignores_an_untracked_file(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        # Byte-identical to a revision of another path, and still not a stale
        # side: the guard claims nothing about untracked files.
        (self.repo / "f.txt").write_text("one\n", encoding="utf-8")
        self.write("g.txt", "one\n")
        self.assertEqual(self.check()[0], 0)

    def test_ignores_a_deleted_file(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        (self.repo / "f.txt").unlink()
        self.assertEqual(self.check()[0], 0)

    def test_gitlink_entries_have_no_content_to_compare(self) -> None:
        self.write("f.txt", "one\n")
        head = self.commit("one")
        self.git("update-index", "--add", "--cacheinfo", f"160000,{head},repos/demo")
        code, out = self.check("--staged")
        self.assertEqual(code, 0, out)
        self.assertNotIn("STALE SIDE", out)

    def test_a_crlf_checkout_is_not_a_stale_side(self) -> None:
        (self.repo / ".gitattributes").write_text("* text eol=lf\n", encoding="utf-8")
        self.write("f.txt", "one\n")
        self.commit("one")
        (self.repo / "f.txt").write_bytes(b"one\r\n")
        # Git itself calls this unchanged, because the clean filter normalizes
        # it; the guard compares through that same filter rather than by bytes.
        self.assertEqual(self.git("diff", "--name-only").strip(), "")
        code, out = self.check()
        self.assertEqual(code, 0, out)

    def test_other_refs_are_matched_only_when_asked(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.git("checkout", "-q", "-b", "side")
        self.write("f.txt", "side\n")
        self.commit("side")
        self.git("checkout", "-q", "main")
        self.write("f.txt", "side\n")

        self.assertEqual(self.check()[0], 0)
        code, out = self.check("--all-refs")
        self.assertEqual(code, 1)
        self.assertIn("another ref", out)

    # -- waivers -----------------------------------------------------------

    def test_a_reasoned_waiver_suppresses_the_finding(self) -> None:
        self.one_commit_then_a_revert()
        self.waive({"path": "f.txt", "reason": "ATLAS-TEST: the revert is intended"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("waived: f.txt", out)
        self.assertIn("ATLAS-TEST", out)

    def test_a_waiver_pinned_to_other_content_does_not_suppress(self) -> None:
        self.one_commit_then_a_revert()
        self.waive({"path": "f.txt", "blob": "0" * 40, "reason": "ATLAS-TEST"})
        self.assertEqual(self.check()[0], 1)

    def test_an_unmatched_waiver_is_reported_but_passes(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.waive({"path": "f.txt", "reason": "ATLAS-TEST: no longer needed"})
        code, out = self.check()
        self.assertEqual(code, 0)
        self.assertIn("explains nothing", out)

    def test_a_waiver_without_a_reason_fails(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.waive({"path": "f.txt"})
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("WAIVER PROBLEM", out)

    def test_malformed_waiver_types_fail_with_a_diagnostic(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        malformed = (
            {"path": ["f.txt"], "reason": "reason"},
            {"path": "f.txt", "reason": 7},
            {"path": "f.txt", "reason": "reason", "blob": ["0" * 40]},
        )
        for entry in malformed:
            with self.subTest(entry=entry):
                self.waive(entry)
                code, out = self.check()
                self.assertEqual(code, 1)
                self.assertIn("WAIVER PROBLEM", out)

    def test_a_missing_waiver_file_is_not_an_error(self) -> None:
        self.one_commit_then_a_revert()
        self.assertFalse(self.waivers.exists())
        self.assertEqual(self.check()[0], 1)

    # -- basis: what can still reproduce an older revision -----------------

    def leave_an_index_behind(self, name: str = "leftover-idx") -> Path:
        """Copy the real index into the gitdir, then move HEAD past it.

        That is the whole defect: an index-shaped file git never reads, holding
        the revision it was written from. Nothing has to misuse it for it to be
        a hazard -- `git checkout -- <path>` reads whichever index it is told
        to, and a `GIT_INDEX_FILE` left in the environment names it.
        """
        self.write("f.txt", "one\n")
        self.commit("one")
        leftover = self.repo / ".git" / name
        leftover.write_bytes((self.repo / ".git" / "index").read_bytes())
        self.write("f.txt", "moved on\n")
        self.commit("two")
        return leftover

    def test_basis_is_clean_on_a_plain_checkout(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        code, out = self.basis()
        self.assertEqual(code, 0, out)
        self.assertIn("unused alternate indexes: none", out)

    def test_basis_flags_an_index_file_git_never_reads(self) -> None:
        leftover = self.leave_an_index_behind()
        code, out = self.basis()
        self.assertEqual(code, 1)
        self.assertIn("STALE BASIS: .git/leftover-idx", out)
        # The remedy has to name the file, not the working copy: the stale
        # revision lives in the index, and restoring from HEAD cannot remove it.
        # `resolve()` because git reports the long form of a Windows 8.3 path
        # (`RYANCL~1` -> `RyanClanton`) and the temp directory may be named in
        # either; the claim is that the remedy names this file, whatever spelling.
        self.assertIn(f"GIT_INDEX_FILE={leftover.resolve()} git diff --cached", out)

    def test_basis_never_flags_the_real_index(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        # `.git/index` is the index git reads; a dirty working copy is `check`'s
        # subject, and calling it a stale basis would make `basis` unpassable.
        self.write("f.txt", "two\n")
        code, out = self.basis()
        self.assertEqual(code, 0, out)
        self.assertNotIn("STALE BASIS", out)

    def test_basis_skips_only_gits_real_index_lock(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        real = (self.repo / ".git" / "index").read_bytes()
        (self.repo / ".git" / "index.lock").write_bytes(real)
        code, out = self.basis()
        self.assertEqual(code, 0, out)
        self.assertNotIn("STALE BASIS", out)

    def test_basis_flags_an_arbitrary_lock_named_index(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        leftover = self.repo / ".git" / "leftover.lock"
        leftover.write_bytes((self.repo / ".git" / "index").read_bytes())
        code, out = self.basis()
        self.assertEqual(code, 1, out)
        self.assertIn("STALE BASIS: .git/leftover.lock", out)

    def test_a_real_path_limited_commit_passes_the_hook(self) -> None:
        """End to end: the guard as `pre-commit`, through `git commit --only`.

        Running the guard by hand never sees the locks git holds during a
        commit; this is the path that was rejected.
        """
        self.write("f.txt", "one\n")
        self.write("g.txt", "one\n")
        self.commit("one")
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(exist_ok=True)
        script = Path(guard.__file__).resolve().as_posix()
        waivers = self.waivers.resolve().as_posix()
        python = Path(sys.executable).resolve().as_posix()
        (hooks / "pre-commit").write_text(
            f'#!/bin/sh\nexec "{python}" "{script}" basis --repo . --waivers "{waivers}"\n',
            encoding="utf-8", newline="\n",
        )
        (hooks / "pre-commit").chmod(0o755)
        self.write("f.txt", "two\n")
        self.write("g.txt", "two\n")
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *IDENT, "commit", "-q", "--only", "f.txt", "-m", "two"],
            capture_output=True, encoding="utf-8", errors="replace", env=self.environment,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.git("show", "HEAD:f.txt"), "two\n")

    def test_staged_scan_uses_the_caller_selected_index(self) -> None:
        self.write("f.txt", "old\n")
        self.commit("one")
        self.write("f.txt", "head\n")
        self.commit("two")

        self.write("f.txt", "old\n")
        self.git("add", "--", "f.txt")
        selected = self.repo / ".git" / "next-index-4242.lock"
        selected.write_bytes((self.repo / ".git" / "index").read_bytes())
        self.write("f.txt", "novel\n")
        selected_env = self.environment | {"GIT_INDEX_FILE": str(selected)}
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *IDENT, "add", "--", "f.txt"],
            capture_output=True, encoding="utf-8", errors="replace", env=selected_env,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        with mock.patch.dict(os.environ, {"GIT_INDEX_FILE": str(selected)}):
            code, out = self.check("--staged")
        self.assertEqual(code, 0, out)

        self.write("f.txt", "old\n")
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *IDENT, "add", "--", "f.txt"],
            capture_output=True, encoding="utf-8", errors="replace", env=selected_env,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with mock.patch.dict(os.environ, {"GIT_INDEX_FILE": str(selected)}):
            code, out = self.check("--staged")
        self.assertEqual(code, 1, out)
        self.assertIn("STALE SIDE: f.txt [index]", out)

    def test_live_split_index_is_not_a_stale_basis(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.git("update-index", "--split-index")
        code, out = self.basis()
        self.assertEqual(code, 0, out)
        self.assertNotIn("STALE BASIS: .git/sharedindex.", out)

    def test_ordinary_split_index_remains_live_during_alternate_index_commit(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.git("update-index", "--split-index")
        selected = self.repo / ".git" / "next-index-4242.lock"
        selected_env = self.environment | {"GIT_INDEX_FILE": str(selected)}
        proc = subprocess.run(
            ["git", "-C", str(self.repo), *IDENT, "read-tree", "HEAD"],
            capture_output=True, encoding="utf-8", errors="replace", env=selected_env,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with mock.patch.dict(os.environ, {"GIT_INDEX_FILE": str(selected)}):
            code, out = self.basis()
        self.assertEqual(code, 0, out)
        self.assertNotIn("STALE BASIS: .git/sharedindex.", out)

    def test_basis_ignores_a_same_named_file_that_is_not_an_index(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        # Detection is by the index file's own `DIRC` signature rather than by
        # name, so an unrelated `.git` scratch file is left alone.
        (self.repo / ".git" / "tmp-idx").write_text("scratch\n", encoding="utf-8")
        code, out = self.basis()
        self.assertEqual(code, 0, out)
        self.assertIn("alternate indexes: none", out)

    def test_basis_names_an_ancestor_branch_without_failing(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        self.git("branch", "previous-basis")
        self.write("f.txt", "two\n")
        self.commit("two")
        code, out = self.basis()
        # Reported, never fatal: keeping the previous basis is normal. What
        # matters is that it is *named*, so a reverted file can be traced to the
        # branch that still carries it instead of being rediscovered by hand.
        self.assertEqual(code, 0, out)
        self.assertIn("branches behind HEAD", out)
        self.assertIn("previous-basis", out)

    def test_a_leftover_index_can_be_waived_with_a_reason(self) -> None:
        self.leave_an_index_behind()
        self.waive({"path": ".git/leftover-idx", "reason": "ATLAS-TEST: one commit"})
        code, out = self.basis()
        self.assertEqual(code, 0, out)
        self.assertIn("waived: .git/leftover-idx", out)

    def test_check_names_the_ref_that_still_carries_the_stale_content(self) -> None:
        self.write("f.txt", "old\n")
        self.commit("one")
        self.git("branch", "previous-basis")
        self.write("f.txt", "new\n")
        self.commit("two")
        self.write("f.txt", "old\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        # The difference between a symptom and a cause: this is why it came
        # back, and it is the line a reader can act on.
        self.assertIn("Still materializable from: previous-basis", out)

    # -- status and read-only promise --------------------------------------

    def test_status_reports_the_match_and_stays_zero(self) -> None:
        self.one_commit_then_a_revert()
        code, out = self.status()
        # `status` is a measurement, not the gate: it reports and returns 0.
        self.assertEqual(code, 0)
        self.assertIn("STALE SIDE", out)
        self.assertIn("1 unexplained stale side(s)", out)

    def test_the_guard_never_writes_to_the_repository(self) -> None:
        self.one_commit_then_a_revert()
        before = (self.repo / "f.txt").read_bytes()
        index_before = self.git("ls-files", "--stage")
        self.check()
        self.status()
        self.basis()
        self.assertEqual((self.repo / "f.txt").read_bytes(), before)
        self.assertEqual(self.git("ls-files", "--stage"), index_before)

    def test_mtime_only_probe_does_not_refresh_index_bytes(self) -> None:
        self.write("f.txt", "one\n")
        self.commit("one")
        index = self.repo / ".git" / "index"
        before = index.read_bytes()
        stat = (self.repo / "f.txt").stat()
        os.utime(self.repo / "f.txt", (stat.st_atime + 2, stat.st_mtime + 2))
        self.assertEqual(self.check()[0], 0)
        self.assertEqual(self.status()[0], 0)
        self.assertEqual(self.basis()[0], 0)
        self.assertEqual(index.read_bytes(), before)

    def test_non_repository_and_corrupt_index_fail_closed(self) -> None:
        missing = self.repo.parent / "missing"
        missing.mkdir()
        for mode in ("check", "basis"):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = guard.main([mode, "--repo", str(missing)])
            self.assertEqual(code, 2)
            self.assertIn("ERROR", out.getvalue())

        self.write("f.txt", "one\n")
        self.commit("one")
        (self.repo / ".git" / "index").write_bytes(b"not an index")
        code, out = self.check("--staged")
        self.assertEqual(code, 2)
        self.assertIn("ERROR", out)

    def test_valid_caller_git_config_is_preserved(self) -> None:
        injected = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.abbrev",
            "GIT_CONFIG_VALUE_0": "12",
        }
        with mock.patch.dict(os.environ, injected):
            child = guard_git.git_env()
        for key, value in injected.items():
            self.assertEqual(child[key], value)

    def test_git_subprocess_terminates_a_spawned_child_at_the_deadline(self) -> None:
        started = time.monotonic()
        with mock.patch.object(guard_git, "GIT_TIMEOUT_SECONDS", 1):
            with self.assertRaises(git_process.GitProcessError):
                guard_git.run(
                    self.repo,
                    "-c",
                    "alias.review-wait=!sleep 5",
                    "review-wait",
                )
        self.assertLess(time.monotonic() - started, 4)


if __name__ == "__main__":
    unittest.main()
