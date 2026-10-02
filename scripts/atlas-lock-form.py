#!/usr/bin/env python3
"""Enforce the committed Cargo.lock form across the Atlas stack (ADR-0021).

A member's committed `Cargo.lock` is a *standalone* artifact: it must resolve
the repository exactly as a clean checkout, CI runner, or `cargo publish`
sandbox would -- none of which see the stack `[patch]` overlay. Therefore every
git dependency the lock actually resolves must carry its `source = "git+..."`
line, and no committed lock may carry `[[patch.unused]]` residue.

The stack overlay (`scripts/atlas-stack-overlay.py`, the `[patch]` block in the
root `.cargo/config.toml`) rewrites working-tree locks on every local build: it
drops the `source` line of every patched package and appends `[[patch.unused]]`
tables. That rewrite is derived state, never an edit -- `restore` puts it back.

Modes:

    check       fail when any *committed* lock is in the overlay-stripped form
    status      same measurement, reported for committed and working copies
    staged      same rule against one member's staged locks (pre-commit hook)
    restore     revert working-tree locks whose only diff from HEAD is the
                overlay rewrite (refuses on any other difference)
    regenerate  rebuild a member's lock in standalone form, by invoking cargo
                from a directory outside the Atlas tree so the overlay is not
                discovered
    install-hooks
                per-clone bootstrap: point member `core.hooksPath` at
                scripts/git-hooks so every member runs the owned pre-commit
                and pre-push hooks, whatever branch its tree has checked out

`check` is the CI gate. It is deliberately narrow: it flags only a package that
is *present in the lock* yet locked without a source despite being declared as
a git dependency. A member with no git dependencies has nothing to flag, and a
`[workspace.dependencies]` entry no crate actually uses is legitimately absent
from the lock -- neither is a violation, and a naive `git+` line count would
misreport both.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_git_process import (  # noqa: E402
    GitProcessError,
    clean_process_env,
    execute as execute_git,
    execute_process,
)
from atlas_stack import ROOT, registered_member_names  # noqa: E402

REPOS = ROOT / "repos"
# A push may run the committed 60-second hook gate; the remainder covers Git
# transport and process-tree teardown without leaving an unbounded member.
GIT_DEADLINE_SECONDS = 90
# `cargo metadata` resolves only what a lock cannot supply, which can mean
# fetching a git dependency's index: the ten-minute foreground bound.
CARGO_METADATA_DEADLINE_SECONDS = 600
CARGO_COMMAND = ("cargo",)
# Each member's in-tree copy of scripts/git-hooks, written by `sync-hooks`.
MEMBER_HOOK_COPY = ".githooks"
SKIP_DIRS = {"target", ".git", "node_modules"}
PATCH_UNUSED = "[[patch.unused]]"
FIRST_PARTY_HOST = "github.com/ryancinsight/"


def run(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command with a deadline that ends its whole process tree.

    The `staged` pre-commit mode must read the index git named, so
    `GIT_INDEX_FILE` stays in the environment (`execute_process` keeps it when
    the caller passes it); every other repository variable is scrubbed. A
    deadline or a launch failure raises `RuntimeError`.
    """
    try:
        result = execute_process(
            args, cwd=cwd, env=dict(os.environ), timeout=GIT_DEADLINE_SECONDS
        )
    except GitProcessError as error:
        raise RuntimeError(str(error)) from error
    return (
        result.returncode,
        result.stdout.decode("utf-8", errors="replace"),
        result.stderr.decode("utf-8", errors="replace"),
    )


def tracked_locks(repo: Path) -> list[str]:
    code, out, _ = run("git", "-C", str(repo), "ls-files", "*Cargo.lock")
    if code != 0:
        return []
    return sorted(line.strip() for line in out.splitlines() if line.strip())


def _dep_tables(data: dict):
    for key in ("dependencies", "dev-dependencies", "build-dependencies"):
        if isinstance(data.get(key), dict):
            yield data[key]
    workspace = data.get("workspace", {})
    if isinstance(workspace.get("dependencies"), dict):
        yield workspace["dependencies"]
    for target in (data.get("target") or {}).values():
        if isinstance(target, dict):
            for key in ("dependencies", "dev-dependencies", "build-dependencies"):
                if isinstance(target.get(key), dict):
                    yield target[key]


def workspace_facts(
    ws_root: Path, nested: list[Path], repo: Path
) -> tuple[set[str], set[str], bool]:
    """Return (locally defined packages, packages declared as git deps, fixture).

    `nested` lists sibling workspace roots that own their own lock; manifests
    beneath them belong to that lock, not this one.

    `fixture` marks a workspace that depends on sibling repositories by relative
    path (`../../../hephaestus/...`). Such a workspace exists only inside a full
    Atlas checkout -- it can never resolve standalone, so the standalone-form
    rule does not apply to its lock. This is the one exemption (ADR-0021) and it
    is reported rather than skipped silently.
    """
    local: set[str] = set()
    git_deps: set[str] = set()
    fixture = False
    for manifest in ws_root.glob("**/Cargo.toml"):
        if {part.lower() for part in manifest.parts} & SKIP_DIRS:
            continue
        if any(other in manifest.parents for other in nested):
            continue
        try:
            data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            continue
        package = data.get("package")
        if isinstance(package, dict) and isinstance(package.get("name"), str):
            local.add(package["name"])
        for table in _dep_tables(data):
            for name, spec in table.items():
                if not isinstance(spec, dict):
                    continue
                if isinstance(spec.get("git"), str):
                    git_deps.add(spec.get("package", name))
                elif isinstance(spec.get("path"), str):
                    target = (manifest.parent / spec["path"]).resolve()
                    root = repo.resolve()
                    if target != root and root not in target.parents:
                        fixture = True
    return local, git_deps, fixture


def violations(lock_text: str, local: set[str], git_deps: set[str]) -> list[str]:
    """Overlay-stripping violations in one lock's text.

    Two independent signatures, both produced only by resolving under a
    `[patch]` overlay and neither reachable from a clean standalone resolve:

    1. a `[[patch.unused]]` table, and
    2. a package declared as a git dependency, present in the lock, resolved
       with no `source` -- i.e. locked as a local path package although no
       manifest in the workspace defines it.
    """
    found: list[str] = []
    try:
        data = tomllib.loads(lock_text)
    except tomllib.TOMLDecodeError as exc:
        return [f"unparseable lock: {exc}"]

    unused = lock_text.count(PATCH_UNUSED)
    if unused:
        found.append(f"{unused} [[patch.unused]] table(s): overlay residue")

    sources: dict[str, list[str | None]] = {}
    for package in data.get("package", []):
        sources.setdefault(package.get("name"), []).append(package.get("source"))

    for name in sorted(git_deps - local):
        entries = sources.get(name)
        if entries is None:
            continue  # declared but unused (e.g. an idle [workspace.dependencies] row)
        if not any(source and source.startswith("git+") for source in entries):
            found.append(f"`{name}` locked without a git source (stripped)")
    return found


def _units_under(label: str, repo: Path) -> list[tuple[str, Path, str, set[str], set[str], bool]]:
    """Every tracked lock in one git repository, with the facts to judge it."""
    locks = tracked_locks(repo)
    roots = [(repo / lock).parent for lock in locks]
    units = []
    for lock in locks:
        ws_root = (repo / lock).parent
        nested = [r for r in roots if r != ws_root and ws_root in r.parents]
        local, git_deps, fixture = workspace_facts(ws_root, nested, repo)
        units.append((label, repo, lock, local, git_deps, fixture))
    return units


def lock_units() -> list[tuple[str, Path, str, set[str], set[str], bool]]:
    """(label, repository, lock path relative to it, local, git deps, fixture).

    Covers the registered members and the superproject itself. The
    superproject matters because its own tool workspaces live under the stack
    root, so a cargo run inside one walks up into the development overlay
    exactly as a member's does and its lock is rewritten the same way -- while
    being tracked here rather than in a submodule, which is how two tool locks
    reached `main` carrying sixty-one `[[patch.unused]]` tables each before
    this looked at them.
    """
    units = []
    for member in sorted(registered_member_names()):
        repo = REPOS / member
        if not repo.is_dir():
            continue
        units.extend(_units_under(member, repo))
    units.extend(_units_under("atlas", ROOT))
    return units


def committed_text(repo: Path, lock: str) -> str | None:
    code, out, _ = run("git", "-C", str(repo), "show", f"HEAD:{lock}")
    return out if code == 0 else None


def cmd_check(_args) -> int:
    failures = 0
    checked = 0
    for member, repo, lock, local, git_deps, fixture in lock_units():
        text = committed_text(repo, lock)
        if text is None:
            print(f"::warning::{member}/{lock}: not readable at HEAD; skipped")
            continue
        if fixture:
            print(f"exempt (in-tree fixture, not standalone-consumable): {member}/{lock}")
            continue
        checked += 1
        for problem in violations(text, local, git_deps):
            failures += 1
            print(f"LOCK FORM VIOLATION: {member}/{lock}: {problem}")
    if failures:
        print(
            f"\n{failures} violation(s) across {checked} committed lock(s).\n"
            "A committed lock must resolve standalone: every git dependency it\n"
            "resolves carries its `source = \"git+...\"` line and no\n"
            "[[patch.unused]] residue (ADR-0021).\n"
            "Repair without touching the shared overlay:\n"
            "  python scripts/atlas-lock-form.py regenerate <member>\n"
            "Never `git add` a lock dirtied by a local build; restore it first:\n"
            "  python scripts/atlas-lock-form.py restore"
        )
        return 1
    print(f"lock form clean: {checked} committed lock(s) resolve standalone")
    return 0


def cmd_staged(args) -> int:
    """Gate one member's *staged* locks -- the member-side pre-commit hook.

    `check` guards integration; this guards the commit that would create the
    violation in the first place, which is where the churn actually escapes:
    a `git add` of a lock a local build has just rewritten.
    """
    repo = Path(args.repo or ".").resolve()
    code, out, _ = run("git", "-C", str(repo), "diff", "--cached", "--name-only")
    staged = {line.strip() for line in out.splitlines() if line.strip().endswith("Cargo.lock")}
    if code != 0 or not staged:
        return 0
    units = {
        lock: (local, deps, fixture)
        for _member, unit_repo, lock, local, deps, fixture in lock_units()
        if unit_repo.resolve() == repo
    }
    failures = 0
    for lock in sorted(staged):
        if lock not in units:
            continue
        local, deps, fixture = units[lock]
        if fixture:
            continue
        blob_code, blob, _ = run("git", "-C", str(repo), "show", f":{lock}")
        if blob_code != 0:
            continue
        for problem in violations(blob, local, deps):
            failures += 1
            print(f"LOCK FORM VIOLATION (staged): {lock}: {problem}")
    if failures:
        print(
            "\nThis lock was rewritten by the stack [patch] overlay, not edited.\n"
            "Unstage it and restore the committed form:\n"
            "  git restore --staged Cargo.lock\n"
            "  python <atlas>/scripts/atlas-lock-form.py restore\n"
            "To change the lock deliberately, regenerate it outside the overlay:\n"
            "  python <atlas>/scripts/atlas-lock-form.py regenerate <member>"
        )
        return 1
    return 0


def cmd_status(_args) -> int:
    print(f"{'member/lock':<44} {'HEAD':<10} {'worktree':<10}")
    for member, repo, lock, local, git_deps, fixture in lock_units():
        head = committed_text(repo, lock)
        path = repo / lock
        work = path.read_text(encoding="utf-8") if path.exists() else None

        def verdict(text: str | None, fixture=fixture, local=local, git_deps=git_deps) -> str:
            if text is None:
                return "missing"
            if fixture:
                return "exempt"
            problems = violations(text, local, git_deps)
            if problems:
                return "STRIPPED"
            return "ok" if git_deps - local else "no-git-deps"

        print(f"{member + '/' + lock:<44} {verdict(head):<10} {verdict(work):<10}")
    return 0


def is_first_party(source: str | None) -> bool:
    return bool(source) and source.startswith("git+") and FIRST_PARTY_HOST in source.lower()


def _strip_only(head_text: str, work_text: str) -> bool:
    """True when `work_text` is exactly `head_text` put through the overlay.

    Guards `restore` against discarding real work. The eligible set is every
    package the committed lock sources from a first-party git repository -- not
    the `[patch]` table's own keys, because patching one crate to a path makes
    its whole workspace resolve by path, so siblings the overlay never names
    (`moirai-transport` beneath a patched `moirai-core`) lose their source too.

    Non-first-party packages must match exactly: name, version, and source. A
    first-party package may change version -- the local tree is routinely ahead
    of the pinned rev -- but must only ever *lose* its source, never gain one
    or move to a different rev; either of those is a real re-resolve.

    The direction matters. A working copy that *removes* overlay residue is a
    repair towards the committed form, not churn away from it; reverting it
    would throw the fix away. Churn only ever adds residue.
    """
    if work_text.count(PATCH_UNUSED) < head_text.count(PATCH_UNUSED):
        return False
    try:
        head = tomllib.loads(head_text)
        work = tomllib.loads(work_text)
    except tomllib.TOMLDecodeError:
        return False
    if head.get("version") != work.get("version"):
        return False

    eligible = {
        pkg.get("name")
        for pkg in head.get("package", [])
        if is_first_party(pkg.get("source"))
    }

    def split(data: dict):
        plain: dict[tuple[str, str], str | None] = {}
        first_party: dict[str, list[str | None]] = {}
        for pkg in data.get("package", []):
            name = pkg.get("name")
            if name in eligible:
                first_party.setdefault(name, []).append(pkg.get("source"))
            else:
                plain[(name, pkg.get("version"))] = pkg.get("source")
        return plain, first_party

    head_plain, head_fp = split(head)
    work_plain, work_fp = split(work)
    if head_plain != work_plain:
        return False
    for name, sources in work_fp.items():
        for source in sources:
            if source is None:
                continue  # replaced by the local tree: the expected rewrite
            if source not in head_fp.get(name, []):
                return False  # a rev the committed lock never pinned
    return True


def cmd_restore(_args) -> int:
    restored, kept = [], []
    for member, repo, lock, local, git_deps, fixture in lock_units():
        path = repo / lock
        head = committed_text(repo, lock)
        if head is None or not path.exists() or fixture:
            continue
        work = path.read_text(encoding="utf-8")
        if work == head:
            continue
        if violations(head, local, git_deps):
            kept.append(f"{member}/{lock} (committed lock itself violates; "
                        "the working copy may be the repair -- left alone)")
            continue
        if _strip_only(head, work):
            code, _, err = run("git", "-C", str(repo), "checkout", "--", lock)
            (restored if code == 0 else kept).append(
                f"{member}/{lock}" + ("" if code == 0 else f" (git checkout failed: {err.strip()})")
            )
        else:
            kept.append(f"{member}/{lock} (real change, left alone)")
    for line in restored:
        print(f"restored overlay churn: {line}")
    for line in kept:
        print(f"kept: {line}")
    print(f"\n{len(restored)} restored, {len(kept)} left for review")
    return 0


def _cargo_outside(manifest: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    """Resolve `manifest` with the stack overlay out of scope.

    Cargo discovers `.cargo/config.toml` upward from the *current directory*,
    not from the manifest path. Running from a scratch directory outside the
    Atlas tree is therefore what makes this resolve against git rather than the
    local working trees -- and it does so without toggling the shared overlay
    out from under concurrent peers. The deadline ends cargo's whole process
    tree; a timeout or a launch failure is a failed resolve (exit 124 or 127).
    """
    with tempfile.TemporaryDirectory(prefix="atlas-lock-") as scratch:
        env = clean_process_env()
        # Leaving the overlay's scope also leaves `[build] target-dir` behind,
        # so cargo would default to a per-member `target/` -- the cache fork
        # the shared root exists to prevent. Name the canonical shared path
        # explicitly: this is the value the config would have supplied, not an
        # override of it.
        env["CARGO_TARGET_DIR"] = str(ROOT / "target")
        command = [
            *CARGO_COMMAND, "metadata", "--format-version", "1",
            "--manifest-path", str(manifest), *extra,
        ]
        try:
            result = execute_process(
                command, cwd=Path(scratch), env=env, timeout=CARGO_METADATA_DEADLINE_SECONDS
            )
        except GitProcessError as error:
            return subprocess.CompletedProcess(
                command, 124 if error.timed_out else 127, "", str(error)
            )
        return subprocess.CompletedProcess(
            command,
            result.returncode,
            result.stdout.decode("utf-8", errors="replace"),
            result.stderr.decode("utf-8", errors="replace"),
        )


def cmd_regenerate(args) -> int:
    """Repair locks into standalone form, then prove they resolve `--locked`.

    `cargo metadata` re-resolves only what the lock cannot supply, so a
    stripped source is restored without gratuitously advancing every unrelated
    pin -- which `cargo generate-lockfile` would do.
    """
    members = args.members or sorted(registered_member_names())
    failed = 0
    for member in members:
        manifest = REPOS / member / "Cargo.toml"
        if not manifest.is_file():
            print(f"{member}: no root Cargo.toml; skipped")
            continue
        repair = _cargo_outside(manifest)
        if repair.returncode != 0:
            failed += 1
            print(f"{member}: repair FAILED\n{repair.stderr.rstrip()}")
            continue
        verify = _cargo_outside(manifest, "--locked")
        if verify.returncode != 0:
            failed += 1
            print(f"{member}: --locked verification FAILED\n{verify.stderr.rstrip()}")
            continue
        print(f"{member}: repaired and verified (`cargo metadata --locked` ok)")
    return 1 if failed else 0


def cmd_sync_hooks(args) -> int:
    """Deploy stack-owned hooks into selected members, or all by default.

    The hooks have to exist inside the member for a standalone clone -- one
    checked out on its own, or on a CI runner -- to run them at all, so
    `core.hooksPath` pointing back into the Atlas tree cannot be the only
    mechanism. That is why each member carries a copy. What it must not be is
    twenty-two hand-maintained copies: this stack's measurement found two
    divergent versions of `pre-push` across twenty-two members, and the fix
    that only one of them carried was the one that mattered on a worktree owned
    by another account.

    So the copies stay and stop being authored: `scripts/git-hooks/` is the
    single source and this writes it outward. `--check` reports drift without
    writing, which is what CI runs.
    """
    source_dir = Path(__file__).resolve().parent / "git-hooks"
    hook_filter = getattr(args, "hook", None)
    if hook_filter and not (source_dir / hook_filter).is_file():
        print(f"hook not found: {hook_filter}")
        return 2
    hooks = sorted(
        p for p in source_dir.iterdir() if p.is_file() and (not hook_filter or p.name == hook_filter)
    )
    members = member_scope(args.members)
    if members is None:
        return 2
    drifted, written, absent = [], 0, []
    for member in members:
        repo = REPOS / member
        if not repo.is_dir():
            continue
        target_dir = repo / MEMBER_HOOK_COPY
        if not target_dir.is_dir():
            absent.append(member)
            continue
        for hook in hooks:
            target = target_dir / hook.name
            want = hook.read_bytes()
            have = target.read_bytes() if target.exists() else None
            if have == want:
                continue
            if args.check:
                drifted.append(f"{member}/.githooks/{hook.name}")
                continue
            target.write_bytes(want)
            written += 1
    if args.check:
        for d in drifted:
            print(f"drift: {d}")
        if absent:
            print(f"no .githooks directory: {', '.join(absent)}")
        print(f"{len(drifted)} hook(s) differ from scripts/git-hooks")
        return 1 if drifted else 0
    print(f"wrote {written} hook file(s); {len(absent)} member(s) without .githooks")
    return 0


HOOK_MODE = "100755"
# One branch per member, named for the work and fixed: a member's hook request
# is the single place its `.githooks/` copy is updated from, so a run that
# names its own branch opens a second request carrying a different revision of
# the same file. Thirteen members carried exactly that pair on 2026-09-21.
PUBLISH_BRANCH = "ci/sync-stack-hooks"
# Hosting calls do not run member code and use the ordinary test slow bound.
HOSTING_DEADLINE_SECONDS = 30


def request_already_open(returncode: int, stderr: str) -> bool:
    """Whether `gh pr create` refused because the branch's request exists.

    A re-run force-pushes the same branch, so the open request already points
    at the commit just pushed. Refusing to create a second one is the correct
    outcome, and treating it as a failure skips the enqueue that follows.
    """
    return returncode != 0 and "already exists" in (stderr or "")


def member_scope(requested: list[str]) -> tuple[str, ...] | None:
    """Return the requested registered members, or all members by default."""
    registered = set(registered_member_names())
    members = set(requested) if requested else registered
    unknown = members - registered
    if unknown:
        print(f"unregistered members: {', '.join(sorted(unknown))}", file=sys.stderr)
        return None
    return tuple(sorted(members))


def git_bytes(
    repo: Path,
    *args: str,
    stdin: bytes | None = None,
    index: Path | None = None,
) -> bytes:
    """Run bounded git in `repo`; raise with git's message on failure.

    `index` points git at a private index file, so a commit can be built from a
    member's fetched default without reading or touching its working tree or
    its real index -- which may belong to a peer mid-edit.
    """
    env = dict(os.environ)
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    try:
        result = execute_git(
            repo,
            tuple(args),
            stdin=stdin,
            env=env,
            timeout=GIT_DEADLINE_SECONDS,
        )
    except GitProcessError as error:
        raise RuntimeError(str(error)) from error
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} in {repo.name}: {detail}")
    return result.stdout


def git_in(
    repo: Path,
    *args: str,
    stdin: bytes | None = None,
    index: Path | None = None,
) -> str:
    """Run bounded git and decode its output as replacement-tolerant UTF-8."""
    return git_bytes(repo, *args, stdin=stdin, index=index).decode(
        "utf-8", errors="replace"
    ).strip()


def hosting_in(repo: Path, *args: str) -> str:
    """Run a bounded GitHub CLI command and preserve its failure context."""
    command = ["gh", *args]
    try:
        proc = subprocess.run(
            command,
            cwd=str(repo),
            capture_output=True,
            timeout=HOSTING_DEADLINE_SECONDS,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"gh command timed out after {HOSTING_DEADLINE_SECONDS}s in {repo.name}: "
            f"{' '.join(command)}"
        ) from error
    except OSError as error:
        raise RuntimeError(f"cannot run gh in {repo.name}: {error}") from error
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} in {repo.name}: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def committed_hooks(atlas: Path, ref: str) -> list[tuple[str, bytes]]:
    """The owned hooks as committed at `ref`: (file name, exact bytes) pairs.

    Read from the commit, never the working tree: in a shared checkout the
    tree holds whatever branch a peer has checked out, so a publish sourced
    from `scripts/git-hooks/` on disk would deploy that branch's copy -- a
    stale hook reached every member that way before this read the commit.
    """
    listing = git_in(atlas, "ls-tree", "--name-only", f"{ref}:scripts/git-hooks")
    hooks = []
    for name in sorted(listing.splitlines()):
        blob = git_bytes(atlas, "cat-file", "blob", f"{ref}:scripts/git-hooks/{name}")
        hooks.append((name, blob))
    return hooks


def hook_commit(
    repo: Path, base: str, hooks: list[tuple[str, bytes]], message: str
) -> str | None:
    """A commit on `base` whose `.githooks/` carries `hooks`, or None if current.

    `hooks` are (file name, bytes) pairs, so line endings are exactly the
    owned copy's whatever any checkout's `core.autocrlf` says, and the mode is
    executable so the hook runs on a Unix clone.
    """
    with tempfile.TemporaryDirectory(prefix="atlas-hooks-") as scratch:
        index = Path(scratch) / "index"
        git_in(repo, "read-tree", base, index=index)
        for name, content in hooks:
            blob = git_in(repo, "hash-object", "-w", "--stdin", stdin=content)
            git_in(
                repo, "update-index", "--add", "--cacheinfo",
                f"{HOOK_MODE},{blob},.githooks/{name}", index=index,
            )
        tree = git_in(repo, "write-tree", index=index)
    if tree == git_in(repo, "rev-parse", f"{base}^{{tree}}"):
        return None
    return git_in(repo, "commit-tree", tree, "-p", base, stdin=message.encode("utf-8"))


def push_hook_branch(
    repo: Path, commit: str, branch: str, pre_push_hook: bytes
) -> None:
    """Update the publication branch under a freshly observed explicit lease."""
    ref = f"refs/heads/{branch}"
    listing = git_bytes(repo, "ls-remote", "--heads", "origin", ref)
    if listing == b"":
        expected = ""
    else:
        try:
            text = listing.decode("ascii")
        except UnicodeDecodeError as error:
            raise RuntimeError(
                f"git ls-remote returned non-ASCII output for {ref}"
            ) from error
        rows = text.splitlines()
        if len(rows) != 1:
            raise RuntimeError(f"git ls-remote returned {len(rows)} rows for {ref}")
        fields = rows[0].split()
        if len(fields) != 2:
            raise RuntimeError(f"git ls-remote returned a malformed row for {ref}")
        expected, observed_ref = fields
        if observed_ref != ref:
            raise RuntimeError(
                f"git ls-remote returned {observed_ref} while querying {ref}"
            )
        if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected) is None:
            raise RuntimeError(f"git ls-remote returned a malformed object ID for {ref}")
    # A member checkout may hold an older or dirty .githooks copy. Select the
    # committed source hook for this push only; Git still invokes it normally
    # with the pushed ref range on stdin.
    with tempfile.TemporaryDirectory(prefix="atlas-pre-push-") as temporary:
        hook_path = Path(temporary) / "pre-push"
        hook_path.write_bytes(pre_push_hook)
        hook_path.chmod(0o755)
        git_in(
            repo,
            "-c",
            f"core.hooksPath={temporary}",
            "push",
            "-q",
            f"--force-with-lease={ref}:{expected}",
            "origin",
            f"{commit}:{ref}",
        )


def pull_request_for(
    repo: Path,
    branch: str,
    base: str,
    subject: str,
    message: str,
) -> tuple[str, bool]:
    """Return the branch's open pull request, creating it when absent."""
    url = hosting_in(
        repo,
        "pr",
        "list",
        "--head",
        branch,
        "--base",
        base,
        "--state",
        "open",
        "--json",
        "url",
        "--jq",
        ".[0].url",
    )
    if url and url != "null":
        return url, False
    return (
        hosting_in(
            repo,
            "pr",
            "create",
            "--head",
            branch,
            "--base",
            base,
            "--title",
            subject,
            "--body",
            message,
        ),
        True,
    )


def enqueue_pull_request(repo: Path, url: str) -> None:
    """Enable merge-on-green for a pull request, surfacing refusal as failure."""
    hosting_in(repo, "pr", "merge", url, "--merge", "--auto")


def cmd_publish_hooks(args) -> int:
    """Publish the owned hooks to every member's default branch, one PR each.

    `sync-hooks` writes into each member's working tree, which is whatever
    branch -- often a peer's, often dirty -- happens to be checked out there, so
    a fleet deployment through it either waits on every tree or edits someone
    else's branch. This builds each member's commit on its freshly fetched
    default instead, with a private index, touching no tree. Members are the
    registered ones only: iterating the `repos/` directory would include
    anything else checked out there, a private consumer among them.

    Without `--push` it reports what it would publish.
    """
    members = member_scope(args.members)
    if members is None:
        return 2
    requested_source = args.source_ref
    if requested_source == "":
        print("invalid committed hook source '': reference is empty", file=sys.stderr)
        return 2
    git_in(ROOT, "fetch", "-q", "origin")
    atlas_default = git_in(ROOT, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    source_ref = atlas_default if requested_source is None else requested_source
    try:
        source_commit = git_in(
            ROOT,
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"{source_ref}^{{commit}}",
        )
    except RuntimeError as error:
        print(f"invalid committed hook source {source_ref!r}: {error}", file=sys.stderr)
        return 2
    committed = committed_hooks(ROOT, source_commit)
    hook_filter = getattr(args, "hook", None)
    if hook_filter:
        hooks = [entry for entry in committed if entry[0] == hook_filter]
        if not hooks:
            print(
                f"committed hook source {source_commit} has no {hook_filter}",
                file=sys.stderr,
            )
            return 2
    else:
        hooks = committed
    pre_push_hook = next(
        (content for name, content in committed if name == "pre-push"), None
    )
    if not pre_push_hook:
        print(
            f"committed hook source {source_commit} has no non-empty pre-push gate",
            file=sys.stderr,
        )
        return 2
    source = git_in(ROOT, "rev-parse", "--short", source_commit)
    subject = "ci: Sync the stack-owned git hooks"
    message = (
        f"{subject}\n\nDeploys atlas `scripts/git-hooks` at {source}, the single\n"
        "source every member's `.githooks/` copies; a copy that differs is the\n"
        "gate-version drift the conformance scan counts.\n"
    )
    failures = 0
    for member in members:
        repo = REPOS / member
        if not repo.is_dir():
            continue
        try:
            git_in(repo, "fetch", "-q", "origin")
            default = git_in(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
            commit = hook_commit(repo, git_in(repo, "rev-parse", default), hooks, message)
            if commit is None:
                print(f"current: {member}")
                continue
            if not args.push:
                print(f"would publish: {member} onto {default}")
                continue
            branch = PUBLISH_BRANCH
            push_hook_branch(repo, commit, branch, pre_push_hook)
            url, created = pull_request_for(
                repo,
                branch,
                default.removeprefix("origin/"),
                subject,
                message,
            )
            enqueue_pull_request(repo, url)
            action = "published" if created else "reused"
            print(f"{action}: {member} {url} enqueued")
        except RuntimeError as error:
            failures += 1
            print(f"FAILED: {error}")
    return 1 if failures else 0


# The hooks ref a shim resolves: the Atlas default branch as last fetched.
HOOK_SOURCE_REF = "refs/remotes/origin/main"

# The client-side hook names in githooks(5), without the `p4-*` and
# `fsmonitor-watchman` integrations no member uses. An owned file under
# another name (`rescue-push`, which the pre-push hook reads from the stack
# ref itself) gets no shim.
GIT_HOOK_NAMES = frozenset({
    "applypatch-msg", "pre-applypatch", "post-applypatch", "pre-commit",
    "pre-merge-commit", "prepare-commit-msg", "commit-msg", "post-commit",
    "pre-rebase", "post-checkout", "post-merge", "pre-push", "pre-auto-gc",
    "post-rewrite", "reference-transaction", "sendemail-validate",
    "post-index-change",
})

# A shim runs the owned hook as committed at `HOOK_SOURCE_REF`, never a
# working-tree copy or the checked-out branch. It resolves the blob at every
# invocation, so a fetch of the Atlas repository moves every member to a
# newer copy of each installed hook; a hook name new to `HOOK_SOURCE_REF`
# needs `install-hooks` again, and one it dropped refuses until
# `install-hooks` removes its shim. The blob is cached by id: a cached file
# is re-hashed before it runs and a fresh copy before it is renamed into
# place, so a corrupt or altered cache, or a blob object whose content does
# not match its id, refuses instead of running. A writer that fails removes
# its partial file; one killed mid-write leaves `<blob>.XXXXXX`, which is
# never run. The cache keeps one file per hook revision.
# Trust: `HOOK_SOURCE_REF` and the commit and tree objects that resolve the
# path are trusted as Git stores them -- Git does not hash a tree it reads,
# and whoever can rewrite them can move the ref too -- but replace refs are
# ignored (`--no-replace-objects`), since `git replace` would redirect the
# lookup without touching either. The environment git runs the hook with is
# trusted as the owned hook itself trusts it: an exported function or a
# `BASH_ENV` file redirects the hook's own `cargo` and `git` as surely as
# the shim's `exec`.
# The lookups name Atlas with `--git-dir`, which outranks any `GIT_DIR` in
# the hook's environment (`git -C <atlas>` would not), and drop the
# variables that would still redirect them to another object store; the
# hook itself runs with the environment git gave it.
HOOK_SHIM = """#!/usr/bin/env bash
# Written by `scripts/atlas-lock-form.py install-hooks`; rerun it instead of
# editing. Runs the owned `{name}` hook as committed at the Atlas
# `{ref}`, never the Atlas checkout's copy, which holds whatever branch a
# peer left checked out.
# The shim's variables carry a reserved prefix and are unset before the exec,
# so a caller's own `cache` or `commit` never reaches the hook altered.
set -euo pipefail
__atlas_shim_git={git_dir}
__atlas_shim_lookup() {{
  env -u GIT_COMMON_DIR -u GIT_OBJECT_DIRECTORY -u GIT_ALTERNATE_OBJECT_DIRECTORIES \\
    -u GIT_REPLACE_REF_BASE git --no-replace-objects --git-dir="$__atlas_shim_git" "$@"
}}
# `show-ref --verify` takes only the full ref name: `rev-parse` would fall
# back to a branch named `{ref}` when the ref itself is gone.
if ! __atlas_shim_commit="$(__atlas_shim_lookup show-ref --verify --hash '{ref}' 2>/dev/null)" ||
   ! __atlas_shim_blob="$(__atlas_shim_lookup rev-parse --verify --quiet "$__atlas_shim_commit:scripts/git-hooks/{name}")"; then
  echo "atlas hooks: {ref} in $__atlas_shim_git has no scripts/git-hooks/{name}; fetch the Atlas repository, then run scripts/atlas-lock-form.py install-hooks there" >&2
  exit 1
fi
__atlas_shim_cache="$__atlas_shim_git/atlas-hooks/blobs/$__atlas_shim_blob"
if [ ! -f "$__atlas_shim_cache" ] || [ "$(__atlas_shim_lookup hash-object --no-filters -- "$__atlas_shim_cache")" != "$__atlas_shim_blob" ]; then
  mkdir -p "${{__atlas_shim_cache%/*}}"
  __atlas_shim_partial="$(mktemp "$__atlas_shim_cache.XXXXXX")"
  # `cat-file` does not check an object against its id, so the copy is
  # hashed before it can run: an altered blob object refuses instead of
  # running. `--no-filters` on every hash: `core.autocrlf` would otherwise
  # give a CRLF copy the id of its LF blob.
  if ! {{ __atlas_shim_lookup cat-file blob "$__atlas_shim_blob" >| "$__atlas_shim_partial" &&
         [ "$(__atlas_shim_lookup hash-object --no-filters -- "$__atlas_shim_partial")" = "$__atlas_shim_blob" ] &&
         chmod +x "$__atlas_shim_partial" && mv -f "$__atlas_shim_partial" "$__atlas_shim_cache"; }}; then
    rm -f "$__atlas_shim_partial"
    exit 1
  fi
fi
set +euo pipefail
set -- "$__atlas_shim_cache" "$@"
unset -f __atlas_shim_lookup
unset __atlas_shim_git __atlas_shim_commit __atlas_shim_blob __atlas_shim_cache __atlas_shim_partial
exec "$@"
"""


def _replace_shim(shim: Path, content: bytes) -> None:
    """Install `content` at `shim` by rename, never by truncating in place.

    Git executes the shim file itself, so a shim rewritten in place is
    briefly empty, and a hook started in that window exits 0 without running
    the owned hook: a refusing gate passes. Unchanged bytes are left alone.
    """
    # Windows has no execute bit; Git for Windows runs a hook by its shebang.
    if (
        shim.is_file()
        and shim.read_bytes() == content
        and (os.name == "nt" or shim.stat().st_mode & 0o100)
    ):
        return
    temporary = shim.with_name(f".{shim.name}.{os.getpid()}.partial")
    temporary.write_bytes(content)
    temporary.chmod(0o755)
    os.replace(temporary, shim)


def _shell_word(text: str) -> str:
    """`text` as one single-quoted bash word, whatever characters it holds."""
    return "'" + text.replace("'", "'\\''") + "'"


def hook_source_commit(atlas: Path) -> str | None:
    """The commit `HOOK_SOURCE_REF` names in `atlas`, matched by full name only."""
    try:
        commit = git_in(atlas, "show-ref", "--verify", "--hash", HOOK_SOURCE_REF)
    except RuntimeError:
        return None
    return commit or None


def common_git_dir(repo: Path) -> Path:
    """The git directory `repo` shares with its linked working trees."""
    return Path(git_in(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def write_hook_shims(atlas: Path) -> Path:
    """The shim directory for `atlas`'s owned hooks, written in its git directory.

    The common git directory, so a linked Atlas tree and the main one share
    one set, and no checkout, branch switch or `git clean` of any Atlas tree
    touches it. Each shim's bytes are written exactly (LF), whatever
    `core.autocrlf` says.
    """
    commit = hook_source_commit(atlas)
    if commit is None:
        raise RuntimeError(f"{atlas} has no {HOOK_SOURCE_REF}; fetch it first")
    git_dir = common_git_dir(atlas)
    shims = git_dir / "atlas-hooks"
    shims.mkdir(parents=True, exist_ok=True)
    # Read as the shim reads it: replace refs ignored.
    listing = git_in(
        atlas, "--no-replace-objects", "ls-tree", "--name-only", f"{commit}:scripts/git-hooks"
    )
    names = set(listing.splitlines()) & GIT_HOOK_NAMES
    # A hook `HOOK_SOURCE_REF` no longer carries loses its shim, which would
    # otherwise refuse every invocation.
    for stale in sorted(GIT_HOOK_NAMES - names):
        if (shims / stale).is_file():
            (shims / stale).unlink()
            print(
                f"install-hooks: removed the {stale} shim; "
                f"{HOOK_SOURCE_REF} has no scripts/git-hooks/{stale}"
            )
    for name in sorted(names):
        _replace_shim(
            shims / name,
            HOOK_SHIM.format(
                name=name, ref=HOOK_SOURCE_REF, git_dir=_shell_word(git_dir.as_posix())
            ).encode(),
        )
    return shims


def cmd_install_hooks(_args) -> int:
    """Point every member's `core.hooksPath` at the committed guard.

    Local git config, so it is a per-clone bootstrap rather than committed
    state -- the same shape as the meta-repo's own
    `git config core.hooksPath .githooks`.

    A member pointing at `.githooks` is retargeted: that directory is the
    copy `sync-hooks` deploys from this same source for standalone clones,
    but as a relative hooks path it runs whatever copy the checked-out branch
    carries, so a tree left on an old branch runs an old gate (CFDrs sat 80
    commits behind on 2026-09-28 and its pre-push failed on the Windows Store
    `python3` stub). Any other value is reported and left alone: silently
    retargeting someone else's hooks would disable them.
    """
    hooks = (Path(__file__).resolve().parent / "git-hooks").as_posix()
    installed, skipped = 0, 0
    for member in sorted(registered_member_names()):
        repo = REPOS / member
        if not repo.is_dir():
            continue
        code, existing, _ = run(
            "git", "-C", str(repo), "config", "--local", "--get", "core.hooksPath"
        )
        current = existing.strip()
        if code == 0 and current and current not in (hooks, MEMBER_HOOK_COPY):
            print(f"{member}: core.hooksPath already set to {current}; left alone")
            skipped += 1
            continue
        code, _, err = run(
            "git", "-C", str(repo), "config", "--local", "core.hooksPath", hooks
        )
        if code != 0:
            print(f"{member}: FAILED to set core.hooksPath: {err.strip()}")
            skipped += 1
            continue
        installed += 1
    print(f"lock-form pre-commit guard installed in {installed} member(s), {skipped} skipped")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sync = sub.add_parser("sync-hooks")
    sync.add_argument("members", nargs="*", help="registered members; defaults to all")
    sync.add_argument("--check", action="store_true",
                      help="report drift instead of writing")
    sync.add_argument("--hook", help="sync only this owned hook")
    sync.set_defaults(func=cmd_sync_hooks)
    publish = sub.add_parser("publish-hooks")
    publish.add_argument("members", nargs="*", help="registered members; defaults to all")
    publish.add_argument("--push", action="store_true", help="push and open the pull requests")
    publish.add_argument("--hook", help="publish only this owned hook")
    publish.add_argument(
        "--source-ref",
        metavar="REF",
        help="locally available committed Atlas ref; defaults to origin/HEAD",
    )
    publish.set_defaults(func=cmd_publish_hooks)
    sub.add_parser("check").set_defaults(func=cmd_check)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("restore").set_defaults(func=cmd_restore)
    staged = sub.add_parser("staged")
    staged.add_argument("--repo", default=None)
    staged.set_defaults(func=cmd_staged)
    regen = sub.add_parser("regenerate")
    regen.add_argument("members", nargs="*")
    regen.set_defaults(func=cmd_regenerate)
    sub.add_parser("install-hooks").set_defaults(func=cmd_install_hooks)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
