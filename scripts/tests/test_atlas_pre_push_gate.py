#!/usr/bin/env python3
"""Integration tests for the owned member pre-push gate.

`scripts/git-hooks/pre-push` is the single source every member consumes
(ATLAS-PREPUSH-HOOK-FORKED-ACROSS-MEMBERS-2026-09-09). These tests drive
the script itself in fixture git repositories with stub `cargo`/`lockfile`
tools, so the range logic, the package mapper, and the blame classifier
are verified without a toolchain or network.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1] / "git-hooks" / "pre-push"
)
ZERO = "0" * 40

_IDENT = ["-c", "user.email=t@t", "-c", "user.name=t"]


def _git(repo: pathlib.Path, *argv: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *_IDENT, *argv],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _write(path: pathlib.Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)


def _path_without_cargo(extra_first: str) -> str:
    """PATH minus any entry holding a cargo binary.

    The missing-toolchain test must genuinely hide cargo, and the developer
    machine running these tests has a real toolchain on PATH.
    """
    entries = [extra_first]
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry or entry in entries:
            continue
        probe = pathlib.Path(entry)
        if (probe / "cargo.exe").exists() or (probe / "cargo").exists():
            continue
        entries.append(entry)
    return os.pathsep.join(entries)


class GateFixture:
    """A member-like git repo with a stub toolchain and lockfile checker."""

    def __init__(
        self,
        root: pathlib.Path,
        layout: str = "crates",
        default_branch: str = "main",
    ) -> None:
        self.root = root
        self.bin = root / "bin"
        self.bin.mkdir(parents=True)
        self.calls: pathlib.Path = root / "calls.log"
        self.lockfile_calls: pathlib.Path = root / "lockfile-calls.log"
        self.layout = layout
        _git_init_repo(root)
        if layout == "crates":
            _write(root / "Cargo.toml", '[workspace]\nmembers = ["crates/foo"]\n')
            _write(
                root / "crates" / "foo" / "Cargo.toml",
                '[package]\nname = "foo"\nversion = "0.1.0"\nedition = "2021"\n',
            )
            _write(root / "crates" / "foo" / "src" / "lib.rs", "pub fn f() {}\n")
        else:
            _write(
                root / "Cargo.toml",
                '[package]\nname = "solo"\nversion = "0.1.0"\nedition = "2021"\n',
            )
            _write(root / "src" / "lib.rs", "pub fn f() {}\n")
        _write(root / "Cargo.lock", "# lock\n")
        # A stub lockfile checker in the member-local location the hook
        # expects; records invocation and exits as configured.
        _write(
            root / "scripts" / "lockfile.py",
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "pathlib.Path(__file__).resolve().parent.parent.joinpath("
            "'lockfile-calls.log').write_text('called\\n')\n"
            "sys.exit(int(__import__('os').environ.get('LOCKFILE_EXIT', '0')))\n",
            executable=True,
        )
        self.set_cargo_behavior("pass")
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "add", "-A"], check=True
        )
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", "seed"],
            check=True,
        )
        # An origin with the default branch pushed, so upstream/default
        # logic resolves the way a real clone does -- including `origin/HEAD`,
        # which is what the gate reads on a first push with no upstream yet.
        subprocess.run(
            ["git", "init", "-q", "-b", default_branch,
             str(root / "upstream.git"), "--bare"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "remote", "add", "origin",
             str(root / "upstream.git")],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "push", "-q", "origin",
             f"HEAD:{default_branch}"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "remote", "set-head", "origin",
             "--auto"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "branch", "--set-upstream-to",
             f"origin/{default_branch}"],
            check=True,
        )

    def set_cargo_behavior(self, mode: str) -> None:
        """Install a stub `cargo`: `pass`, `fail-fmt`, `fail-clippy-ours`,
        `fail-clippy-environment`, or `missing` (no stub on PATH).

        A failing clippy prints `$CARGO_FAIL_LOG`, supplied by the caller
        through the hook's environment: embedding the log in the stub would
        re-evaluate its backticks (``could not compile `foo` ``) as command
        substitutions and mangle the witness lines the classifier reads.
        """
        stub = self.bin / "cargo"
        if stub.exists():
            stub.unlink()
        if mode == "missing":
            return
        if mode == "pass":
            body = 'echo "$@" >> "$FIXTURE_ROOT/calls.log"\nexit 0\n'
        elif mode == "fail-fmt":
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'if [ "$1" = "fmt" ]; then exit 1; fi\nexit 0\n'
            )
        elif mode.startswith("fail-clippy"):
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'if [ "$1" = "clippy" ]; then\n'
                '  printf "%s\\n" "$CARGO_FAIL_LOG" >&2\n'
                "  exit 1\n"
                "fi\nexit 0\n"
            )
        else:
            raise AssertionError(f"unknown cargo mode {mode}")
        _write(
            stub,
            "#!/usr/bin/env bash\n"
            f'FIXTURE_ROOT="{self.root}"\n' + body,
            executable=True,
        )

    def run_hook(self, push_lines: str, extra_env: dict | None = None) -> tuple:
        """Run the owned hook script in this fixture; return (exit, stderr)."""
        env = dict(os.environ)
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        if extra_env:
            env.update(extra_env)
        # Bytes, not text: on Windows a text-mode pipe translates `\n` to
        # `\r\n`, and the hook (like git itself) speaks raw `\n`-terminated
        # protocol lines. A stray `\r` would poison every SHA comparison.
        # (Byte input also requires binary mode: `text=True` breaks the
        # writer thread and hangs waiting on stdin forever.)
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            input=push_lines.encode("utf-8"),
            cwd=str(self.root),
            env=env,
            capture_output=True,
        )
        return (
            proc.returncode,
            proc.stderr.decode("utf-8", errors="replace"),
        )

    def push_line_new_branch(self, branch: str = "feat") -> str:
        """A pre-push stdin line for a never-pushed branch tip."""
        sha = _git(self.root, "rev-parse", branch)
        return f"refs/heads/{branch} {sha} refs/heads/{branch} {ZERO}\n"


def _git_init_repo(root: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), *_IDENT, "config", "user.email", "t@t"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), *_IDENT, "config", "user.name", "t"],
        check=True,
    )


class NewBranchRangeTestCase(unittest.TestCase):
    """A manifest-changing new branch must run the lockfile check.

    The vacuity this pins: comparing the tip against HEAD reads an empty
    range exactly when pushing the checked-out branch, so the check was
    skipped on precisely the pushes that needed it.
    """

    def test_new_branch_manifest_push_runs_lockfile_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            (fixture.root / "Cargo.toml").write_text(
                '[workspace]\nmembers = ["crates/foo", "crates/bar"]\n'
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "Cargo.toml"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "manifest"],
                check=True,
            )
            code, _ = fixture.run_hook(fixture.push_line_new_branch())
            self.assertEqual(code, 0)
            self.assertTrue(
                fixture.lockfile_calls.is_file(),
                "lockfile checker never ran for a manifest-changing new branch",
            )

    def test_docs_only_push_skips_lockfile_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            _write(fixture.root / "notes.md", "docs\n")
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "notes.md"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "docs"],
                check=True,
            )
            code, stderr = fixture.run_hook(fixture.push_line_new_branch())
            self.assertEqual(code, 0)
            self.assertFalse(fixture.lockfile_calls.is_file())
            self.assertIn("not needed", stderr)


class PackageMapperTestCase(unittest.TestCase):
    """Changed paths map to owning packages in both layouts."""

    def test_single_crate_root_sources_gate_the_root_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp), layout="single")
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            (fixture.root / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// tweak\n"
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add",
                 "src/lib.rs"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "src"],
                check=True,
            )
            code, stderr = fixture.run_hook(fixture.push_line_new_branch())
            self.assertEqual(code, 0)
            self.assertIn("gating solo", stderr)
            calls = (fixture.root / "calls.log").read_text(encoding="utf-8")
            self.assertIn("-p solo", calls)


class BlameClassifierTestCase(unittest.TestCase):
    """Failures inside the repo block; environment failures do not."""

    inside_log = (
        "error: something broke\n"
        "  --> {root}/crates/foo/src/lib.rs:1:1\n"
        "error: could not compile `foo`\n"
    )
    outside_log = (
        "error: something broke\n"
        "  --> /home/other/.cargo/registry/src/x.rs:1:1\n"
        "error: could not compile `foreign-crate`\n"
    )

    def _gate(self, fixture: GateFixture, log: str) -> tuple:
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
             "-b", "feat"],
            check=True,
        )
        (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
            "pub fn f() {}\n// tweak\n"
        )
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "add",
             "crates/foo/src/lib.rs"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
             "-m", "src"],
            check=True,
        )
        root = str(fixture.root).replace("\\", "/")
        fixture.set_cargo_behavior(
            "fail-clippy-ours" if "could not compile `foo`" in log else
            "fail-clippy-environment",
        )
        return fixture.run_hook(
            fixture.push_line_new_branch(),
            extra_env={"CARGO_FAIL_LOG": log.format(root=root)},
        )

    def test_clippy_failure_inside_repo_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            code, stderr = self._gate(
                GateFixture(pathlib.Path(temp)), self.inside_log
            )
            self.assertEqual(code, 1)
            self.assertIn("clippy fails", stderr)

    def test_clippy_failure_outside_repo_reports_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            code, stderr = self._gate(
                GateFixture(pathlib.Path(temp)), self.outside_log
            )
            self.assertEqual(code, 0)
            self.assertIn("dependency graph is broken", stderr)

    @unittest.skipUnless(shutil.which("cygpath"), "needs cygpath")
    def test_windows_drive_path_outside_repo_reports_environment(self) -> None:
        """cygpath spells a converted path with an upper-case drive letter
        while the classifier's drive-path case is lower case, so an existing
        registry file outside the repo read as inside and blamed the push.
        The file must exist: cygpath declines a short name for one that
        does not, and the path then never reaches the conversion."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp, \
                tempfile.TemporaryDirectory(prefix="atlas-registry-") as registry:
            source = pathlib.Path(registry).resolve() / "x.rs"
            source.write_text("fn broken() {}\n", encoding="utf-8")
            log = (
                "error: something broke\n"
                f"  --> {str(source).replace(chr(92), '/')}:1:1\n"
                "error: could not compile `foreign-crate`\n"
            )
            code, stderr = self._gate(GateFixture(pathlib.Path(temp)), log)
            self.assertEqual(code, 0, stderr)
            self.assertIn("dependency graph is broken", stderr)


class MissingToolchainTestCase(unittest.TestCase):
    """No cargo on PATH skips the gate loudly instead of failing."""

    def test_missing_cargo_skips_local_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            fixture.set_cargo_behavior("missing")
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// tweak\n"
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add",
                 "crates/foo/src/lib.rs"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "src"],
                check=True,
            )
            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch(),
                extra_env={
                    "PATH": _path_without_cargo(str(fixture.bin)),
                },
            )
            self.assertEqual(code, 0)
            self.assertIn("no cargo toolchain found", stderr)


class DefaultBranchTestCase(unittest.TestCase):
    """The gate follows the remote's default branch, not `main`.

    On a repository whose default branch is not `main` (hephaestus uses
    `master`), a first push has no upstream yet, so `origin/main` resolves
    nothing and the gate used to skip everything -- failing open.
    """

    def test_first_push_on_master_default_gates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(
                pathlib.Path(temp), default_branch="master"
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// tweak\n"
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add",
                 "crates/foo/src/lib.rs"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "src"],
                check=True,
            )
            code, stderr = fixture.run_hook(fixture.push_line_new_branch())
            self.assertEqual(code, 0)
            self.assertIn("gating foo", stderr)


class LockRestoreTestCase(unittest.TestCase):
    """The gate restores the lock byte-for-byte whatever it held."""

    def test_lock_bytes_survive_a_passing_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            lock = fixture.root / "Cargo.lock"
            before = lock.read_bytes()
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// tweak\n"
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add",
                 "crates/foo/src/lib.rs"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "src"],
                check=True,
            )
            code, _ = fixture.run_hook(fixture.push_line_new_branch())
            self.assertEqual(code, 0)
            self.assertEqual(lock.read_bytes(), before)
