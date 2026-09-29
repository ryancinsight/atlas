#!/usr/bin/env python3
"""Refuse a push that adds a credential.

A secret that reaches a remote is published: rewriting history does not
unpublish it, so the only cure is rotating it. The pre-push gate therefore
scans what a push adds before it leaves the machine (prompt.yaml,
engineering_gates: workflow hygiene).

The gitleaks-class tools were measured unusable as a fleet gate here:
`ripsecrets` 0.1.11 does not compile on Windows (its pre-commit installer
uses `std::os::unix` unconditionally), and gitleaks ships as a downloaded
binary. This scanner runs the high-signal subset of gitleaks' default rules --
provider-prefixed tokens and private keys, whose false-positive rate is near
zero -- over the lines a pushed range adds. It carries no entropy heuristics:
a blocking gate that fires on random-looking test data is a gate people
bypass, and that coverage limit is the price of never doing so.

Findings never print the secret. Each names its rule, file, line, and a
fingerprint: the first twelve hex digits of the value's SHA-256. A deliberate
fixture, such as a documented example key, is allowed by committing its full
fingerprint to `.secret-scan-allowlist` at the repository root, one per line;
`fingerprint` prints it from standard input, so the value never reaches a
command line or shell history.

    python scripts/atlas-secret-scan.py check --root repos/ritk --rev HEAD --base origin/main
    python scripts/atlas-secret-scan.py fingerprint < value.txt
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# `git diff` against the empty tree lists every line of the revision, which
# is what a push with no base (a first push, nothing upstream) adds.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
ALLOWLIST = ".secret-scan-allowlist"

# Patterns follow gitleaks' default rules (config/gitleaks.toml; the rule ids
# are the names here), with their trailing-delimiter groups written as
# lookaheads so the match is the secret alone. The crates.io token follows
# crates.io's own generator instead: "cio" and 32 alphanumerics
# (crates/crates_io_database/src/utils/token.rs).
RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws-access-token",
     re.compile(r"\b((?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16})\b")),
    ("github-pat", re.compile(r"(ghp_[0-9a-zA-Z]{36})")),
    ("github-fine-grained-pat", re.compile(r"(github_pat_\w{82})")),
    ("github-oauth", re.compile(r"(gho_[0-9a-zA-Z]{36})")),
    ("github-app-token", re.compile(r"((?:ghu|ghs)_[0-9a-zA-Z]{36})")),
    ("github-refresh-token", re.compile(r"(ghr_[0-9a-zA-Z]{36})")),
    ("crates-io-token", re.compile(r"\b(cio[A-Za-z0-9]{32})\b")),
    ("pypi-upload-token", re.compile(r"(pypi-AgEIcHlwaS5vcmc[\w-]{50,1000})")),
    ("anthropic-api-key",
     re.compile(r"\b(sk-ant-(?:api03|admin01)-[a-zA-Z0-9_\-]{93}AA)(?![a-zA-Z0-9_\-])")),
    ("slack-bot-token", re.compile(r"(xoxb-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*)")),
    ("slack-user-token", re.compile(r"(xox[pe](?:-[0-9]{10,13}){3}-[a-zA-Z0-9-]{28,34})")),
    ("gcp-api-key", re.compile(r"\b(AIza[\w-]{35})(?![\w-])")),
    ("stripe-access-token",
     re.compile(r"\b((?:sk|rk)_(?:test|live|prod)_[a-zA-Z0-9]{10,99})(?![a-zA-Z0-9])")),
)

# A private key is its header followed by base64 body. The header alone is
# prose -- documentation describing the format -- so a finding needs the body
# line after it, and the body line is what is fingerprinted.
PRIVATE_KEY_HEADER = re.compile(r"(?i)-----BEGIN[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----")
KEY_BODY = re.compile(r"^\s*([A-Za-z0-9+/]{40,}={0,2})\s*$")

HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def fingerprint(secret: str) -> str:
    """The full SHA-256 hex digest an allowlist entry records."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)


def added_lines(root: Path, rev: str, base: str | None) -> list[tuple[str, int, str]]:
    """Return every line from each added or modified blob in the range."""
    diff_base = base or EMPTY_TREE
    proc = _git(root, "diff", "--no-renames", "--name-status", "--diff-filter=ACMRT", "-z", diff_base, rev)
    if proc.returncode:
        raise RuntimeError(f"git diff {diff_base}..{rev} failed: {proc.stderr.decode('utf-8', 'replace').strip()}")
    fields = proc.stdout.split(b"\0")
    lines: list[tuple[str, int, str]] = []
    for index in range(0, len(fields) - 1, 2):
        status = fields[index].decode("ascii", "replace")
        raw_path = fields[index + 1]
        if not raw_path or status[:1] not in {"A", "C", "M", "R", "T"}:
            continue
        path = raw_path.decode("utf-8", "replace")
        tree_entry = _git(root, "ls-tree", rev, "--", path)
        if tree_entry.returncode: raise RuntimeError(f"git ls-tree {rev}:{path} failed")
        if tree_entry.stdout.startswith(b"160000 "): continue
        blob = _git(root, "show", f"{rev}:{path}")
        if blob.returncode:
            raise RuntimeError(f"git show {rev}:{path} failed: {blob.stderr.decode('utf-8', 'replace').strip()}")
        text = blob.stdout.decode("utf-8", "replace")
        previous: Counter[str] = Counter()
        if base:
            prior = _git(root, "show", f"{base}:{path}")
            if prior.returncode == 0:
                previous = Counter(prior.stdout.decode("utf-8", "replace").splitlines())
        for number, line in enumerate(text.splitlines(), 1):
            if previous[line]:
                previous[line] -= 1
                continue
            lines.append((path, number, line))
    return lines

def scan(lines: list[tuple[str, int, str]]) -> list[tuple[str, str, int, str]]:
    """`(rule, path, line, secret)` for each credential in `lines`."""
    findings: list[tuple[str, str, int, str]] = []
    for index, (path, number, text) in enumerate(lines):
        for rule, pattern in RULES:
            findings.extend((rule, path, number, m.group(1)) for m in pattern.finditer(text))
        if PRIVATE_KEY_HEADER.search(text) and index + 1 < len(lines):
            next_path, next_number, next_text = lines[index + 1]
            body = KEY_BODY.match(next_text)
            if next_path == path and next_number == number + 1 and body:
                findings.append(("private-key", path, number, body.group(1)))
    return findings


def allowlist(root: Path, rev: str) -> frozenset[str]:
    """Fingerprints the revision's `.secret-scan-allowlist` permits."""
    proc = _git(root, "show", f"{rev}:{ALLOWLIST}")
    if proc.returncode:
        return frozenset()
    return frozenset(
        line.split("#", 1)[0].strip().lower()
        for line in proc.stdout.decode("utf-8", "replace").splitlines()
        if line.split("#", 1)[0].strip()
    )


def check(root: Path, rev: str, base: str | None) -> int:
    allowed = allowlist(root, rev)
    findings = [
        finding for finding in scan(added_lines(root, rev, base))
        if fingerprint(finding[3]) not in allowed
    ]
    if not findings:
        print(f"secret-scan: no credential in the lines {rev[:12]} adds")
        return 0
    print(f"secret-scan: {len(findings)} credential(s) in the lines {rev[:12]} adds:")
    for rule, path, number, secret in findings:
        print(f"  {path}:{number}  {rule}  fingerprint {fingerprint(secret)[:12]}")
    print(
        "\nRemove each from every commit in the range. A value that ever reached a "
        "remote is published: rotate it. A deliberate fixture is allowed by adding "
        f"its full fingerprint to {ALLOWLIST}."
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    run = sub.add_parser("check", help="scan the lines a revision adds over a base")
    run.add_argument("--root", type=Path, default=Path.cwd(), help="repository to scan")
    run.add_argument("--rev", default="HEAD", help="pushed revision")
    run.add_argument("--base", help="base revision; omitted scans the whole revision")
    sub.add_parser("fingerprint", help="print the allowlist fingerprint of standard input")
    args = parser.parse_args()
    if args.mode == "fingerprint":
        print(fingerprint(sys.stdin.read().strip()))
        return 0
    try:
        return check(args.root, args.rev, args.base)
    except RuntimeError as error:
        print(f"secret-scan: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
