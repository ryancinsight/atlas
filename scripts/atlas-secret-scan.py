#!/usr/bin/env python3
"""Refuse a push that adds a credential.

A secret that reaches a remote is published: rewriting history does not
unpublish it, so the only cure is rotating it. The pre-push gate therefore
scans what a push adds before it leaves the machine (prompt.yaml,
engineering_gates: workflow hygiene). The scan covers every commit the push
introduces, each against its first parent: a credential added by one commit
and removed by the next is published with the push, though the pushed range's
net diff never contains it. Commit objects (messages included) and the names
of added files are scanned too. A scan that cannot run (an unreadable range,
blobs a partial clone lacks and cannot fetch) exits 2, distinct from the exit
1 that reports a credential.

The gitleaks-class tools were measured unusable as a fleet gate here:
`ripsecrets` 0.1.11 does not compile on Windows (its pre-commit installer
uses `std::os::unix` unconditionally), and gitleaks ships as a downloaded
binary. This scanner runs the high-signal subset of gitleaks' default rules --
provider-prefixed tokens and private keys, whose false-positive rate is near
zero -- over the lines each commit of a pushed range adds. It carries no entropy heuristics:
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
import hashlib
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO


def _load_sibling(module: str):
    """Load an exact adjacent runtime dependency under its import name."""
    path = Path(__file__).resolve().with_name(f"{module}.py")
    spec = importlib.util.spec_from_file_location(module, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    loaded = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(module)
    sys.modules[module] = loaded
    try:
        spec.loader.exec_module(loaded)
    except BaseException:
        if previous is None:
            sys.modules.pop(module, None)
        else:
            sys.modules[module] = previous
        raise
    return loaded


_load_sibling("windows_process")
process_tree = _load_sibling("process_tree")

ALLOWLIST = ".secret-scan-allowlist"

# Starts the line `git log` prints before each commit's patch. A patch line
# begins with a diff header, `@@`, or one of `+`, `-`, and space, so a line
# beginning with this control character is never patch content.
COMMIT_MARK = "\x01"

# What a finding names in place of a file when the value sits in a commit
# object (its headers or its message) or in the name of an added file.
COMMIT_PATH = "(commit object)"
NAME_PATH = "(file name)"

# Bytes read from a git process at a time, and objects asked of `cat-file` at
# a time.
READ_SIZE = 1 << 16
BATCH_SIZE = 10_000

GITLINK_MODE = "160000"

# One request fetches every blob a partial clone lacks for the pushed range;
# a push must not wait on the network without bound.
FETCH_DEADLINE_SECONDS = 300

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


@contextmanager
def _git_process(
    root: Path, args: list[str], feed: bytes | None = None
) -> Iterator[IO[bytes]]:
    """Run `git <args>`; yield its standard output; raise `RuntimeError` if it fails.

    Lazy fetching is off: a push must not reach out to a promisor remote one
    object at a time. `fetch_missing` fetches what a scan needs in one batch.
    `feed` is the process's standard input.
    """
    environment = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
    with tempfile.TemporaryFile() as errors, tempfile.TemporaryFile() as stdin:
        if feed is not None:
            stdin.write(feed)
            stdin.seek(0)
        proc = subprocess.Popen(
            ["git", "-C", str(root), *args],
            stdin=stdin if feed is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=errors, env=environment,
        )
        assert proc.stdout is not None
        try:
            yield proc.stdout
            proc.wait()
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                # The consumer abandoned the stream.
                proc.kill()
                proc.wait()
        if proc.returncode:
            errors.seek(0)
            raise RuntimeError(
                f"git {args[0]} failed: {errors.read().decode('utf-8', 'replace').strip()}"
            )


def _split_records(pieces: Iterable[bytes], separator: bytes) -> Iterator[bytes]:
    """Yield each `separator`-ended record of the stream `pieces`, without the separator.

    `separator` is one byte. Only the piece just read is searched, and the
    unfinished record is kept as a list of pieces joined once when it ends,
    so the work is linear in the stream however long a record is; rejoining
    and re-splitting the unfinished record per piece is quadratic in it.
    """
    unfinished: list[bytes] = []
    for piece in pieces:
        *whole, rest = piece.split(separator)
        if not whole:
            unfinished.append(rest)
            continue
        yield b"".join(unfinished) + whole[0]
        yield from whole[1:]
        unfinished = [rest]
    last = b"".join(unfinished)
    if last:
        yield last


def _git_records(
    root: Path, args: list[str], separator: bytes = b"\n"
) -> Iterator[bytes]:
    """Yield each `separator`-ended record `git <args>` prints, without the separator.

    The output is read in fixed pieces, so memory does not grow with it and a
    record may be longer than a piece.
    """
    with _git_process(root, args) as output:
        yield from _split_records(iter(lambda: output.read(READ_SIZE), b""), separator)


def _changes(root: Path, span: str) -> Iterator[tuple[str, str, str, str, str, str, str]]:
    """Yield `(commit, status, old_mode, new_mode, old_id, new_id, path)` per change in `span`.

    Each commit is listed against its first parent, a root commit against the
    empty tree, with renames off so a renamed file is a deletion and an
    addition: every name that appears is an added one. The listing is
    NUL-terminated, which no file name can contain.
    """
    command = [
        "log", "--raw", "-z", "--no-abbrev", "--no-renames", "--root",
        "--diff-merges=first-parent", "--no-color", f"--format={COMMIT_MARK}%H", span, "--",
    ]
    commit = ""
    entry: tuple[str, str, str, str, str] | None = None
    for field in _git_records(root, command, b"\0"):
        text = field.decode("utf-8", "replace")
        if entry is not None:
            # A path is whatever follows its entry, whatever it begins with.
            yield (commit, *entry, text)
            entry = None
        elif text.startswith(COMMIT_MARK):
            commit = text[1:]
        else:
            # `:<old mode> <new mode> <old id> <new id> <status>`, led by the
            # newline git prints between a commit's line and its first entry.
            parts = text.lstrip("\n").removeprefix(":").split()
            if len(parts) != 5:
                raise RuntimeError(f"git log {span} printed an unreadable change: {text!r}")
            old_mode, new_mode, old_id, new_id, status = parts
            entry = (status, old_mode, new_mode, old_id, new_id)


def added_lines(
    root: Path, rev: str, base: str | None
) -> Iterator[tuple[str, str, int, str]]:
    """Yield `(commit, path, line, text)` for every line each commit of `base..rev` adds.

    One `git log -p` process lists the whole range, each commit diffed against
    its first parent (a merge's own changes included) and a root commit against
    the empty tree. Without a base, every commit reachable from `rev` is
    scanned.

    The pushed revision supplies the patch content and nothing else about how
    it is read: `--text` makes a file its attributes mark binary, or that holds
    a NUL byte, a patch like any other, `--no-textconv` and `--no-ext-diff`
    keep a diff driver it names from rewriting the lines, and `--root` keeps a
    user's `log.showRoot=false` from hiding a root commit's patch.
    """
    span = f"{base}..{rev}" if base else rev
    command = [
        "log", "-p", "--root", "--text", "--no-textconv", "--no-ext-diff",
        "--diff-merges=first-parent", "--no-color", "--unified=0",
        "--src-prefix=a/", "--dst-prefix=b/", f"--format={COMMIT_MARK}%H", span, "--",
    ]
    commit = ""
    path: str | None = None
    number = 0
    # A file's header runs from `diff --git` to its first hunk; only there is a
    # `+++` line a path. Inside a hunk it is an added line that begins with
    # "++", and reading it as a header would drop the rest of the file.
    in_header = False
    for record in _git_records(root, command):
        # Only a newline ends a patch line: a form feed or a Unicode separator
        # inside an added line stays in it.
        raw = record.decode("utf-8", "replace")
        hunk = HUNK.match(raw)
        if raw.startswith(COMMIT_MARK):
            commit, path, in_header = raw[1:].strip(), None, False
        elif raw.startswith("diff --git "):
            in_header, path = True, None
        elif hunk is not None:
            in_header, number = False, int(hunk.group(1))
        elif in_header:
            if raw.startswith("+++ "):
                target = raw[4:]
                path = None if target == "/dev/null" else target.removeprefix("b/")
        elif raw.startswith("+") and path is not None:
            yield commit, path, number, raw[1:].removesuffix("\r")
            number += 1


def added_names(
    root: Path, rev: str, base: str | None
) -> Iterator[tuple[str, str, int, str]]:
    """Yield `(commit, NAME_PATH, 0, name)` for every file name each commit of `base..rev` adds.

    An empty file and a pure rename have no patch lines, so only the change
    listing shows their names.
    """
    span = f"{base}..{rev}" if base else rev
    for commit, status, *_, path in _changes(root, span):
        if status == "A":
            yield commit, NAME_PATH, 0, path


def commit_lines(
    root: Path, rev: str, base: str | None
) -> Iterator[tuple[str, str, int, str]]:
    """Yield `(commit, COMMIT_PATH, line, text)` for every line of each commit object in `base..rev`.

    Each object is read whole at the length its header states, so nothing a
    message holds can end it early. The headers come with it: an author or
    committer name is published with the push like the message.
    """
    span = f"{base}..{rev}" if base else rev
    commits = [record + b"\n" for record in _git_records(root, ["rev-list", span, "--"])]
    if not commits:
        return
    with _git_process(root, ["cat-file", "--batch"], b"".join(commits)) as output:
        while header := output.readline():
            fields = header.split()
            if len(fields) != 3:
                raise RuntimeError(f"commit {fields[0].decode()} is unavailable")
            body = output.read(int(fields[2])).decode("utf-8", "replace")
            output.read(1)
            for number, line in enumerate(body.split("\n"), 1):
                yield fields[0].decode(), COMMIT_PATH, number, line.removesuffix("\r")


def scanned_lines(
    root: Path, rev: str, base: str | None
) -> Iterator[tuple[str, str, int, str]]:
    """Everything a push publishes that a credential can sit in: commits, names, patches."""
    yield from commit_lines(root, rev, base)
    yield from added_names(root, rev, base)
    yield from added_lines(root, rev, base)


def _objects_a_scan_reads(root: Path, span: str) -> Iterator[str]:
    """Yield the blob IDs the patches of `span` are computed from: both sides of every change."""
    for _commit, _status, old_mode, new_mode, old_id, new_id, _path in _changes(root, span):
        # A gitlink names a commit of another repository, never a blob here.
        for mode, id_ in ((old_mode, old_id), (new_mode, new_id)):
            if mode != GITLINK_MODE and id_.strip("0"):
                yield id_


def _missing(root: Path, objects: Iterable[str]) -> list[str]:
    """The IDs in `objects` this repository does not hold (no lazy fetch).

    Asked in batches, so only the missing IDs are held, not the whole listing.
    """
    missing: dict[str, None] = {}

    def ask(batch: list[str]) -> None:
        feed = "".join(f"{queried}\n" for queried in batch).encode()
        with _git_process(root, ["cat-file", "--batch-check"], feed) as output:
            missing.update(
                dict.fromkeys(
                    line.split()[0].decode() for line in output
                    if line.rstrip().endswith(b" missing")
                )
            )

    batch: list[str] = []
    for id_ in objects:
        batch.append(id_)
        if len(batch) == BATCH_SIZE:
            ask(batch)
            batch = []
    if batch:
        ask(batch)
    return list(missing)


def _run_bounded(command: list[str], feed: bytes, timeout: float) -> int:
    """Run `command` with bounded ownership of every descendant."""
    return process_tree.run(command, input=feed, timeout=timeout).returncode


def _promisor_remotes(root: Path) -> list[str]:
    """Names of the remotes git may fetch missing objects from, as git itself reads the flag."""
    listed = _git(root, "config", "--type=bool", "--get-regexp", r"^remote\..*\.promisor$")
    # Exit 1 is "no such key": not a partial clone.
    if listed.returncode not in (0, 1):
        raise RuntimeError(f"git config failed: {listed.stderr.decode('utf-8', 'replace').strip()}")
    return [
        line.split()[0].removeprefix("remote.").removesuffix(".promisor")
        for line in listed.stdout.decode("utf-8", "replace").splitlines()
        if line.split()[-1:] == ["true"]
    ]


def fetch_missing(root: Path, rev: str, base: str | None) -> None:
    """Fetch, in one batch, the blobs a partial clone lacks for scanning `base..rev`.

    A partial clone holds commits and trees but fetches blobs on demand, and
    a merge of the default branch that never read a changed file's blob leaves
    that blob missing. A bounded range names the blobs its patches need, so
    they are fetched from the promisor remote with a single request before
    the scan, which then runs with lazy fetching off. A range with no base
    would need every blob in history: it is refused instead, naming the cure.
    """
    span = f"{base}..{rev}" if base else rev
    missing = _missing(root, _objects_a_scan_reads(root, span))
    if not missing:
        return
    if base is None:
        raise RuntimeError(
            f"{len(missing)} blobs the scan reads are not in this partial clone, and a scan "
            f"with no base would need all of history: in a detached worktree of {rev[:12]} "
            f"(`git worktree add --detach <dir> {rev[:12]}`) run `git backfill`, which "
            "fetches the blobs reachable from HEAD only, then push again; the "
            "checkout the push runs from stays where it is"
        )
    remotes = _promisor_remotes(root)
    for remote in remotes:
        command = [
            "git", "-C", str(root), "fetch", remote, "--no-tags", "--no-write-fetch-head",
            "--recurse-submodules=no", "--filter=blob:none", "--stdin",
        ]
        try:
            fetched = _run_bounded(
                command, "".join(f"{id_}\n" for id_ in missing).encode(), FETCH_DEADLINE_SECONDS
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"fetching {len(missing)} blobs from {remote} took over {FETCH_DEADLINE_SECONDS} s"
            ) from None
        if fetched == 0:
            missing = _missing(root, missing)
        if not missing:
            return
    raise RuntimeError(
        f"{len(missing)} blobs the scan reads are missing and the promisor "
        f"remote(s) {remotes or 'none configured'} did not supply them"
    )


def scan(
    lines: Iterable[tuple[str, str, int, str]],
) -> list[tuple[str, str, str, int, str]]:
    """`(rule, commit, path, line, secret)` for each credential in `lines`."""
    findings: list[tuple[str, str, str, int, str]] = []
    # A private key is its header line and the body line right after it.
    header: tuple[str, str, int] | None = None
    for commit, path, number, text in lines:
        if header is not None:
            header_commit, header_path, header_number = header
            header = None
            body = KEY_BODY.match(text)
            if (
                header_commit == commit
                and header_path == path
                and number == header_number + 1
                and body
            ):
                findings.append(
                    ("private-key", header_commit, header_path, header_number, body.group(1))
                )
        for rule, pattern in RULES:
            findings.extend(
                (rule, commit, path, number, m.group(1)) for m in pattern.finditer(text)
            )
        if PRIVATE_KEY_HEADER.search(text):
            header = (commit, path, number)
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


def check(
    root: Path,
    rev: str,
    base: str | None,
    allowlist_rev: str | None = None,
) -> int:
    """Scan every commit of ``base..rev`` using an allowlist from a trusted revision."""
    fetch_missing(root, rev, base)
    allowed = allowlist(root, allowlist_rev or rev)
    findings = [
        finding for finding in scan(scanned_lines(root, rev, base))
        if fingerprint(finding[4]) not in allowed
    ]
    scope = f"{base[:12]}..{rev[:12]}" if base else rev[:12]
    if not findings:
        print(f"secret-scan: no credential in the commits {scope} adds")
        return 0
    print(f"secret-scan: {len(findings)} credential(s) in the commits {scope} adds:")
    for rule, commit, path, number, secret in findings:
        print(f"  {commit[:12]}  {path}:{number}  {rule}  fingerprint {fingerprint(secret)[:12]}")
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
    run = sub.add_parser("check", help="scan the lines each commit of a range adds")
    run.add_argument("--root", type=Path, default=Path.cwd(), help="repository to scan")
    run.add_argument("--rev", default="HEAD", help="pushed revision")
    run.add_argument("--base", help="base revision; omitted scans every commit reachable from --rev")
    run.add_argument(
        "--allowlist-rev",
        help="trusted revision supplying .secret-scan-allowlist; defaults to --rev",
    )
    sub.add_parser("fingerprint", help="print the allowlist fingerprint of standard input")
    args = parser.parse_args()
    if args.mode == "fingerprint":
        print(fingerprint(sys.stdin.read().strip()))
        return 0
    try:
        return check(args.root, args.rev, args.base, args.allowlist_rev)
    except RuntimeError as error:
        print(f"secret-scan: could not run: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
