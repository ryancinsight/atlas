#!/usr/bin/env python3
"""Integration tests for the owned member pre-push gate.

`scripts/git-hooks/pre-push` is the single source every member's
`.githooks/pre-push` copies. These tests drive
the script itself in fixture git repositories with stub `cargo`/`lockfile`
tools, so the range logic, the package mapper, and the blame classifier
are verified without a toolchain or network.
"""

from __future__ import annotations

import json
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


_FIXTURE_EXCLUDES = "upstream.git/\nbin/\ncalls.log\nlockfile-calls.log\n"


def assert_blocked_before_building(
    test: unittest.TestCase, code: int, stderr: str, fixture: "GateFixture"
) -> None:
    """The package gate refused to build a checkout other than the pushed tip.

    Every check before it reads the pushed revision; cargo reads the working
    tree, so an accepted verdict would describe a tree the push does not carry.
    """
    test.assertEqual(code, 1, stderr)
    test.assertIn("BLOCKED -- pushed revision", stderr)
    calls = fixture.calls.read_text(encoding="utf-8") if fixture.calls.is_file() else ""
    test.assertNotIn("-p foo", calls, "cargo ran against the checkout")


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
        # The stub toolchain and its call logs live inside the repository,
        # and the gate refuses a dirty checkout before building it. Excluded
        # from the first commit on, switching the stub's behaviour or logging
        # a call stays fixture plumbing instead of looking like work the
        # push does not carry.
        _write(root / ".git" / "info" / "exclude", _FIXTURE_EXCLUDES)
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
        self.set_workspace_packages(
            ["unrelated-member", "foo"] if layout == "crates" else ["solo"]
        )
        _write(root / "Cargo.lock", "# lock\n")
        # A stub lockfile checker in the member-local location the hook
        # expects; records invocation and exits as configured.
        _write(
            root / "scripts" / "lockfile.py",
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            f"pathlib.Path({str(root / 'lockfile-calls.log')!r}).write_text("
            "'called\\n')\n"
            "sys.exit(int(__import__('os').environ.get('LOCKFILE_EXIT', '0')))\n",
            executable=True,
        )
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

    def set_workspace_packages(
        self, names: list[str], workspace_root: pathlib.Path | None = None
    ) -> None:
        """Set the Cargo metadata returned by the fixture toolchain."""
        workspace_root = workspace_root or self.root
        packages = []
        for name in names:
            manifest = (
                workspace_root / "Cargo.toml"
                if self.layout == "single"
                else workspace_root / "crates" / name / "Cargo.toml"
            )
            packages.append(
                {
                    "id": f"fixture:{name}",
                    "name": name,
                    "manifest_path": str(manifest.resolve()),
                }
            )
        _write(
            self.bin / "metadata.json",
            json.dumps(
                {
                    "packages": packages,
                    "workspace_members": [package["id"] for package in packages],
                }
            ),
        )

    def set_cargo_behavior(self, mode: str) -> None:
        """Install a stub `cargo`: `pass`, `fail-fmt`, `fail-clippy-ours`,
        `fail-clippy-environment`, `fail-deny`, or `missing` (no stub on PATH).

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
                '  printf "%s\\n" "$CARGO_FAIL_LOG" >&2\n'
                "  exit 1\n"
                "fi\nexit 0\n"
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
            f'FIXTURE_ROOT="{self.root}"\n'
            'if [ "$1" = "metadata" ]; then\n'
            '  if [ "${CARGO_REAL_METADATA:-0}" = "1" ]; then exec "$ATLAS_REAL_CARGO" "$@"; fi\n'
            '  cat "$FIXTURE_ROOT/bin/metadata.json"\n'
            "  exit 0\n"
            "fi\n"
            'if [ "${CARGO_OBSERVE_LOCK:-0}" = "1" ] && [ "$1" != "fmt" ]; then\n'
            '  manifest=""\n'
            '  previous=""\n'
            '  for argument in "$@"; do\n'
            '    if [ "$previous" = "--manifest-path" ]; then manifest="$argument"; fi\n'
            '    previous="$argument"\n'
            '  done\n'
            '  if [ -z "$manifest" ]; then manifest="$PWD/Cargo.toml"; fi\n'
            '  if [ ! -f "$FIXTURE_ROOT/observed-lock" ]; then cat "$(dirname "$manifest")/Cargo.lock" > "$FIXTURE_ROOT/observed-lock"; fi\n'
            '  printf "%s" "${CARGO_TARGET_DIR:-}" > "$FIXTURE_ROOT/observed-target"\n'
            '  case " $* " in *" --locked "*) ;; *) echo "missing --locked" >&2; exit 77 ;; esac\n'
            'fi\n'
            'if [ "${CARGO_MUTATE_LOCK:-0}" = "1" ] && [ "$1" != "fmt" ]; then\n'
            '  manifest=""\n'
            '  previous=""\n'
            '  for argument in "$@"; do\n'
            '    if [ "$previous" = "--manifest-path" ]; then manifest="$argument"; fi\n'
            '    previous="$argument"\n'
            '  done\n'
            '  if [ -z "$manifest" ]; then manifest="$PWD/Cargo.toml"; fi\n'
            '  printf "# cargo rewrote this graph\\n" >> "$(dirname "$manifest")/Cargo.lock"\n'
            'fi\n'
            + body,
            executable=True,
        )

    def run_hook(self, push_lines: str, extra_env: dict | None = None) -> tuple:
        """Run the owned hook script in this fixture; return (exit, stderr)."""
        env = dict(os.environ)
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env["CARGO"] = str(self.cargo_launcher)
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


def _publish_stack_scripts(
    stack: pathlib.Path, remove_from_checkout: tuple = ()
) -> None:
    """Commit the stack checkout's `scripts/` and make that commit the stack's
    fetched default, which is where the hook runs stack tools from.

    Names in `remove_from_checkout` then leave the working tree, as they do
    when the stack checkout sits on a branch that predates them.
    """
    if not (stack / "scripts").is_dir():
        return
    if not (stack / ".git").exists():
        _git_init_repo(stack)
    subprocess.run(["git", "-C", str(stack), *_IDENT, "add", "scripts"], check=True)
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
            fixture = GateFixture(pathlib.Path(temp))
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

    def test_merged_default_assets_do_not_expand_the_feature_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
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
            fixture = GateFixture(pathlib.Path(temp))
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

    def test_excluded_workspace_changes_refuse_without_parent_package_flag(self) -> None:
        cases = (
            ("fuzz/src/main.rs", "consus-fuzz"),
            ("fuzz/corpus/seed", "consus-fuzz"),
            ("fuzz/src/name_collision.rs", "foo"),
        )
        for changed_path, package_name in cases:
            with self.subTest(
                changed_path=changed_path, package_name=package_name
            ), tempfile.TemporaryDirectory(
                prefix="atlas-gate-"
            ) as temp:
                fixture = GateFixture(pathlib.Path(temp))
                _write(
                    fixture.root / "fuzz" / "Cargo.toml",
                    f'[package]\nname = "{package_name}"\nversion = "0.0.0"\n'
                    '[workspace]\n',
                )
                subprocess.run(
                    ["git", "-C", str(fixture.root), *_IDENT, "add", "fuzz"],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                     "-m", "fuzz workspace"],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(fixture.root), *_IDENT, "push", "-q",
                     "origin", "HEAD:main"],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q",
                     "-b", "feat"],
                    check=True,
                )
                _write(fixture.root / changed_path, "changed\n")
                subprocess.run(
                    ["git", "-C", str(fixture.root), *_IDENT, "add", changed_path],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
                     "-m", "fuzz input"],
                    check=True,
                )

                code, stderr = fixture.run_hook(fixture.push_line_new_branch())

                self.assertEqual(code, 1, stderr)
                self.assertIn("excluded from the parent", stderr)
                self.assertIn("fuzz/Cargo.toml", stderr)
                calls = (
                    fixture.calls.read_text(encoding="utf-8")
                    if fixture.calls.exists()
                    else ""
                )
                self.assertNotIn("-p consus-fuzz", calls)
                if package_name == "foo":
                    self.assertNotIn("clippy", calls)

    def test_nested_virtual_workspace_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
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
            self.assertEqual(code, 0, stderr)
            self.assertIn("gating solo", stderr)
            calls = (fixture.root / "calls.log").read_text(encoding="utf-8")
            self.assertIn("-p solo", calls)
            self.assertIn("doc --no-deps -p solo", calls)


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

    def test_rustdoc_failure_inside_repo_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
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
            fixture.set_cargo_behavior("fail-doc")
            code, stderr = fixture.run_hook(
                fixture.push_line_new_branch(),
                extra_env={"CARGO_FAIL_LOG": self.inside_log.format(root=root)},
            )
            self.assertEqual(code, 1, stderr)
            self.assertIn("rustdoc fails for", stderr)

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

    def test_locked_metadata_failure_reports_the_overlay_environment(self) -> None:
        log = (
            "error: cargo metadata failed for Cargo.toml: cannot update the lock file "
            "because --locked was passed\n"
        )
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            code, stderr = self._gate(GateFixture(pathlib.Path(temp)), log)
        self.assertEqual(code, 0, stderr)
        self.assertIn("dependency graph is broken", stderr)

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
            fixture = GateFixture(pathlib.Path(temp))
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
            fixture = GateFixture(pathlib.Path(temp))
            if ratchet_exit is not None:
                _write(
                    fixture.root / "scripts" / "safety_ratchet.py",
                    "#!/usr/bin/env python3\n"
                    "import pathlib, sys\n"
                    "assert sys.argv[1:] == ['check'], sys.argv\n"
                    "pathlib.Path('ratchet-calls.log').write_text('called')\n"
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
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "crates", "scripts"],
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
            fixture = GateFixture(pathlib.Path(temp))
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
            fixture = GateFixture(pathlib.Path(temp))
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

            assert_blocked_before_building(self, code, stderr, fixture)
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

    def test_lock_bytes_survive_a_failing_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            lock = fixture.root / "Cargo.lock"
            before = lock.read_bytes()
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q", "-b", "feat"],
                check=True,
            )
            _write(fixture.root / "crates" / "foo" / "src" / "lib.rs", "pub fn g() {}\n")
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "add", "-A"], check=True
            )
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q", "-m", "src"],
                check=True,
            )
            fixture.set_cargo_behavior("fail-doc")
            code, _ = fixture.run_hook(
                fixture.push_line_new_branch(),
                {"CARGO_MUTATE_LOCK": "1"},
            )
            self.assertEqual(code, 1)
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
        runs the pushed revision's own checker, so `drop_checker` removes it
        from the commit, not just from the working tree.
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
            subprocess.run(
                ["git", "-C", str(fixture.root), *_IDENT, "rm", "-q",
                 "scripts/lockfile.py"],
                check=True,
            )
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "commit", "-q",
             "-m", "lock"],
            check=True,
        )
        return fixture.push_line_new_branch()

    def test_absent_checker_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            push_line = self._branch_touching_the_lock(fixture, drop_checker=True)
            code, stderr = fixture.run_hook(push_line)
            self.assertNotEqual(code, 0)
            self.assertIn("lockfile.py not present", stderr)
            self.assertNotIn("SKIP_LOCKFILE_CHECK", stderr)

    def test_absent_interpreter_refuses_the_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
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
            fixture = GateFixture(pathlib.Path(temp))
            push_line = self._branch_touching_the_lock(fixture, drop_checker=True)
            code, stderr = fixture.run_hook(
                push_line, extra_env={"SKIP_LOCKFILE_CHECK": "1"}
            )
            self.assertNotEqual(code, 0, stderr)
            self.assertIn("SKIP_LOCKFILE_CHECK is no longer honoured", stderr)
            self.assertIn("lockfile.py not present", stderr)

    def test_skip_variable_cannot_hide_a_failing_lock(self) -> None:
        """A lock the checker rejects still refuses the push under the skip var."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            push_line = self._branch_touching_the_lock(fixture)
            code, stderr = fixture.run_hook(
                push_line,
                extra_env={"SKIP_LOCKFILE_CHECK": "1", "LOCKFILE_EXIT": "1"},
            )
            self.assertNotEqual(code, 0, stderr)
            self.assertIn("SKIP_LOCKFILE_CHECK is no longer honoured", stderr)
            self.assertIn("does not resolve under --locked", stderr)


class DenySourcesTestCase(unittest.TestCase):
    """A lock-changing push checks dependency sources on an export."""

    def _push(self, mode: str, change: str) -> tuple:
        temp = tempfile.TemporaryDirectory(prefix="pre-push-deny-")
        self.addCleanup(temp.cleanup)
        fixture = GateFixture(pathlib.Path(temp.name))
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
        fixture.set_workspace_packages(["unrelated-member", "foo"], lane)
        if target_directory is not None:
            metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
            metadata["target_directory"] = str(target_directory)
            _write(fixture.bin / "metadata.json", json.dumps(metadata))
        env = dict(os.environ)
        env["PATH"] = str(fixture.bin) + os.pathsep + env.get("PATH", "")
        env.pop("CARGO_TARGET_DIR", None)
        real_cargo = shutil.which("cargo")
        self.assertIsNotNone(real_cargo)
        env["CARGO_REAL_METADATA"] = "1"
        env["ATLAS_REAL_CARGO"] = real_cargo
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

    def test_a_lane_missing_a_tracked_manifest_is_refused_before_gating(self) -> None:
        _, fixture, lane = self._lane(overlay=True)
        (lane / "crates" / "foo" / "Cargo.toml").unlink()
        code, err = self._run_in_lane(fixture, lane)
        self.assertEqual(code, 1, err)
        self.assertIn("checkout has uncommitted changes", err)
        calls = fixture.calls.read_text(encoding="utf-8") if fixture.calls.is_file() else ""
        self.assertNotIn("clippy", calls)

    def test_a_lane_runs_the_committed_safety_checker(self) -> None:
        _, fixture, lane = self._lane(overlay=True)
        checker = lane / "scripts" / "safety_ratchet.py"
        checker.parent.mkdir(parents=True, exist_ok=True)
        checker.write_text("import sys; sys.exit(1)\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(lane), *_IDENT, "add", "scripts/safety_ratchet.py"], check=True)
        subprocess.run(["git", "-C", str(lane), *_IDENT, "commit", "-q", "-m", "checker"], check=True)
        code, err = self._run_in_lane(fixture, lane)
        self.assertEqual(code, 1, err)
        self.assertIn("SAFETY ratchet fails", err)

    def test_a_lane_classifies_exported_diagnostic_paths_as_ours(self) -> None:
        _, fixture, lane = self._lane(overlay=True)
        fixture.set_cargo_behavior("fail-clippy-ours")
        log = self.inside_log.replace("{root}", "__GATE_CWD__")
        code, err = self._run_in_lane(fixture, lane, {"CARGO_FAIL_LOG": log})
        self.assertEqual(code, 1, err)
        self.assertIn("clippy fails", err)

    def test_a_lane_gates_from_outside_the_stack_with_its_manifest(self) -> None:
        stack, fixture, lane = self._lane(overlay=True)
        code, err = self._run_in_lane(fixture, lane)
        self.assertEqual(code, 0, err)
        self.assertIn("gating outside the stack overlay", err)
        calls = fixture.calls.read_text(encoding="utf-8")
        self.assertIn("--manifest-path", calls)
        fmt = [line for line in calls.splitlines() if line.startswith("fmt ")]
        self.assertTrue(fmt and all(line.startswith("fmt --all ") for line in fmt), fmt)
        for cwd in (fixture.root / "cwd.log").read_text(encoding="utf-8").split():
            self.assertNotIn(
                os.path.normcase(str(stack.resolve())), os.path.normcase(str(pathlib.Path(cwd).resolve())),
                "cargo must not run inside the stack",
            )

    def test_a_lane_maps_real_metadata_from_the_exported_revision(self) -> None:
        _, fixture, lane = self._lane(overlay=True)
        real_cargo = shutil.which("cargo")
        self.assertIsNotNone(real_cargo)
        code, err = self._run_in_lane(
            fixture,
            lane,
            {"CARGO_REAL_METADATA": "1", "ATLAS_REAL_CARGO": real_cargo},
        )
        self.assertEqual(code, 0, err)
        self.assertIn("clippy", fixture.calls.read_text(encoding="utf-8"))

    def test_a_lane_uses_the_committed_lock_and_locked_commands(self) -> None:
        stack, fixture, lane = self._lane(overlay=True)
        committed = subprocess.run(
            ["git", "-C", str(lane), "show", "HEAD:Cargo.lock"],
            check=True,
            capture_output=True,
        ).stdout
        working = b"# overlay-flattened working lock\n"
        (lane / "Cargo.lock").write_bytes(working)
        code, err = self._run_in_lane(
            fixture,
            lane,
            {"CARGO_OBSERVE_LOCK": "1", "CARGO_MUTATE_LOCK": "1"},
        )
        self.assertEqual(code, 0, err)
        self.assertEqual((lane / "Cargo.lock").read_bytes(), working)
        self.assertEqual(
            (fixture.root / "observed-lock").read_bytes().replace(b"\r\n", b"\n"),
            committed.replace(b"\r\n", b"\n"),
        )
        observed_target = (fixture.root / "observed-target").read_text(encoding="utf-8")
        self.assertTrue(observed_target, "lane gate dropped CARGO_TARGET_DIR")
        self.assertEqual(pathlib.PurePosixPath(observed_target.replace("\\", "/")).name, "target")
        calls = fixture.calls.read_text(encoding="utf-8")
        required_commands = ("clippy", "doc")
        if shutil.which("cargo-nextest") is not None:
            required_commands += ("nextest",)
        for command in required_commands:
            matching = [line for line in calls.splitlines() if line.startswith(command)]
            self.assertTrue(matching, calls)
            self.assertTrue(all("--locked" in line for line in matching), matching)

    def test_a_lane_keeps_the_working_lock_after_a_failed_command(self) -> None:
        _, fixture, lane = self._lane(overlay=True)
        working = b"# overlay-flattened working lock\n"
        (lane / "Cargo.lock").write_bytes(working)
        fixture.set_cargo_behavior("fail-doc")
        code, err = self._run_in_lane(
            fixture,
            lane,
            {"CARGO_OBSERVE_LOCK": "1", "CARGO_MUTATE_LOCK": "1"},
        )
        self.assertEqual(code, 1, err)
        self.assertEqual((lane / "Cargo.lock").read_bytes(), working)
        self.assertEqual(
            (fixture.root / "observed-lock").read_bytes().replace(b"\r\n", b"\n"),
            subprocess.run(
                ["git", "-C", str(lane), "show", "HEAD:Cargo.lock"],
                check=True,
                capture_output=True,
            ).stdout.replace(b"\r\n", b"\n"),
        )

    def test_a_lane_without_an_overlay_gates_in_place(self) -> None:
        _, fixture, lane = self._lane(overlay=False)
        code, err = self._run_in_lane(fixture, lane)
        self.assertEqual(code, 0, err)
        self.assertNotIn("gating outside the stack overlay", err)
        self.assertNotIn("--manifest-path", fixture.calls.read_text(encoding="utf-8"))
        self.assertIn("fmt -- --check\n", fixture.calls.read_text(encoding="utf-8"))

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
            "import pathlib, sys\n"
            f"log = pathlib.Path({str(log)!r})\n"
            "command = sys.argv[sys.argv.index('--') + 1:]\n"
            "with log.open('a', encoding='utf-8') as stream:\n"
            "    stream.write(' '.join(command) + '\\n')\n",
        )
        code, err = self._run_in_lane(fixture, lane, target_directory=stack / "target")
        self.assertEqual(code, 0, err)
        commands = [line.split() for line in log.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(any("clippy" in command for command in commands), commands)
        for command in commands:
            self.assertIn(command[0], ("cargo", "env"), command)
            cargo = command.index("cargo")
            manifest = command.index("--manifest-path")
            self.assertGreater(manifest, cargo + 1, command)
            self.assertEqual(
                pathlib.Path(command[manifest + 1]).resolve(),
                (lane / "Cargo.toml").resolve(),
            )

    def test_a_lane_reproduce_line_is_a_runnable_command(self) -> None:
        """The lane manifest is a separate argument, not glued to the flag.

        Only the lane path sets a manifest, and the reproduce lines render it
        by interpolation; without a leading space the flag joined its
        subcommand (`cargo doc --no-deps--manifest-path ...`), so the one
        command an author copies out of a refusal did not run.
        """
        _, fixture, lane = self._lane(overlay=True)
        fixture.set_cargo_behavior("fail-doc")
        env = {"CARGO_FAIL_LOG": self.inside_log.replace(
            "{root}", "__GATE_CWD__"
        )}
        code, err = self._run_in_lane(fixture, lane, extra_env=env)
        self.assertEqual(code, 1, err)
        reproduce = [
            line.strip() for line in err.splitlines() if "cargo doc" in line
        ]
        self.assertTrue(reproduce, err)
        for line in reproduce:
            self.assertIn("--no-deps --manifest-path", line)
            self.assertNotIn("--no-deps--", line)

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

    def test_a_branch_pushed_while_head_sits_elsewhere_blocks_before_building(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            self._commit_rust_on_a_branch_then_leave_it(fixture)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch())

            # The range is still found (no silent "not needed"), but the
            # package gate will not build a checkout the push does not carry.
            self.assertNotIn("local gate not needed", stderr)
            assert_blocked_before_building(self, code, stderr, fixture)

    def test_an_unresolvable_pushed_base_falls_back_rather_than_skipping(self) -> None:
        """A remote tip this clone never fetched cannot be diffed against;
        reading that as an empty range would skip the gate silently."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            self._commit_rust_on_a_branch_then_leave_it(fixture)
            tip = _git(fixture.root, "rev-parse", "feat")
            absent = "0123456789abcdef0123456789abcdef01234567"

            code, stderr = fixture.run_hook(
                f"refs/heads/feat {tip} refs/heads/feat {absent}\n"
            )

            self.assertNotIn("local gate not needed", stderr)
            assert_blocked_before_building(self, code, stderr, fixture)


class DebtRatchetTestCase(unittest.TestCase):
    """The conformance ratchet runs on the pushed revision, as CI runs it.

    metis#394 passed every local stage and then failed CI's conformance job
    on `oversized_files: 0 -> 1`: nothing local ran the ratchet. The hook
    must judge the pushed tip (never the checkout, which a peer may hold on
    another branch), against the baseline committed at the stack's default
    branch (never its working copy), bounded by the range's base.
    """

    def _stack(
        self, temp: str, exit_code: int, revision_scans: bool = True,
        location: str = "repos",
    ) -> tuple:
        stack = pathlib.Path(temp)
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
        _git_init_repo(stack)
        subprocess.run(["git", "-C", str(stack), *_IDENT, "add", "scripts"], check=True)
        subprocess.run(
            ["git", "-C", str(stack), *_IDENT, "commit", "-q", "-m", "stack"], check=True
        )
        stack_head = _git(stack, "rev-parse", "HEAD")
        _git(stack, "update-ref", "refs/remotes/origin/main", stack_head)
        (stack / "repos").mkdir(exist_ok=True)
        fixture = GateFixture(stack / location / "member")
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
            assert_blocked_before_building(self, code, stderr, fixture)
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
            assert_blocked_before_building(self, code, stderr, fixture)
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
            assert_blocked_before_building(self, code, stderr, fixture)
            self.assertTrue(log.is_file())
            self.assertFalse(stray.exists(), "the working-tree checker ran")
            # A second push reuses the extracted revision.
            cache = pathlib.Path(temp) / ".git" / "atlas-checker"
            self.assertEqual(len([p for p in cache.iterdir() if p.is_dir()]), 1)
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            assert_blocked_before_building(self, code, stderr, fixture)
            self.assertEqual(len([p for p in cache.iterdir() if p.is_dir()]), 1)

    @staticmethod
    def _git_push(fixture: GateFixture, cwd: pathlib.Path, *refspec: str) -> tuple:
        """Push through git itself, so the hook sees the environment git gives
        hooks -- `GIT_DIR` among it, absolute in a lane -- not a bare shell's.
        """
        env = dict(os.environ)
        env["PATH"] = str(fixture.bin) + os.pathsep + env.get("PATH", "")
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

    def test_an_unregistered_checkout_is_not_gated(self) -> None:
        """No `repos/` entry shares this checkout's store, so it has no row."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture, log, _, _, _ = self._stack(temp, 1, location="scratch")
            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))
            self.assertFalse(log.is_file())
            assert_blocked_before_building(self, code, stderr, fixture)
            self.assertIn("not a registered stack member", stderr)


class CheckoutIdentityTestCase(unittest.TestCase):
    """The package gate builds only the tree the push carries."""

    def test_a_dirty_checkout_is_blocked_before_building(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            root = fixture.root
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "feat"], check=True
            )
            (root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn f() {}\n// pushed\n")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-am", "pushed"], check=True
            )
            # Cargo would compile this uncommitted module; the push would not carry it.
            (root / "crates" / "foo" / "src" / "scratch.rs").write_text("pub fn g() {}\n")

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 1, stderr)
            self.assertIn("checkout has uncommitted changes", stderr)
            calls = fixture.calls.read_text(encoding="utf-8") if fixture.calls.is_file() else ""
            self.assertNotIn("-p foo", calls)

    def test_an_overlay_rewritten_lock_does_not_block_the_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            root = fixture.root
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "feat"], check=True
            )
            (root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn f() {}\n// pushed\n")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-am", "pushed"], check=True
            )
            working = "# flattened by the overlay\n"
            (root / "Cargo.lock").write_text(working)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            self.assertNotIn("checkout has uncommitted changes", stderr)
            self.assertIn("-p foo", fixture.calls.read_text(encoding="utf-8"))
            self.assertEqual((root / "Cargo.lock").read_text(), working)

    def test_a_hook_publication_from_another_checkout_is_accepted(self) -> None:
        """The publisher pushes `ci/sync-stack-hooks` without checking it out."""
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            root = fixture.root
            base = _git(root, "rev-parse", "main")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "ci/sync-stack-hooks"],
                check=True,
            )
            _write(root / ".githooks" / "pre-push", "#!/bin/sh\nexit 0\n", executable=True)
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "add", ".githooks/pre-push"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-m",
                 "ci: Sync the stack-owned git hooks"],
                check=True,
            )
            tip = _git(root, "rev-parse", "HEAD")
            subprocess.run(["git", "-C", str(root), *_IDENT, "checkout", "-q", "main"], check=True)

            code, stderr = fixture.run_hook(
                f"refs/heads/ci/sync-stack-hooks {tip} refs/heads/ci/sync-stack-hooks {base}\n"
            )

            self.assertEqual(code, 0, stderr)
            self.assertIn("canonical hook publication accepted", stderr)
            self.assertNotIn("BLOCKED", stderr)

    def test_a_publication_subject_on_other_paths_is_not_a_publication(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            fixture = GateFixture(pathlib.Path(temp))
            root = fixture.root
            base = _git(root, "rev-parse", "main")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "checkout", "-q", "-b", "ci/sync-stack-hooks"],
                check=True,
            )
            (root / "crates" / "foo" / "src" / "lib.rs").write_text("pub fn f() {}\n// smuggled\n")
            subprocess.run(
                ["git", "-C", str(root), *_IDENT, "commit", "-q", "-am",
                 "ci: Sync the stack-owned git hooks"],
                check=True,
            )
            tip = _git(root, "rev-parse", "HEAD")
            subprocess.run(["git", "-C", str(root), *_IDENT, "checkout", "-q", "main"], check=True)

            code, stderr = fixture.run_hook(
                f"refs/heads/ci/sync-stack-hooks {tip} refs/heads/ci/sync-stack-hooks {base}\n"
            )

            self.assertNotIn("canonical hook publication accepted", stderr)
            assert_blocked_before_building(self, code, stderr, fixture)


class SourceIdentityGateTestCase(unittest.TestCase):
    """A stack member's package steps run through the stack's identity checker."""

    def _member_at_pushed_tip(self, temp: str) -> tuple:
        """A registered member (the stack checker names it) checked out at the tip."""
        fixture, _, _, _, _ = DebtRatchetTestCase._stack(self, temp, 0)
        stack = pathlib.Path(temp)
        metadata = json.loads((fixture.bin / "metadata.json").read_text(encoding="utf-8"))
        metadata["target_directory"] = str(stack / "target")
        _write(fixture.bin / "metadata.json", json.dumps(metadata))
        subprocess.run(
            ["git", "-C", str(fixture.root), *_IDENT, "checkout", "-q", "feat"], check=True
        )
        return stack, fixture

    def test_package_steps_run_through_the_identity_checker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            stack, fixture = self._member_at_pushed_tip(temp)
            log = stack / "identity-args.log"
            _write(
                stack / "scripts" / "atlas-build-identity.py",
                "import os, pathlib, subprocess, sys\n"
                f"log = pathlib.Path({str(log)!r})\n"
                "with log.open('a', encoding='utf-8') as stream:\n"
                "    stream.write(' '.join(sys.argv[1:]) + '\\n')\n"
                "command = [os.environ.get('CARGO', 'cargo') if value == 'cargo' else value for value in sys.argv[sys.argv.index('--') + 1:]]\n"
                "raise SystemExit(subprocess.run(command).returncode)\n",
            )
            _publish_stack_scripts(stack)

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any("cargo clippy -p foo" in line for line in lines), lines)
            first = lines[0].split()
            self.assertEqual(first[0], "run")
            self.assertEqual(first[first.index("--package") + 1], "foo")
            self.assertEqual(first[first.index("--command-key") + 1], "atlas-pre-push:foo")
            self.assertEqual(
                pathlib.Path(first[first.index("--ignore-path") + 1]).name, "Cargo.lock"
            )
            self.assertEqual(
                pathlib.Path(first[first.index("--target-dir") + 1]).resolve(),
                (stack / "target").resolve(),
            )

    def test_a_missing_identity_checker_blocks_a_stack_member(self) -> None:
        with tempfile.TemporaryDirectory(prefix="atlas-gate-") as temp:
            _, fixture = self._member_at_pushed_tip(temp)

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
                _recording_tool(identity_log, 0),
            )
            _publish_stack_scripts(stack, ("atlas-build-identity.py",))

            code, stderr = fixture.run_hook(fixture.push_line_new_branch("feat"))

            self.assertEqual(code, 0, stderr)
            self.assertNotIn("identity checker is missing", stderr)
            lines = identity_log.read_text(encoding="utf-8").splitlines()
            self.assertTrue(lines, "the identity checker did not run")
            ran_from, mode, *argv = lines[0].split()
            self.assertTrue(self._extracted(stack, ran_from), ran_from)
            self.assertEqual(mode, "run")
            self.assertEqual(argv[argv.index("--package") + 1], "foo")
            self.assertTrue(
                any("cargo clippy" in line and "-p foo" in line for line in lines), lines
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
            assert_blocked_before_building(self, code, stderr, fixture)
