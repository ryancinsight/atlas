#!/usr/bin/env python3
"""Tests for the pre-push credential scan.

Every token here is assembled at run time, so this file never carries a
literal credential for the scan to find in its own push.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import tracemalloc
import unittest
from pathlib import Path
from unittest import mock

from readonly_tree import clear_readonly_tree

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-secret-scan.py"
_SPEC = importlib.util.spec_from_file_location("atlas_secret_scan", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
scan = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scan
_SPEC.loader.exec_module(scan)

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}

ALNUM = "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7cF0hL"  # 32 mixed-case alphanumerics


def token(rule: str) -> str:
    """A syntactically valid, meaningless credential for `rule`."""
    return {
        "aws-access-token": "AK" + "IA" + "QWERTYUIOPASDFGH",
        "github-pat": "gh" + "p_" + ALNUM + "Xy12",
        "github-fine-grained-pat": "github" + "_pat_" + ("aB3_" * 20) + "Zz",
        "github-oauth": "gh" + "o_" + ALNUM + "Xy12",
        "github-app-token": "gh" + "s_" + ALNUM + "Xy12",
        "github-refresh-token": "gh" + "r_" + ALNUM + "Xy12",
        "crates-io-token": "ci" + "o" + ALNUM,
        "pypi-upload-token": "pypi-" + "AgEIcHlwaS5vcmc" + ("x-Y_" * 14),
        "anthropic-api-key": "sk-" + "ant-api03-" + ("a1B-_" * 18) + "abc" + "AA",
        "slack-bot-token": "xo" + "xb-" + "1234567890-" + "0987654321-" + "AbCdEf",
        "slack-user-token": "xo" + "xp-" + "1234567890-" * 3 + ("aB3-" * 7),
        "gcp-api-key": "AI" + "za" + ALNUM + "_-x",
        "stripe-access-token": "sk" + "_live_" + "a1B2c3D4e5F6g7H8",
    }[rule]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True, env=GIT_ENV).stdout.strip()


def _is_running(pid: int, wait_for_exit: bool = False) -> bool:
    """Whether process `pid` is alive; with `wait_for_exit`, after waiting for it to end."""
    if os.name == "nt":
        import ctypes

        kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if not handle:
            return False
        try:
            # WAIT_OBJECT_0: the process has exited.
            return kernel.WaitForSingleObject(handle, 10_000 if wait_for_exit else 0) != 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        # A killed process is a zombie until its parent reaps it.
        return Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split(") ")[-1][0] != "Z"
    except OSError:
        return True


class RuleTestCase(unittest.TestCase):
    def test_every_rule_finds_its_credential_exactly(self) -> None:
        for rule, _ in scan.RULES:
            with self.subTest(rule=rule):
                value = token(rule)
                found = scan.scan([("c0", "config.toml", 7, f'key = "{value}"')])
                self.assertEqual(found, [(rule, "c0", "config.toml", 7, value)])

    def test_near_misses_are_not_credentials(self) -> None:
        for text in (
            "gh" + "p_" + ALNUM,                  # 32 characters, not 36
            "AK" + "IA" + "qwertyuiopasdfgh",     # lowercase body
            "ci" + "o" + ALNUM[:31],              # 31 characters, not 32
            "the " + "AI" + "za" + " prefix alone",
            "-----BEGIN RSA PRIVATE KEY----- appears in the format's documentation",
        ):
            with self.subTest(text=text):
                self.assertEqual(scan.scan([("c0", "docs.md", 1, text)]), [])

    def test_a_private_key_needs_its_body_on_the_next_added_line(self) -> None:
        body = "MIIEow" + "IBAAKCAQEA" + ALNUM + ALNUM
        header = "-----BEGIN RSA " + "PRIVATE KEY-----"
        self.assertEqual(
            scan.scan([("c0", "id_rsa", 1, header), ("c0", "id_rsa", 2, body)]),
            [("private-key", "c0", "id_rsa", 1, body)],
        )
        # A body in another file, another commit, or not adjacent, is not this key's.
        self.assertEqual(scan.scan([("c0", "id_rsa", 1, header), ("c0", "other", 2, body)]), [])
        self.assertEqual(scan.scan([("c0", "id_rsa", 1, header), ("c1", "id_rsa", 2, body)]), [])
        self.assertEqual(scan.scan([("c0", "id_rsa", 1, header), ("c0", "id_rsa", 5, body)]), [])

    def test_fingerprints_are_sha256(self) -> None:
        self.assertEqual(
            scan.fingerprint("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )


class _CountedPiece(bytes):
    """A piece of a stream that counts the bytes searched in it or joined onto it."""

    examined = 0

    def _count(self, size: int) -> None:
        type(self).examined += size

    def split(self, *args: object) -> list[bytes]:  # type: ignore[override]
        self._count(len(self))
        return bytes.split(self, *args)  # type: ignore[arg-type]

    def find(self, *args: object) -> int:  # type: ignore[override]
        self._count(len(self))
        return bytes.find(self, *args)  # type: ignore[arg-type]

    def partition(self, *args: object) -> tuple[bytes, bytes, bytes]:  # type: ignore[override]
        self._count(len(self))
        return bytes.partition(self, *args)  # type: ignore[arg-type]

    def __contains__(self, item: object) -> bool:
        self._count(len(self))
        return bytes.__contains__(self, item)  # type: ignore[arg-type]

    def __add__(self, other: bytes) -> bytes:  # type: ignore[override]
        self._count(len(self) + len(other))
        return bytes(self) + bytes(other)

    def __radd__(self, other: bytes) -> bytes:
        self._count(len(self) + len(other))
        return bytes(other) + bytes(self)


class RecordSplitTestCase(unittest.TestCase):
    def test_records_are_the_same_whatever_the_piece_size(self) -> None:
        for separator in (b"\n", b"\0"):
            data = separator.join([b"a", b"", b"bc", b"", b"", b"def", b"g"]) + separator + b"tail"
            expected = data.split(separator)
            for size in range(1, len(data) + 2):
                with self.subTest(separator=separator, size=size):
                    pieces = [data[i:i + size] for i in range(0, len(data), size)]
                    self.assertEqual(list(scan._split_records(pieces, separator)), expected)

    def test_a_terminated_stream_has_no_empty_final_record(self) -> None:
        self.assertEqual(list(scan._split_records([b"a\nb", b"\n"], b"\n")), [b"a", b"b"])
        self.assertEqual(list(scan._split_records([], b"\n")), [])

    def test_a_long_record_is_examined_a_bounded_number_of_times(self) -> None:
        # One record of 1 MiB in 512-byte pieces. Examined bytes are counted,
        # not time: rejoining and re-splitting the unfinished record per piece
        # examines about 1 GiB, a linear split about 1 MiB.
        piece, count = 512, 2048
        stream = [_CountedPiece(b"x" * piece) for _ in range(count)]
        stream.append(_CountedPiece(b"tail\nnext\n"))
        _CountedPiece.examined = 0
        records = list(scan._split_records(stream, b"\n"))
        self.assertEqual(records, [b"x" * piece * count + b"tail", b"next"])
        total = sum(len(item) for item in stream)
        self.assertLessEqual(_CountedPiece.examined, 2 * total)


class PushedRangeTestCase(unittest.TestCase):
    """Only the lines a range adds are scanned, and nothing prints a secret."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="atlas-secret-scan-")
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        (self.root / "settings.env").write_text(
            f"OLD={token('github-pat')}\n", encoding="utf-8"
        )
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "base")
        self.base = _git(self.root, "rev-parse", "HEAD")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _commit(self, name: str, text: str) -> str:
        path = self.root / name
        path.write_text(path.read_text(encoding="utf-8") + text if path.exists() else text,
                        encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", name)
        return _git(self.root, "rev-parse", "HEAD")

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                              text=True, env=GIT_ENV)

    def test_a_credential_already_in_the_base_is_not_rescanned(self) -> None:
        rev = self._commit("settings.env", "PORT=8080\n")
        self.assertEqual(scan.check(self.root, rev, self.base), 0)

    def test_an_added_credential_blocks_without_printing_it(self) -> None:
        value = token("crates-io-token")
        rev = self._commit("publish.env", f"CARGO_REGISTRY_TOKEN={value}\n")
        proc = self._run("check", "--root", str(self.root), "--rev", rev, "--base", self.base)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("publish.env:1  crates-io-token", proc.stdout)
        self.assertIn(scan.fingerprint(value)[:12], proc.stdout)
        self.assertNotIn(value, proc.stdout + proc.stderr)

    def test_a_line_beginning_with_plus_plus_is_still_scanned(self) -> None:
        value = token("stripe-access-token")
        rev = self._commit("notes.txt", f"++ {value}\n")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertEqual(found, [("stripe-access-token", rev, "notes.txt", 1, value)])

    def test_an_allowlisted_fingerprint_passes(self) -> None:
        value = token("aws-access-token")
        self._commit("fixture.txt", f"example: {value}\n")
        rev = self._commit(scan.ALLOWLIST, f"{scan.fingerprint(value)}  # documented example\n")
        self.assertEqual(scan.check(self.root, rev, self.base), 0)

    def test_without_a_base_the_whole_revision_is_scanned(self) -> None:
        self.assertEqual(scan.check(self.root, self.base, None), 1)

    def test_a_credential_added_then_removed_in_the_range_still_blocks(self) -> None:
        value = token("github-pat")
        added = self._commit("temporary.env", f"TOKEN={value}\n")
        (self.root / "temporary.env").unlink()
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "remove the credential")
        rev = _git(self.root, "rev-parse", "HEAD")
        self.assertEqual(_git(self.root, "diff", self.base, rev), "")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", added, "temporary.env", 1, value)])
        proc = self._run("check", "--root", str(self.root), "--rev", rev, "--base", self.base)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn(added[:12], proc.stdout)
        self.assertNotIn(value, proc.stdout + proc.stderr)

    def test_each_finding_names_its_own_commit(self) -> None:
        first = self._commit("one.env", f"A={token('crates-io-token')}\n")
        second = self._commit("two.env", f"B={token('stripe-access-token')}\n")
        found = scan.scan(scan.added_lines(self.root, second, self.base))
        self.assertEqual(
            sorted((rule, commit) for rule, commit, *_ in found),
            sorted([("crates-io-token", first), ("stripe-access-token", second)]),
        )

    def test_a_merge_is_judged_against_its_first_parent(self) -> None:
        value = token("github-oauth")
        _git(self.root, "switch", "-q", "-c", "side")
        side = self._commit("side.env", f"S={value}\n")
        _git(self.root, "switch", "-q", "main")
        self._commit("main.txt", "main\n")
        _git(self.root, "merge", "--no-ff", "--no-edit", "side")
        rev = _git(self.root, "rev-parse", "HEAD")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertIn(("github-oauth", side, "side.env", 1, value), found)

    def test_a_credential_introduced_only_by_a_merge_resolution_blocks(self) -> None:
        _git(self.root, "switch", "-q", "-c", "side")
        self._commit("shared.txt", "side line\n")
        _git(self.root, "switch", "-q", "main")
        self._commit("main.txt", "main line\n")
        _git(self.root, "merge", "--no-commit", "--no-ff", "side")
        value = token("slack-bot-token")
        (self.root / "resolution.env").write_text(f"SLACK={value}\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "merge with a resolution")
        merge = _git(self.root, "rev-parse", "HEAD")
        found = scan.scan(scan.added_lines(self.root, merge, self.base))
        self.assertEqual(found, [("slack-bot-token", merge, "resolution.env", 1, value)])

    def test_a_token_after_a_form_feed_on_the_same_line_is_scanned(self) -> None:
        value = token("github-pat")
        rev = self._commit("notes.txt", f"note\x0c{value}\n")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", rev, "notes.txt", 1, value)])

    def test_a_pushed_diff_attribute_cannot_hide_a_credential(self) -> None:
        value = token("github-pat")
        (self.root / ".gitattributes").write_text("* -diff\n", encoding="utf-8")
        rev = self._commit("hidden.env", f"TOKEN={value}\n")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", rev, "hidden.env", 1, value)])

    def test_a_nul_byte_cannot_hide_a_credential(self) -> None:
        value = token("github-pat")
        (self.root / "blob.bin").write_bytes(b"\x00" + value.encode() + b"\n")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "binary")
        rev = _git(self.root, "rev-parse", "HEAD")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", rev, "blob.bin", 1, value)])

    def test_a_pushed_textconv_driver_cannot_rewrite_the_patch(self) -> None:
        value = token("github-pat")
        (self.root / ".gitattributes").write_text("*.env diff=hide\n", encoding="utf-8")
        _git(self.root, "config", "diff.hide.textconv", "echo converted")
        rev = self._commit("driven.env", f"TOKEN={value}\n")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", rev, "driven.env", 1, value)])

    def test_a_failing_log_raises_instead_of_reporting_a_clean_range(self) -> None:
        with self.assertRaises(RuntimeError):
            list(scan.added_lines(self.root, "0" * 40, self.base))

    def test_a_root_commit_is_scanned_when_the_user_hides_root_patches(self) -> None:
        _git(self.root, "config", "log.showRoot", "false")
        found = scan.scan(scan.added_lines(self.root, self.base, None))
        self.assertEqual(
            found, [("github-pat", self.base, "settings.env", 1, token("github-pat"))]
        )

    def test_a_token_straddling_a_read_boundary_is_found(self) -> None:
        value = token("github-pat")
        # One 800 KB line of adjacent tokens: whatever size a reader takes at a
        # time, some boundary falls inside a token.
        count = 20_000
        rev = self._commit("wide.txt", " ".join([value] * count) + "\n")
        found = scan.scan(scan.added_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", rev, "wide.txt", 1, value)] * count)

    def _object_line(self, rev: str, needle: str) -> int:
        """The 1-based line of the commit object `rev` that holds `needle`."""
        lines = _git(self.root, "cat-file", "commit", rev).split("\n")
        return next(number for number, line in enumerate(lines, 1) if needle in line)

    def test_a_credential_in_a_commit_message_is_found(self) -> None:
        message_token, file_token = token("github-pat"), token("github-oauth")
        (self.root / "notes.txt").write_text(f"TOKEN={file_token}\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", f"deploy with {message_token}", "-m", "second paragraph")
        rev = _git(self.root, "rev-parse", "HEAD")
        found = scan.scan(scan.scanned_lines(self.root, rev, self.base))
        self.assertEqual(
            found,
            [("github-pat", rev, scan.COMMIT_PATH, self._object_line(rev, message_token), message_token),
             ("github-oauth", rev, "notes.txt", 1, file_token)],
        )

    def test_a_credential_after_the_first_line_of_a_message_survives_a_control_character(self) -> None:
        first, third = token("github-pat"), token("github-oauth")
        message = f"subject {first}\x02 and more\n\nbody line\n{third}\n"
        tree = _git(self.root, "rev-parse", "HEAD^{tree}")
        rev = subprocess.run(
            ["git", "-C", str(self.root), "commit-tree", tree, "-p", self.base, "-F", "-"],
            check=True, capture_output=True, text=True, env=GIT_ENV, input=message,
        ).stdout.strip()
        found = scan.scan(scan.scanned_lines(self.root, rev, self.base))
        self.assertEqual(
            found,
            [("github-pat", rev, scan.COMMIT_PATH, self._object_line(rev, first), first),
             ("github-oauth", rev, scan.COMMIT_PATH, self._object_line(rev, third), third)],
        )

    def test_a_credential_in_the_name_of_an_empty_added_file_is_found(self) -> None:
        value = token("github-pat")
        (self.root / value).write_text("", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "add an empty file")
        rev = _git(self.root, "rev-parse", "HEAD")
        found = scan.scan(scan.scanned_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", rev, scan.NAME_PATH, 0, value)])

    def test_a_credential_in_the_new_name_of_a_pure_rename_is_found(self) -> None:
        value = token("github-pat")
        self._commit("plain.txt", "unchanged content\n")
        _git(self.root, "mv", "plain.txt", f"{value}.txt")
        _git(self.root, "commit", "-q", "-m", "rename")
        rev = _git(self.root, "rev-parse", "HEAD")
        self.assertIn("similarity index 100%", _git(self.root, "show", "-M", "--format=", rev))
        found = scan.scan(scan.scanned_lines(self.root, rev, self.base))
        self.assertEqual(found, [("github-pat", rev, scan.NAME_PATH, 0, f"{value}")])

    def _partial_clone(self, parent: str) -> tuple[Path, Path]:
        """A `blob:none` clone of this repository, and the bare origin it came from."""
        bare = Path(parent) / "origin.git"
        clone = Path(parent) / "clone"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.root), str(bare)],
                       check=True, env=GIT_ENV)
        _git(bare, "config", "uploadpack.allowFilter", "true")
        _git(bare, "config", "uploadpack.allowAnySHA1InWant", "true")
        subprocess.run(["git", "clone", "-q", "--no-checkout", "--filter=blob:none",
                        bare.as_uri(), str(clone)], check=True, env=GIT_ENV)
        return bare, clone

    def _main_moves_in_a_partial_clone(self, bare: Path, clone: Path) -> str:
        """The origin's main changes a file; the clone fetches commits and trees, no blobs."""
        (self.root / "other.txt").write_text("added on main\n", encoding="utf-8")
        moved = self._commit("settings.env", "PORT=9090\n")
        _git(self.root, "push", "-q", str(bare), "main")
        _git(clone, "fetch", "-q", "origin", "main")
        return moved

    def _plumbing_merge_of_main(self, clone: Path, main: str) -> str:
        """A merge of `main` into a branch that never read the blobs `main` changed."""
        env = {**GIT_ENV, "GIT_INDEX_FILE": str(clone / "plumbing.index")}

        def plumbing(*args: str, data: str | None = None) -> str:
            return subprocess.run(["git", "-C", str(clone), *args], check=True, text=True,
                                  capture_output=True, env=env, input=data).stdout.strip()

        plumbing("read-tree", self.base)
        blob = plumbing("hash-object", "-w", "--stdin", data="branch file\n")
        plumbing("update-index", "--add", "--cacheinfo", f"100644,{blob},branch.txt")
        branch = plumbing("commit-tree", plumbing("write-tree"), "-p", self.base, "-m", "branch change")
        merged = plumbing("merge-tree", "--write-tree", branch, main).splitlines()[0]
        return plumbing("commit-tree", merged, "-p", branch, "-p", main, "-m", "merge main")

    def test_a_bounded_range_fetches_its_missing_blobs_in_one_batch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            main = self._main_moves_in_a_partial_clone(bare, clone)
            merge = self._plumbing_merge_of_main(clone, main)
            needed = list(scan._objects_a_scan_reads(clone, f"{main}..{merge}"))
            self.assertGreaterEqual(len(scan._missing(clone, needed)), 2)
            trace = Path(parent) / "trace.json"
            with mock.patch.dict(os.environ, {"GIT_TRACE2_EVENT": str(trace)}):
                self.assertEqual(scan.check(clone, merge, main), 0)
            self.assertEqual(scan._missing(clone, needed), [])
            starts = [
                event["argv"] for event in map(json.loads, trace.read_text(encoding="utf-8").splitlines())
                if event.get("event") == "start"
            ]
            self.assertEqual(sum("fetch" in argv for argv in starts), 1, starts)

    def test_a_credential_inside_a_fetched_blob_is_found(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            value = token("github-oauth")
            # A modification: its patch needs the base blob and the new one,
            # and neither is in the clone.
            moved = self._commit("settings.env", f"NEW={value}\n")
            _git(self.root, "push", "-q", str(bare), "main")
            _git(clone, "fetch", "-q", "origin", "main")
            result = self._run("check", "--root", str(clone), "--rev", moved, "--base", self.base)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn(scan.fingerprint(value)[:12], result.stdout)
            self.assertNotIn(value, result.stdout)

    def test_a_promisor_flag_git_reads_as_true_is_honoured(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            main = self._main_moves_in_a_partial_clone(bare, clone)
            _git(clone, "config", "remote.origin.promisor", "yes")
            self.assertEqual(scan._promisor_remotes(clone), ["origin"])
            self.assertEqual(scan.check(clone, main, self.base), 0)

    def test_missing_blobs_are_found_across_batches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            main = self._main_moves_in_a_partial_clone(bare, clone)
            needed = list(scan._objects_a_scan_reads(clone, f"{self.base}..{main}"))
            whole = sorted(scan._missing(clone, needed))
            self.assertGreaterEqual(len(whole), 3)
            with mock.patch.object(scan, "BATCH_SIZE", 2):
                self.assertEqual(sorted(scan._missing(clone, needed)), whole)

    def test_a_fetch_past_its_deadline_cannot_run_the_scan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            main = self._main_moves_in_a_partial_clone(bare, clone)
            sleeper = f'"{Path(sys.executable).as_posix()}" -c "import time; time.sleep(300)"'
            _git(clone, "config", "remote.origin.uploadpack", sleeper)
            with mock.patch.object(scan, "FETCH_DEADLINE_SECONDS", 1):
                with self.assertRaisesRegex(RuntimeError, "took over 1 s"):
                    scan.check(clone, main, self.base)

    def test_ending_a_process_tree_ends_the_grandchild(self) -> None:
        code = (
            "import subprocess, sys\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])\n"
            "print(child.pid, flush=True)\n"
            "child.wait()\n"
        )
        proc = scan._start([sys.executable, "-c", code], stdout=subprocess.PIPE)
        assert proc.stdout is not None
        grandchild = int(proc.stdout.readline())
        self.assertTrue(_is_running(grandchild))
        scan._kill_tree(proc)
        proc.wait()
        proc.stdout.close()
        self.assertFalse(_is_running(grandchild, wait_for_exit=True))

    def test_a_command_past_its_deadline_is_reported(self) -> None:
        with self.assertRaises(subprocess.TimeoutExpired):
            scan._run_bounded([sys.executable, "-c", "import time; time.sleep(300)"], b"", 1)

    def test_the_patch_read_itself_never_fetches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            main = self._main_moves_in_a_partial_clone(bare, clone)
            with self.assertRaises(RuntimeError):
                list(scan.added_lines(clone, main, self.base))

    def test_an_unbounded_scan_of_a_partial_clone_cannot_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            main = self._main_moves_in_a_partial_clone(bare, clone)
            result = self._run("check", "--root", str(clone), "--rev", main)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("could not run", result.stderr)
            self.assertIn("backfill", result.stderr)
            self.assertIn("worktree add --detach", result.stderr)
            self.assertNotIn("switch", result.stderr)
            self.assertIn("HEAD only", result.stderr)

    def test_blobs_no_promisor_remote_supplies_make_the_scan_unable_to_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-secret-scan-clone-") as parent:
            bare, clone = self._partial_clone(parent)
            main = self._main_moves_in_a_partial_clone(bare, clone)
            clear_readonly_tree(bare)
            result = self._run("check", "--root", str(clone), "--rev", main, "--base", self.base)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("could not run", result.stderr)
            self.assertIn("did not supply", result.stderr)
            self.assertNotIn("credential", result.stdout)

    def test_the_patch_is_streamed_not_held(self) -> None:
        line = "x" * 79 + "\n"
        (self.root / "large.txt").write_text(line * 300_000, encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "large file")
        rev = _git(self.root, "rev-parse", "HEAD")
        tracemalloc.start()
        try:
            found = scan.scan(scan.added_lines(self.root, rev, self.base))
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        self.assertEqual(found, [])
        # The patch is 24 MB; holding it as bytes, text, or a list of lines
        # costs at least that much, streaming costs one line.
        self.assertLess(peak, 4 * 1024 * 1024)

    def test_fingerprint_reads_standard_input(self) -> None:
        proc = subprocess.run([sys.executable, str(SCRIPT), "fingerprint"], input="abc\n",
                              capture_output=True, text=True)
        self.assertEqual(proc.stdout.strip(), scan.fingerprint("abc"))


if __name__ == "__main__":
    unittest.main()
