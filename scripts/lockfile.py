#!/usr/bin/env python3
"""Regenerate or check `Cargo.lock` against the source set CI actually resolves.

# The trap this exists for

This repository is normally worked on inside the Atlas stack, whose
`.cargo/config.toml` carries a `[patch]` overlay redirecting every first-party
dependency to a local working tree. Cargo discovers that config by walking up
from the *current directory*, so any `cargo` command run from inside the stack
picks it up -- including anything that rewrites the lock.

A lock written with the overlay active has every `source = "git+..."` line
**stripped**, because those dependencies resolved to local paths rather than to
git. Committing it replaces all 87 git sources with nothing. CI has no overlay,
so it re-resolves, and every `--locked` job fails with

    error: cannot update the lock file ... because --locked was passed

which names neither the cause nor the fix. That message is also what a merely
*stale* lock produces -- one pinning first-party revisions whose versions no
longer satisfy the manifests -- so the two failures are indistinguishable from
the log alone (KW-CI-087).

This is not limited to deliberate regeneration. *Any* cargo invocation that
updates the lock while the overlay is active flattens it -- an ordinary
`cargo check` inside the stack is enough, which is how it happens in practice:
nobody sets out to rewrite the lock. Treat a modified `Cargo.lock` after routine
work as suspect and run `--check` before staging it.

Both are fixed the same way: regenerate from outside the overlay. This script
does that by running cargo from a temporary directory that is not underneath the
stack root, which is the whole mechanism -- there is no flag that disables config
discovery.

# Usage

    scripts/lockfile.py --check          # verify the committed lock resolves
    scripts/lockfile.py --check-staged   # judge the staged locks, index only
    scripts/lockfile.py --check-committed REPOSITORY...
                                         # judge every tracked lock at HEAD
    scripts/lockfile.py --regenerate     # repair it, advancing no pin (needs network)

This is the stack's one lockfile checker, and the one place the rule defining a
standalone lock lives (ADR-0044): `--check`, `--check-staged` and
`--check-committed` all judge a lock by `judge_locks`. The `pre-commit` hook
runs `--check-staged`, `pre-push` and the shared `lockfile-guard` workflow run
`--check --manifest-path`, and the conformance workflow runs
`--check-committed`. The hooks run the copy of this script that the repository
they guard carries. The file imports nothing beside the standard library because
the hooks export it alone, which is why it stays one file.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import signal
import subprocess
import posixpath
import sys
import tempfile
import tomllib
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple

REPOSITORY = Path(__file__).resolve().parent.parent
# The checkout this script belongs to. The shared `lockfile-guard` workflow
# checks Atlas out inside the repository it judges, and that copy is not part of
# the repository.
SCRIPT_CHECKOUT = REPOSITORY
LOCKFILE = REPOSITORY / "Cargo.lock"
MANIFEST = REPOSITORY / "Cargo.toml"

# A first-party source retains the revision and URL spelling because both take
# part in provider-identity comparison.
FIRST_PARTY_GIT = "git+https://github.com/ryancinsight/"

# A member records how many first-party providers its graph currently resolves
# through more than one source, as a single integer beside its lock. The file is
# a ratchet: the check fails when the measured excess exceeds it, and the number
# is lowered as the dependency-ordered unpin sweep closes each fork. Absent, the
# check reports and does not fail -- a member that has never measured its graph
# is not failed by a guard it has not adopted.
PROVIDER_IDENTITY_BASELINE_NAME = ".provider-identity-baseline"

# What a failing check tells the reader to run: the stack's copy of this script,
# which every member can reach whether or not it carries one of its own.
REGENERATE_COMMAND = (
    "python3 <stack>/scripts/lockfile.py --regenerate --manifest-path Cargo.toml"
)

# A standalone lock carries no `[[patch.unused]]` table: a `[patch]` the build
# did not consume leaves one, so it appears only when the stack overlay was
# active.
PATCH_UNUSED = "[[patch.unused]]"
DEPENDENCY_KINDS = ("dependencies", "dev-dependencies", "build-dependencies")
# Manifests under these directories are build output or vendored, not part of
# any workspace.
IGNORED_DIRECTORIES = frozenset({"target", ".git", "node_modules"})
GIT_DEADLINE_SECONDS = 60

# One cargo invocation is bounded: `cargo metadata --locked` and the consumer
# sweep's `cargo update` both fetch first-party git sources, and a fetch that
# hangs must fail the push rather than stall it. The `lockfile-guard` workflow
# bounds the same run at five minutes from the outside; this is the deadline
# the runner itself owns, so it also holds where no workflow wraps it.
CARGO_DEADLINE_SECONDS = 600
# A killed tree is already dead; this bounds only the wait to reap the launcher
# and collect the output it wrote before the deadline.
PROCESS_TREE_CLEANUP_SECONDS = 10.0
# What the runner launches. A test replaces this with a stand-in so the
# deadline and the tree kill are exercised without cargo.
CARGO_COMMAND: tuple[str, ...] = ("cargo",)


class CargoDeadlineExceeded(subprocess.TimeoutExpired):
    """cargo outlived its deadline; its process tree has been killed.

    A typed timeout rather than a return code, because the two failures cargo
    produces here mean different things: a nonzero exit is a resolution that
    ran and refused, while an expired deadline is a run that never finished.
    Reporting the second as the first would blame the lock for a hung fetch.
    """


class CargoMetadataError(RuntimeError):
    """A locked Cargo graph is unavailable, mutable, or structurally unreadable."""


def _kill_process_tree(process: subprocess.Popen[str]) -> None:
    """Kill `process` and every descendant it started.

    The tree is the point: `cargo metadata` starts a rustc and git fetches, and
    killing only the launcher leaves them holding the network and the lock.
    POSIX starts the launcher in its own session, so one `killpg` retires the
    group. Windows has no equivalent without a job object, and this file is
    exported alone to the hooks, so it uses `taskkill /T` instead.
    """
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
                timeout=PROCESS_TREE_CLEANUP_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except OSError:
            pass
    if process.poll() is None:
        process.kill()


def run_bounded(
    command: Sequence[str], *, cwd: Path, env: Mapping[str, str], deadline: float
) -> subprocess.CompletedProcess[str]:
    """Run `command`, killing its whole process tree if it outlives `deadline`.

    `subprocess.run(timeout=...)` kills the launcher only, so the runner owns
    the launch: a timeout is followed by [`_kill_process_tree`] and only then by
    a collected result. A timeout raises [`CargoDeadlineExceeded`] carrying the
    output the command managed to write before it was stopped.
    """
    process = subprocess.Popen(
        tuple(command),
        cwd=cwd,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # `text=True` alone decodes with the locale codepage. Cargo emits UTF-8,
        # so on a Windows console (cp1252) subprocess's reader thread dies on
        # the first byte it cannot map and the captured stream is lost. The
        # verdict survives -- it comes from `returncode` -- but the message
        # explaining a failure does not, which is the one moment it is needed.
        text=True,
        encoding="utf-8",
        errors="replace",
        # The POSIX tree is the process group: the launcher must lead its own
        # session for `killpg` to reach a descendant cargo did not reap.
        start_new_session=os.name != "nt",
    )
    try:
        stdout, stderr = process.communicate(timeout=deadline)
    except subprocess.TimeoutExpired:
        _kill_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=PROCESS_TREE_CLEANUP_SECONDS)
        except subprocess.TimeoutExpired:
            stdout, stderr = "", ""
        note = (
            f"cargo did not finish within {deadline:g}s; "
            "its process tree was killed."
        )
        raise CargoDeadlineExceeded(
            tuple(command), deadline, output=stdout, stderr=(stderr + "\n" + note).strip()
        ) from None
    return subprocess.CompletedProcess(tuple(command), process.returncode, stdout, stderr)


def shared_target_dir(manifest: Path) -> Path | None:
    """The `target-dir` a stack config above `manifest` declares, if any.

    The neutral working directory below disables cargo's config discovery on
    purpose — that is what excludes the `[patch]` overlay. It excludes the rest
    of the config with it, and `target-dir` is in the rest: cargo then falls
    back to `<manifest dir>/target` and writes a repo-local cache inside the
    member. That is the `target_forks` debt class the conformance ratchet
    counts, produced by the tooling that measures it.

    Walking up from the manifest rather than from the cwd is the correction:
    the overlay is excluded because of *where cargo runs*, and the target
    directory is restored because of *what is being built*.
    """
    for directory in [manifest.parent, *manifest.parent.parents]:
        config = directory / ".cargo" / "config.toml"
        if not config.is_file():
            continue
        for line in config.read_text(encoding="utf-8").splitlines():
            stripped = line.split("#", 1)[0].strip()
            if not stripped.startswith("target-dir"):
                continue
            _, _, value = stripped.partition("=")
            value = value.strip().strip('"').strip("'")
            if value:
                return (directory / value).resolve()
    return None



def run_outside_the_overlay(
    arguments: list[str],
    manifest: Path | None = None,
    *,
    deadline: float = CARGO_DEADLINE_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Run cargo with a working directory outside the stack root.

    Cargo resolves `.cargo/config.toml` by walking up from the working
    directory, never from `--manifest-path`, so this is what excludes the
    overlay. Running from the repository itself would silently include it.

    `manifest` defaults to `MANIFEST` as it stands at call time -- `main`
    reassigns it under `--manifest-path`, which a definition-time default would
    never see -- and the consumer lock sweep passes a member's, so one
    overlay-free runner serves the stack. The manifest option goes before `--`
    when present because cargo forwards everything after it to the subcommand.

    Excluding the overlay excludes the whole config, `target-dir` included, so
    the shared cache is restored explicitly from the stack config above the
    manifest ([`shared_target_dir`]). Without it every check writes a
    repo-local `target/` into the member it inspects, which is the
    `target_forks` class the conformance ratchet counts. An inherited
    `CARGO_TARGET_DIR` wins, so CI -- where there is no stack config and each
    job is isolated anyway -- is unaffected.

    The run is bounded by `deadline` ([`run_bounded`]): a first-party fetch
    that never returns raises [`CargoDeadlineExceeded`] after its whole process
    tree is killed, so a stalled push fails instead of holding the hook open.
    """
    if manifest is None:
        manifest = MANIFEST
    environment = dict(os.environ)
    if "CARGO_TARGET_DIR" not in environment:
        shared = shared_target_dir(manifest)
        if shared is not None:
            environment["CARGO_TARGET_DIR"] = str(shared)
    try:
        separator = arguments.index("--")
    except ValueError:
        separator = len(arguments)
    cargo_arguments = [
        *arguments[:separator],
        "--manifest-path",
        str(manifest),
        *arguments[separator:],
    ]
    with tempfile.TemporaryDirectory() as neutral_directory:
        return run_bounded(
            [*CARGO_COMMAND, *cargo_arguments],
            cwd=Path(neutral_directory),
            env=environment,
            deadline=deadline,
        )


def locked_metadata(
    manifest: Path, *, deadline: float = CARGO_DEADLINE_SECONDS
) -> dict[str, object]:
    """Read one complete locked Cargo graph without changing its lock bytes.

    Cargo owns workspace membership, path-dependency reachability, target and
    feature resolution. The command therefore uses the full graph rather than
    reconstructing those semantics from manifests. Offline mode fixes the
    available source set; callers prepare the selected immutable sources first.
    """
    lock = manifest.with_name("Cargo.lock")
    try:
        before = lock.read_bytes()
    except OSError as error:
        raise CargoMetadataError(f"cannot read {lock}: {error}") from error
    try:
        completed = run_outside_the_overlay(
            [
                "metadata",
                "--locked",
                "--offline",
                "--all-features",
                "--format-version",
                "1",
            ],
            manifest=manifest,
            deadline=deadline,
        )
    finally:
        try:
            after = lock.read_bytes()
        except OSError as error:
            raise CargoMetadataError(f"cannot reread {lock}: {error}") from error
        if after != before:
            raise CargoMetadataError(f"cargo metadata changed locked bytes in {lock}")
    if completed.returncode:
        detail = completed.stderr.strip()
        raise CargoMetadataError(
            f"cargo metadata --locked --offline failed for {manifest}: {detail}"
        )
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise CargoMetadataError(
            f"cargo metadata returned unreadable JSON for {manifest}"
        ) from error
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("packages"), list)
        or not isinstance(document.get("workspace_members"), list)
        or not isinstance(document.get("resolve"), dict)
    ):
        raise CargoMetadataError(
            f"cargo metadata returned an incomplete graph for {manifest}"
        )
    return document


def check() -> int:
    """Judge every lock under the repository, then prove the root one resolves.

    The overlay's signature is judged by the one rule ([`judge_locks`]) that
    `--check-staged` and `--check-committed` apply, over every lock in the tree
    (nested workspaces included), read from disk because the pre-push export
    and a CI checkout are not always repositories to ask. Staleness, which
    needs real resolution, is the `--locked` arm below.
    """
    if not LOCKFILE.is_file():
        print(f"error: {LOCKFILE} does not exist", file=sys.stderr)
        return 1

    try:
        texts = disk_texts(REPOSITORY)
    except OSError as error:
        print(f"error: the manifests and locks could not be read: {error}", file=sys.stderr)
        return 1
    problems, exempt = judge_locks(texts)
    for lock in exempt:
        print(f"exempt (in-tree fixture, not standalone-consumable): {lock}")
    if problems:
        for problem in problems:
            print(f"LOCK FORM VIOLATION: {problem}", file=sys.stderr)
        print(
            "\n"
            "A lock regenerated with the Atlas stack overlay active resolves\n"
            "first-party dependencies to local paths and drops their git\n"
            "sources, and leaves [[patch.unused]] residue. CI has no overlay and\n"
            "will fail every --locked job.\n"
            "\n"
            f"Fix: {REGENERATE_COMMAND}",
            file=sys.stderr,
        )
        return 1

    try:
        locked_metadata(MANIFEST)
    except CargoDeadlineExceeded as error:
        print(
            f"error: cargo metadata --locked did not finish within "
            f"{error.timeout:g}s, so its process tree was killed.\n"
            "\n"
            "The lock form is intact; this is a resolution that never finished\n"
            "(usually a stalled first-party fetch), not a flattened lock.\n"
            "\n"
            f"cargo said:\n{(error.stderr or '').strip()}",
            file=sys.stderr,
        )
        return 1
    except CargoMetadataError as error:
        print(
            "error: the committed Cargo.lock does not resolve under --locked "
            "(its sources are intact, so it is stale rather than flattened).\n"
            "\n"
            "The pinned first-party revisions no longer satisfy the manifests'\n"
            "version requirements, so cargo must re-resolve and --locked\n"
            "refuses. This is what blocks the benchmark baseline alignment.\n"
            "\n"
            f"Fix: {REGENERATE_COMMAND}\n"
            "\n"
            f"cargo said:\n{error}",
            file=sys.stderr,
        )
        return 1

    locks = sum(1 for path in texts if PurePosixPath(path).name == "Cargo.lock")
    print(f"Cargo.lock resolves under --locked; {locks - len(exempt)} lock(s) in standalone form.")
    return check_provider_identity()


def locked_package_records(lock_text: str) -> list[Mapping[str, object]]:
    """Return structurally readable package records from one Cargo lock.

    Cargo owns the semantic grammars of package names, versions, and source
    URLs. This boundary validates only the fields consumers must read without
    ambiguity; callers interpret source identities for their own domain.
    """
    try:
        data = tomllib.loads(lock_text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"unparseable lock: {error}") from error

    packages = data.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("lock package collection is not an array")

    records: list[Mapping[str, object]] = []
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            raise ValueError(f"lock package {index} is not a table")
        for field in ("name", "version"):
            value = package.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"lock package {index} has missing, empty, or non-string {field}"
                )
        if "source" in package:
            source = package["source"]
            if not isinstance(source, str) or not source:
                raise ValueError(f"lock package {index} has empty or non-string source")
        records.append(package)
    return records


def provider_identities(lock_text: str) -> dict[str, set[str]]:
    """Map each first-party repository to the distinct sources it resolves through.

    The key drops the `.git` suffix and the URL case, so the two spellings of one
    repository count as the fork they are rather than as two providers.
    """
    identities: dict[str, set[str]] = {}
    for package in locked_package_records(lock_text):
        source = package.get("source")
        if not isinstance(source, str) or not source.startswith(FIRST_PARTY_GIT):
            continue
        base = source.split("#", 1)[0]
        repository = base.split("?", 1)[0].removesuffix(".git").lower()
        identities.setdefault(repository, set()).add(base)
    return identities


def provider_identity_baseline() -> int | None:
    """Read the member's committed excess-source bound, or `None` when unset."""
    path = LOCKFILE.parent / PROVIDER_IDENTITY_BASELINE_NAME
    if not path.is_file():
        return None
    try:
        return int(path.read_text(encoding="utf-8").split("#", 1)[0].strip())
    except ValueError:
        print(
            f"error: {path} must contain a single integer bound.",
            file=sys.stderr,
        )
        return -1


def check_provider_identity() -> int:
    """Bound the first-party providers that resolve through more than one source.

    A provider reached by two sources is compiled twice, so its public types stop
    matching across the boundary between the consumers that took different
    routes. Nothing reports this: the build is green, the lock resolves under
    `--locked`, and the mismatch surfaces only where the two halves meet.

    It is also the reason a merged co-evolution pin cannot be dropped on its own.
    Removing one while a transitive first-party consumer still pins the older
    revision adds a source rather than removing one -- measured on apollo, where
    dropping four merged pins raised the excess from four to eight because
    `leto-ops` still pinned hermes at `5a399ee`.

    The bound is a ratchet, not a zero: these forks exist today and a check that
    fails on arrival gets disabled rather than fixed.
    """
    identities = provider_identities(LOCKFILE.read_text(encoding="utf-8"))
    forked = {name: sources for name, sources in identities.items() if len(sources) > 1}
    excess = sum(len(sources) - 1 for sources in forked.values())

    for name, sources in sorted(forked.items()):
        print(f"  {name.rsplit('/', 1)[-1]} resolves through {len(sources)} sources:")
        for source in sorted(sources):
            print(f"    {source.split('ryancinsight/', 1)[-1]}")

    baseline = provider_identity_baseline()
    if baseline is None:
        print(
            f"Provider identity: {excess} source(s) in excess of one per "
            f"repository; unbounded (no {PROVIDER_IDENTITY_BASELINE_NAME})."
        )
        return 0
    if baseline < 0:
        return 1

    if excess > baseline:
        print(
            f"error: {excess} first-party provider sources in excess of one per\n"
            f"repository; the committed bound is {baseline}.\n"
            f"\n"
            f"Each extra source is a second copy of that provider in the graph, so\n"
            f"its public types no longer match across the boundary between the\n"
            f"consumers that reached it by different routes.\n"
            f"\n"
            f"A merged co-evolution pin cannot be removed until every transitive\n"
            f"first-party consumer of that provider has advanced too; unpinning\n"
            f"ahead of them adds a source rather than removing one.\n"
            f"\n"
            f"Fix: advance the consumers first, or restore the pin. Lower\n"
            f"{PROVIDER_IDENTITY_BASELINE_NAME} only when a fork actually closes.",
            file=sys.stderr,
        )
        return 1

    if excess < baseline:
        print(
            f"Provider identity: {excess} source(s) in excess of one per repository, "
            f"below the committed bound of {baseline} -- lower it to {excess}."
        )
        return 0

    print(
        f"Provider identity: {excess} source(s) in excess of one per repository "
        f"(bound {baseline})."
    )
    return 0

class GitUnavailable(Exception):
    """git could not answer, so the repository cannot be judged.

    Every caller reports this as a failed check. A listing that errors is not
    an empty listing: reading it as one would pass a lock nothing looked at.
    """


class WorkspaceFacts(NamedTuple):
    """What a workspace's manifests say about the lock it owns."""

    local: frozenset[str]
    git_dependencies: frozenset[str]
    fixture: bool
    unreadable: tuple[str, ...]
    problems: tuple[str, ...]


def run_git(
    arguments: Sequence[str], repository: Path | None = None, stdin: bytes | None = None
) -> bytes:
    """Run git in `repository`, or in the current directory when it is None.

    The current directory is the member a hook runs in, and git reads the index
    from the `GIT_INDEX_FILE` the environment carries, which is how a commit
    that stages through a private index is judged by what it stages.
    """
    prefix = ["-C", str(repository)] if repository is not None else []
    try:
        completed = subprocess.run(
            ["git", *prefix, *arguments],
            input=stdin,
            capture_output=True,
            check=False,
            timeout=GIT_DEADLINE_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GitUnavailable(f"git {arguments[0]} could not run: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitUnavailable(f"git {arguments[0]} exited {completed.returncode}: {detail}")
    return completed.stdout


def violations(
    lock_text: str, local: Iterable[str], git_dependencies: Iterable[str]
) -> list[str]:
    """Overlay-stripping violations in one lock's text.

    Two independent signatures, both produced only by resolving under a
    `[patch]` overlay and neither reachable from a clean standalone resolve:

    1. a `[[patch.unused]]` table, and
    2. a package declared as a git dependency, present in the lock, resolved
       with no `source` -- locked as a local path package although no manifest
       in the workspace defines it.

    A declared dependency absent from the lock (an idle `[workspace.dependencies]`
    row) and a workspace declaring none are not violations: the rule is
    quantified over what the lock resolves, never over a count of `git+` lines.
    """
    try:
        packages = locked_package_records(lock_text)
    except ValueError as error:
        return [str(error)]

    found: list[str] = []
    unused = lock_text.count(PATCH_UNUSED)
    if unused:
        found.append(f"{unused} {PATCH_UNUSED} table(s): overlay residue")

    sources: dict[str, list[str | None]] = {}
    for package in packages:
        sources.setdefault(package.get("name"), []).append(package.get("source"))

    for name in sorted(set(git_dependencies) - set(local)):
        entries = sources.get(name)
        if entries is None:
            continue
        if not any(source and source.startswith("git+") for source in entries):
            found.append(f"`{name}` locked without a git source (stripped)")
    return found


def package_dependency_tables(manifest: Mapping[str, object]) -> Iterator[Mapping[str, object]]:
    """Every dependency table attached to a package, including target tables."""
    for kind in DEPENDENCY_KINDS:
        table = manifest.get(kind)
        if isinstance(table, dict):
            yield table
    targets = manifest.get("target")
    for target in targets.values() if isinstance(targets, dict) else ():
        if isinstance(target, dict):
            for kind in DEPENDENCY_KINDS:
                if isinstance(target.get(kind), dict):
                    yield target[kind]


def dependency_tables(manifest: Mapping[str, object]) -> Iterator[Mapping[str, object]]:
    """Every package or workspace table that declares dependencies."""
    yield from package_dependency_tables(manifest)
    workspace = manifest.get("workspace")
    if isinstance(workspace, dict) and isinstance(workspace.get("dependencies"), dict):
        yield workspace["dependencies"]


def resolved_dependency_specs(
    manifest: Mapping[str, object], workspace_dependencies: Mapping[str, object]
) -> Iterator[tuple[str, Mapping[str, object], bool]]:
    """Package dependencies with `workspace = true` resolved at their owner.

    The boolean says the source specification came from the workspace root;
    Cargo resolves an inherited `path` relative to that root, not the member.
    Unused workspace declarations never enter this projection.
    """
    for table in package_dependency_tables(manifest):
        for dependency, spec in table.items():
            if not isinstance(spec, dict):
                continue
            if spec.get("workspace") is not True:
                yield dependency, spec, False
                continue
            inherited = workspace_dependencies.get(dependency)
            if not isinstance(inherited, dict):
                raise ValueError(
                    f"workspace dependency {dependency!r} is missing or unreadable"
                )
            resolved = dict(inherited)
            resolved.update({key: value for key, value in spec.items() if key != "workspace"})
            yield dependency, resolved, True


def escapes_repository(manifest: PurePosixPath, path: str) -> bool:
    """Whether a manifest's `path` dependency leaves its repository.

    Both sides are repository-relative, so the answer comes from the paths
    alone and reads neither a working tree nor a checkout's layout.
    """
    path = path.replace("\\", "/")
    if posixpath.isabs(path) or path[1:2] == ":":
        return True
    resolved = posixpath.normpath(posixpath.join(manifest.parent.as_posix(), path))
    return resolved == ".." or resolved.startswith("../")


def directory_pattern_matches(pattern: PurePosixPath, directory: PurePosixPath) -> bool:
    """Whether `directory` matches one of cargo's member or exclude globs.

    Cargo confines `*` and `?` to one path component and lets `**` span them;
    `PurePosixPath.match` lets `*` cross separators, so the components are
    walked here instead.
    """
    wanted = pattern.parts
    actual = directory.parts

    def walk(pattern_index: int, directory_index: int) -> bool:
        if pattern_index == len(wanted):
            return directory_index == len(actual)
        component = wanted[pattern_index]
        if component == "**":
            return any(
                walk(pattern_index + 1, index)
                for index in range(directory_index, len(actual) + 1)
            )
        if directory_index == len(actual):
            return False
        return (
            fnmatch.fnmatchcase(actual[directory_index], component)
            and walk(pattern_index + 1, directory_index + 1)
        )

    return walk(0, 0)


def workspace_relative(workspace: PurePosixPath, path: str) -> PurePosixPath:
    """A member or exclude entry, resolved against the workspace root."""
    joined = posixpath.normpath(posixpath.join(workspace.as_posix(), path.replace("\\", "/")))
    return PurePosixPath(joined)


def workspace_selection(
    manifests: Mapping[str, str],
    parsed: Mapping[str, Mapping[str, object] | None],
    workspace: PurePosixPath,
    nested: Sequence[PurePosixPath],
) -> set[str] | None:
    """The manifests cargo resolves in the workspace's lock, or None when it declares none.

    Cargo, not directory containment, decides membership: `members` names the
    packages (globs included), `exclude` removes paths from that set, path
    dependencies under the root join it, and a manifest declaring its own
    `[workspace]` is a separate unit whether or not it has a lock. Grouping by
    containing directory instead missed a member outside the lock's directory,
    let an excluded crate shadow a stripped source by name, and let a lockless
    nested workspace exempt the root lock through a path leaving the repository.

    `None` means the root declares no `[workspace]` table; the caller then keeps
    the directory-based reading, which is all a single-package manifest has.
    """
    root = (workspace / "Cargo.toml").as_posix()
    root_data = parsed.get(root)
    table = root_data.get("workspace") if isinstance(root_data, dict) else None
    if not isinstance(table, dict):
        return None

    def entries(key: str) -> list[PurePosixPath]:
        listed = table.get(key)
        if not isinstance(listed, list):
            return []
        return [
            workspace_relative(workspace, entry)
            for entry in listed
            if isinstance(entry, str)
        ]

    members = entries("members")
    excluded = entries("exclude")
    # Only workspaces *beneath* this one are boundaries. An ancestor's
    # `[workspace]` does not own this lock: this one declares its own, and may
    # itself be a `[workspace]` root under an umbrella that only lists other
    # members.
    boundaries = {
        PurePosixPath(name).parent
        for name, data in parsed.items()
        if isinstance(data, dict)
        and isinstance(data.get("workspace"), dict)
        and workspace in PurePosixPath(name).parent.parents
    }
    boundaries.update(boundary for boundary in nested if workspace in boundary.parents)

    def ignored(directory: PurePosixPath) -> bool:
        return bool({part.lower() for part in directory.parts} & IGNORED_DIRECTORIES)

    def inside_boundary(directory: PurePosixPath) -> bool:
        return any(
            boundary == directory or boundary in directory.parents
            for boundary in boundaries
        )

    def excluded_manifest(name: str) -> bool:
        directory = PurePosixPath(name).parent
        ancestors = [
            PurePosixPath(*directory.parts[:index])
            for index in range(len(directory.parts), 0, -1)
        ]
        return any(
            directory_pattern_matches(pattern, ancestor)
            for pattern in excluded
            for ancestor in ancestors
        )

    selected = {root}
    for name in manifests:
        directory = PurePosixPath(name).parent
        if inside_boundary(directory) or ignored(directory):
            continue
        if any(directory_pattern_matches(pattern, directory) for pattern in members):
            selected.add(name)

    workspace_dependencies = table.get("dependencies", {})
    if not isinstance(workspace_dependencies, dict):
        workspace_dependencies = {}

    # Cargo joins every consumed path dependency under the root to the workspace; one
    # outside it is a separate package even when a member reaches it.
    changed = True
    while changed:
        changed = False
        for name in sorted(selected):
            data = parsed.get(name)
            if not isinstance(data, dict):
                continue
            for _dependency, spec, inherited in resolved_dependency_specs(
                data, workspace_dependencies
            ):
                if not isinstance(spec.get("path"), str):
                    continue
                owner = workspace if inherited else PurePosixPath(name).parent
                target = workspace_relative(owner, spec["path"])
                target_manifest = (target / "Cargo.toml").as_posix()
                if target_manifest in selected or target_manifest not in manifests:
                    continue
                if inside_boundary(target) or ignored(target):
                    continue
                selected.add(target_manifest)
                changed = True

    return {
        name
        for name in selected
        if not inside_boundary(PurePosixPath(name).parent)
        and not ignored(PurePosixPath(name).parent)
        and not excluded_manifest(name)
    }


def workspace_facts(
    manifests: Mapping[str, str],
    workspace: PurePosixPath,
    nested: Sequence[PurePosixPath],
) -> WorkspaceFacts:
    """The packages a workspace defines and the git dependencies it declares.

    `manifests` maps repository-relative paths to manifest text. `nested` lists
    workspace roots beneath this one that own their own lock; their manifests
    belong to that lock, not this one.

    Membership comes from the workspace's own declarations when it has any
    ([`workspace_selection`]); a manifest without a `[workspace]` table keeps
    the directory reading, which is the only membership a lone package has.

    `fixture` marks a workspace depending on a sibling repository by relative
    path (`../../../hephaestus/...`). It exists only inside a full Atlas
    checkout and cannot resolve standalone, so the standalone rule does not
    apply to its lock (ADR-0044's one exemption).
    """
    parsed: dict[str, Mapping[str, object] | None] = {}
    for name, text in manifests.items():
        try:
            parsed[name] = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            parsed[name] = None

    problems: list[str] = []
    try:
        selected = workspace_selection(manifests, parsed, workspace, nested)
    except ValueError as error:
        return WorkspaceFacts(
            frozenset(), frozenset(), False, (), (str(error),)
        )
    if selected is None:
        selected = {
            name
            for name in manifests
            if workspace in PurePosixPath(name).parents
            and not ({part.lower() for part in PurePosixPath(name).parts} & IGNORED_DIRECTORIES)
            and not any(other in PurePosixPath(name).parents for other in nested)
        }

    local: set[str] = set()
    git_dependencies: set[str] = set()
    unreadable: list[str] = []
    fixture = False
    root_data = parsed.get((workspace / "Cargo.toml").as_posix())
    root_workspace = root_data.get("workspace") if isinstance(root_data, dict) else None
    workspace_dependencies = (
        root_workspace.get("dependencies", {}) if isinstance(root_workspace, dict) else {}
    )
    if not isinstance(workspace_dependencies, dict):
        workspace_dependencies = {}
    for name in sorted(selected):
        data = parsed.get(name)
        if data is None:
            unreadable.append(name)
            continue
        package = data.get("package")
        if isinstance(package, dict) and isinstance(package.get("name"), str):
            local.add(package["name"])
        manifest = PurePosixPath(name)
        try:
            dependencies = tuple(resolved_dependency_specs(data, workspace_dependencies))
        except ValueError as error:
            problems.append(f"{name}: {error}")
            continue
        for dependency, spec, inherited in dependencies:
            package_name = spec.get("package", dependency)
            if isinstance(spec.get("git"), str):
                if not isinstance(package_name, str) or not package_name:
                    problems.append(f"{name}: dependency {dependency!r} has unreadable package identity")
                    continue
                git_dependencies.add(package_name)
            elif isinstance(spec.get("path"), str):
                owner = workspace / "Cargo.toml" if inherited else manifest
                if escapes_repository(owner, spec["path"]):
                    fixture = True
    return WorkspaceFacts(
        frozenset(local),
        frozenset(git_dependencies),
        fixture,
        tuple(unreadable),
        tuple(problems),
    )


def workspace_units(
    texts: Mapping[str, str], locks: Iterable[str] | None = None
) -> dict[str, WorkspaceFacts]:
    """The facts judging each lock among `texts`, keyed by the lock's path.

    `texts` maps every tracked `Cargo.toml` and `Cargo.lock` of one repository
    to its text; `locks` selects which locks to judge, all of them by default.
    """
    manifests = {
        path: text for path, text in texts.items() if PurePosixPath(path).name == "Cargo.toml"
    }
    present = sorted(path for path in texts if PurePosixPath(path).name == "Cargo.lock")
    roots = [PurePosixPath(path).parent for path in present]
    units: dict[str, WorkspaceFacts] = {}
    for lock in sorted(present if locks is None else locks):
        workspace = PurePosixPath(lock).parent
        nested = [root for root in roots if root != workspace and workspace in root.parents]
        units[lock] = workspace_facts(manifests, workspace, nested)
    return units


def judge_locks(
    texts: Mapping[str, str], locks: Iterable[str] | None = None
) -> tuple[list[str], list[str]]:
    """Judge locks against the standalone form: (problems, exempt lock paths).

    A manifest that does not parse leaves the workspace's declarations unknown,
    and an unknown is refused rather than read as none declared.
    """
    problems: list[str] = []
    exempt: list[str] = []
    for lock, facts in workspace_units(texts, locks).items():
        if facts.fixture:
            exempt.append(lock)
            continue
        for problem in violations(texts[lock], facts.local, facts.git_dependencies):
            problems.append(f"{lock}: {problem}")
        for manifest in facts.unreadable:
            problems.append(f"{lock}: {manifest} does not parse, so the lock cannot be judged")
        problems.extend(f"{lock}: {problem}" for problem in facts.problems)
    return problems, exempt


def tracked_texts(
    repository: Path | None, *, staged: bool, revision: str = "HEAD"
) -> dict[str, str]:
    """Text of every tracked `Cargo.toml` and `Cargo.lock`, by repository-relative path.

    `staged` reads the index, which is what becomes the commit; otherwise the
    tree at `revision`, so the answer is a function of that commit alone and no
    working file takes part. Raises [`GitUnavailable`] when git cannot answer.
    """
    if staged:
        listing = run_git(["ls-files", "--stage", "-z"], repository)
    else:
        listing = run_git(["ls-tree", "-r", "-z", revision], repository)
    blobs: dict[str, str] = {}
    for record in listing.decode("utf-8", errors="replace").split("\0"):
        head, _, path = record.partition("\t")
        if not path or PurePosixPath(path).name not in {"Cargo.toml", "Cargo.lock"}:
            continue
        fields = head.split()
        if staged:
            mode, blob, stage = fields
            if mode == "160000" or stage != "0":
                continue
        else:
            _, kind, blob = fields
            if kind != "blob":
                continue
        blobs[path] = blob
    texts = read_blobs(repository, sorted(set(blobs.values())))
    return {path: texts[blob] for path, blob in blobs.items()}


def read_blobs(repository: Path | None, blobs: Sequence[str]) -> dict[str, str]:
    """Text of each blob, read in one `git cat-file --batch` call."""
    if not blobs:
        return {}
    request = "".join(f"{blob}\n" for blob in blobs).encode("ascii")
    output = run_git(["cat-file", "--batch"], repository, stdin=request)
    texts: dict[str, str] = {}
    position = 0
    for blob in blobs:
        end = output.find(b"\n", position)
        header = output[position:end].decode("ascii", errors="replace").split() if end >= 0 else []
        if len(header) != 3 or header[0] != blob or header[1] != "blob":
            raise GitUnavailable(f"git cat-file could not read {blob}")
        size = int(header[2])
        texts[blob] = output[end + 1 : end + 1 + size].decode("utf-8", errors="replace")
        position = end + 1 + size + 1
    return texts


def disk_texts(repository: Path) -> dict[str, str]:
    """Text of every `Cargo.toml` and `Cargo.lock` under `repository`, by relative path.

    The filesystem counterpart of [`tracked_texts`], for a tree that is not a
    repository to ask: the pre-push export is `git archive` output, and a CI
    checkout is judged as it stands. Directories of build output and vendored
    code are not entered, nor is the checkout this script runs from when it sits
    inside `repository` (`SCRIPT_CHECKOUT`).
    """
    texts: dict[str, str] = {}
    own = SCRIPT_CHECKOUT.resolve()
    for directory, subdirectories, files in os.walk(repository):
        subdirectories[:] = [
            name
            for name in subdirectories
            if name.lower() not in IGNORED_DIRECTORIES
            and (Path(directory) / name).resolve() != own
        ]
        for name in files:
            if name in {"Cargo.toml", "Cargo.lock"}:
                path = Path(directory) / name
                texts[path.relative_to(repository).as_posix()] = path.read_text(
                    encoding="utf-8", errors="replace"
                )
    return texts


def check_staged() -> int:
    """Judge the *staged* locks of the repository in the current directory.

    For the `pre-commit` hook. It runs no cargo: a hook slow enough that anyone
    reaches for `--no-verify` guards nothing, and the overlay's signature is
    settled by reading the lock. Staleness, which needs real resolution, stays
    a `--check` concern at push.

    The staged blob is judged rather than the working file, since a repaired
    working copy with the poisoned version still in the index is the case that
    would otherwise pass, and the index is what becomes the commit. Manifests
    are read from the index for the same reason. Every staged lock is judged,
    nested ones included.
    """
    try:
        changed = run_git(
            ["diff", "--cached", "--name-only", "--diff-filter=d", "-z", "--", "*Cargo.lock"]
        )
        staged = [
            path
            for path in changed.decode("utf-8", errors="replace").split("\0")
            if path and PurePosixPath(path).name == "Cargo.lock"
        ]
        if not staged:
            return 0
        texts = tracked_texts(None, staged=True)
        missing = [path for path in staged if path not in texts]
        if missing:
            raise GitUnavailable(f"git did not list the staged lock {missing[0]}")
    except GitUnavailable as error:
        print(f"error: the staged locks could not be read: {error}", file=sys.stderr)
        return 1

    problems, _ = judge_locks(texts, staged)
    if not problems:
        return 0
    for problem in problems:
        print(f"LOCK FORM VIOLATION (staged): {problem}", file=sys.stderr)
    print(
        "\n"
        "A cargo command run beneath the Atlas stack root rewrote the lock with\n"
        "the overlay active, which resolves first-party dependencies to local\n"
        "paths and drops their git sources. It was rewritten, not edited.\n"
        "\n"
        "Unstage it and restore the committed form:\n"
        "  git restore --staged <lock>\n"
        "  python3 <stack>/scripts/atlas-lock-form.py restore\n"
        "To change the lock deliberately, regenerate it outside the overlay:\n"
        f"  {REGENERATE_COMMAND}",
        file=sys.stderr,
    )
    return 1


def check_committed(repositories: Sequence[Path]) -> int:
    """Judge every tracked lock at HEAD of each repository: the stack sweep.

    Reads commits only, so the verdict does not depend on what a peer left in a
    working tree. A directory that is not a repository root (an uninitialized
    submodule would answer with its parent) is skipped with a warning; a
    repository git cannot read is a failure.
    """
    failures = 0
    checked = 0
    for repository in repositories:
        label = repository.resolve().name
        if not repository.is_dir():
            print(f"::warning::{label}: not a directory; skipped")
            continue
        try:
            top = run_git(["rev-parse", "--show-toplevel"], repository).decode("utf-8").strip()
            if Path(top).resolve() != repository.resolve():
                print(f"::warning::{label}: not a repository root; skipped")
                continue
            texts = tracked_texts(repository, staged=False)
        except GitUnavailable as error:
            failures += 1
            print(f"LOCK FORM VIOLATION: {label}: cannot be read: {error}")
            continue
        problems, exempt = judge_locks(texts)
        for lock in exempt:
            print(f"exempt (in-tree fixture, not standalone-consumable): {label}/{lock}")
        locks = sum(1 for path in texts if PurePosixPath(path).name == "Cargo.lock")
        checked += locks - len(exempt)
        for problem in problems:
            failures += 1
            print(f"LOCK FORM VIOLATION: {label}/{problem}")
    if failures:
        print(
            f"\n{failures} violation(s) across {checked} committed lock(s).\n"
            "A committed lock must resolve standalone: every git dependency it\n"
            'resolves carries its `source = "git+..."` line and no\n'
            "[[patch.unused]] residue (ADR-0044).\n"
            "Repair without touching the shared overlay:\n"
            "  python3 scripts/lockfile.py --regenerate --manifest-path <member>/Cargo.toml\n"
            "Never `git add` a lock dirtied by a local build; restore it first:\n"
            "  python3 scripts/atlas-lock-form.py restore"
        )
        return 1
    print(f"lock form clean: {checked} committed lock(s) resolve standalone")
    return 0


def regenerate() -> int:
    """Repair the lock outside the overlay without advancing any pin.

    `cargo metadata` re-resolves only what the lock cannot supply, so a source
    the overlay stripped is restored and the residue it left is dropped, while
    every unrelated pin stays where it is. `cargo generate-lockfile` would
    re-resolve all of them and move first-party branch pins to their tips, which
    a repair must not do (ADR-0044); advancing a pin is `cargo update`, run
    deliberately.
    """
    try:
        completed = run_outside_the_overlay(["metadata", "--format-version", "1"])
    except CargoDeadlineExceeded as error:
        print(
            f"error: regeneration did not finish within {error.timeout:g}s; its "
            f"process tree was killed.\n{(error.stderr or '').strip()}",
            file=sys.stderr,
        )
        return 1
    if completed.returncode != 0:
        print(f"error: regeneration failed:\n{completed.stderr.strip()}", file=sys.stderr)
        return 1
    print("Cargo.lock repaired outside the overlay; no pin advanced.")
    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify the committed lock")
    mode.add_argument("--regenerate", action="store_true", help="rewrite the lock correctly")
    mode.add_argument(
        "--check-staged",
        action="store_true",
        help="judge the staged locks from the index, for pre-commit",
    )
    mode.add_argument(
        "--check-committed",
        nargs="+",
        type=Path,
        metavar="REPOSITORY",
        help="judge every tracked lock at HEAD of each repository, offline",
    )
    parser.add_argument("--manifest-path", type=Path, default=None,
                        help="path to Cargo.toml (overrides auto-detection from __file__)")
    arguments = parser.parse_args()
    if arguments.manifest_path is not None:
        global REPOSITORY, LOCKFILE, MANIFEST
        MANIFEST = arguments.manifest_path.resolve()
        REPOSITORY = MANIFEST.parent
        LOCKFILE = REPOSITORY / "Cargo.lock"
    if arguments.regenerate:
        return regenerate()
    if arguments.check_staged:
        return check_staged()
    if arguments.check_committed:
        return check_committed(arguments.check_committed)
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
