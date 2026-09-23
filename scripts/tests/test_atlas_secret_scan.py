#!/usr/bin/env python3
"""Tests for the pre-push credential scan.

Every token here is assembled at run time, so this file never carries a
literal credential for the scan to find in its own push.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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


class RuleTestCase(unittest.TestCase):
    def test_every_rule_finds_its_credential_exactly(self) -> None:
        for rule, _ in scan.RULES:
            with self.subTest(rule=rule):
                value = token(rule)
                found = scan.scan([("config.toml", 7, f'key = "{value}"')])
                self.assertEqual(found, [(rule, "config.toml", 7, value)])

    def test_near_misses_are_not_credentials(self) -> None:
        for text in (
            "gh" + "p_" + ALNUM,                  # 32 characters, not 36
            "AK" + "IA" + "qwertyuiopasdfgh",     # lowercase body
            "ci" + "o" + ALNUM[:31],              # 31 characters, not 32
            "the " + "AI" + "za" + " prefix alone",
            "-----BEGIN RSA PRIVATE KEY----- appears in the format's documentation",
        ):
            with self.subTest(text=text):
                self.assertEqual(scan.scan([("docs.md", 1, text)]), [])

    def test_a_private_key_needs_its_body_on_the_next_added_line(self) -> None:
        body = "MIIEow" + "IBAAKCAQEA" + ALNUM + ALNUM
        header = "-----BEGIN RSA " + "PRIVATE KEY-----"
        self.assertEqual(
            scan.scan([("id_rsa", 1, header), ("id_rsa", 2, body)]),
            [("private-key", "id_rsa", 1, body)],
        )
        # A body in another file, or not adjacent, is not this key's.
        self.assertEqual(scan.scan([("id_rsa", 1, header), ("other", 2, body)]), [])
        self.assertEqual(scan.scan([("id_rsa", 1, header), ("id_rsa", 5, body)]), [])

    def test_fingerprints_are_sha256(self) -> None:
        self.assertEqual(
            scan.fingerprint("abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )


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
        self.assertEqual(found, [("stripe-access-token", "notes.txt", 1, value)])

    def test_an_allowlisted_fingerprint_passes(self) -> None:
        value = token("aws-access-token")
        self._commit("fixture.txt", f"example: {value}\n")
        rev = self._commit(scan.ALLOWLIST, f"{scan.fingerprint(value)}  # documented example\n")
        self.assertEqual(scan.check(self.root, rev, self.base), 0)

    def test_without_a_base_the_whole_revision_is_scanned(self) -> None:
        self.assertEqual(scan.check(self.root, self.base, None), 1)

    def test_fingerprint_reads_standard_input(self) -> None:
        proc = subprocess.run([sys.executable, str(SCRIPT), "fingerprint"], input="abc\n",
                              capture_output=True, text=True)
        self.assertEqual(proc.stdout.strip(), scan.fingerprint("abc"))


if __name__ == "__main__":
    unittest.main()
