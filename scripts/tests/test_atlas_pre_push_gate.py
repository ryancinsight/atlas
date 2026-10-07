#!/usr/bin/env python3
"""Integration tests for the owned member pre-push gate.

`scripts/git-hooks/pre-push` is the single source every member's
`.githooks/pre-push` copies. These tests drive
the script itself in fixture git repositories with stub `cargo`/`lockfile`
tools, so the range logic, the package mapper, and the blame classifier
are verified without a toolchain or network. The stub cargo runs in the
gate's export of the pushed revision, so its package metadata and failure
logs name `@ROOT@`, which it replaces with its own working directory.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import signal
import stat
import subprocess
import tempfile
import threading
import time
import tomllib
import unittest
import weakref

from identity_fixture import PASSTHROUGH_IDENTITY

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1] / "git-hooks" / "pre-push"
)
ZERO = "0" * 40
# Bound on any wait for a hook run; the hooks finish in seconds, so this is
# a backstop that ends a hung run, never a pace the tests rely on.
WATCHDOG_SECONDS = 120

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


# Every external command the hook runs before and inside its lockfile section.
# The interpreter-free PATH is built from these by name, so a command added to
# the hook without being added here fails the test loudly rather than changing
# which branch the test observes.
_HOOK_COMMANDS = (
    "bash",
    "git",
    "seq",
    "sed",
    "grep",
    "awk",
    "cat",
    "head",
    "sort",
    "tr",
    "mktemp",
    "rm",
    "tar",
    "mkdir",
    "mv",
    "touch",
)


def _path_without_python(extra_first: str, root: pathlib.Path) -> str:
    """A PATH carrying the hook's own commands and no python interpreter.

    The hook resolves its repository with git and runs coreutils before it
    searches for an interpreter, so an empty PATH tests the wrong failure --
    but so does dropping every PATH entry that holds a python binary, because
    on Linux that entry is `/usr/bin`, which holds `bash` and the coreutils
    too. Linking the named commands into a fresh directory keeps exactly what
    the hook needs and nothing that would answer its search.

    Windows keeps its interpreter in its own directory, so the filter is
    correct there, and symlink creation needs a privilege the runner may not
    have -- hence the split.
    """
    if os.name == "nt":
        entries = [extra_first]
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            if not entry or entry in entries:
                continue
            probe = pathlib.Path(entry)
            if any(
                (probe / name).exists()
                for name in ("python.exe", "python3.exe", "python", "python3")
            ):
                continue
            entries.append(entry)
        return os.pathsep.join(entries)

    tools = root / "interpreter-free-tools"
    tools.mkdir(exist_ok=True)
    for name in _HOOK_COMMANDS:
        found = shutil.which(name)
        if found is None:
            continue
        link = tools / name
        if not link.exists():
            link.symlink_to(found)
    absent = [name for name in ("bash", "git") if not (tools / name).exists()]
    if absent:
        raise AssertionError(
            f"interpreter-free PATH is missing {absent}; the fixture would test "
            "a missing shell rather than a missing interpreter"
        )
    return os.pathsep.join([extra_first, str(tools)])


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


_FIXTURE_EXCLUDES = "upstream.git/\nbin/\ncalls.log\nlockfile-calls.log\nmetadata-calls.log\n"


def assert_gated_on_the_export(
    test: unittest.TestCase, code: int, stderr: str, fixture: "GateFixture"
) -> None:
    """The package gate built the pushed revision's export, never the checkout.

    Every check before it reads the pushed revision, and so does cargo: it runs
    in an export outside the checkout, whatever branch or dirt the checkout holds.
    """
    test.assertEqual(code, 0, stderr)
    test.assertNotIn("BLOCKED", stderr)
    calls = fixture.calls.read_text(encoding="utf-8") if fixture.calls.is_file() else ""
    test.assertIn("-p foo", calls, "the pushed package was not gated")
    checkout = os.path.normcase(str(fixture.root.resolve()))
    for cwd in (fixture.root / "cwd.log").read_text(encoding="utf-8").split():
        test.assertNotIn(
            checkout, os.path.normcase(str(pathlib.Path(cwd).resolve())),
            "cargo ran in the checkout",
        )


# The stack's lockfile checker, as a stub: it records its arguments where the
# fixture says (`LOCKFILE_CALLS_LOG`) and exits as `LOCKFILE_EXIT` says.
_STACK_LOCKFILE_STUB = (
    "#!/usr/bin/env python3\n"
    "import os, pathlib, sys\n"
    "log = os.environ.get('LOCKFILE_CALLS_LOG')\n"
    "if log:\n"
    "    pathlib.Path(log).write_text(' '.join(sys.argv[1:]) + '\\n')\n"
    "sys.exit(int(os.environ.get('LOCKFILE_EXIT', '0')))\n"
)


# A stack checker that reads the lock beside the manifest it is handed, so a
# verdict names the content that was judged.
_LOCK_READING_CHECKER = (
    "import pathlib, sys\n"
    "manifest = pathlib.Path(sys.argv[sys.argv.index('--manifest-path') + 1])\n"
    "lock = (manifest.parent / 'Cargo.lock').read_text(encoding='utf-8')\n"
    "sys.exit(1 if 'FLATTENED' in lock else 0)\n"
)


class GateFixture:
    """A member-like git repo with a stub toolchain; `in_stack` adds the
    stack's lockfile checker."""

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
        # The hook's temporary root: its reusable export lives there, so a
        # test run never leaves one in the host's temporary directory. It
        # sits outside the fixture, as the host's does outside a stack: an
        # export under the stack would read the stack's own cargo config.
        self.tmp: pathlib.Path = pathlib.Path(tempfile.mkdtemp(prefix="gate-tmp-")).resolve()
        weakref.finalize(self, shutil.rmtree, str(self.tmp), True)
        self.lockfile_calls: pathlib.Path = root / "lockfile-calls.log"
        self.stack: pathlib.Path = root.parent.parent
        self.layout = layout
        _git_init_repo(root)
        # The stub toolchain and its call logs live inside the repository.
        # Excluded from the first commit on, switching the stub's behaviour
        # or logging a call stays fixture plumbing instead of looking like
        # content a test commit might carry.
        _write(root / ".git" / "info" / "exclude", _FIXTURE_EXCLUDES)
        if layout == "crates":
            _write(root / "Cargo.toml", '[workspace]\nmembers = ["crates/foo"]\n')
            _write(
                root / "crates" / "foo" / "Cargo.toml",
                '[package]\nname = "foo"\nversion = "0.1.0"\nedition = "2021"\n',
            )
            _write(root / "crates" / "foo" / "src" / "lib.rs", "pub fn f() {}\n")
        elif layout == "single":
            _write(
                root / "Cargo.toml",
                '[package]\nname = "solo"\nversion = "0.1.0"\nedition = "2021"\n',
            )
            _write(root / "src" / "lib.rs", "pub fn f() {}\n")
        elif layout == "meta":
            for directory in (
                "checkout-path-dependencies",
                "criterion-regression",
                "gitlink-coherence",
                "version-guard",
            ):
                workspace = root / "tools" / directory
                _write(
                    workspace / "Cargo.toml",
                    f'[package]\nname = "{directory}"\nversion = "0.1.0"\nedition = "2024"\n',
                )
                _write(workspace / "Cargo.lock", "# lock\n")
                _write(workspace / "src" / "lib.rs", "pub fn f() {}\n")
        else:
            raise ValueError(f"unknown gate fixture layout {layout}")
        self.set_workspace_packages(
            ["unrelated-member", "foo"]
            if layout == "crates"
            else (["solo"] if layout == "single" else ["tool"])
        )
        if layout != "meta":
            _write(root / "Cargo.lock", "# lock\n")
        # The member carries no lockfile checker: the hook runs the stack's
        # (`install_stack_lockfile`).
        self.set_cargo_behavior("pass")
        _write(
            self.bin / "cargo-nextest",
            "#!/usr/bin/env bash\nexit 0\n",
            executable=True,
        )
        self.cargo_launcher = self.bin / ("cargo.cmd" if os.name == "nt" else "cargo")
        if os.name == "nt":
            _write(
                self.cargo_launcher,
                f'@echo off\r\nbash "{self.bin / "cargo"}" %*\r\n',
            )
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
        # Fixture teardown must not race Git's opportunistic maintenance. The
        # gate exercises several short-lived repositories in parallel, and a
        # background `gc --auto` can still rewrite `.git/objects` while
        # TemporaryDirectory removes it. Disable maintenance in both the
        # repository under test and its local bare remote; this changes no
        # gate behavior, only the fixture's lifetime semantics.
        for repo in (root, root / "upstream.git"):
            subprocess.run(
                ["git", "-C", str(repo), "config", "gc.auto", "0"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "maintenance.auto", "false"],
                check=True,
            )
        subprocess.run(
            ["git", "-C", str(root / "upstream.git"), "config",
             "receive.autogc", "false"],
            check=True,
        )
        # The remote is bare, so it carries no `.git` entry for git to
        # recognise and skip: without this exclude a `git add -A` in a
        # test walks it as ordinary files and indexes the remote's own
        # HEAD, config, hooks and object store into the repository under
        # test. That both feeds the gate a diff of hundreds of files it
        # should never see, and races the push writing those objects --
        # `fatal: unable to stat upstream.git/objects/..` when a loose
        # object is packed away between readdir and stat, which is how it
        # surfaced (a required check, failing on an unrelated pull
        # request). A directory pattern prunes the traversal outright.
        _write(root / ".git" / "info" / "exclude", _FIXTURE_EXCLUDES)
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

    @classmethod
    def in_stack(
        cls,
        stack: pathlib.Path,
        below: tuple = ("repos", "member"),
        **options,
    ) -> "GateFixture":
        """A checkout at `stack/<below>` of a stack whose default carries a
        stub lockfile checker, which is where the hook runs it from."""
        fixture = cls(stack.joinpath(*below), **options)
        fixture.stack = stack
        fixture.install_stack_lockfile()
        return fixture

    def install_stack_lockfile(self, source: str = "") -> None:
        """Publish `source` as the stack's `scripts/lockfile.py` on its default."""
        _write(
            self.stack / "scripts" / "lockfile.py",
            source or _STACK_LOCKFILE_STUB,
            executable=True,
        )
        _publish_stack_scripts(self.stack)

    def retire_stack_lockfile(self) -> None:
        """Remove the checker from the stack's fetched default, as a stack
        default cut before the checker existed lacks it."""
        stack = self.stack
        (stack / "scripts" / "lockfile.py").unlink()
        subprocess.run(
            ["git", "-C", str(stack), *_IDENT, "add", "-A", "scripts"], check=True
        )
        subprocess.run(
            ["git", "-C", str(stack), *_IDENT, "commit", "-q", "-m", "retire"],
            check=True,
        )
        _git(stack, "update-ref", "refs/remotes/origin/main", _git(stack, "rev-parse", "HEAD"))

    def set_workspace_packages(
        self, names: list[str], targets: dict[str, list[dict]] | None = None
    ) -> None:
        """Set the Cargo metadata returned by the fixture toolchain.

        Manifests sit under `@ROOT@`, the directory the stub runs in: the
        gate's export of the pushed revision.
        """
        packages = []
        for name in names:
            manifest = (
                f"@ROOT@/crates/{name}/Cargo.toml"
                if self.layout == "crates"
                else "@ROOT@/Cargo.toml"
            )
            package = {
                "id": f"fixture:{name}",
                "name": name,
                "version": "0.1.0",
                "source": None,
                "manifest_path": manifest,
                "dependencies": [],
            }
            if targets is not None and name in targets:
                package["targets"] = targets[name]
            packages.append(package)
        _write(
            self.bin / "metadata.json",
            json.dumps(
                {
                    "packages": packages,
                    "workspace_members": [package["id"] for package in packages],
                    "workspace_root": "@ROOT@",
                    "target_directory": str(self.stack / "target"),
                    "resolve": {
                        "nodes": [
                            {
                                "id": package["id"],
                                "dependencies": [],
                                "deps": [],
                                "features": [],
                            }
                            for package in packages
                        ]
                    },
                }
            ),
        )

    def set_cargo_behavior(self, mode: str) -> None:
        """Install a stub `cargo`: `pass`, `fail-fmt`, `fail-clippy-ours`,
        `fail-clippy-environment`, `fail-deny`, or `missing` (no stub on PATH).

        A failing step prints `$CARGO_FAIL_LOG`, `@ROOT@` replaced by the
        directory it ran in, supplied by the caller
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
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'pwd >> "$FIXTURE_ROOT/cwd.log"\n'
                'if [ "$1" = "deny" ] && [ "$2" != "--version" ]; then\n'
                '  pwd >> "$FIXTURE_ROOT/deny-cwd.log"\n'
                "fi\nexit 0\n"
            )
        elif mode == "fail-deny":
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'if [ "$1" = "deny" ] && [ "$2" != "--version" ]; then exit 1; fi\n'
                "exit 0\n"
            )
        elif mode == "fail-doc":
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'if [ "$1" = "doc" ]; then\n'
                '  printf "%s\\n" "${CARGO_FAIL_LOG//@ROOT@/$here}" >&2\n'
                "  exit 1\n"
                "fi\nexit 0\n"
            )
        elif mode == "mutate-source-on-doc":
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'pwd >> "$FIXTURE_ROOT/cwd.log"\n'
                'if [ "$1" = "doc" ]; then\n'
                '  printf "\\nmutation\\n" >> "$CARGO_MUTATE_SOURCE"\n'
                "fi\nexit 0\n"
            )
        elif mode == "fmt-by-content":
            # fmt fails exactly when the tree it runs in carries the marker,
            # so a verdict names the content that was judged.
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'pwd >> "$FIXTURE_ROOT/cwd.log"\n'
                'if [ "$1" = "fmt" ] && grep -rqs --include="*.rs" UNFORMATTED .; then exit 1; fi\n'
                'if [ "$1" != "fmt" ]; then\n'
                '  [ -f "$FIXTURE_ROOT/observed-lock" ] || cat Cargo.lock > "$FIXTURE_ROOT/observed-lock"\n'
                '  printf "%s" "${CARGO_TARGET_DIR:-}" > "$FIXTURE_ROOT/observed-target"\n'
                'fi\n'
                "exit 0\n"
            )
        elif mode == "fail-fmt":
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'if [ "$1" = "fmt" ]; then exit 1; fi\nexit 0\n'
            )
        elif mode == "fail-collision":
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'if [ "$1" = "clippy" ]; then\n'
                '  echo "error: package collision in the lockfile: packages foo v0.1.0 '
                '(/stack/repos/foo) and foo v0.1.0 (/stack/worktrees/foo-lane)" >&2\n'
                "  exit 101\n"
                "fi\nexit 0\n"
            )
        elif mode.startswith("fail-clippy"):
            body = (
                'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                'if [ "$1" = "clippy" ]'
                + (' && [[ "$here" = */version-guard ]]'
                   if mode == "fail-clippy-version-guard" else '')
                + '; then\n'
                '  printf "%s\\n" "${CARGO_FAIL_LOG//@ROOT@/$here}" >&2\n'
                "  exit 1\n"
                "fi\nexit 0\n"
            )
        else:
            raise AssertionError(f"unknown cargo mode {mode}")
        _write(
            stub,
            "#!/usr/bin/env bash\n"
            f'FIXTURE_ROOT="{self.root}"\n'
            'here="$(pwd -W 2>/dev/null || pwd)"\n'
            'if [ "$1" = "metadata" ]; then\n'
            '  echo "$@" >> "$FIXTURE_ROOT/metadata-calls.log"\n'
            '  sed "s|@ROOT@|$here|g" "$FIXTURE_ROOT/bin/metadata.json"\n'
            "  exit 0\n"
            "fi\n"
            'if [ "$1" = "doc" ]; then printf "%s" "${RUSTDOCFLAGS:-}" > "$FIXTURE_ROOT/rustdoc-flags.log"; fi\n'
            + body,
            executable=True,
        )

    def add_worktree(self, where: pathlib.Path, branch: str) -> pathlib.Path:
        """A linked worktree of this member at `where` on a new branch, as a
        lane or a harness makes one."""
        where.parent.mkdir(parents=True, exist_ok=True)
        _git(self.root, "worktree", "add", "-q", "-b", branch, str(where), "main")
        return where

    def run_hook(
        self,
        push_lines: str,
        extra_env: dict | None = None,
        cwd: pathlib.Path | None = None,
    ) -> tuple:
        """Run the owned hook script in this fixture, or in `cwd`, a worktree
        of it; return (exit, stderr)."""
        env = dict(os.environ)
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env["CARGO"] = str(self.cargo_launcher)
        env["TMPDIR"] = self.tmp.as_posix()
        env["LOCKFILE_CALLS_LOG"] = str(self.lockfile_calls)
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
            cwd=str(self.root if cwd is None else cwd),
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


def _register_stack(stack: pathlib.Path) -> None:
    """Mark `stack` as an Atlas stack: its `.gitmodules` registers the members
    under `repos/` (`member` when none exists yet), which is how the hook
    recognises a stack and the member a checkout belongs to."""
    repos = stack / "repos"
    names = sorted(entry.name for entry in repos.iterdir() if entry.is_dir()) if repos.is_dir() else []
    _write(
        stack / ".gitmodules",
        "".join(
            f'[submodule "{name}"]\n\tpath = repos/{name}\n\turl = ./{name}\n'
            for name in names or ["member"]
        ),
    )


# The credential scanner a stack publishes when a test does not supply its own:
# the hook refuses a push it could not scan, so every stack that reaches that
# step carries one. This stand-in reports a clean range.
_CLEAN_RANGE_SCANNER = "import sys\nsys.exit(0)\n"

def _seed_scanner(stack: pathlib.Path) -> None:
    """Give the stack a credential scanner unless the test wrote its own."""
    scanner = stack / "scripts" / "atlas-secret-scan.py"
    if not scanner.exists():
        _write(scanner, _CLEAN_RANGE_SCANNER, executable=True)


def _seed_identity(stack: pathlib.Path) -> None:
    """Give valid stack fixtures the command-running identity checker."""
    identity = stack / "scripts" / "atlas-build-identity.py"
    if not identity.exists():
        _write(identity, PASSTHROUGH_IDENTITY, executable=True)


def _stacked_fixture(temp: str, **options: object) -> "GateFixture":
    """A member at `<temp>/repos/member` of a stack that carries the scanner
    and lockfile checkers plus the command-running identity checker."""
    return GateFixture.in_stack(pathlib.Path(temp), **options)


def _publish_stack_scripts(
    stack: pathlib.Path, remove_from_checkout: tuple = ()
) -> None:
    """Commit the stack checkout's `scripts/` and make that commit the stack's
    fetched default, which is where the hook runs stack tools from.

    Names in `remove_from_checkout` then leave the working tree, as they do
    when the stack checkout sits on a branch that predates them.
    """
    _seed_scanner(stack)
    _seed_identity(stack)
    if not (stack / ".git").exists():
        _git_init_repo(stack)
    _register_stack(stack)
    subprocess.run(
        ["git", "-C", str(stack), *_IDENT, "add", ".gitmodules", "scripts"], check=True
    )
    subprocess.run(
        ["git", "-C", str(stack), *_IDENT, "commit", "-q", "--allow-empty",
         "-m", "stack scripts"],
        check=True,
    )
    _git(stack, "update-ref", "refs/remotes/origin/main", _git(stack, "rev-parse", "HEAD"))
    for name in remove_from_checkout:
        (stack / "scripts" / name).unlink()


def _recording_tool(log: pathlib.Path, exit_code: int) -> str:
    """A stack tool that records the path it ran from and its argv, then exits."""
    return (
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        f"with pathlib.Path({str(log)!r}).open('a', encoding='utf-8') as stream:\n"
        "    stream.write(' '.join([__file__, *sys.argv[1:]]) + '\\n')\n"
        f"sys.exit({exit_code})\n"
    )


def _recording_passthrough_identity(log: pathlib.Path) -> str:
    """Record one checker invocation, then run its command with fixture tools."""
    return (
        "import json, pathlib, subprocess, sys\n"
        "argv = sys.argv[1:]\n"
        "cwd = argv[argv.index('--command-cwd') + 1]\n"
        "command = argv[argv.index('--') + 1:]\n"
        f"with pathlib.Path({str(log)!r}).open('a', encoding='utf-8') as stream:\n"
        "    stream.write(json.dumps(command) + '\\n')\n"
        "raise SystemExit(subprocess.run(command, cwd=cwd).returncode)\n"
    )


def _recording_identity_invocation(log: pathlib.Path) -> str:
    """Record a complete checker invocation, then execute its build command."""
    return (
        "import json, pathlib, subprocess, sys\n"
        "argv = sys.argv[1:]\n"
        "root = argv[argv.index('--root') + 1]\n"
        "cwd = argv[argv.index('--command-cwd') + 1]\n"
        "head = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'], "
        "capture_output=True, check=True, text=True).stdout.strip()\n"
        f"with pathlib.Path({str(log)!r}).open('a', encoding='utf-8') as stream:\n"
        "    stream.write(json.dumps({'path': __file__, 'argv': argv, "
        "'root_head': head}) + '\\n')\n"
        "command = argv[argv.index('--') + 1:]\n"
        "raise SystemExit(subprocess.run(command, cwd=cwd).returncode)\n"
    )


def _install_real_identity(stack: pathlib.Path) -> None:
    """Install the production identity CLI and its modules in a fixture stack."""
    source = SCRIPT.parents[1]
    destination = stack / "scripts"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "atlas-build-identity.py", destination)
    shutil.copy2(source / "atlas_claim_log.py", destination)
    for module in source.glob("atlas_build_*.py"):
        shutil.copy2(module, destination)


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

    def test_force_updated_publication_branch_uses_current_default_base(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-force-update-") as temp:
            fixture = _stacked_fixture(temp)
            root = fixture.root
            branch = "ci/sync-stack-hooks"

            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "old-publication"],
                check=True,
            )
            _write(root / "old-hook.txt", "previous published hook\n")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "add", "old-hook.txt"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", "old publication"],
                check=True,
            )
            old_publication = _git(root, "rev-parse", "HEAD")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "push", "-q", "origin",
                 f"{old_publication}:refs/heads/{branch}"],
                check=True,
            )

            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "main"],
                check=True,
            )
            with (root / "Cargo.toml").open("a", encoding="utf-8") as manifest:
                manifest.write("\n# unrelated default-branch update\n")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-am", "default update"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "push", "-q", "origin", "main"],
                check=True,
            )
            subprocess.run(["git", "-C", str(root), "fetch", "-q", "origin"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "remote", "set-head", "origin", "--auto"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "rebuilt",
                 "origin/main"],
                check=True,
            )
            _write(root / "new-hook.txt", "rebuilt hook\n")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "add", "new-hook.txt"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", "rebuilt publication"],
                check=True,
            )
            desired = _git(root, "rev-parse", "HEAD")
            self.assertNotEqual(
                subprocess.run(
                    [
                        "git", "-C", str(root), "merge-base", "--is-ancestor",
                        old_publication, desired,
                    ],
                    capture_output=True,
                ).returncode,
                0,
            )
            push_line = (
                f"refs/heads/{branch} {desired} refs/heads/{branch} {old_publication}\n"
            )

            code, stderr = fixture.run_hook(push_line)

            self.assertEqual(code, 0, stderr)
            self.assertIn("no Cargo.lock or Cargo.toml in the pushed range", stderr)
            self.assertFalse(fixture.lockfile_calls.exists())

    def test_new_branch_manifest_push_runs_lockfile_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
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
            fixture = _stacked_fixture(temp)
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

    def test_merged_default_assets_do_not_expand_the_feature_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), "checkout", "-q", "main"],
                check=True,
            )
            _write(
                fixture.root / "fuzz" / "Cargo.toml",
                '[package]\nname = "consus-fuzz"\nversion = "0.0.0"\n'
                "[workspace]\n",
            )
            _write(fixture.root / "fuzz" / "corpus" / "seed", "seed\n")
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "fuzz"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "default corpus"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "push", "-q",
                 "origin", "HEAD:main"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), "checkout", "-q", "feat"],
                check=True,
            )
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// feature\n"
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-qam",
                 "feature"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "merge", "-q",
                 "--no-edit", "origin/main"],
                check=True,
            )

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 0, stderr)
            self.assertIn("gating foo", stderr)
            calls = fixture.calls.read_text(encoding="utf-8")
            self.assertIn("-p foo", calls)
            self.assertNotIn("consus-fuzz", calls)

    def test_fixture_only_change_gates_its_workspace_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            binary_fixture = (
                fixture.root / "crates" / "foo" / "tests" / "fixtures" / "sample.bin"
            )
            binary_fixture.parent.mkdir(parents=True, exist_ok=True)
            binary_fixture.write_bytes(b"\x00\xff\x80fixture\x00")
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "crates/foo"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "fixture"],
                check=True,
            )

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 0, stderr)
            self.assertIn("gating foo", stderr)
            self.assertIn(
                "-p foo", fixture.calls.read_text(encoding="utf-8")
            )

    def _push_standalone_crate_change(
        self, changed_path: str, package_name: str, cargo_behavior: str
    ) -> tuple:
        """Push one change under an excluded `fuzz` workspace; return the fixture,
        the hook's exit code and its stderr."""
        temp = tempfile.TemporaryDirectory(prefix="atlas-gate-")
        self.addCleanup(temp.cleanup)
        fixture = _stacked_fixture(temp.name)
        _write(
            fixture.root / "fuzz" / "Cargo.toml",
            f'[package]\nname = "{package_name}"\nversion = "0.0.0"\n'
            '[workspace]\n',
        )
        for argv in (
            ["add", "fuzz"],
            ["commit", "-q", "-m", "fuzz workspace"],
            ["push", "-q", "origin", "HEAD:main"],
            ["checkout", "-q", "-b", "feat"],
        ):
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, *argv], check=True
            )
        _write(fixture.root / changed_path, "changed\n")
        for argv in (
            ["add", changed_path],
            ["commit", "-q", "-m", "fuzz input"],
        ):
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, *argv], check=True
            )
        fixture.set_cargo_behavior(cargo_behavior)
        code, stderr = fixture.run_hook(fixture.push_line_new_branch())
        return fixture, code, stderr

    def test_standalone_crate_changes_check_lock_and_format_only(self) -> None:
        """A standalone cargo-fuzz crate cannot be named by a parent `-p`, so the gate
        checks what every host can (its lock resolves, its sources are
        formatted) and leaves the build to CI; the push is not refused."""
        cases = (
            ("fuzz/src/main.rs", "consus-fuzz"),
            ("fuzz/corpus/seed", "consus-fuzz"),
            ("fuzz/src/name_collision.rs", "foo"),
        )
        for changed_path, package_name in cases:
            with self.subTest(changed_path=changed_path, package_name=package_name):
                fixture, code, stderr = self._push_standalone_crate_change(
                    changed_path, package_name, "pass"
                )
                self.assertEqual(code, 0, stderr)
                self.assertIn("standalone crate fuzz/Cargo.toml", stderr)
                calls = fixture.calls.read_text(encoding="utf-8")
                metadata = (fixture.root / "metadata-calls.log").read_text(encoding="utf-8")
                self.assertRegex(metadata, r"metadata --locked --no-deps .*fuzz/Cargo.toml")
                self.assertRegex(calls, r"fmt --manifest-path .*fuzz/Cargo\.toml -- --check")
                self.assertNotIn("-p consus-fuzz", calls)
                self.assertNotIn("clippy", calls)

    def test_standalone_crate_format_failure_refuses_the_push(self) -> None:
        _, code, stderr = self._push_standalone_crate_change(
            "fuzz/src/main.rs", "consus-fuzz", "fail-fmt"
        )
        self.assertEqual(code, 1, stderr)
        self.assertIn("fails for the standalone crate fuzz/Cargo.toml", stderr)

    def test_nested_virtual_workspace_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            _write(
                fixture.root / "tools" / "Cargo.toml",
                '[workspace]\nresolver = "3"\nmembers = []\n',
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "tools/Cargo.toml"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "nested workspace"],
                check=True,
            )

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 1, stderr)
            self.assertIn("excluded from the parent", stderr)
            self.assertIn("tools/Cargo.toml", stderr)

    def test_single_crate_root_sources_gate_the_root_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp, layout="single")
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
            self.assertEqual(code, 0, stderr)
            self.assertIn("gating solo", stderr)
            calls = (fixture.root / "calls.log").read_text(encoding="utf-8")
            self.assertIn("-p solo", calls)
            self.assertTrue(
                any(line.startswith("doc --no-deps ") and line.endswith(" --locked -p solo")
                    for line in calls.splitlines()),
                calls,
            )

    def _commit_paths_on_a_branch(self, fixture: "GateFixture", files: dict[str, str]) -> None:
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q", "-b", "feat"],
            check=True,
        )
        for relative, text in files.items():
            _write(fixture.root / relative, text)
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", relative], check=True
            )
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q", "-m", "paths"],
            check=True,
        )

    def test_hook_and_ci_definitions_alone_gate_no_package(self) -> None:
        """A single-package repository has no package dir above `.githooks/`.

        The root package used to own every path outside a sub-package, so a
        push that only synced the hook ran the whole package gate and queued
        behind every peer's build lease.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp, layout="single")
            self._commit_paths_on_a_branch(
                fixture,
                {
                    ".githooks/pre-push": "#!/bin/sh\n",
                    ".github/workflows/ci.yml": "name: ci\n",
                },
            )

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 0, stderr)
            self.assertIn("local gate not needed", stderr)
            calls = fixture.calls.read_text(encoding="utf-8") if fixture.calls.is_file() else ""
            self.assertNotIn("-p solo", calls)

    def test_a_root_readme_still_gates_the_root_package(self) -> None:
        """A README can be `include_str!`-ed into the crate docs, so it stays an input."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp, layout="single")
            self._commit_paths_on_a_branch(
                fixture,
                {".githooks/pre-push": "#!/bin/sh\n", "README.md": "# solo\n"},
            )

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 0, stderr)
            self.assertIn("gating solo", stderr)


class MetaRootCargoGateTestCase(unittest.TestCase):
    """The Atlas root owns independent Cargo workspaces below ``tools/``."""

    workspaces = (
        "checkout-path-dependencies",
        "criterion-regression",
        "gitlink-coherence",
        "version-guard",
    )

    def _fixture(self, temp: str) -> tuple[GateFixture, pathlib.Path, pathlib.Path]:
        stack = pathlib.Path(temp)
        fixture = GateFixture(stack, layout="meta")
        fixture.stack = stack
        metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
        metadata["target_directory"] = str(stack / "target")
        _write(fixture.bin / "metadata.json", json.dumps(metadata))
        content_log = stack / "content-gates.log"
        identity_log = stack / "identity-gates.log"
        _write(stack / "scripts" / "lockfile.py", _STACK_LOCKFILE_STUB, executable=True)
        _write(
            stack / "scripts" / "atlas-artifact-budget.py",
            _recording_tool(content_log, 0),
            executable=True,
        )
        _write(
            stack / "scripts" / "atlas-secret-scan.py",
            _recording_tool(content_log, 0),
            executable=True,
        )
        _write(
            stack / "scripts" / "atlas-conformance.py",
            _recording_tool(content_log, 0),
            executable=True,
        )
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            _recording_identity_invocation(identity_log),
            executable=True,
        )
        _write(stack / "scripts" / "atlas_stack.py", "ROOT = None  # honours ATLAS_STACK_ROOT\n")
        _publish_stack_scripts(stack)
        subprocess.run(
            ["git", "-C", str(stack), *_IDENT, "checkout", "-q", "-b", "feat"],
            check=True,
        )
        return fixture, content_log, identity_log

    @staticmethod
    def _commit(fixture: GateFixture, *paths: str) -> None:
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "add", "--", *paths], check=True
        )
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q", "-m", "change"],
            check=True,
        )

    def _point_branch_at_unique_tree(
        self, fixture: GateFixture, with_parent: bool
    ) -> pathlib.Path:
        _write(fixture.root / "changed.txt", "changed\n")
        self._commit(fixture, "changed.txt")
        tree = _git(fixture.root, "rev-parse", "HEAD^{tree}")
        if not with_parent:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(fixture.root),
                    *_IDENT,
                    "commit-tree",
                    tree,
                    "-F",
                    "-",
                ],
                input=b"orphan\n",
                check=True,
                capture_output=True,
            )
            revision = result.stdout.decode("ascii").strip()
            subprocess.run(
                ["git", "-C", str(fixture.root), "update-ref", "refs/heads/feat", revision],
                check=True,
            )
        object_path = fixture.root / ".git" / "objects" / tree[:2] / tree[2:]
        self.assertTrue(object_path.is_file())
        return object_path

    def test_changed_path_discovery_failures_block_before_native_gates(self) -> None:
        for label, with_parent in (("range-diff", True), ("whole-revision", False)):
            with self.subTest(discovery=label), tempfile.TemporaryDirectory(
                prefix="atlas-meta-gate-"
            ) as temp:
                fixture, content_log, identity_log = self._fixture(temp)
                _write(
                    fixture.stack / "scripts" / "atlas-conformance.py",
                    "import atexit, os, pathlib, stat\n"
                    "def remove_object():\n"
                    "    path = pathlib.Path(os.environ['REMOVE_OBJECT'])\n"
                    "    path.chmod(path.stat().st_mode | stat.S_IWRITE)\n"
                    "    path.unlink()\n"
                    "atexit.register(remove_object)\n"
                    + _recording_tool(content_log, 0),
                    executable=True,
                )
                _publish_stack_scripts(fixture.stack)
                object_path = self._point_branch_at_unique_tree(fixture, with_parent)

                code, stderr = fixture.run_hook(
                    fixture.push_line_new_branch(),
                    {"REMOVE_OBJECT": str(object_path)},
                )

                self.assertEqual(code, 1, stderr)
                self.assertIn("BLOCKED -- could not discover", stderr)
                self.assertNotIn("native gate not applicable", stderr)
                self.assertEqual(
                    len(content_log.read_text(encoding="utf-8").splitlines()), 3
                )
                self.assertFalse(identity_log.exists())
                self.assertFalse(fixture.calls.exists())

    def test_content_only_root_change_runs_content_gates_without_cargo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-meta-gate-") as temp:
            fixture, content_log, identity_log = self._fixture(temp)
            _write(fixture.root / "README.md", "# changed\n")
            self._commit(fixture, "README.md")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 0, stderr)
            self.assertIn("native gate not applicable", stderr)
            self.assertEqual(len(content_log.read_text(encoding="utf-8").splitlines()), 3)
            self.assertFalse(identity_log.exists())
            self.assertFalse(fixture.calls.exists())

    def test_nested_workspace_uses_its_manifest_cwd_and_complete_sequence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-meta-gate-") as temp:
            fixture, _, identity_log = self._fixture(temp)
            source = fixture.root / "tools" / "version-guard" / "src" / "lib.rs"
            source.write_text("pub fn f() {}\n// changed\n", encoding="utf-8")
            self._commit(fixture, "tools/version-guard/src/lib.rs")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 0, stderr)
            self.assertIn("gating tool", stderr)
            invocation = json.loads(identity_log.read_text(encoding="utf-8").splitlines()[0])
            argv = invocation["argv"]
            manifest = pathlib.Path(argv[argv.index("--manifest") + 1])
            command_cwd = pathlib.Path(argv[argv.index("--command-cwd") + 1])
            self.assertEqual(manifest.parent, command_cwd)
            self.assertEqual(manifest.parent.name, "version-guard")
            self.assertEqual(invocation["root_head"], _git(fixture.root, "rev-parse", "feat"))
            calls = fixture.calls.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(line.startswith("clippy ") for line in calls), calls)
            self.assertTrue(any(line.startswith("nextest run ") for line in calls), calls)
            self.assertTrue(any(line.startswith("doc ") for line in calls), calls)

    def test_root_build_inputs_gate_all_four_workspaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-meta-gate-") as temp:
            fixture, _, identity_log = self._fixture(temp)
            _write(fixture.root / ".cargo" / "config.toml", "[build]\nincremental = false\n")
            self._commit(fixture, ".cargo/config.toml")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 0, stderr)
            invocations = [json.loads(line) for line in identity_log.read_text(encoding="utf-8").splitlines()]
            manifests = {
                pathlib.Path(item["argv"][item["argv"].index("--manifest") + 1]).parent.name
                for item in invocations
            }
            self.assertEqual(manifests, set(self.workspaces))

    def test_two_workspaces_run_before_a_later_stage_failure_propagates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-meta-gate-") as temp:
            fixture, _, identity_log = self._fixture(temp)
            fixture.set_cargo_behavior("fail-clippy-version-guard")
            for workspace in ("checkout-path-dependencies", "version-guard"):
                source = fixture.root / "tools" / workspace / "src" / "lib.rs"
                source.write_text(f"pub fn f() {{}}\n// {workspace}\n", encoding="utf-8")
            self._commit(
                fixture,
                "tools/checkout-path-dependencies/src/lib.rs",
                "tools/version-guard/src/lib.rs",
            )

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch(),
                {"CARGO_FAIL_LOG": "error: failed\n  --> @ROOT@/src/lib.rs:1:1"},
            )

            self.assertEqual(code, 1)
            self.assertIn("clippy fails for tool", stderr)
            invocations = [json.loads(line) for line in identity_log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(invocations), 2)
            self.assertEqual(
                [
                    pathlib.Path(item["argv"][item["argv"].index("--manifest") + 1]).parent.name
                    for item in invocations
                ],
                ["checkout-path-dependencies", "version-guard"],
            )

    def test_removed_selected_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-meta-gate-") as temp:
            fixture, _, identity_log = self._fixture(temp)
            manifest = fixture.root / "tools" / "version-guard" / "Cargo.toml"
            manifest.unlink()
            self._commit(fixture, "tools/version-guard/Cargo.toml")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            self.assertEqual(code, 1)
            self.assertIn("selected Cargo workspace manifest tools/version-guard/Cargo.toml is missing", stderr)
            self.assertFalse(identity_log.exists())

    def test_malformed_selected_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-meta-gate-") as temp:
            fixture, _, identity_log = self._fixture(temp)
            manifest = fixture.root / "tools" / "version-guard" / "Cargo.toml"
            manifest.write_text("[package\n", encoding="utf-8")
            self._commit(fixture, "tools/version-guard/Cargo.toml")
            fixture.set_cargo_behavior("missing")
            fixture.cargo_launcher.unlink()
            cargo = shutil.which("cargo")
            self.assertIsNotNone(cargo)

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch(), {"CARGO": str(cargo)}
            )

            self.assertEqual(code, 1, stderr)
            self.assertIn("cargo metadata could not establish testable packages", stderr)
            self.assertFalse(identity_log.exists())


class BlameClassifierTestCase(unittest.TestCase):
    """Failures inside the repo block; identity keeps environment failures unverified."""

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
        fixture.set_cargo_behavior(
            "fail-clippy-ours" if "could not compile `foo`" in log else
            "fail-clippy-environment",
        )
        return fixture.run_hook(
            fixture.push_line_new_branch(),
            extra_env={"CARGO_FAIL_LOG": log.format(root="@ROOT@")},
        )

    def test_rustdoc_failure_inside_repo_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
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
            fixture.set_cargo_behavior("fail-doc")
            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch(),
                extra_env={"CARGO_FAIL_LOG": self.inside_log.format(root="@ROOT@")},
            )
            self.assertEqual(code, 1, stderr)
            self.assertIn("rustdoc fails for", stderr)

    def test_clippy_failure_inside_repo_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            code, stderr = self._gate(
                _stacked_fixture(temp), self.inside_log
            )
            self.assertEqual(code, 1)
            self.assertIn("clippy fails", stderr)

    def test_clippy_failure_outside_repo_reports_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            code, stderr = self._gate(
                _stacked_fixture(temp), self.outside_log
            )
            self.assertEqual(code, 1)
            self.assertIn("dependency graph is broken", stderr)
            self.assertIn("source identity did not verify", stderr)

    def test_locked_metadata_failure_reports_the_overlay_environment(self) -> None:
        log = (
            "error: cargo metadata failed for Cargo.toml: cannot update the lock file "
            "because --locked was passed\n"
        )
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            code, stderr = self._gate(_stacked_fixture(temp), log)
        self.assertEqual(code, 1, stderr)
        self.assertIn("dependency graph is broken", stderr)
        self.assertIn("source identity did not verify", stderr)

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
            code, stderr = self._gate(_stacked_fixture(temp), log)
            self.assertEqual(code, 1, stderr)
            self.assertIn("dependency graph is broken", stderr)
            self.assertIn("source identity did not verify", stderr)


class MissingToolchainTestCase(unittest.TestCase):
    """No cargo on PATH skips the gate loudly instead of failing."""

    def test_missing_cargo_skips_local_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
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


class FixtureRemoteTestCase(unittest.TestCase):
    """The fixture's own remote is not content of the repository under test.

    `upstream.git` is bare, so it carries no `.git` entry for git to
    recognise and skip, and it sits inside the work tree. Before the
    exclude, a `git add -A` indexed the remote's HEAD, config, hooks and
    object store -- every gate test then ran against a diff of hundreds
    of files the gate should never see, and the traversal raced the push
    writing those objects (`fatal: unable to stat
    upstream.git/objects/..`), which is how it surfaced.
    """

    def test_add_all_does_not_index_the_bare_remote(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "-A"],
                check=True,
            )
            tracked = subprocess.run(
                ["git", "-C", str(fixture.root), "ls-files"],
                capture_output=True, text=True, check=True,
            ).stdout.splitlines()

        remote = [f for f in tracked if f.startswith("upstream.git/")]
        self.assertEqual(
            remote, [],
            "the fixture's remote is infrastructure, not repository content",
        )
        self.assertTrue(tracked, "the repository under test still has content")


class SafetyRatchetTestCase(unittest.TestCase):
    """The member's SAFETY ratchet runs in the local gate, as CI runs it.

    apollo#397 passed this gate and failed CI's workspace job on the ratchet:
    nothing local ran it, so CI discovered what the gate should have.
    """

    def _push_source_change(self, ratchet_exit: int | None) -> tuple:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            if ratchet_exit is not None:
                _write(
                    fixture.root / "scripts" / "safety_ratchet.py",
                    "#!/usr/bin/env python3\n"
                    "import pathlib, sys\n"
                    "assert sys.argv[1:] == ['check'], sys.argv\n"
                    f"pathlib.Path({str(fixture.root / 'ratchet-calls.log')!r}).write_text('called')\n"
                    f"sys.exit({ratchet_exit})\n",
                    executable=True,
                )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                 "-b", "feat"],
                check=True,
            )
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// tweak\n"
            )
            tracked = ["crates"] + (["scripts"] if ratchet_exit is not None else [])
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", *tracked],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                 "-m", "src"],
                check=True,
            )
            code, stderr = fixture.run_hook(fixture.push_line_new_branch())
            ran = (fixture.root / "ratchet-calls.log").is_file()
            calls = fixture.calls.read_text() if fixture.calls.is_file() else ""
            return code, stderr, ran, calls

    def test_a_failing_ratchet_refuses_the_push_before_compiling(self) -> None:
        code, stderr, ran, calls = self._push_source_change(ratchet_exit=1)
        self.assertTrue(ran, "the ratchet was not invoked")
        self.assertEqual(code, 1)
        self.assertIn("the SAFETY ratchet fails", stderr)
        self.assertNotIn("clippy", calls, "the text scan gates before the compile steps")

    def test_a_passing_ratchet_continues_to_the_compile_steps(self) -> None:
        code, stderr, ran, calls = self._push_source_change(ratchet_exit=0)
        self.assertTrue(ran, "the ratchet was not invoked")
        self.assertEqual(code, 0, stderr)
        self.assertIn("clippy", calls)

    def test_a_member_without_the_ratchet_is_not_gated_on_it(self) -> None:
        code, stderr, ran, calls = self._push_source_change(ratchet_exit=None)
        self.assertFalse(ran)
        self.assertEqual(code, 0, stderr)
        self.assertNotIn("SAFETY ratchet", stderr)


class LockRevisionTestCase(unittest.TestCase):
    """The lock is checked on the pushed revision, not the working tree."""

    def test_a_dirty_working_lock_does_not_refuse_a_clean_push(self) -> None:
        """An overlay-flattened working lock is not the push; its verdict is not asked."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            push_line = UnverifiableLockTestCase()._branch_touching_the_lock(fixture)
            (fixture.root / "Cargo.lock").write_text("# flattened by the overlay\n")
            code, stderr = fixture.run_hook(push_line, {"SKIP_LOCAL_GATE": "1"})
            self.assertEqual(code, 0, stderr)
            self.assertTrue(fixture.lockfile_calls.is_file())
            self.assertEqual(
                (fixture.root / "Cargo.lock").read_text(), "# flattened by the overlay\n"
            )

    def test_the_pushed_lock_is_the_one_checked(self) -> None:
        """A failing checker refuses even when the working tree is clean of the change."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            push_line = UnverifiableLockTestCase()._branch_touching_the_lock(fixture)
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q", "main"],
                check=True,
            )
            code, stderr = fixture.run_hook(
                push_line, {"SKIP_LOCAL_GATE": "1", "LOCKFILE_EXIT": "1"}
            )
            self.assertNotEqual(code, 0)
            self.assertIn("does not resolve under --locked", stderr)
            sha = push_line.split()[1]
            self.assertIn(sha, stderr)


class ArtifactBudgetRevisionTestCase(unittest.TestCase):
    """The budget check judges the pushed tip, not the checkout's `HEAD`.

    A shared tree checked out on a peer's branch carried a board over budget;
    the hook passed `--rev HEAD` and refused an unrelated plumbing push whose
    own board was within budget.
    """

    def test_budget_checks_the_pushed_tip_not_head(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack = pathlib.Path(temp)
            fixture = GateFixture(stack / "repos" / "member")
            log = stack / "budget-args.log"
            _write(
                stack / "scripts" / "atlas-artifact-budget.py",
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                f"pathlib.Path({str(log)!r}).write_text(' '.join(sys.argv[1:]))\n",
                executable=True,
            )
            _publish_stack_scripts(stack)
            root = fixture.root
            base = _git(root, "rev-parse", "HEAD")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "feat"],
                check=True,
            )
            (root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// pushed\n"
            )
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-am", "pushed"],
                check=True,
            )
            pushed = _git(root, "rev-parse", "feat")
            # The checkout moves to a different branch, as a peer's would.
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "peer", base],
                check=True,
            )
            (root / "README.md").write_text("peer\n")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "add", "README.md"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", "peer"],
                check=True,
            )
            self.assertNotEqual(_git(root, "rev-parse", "HEAD"), pushed)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            assert_gated_on_the_export(self, code, stderr, fixture)
            args = log.read_text().split()
            self.assertEqual(args[args.index("--rev") + 1], pushed)
            self.assertEqual(args[args.index("--base") + 1], base)


class SecretScanTestCase(unittest.TestCase):
    """The credential scan judges the pushed range and blocks on a finding."""

    def _stack(self, temp: str, exit_code: int) -> tuple:
        stack = pathlib.Path(temp)
        fixture = GateFixture(stack / "repos" / "member")
        log = stack / "secret-args.log"
        _write(
            stack / "scripts" / "atlas-secret-scan.py",
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            f"pathlib.Path({str(log)!r}).write_text(' '.join(sys.argv[1:]))\n"
            f"sys.exit({exit_code})\n",
            executable=True,
        )
        _publish_stack_scripts(stack)
        root = fixture.root
        base = _git(root, "rev-parse", "HEAD")
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "feat"], check=True
        )
        (root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn f() {}\n// pushed\n")
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "commit", "-q", "-am", "pushed"], check=True
        )
        return fixture, log, base, _git(root, "rev-parse", "feat")

    def test_scan_runs_on_the_pushed_range(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, base, pushed = self._stack(temp, 0)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            self.assertEqual(code, 0, stderr)
            args = log.read_text().split()
            self.assertEqual(args[args.index("--rev") + 1], pushed)
            self.assertEqual(args[args.index("--base") + 1], base)

    def test_a_finding_blocks_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, _, _, _ = self._stack(temp, 1)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            self.assertEqual(code, 1)
            self.assertIn("adds a credential", stderr)


class DefaultBranchTestCase(unittest.TestCase):
    """The gate follows the remote's default branch, not `main`.

    On a repository whose default branch is not `main` (hephaestus uses
    `master`), a first push has no upstream yet, so `origin/main` resolves
    nothing and the gate used to skip everything -- failing open.
    """

    def test_first_push_on_master_default_gates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp, default_branch="master")
            metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
            metadata["target_directory"] = str(fixture.stack / "target")
            _write(fixture.bin / "metadata.json", json.dumps(metadata))
            _write(
                fixture.stack / "scripts" / "atlas-build-identity.py",
                PASSTHROUGH_IDENTITY,
            )
            _publish_stack_scripts(fixture.stack)
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
            fixture = _stacked_fixture(temp)
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


class UnverifiableLockTestCase(unittest.TestCase):
    """A lockfile guard that cannot run must refuse, not announce and pass.

    Both arms previously printed their reason and exited 0, which is the
    absence of the guard with a message in front of it: the push carried an
    unverified lock exactly as if no hook were installed, and the line
    scrolled past in the push output.
    """

    def _branch_touching_the_lock(
        self, fixture: GateFixture, drop_checker: bool = False
    ) -> str:
        """A never-pushed branch whose range changes `Cargo.lock`.

        The lockfile section is skipped when the range touches no manifest and
        no lock, so a fixture that does not commit one tests nothing. The hook
        runs the stack's checker from its fetched default, so `drop_checker`
        removes it from there, as a default cut before the checker lacks it.
        """
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
             "-b", "feat"],
            check=True,
        )
        (fixture.root / "Cargo.lock").write_text("# lock\n# touched\n")
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "add", "Cargo.lock"],
            check=True,
        )
        if drop_checker:
            fixture.retire_stack_lockfile()
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
             "-m", "lock"],
            check=True,
        )
        return fixture.push_line_new_branch()

    def test_absent_checker_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            push_line = self._branch_touching_the_lock(fixture, drop_checker=True)
            code, stderr = fixture.run_hook(push_line)
            self.assertNotEqual(code, 0)
            self.assertIn("carry no lockfile.py", stderr)
            self.assertNotIn("SKIP_LOCKFILE_CHECK", stderr)

    def test_absent_interpreter_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            push_line = self._branch_touching_the_lock(fixture)
            # `PYTHON=""` forces the hook's own search, and a PATH holding
            # only the fixture's stub bin makes that search fail. An
            # explicit-but-absent interpreter would instead fall through to
            # the checker invocation and fail there, testing the wrong branch.
            code, stderr = fixture.run_hook(
                push_line,
                extra_env={
                    "PYTHON": "",
                    "PATH": _path_without_python(str(fixture.bin), fixture.root),
                },
            )
            self.assertNotEqual(code, 0)
            self.assertIn("no python interpreter found", stderr)
            self.assertNotIn("SKIP_LOCKFILE_CHECK", stderr)

    def test_skip_variable_cannot_hide_checker_failures(self) -> None:
        """`SKIP_LOCKFILE_CHECK=1` no longer hides an absent checker.

        The recorded reason for routine `SKIP_LOCKFILE_CHECK=1` use -- an
        overlay-flattened working-tree lock the archive-based check never saw
        anyway -- is gone (2026 stack-hook revision). coeus's checker contract
        (scripts/tests/test_hooks.py::
        test_skip_variable_cannot_hide_checker_failures) requires that no
        variable can hide a checker failure; this pins the same guarantee
        here so the two do not drift apart again.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            push_line = self._branch_touching_the_lock(fixture, drop_checker=True)
            code, stderr = fixture.run_hook(
                push_line, extra_env={"SKIP_LOCKFILE_CHECK": "1"}
            )
            self.assertNotEqual(code, 0, stderr)
            self.assertIn("SKIP_LOCKFILE_CHECK is no longer honoured", stderr)
            self.assertIn("carry no lockfile.py", stderr)

    def test_skip_variable_cannot_hide_a_failing_lock(self) -> None:
        """A lock the checker rejects still refuses the push under the skip var."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            push_line = self._branch_touching_the_lock(fixture)
            code, stderr = fixture.run_hook(
                push_line,
                extra_env={"SKIP_LOCKFILE_CHECK": "1", "LOCKFILE_EXIT": "1"},
            )
            self.assertNotEqual(code, 0, stderr)
            self.assertIn("SKIP_LOCKFILE_CHECK is no longer honoured", stderr)
            self.assertIn("does not resolve under --locked", stderr)


class StackLockfileCheckerTestCase(unittest.TestCase):
    """The lockfile stage runs the stack's checker; a member carries none."""

    def _push(self, fixture: GateFixture, **env: str) -> tuple:
        push_line = UnverifiableLockTestCase()._branch_touching_the_lock(fixture)
        return fixture.run_hook(push_line, {"SKIP_LOCAL_GATE": "1", **env})

    def test_a_member_without_a_lockfile_copy_passes_the_lockfile_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            self.assertFalse((fixture.root / "scripts" / "lockfile.py").exists())
            code, stderr = self._push(fixture)
            self.assertEqual(code, 0, stderr)
            arguments = fixture.lockfile_calls.read_text(encoding="utf-8").split()
            self.assertEqual(arguments[0], "--check")
            self.assertEqual(arguments[1], "--manifest-path")
            manifest = pathlib.Path(arguments[2])
            self.assertEqual(manifest.name, "Cargo.toml")
            self.assertNotIn(
                os.path.normcase(str(fixture.root.resolve())),
                os.path.normcase(str(manifest.resolve())),
                "the manifest is the export's, never the checkout's",
            )

    def test_a_lock_the_stack_checker_rejects_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            code, stderr = self._push(fixture, LOCKFILE_EXIT="1")
            self.assertEqual(code, 1, stderr)
            self.assertIn("does not resolve under --locked", stderr)
            self.assertIn("scripts/lockfile.py --regenerate --manifest-path Cargo.toml", stderr)

    def test_a_member_copy_is_never_the_checker_that_runs(self) -> None:
        """A copy that accepts every lock cannot overrule the stack's verdict."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            _write(
                fixture.root / "scripts" / "lockfile.py",
                "import sys\nsys.exit(0)\n",
            )
            _commit_all(fixture.root, "a member copy")
            code, stderr = self._push(fixture, LOCKFILE_EXIT="1")
            self.assertEqual(code, 1, stderr)
            self.assertIn("does not resolve under --locked", stderr)

    def test_a_clone_outside_a_stack_says_the_lock_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            code, stderr = self._push(fixture)
            # The lock stage passes a clone with no stack and says so; the
            # credential stage, which has no scanner to run, refuses the push.
            self.assertEqual(code, 1, stderr)
            self.assertIn("no Atlas stack above this clone", stderr)
            self.assertIn("not verified here", stderr)
            self.assertIn("credential scanner is not reachable from this clone", stderr)
            self.assertNotIn("lockfile-guard", stderr)
            self.assertFalse(fixture.lockfile_calls.exists())

    def test_a_stack_with_no_fetched_default_refuses_the_push(self) -> None:
        """Inside a stack the checker is owed: a stack with neither
        `origin/HEAD` nor `origin/main` is not a clone outside any stack."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            _git(fixture.stack, "update-ref", "-d", "refs/remotes/origin/main")
            code, stderr = self._push(fixture)
            self.assertEqual(code, 1, stderr)
            self.assertIn("neither origin/HEAD nor origin/main", stderr)
            self.assertNotIn("not verified here", stderr)
            self.assertFalse(fixture.lockfile_calls.exists())

    def _lane_push(self, fixture: GateFixture, lane: pathlib.Path, **env: str) -> tuple:
        """Push a lock-changing branch from the linked worktree `lane`."""
        branch = f"feat-{lane.name}"
        _git(lane, "switch", "-q", "-c", branch)
        (lane / "Cargo.lock").write_text("# lock\n# touched\n", encoding="utf-8")
        sha = _commit_all(lane, "lock")
        push_line = f"refs/heads/{branch} {sha} refs/heads/{branch} {ZERO}\n"
        return fixture.run_hook(push_line, {"SKIP_LOCAL_GATE": "1", **env}, cwd=lane)

    def test_a_lane_and_a_harness_worktree_are_inside_their_members_stack(self) -> None:
        """A harness worktree sits below a member, a lane directly below the
        stack; neither is two levels down, and both belong to the member whose
        object store they share."""
        for where in (
            ("worktrees", "member-lane"),
            ("repos", "member", ".claude", "worktrees", "lane"),
        ):
            with self.subTest(where=where):
                with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
                    fixture = GateFixture.in_stack(pathlib.Path(temp))
                    lane = fixture.add_worktree(
                        fixture.stack.joinpath(*where), f"base-{where[-1]}"
                    )
                    code, stderr = self._lane_push(fixture, lane, LOCKFILE_EXIT="1")
                    self.assertEqual(code, 1, stderr)
                    self.assertIn("does not resolve under --locked", stderr)
                    self.assertTrue(fixture.lockfile_calls.exists())

    def test_a_gitmodules_planted_in_a_member_does_not_capture_its_worktrees(self) -> None:
        """A harness worktree below a member would meet the member's own
        `.gitmodules` first; the stack that runs is the one that registers
        the member."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            _write(
                fixture.root / ".gitmodules",
                '[submodule "x"]\n\tpath = repos/x\n\turl = ./x\n',
            )
            _commit_all(fixture.root, "planted")
            lane = fixture.add_worktree(
                fixture.root / ".claude" / "worktrees" / "lane", "base-lane"
            )
            code, stderr = self._lane_push(fixture, lane, LOCKFILE_EXIT="1")
            self.assertEqual(code, 1, stderr)
            self.assertIn("does not resolve under --locked", stderr)
            self.assertNotIn("carry no lockfile.py", stderr)

    def test_a_directory_that_is_not_a_repository_root_is_not_a_stack(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack = pathlib.Path(temp)
            _write(
                stack / ".gitmodules",
                '[submodule "member"]\n\tpath = repos/member\n\turl = ./member\n',
            )
            fixture = GateFixture(stack / "repos" / "member")
            code, stderr = self._push(fixture)
            self.assertEqual(code, 1, stderr)
            self.assertIn("no Atlas stack above this clone", stderr)
            self.assertIn("credential scanner is not reachable from this clone", stderr)

    def test_only_members_registered_under_repos_make_a_stack(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp), below=("vendor", "member"))
            _write(
                fixture.stack / ".gitmodules",
                '[submodule "member"]\n\tpath = vendor/member\n\turl = ./member\n',
            )
            _git(fixture.stack, "add", ".gitmodules")
            _git(fixture.stack, "commit", "-q", "-m", "vendor only")
            code, stderr = self._push(fixture)
            self.assertEqual(code, 1, stderr)
            self.assertIn("no Atlas stack above this clone", stderr)
            self.assertIn("credential scanner is not reachable from this clone", stderr)

    def _distrusting_environment(self, directory: pathlib.Path) -> dict:
        """Git as it behaves when another account owns every checkout and only
        what the hook itself trusts is readable: no global or system config (a
        user's `safe.directory = *` would hide the case)."""
        empty = directory / "empty.gitconfig"
        empty.write_text("", encoding="utf-8")
        return {
            "GIT_TEST_ASSUME_DIFFERENT_OWNER": "1",
            "GIT_CONFIG_GLOBAL": str(empty),
            "GIT_CONFIG_NOSYSTEM": "1",
        }

    def test_a_stack_git_cannot_read_refuses_instead_of_passing_as_no_stack(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            code, stderr = self._push(
                fixture, **self._distrusting_environment(pathlib.Path(temp))
            )
            self.assertEqual(code, 1, stderr)
            self.assertIn("registers members but git cannot read it", stderr)
            self.assertIn("safe.directory", stderr)
            self.assertNotIn("no Atlas stack above this clone", stderr)
            # Other git calls under the same distrust fail on their own, so the
            # refusal is the locator's only if the run stops there.
            self.assertNotIn("could not export", stderr)
            self.assertFalse(fixture.lockfile_calls.exists())

    def _unmatched_checkout(self, temp: str) -> GateFixture:
        """A clone inside a stack that registers a member on disk, which is not
        this clone: no registered member shares its object store."""
        stack = pathlib.Path(temp)
        GateFixture(stack / "repos" / "other")
        fixture = GateFixture.in_stack(stack, below=("scratch", "member"))
        return fixture

    def test_a_clone_the_stack_does_not_register_is_named_not_gated(self) -> None:
        """The stack names exactly its members and does not name this clone, so no
        lockfile checker is owed to it: the lock stage passes it with a message
        that says a stack is above it and does not register it, never that no
        stack is, and claims nothing about CI. A lock that gets through meets
        the `--locked` CI jobs and is repaired by regenerating it, where a
        credential, whose push cannot be taken back, is not: the credential
        stage refuses the push, saying why. The registered member, or a lane of
        it, is where the push is checked."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = self._unmatched_checkout(temp)
            code, stderr = self._push(fixture)
            self.assertEqual(code, 1, stderr)
            self.assertIn("inside the Atlas stack at", stderr)
            self.assertIn("not one of its registered members", stderr)
            self.assertIn("lockfile checker is not used", stderr)
            self.assertIn("BLOCKED -- inside the Atlas stack at", stderr)
            self.assertIn("credential scanner is not used", stderr)
            self.assertNotIn("no Atlas stack above this clone", stderr)
            self.assertNotIn("--locked CI", stderr)
            self.assertFalse(fixture.lockfile_calls.exists())

    def test_a_candidate_stack_inside_a_repository_git_cannot_read_is_refused(self) -> None:
        """The superproject query prints nothing for a candidate whose
        enclosing repository git cannot read, as it does for one with none, so
        a member carrying its own `.gitmodules` would be taken for the stack and
        its own checker run. An unreadable enclosing repository is unknown, and
        unknown refuses."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            _write(
                fixture.root / ".gitmodules",
                '[submodule "y"]\n\tpath = repos/y\n\turl = ./y\n',
            )
            _commit_all(fixture.root, "planted")
            _git(fixture.stack, "add", "repos/member")
            _git(fixture.stack, "commit", "-q", "-m", "register the member")
            fixture.add_worktree(fixture.root / "repos" / "y", "base-y")
            lane = fixture.add_worktree(
                fixture.root / ".claude" / "worktrees" / "lane", "base-lane"
            )
            trusting_the_member = pathlib.Path(temp) / "trusting.gitconfig"
            trusting_the_member.write_text(
                f"[safe]\n\tdirectory = {fixture.root.resolve().as_posix()}\n",
                encoding="utf-8",
            )
            environment = self._distrusting_environment(pathlib.Path(temp))
            environment["GIT_CONFIG_GLOBAL"] = str(trusting_the_member)
            code, stderr = self._lane_push(fixture, lane, **environment)
            self.assertEqual(code, 1, stderr)
            self.assertIn("cannot be told apart from a submodule", stderr)
            self.assertIn("safe.directory", stderr)
            self.assertFalse(fixture.lockfile_calls.exists())

    def test_a_shared_clone_below_the_stack_is_not_a_member(self) -> None:
        """A `--shared` clone of a member keeps its own object store."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            clone = fixture.stack / "scratch" / "clone"
            clone.parent.mkdir()
            subprocess.run(
                ["git", "clone", "-q", "--shared", str(fixture.root), str(clone)],
                check=True, capture_output=True,
            )
            branch = "feat-shared"
            _git(clone, "switch", "-q", "-c", branch)
            (clone / "Cargo.lock").write_text("# lock\n# touched\n", encoding="utf-8")
            sha = _commit_all(clone, "lock")
            push_line = f"refs/heads/{branch} {sha} refs/heads/{branch} {ZERO}\n"
            code, stderr = fixture.run_hook(
                push_line, {"SKIP_LOCAL_GATE": "1", "LOCKFILE_EXIT": "1"}, cwd=clone
            )
            self.assertEqual(code, 1, stderr)
            self.assertIn("not one of its registered members", stderr)
            self.assertIn("credential scanner is not used", stderr)
            self.assertFalse(fixture.lockfile_calls.exists())

    def test_a_member_that_is_a_submodule_is_never_taken_for_the_stack(self) -> None:
        """A member carrying its own `.gitmodules`, with a worktree of itself at
        the path it registers, would otherwise match its own harness worktree
        and run the member's checker. A candidate with a superproject is a
        submodule, not a stack."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            _write(
                fixture.root / ".gitmodules",
                '[submodule "y"]\n\tpath = repos/y\n\turl = ./y\n',
            )
            _commit_all(fixture.root, "planted")
            _git(fixture.stack, "add", "repos/member")
            _git(fixture.stack, "commit", "-q", "-m", "register the member")
            fixture.add_worktree(fixture.root / "repos" / "y", "base-y")
            lane = fixture.add_worktree(
                fixture.root / ".claude" / "worktrees" / "lane", "base-lane"
            )
            code, stderr = self._lane_push(fixture, lane, LOCKFILE_EXIT="1")
            self.assertEqual(code, 1, stderr)
            self.assertIn("does not resolve under --locked", stderr)
            self.assertNotIn("carry no lockfile.py", stderr)

    def _git_processes(self, name: str, fillers: int = 11) -> int:
        """Git processes one source-only push starts for member `name`,
        registered among `fillers` others (trace2 logs one `version` event per
        process)."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack = pathlib.Path(temp)
            for index in range(fillers):
                filler = stack / "repos" / f"filler{index:02d}"
                filler.mkdir(parents=True)
                _git(filler, "init", "-q")
            fixture = GateFixture.in_stack(stack, below=("repos", name))
            trace = stack / "trace2.log"
            code, stderr = self._push(fixture, GIT_TRACE2_EVENT=str(trace))
            self.assertEqual(code, 0, stderr)
            return trace.read_text(encoding="utf-8").count('"event":"version"')

    def test_the_git_work_does_not_depend_on_the_members_position_in_the_registry(self) -> None:
        """The member is resolved from its object store, not found by probing
        every registered member in turn."""
        self.assertEqual(self._git_processes("aaa"), self._git_processes("zzz"))

    def test_a_push_of_deletions_needs_no_readable_stack(self) -> None:
        """A deletion pushes nothing, so there is nothing to judge and nothing
        for a stack to say about it."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            sha = _git(fixture.root, "rev-parse", "HEAD")
            code, stderr = fixture.run_hook(
                f"(delete) {ZERO} refs/heads/gone {sha}\n",
                {"SKIP_LOCAL_GATE": "1", **self._distrusting_environment(pathlib.Path(temp))},
            )
            self.assertEqual(code, 0, stderr)
            self.assertIn("nothing to gate", stderr)
            self.assertNotIn("registers members but git cannot read it", stderr)

    def test_a_registered_member_git_cannot_read_leaves_the_match_unknown(self) -> None:
        """The stack is readable but one of its members is not, so this clone
        may be that member's worktree: refuse rather than call it outside."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = self._unmatched_checkout(temp)
            trusting_the_stack = pathlib.Path(temp) / "trusting.gitconfig"
            trusting_the_stack.write_text(
                f"[safe]\n\tdirectory = {pathlib.Path(temp).resolve().as_posix()}\n",
                encoding="utf-8",
            )
            environment = self._distrusting_environment(pathlib.Path(temp))
            environment["GIT_CONFIG_GLOBAL"] = str(trusting_the_stack)
            code, stderr = self._push(fixture, **environment)
            self.assertEqual(code, 1, stderr)
            self.assertIn("cannot be matched to the stack", stderr)
            self.assertNotIn("no Atlas stack above this clone", stderr)
            self.assertNotIn("could not export", stderr)

    def test_the_checker_comes_from_the_fetched_default_not_the_stack_checkout(self) -> None:
        """The stack checkout may sit on a peer's branch with another copy of
        the script, committed or not; the fetched default's copy is what runs."""
        for committed in (False, True):
            with self.subTest(committed=committed):
                with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
                    fixture = GateFixture.in_stack(pathlib.Path(temp))
                    push_line = self._lock_revisions(fixture, "# FLATTENED\n", "# sound\n")
                    _write(
                        fixture.stack / "scripts" / "lockfile.py",
                        "import sys\nsys.exit(0)\n",
                        executable=True,
                    )
                    if committed:
                        _git(fixture.stack, "commit", "-q", "-am", "a peer's checker")
                    code, stderr = fixture.run_hook(push_line, {"SKIP_LOCAL_GATE": "1"})
                    self.assertEqual(code, 1, stderr)
                    self.assertIn("does not resolve under --locked", stderr)

    def _lock_revisions(
        self, fixture: GateFixture, pushed_lock: str, head_lock: str
    ) -> str:
        """Push a branch holding `pushed_lock` while the checkout's HEAD holds
        `head_lock`, and return the push line."""
        fixture.install_stack_lockfile(_LOCK_READING_CHECKER)
        _git(fixture.root, "switch", "-q", "-c", "feat")
        (fixture.root / "Cargo.lock").write_text(pushed_lock, encoding="utf-8")
        _commit_all(fixture.root, "pushed lock")
        push_line = fixture.push_line_new_branch("feat")
        _git(fixture.root, "switch", "-q", "main")
        (fixture.root / "Cargo.lock").write_text(head_lock, encoding="utf-8")
        _commit_all(fixture.root, "head lock")
        return push_line

    def test_the_pushed_lock_is_judged_not_the_one_at_head(self) -> None:
        """The checker reads the lock it is handed, so the verdict names which
        revision was exported: a push of a sound lock passes while HEAD holds a
        flattened one, and a flattened push is refused while HEAD is sound."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            push_line = self._lock_revisions(fixture, "# sound\n", "# FLATTENED\n")
            code, stderr = fixture.run_hook(push_line, {"SKIP_LOCAL_GATE": "1"})
            self.assertEqual(code, 0, stderr)
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture.in_stack(pathlib.Path(temp))
            push_line = self._lock_revisions(fixture, "# FLATTENED\n", "# sound\n")
            code, stderr = fixture.run_hook(push_line, {"SKIP_LOCAL_GATE": "1"})
            self.assertEqual(code, 1, stderr)
            self.assertIn("does not resolve under --locked", stderr)


class DenySourcesTestCase(unittest.TestCase):
    """A lock-changing push checks dependency sources on an export."""

    def _push(self, mode: str, change: str) -> tuple:
        temp = tempfile.TemporaryDirectory(prefix="pre-push-deny-")
        self.addCleanup(temp.cleanup)
        fixture = _stacked_fixture(temp.name)
        _write(fixture.root / "deny.toml", "[sources]\nallow-git = []\n")
        subprocess.run(["git", "-C", str(fixture.root), *_IDENT, "add", "deny.toml"], check=True)
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q", "-m", "deny"], check=True
        )
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "push", "-q", "origin", "HEAD:main"],
            check=True,
        )
        subprocess.run(["git", "-C", str(fixture.root), "switch", "-q", "-c", "feat"], check=True)
        target = fixture.root / change
        _write(target, target.read_text(encoding="utf-8") + "# changed\n")
        subprocess.run(["git", "-C", str(fixture.root), *_IDENT, "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q", "-m", "change"], check=True
        )
        fixture.set_cargo_behavior(mode)
        lock_before = (fixture.root / "Cargo.lock").read_bytes()
        code, err = fixture.run_hook(
            fixture.push_line_new_branch(), {"SKIP_LOCAL_GATE": "1"}
        )
        self.assertEqual((fixture.root / "Cargo.lock").read_bytes(), lock_before)
        calls = fixture.calls.read_text(encoding="utf-8") if fixture.calls.exists() else ""
        cwd_log = fixture.root / "deny-cwd.log"
        cwd = cwd_log.read_text(encoding="utf-8").strip() if cwd_log.exists() else ""
        return code, err, calls, cwd, fixture.root

    def test_a_lock_change_checks_sources_on_an_export_outside_the_member(self) -> None:
        code, err, calls, cwd, root = self._push("pass", "Cargo.lock")
        self.assertEqual(code, 0, err)
        self.assertIn("deny --locked check sources", calls)
        self.assertTrue(cwd, "cargo deny must have run")
        self.assertNotIn(
            os.path.normcase(str(root.resolve())), os.path.normcase(cwd),
            "the check runs on an export, never in the member's tree",
        )

    def test_a_disallowed_source_refuses_the_push(self) -> None:
        code, err, _, _, _ = self._push("fail-deny", "Cargo.lock")
        self.assertEqual(code, 1, err)
        self.assertIn("resolves a source deny.toml does not allow", err)

    def test_a_push_without_a_dependency_change_skips_the_check(self) -> None:
        code, err, calls, _, _ = self._push("fail-deny", "crates/foo/src/lib.rs")
        self.assertEqual(code, 0, err)
        self.assertNotIn("deny --locked check sources", calls)


class LaneGateTestCase(unittest.TestCase):
    """A lane of an overlaid member gates outside the overlay."""

    inside_log = BlameClassifierTestCase.inside_log

    def _lane(self, overlay: bool) -> tuple:
        temp = tempfile.TemporaryDirectory(prefix="pre-push-lane-")
        self.addCleanup(temp.cleanup)
        stack = pathlib.Path(temp.name)
        fixture = GateFixture(stack / "repos" / "foo")
        _write(stack / "scripts" / "lockfile.py", _STACK_LOCKFILE_STUB, executable=True)
        _publish_stack_scripts(stack)
        if overlay:
            _write(stack / ".cargo" / "config.toml", '[build]\ntarget-dir = "target"\n')
        lane = stack / "worktrees" / "foo-lane"
        subprocess.run(
            ["git", "-C", str(fixture.root), "worktree", "add", "-q", "-b", "lane", str(lane)],
            check=True,
        )
        _write(lane / "crates" / "foo" / "src" / "lib.rs", "pub fn g() {}\n")
        subprocess.run(["git", "-C", str(lane), *_IDENT, "commit", "-qam", "lane"], check=True)
        return stack, fixture, lane

    def _run_in_lane(self, fixture: GateFixture, lane: pathlib.Path,
                     extra_env: dict | None = None,
                     target_directory: pathlib.Path | None = None) -> tuple:
        # No SKIP_LOCKFILE_CHECK here: the lane's own commit touches only
        # crates/foo/src/lib.rs, so the range never touches Cargo.lock or
        # Cargo.toml and the lockfile section already self-skips on that
        # evidence (removing the var, previously set unconditionally, changes
        # nothing -- confirmed by running this suite with and without it).
        fixture.set_workspace_packages(["unrelated-member", "foo"])
        if target_directory is not None:
            metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
            metadata["target_directory"] = str(target_directory)
            _write(fixture.bin / "metadata.json", json.dumps(metadata))
        env = dict(os.environ)
        env["PATH"] = str(fixture.bin) + os.pathsep + env.get("PATH", "")
        env["CARGO"] = str(fixture.cargo_launcher)
        env["TMPDIR"] = fixture.tmp.as_posix()
        env.pop("CARGO_TARGET_DIR", None)
        env.update(extra_env or {})
        _publish_stack_scripts(lane.parents[1])
        sha = _git(lane, "rev-parse", "HEAD")
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            input=f"refs/heads/lane {sha} refs/heads/lane {ZERO}\n".encode("utf-8"),
            cwd=str(lane),
            env=env,
            capture_output=True,
        )
        return proc.returncode, proc.stderr.decode("utf-8", errors="replace")

    def test_a_lane_gates_from_outside_the_stack_with_its_manifest(self) -> None:
        stack, fixture, lane = self._lane(overlay=True)
        code, err = self._run_in_lane(fixture, lane)
        self.assertEqual(code, 0, err)
        calls = fixture.calls.read_text(encoding="utf-8")
        self.assertIn("--manifest-path", calls)
        self.assertIn("foo-lane/Cargo.toml", calls.replace("\\", "/"))
        fmt = [line for line in calls.splitlines() if line.startswith("fmt ")]
        self.assertTrue(fmt and all(line.startswith("fmt --all ") for line in fmt), fmt)
        for cwd in (fixture.root / "cwd.log").read_text(encoding="utf-8").split():
            self.assertNotIn(
                os.path.normcase(str(stack.resolve())), os.path.normcase(str(pathlib.Path(cwd).resolve())),
                "cargo must not run inside the stack",
            )

    def test_a_lane_without_an_overlay_gates_its_export(self) -> None:
        stack, fixture, lane = self._lane(overlay=False)
        code, err = self._run_in_lane(fixture, lane)
        self.assertEqual(code, 0, err)
        calls = fixture.calls.read_text(encoding="utf-8")
        self.assertIn("fmt --all --manifest-path", calls)
        for cwd in (fixture.root / "cwd.log").read_text(encoding="utf-8").split():
            self.assertNotIn(
                os.path.normcase(str(stack.resolve())),
                os.path.normcase(str(pathlib.Path(cwd).resolve())),
            )

    def test_a_lane_identity_step_runs_cargo_with_its_manifest(self) -> None:
        """The checker receives a runnable command, manifest after the subcommand.

        The checker runs everything after `--` verbatim, so a lane manifest
        placed before `cargo` made `--manifest-path` the program and refused
        every lane push of a stack member.
        """
        stack, fixture, lane = self._lane(overlay=True)
        log = stack / "identity-commands.log"
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            _recording_passthrough_identity(log),
        )
        code, err = self._run_in_lane(fixture, lane, target_directory=stack / "target")
        self.assertEqual(code, 0, err)
        commands = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(commands), 1, commands)
        self.assertEqual(commands[0][0:2], ["bash", "-c"], commands[0])
        manifests = [pathlib.Path(value) for value in commands[0] if value.endswith("Cargo.toml")]
        self.assertEqual(len(manifests), 1, commands[0])
        exported = manifests[0]
        self.assertEqual((exported.parent.name, exported.name), ("foo-lane", "Cargo.toml"))
        self.assertNotIn(
            os.path.normcase(str(stack.resolve())),
            os.path.normcase(str(exported.resolve())),
        )
        cargo_calls = fixture.calls.read_text(encoding="utf-8").splitlines()
        stages = [line for line in cargo_calls if line.split()[0] in {"clippy", "nextest", "doc"}]
        self.assertEqual([line.split()[0] for line in stages], ["clippy", "nextest", "doc"])
        self.assertIn("--all-targets --locked -p foo", stages[0])
        self.assertIn("--locked --no-tests=pass -p foo", stages[1])
        self.assertIn("--no-deps", stages[2])
        self.assertTrue(all("--manifest-path" in line for line in stages), stages)
        self.assertEqual((fixture.root / "rustdoc-flags.log").read_text(), "-D warnings")

    def test_identity_clippy_failure_stops_before_tests_and_rustdoc(self) -> None:
        stack, fixture, lane = self._lane(overlay=True)
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            _recording_passthrough_identity(stack / "identity-commands.log"),
        )
        fixture.set_cargo_behavior("fail-clippy-ours")
        code, err = self._run_in_lane(
            fixture,
            lane,
            extra_env={"CARGO_FAIL_LOG": self.inside_log.format(root="@ROOT@")},
            target_directory=stack / "target",
        )

        self.assertEqual(code, 1, err)
        stages = [
            line.split()[0] for line in fixture.calls.read_text(encoding="utf-8").splitlines()
            if line.split()[0] in {"clippy", "nextest", "doc"}
        ]
        self.assertEqual(stages, ["clippy"])
        self.assertIn("clippy fails for", err)

    def test_identity_rejects_a_source_mutation_after_the_sequence(self) -> None:
        stack, fixture, lane = self._lane(overlay=True)
        _install_real_identity(stack)
        fixture.set_cargo_behavior("mutate-source-on-doc")
        code, err = self._run_in_lane(
            fixture,
            lane,
            extra_env={"CARGO_MUTATE_SOURCE": "crates/foo/src/lib.rs"},
            target_directory=stack / "target",
        )

        self.assertEqual(code, 1, err)
        stages = [
            line.split()[0] for line in fixture.calls.read_text(encoding="utf-8").splitlines()
            if line.split()[0] in {"clippy", "nextest", "doc"}
        ]
        self.assertEqual(stages, ["clippy", "nextest", "doc"], err)
        self.assertIn("source identity blocked verification", err)
        self.assertIn("source tree changed while the build was running", err)
        records = list(
            (stack / "target" / ".atlas" / "source-identity").glob("*.json")
        )
        self.assertEqual(records, [], "a mutated source must not receive a build record")

    def test_a_new_member_gates_each_package_once_by_its_exact_name(self) -> None:
        """A root-manifest change gates every member under its exact name.

        The membership listing is printed by Python; on Windows its text-mode
        stdout ends each line with CRLF, and bash keeps the CR, so a push that
        added a member gated `helios-core\\r` beside `helios-core` and the
        identity checker found no package of that name (helios#112).
        """
        stack, fixture, lane = self._lane(overlay=True)
        _write(lane / "Cargo.toml", '[workspace]\nmembers = ["crates/foo", "crates/bar"]\n')
        _write(
            lane / "crates" / "bar" / "Cargo.toml",
            '[package]\nname = "bar"\nversion = "0.1.0"\nedition = "2021"\n',
        )
        _write(lane / "crates" / "bar" / "src" / "lib.rs", "pub fn h() {}\n")
        subprocess.run(["git", "-C", str(lane), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(lane), *_IDENT, "commit", "-qm", "member"], check=True)
        log = stack / "identity-packages.log"
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            "import pathlib, sys\n"
            f"log = pathlib.Path({str(log)!r})\n"
            "packages = [sys.argv[i + 1] for i, v in enumerate(sys.argv) if v == '--package']\n"
            "with log.open('a', encoding='utf-8', newline='') as stream:\n"
            "    stream.write(' '.join(repr(package) for package in packages) + '\\n')\n",
        )
        fixture.set_workspace_packages(["foo", "bar"])
        original = fixture.set_workspace_packages
        fixture.set_workspace_packages = lambda names: original(["foo", "bar"])
        code, err = self._run_in_lane(fixture, lane, target_directory=stack / "target")
        self.assertEqual(code, 0, err)
        # Split on LF only: splitlines() would also split at the stray CR.
        gating = [line for line in err.split("\n") if line.startswith("pre-push: gating ")]
        self.assertEqual(len(gating), 1, err)
        gated = gating[0].removeprefix("pre-push: gating ").split(" ")
        self.assertEqual(sorted(gated), ["bar", "foo"], repr(gating[0]))
        runs = log.read_text(encoding="utf-8").splitlines()
        # One identity run names every gated package and holds their leases
        # across the complete clippy, tests, and rustdoc sequence.
        self.assertEqual(len(runs), 1, runs)
        self.assertEqual({frozenset(run.split()) for run in runs}, {frozenset({"'bar'", "'foo'"})})

    def test_a_package_without_test_targets_skips_only_the_tests_step(self) -> None:
        """A `test = false` cdylib builds no test artifact for the identity checker.

        Pushing a workspace `Cargo.toml` change gates every member, and the
        checker refused the PyO3 extension with "no artifact found" because
        `cargo nextest run -p` has nothing to build for it. Its clippy and
        rustdoc steps still run.
        """
        stack, fixture, lane = self._lane(overlay=True)
        _write(lane / "Cargo.toml", '[workspace]\nmembers = ["crates/foo", "crates/bar"]\n')
        _write(
            lane / "crates" / "bar" / "Cargo.toml",
            '[package]\nname = "bar"\nversion = "0.1.0"\nedition = "2021"\n',
        )
        _write(lane / "crates" / "bar" / "src" / "lib.rs", "pub fn h() {}\n")
        subprocess.run(["git", "-C", str(lane), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(lane), *_IDENT, "commit", "-qm", "member"], check=True)
        log = stack / "identity-steps.log"
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            _recording_passthrough_identity(log),
        )
        bar_targets = {"bar": [{"kind": ["cdylib"], "test": False, "doc": True}]}
        fixture.set_workspace_packages(["foo", "bar"], targets=bar_targets)
        original = fixture.set_workspace_packages
        fixture.set_workspace_packages = lambda names, targets=None: original(
            ["foo", "bar"], targets=bar_targets
        )
        code, err = self._run_in_lane(fixture, lane, target_directory=stack / "target")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(log.read_text(encoding="utf-8").splitlines()), 1)
        stages = [
            line for line in fixture.calls.read_text(encoding="utf-8").splitlines()
            if line.split()[0] in {"clippy", "nextest", "doc"}
        ]
        self.assertEqual([line.split()[0] for line in stages], ["clippy", "nextest", "doc"])
        for line in stages:
            values = line.split()
            self.assertEqual(
                [values[index + 1] for index, value in enumerate(values) if value == "-p"],
                ["foo", "bar"],
            )

    def test_all_undocumented_packages_skip_only_rustdoc(self) -> None:
        """Every gated package undocumented: the one identity run omits rustdoc."""
        stack, fixture, lane = self._lane(overlay=True)
        _write(lane / "Cargo.toml", '[workspace]\nmembers = ["crates/foo", "crates/bar"]\n')
        _write(
            lane / "crates" / "bar" / "Cargo.toml",
            '[package]\nname = "bar"\nversion = "0.1.0"\nedition = "2021"\n',
        )
        _write(lane / "crates" / "bar" / "src" / "lib.rs", "pub fn h() {}\n")
        subprocess.run(["git", "-C", str(lane), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(lane), *_IDENT, "commit", "-qm", "members"], check=True)
        log = stack / "identity-steps.log"
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            _recording_passthrough_identity(log),
        )
        undocumented = {"kind": ["lib"], "doc": False}
        original = fixture.set_workspace_packages
        fixture.set_workspace_packages = lambda names: original(
            ["foo", "bar"], targets={"foo": [undocumented], "bar": [undocumented]},
        )
        fixture.set_workspace_packages(["foo", "bar"])
        code, err = self._run_in_lane(fixture, lane, target_directory=stack / "target")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(log.read_text(encoding="utf-8").splitlines()), 1)
        stages = [
            line.split()[0] for line in fixture.calls.read_text(encoding="utf-8").splitlines()
            if line.split()[0] in {"clippy", "nextest", "doc"}
        ]
        self.assertEqual(stages, ["clippy", "nextest"])
        self.assertIn("rustdoc skipped for foo", err)
        self.assertIn("rustdoc skipped for bar", err)

    def test_a_package_without_a_documented_target_skips_only_the_rustdoc_step(self) -> None:
        """A bench-only package writes no rustdoc artifact, so its step is skipped.

        `cargo doc` documents lib and bin targets; a package of benches alone
        (moirai-benchmarks) or a `[lib] doc = false` one leaves the identity
        checker nothing to record and refused every push touching it. Its
        other steps and every documented package still run.
        """
        stack, fixture, lane = self._lane(overlay=True)
        _write(lane / "Cargo.toml", '[workspace]\nmembers = ["crates/foo", "crates/bar", "crates/baz"]\n')
        for name in ("bar", "baz"):
            _write(
                lane / "crates" / name / "Cargo.toml",
                f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2021"\n',
            )
            _write(lane / "crates" / name / "src" / "lib.rs", "pub fn h() {}\n")
        subprocess.run(["git", "-C", str(lane), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(lane), *_IDENT, "commit", "-qm", "members"], check=True)
        log = stack / "identity-steps.log"
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            _recording_passthrough_identity(log),
        )
        lib = {"kind": ["lib"], "doc": True}
        original = fixture.set_workspace_packages
        fixture.set_workspace_packages = lambda names: original(
            ["foo", "bar", "baz"],
            targets={
                "foo": [lib],
                "bar": [{"kind": ["bench"], "doc": True}],
                "baz": [{"kind": ["lib"], "doc": False}],
            },
        )
        fixture.set_workspace_packages(["foo", "bar", "baz"])
        code, err = self._run_in_lane(fixture, lane, target_directory=stack / "target")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(log.read_text(encoding="utf-8").splitlines()), 1)
        stages = [
            line for line in fixture.calls.read_text(encoding="utf-8").splitlines()
            if line.split()[0] in {"clippy", "nextest", "doc"}
        ]
        self.assertEqual([line.split()[0] for line in stages], ["clippy", "nextest", "doc"])
        for line in stages:
            values = line.split()
            self.assertEqual(
                [values[index + 1] for index, value in enumerate(values) if value == "-p"],
                ["foo", "bar", "baz"],
            )
        self.assertIn("rustdoc skipped for bar", err)

    def test_identity_rustdoc_failure_uses_the_pushed_export(self) -> None:
        """The identity checker receives the pushed export and exact Cargo argv."""
        stack, fixture, lane = self._lane(overlay=True)
        identity_log = stack / "identity-invocations.log"
        _write(
            stack / "scripts" / "atlas-build-identity.py",
            _recording_identity_invocation(identity_log),
        )
        fixture.set_cargo_behavior("fail-doc")
        env = {"CARGO_FAIL_LOG": self.inside_log.format(root="@ROOT@")}
        code, err = self._run_in_lane(fixture, lane, extra_env=env)
        self.assertEqual(code, 1, err)
        self.assertIn("rustdoc fails for foo", err)

        records = [
            json.loads(line)
            for line in identity_log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(records), 1, records)
        record = records[0]
        argv = record["argv"]
        pushed = _git(lane, "rev-parse", "HEAD")
        self.assertEqual(record["root_head"], pushed)
        exported = pathlib.Path(argv[argv.index("--root") + 1]).resolve()
        command_cwd = pathlib.Path(argv[argv.index("--command-cwd") + 1]).resolve()
        self.assertEqual(exported, command_cwd)
        self.assertNotIn(
            os.path.normcase(str(stack.resolve())),
            os.path.normcase(str(exported)),
        )
        self.assertEqual(argv[argv.index("--command-key") + 1], "atlas-pre-push")

        stages = [
            line.split()
            for line in fixture.calls.read_text(encoding="utf-8").splitlines()
            if line.split()[0] in {"clippy", "nextest", "doc"}
        ]
        self.assertEqual([stage[0] for stage in stages], ["clippy", "nextest", "doc"])
        manifest = argv[argv.index("--manifest") + 1]
        self.assertEqual(pathlib.Path(manifest).resolve(), exported / "Cargo.toml")
        self.assertEqual(
            stages[-1],
            ["doc", "--no-deps", "--manifest-path", manifest, "--locked", "-p", "foo"],
        )

    def test_a_lockfile_package_collision_is_the_environment(self) -> None:
        _, fixture, lane = self._lane(overlay=False)
        fixture.set_cargo_behavior("fail-collision")
        code, err = self._run_in_lane(fixture, lane)
        self.assertNotIn("clippy fails for", err)
        self.assertIn("NOT verified", err)


class PushedRangeSelectionTestCase(unittest.TestCase):
    """The gate selects packages from the range git supplies on stdin.

    `HEAD` is the checkout's branch, not the ref being pushed. In a shared
    member tree those differ constantly: a commit built by plumbing and pushed
    by SHA leaves HEAD on the base, so the gate diffed an empty range and ran
    nothing for a Rust change; and with the tree on a peer's branch the gate
    selected that branch's packages instead of the pushed one's.
    """

    def _commit_rust_on_a_branch_then_leave_it(self, fixture: GateFixture) -> None:
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q", "-b", "feat"],
            check=True,
        )
        source = fixture.root / "crates" / "foo" / "src" / "lib.rs"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("pub fn answer() -> u32 {\n    42\n}\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "add", "crates/foo"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q", "-m", "source"],
            check=True,
        )
        # The push happens from a checkout sitting elsewhere, which is the case
        # the gate got wrong.
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q", "main"],
            check=True,
        )

    def test_a_branch_pushed_while_head_sits_elsewhere_gates_the_pushed_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            self._commit_rust_on_a_branch_then_leave_it(fixture)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            # The range is still found (no silent "not needed"), and the
            # package gate builds the pushed commit, not the checkout.
            self.assertNotIn("local gate not needed", stderr)
            assert_gated_on_the_export(self, code, stderr, fixture)

    def test_an_unresolvable_pushed_base_fails_closed_before_gating(self) -> None:
        """A remote tip this clone never fetched fails closed before gating."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            self._commit_rust_on_a_branch_then_leave_it(fixture)
            tip = _git(fixture.root, "rev-parse", "feat")
            absent = "0123456789abcdef0123456789abcdef01234567"

            code, stderr = fixture.run_hook(
                f"refs/heads/feat {tip} refs/heads/feat {absent}\n"
            )

            self.assertNotEqual(code, 0)
            self.assertIn("remote commit is unavailable", stderr)


class DebtRatchetTestCase(unittest.TestCase):
    """The conformance ratchet runs on the pushed revision, as CI runs it.

    metis#394 passed every local stage and then failed CI's conformance job
    on `oversized_files: 0 -> 1`: nothing local ran the ratchet. The hook
    must judge the pushed tip (never the checkout, which a peer may hold on
    another branch), against the baseline committed at the stack's default
    branch (never its working copy).
    """

    def _stack(
        self, temp: str, exit_code: int, revision_scans: bool = True,
        location: str = "repos", identity: bool = True,
    ) -> tuple:
        stack = pathlib.Path(temp)
        if identity:
            # A registered member's package steps run through the stack's
            # identity checker; this one runs the step it is handed.
            _write(stack / "scripts" / "atlas-build-identity.py", PASSTHROUGH_IDENTITY)
        log = stack / "conformance-args.log"
        # The stack's committed checker: it logs the stack it was told to
        # measure, then its arguments, one per line.
        _write(
            stack / "scripts" / "atlas-conformance.py",
            "#!/usr/bin/env python3\n"
            "import os, pathlib, sys\n"
            f"pathlib.Path({str(log)!r}).write_text("
            "'\\n'.join([os.environ.get('ATLAS_STACK_ROOT', ''), *sys.argv[1:]]))\n"
            f"sys.exit({exit_code})\n",
            executable=True,
        )
        _write(
            stack / "scripts" / "atlas_stack.py",
            "ROOT = None  # honours ATLAS_STACK_ROOT\n" if revision_scans else "ROOT = None\n",
        )
        _seed_scanner(stack)
        _git_init_repo(stack)
        _register_stack(stack)
        subprocess.run(
            ["git", "-C", str(stack), *_IDENT, "add", ".gitmodules", "scripts"], check=True
        )
        subprocess.run(
            ["git", "-C", str(stack), *_IDENT, "commit", "-q", "-m", "stack"], check=True
        )
        stack_head = _git(stack, "rev-parse", "HEAD")
        _git(stack, "update-ref", "refs/remotes/origin/main", stack_head)
        (stack / "repos").mkdir(exist_ok=True)
        fixture = GateFixture(stack / location / "member")
        metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
        metadata["target_directory"] = str(stack / "target")
        _write(fixture.bin / "metadata.json", json.dumps(metadata))
        root = fixture.root
        base = _git(root, "rev-parse", "HEAD")
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "feat"], check=True
        )
        (root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn f() {}\n// pushed\n")
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "commit", "-q", "-am", "pushed"], check=True
        )
        pushed = _git(root, "rev-parse", "feat")
        # The shared checkout moves to a peer's branch before the push.
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "peer", base],
            check=True,
        )
        return fixture, log, stack_head, base, pushed

    @staticmethod
    def _args(log: pathlib.Path) -> dict:
        stack_root, *argv = log.read_text().split("\n")
        return {flag: argv[argv.index(flag) + 1] for flag in (
            "--repo", "--member-path", "--member-revision", "--baseline-rev",
        )} | {"mode": argv[0], "ATLAS_STACK_ROOT": stack_root}

    def test_the_pushed_tip_is_judged_against_the_committed_baseline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, stack_head, base, pushed = self._stack(temp, 0)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            assert_gated_on_the_export(self, code, stderr, fixture)
            args = self._args(log)
            self.assertEqual(args["mode"], "check")
            self.assertEqual(
                pathlib.Path(args["ATLAS_STACK_ROOT"]).resolve(), pathlib.Path(temp).resolve()
            )
            self.assertEqual(args["--repo"], "member")
            self.assertEqual(
                pathlib.Path(args["--member-path"]).resolve(), fixture.root.resolve()
            )
            self.assertEqual(args["--member-revision"], pushed)
            self.assertEqual(args["--baseline-rev"], stack_head)

    def test_stack_root_push_uses_meta_ratchet_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack = pathlib.Path(temp)
            fixture = GateFixture(stack, layout="meta")
            fixture.set_workspace_packages(["foo"])
            metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
            metadata["target_directory"] = str(stack / "target")
            _write(fixture.bin / "metadata.json", json.dumps(metadata))
            log = stack / "conformance-args.log"
            _write(stack / "scripts" / "atlas-build-identity.py", PASSTHROUGH_IDENTITY)
            _write(
                stack / "scripts" / "atlas-conformance.py",
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                f"pathlib.Path({str(log)!r}).write_text("
                "'\\n'.join([os.environ.get('ATLAS_STACK_ROOT', ''), *sys.argv[1:]]))\n",
                executable=True,
            )
            _write(stack / "scripts" / "atlas_stack.py", "ROOT = None  # honours ATLAS_STACK_ROOT\n")
            _seed_scanner(stack)
            _register_stack(stack)
            subprocess.run(
                ["git", "-C", str(stack), *_IDENT, "add", ".gitmodules", "scripts"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(stack), *_IDENT, "commit", "-q", "-m", "stack"],
                check=True,
            )
            stack_head = _git(stack, "rev-parse", "HEAD")
            _git(stack, "update-ref", "refs/remotes/origin/main", stack_head)
            subprocess.run(
                ["git", "-C", str(stack), *_IDENT, "checkout", "-q", "-b", "feat"],
                check=True,
            )
            (stack / "tools" / "version-guard" / "src" / "lib.rs").write_text(
                "pub fn f() {}\n// pushed\n"
            )
            subprocess.run(
                ["git", "-C", str(stack), *_IDENT, "commit", "-q", "-am", "pushed"],
                check=True,
            )
            pushed = _git(stack, "rev-parse", "feat")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            assert_gated_on_the_export(self, code, stderr, fixture)
            stack_root, *argv = log.read_text().split("\n")
            self.assertEqual(pathlib.Path(stack_root).resolve(), stack.resolve())
            self.assertEqual(argv[0], "check")
            self.assertEqual(argv[argv.index("--revision") + 1], pushed)
            self.assertEqual(argv[argv.index("--baseline-rev") + 1], stack_head)
            self.assertNotIn("--repo", argv)

    def test_a_raise_refuses_the_push_before_compiling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, _, _, _ = self._stack(temp, 1)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            self.assertTrue(log.is_file(), "the ratchet was not invoked")
            self.assertEqual(code, 1)
            self.assertIn("raises a debt class", stderr)
            calls = fixture.calls.read_text() if fixture.calls.is_file() else ""
            self.assertNotIn("clippy", calls, "the ratchet gates before the compile steps")

    def test_a_ratchet_that_cannot_run_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, _, _, _, _ = self._stack(temp, 2)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            self.assertEqual(code, 1)
            self.assertIn("could not run (exit 2)", stderr)

    def test_a_stack_checker_without_revision_scans_is_reported_not_run(self) -> None:
        """A working-tree scan would judge the wrong state; say so instead."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, _, _, _ = self._stack(temp, 1, revision_scans=False)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            self.assertFalse(log.is_file())
            assert_gated_on_the_export(self, code, stderr, fixture)
            self.assertIn("predates revision scans", stderr)

    def test_the_committed_checker_runs_not_the_stack_checkout_s(self) -> None:
        """The stack tree on a peer's branch or dirty never picks the checker."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, _, _, _ = self._stack(temp, 0)
            stray = pathlib.Path(temp) / "stray.log"
            _write(
                pathlib.Path(temp) / "scripts" / "atlas-conformance.py",
                "import pathlib, sys\n"
                f"pathlib.Path({str(stray)!r}).write_text('ran')\n"
                "sys.exit(1)\n",
            )
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            assert_gated_on_the_export(self, code, stderr, fixture)
            self.assertTrue(log.is_file())
            self.assertFalse(stray.exists(), "the working-tree checker ran")
            # A second push reuses the extracted revision.
            cache = pathlib.Path(temp) / ".git" / "atlas-checker"
            self.assertEqual(len([p for p in cache.iterdir() if p.is_dir() and not p.name.startswith(".")]), 1)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            assert_gated_on_the_export(self, code, stderr, fixture)
            self.assertEqual(len([p for p in cache.iterdir() if p.is_dir() and not p.name.startswith(".")]), 1)

    @staticmethod
    def _git_push(fixture: GateFixture, cwd: pathlib.Path, *refspec: str) -> tuple:
        """Push through git itself, so the hook sees the environment git gives
        hooks -- `GIT_DIR` among it, absolute in a lane -- not a bare shell's.
        """
        env = dict(os.environ)
        env["PATH"] = str(fixture.bin) + os.pathsep + env.get("PATH", "")
        env["TMPDIR"] = fixture.tmp.as_posix()
        # The fixture's package metadata names the main tree, so the compile
        # gate is out of scope; the ratchet precedes it and this variable does
        # not skip it.
        env["SKIP_LOCAL_GATE"] = "1"
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            env.pop(key, None)
        proc = subprocess.run(
            ["git", "-C", str(cwd), *_IDENT, "-c", f"core.hooksPath={SCRIPT.parent}",
             "push", "-q", "origin", *refspec],
            env=env, capture_output=True,
        )
        return proc.returncode, proc.stderr.decode("utf-8", errors="replace")

    def test_a_main_tree_push_through_git_runs_the_ratchet(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, stack_head, base, pushed = self._stack(temp, 0)
            code, stderr = self._git_push(fixture, fixture.root, "feat")
            self.assertEqual(code, 0, stderr)
            args = self._args(log)
            self.assertEqual(args["--repo"], "member")
            self.assertEqual(args["--member-revision"], pushed)
            self.assertEqual(args["--baseline-rev"], stack_head)

    def test_a_lane_push_through_git_judges_its_registered_member(self) -> None:
        """From a lane the stack's refs, not the lane's, name the baseline."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, stack_head, _, _ = self._stack(temp, 0)
            lane = pathlib.Path(temp) / "worktrees" / "member-lane"
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "worktree", "add", "-q",
                 "-b", "lane", str(lane), "feat"],
                check=True,
            )
            pushed = _git(lane, "rev-parse", "HEAD")
            code, stderr = self._git_push(fixture, lane, "lane")
            self.assertEqual(code, 0, stderr)
            self.assertNotIn("no stack checker reachable", stderr)
            args = self._args(log)
            self.assertEqual(args["--repo"], "member")
            self.assertEqual(pathlib.Path(args["--member-path"]).resolve(), lane.resolve())
            self.assertEqual(args["--member-revision"], pushed)
            self.assertEqual(args["--baseline-rev"], stack_head)

    def test_a_deletion_only_push_is_not_judged(self) -> None:
        """No commit is pushed, so nothing -- `HEAD` least of all -- is scanned."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, _, _, pushed = self._stack(temp, 1)
            code, stderr = fixture.run_hook(
                f"(delete) {ZERO} refs/heads/feat {pushed}\n"
            )
            self.assertFalse(log.is_file())
            self.assertIn("carries no commits", stderr)
            self.assertNotIn("raises a debt class", stderr)

    def test_an_unregistered_checkout_is_refused_before_the_ratchet(self) -> None:
        """No registered member shares this checkout's store, so the stack is
        not its stack: the ratchet has no row, and the credential stage, which
        has no trusted scanner to use, refuses the push before the ratchet."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, _, _, _ = self._stack(temp, 1, location="scratch")
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            self.assertEqual(code, 1, stderr)
            self.assertFalse(log.is_file())
            self.assertIn("BLOCKED -- inside the Atlas stack at", stderr)
            self.assertNotIn("debt ratchet", stderr)


class PushedRevisionGateTestCase(unittest.TestCase):
    """The package gate judges the pushed commit, whatever the checkout holds.

    The stack commits through a private index onto an item branch nobody
    checked out, while the shared checkout sits on a peer's branch with
    uncommitted files and an overlay-rewritten lock. The gate once ran cargo
    in that checkout: ritk's push failed fmt on a peer's uncommitted layout
    modules and kwavers's on files the push did not carry, and then a
    refusal of any push whose tip differed from the checkout refused them all.
    """

    PEER_LOCK = b"# rewritten by the overlay in a peer's checkout\n"

    def _push_from_a_peer_checkout(self, temp: str, pushed_source: str) -> tuple:
        fixture = _stacked_fixture(temp)
        fixture.set_cargo_behavior("fmt-by-content")
        metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
        metadata["target_directory"] = str(fixture.stack / "target")
        _write(fixture.bin / "metadata.json", json.dumps(metadata))
        _write(
            fixture.stack / "scripts" / "atlas-build-identity.py",
            PASSTHROUGH_IDENTITY,
        )
        _publish_stack_scripts(fixture.stack)
        root = fixture.root
        base = _git(root, "rev-parse", "main")

        # The item commit, built through a private index and never checked out.
        index = root / ".git" / "item-index"
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        blob = subprocess.run(
            ["git", "-C", str(root), "hash-object", "-w", "--stdin"],
            input=pushed_source.encode("utf-8"), capture_output=True, check=True,
        ).stdout.decode().strip()
        for argv in (
            ["read-tree", base],
            ["update-index", "--cacheinfo", f"100644,{blob},crates/foo/src/lib.rs"],
        ):
            subprocess.run(["git", "-C", str(root), *argv], env=env, check=True)
        tree = subprocess.run(
            ["git", "-C", str(root), "write-tree"], env=env, capture_output=True, check=True,
        ).stdout.decode().strip()
        item = _git(root, "commit-tree", tree, "-p", base, "-m", "item")
        _git(root, "update-ref", "refs/heads/item", item)

        # The checkout: a peer's branch, fmt-failing dirt, a divergent lock.
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "peer"], check=True
        )
        _write(root / "README.md", "peer\n")
        subprocess.run(["git", "-C", str(root), *_IDENT, "add", "README.md"], check=True)
        subprocess.run(
            ["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", "peer"], check=True
        )
        _write(root / "crates" / "foo" / "src" / "lib.rs", "pub fn f() {} // UNFORMATTED\n")
        _write(root / "crates" / "foo" / "src" / "layout.rs", "fn g(){} // UNFORMATTED\n")
        (root / "Cargo.lock").write_bytes(self.PEER_LOCK)
        self.assertNotEqual(_git(root, "rev-parse", "HEAD"), item)

        code, stderr = fixture.run_hook(fixture.push_line_new_branch("item"))
        return fixture, item, code, stderr

    def test_a_clean_pushed_commit_is_accepted_over_a_dirty_peer_checkout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, item, code, stderr = self._push_from_a_peer_checkout(
                temp, "pub fn f() {}\n// pushed\n"
            )

            assert_gated_on_the_export(self, code, stderr, fixture)
            self.assertIn("gating foo", stderr)
            calls = fixture.calls.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(line.startswith("fmt --all --manifest-path") for line in calls), calls)
            for step in ("clippy", "doc"):
                matching = [line for line in calls if line.startswith(step)]
                self.assertTrue(matching, calls)
                self.assertTrue(all("-p foo" in line and "--locked" in line for line in matching), matching)
            # The steps read the pushed commit's lock, not the checkout's.
            committed = subprocess.run(
                ["git", "-C", str(fixture.root), "show", f"{item}:Cargo.lock"],
                capture_output=True, check=True,
            ).stdout
            self.assertEqual(
                (fixture.root / "observed-lock").read_bytes().replace(b"\r\n", b"\n"),
                committed.replace(b"\r\n", b"\n"),
            )
            self.assertTrue((fixture.root / "observed-target").read_text(encoding="utf-8"))
            # The checkout is left exactly as the peer left it.
            self.assertEqual((fixture.root / "Cargo.lock").read_bytes(), self.PEER_LOCK)
            self.assertTrue((fixture.root / "crates" / "foo" / "src" / "layout.rs").is_file())

    def test_a_fmt_failing_pushed_commit_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, item, code, stderr = self._push_from_a_peer_checkout(
                temp, "pub fn f() {} // UNFORMATTED\n"
            )

            self.assertEqual(code, 1, stderr)
            self.assertIn(f"`cargo fmt --check` fails on {item}", stderr)
            calls = fixture.calls.read_text(encoding="utf-8")
            self.assertIn("fmt --all --manifest-path", calls)
            self.assertNotIn("clippy", calls, "fmt gates before the compile steps")


def _commit_all(root: pathlib.Path, message: str) -> str:
    subprocess.run(["git", "-C", str(root), *_IDENT, "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", message], check=True)
    return _git(root, "rev-parse", "HEAD")


class PushShapeTestCase(unittest.TestCase):
    """Every ref a push carries is judged, and only what it carries."""

    def test_every_ref_of_a_multi_ref_push_is_gated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            fixture.set_cargo_behavior("fmt-by-content")
            lib = fixture.root / "crates" / "foo" / "src" / "lib.rs"
            _git(fixture.root, "switch", "-q", "-c", "good")
            lib.write_text("pub fn f() {}\npub fn g() {}\n", encoding="utf-8")
            _commit_all(fixture.root, "good")
            _git(fixture.root, "switch", "-q", "-c", "bad", "main")
            lib.write_text("pub fn f() {} // UNFORMATTED\n", encoding="utf-8")
            bad = _commit_all(fixture.root, "bad")
            _git(fixture.root, "switch", "-q", "good")

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch("good") + fixture.push_line_new_branch("bad")
            )

            self.assertEqual(code, 1, stderr)
            self.assertIn(f"`cargo fmt --check` fails on {bad}", stderr)

    def test_an_orphan_branch_is_judged_on_its_own_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            fixture.set_cargo_behavior("fmt-by-content")
            metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
            metadata["target_directory"] = str(fixture.stack / "target")
            _write(fixture.bin / "metadata.json", json.dumps(metadata))
            _write(
                fixture.stack / "scripts" / "atlas-build-identity.py",
                PASSTHROUGH_IDENTITY,
            )
            _publish_stack_scripts(fixture.stack)
            root = fixture.root
            # An orphan keeps the tree but shares no history with main.
            _git(root, "checkout", "-q", "--orphan", "orphan")
            _write(root / "crates" / "foo" / "src" / "lib.rs", "pub fn f() {} // UNFORMATTED\n")
            orphan = _commit_all(root, "orphan")
            _git(root, "switch", "-q", "main")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("orphan"))

            self.assertEqual(code, 1, stderr)
            self.assertIn(f"`cargo fmt --check` fails on {orphan}", stderr)

    def test_a_deletion_only_push_gates_nothing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            fixture.set_cargo_behavior("fmt-by-content")
            _git(fixture.root, "switch", "-q", "-c", "bad")
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn f() {} // UNFORMATTED\n", encoding="utf-8"
            )
            _commit_all(fixture.root, "bad")
            main = _git(fixture.root, "rev-parse", "main")

            code, stderr = fixture.run_hook(f"(delete) {ZERO} refs/heads/old {main}\n")

            self.assertEqual(code, 0, stderr)
            self.assertIn("carries no commits; nothing to gate", stderr)
            self.assertFalse(fixture.calls.exists(), "cargo ran for a deletion")


class ExportHygieneTestCase(unittest.TestCase):
    """Exports are exact, confined, and never outlive the run."""

    def test_symlinks_are_exported_without_being_followed(self) -> None:
        """A dangling in-tree link and a link to a directory outside the tree.

        Git Bash tar refused the dangling link and deep-copied the outside
        directory; the export writes links as links, or as files where
        `core.symlinks` is false.
        """
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            outside = pathlib.Path(temp) / "outside"
            _write(outside / "secret.txt", "outside\n")
            root = fixture.root
            _git(root, "switch", "-q", "-c", "links")
            (root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn g() {}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
            for name, target in (("dangling", "missing/file"), ("escape", "../../outside")):
                blob = subprocess.run(
                    ["git", "-C", str(root), "hash-object", "-w", "--stdin"],
                    input=target.encode(), capture_output=True, check=True,
                ).stdout.decode().strip()
                subprocess.run(
                    ["git", "-C", str(root), "update-index", "--add", "--cacheinfo",
                     f"120000,{blob},crates/foo/{name}"],
                    check=True,
                )
            subprocess.run(["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", "links"], check=True)
            stub = fixture.bin / "cargo"
            stub.write_text(
                stub.read_text(encoding="utf-8").replace(
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n',
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                    'for link in crates/foo/escape crates/foo/dangling; do\n'
                    '  if [ -L "$link" ]; then kind=link; elif [ -d "$link" ]; then kind=copied;'
                    ' elif [ -f "$link" ]; then kind=file; else kind=absent; fi\n'
                    '  echo "$link $kind" >> "$FIXTURE_ROOT/links.log"\n'
                    "done\n",
                    1,
                ),
                encoding="utf-8",
            )

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("links"))

            self.assertEqual(code, 0, stderr)
            kinds = set((fixture.root / "links.log").read_text(encoding="utf-8").splitlines())
            for link in ("crates/foo/escape", "crates/foo/dangling"):
                self.assertTrue({f"{link} link", f"{link} file"} & kinds, kinds)
                self.assertNotIn(f"{link} copied", kinds)
                self.assertNotIn(f"{link} absent", kinds)

    def test_stack_config_is_mirrored_without_any_patch_form(self) -> None:
        """Every `[patch]` form leaves; everything else, and the target, stays."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack = pathlib.Path(temp)
            fixture = GateFixture(stack / "repos" / "member")
            _publish_stack_scripts(stack)
            target = (stack / "shared-target").as_posix()
            _write(
                stack / ".cargo" / "config.toml",
                "patch.dotted-registry.top = { path = \"top-level-dotted\" }\n"
                "[build]\n"
                f"target-dir = '{target}'\n"
                "[patch.crates-io]\n"
                "a = { path = \"x\" }\n"
                "[ patch . \"https://g/x\" ]\n"
                "b = { path = \"y\" }\n"
                "[profile.dev]\n"
                "opt-level = 0\n"
                "[target.x86_64-pc-windows-msvc]\n"
                "rustflags = [\n"
                "  \"-Clink-arg=/x\",\n"
                "]\n"
                "[patch.\"https://g/w\"]\n"
                "list = [\n"
                "[1, 2],\n"
                "]\n"
                "g = { path = \"leaked-after-array-line\" }\n",
            )
            _git(fixture.root, "switch", "-q", "-c", "feat")
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn g() {}\n", encoding="utf-8")
            _commit_all(fixture.root, "feat")
            stub = fixture.bin / "cargo"
            stub.write_text(
                stub.read_text(encoding="utf-8").replace(
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n',
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                    'printf "%s" "${CARGO_TARGET_DIR:-}" > "$FIXTURE_ROOT/observed-target"\n'
                    'dir="$PWD"\n'
                    'while [ "$dir" != "/" ] && [ "$dir" != "." ]; do\n'
                    '  [ -f "$dir/.cargo/config.toml" ] && cp "$dir/.cargo/config.toml" "$FIXTURE_ROOT/mirrored.toml"\n'
                    '  parent="$(dirname "$dir")"; [ "$parent" = "$dir" ] && break; dir="$parent"\n'
                    "done\n",
                    1,
                ),
                encoding="utf-8",
            )
            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch("feat"), {"CARGO_TARGET_DIR": ""}
            )

            self.assertEqual(code, 0, stderr)
            mirrored_text = (fixture.root / "mirrored.toml").read_text(encoding="utf-8")
            self.assertNotIn("leaked-after-array-line", mirrored_text)
            self.assertNotIn("top-level-dotted", mirrored_text)
            mirrored = tomllib.loads(mirrored_text)
            self.assertNotIn("patch", mirrored)
            self.assertEqual(mirrored["profile"]["dev"]["opt-level"], 0)
            self.assertEqual(
                mirrored["target"]["x86_64-pc-windows-msvc"]["rustflags"], ["-Clink-arg=/x"]
            )
            self.assertEqual(
                pathlib.Path((fixture.root / "observed-target").read_text(encoding="utf-8")).resolve(),
                pathlib.Path(target).resolve(),
            )

    def test_a_failed_checker_rename_without_a_winner_keeps_the_checker(self) -> None:
        """A rename can fail with no concurrent winner; the copy is still usable."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, stack_head, _, _ = DebtRatchetTestCase._stack(self, temp, 0)
            cache = pathlib.Path(temp) / ".git" / "atlas-checker"
            cache.mkdir()
            # A plain file where the copy belongs: the rename fails, and no
            # complete copy won it.
            (cache / stack_head).write_text("not a checker\n", encoding="utf-8")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            self.assertNotIn("could not extract", stderr)
            self.assertTrue(log.is_file(), "the ratchet did not run")

    def test_stale_exports_of_dead_runs_are_swept(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            tmp = pathlib.Path(temp) / "tmp"
            stale = tmp / "pre-push-gate.dead01"
            young = tmp / "pre-push-lock.young1"
            for directory in (stale, young):
                _write(directory / "tree" / "big.bin", "x")
            (stale / ".pre-push-owner").write_text("999999\n", encoding="utf-8")
            hour_ago = time.time() - 7200
            os.utime(stale, (hour_ago, hour_ago))

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch("main").replace("refs/heads/main", "refs/heads/copy"),
                {"TMPDIR": tmp.as_posix(), "SKIP_LOCAL_GATE": "1"},
            )

            self.assertEqual(code, 0, stderr)
            self.assertFalse(stale.exists(), "a dead run's export survived")
            self.assertTrue(young.exists(), "a recent export was removed")

    def test_an_interrupted_lock_check_leaves_no_export(self) -> None:
        """TERM while the lock export exists: the trap removes it."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            tmp = pathlib.Path(temp) / "tmp"
            tmp.mkdir()
            _git(fixture.root, "switch", "-q", "-c", "feat")
            # The checker announces its pid on stderr, which the test reads,
            # and then holds the run open until the test kills it; the sleep
            # is only a backstop that ends a stranded checker.
            fixture.install_stack_lockfile(
                "import os, sys, time\n"
                "sys.stderr.write(f'lock-check-started {os.getpid()}\\n')\n"
                "sys.stderr.flush()\n"
                "time.sleep(300)\n"
            )
            (fixture.root / "Cargo.lock").write_text("# lock\n# touched\n", encoding="utf-8")
            _commit_all(fixture.root, "lock")
            env = dict(os.environ)
            env["PATH"] = str(fixture.bin) + os.pathsep + env.get("PATH", "")
            env["TMPDIR"] = tmp.as_posix()
            proc = subprocess.Popen(
                ["bash", str(SCRIPT)], cwd=str(fixture.root), env=env,
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            self.addCleanup(proc.stderr.close)
            # Every wait below ends when the hook exits, and the watchdog ends
            # the hook if it never does, so no read or wait is unbounded.
            watchdog = threading.Timer(WATCHDOG_SECONDS, proc.kill)
            watchdog.start()
            self.addCleanup(watchdog.cancel)
            self.addCleanup(proc.kill)
            proc.stdin.write(fixture.push_line_new_branch("feat").encode())
            proc.stdin.close()
            checker_pid = None
            for line in proc.stderr:
                if line.startswith(b"lock-check-started "):
                    checker_pid = int(line.split()[1])
                    break
            self.assertIsNotNone(checker_pid, "the hook ended before the lock check started")
            self.assertTrue(any(tmp.glob("pl.*")))
            if os.name == "nt":
                # The hook's bash is an MSYS process: signal it by its MSYS pid,
                # as a terminal's Ctrl-C or a killed parent does.
                listing = subprocess.run(["ps", "-W"], capture_output=True, text=True).stdout
                pids = [line.split()[0] for line in listing.splitlines()[1:]
                        if len(line.split()) > 3 and line.split()[3] == str(proc.pid)]
                self.assertTrue(pids, listing)
                subprocess.run(["bash", "-c", f"kill -TERM {pids[0]}"], check=True)
            else:
                proc.terminate()
            # bash runs the trap once its foreground checker returns, so the
            # checker is ended by the pid it announced.
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(checker_pid)],
                    capture_output=True, check=True,
                )
            else:
                os.kill(checker_pid, signal.SIGKILL)
            proc.wait()
            self.assertFalse(watchdog.finished.is_set(), "the hook had to be killed")
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(list(tmp.glob("pl.*")), [])


def _live_msys_pid(test: unittest.TestCase) -> str:
    """The pid of a live shell as the hook's `kill -0` sees it."""
    holder = subprocess.Popen(
        ["bash", "-c", "echo $$; exec sleep 120"], stdout=subprocess.PIPE, text=True
    )
    test.addCleanup(holder.wait, 30)
    test.addCleanup(holder.kill)
    test.addCleanup(holder.stdout.close)
    return holder.stdout.readline().strip()


class ExportSourceTestCase(unittest.TestCase):
    """The export is written through the member, reused, and never too long."""

    @staticmethod
    def _export_function() -> str:
        source = SCRIPT.read_text(encoding="utf-8")
        start = source.index("export_revision() (")
        end = source.index("\n)\n\n# Exports a killed push", start) + 2
        return source[start:end]

    def _run_export(
        self,
        source: pathlib.Path,
        outer: pathlib.Path,
        revision: str,
        destination: pathlib.Path,
        declaration: str,
    ) -> subprocess.CompletedProcess:
        before = destination.parent / f"{destination.name}-{declaration}-before"
        after = destination.parent / f"{destination.name}-{declaration}-after"
        script = self._export_function() + r'''
repo_git_dir="$1"
repo_store="$2"
revision="$3"
destination="$4"
declaration="$5"
before="$6"
after="$7"
outer_git_dir="$8"
outer_work_tree="$9"
outer_index="${10}"
outer_prefix="${11}"
outer_common_dir="${12}"
case "$declaration" in
  absent)
    unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX GIT_COMMON_DIR
    ;;
  unexported)
    GIT_DIR="$outer_git_dir"
    GIT_WORK_TREE="$outer_work_tree"
    GIT_INDEX_FILE="$outer_index"
    GIT_PREFIX="$outer_prefix"
    GIT_COMMON_DIR="$outer_common_dir"
    ;;
  exported)
    export GIT_DIR="$outer_git_dir"
    export GIT_WORK_TREE="$outer_work_tree"
    export GIT_INDEX_FILE="$outer_index"
    export GIT_PREFIX="$outer_prefix"
    export GIT_COMMON_DIR="$outer_common_dir"
    ;;
  *) exit 97 ;;
esac
{ declare -p GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX GIT_COMMON_DIR 2>/dev/null || true; } > "$before"
export_revision "$revision" "$destination"
status=$?
{ declare -p GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX GIT_COMMON_DIR 2>/dev/null || true; } > "$after"
exit "$status"
'''
        return subprocess.run(
            [
                "bash", "-c", script, "export-boundary",
                _git(source, "rev-parse", "--absolute-git-dir"),
                _git(source, "rev-parse", "--path-format=absolute", "--git-common-dir"),
                revision,
                str(destination),
                declaration,
                str(before),
                str(after),
                _git(outer, "rev-parse", "--absolute-git-dir"),
                str(outer),
                str(outer / ".git" / "index"),
                "outer-prefix/",
                _git(outer, "rev-parse", "--path-format=absolute", "--git-common-dir"),
            ],
            capture_output=True,
        )

    @staticmethod
    def _export_block(start_marker: str, end_marker: str) -> str:
        source = SCRIPT.read_text(encoding="utf-8")
        start = source.index(start_marker)
        end = source.index(end_marker, start)
        return source[start:end]

    def _run_gate_export(
        self,
        source: pathlib.Path,
        revision: str,
        destination: pathlib.Path,
        trace: pathlib.Path,
    ) -> subprocess.CompletedProcess:
        block = self._export_block(
            'if ! export_revision "$gate_sha" "$gate_export"; then',
            "\n\nrun_cargo_workspace_gate()",
        )
        script = self._export_function() + "\n" + block
        environment = dict(os.environ)
        environment["GIT_TRACE2_EVENT"] = str(trace)
        return subprocess.run(
            [
                "bash", "-c",
                'repo_git_dir="$1"; repo_store="$2"; gate_sha="$3"; '
                'gate_export="$4"; shift 4; ' + script,
                "gate-export",
                _git(source, "rev-parse", "--absolute-git-dir"),
                _git(source, "rev-parse", "--path-format=absolute", "--git-common-dir"),
                revision,
                str(destination),
            ],
            env=environment,
            capture_output=True,
        )

    def assert_read_tree_count(self, trace: pathlib.Path, expected: int) -> None:
        events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
        commands = [
            event["argv"]
            for event in events
            if event.get("event") == "start" and "read-tree" in event.get("argv", [])
        ]
        self.assertEqual(len(commands), expected, commands)

    def test_a_partial_clone_exports_blobs_it_never_fetched(self) -> None:
        """13 of 28 members are `blob:none` clones; the export fetches on demand."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            upstream = fixture.root / "upstream.git"
            _git(upstream, "config", "uploadpack.allowFilter", "true")
            _git(upstream, "config", "uploadpack.allowAnySHA1InWant", "true")
            _git(fixture.root, "switch", "-q", "-c", "feat")
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn fetched_on_demand() {}\n", encoding="utf-8"
            )
            pushed = _commit_all(fixture.root, "feat")
            _git(fixture.root, "push", "-q", "origin", "feat")
            partial = pathlib.Path(temp) / "repos" / "partial"
            subprocess.run(
                ["git", "clone", "-q", "--filter=blob:none", upstream.as_uri(), str(partial)],
                check=True,
            )
            _register_stack(pathlib.Path(temp))
            for key, value in (("gc.auto", "0"), ("maintenance.auto", "false")):
                _git(partial, "config", key, value)
            missing = subprocess.run(
                ["git", "-C", str(partial), "cat-file", "-e", f"{pushed}:crates/foo/src/lib.rs"],
                env=dict(os.environ, GIT_NO_LAZY_FETCH="1"), capture_output=True,
            )
            self.assertNotEqual(missing.returncode, 0, "the fixture's blob is already local")
            env = dict(os.environ)
            env["PATH"] = str(fixture.bin) + os.pathsep + env.get("PATH", "")
            env["CARGO"] = str(fixture.cargo_launcher)
            env["TMPDIR"] = (pathlib.Path(temp) / "tmp").as_posix()
            (pathlib.Path(temp) / "tmp").mkdir()

            proc = subprocess.run(
                ["bash", str(SCRIPT)], cwd=str(partial), env=env, capture_output=True,
                input=f"refs/heads/feat {pushed} refs/heads/feat {ZERO}\n".encode(),
            )

            stderr = proc.stderr.decode("utf-8", errors="replace")
            self.assertEqual(proc.returncode, 0, stderr)
            self.assertIn("gating foo", stderr)

    @unittest.skipUnless(os.name == "nt", "the 260-character path limit is Windows'")
    def test_a_path_past_the_windows_limit_is_exported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            root = fixture.root
            _git(root, "config", "core.longpaths", "true")
            _git(root, "switch", "-q", "-c", "deep")
            deep = "crates/foo/tests/" + "d" * 110 + "/" + "e" * 110 + ".txt"
            blob = subprocess.run(
                ["git", "-C", str(root), "hash-object", "-w", "--stdin"],
                input=b"deep\n", capture_output=True, check=True,
            ).stdout.decode().strip()
            _git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{deep}")
            subprocess.run(["git", "-C", str(root), *_IDENT, "commit", "-q", "-m", "deep"], check=True)
            self.assertGreater(len(str(fixture.tmp.resolve())) + len(deep), 260)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("deep"))

            self.assertEqual(code, 0, stderr)
            self.assertIn("gating foo", stderr)

    def test_a_re_push_reuses_the_export_and_its_file_times(self) -> None:
        """Cargo fingerprints the export path; a new one per push rebuilt it all."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            stub = fixture.bin / "cargo"
            stub.write_text(
                stub.read_text(encoding="utf-8").replace(
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n',
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                    'if [ "$1" = clippy ]; then\n'
                    '  echo "$here $(stat -c %Y crates/foo/Cargo.toml)" >> "$FIXTURE_ROOT/exports.log"\n'
                    "fi\n",
                    1,
                ),
                encoding="utf-8",
            )
            _git(fixture.root, "switch", "-q", "-c", "feat")
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text(
                "pub fn g() {}\n", encoding="utf-8"
            )
            _commit_all(fixture.root, "feat")
            line = fixture.push_line_new_branch("feat")

            first_code, first = fixture.run_hook(line)
            time.sleep(1.1)
            second_code, second = fixture.run_hook(line)

            self.assertEqual((first_code, second_code), (0, 0), first + second)
            runs = (fixture.root / "exports.log").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(runs), 2, runs)
            self.assertEqual(runs[0], runs[1], "the export moved or rewrote an unchanged file")

    def test_an_export_isolated_from_the_source_repository(self) -> None:
        """An export reads its source while preserving the caller's Git state."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            base = pathlib.Path(temp)
            outer = base / "outer"
            source = base / "source"
            for repository, value in ((outer, "outer-content"), (source, "source-content")):
                _git_init_repo(repository)
                _write(repository / "value.txt", value)
                _git(repository, "add", "value.txt")
                _git(repository, "commit", "-m", "seed")
            source_head = _git(source, "rev-parse", "HEAD")
            source_tree = _git(source, "write-tree")
            repository_states = {
                repository: (
                    _git(repository, "rev-parse", "HEAD"),
                    _git(repository, "write-tree"),
                    _git(repository, "status", "--porcelain=v1"),
                    _git(repository, "config", "--local", "--list"),
                )
                for repository in (outer, source)
            }

            for declaration in ("absent", "unexported", "exported"):
                with self.subTest(declaration=declaration):
                    destination = base / f"export-{declaration}"
                    result = self._run_export(
                        source, outer, source_head, destination, declaration
                    )
                    self.assertEqual(
                        result.returncode,
                        0,
                        result.stderr.decode("utf-8", errors="replace"),
                    )
                    before = base / f"export-{declaration}-{declaration}-before"
                    after = base / f"export-{declaration}-{declaration}-after"
                    self.assertEqual(before.read_bytes(), after.read_bytes())
                    self.assertEqual(_git(destination, "rev-parse", "HEAD"), source_head)
                    self.assertEqual(_git(destination, "write-tree"), source_tree)
                    self.assertEqual(
                        (destination / "value.txt").read_bytes(), b"source-content"
                    )
                    self.assertTrue((destination / ".git" / "index").is_file())
                    self.assertEqual(
                        (destination / ".git" / "objects" / "info" / "alternates")
                        .read_text(encoding="utf-8").strip(),
                        f"{_git(source, 'rev-parse', '--path-format=absolute', '--git-common-dir')}/objects",
                    )
                    for key, value in (
                        ("core.longpaths", "true"),
                        ("gc.auto", "0"),
                        ("maintenance.auto", "false"),
                    ):
                        self.assertEqual(_git(destination, "config", "--get", key), value)

            reused = base / "export-exported"
            untracked = reused / "untracked.txt"
            untracked.write_bytes(b"remove after a complete replacement\n")
            repeated = self._run_export(
                source, outer, source_head, reused, "exported"
            )
            self.assertEqual(
                repeated.returncode,
                0,
                repeated.stderr.decode("utf-8", errors="replace"),
            )
            self.assertEqual(_git(reused, "rev-parse", "HEAD"), source_head)
            self.assertEqual(_git(reused, "write-tree"), source_tree)
            self.assertEqual((reused / "value.txt").read_bytes(), b"source-content")
            self.assertFalse(untracked.exists())

            for repository, state in repository_states.items():
                self.assertEqual(
                    (
                        _git(repository, "rev-parse", "HEAD"),
                        _git(repository, "write-tree"),
                        _git(repository, "status", "--porcelain=v1"),
                        _git(repository, "config", "--local", "--list"),
                    ),
                    state,
                )

    def test_a_missing_object_preserves_the_last_complete_export(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            base = pathlib.Path(temp)
            outer = base / "outer"
            source = base / "source"
            for repository in (outer, source):
                _git_init_repo(repository)
                _write(repository / "value.txt", f"{repository.name}\n")
                _git(repository, "add", "value.txt")
                _git(repository, "commit", "-m", "seed")
            destination = base / "export"
            source_head = _git(source, "rev-parse", "HEAD")
            valid = self._run_export(source, outer, source_head, destination, "exported")
            self.assertEqual(valid.returncode, 0, valid.stderr.decode(errors="replace"))
            previous_head = _git(destination, "rev-parse", "HEAD")
            previous_tree = _git(destination, "write-tree")
            sentinel = destination / "untracked.txt"
            sentinel.write_bytes(b"retain until a complete replacement\n")
            _write(source / "value.txt", "candidate-content")
            _git(source, "add", "value.txt")
            _git(source, "commit", "-m", "candidate")
            missing = _git(source, "rev-parse", "HEAD")
            missing_blob = _git(source, "rev-parse", "HEAD:value.txt")
            loose_blob = source / ".git" / "objects" / missing_blob[:2] / missing_blob[2:]
            self.assertTrue(loose_blob.is_file())
            loose_blob.chmod(stat.S_IWRITE)
            loose_blob.unlink()
            self.assertNotEqual(
                subprocess.run(
                    ["git", "-C", str(source), "cat-file", "-e", "HEAD:value.txt"],
                    capture_output=True,
                ).returncode,
                0,
            )

            failed = self._run_export(source, outer, missing, destination, "unexported")

            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(_git(destination, "rev-parse", "HEAD"), previous_head)
            self.assertEqual(_git(destination, "write-tree"), previous_tree)
            self.assertEqual(sentinel.read_bytes(), b"retain until a complete replacement\n")

    def test_the_gate_rebuilds_one_incomplete_export_then_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            base = pathlib.Path(temp)
            source = base / "source"
            _git_init_repo(source)
            _write(source / "value.txt", "source-content")
            _git(source, "add", "value.txt")
            _git(source, "commit", "-m", "seed")
            revision = _git(source, "rev-parse", "HEAD")
            destination = base / "export"
            valid = self._run_export(source, source, revision, destination, "absent")
            self.assertEqual(valid.returncode, 0, valid.stderr.decode(errors="replace"))
            (destination / ".git" / "index").unlink()
            (destination / ".git" / "index").mkdir()
            sentinel = destination / "untracked.txt"
            sentinel.write_bytes(b"discard an incomplete export\n")
            retry_trace = base / "retry-trace.json"

            retried = self._run_gate_export(
                source, revision, destination, retry_trace
            )

            self.assertEqual(
                retried.returncode, 0, retried.stderr.decode("utf-8", errors="replace")
            )
            self.assert_read_tree_count(retry_trace, 2)
            self.assertEqual(_git(destination, "rev-parse", "HEAD"), revision)
            self.assertFalse(sentinel.exists())
            self.assertTrue((destination / ".git" / "index").is_file())

            blocked_trace = base / "blocked-trace.json"
            blocked = self._run_gate_export(
                source, "1" * 40, destination, blocked_trace
            )

            stderr = blocked.stderr.decode("utf-8", errors="replace")
            self.assertEqual(blocked.returncode, 1, stderr)
            self.assert_read_tree_count(blocked_trace, 2)
            self.assertIn("could not export", stderr)
            self.assertIn("for the local gate", stderr)
            self.assertFalse((destination / "value.txt").exists())

    def test_the_lock_export_blocks_on_a_missing_real_object(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            base = pathlib.Path(temp)
            source = base / "source"
            _git_init_repo(source)
            _write(source / "Cargo.lock", "candidate-lock-content")
            _git(source, "add", "Cargo.lock")
            _git(source, "commit", "-m", "candidate")
            revision = _git(source, "rev-parse", "HEAD")
            blob = _git(source, "rev-parse", "HEAD:Cargo.lock")
            loose_blob = source / ".git" / "objects" / blob[:2] / blob[2:]
            self.assertTrue(loose_blob.is_file())
            loose_blob.chmod(stat.S_IWRITE)
            loose_blob.unlink()
            self.assertEqual(_git(source, "rev-parse", "--verify", "HEAD^{commit}"), revision)
            self.assertNotEqual(
                subprocess.run(
                    ["git", "-C", str(source), "cat-file", "-e", "HEAD:Cargo.lock"],
                    capture_output=True,
                ).returncode,
                0,
            )
            block = self._export_block(
                'if ! export_revision "$(git rev-parse --verify "$lock_rev^{commit}")" "$lock_export"; then',
                '\nfi\nif [ -n "$unmatched_stack" ]',
            ) + "\nfi"
            script = self._export_function() + "\n" + block
            trace = base / "lock-trace.json"
            environment = dict(os.environ)
            environment["GIT_TRACE2_EVENT"] = str(trace)
            result = subprocess.run(
                [
                    "bash", "-c",
                    'repo_git_dir="$1"; repo_store="$2"; lock_rev="$3"; '
                    'lock_export="$4"; shift 4; ' + script,
                    "lock-export",
                    _git(source, "rev-parse", "--absolute-git-dir"),
                    _git(source, "rev-parse", "--path-format=absolute", "--git-common-dir"),
                    revision,
                    str(base / "lock-export"),
                ],
                cwd=source,
                env=environment,
                capture_output=True,
            )

            stderr = result.stderr.decode("utf-8", errors="replace")
            self.assertEqual(result.returncode, 1, stderr)
            self.assert_read_tree_count(trace, 1)
            self.assertIn(blob, stderr)
            self.assertNotIn("not a git repository", stderr)
            self.assertIn("could not export", stderr)
            self.assertIn("for the lockfile check", stderr)

    def test_a_held_export_is_not_shared(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            _git(fixture.root, "switch", "-q", "-c", "feat")
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn g() {}\n", encoding="utf-8")
            _commit_all(fixture.root, "feat")
            fixture.run_hook(fixture.push_line_new_branch("feat"))
            locks = list(fixture.tmp.glob("pg-*"))
            stable = [path for path in locks if path.is_dir() and not path.name.endswith(".lock")]
            self.assertEqual(len(stable), 1, locks)
            _write(stable[0].with_name(stable[0].name + ".lock") / "pid", _live_msys_pid(self) + "\n")
            (fixture.root / "cwd.log").unlink()

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            self.assertIn("export is in use", stderr)
            for cwd in (fixture.root / "cwd.log").read_text(encoding="utf-8").split():
                self.assertNotIn(stable[0].name, cwd)

    def test_a_crate_without_tests_passes_the_test_step(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            stub = fixture.bin / "cargo"
            stub.write_text(
                stub.read_text(encoding="utf-8").replace(
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n',
                    'echo "$@" >> "$FIXTURE_ROOT/calls.log"\n'
                    'if [ "$1" = nextest ]; then\n'
                    '  case " $* " in *" --no-tests=pass "*) exit 0 ;; esac\n'
                    '  echo "error: no tests to run" >&2; exit 4\n'
                    "fi\n",
                    1,
                ),
                encoding="utf-8",
            )
            _git(fixture.root, "switch", "-q", "-c", "feat")
            (fixture.root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn g() {}\n", encoding="utf-8")
            _commit_all(fixture.root, "feat")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            self.assertNotIn("tests fail for", stderr)


class TemporaryOwnershipTestCase(unittest.TestCase):
    """Nothing a live or older run may still use is removed."""

    def test_an_ownerless_export_younger_than_a_day_survives(self) -> None:
        """An older hook records no owner and may still be building there."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            older = fixture.tmp / "pre-push-gate.old326"
            dead = fixture.tmp / "pl.dead01"
            _write(older / "tree" / "Cargo.toml", "[workspace]\n")
            _write(dead / "tree" / "Cargo.toml", "[workspace]\n")
            (dead / ".pre-push-owner").write_text("999999\n", encoding="utf-8")
            two_hours_ago = time.time() - 7200
            os.utime(older, (two_hours_ago, two_hours_ago))

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch("main").replace("refs/heads/main", "refs/heads/copy"),
                {"SKIP_LOCAL_GATE": "1"},
            )

            self.assertEqual(code, 0, stderr)
            self.assertTrue(older.exists(), "an ownerless export in use was swept")
            self.assertFalse(dead.exists(), "a dead run's export survived")

    def test_an_ownerless_export_older_than_a_day_is_swept(self) -> None:
        """No owner and no activity for a day: the run that wrote it is gone."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            abandoned = fixture.tmp / "pre-push-gate.old999"
            _write(abandoned / "tree" / "Cargo.toml", "[workspace]\n")
            two_days_ago = time.time() - 2 * 86400
            os.utime(abandoned, (two_days_ago, two_days_ago))

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch("main").replace("refs/heads/main", "refs/heads/copy"),
                {"SKIP_LOCAL_GATE": "1"},
            )

            self.assertEqual(code, 0, stderr)
            self.assertFalse(abandoned.exists(), "an abandoned export survived")

    def test_a_reusable_export_is_swept_only_after_a_week_without_a_holder(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = _stacked_fixture(temp)
            gone = fixture.tmp / "pg-0123456789"
            recent = fixture.tmp / "pg-9876543210"
            held = fixture.tmp / "pg-abcdefabcd"
            for export in (gone, recent, held):
                _write(export / "tree" / "Cargo.toml", "[workspace]\n")
            _write(fixture.tmp / "pg-0123456789.lock" / "pid", "999999\n")
            _write(fixture.tmp / "pg-abcdefabcd.lock" / "pid", f"{_live_msys_pid(self)}\n")
            for export, age_days in ((gone, 8), (recent, 6), (held, 8)):
                aged = time.time() - age_days * 86400
                os.utime(export, (aged, aged))

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch("main").replace("refs/heads/main", "refs/heads/copy"),
                {"SKIP_LOCAL_GATE": "1"},
            )

            self.assertEqual(code, 0, stderr)
            self.assertFalse(gone.exists(), "a week-old export with a dead holder survived")
            self.assertFalse((fixture.tmp / "pg-0123456789.lock").exists())
            self.assertTrue(recent.exists(), "an export younger than a week was removed")
            self.assertTrue(held.exists(), "an export a live run holds was removed")

    def test_a_checker_copy_in_use_is_not_pruned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, _, _, _ = DebtRatchetTestCase._stack(self, temp, 0)
            cache = pathlib.Path(temp) / ".git" / "atlas-checker"
            in_use = cache / ("a" * 40)
            unused = cache / ("b" * 40)
            for copy in (in_use, unused):
                _write(copy / "scripts" / "atlas_stack.py", "ROOT = None\n")
                two_hours_ago = time.time() - 7200
                os.utime(copy, (two_hours_ago, two_hours_ago))
            _write(cache / ".users" / f"{in_use.name}.{_live_msys_pid(self)}", "")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            self.assertTrue(in_use.exists(), "a copy a live gate reads was pruned")
            self.assertFalse(unused.exists(), "an unused old copy survived")


class SourceIdentityGateTestCase(unittest.TestCase):
    """A stack member's package steps run through the stack's identity checker."""

    def _member_at_pushed_tip(self, temp: str, identity: bool = True) -> tuple:
        """A registered member (the stack checker names it) pushing `feat`."""
        fixture, _, _, _, _ = DebtRatchetTestCase._stack(self, temp, 0, identity=identity)
        return pathlib.Path(temp), fixture

    def test_package_steps_run_through_the_identity_checker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack, fixture = self._member_at_pushed_tip(temp)
            log = stack / "identity-args.log"
            _write(
                stack / "scripts" / "atlas-build-identity.py",
                _recording_identity_invocation(log),
            )
            _publish_stack_scripts(stack)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1, lines)
            invocation = json.loads(lines[0])
            first = invocation["argv"]
            command = first[first.index("--") + 1:]
            self.assertEqual(command[0:2], ["bash", "-c"], command)
            self.assertIn('"$cargo_command" clippy --manifest-path', command[2])
            self.assertEqual(command[-2:], ["-p", "foo"])
            self.assertEqual(first[0], "run")
            self.assertEqual(first[first.index("--package") + 1], "foo")
            # One key for the step; the record is per package regardless.
            self.assertEqual(first[first.index("--command-key") + 1], "atlas-pre-push")
            self.assertNotIn("--ignore-path", first)
            pushed = _git(fixture.root, "rev-parse", "feat")
            self.assertEqual(invocation["root_head"], pushed)
            exported = pathlib.Path(first[first.index("--root") + 1]).resolve()
            self.assertNotIn(
                os.path.normcase(str(stack.resolve())), os.path.normcase(str(exported))
            )
            self.assertEqual(
                pathlib.Path(first[first.index("--target-dir") + 1]).resolve(),
                (stack / "target").resolve(),
            )

    def test_prepared_identity_checker_runs_from_the_selected_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack, fixture = self._member_at_pushed_tip(temp)
            log = stack / "prepared-identity-args.log"
            _write(
                stack / "scripts" / "atlas-build-identity.py",
                _recording_identity_invocation(log),
            )
            _commit_all(stack, "prepared tools")
            prepared = _git(stack, "rev-parse", "HEAD")

            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch("feat"),
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "atlas.preparedTools",
                    "GIT_CONFIG_VALUE_0": prepared,
                },
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn(prepared, stderr)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1, lines)
            invocation = json.loads(lines[0])
            ran_from = pathlib.Path(invocation["path"]).resolve()
            self.assertNotIn(stack.resolve(), ran_from.parents)
            self.assertEqual(invocation["argv"][0], "run")

    def test_a_missing_identity_checker_blocks_a_stack_member(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            _, fixture = self._member_at_pushed_tip(temp, identity=False)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 1, stderr)
            self.assertIn("source identity checker is missing", stderr)


class StackToolBaselineTestCase(unittest.TestCase):
    """Stack tools run from the stack's fetched default, not its checkout.

    The stack checkout sits on whatever branch a peer left there. On one cut
    before the secret scanner existed, the hook reported the scanner "not
    reachable" and pushed unscanned; on one before the identity checker, a
    registered member was blocked on a checker the default branch carried.
    """

    @staticmethod
    def _extracted(stack: pathlib.Path, ran_from: str) -> bool:
        cache = (stack / ".git" / "atlas-checker").resolve()
        return cache in pathlib.Path(ran_from).resolve().parents

    def test_a_baseline_secret_finding_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack = pathlib.Path(temp)
            fixture, _, _, _, pushed = DebtRatchetTestCase._stack(self, temp, 0)
            scan_log = stack / "secret-args.log"
            _write(stack / "scripts" / "atlas-secret-scan.py", _recording_tool(scan_log, 1))
            _publish_stack_scripts(stack, ("atlas-secret-scan.py",))

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 1, stderr)
            self.assertIn("adds a credential", stderr)
            self.assertNotIn("secret scanner not reachable", stderr)
            ran_from, *argv = scan_log.read_text(encoding="utf-8").split()
            self.assertTrue(self._extracted(stack, ran_from), ran_from)
            self.assertEqual(argv[argv.index("--rev") + 1], pushed)

    def test_the_baseline_identity_checker_runs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack, fixture = SourceIdentityGateTestCase._member_at_pushed_tip(self, temp)
            identity_log = stack / "identity-args.log"
            _write(
                stack / "scripts" / "atlas-build-identity.py",
                _recording_identity_invocation(identity_log),
            )
            _publish_stack_scripts(stack, ("atlas-build-identity.py",))

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            self.assertNotIn("identity checker is missing", stderr)
            lines = identity_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1, lines)
            invocation = json.loads(lines[0])
            ran_from = invocation["path"]
            argv = invocation["argv"]
            self.assertTrue(self._extracted(stack, ran_from), ran_from)
            self.assertEqual(argv[0], "run")
            self.assertEqual(argv[argv.index("--package") + 1], "foo")
            command = argv[argv.index("--") + 1:]
            self.assertEqual(command[0:2], ["bash", "-c"], command)
            self.assertIn('"$cargo_command" clippy --manifest-path', command[2])
            stages = [
                line for line in fixture.calls.read_text(encoding="utf-8").splitlines()
                if line.split()[0] in {"clippy", "nextest", "doc"}
            ]
            self.assertEqual([line.split()[0] for line in stages], ["clippy", "nextest", "doc"])
            for line in stages:
                values = line.split()
                self.assertEqual(
                    [values[index + 1] for index, value in enumerate(values) if value == "-p"],
                    ["foo"],
                )

    def test_a_tool_changed_only_in_the_checkout_is_not_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack = pathlib.Path(temp)
            fixture, _, _, _, _ = DebtRatchetTestCase._stack(self, temp, 0)
            scan_log = stack / "secret-args.log"
            stray = stack / "stray.log"
            _write(stack / "scripts" / "atlas-secret-scan.py", _recording_tool(scan_log, 0))
            _publish_stack_scripts(stack)
            # An uncommitted edit in the stack checkout, as a peer leaves one.
            _write(stack / "scripts" / "atlas-secret-scan.py", _recording_tool(stray, 1))

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertNotIn("adds a credential", stderr)
            self.assertFalse(stray.exists(), "the checkout's copy of the scanner ran")
            ran_from = scan_log.read_text(encoding="utf-8").split()[0]
            self.assertTrue(self._extracted(stack, ran_from), ran_from)
            assert_gated_on_the_export(self, code, stderr, fixture)
