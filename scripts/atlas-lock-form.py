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

The rule itself, and every mode that judges a lock against it -- the sweep
over committed locks, the staged check of the pre-commit hook, and regeneration
outside the overlay -- live in `lockfile.py`, the stack's one lockfile checker.
This script keeps what acts on the stack as a whole:

    status      the same measurement, reported for committed and working copies
    restore     revert working-tree locks whose only diff from HEAD is the
                overlay rewrite (refuses on any other difference)
    sync-hooks, publish-hooks
                deploy the owned hooks into the members
    install-hooks
                per-clone bootstrap: point member `core.hooksPath` at
                scripts/git-hooks so every member runs the owned pre-commit
                and pre-push hooks, whatever branch its tree has checked out

The rule is deliberately narrow: it flags only a package that is *present in
the lock* yet locked without a source despite being declared as a git
dependency. A member with no git dependencies has nothing to flag, and a
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
import time
import tomllib
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lockfile  # noqa: E402
from atlas_git_process import (  # noqa: E402
    GitProcessError,
    GitProcessResult,
    clean_process_env,
    execute as execute_git,
    execute_process,
)
from atlas_stack import ROOT, registered_member_names  # noqa: E402

REPOS = ROOT / "repos"
# Each member's in-tree copy of scripts/git-hooks, written by `sync-hooks`.
MEMBER_HOOK_COPY = ".githooks"
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


class LockUnit(NamedTuple):
    """One tracked lock at HEAD, with the facts that judge it."""

    label: str
    repository: Path
    lock: str
    facts: lockfile.WorkspaceFacts
    committed: str


def lock_units() -> list[LockUnit]:
    """Every tracked lock at HEAD of the registered members and the superproject.

    The superproject matters because its own tool workspaces live under the
    stack root, so a cargo run inside one walks up into the development overlay
    exactly as a member's does and its lock is rewritten the same way -- while
    being tracked here rather than in a submodule, which is how two tool locks
    reached `main` carrying sixty-one `[[patch.unused]]` tables each.
    """
    repositories = [(member, REPOS / member) for member in sorted(registered_member_names())]
    units = []
    for label, repository in [*repositories, ("atlas", ROOT)]:
        if not repository.is_dir():
            continue
        try:
            texts = lockfile.tracked_texts(repository, staged=False)
        except lockfile.GitUnavailable as error:
            print(f"warning: {label}: locks not read: {error}", file=sys.stderr)
            continue
        for lock, facts in lockfile.workspace_units(texts).items():
            units.append(LockUnit(label, repository, lock, facts, texts[lock]))
    return units


def cmd_status(_args) -> int:
    print(f"{'member/lock':<44} {'HEAD':<10} {'worktree':<10}")
    for unit in lock_units():
        path = unit.repository / unit.lock
        work = path.read_text(encoding="utf-8") if path.exists() else None

        def verdict(text: str | None, facts=unit.facts) -> str:
            if text is None:
                return "missing"
            if facts.fixture:
                return "exempt"
            if lockfile.violations(text, facts.local, facts.git_dependencies):
                return "STRIPPED"
            return "ok" if facts.git_dependencies - facts.local else "no-git-deps"

        label = f"{unit.label}/{unit.lock}"
        print(f"{label:<44} {verdict(unit.committed):<10} {verdict(work):<10}")
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
    if work_text.count(lockfile.PATCH_UNUSED) < head_text.count(lockfile.PATCH_UNUSED):
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
    for unit in lock_units():
        member, repo, lock, head = unit.label, unit.repository, unit.lock, unit.committed
        path = repo / lock
        if not path.exists() or unit.facts.fixture:
            continue
        work = path.read_text(encoding="utf-8")
        if work == head:
            continue
        if lockfile.violations(head, unit.facts.local, unit.facts.git_dependencies):
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
# A push may run the committed 60-second hook gate; the remainder covers Git
# transport and process-tree teardown without leaving an unbounded member.
GIT_DEADLINE_SECONDS = 90
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


def git_result(
    repo: Path,
    *args: str,
    stdin: bytes | None = None,
    index: Path | None = None,
) -> GitProcessResult:
    """Run bounded git in `repo` with the inherited repository selection removed.

    None of the variables `git rev-parse --local-env-vars` lists (`GIT_DIR`,
    `GIT_COMMON_DIR`, `GIT_INDEX_FILE`, ...) in the caller's environment
    redirects the command away from `repo`; only `index` names an index. A
    launch failure or a deadline raises; a non-zero exit is the caller's to
    read.

    `index` points git at a private index file, so a commit can be built from a
    member's fetched default without reading or touching its working tree or
    its real index -- which may belong to a peer mid-edit.
    """
    env = clean_process_env()
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    try:
        return execute_git(
            repo,
            tuple(args),
            stdin=stdin,
            env=env,
            timeout=GIT_DEADLINE_SECONDS,
        )
    except GitProcessError as error:
        raise RuntimeError(str(error)) from error


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
    result = git_result(repo, *args, stdin=stdin, index=index)
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


def retired_member_paths(requested: list[str] | None) -> list[str] | None:
    """The member-relative files a publication deletes, or None when one is unsafe.

    A retired file is one the owned hooks no longer read, so a member's copy is
    a second source (`scripts/lockfile.py`). Only plain relative paths are
    accepted: the deletion is applied to every member's default branch.
    """
    paths = list(requested or [])
    for path in paths:
        parts = path.split("/")
        if path == "" or path.startswith("/") or "\\" in path or ".." in parts or "" in parts:
            print(f"invalid retired path {path!r}: not a plain relative path", file=sys.stderr)
            return None
    return paths


def hook_commit(
    repo: Path,
    base: str,
    hooks: list[tuple[str, bytes]],
    message: str,
    retired: tuple[str, ...] = (),
) -> str | None:
    """A commit on `base` whose `.githooks/` carries `hooks`, or None if current.

    `hooks` are (file name, bytes) pairs, so line endings are exactly the
    owned copy's whatever any checkout's `core.autocrlf` says, and the mode is
    executable so the hook runs on a Unix clone. Each `retired` path is
    removed from the commit's tree when `base` carries it.
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
        for path in retired:
            git_in(repo, "update-index", "--force-remove", "--", path, index=index)
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
        try:
            git_in(repo, "cat-file", "-e", f"{expected}^{{commit}}")
        except RuntimeError:
            git_in(repo, "fetch", "-q", "origin", ref)
            try:
                git_in(repo, "cat-file", "-e", f"{expected}^{{commit}}")
            except RuntimeError as error:
                raise RuntimeError(
                    f"could not fetch the observed {ref} head {expected}"
                ) from error
        candidate_contains_head = True
        try:
            git_in(repo, "merge-base", "--is-ancestor", expected, commit)
        except RuntimeError:
            candidate_contains_head = False
        default = git_in(
            repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"
        )
        default_contains_head = True
        try:
            git_in(repo, "merge-base", "--is-ancestor", expected, default)
        except RuntimeError:
            default_contains_head = False
        if not candidate_contains_head and not default_contains_head:
            raise RuntimeError(
                f"{ref} at {expected} is not an ancestor of candidate {commit}; "
                "refusing to overwrite unique remote work"
            )
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


def hook_publish_message(source: str, retired: list[str], item: str | None) -> str:
    """Build the commit and pull-request message for one hook publication."""
    subject = "ci: Sync the stack-owned git hooks"
    message = (
        f"{subject}\n\nDeploys atlas `scripts/git-hooks` at {source}, the single\n"
        "source every member's `.githooks/` copies; a copy that differs is the\n"
        "gate-version drift the conformance scan counts.\n"
    )
    if retired:
        message += (
            "\nRemoves "
            + ", ".join(f"`{path}`" for path in retired)
            + ", which the hooks no longer read.\n"
        )
    if item is not None:
        message += f"\nItem: {item}\n"
    return message


def cmd_publish_hooks(args) -> int:
    """Publish the owned hooks to every member's default branch, one PR each.

    `sync-hooks` writes into each member's working tree, which is whatever
    branch -- often a peer's, often dirty -- happens to be checked out there, so
    a fleet deployment through it either waits on every tree or edits someone
    else's branch. This builds each member's commit on its freshly fetched
    default instead, with a private index, touching no tree. Members are the
    registered ones only: iterating the `repos/` directory would include
    anything else checked out there, a private consumer among them.

    `--retire PATH` also deletes a repository-relative file the owned hooks no
    longer read, in the same commit and pull request.

    Without `--push` it reports what it would publish.
    """
    members = member_scope(args.members)
    if members is None:
        return 2
    retired = retired_member_paths(getattr(args, "retire", None))
    if retired is None:
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
    item = args.item
    if item is not None and (
        not item or item.strip() != item or "\n" in item or "\r" in item
    ):
        print("invalid item: expected one non-empty line", file=sys.stderr)
        return 2
    source = git_in(ROOT, "rev-parse", "--short", source_commit)
    subject = "ci: Sync the stack-owned git hooks"
    message = hook_publish_message(source, retired, item)
    failures = 0
    for member in members:
        repo = REPOS / member
        if not repo.is_dir():
            continue
        try:
            git_in(repo, "fetch", "-q", "origin")
            default = git_in(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
            commit = hook_commit(
                repo,
                git_in(repo, "rev-parse", default),
                hooks,
                message,
                retired=tuple(retired),
            )
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
# The caller's options, restored for the hook: with SHELLOPTS exported they
# reach it exactly as in a direct run. Read from SHELLOPTS, not `$(set +o)`,
# whose subshell drops errexit. The shim's variables carry a reserved prefix
# and are unset before the exec, so a caller's own `cache` or `commit`, or an
# inherited allexport that would export the shim's assignments, never reaches
# the hook altered. A caller's xtrace is off inside the shim, so the shim's
# own commands never reach the hook's stderr, and back on for the exec.
{{ __atlas_shim_options=":$SHELLOPTS:"; set +x; }} 2>/dev/null
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
case $__atlas_shim_options in *:errexit:*) set -e ;; esac
case $__atlas_shim_options in *:nounset:*) set -u ;; esac
case $__atlas_shim_options in *:pipefail:*) set -o pipefail ;; esac
case $__atlas_shim_options in
  *:xtrace:*) unset __atlas_shim_options; set -x ;;
  *) unset __atlas_shim_options ;;
esac
exec "$@"
"""


# A shim replaced while bash has it open: Windows refuses the rename with a
# denial (WinError 5) until every reader closes it. One hook start reads it in
# milliseconds; overlapping runs can keep it open past the bound, and the
# install then fails rather than leave a member half-installed.
SHIM_REPLACE_ATTEMPTS = 50
SHIM_REPLACE_BACKOFF_SECONDS = 0.1

SHIM_REPLACE_ATTEMPTS = 50
SHIM_REPLACE_BACKOFF_SECONDS = 0.1


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
    for attempt in range(SHIM_REPLACE_ATTEMPTS):
        try:
            os.replace(temporary, shim)
            return
        except PermissionError:
            if attempt + 1 == SHIM_REPLACE_ATTEMPTS:
                temporary.unlink(missing_ok=True)
                raise
            time.sleep(SHIM_REPLACE_BACKOFF_SECONDS)


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


def _comparable_hooks_path(value: str) -> str:
    """One spelling per `core.hooksPath` location, for equality tests.

    An absolute path is resolved and folded as the platform folds file names:
    a trailing separator, backslashes, and drive-letter or directory case
    name the same directory on Windows. A relative value is a name resolved
    against each work tree (`.githooks`), so only its separators are unified.
    """
    if os.path.isabs(value):
        return os.path.normcase(os.path.realpath(value))
    return value.replace("\\", "/").rstrip("/")


def _same_directory(first: str | Path, second: str | Path) -> bool:
    """Whether two existing paths name one directory."""
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def cmd_install_hooks(_args) -> int:
    """Point every member's `core.hooksPath` at the owned-hook shims.

    Local git config, so it is a per-clone bootstrap rather than committed
    state -- the same shape as the meta-repo's own
    `git config core.hooksPath .githooks`.

    Two earlier values are retargeted, because each ran a working-tree copy.
    `.githooks` is the copy `sync-hooks` deploys for standalone clones, and a
    tree left on an old branch ran an old gate (CFDrs sat 80 commits behind
    on 2026-09-28 and its pre-push failed on the Windows Store `python3`
    stub). `scripts/git-hooks` in the Atlas tree ran whatever branch that
    shared checkout held: on 2026-10-01 a peer branch's pre-push refused the
    metis fuzz push on a standalone workspace that `origin/main`'s hook gates.
    Any other value is reported and left alone, and the install exits 1:
    silently retargeting someone else's hooks would disable them, and a member
    left on its own hooks does not run the owned gate.

    Every git call is bounded and ignores an inherited `GIT_DIR`, so a member's
    configuration is written in that member. A directory under `repos/` that
    is not a repository of its own is refused: git would resolve it to the
    Atlas repository, or the directory is a linked working tree of it or
    carries a `.git` file naming its git directory, and the write would
    retarget the umbrella's hooks.
    """
    try:
        hooks = write_hook_shims(ROOT).as_posix()
    except (RuntimeError, OSError) as err:
        print(f"install-hooks: shims not all written, members left unchanged: {err}")
        return 1
    # The stack's tree and, when this copy runs from elsewhere (an export),
    # the tree it runs from.
    working_tree_copies = {
        (ROOT / "scripts" / "git-hooks").as_posix(),
        (Path(__file__).resolve().parent / "git-hooks").as_posix(),
    }
    owned = {_comparable_hooks_path(path) for path in (hooks, *working_tree_copies)}
    owned.add(MEMBER_HOOK_COPY)
    atlas_common = Path(hooks).parent
    installed, failed = 0, 0
    left_alone: list[str] = []
    for member in sorted(registered_member_names()):
        repo = REPOS / member
        if not repo.is_dir():
            continue
        try:
            top = git_in(repo, "rev-parse", "--show-toplevel")
            common = common_git_dir(repo)
            if not _same_directory(top, repo) or _same_directory(common, atlas_common):
                print(
                    f"{member}: {repo} is not a repository of its own "
                    f"(git resolves it to {top}, git directory {common}); refused"
                )
                failed += 1
                continue
            read = git_result(repo, "config", "--local", "--get", "core.hooksPath")
            # Exit 1 is "no such key"; any other failure is not an unset value.
            if read.returncode not in (0, 1):
                detail = read.stderr.decode("utf-8", errors="replace").strip()
                print(f"{member}: FAILED to read core.hooksPath: {detail}")
                failed += 1
                continue
            current = read.stdout.decode("utf-8", errors="replace").strip()
            if current and _comparable_hooks_path(current) not in owned:
                print(f"{member}: core.hooksPath already set to {current}; left alone")
                left_alone.append(member)
                continue
            write = git_result(repo, "config", "--local", "core.hooksPath", hooks)
        except RuntimeError as err:
            print(f"{member}: FAILED to install: {err}")
            failed += 1
            continue
        if write.returncode != 0:
            detail = write.stderr.decode("utf-8", errors="replace").strip()
            print(f"{member}: FAILED to set core.hooksPath: {detail}")
            failed += 1
            continue
        installed += 1
    # The Atlas root gates its own pushes with the same shims. Its
    # `core.hooksPath=.githooks` runs the checked-out tip's hook: the
    # trampoline prelude corrects only a copy that still contains the
    # prelude, so a tip that replaces `.githooks/pre-push` edits the gate
    # that judges it (ATLAS-ROOT-HOOK-TIP-CONTROLLED). The shim runs the
    # origin/main blob, which no pushed tip can alter.
    try:
        read = git_result(ROOT, "config", "--local", "--get", "core.hooksPath")
        if read.returncode not in (0, 1):
            detail = read.stderr.decode("utf-8", errors="replace").strip()
            print(f"atlas: FAILED to read core.hooksPath: {detail}")
            failed += 1
        else:
            current = read.stdout.decode("utf-8", errors="replace").strip()
            if current and _comparable_hooks_path(current) not in owned:
                print(f"atlas: core.hooksPath already set to {current}; left alone")
                left_alone.append("atlas")
            else:
                write = git_result(ROOT, "config", "--local", "core.hooksPath", hooks)
                if write.returncode != 0:
                    detail = write.stderr.decode("utf-8", errors="replace").strip()
                    print(f"atlas: FAILED to set core.hooksPath: {detail}")
                    failed += 1
                else:
                    print("atlas: core.hooksPath -> owned-hook shims")
    except RuntimeError as err:
        print(f"atlas: FAILED to install: {err}")
        failed += 1

    print(
        f"owned hook shims installed in {installed} member(s), "
        f"{len(left_alone)} left alone, {failed} failed"
    )
    if left_alone:
        print(f"install-hooks: left on their own core.hooksPath: {', '.join(left_alone)}")
    # A member left on other hooks does not run the owned gate.
    return 1 if failed or left_alone else 0


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
        "--retire",
        action="append",
        metavar="PATH",
        help="also delete this repository-relative file in the same commit "
        "(repeatable); for a file the owned hooks no longer read",
    )
    publish.add_argument(
        "--source-ref",
        metavar="REF",
        help="locally available committed Atlas ref; defaults to origin/HEAD",
    )
    publish.add_argument(
        "--item",
        metavar="ID",
        help="append an Item trailer to each generated member commit",
    )
    publish.set_defaults(func=cmd_publish_hooks)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("restore").set_defaults(func=cmd_restore)
    sub.add_parser("install-hooks").set_defaults(func=cmd_install_hooks)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
