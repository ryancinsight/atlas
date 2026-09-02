#!/usr/bin/env python3
"""Tests for the diff-line parser and member filter of atlas-fmt-check.py.

`unformatted_files` shells out to `cargo fmt --all --check`; we exercise
that surface through `parse_rustfmt_diff_paths` (pure string in, list
out) and through `members` (pure directory filter), so the subprocess
boundary is the only behaviour this suite does not cover.
"""
from __future__ import annotations

import contextlib
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import os
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "atlas-fmt-check.py"
_SPEC = importlib.util.spec_from_file_location("atlas_fmt_check", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_fmt = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _fmt
_SPEC.loader.exec_module(_fmt)


# pathlib.Path.relative_to() emits backslashes on Windows, forward
# slashes on POSIX. The parser returns str(relative), so its output is
# platform-shaped; tests compare against os.fspath of the same join so
# they work on either host.
def _rel(repo: pathlib.Path, *parts: str) -> str:
    """str() of a relative path under repo, in the host's separator."""
    return os_fspath(pathlib.Path(repo, *parts).relative_to(repo))


import os as _os
def os_fspath(p):
    return _os.fspath(p)


class ParseRustfmtDiffPathsTestCase(unittest.TestCase):
    def test_empty_stdout_returns_placeholder(self) -> None:
        # Nonzero exit with no parseable diff still surfaces as a finding;
        # the placeholder tells the operator to read rustfmt's own output.
        result = _fmt.parse_rustfmt_diff_paths("", pathlib.Path("/tmp/repo"))
        self.assertEqual(
            result,
            ["(rustfmt reported changes; see `cargo fmt --all --check`)"],
        )

    def test_single_hunk_yields_relative_path(self) -> None:
        repo = pathlib.Path("/tmp/repo")
        stdout = f"Diff in {repo}{_os.sep}src{_os.sep}lib.rs:42:\n"
        result = _fmt.parse_rustfmt_diff_paths(stdout, repo)
        self.assertEqual(result, [_rel(repo, "src", "lib.rs")])

    def test_multiple_hunks_in_same_file_dedup(self) -> None:
        repo = pathlib.Path("/tmp/repo")
        stdout = "".join(
            f"Diff in {repo}{_os.sep}src{_os.sep}lib.rs:{line}:\n"
            for line in (10, 42, 99)
        )
        result = _fmt.parse_rustfmt_diff_paths(stdout, repo)
        self.assertEqual(result, [_rel(repo, "src", "lib.rs")])

    def test_distinct_files_kept_in_order(self) -> None:
        repo = pathlib.Path("/tmp/repo")
        stdout = (
            f"Diff in {repo}{_os.sep}src{_os.sep}a.rs:1:\n"
            f"Diff in {repo}{_os.sep}src{_os.sep}b.rs:2:\n"
            f"Diff in {repo}{_os.sep}src{_os.sep}a.rs:3:\n"
        )
        result = _fmt.parse_rustfmt_diff_paths(stdout, repo)
        self.assertEqual(
            result,
            [_rel(repo, "src", "a.rs"), _rel(repo, "src", "b.rs")],
        )

    @unittest.skipUnless(os.name == "nt", "verbatim-prefix stripping is Windows path semantics")
    def test_windows_extended_length_prefix_stripped(self) -> None:
        # Rustfmt on Windows emits the verbatim-path prefix; the parser
        # strips it before path normalization so the result is portable.
        repo = pathlib.Path(r"C:\repo")
        stdout = "Diff in \\\\?\\C:\\repo\\src\\lib.rs:10:\n"
        result = _fmt.parse_rustfmt_diff_paths(stdout, repo)
        self.assertEqual(result, [os_fspath(pathlib.Path("src") / "lib.rs")])

    def test_path_outside_repo_is_left_absolute(self) -> None:
        # A path rustfmt somehow emits that does not live under the repo
        # is left absolute — the caller surfaces it and the operator
        # investigates. We do not silently swallow it.
        stdout = "Diff in /somewhere/else/x.rs:1:\n"
        result = _fmt.parse_rustfmt_diff_paths(stdout, pathlib.Path("/tmp/repo"))
        self.assertEqual(result, ["/somewhere/else/x.rs"])

    def test_non_diff_lines_ignored(self) -> None:
        # Cargo and rustfmt sometimes emit lines around the diff (status,
        # banner). The parser only acts on `Diff in ...:` lines.
        repo = pathlib.Path("/tmp/repo")
        stdout = (
            "Note: rustfmt could not format some files.\n"
            f"Diff in {repo}{_os.sep}src{_os.sep}lib.rs:10:\n"
            "Some other line that should be ignored\n"
        )
        result = _fmt.parse_rustfmt_diff_paths(stdout, repo)
        self.assertEqual(result, [_rel(repo, "src", "lib.rs")])

    def test_workspace_root_path_normalized(self) -> None:
        # When the diff points at the workspace root itself (e.g.,
        # something rustfmt emits for a Cargo.toml), the relative_to
        # conversion yields 'Cargo.toml'.
        repo = pathlib.Path("/tmp/repo")
        stdout = f"Diff in {repo}{_os.sep}Cargo.toml:5:\n"
        result = _fmt.parse_rustfmt_diff_paths(stdout, repo)
        self.assertEqual(result, ["Cargo.toml"])


class MembersFilterTestCase(unittest.TestCase):
    def _make_repo(self, root: Path, name: str) -> Path:
        repo = root / "repos" / name
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "Cargo.toml").write_text('[package]\nname = "x"\n', encoding="utf-8")
        return repo

    def _stub_check_ignore(self, ignored_names: set[str]):
        """Return a stand-in for subprocess.run that mimics git check-ignore."""
        def _run(args, *args_, **kwargs):
            class _Result:
                stdout = ""
                stderr = ""
                returncode = 0 if (len(args) >= 4 and args[3] in ignored_names) else 1
            return _Result()
        return _run

    def test_returns_all_publishable_members_when_unselected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-fmt-check-") as tmp:
            root = Path(tmp)
            self._make_repo(root, "aequitas")
            self._make_repo(root, "asclepius")
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    mock.patch.object(_fmt, "REPOS", root / "repos")
                )
                stack.enter_context(
                    mock.patch.object(_fmt, "ROOT", root)
                )
                stack.enter_context(
                    mock.patch.object(
                        _fmt.subprocess, "run",
                        self._stub_check_ignore(set())
                    )
                )
                found = _fmt.members([])
            self.assertEqual({p.name for p in found}, {"aequitas", "asclepius"})

    def test_filters_to_selected_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-fmt-check-") as tmp:
            root = Path(tmp)
            self._make_repo(root, "aequitas")
            self._make_repo(root, "apollo")
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    mock.patch.object(_fmt, "REPOS", root / "repos")
                )
                stack.enter_context(
                    mock.patch.object(_fmt, "ROOT", root)
                )
                stack.enter_context(
                    mock.patch.object(
                        _fmt.subprocess, "run",
                        self._stub_check_ignore(set())
                    )
                )
                found = _fmt.members(["apollo"])
            self.assertEqual([p.name for p in found], ["apollo"])

    def test_skips_ignored_members(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-fmt-check-") as tmp:
            root = Path(tmp)
            self._make_repo(root, "aequitas")
            self._make_repo(root, "apollo")
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            (root / ".gitignore").write_text("repos/apollo\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore"], cwd=tmp, check=True)
            with contextlib.ExitStack() as stack:
                stack.enter_context(
                    mock.patch.object(_fmt, "REPOS", root / "repos")
                )
                stack.enter_context(
                    mock.patch.object(_fmt, "ROOT", root)
                )
                # Real `git check-ignore` in the temp repo honours the
                # .gitignore; the stub above is unnecessary here.
                found = _fmt.members([])
            self.assertEqual([p.name for p in found], ["aequitas"])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
