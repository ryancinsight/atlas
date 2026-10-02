#!/usr/bin/env python3
"""Advance every consumer's lock to named first-party provider merges.

# The trap this exists for

A provider merge (hermes `6da6d139`, the Linux processor binding) changes
nothing for a consumer until that consumer's `Cargo.lock` moves. Six members
depend on `hermes-simd`; on 2026-09-01 their locks sat at unrelated hermes
revisions and only the one with an acceptance line advanced, by hand. Pin
discipline says allowlisted consumers never sit more than one sweep behind and
that the sweep is a tool, never agent choreography. This is the tool.

# What it does

A sweep names its targets: `--target <provider>=<rev>` per provider merge, or
`--heads` for every registered provider's fetched default-branch head, each
resolved to a full SHA and printed before anything moves. A sweep is a
deliberate act after specific merges -- defaulting to a provider's moving HEAD
churned three consumer locks on a board-only commit the first time that was
exercised.

For each registered member, read from its fetched default branch:

1. Its lock's first-party git sources whose provider is a target and whose
   revision is not the target's are the stale sources. None: the member is
   current.
2. The default branch is exported (`git archive`) into a temporary directory
   outside the stack, so cargo resolves without the `[patch]` overlay, and
   every package of every stale source is updated in one `cargo update`, by
   full package-id spec, then `cargo check --workspace --locked` runs against
   the shared target directory.
3. Every stale source must now sit at its target. A provider whose head moved
   past the named merge -- the sweep's own lock commits in providers move it
   -- is returned to that merge with `cargo update --precise`; a source that
   cannot return is a failed row, never a lock committed at an unnamed
   revision.
4. With `--open-prs`, the new lock blob is committed through a private index
   onto the default branch -- one commit per consumer per sweep, naming each
   provider merge in a `Refs:` line -- pushed from the member through the
   stack's owned pre-push hook, and opened as a pull request with auto-merge
   (`--rebase`: one commit on an unshared branch).

No working tree is created or switched, so a member at its two-worktree bound
is swept like any other: the bound governs lanes, and this tool needs none.

A rerun with the same targets resumes: a member whose sweep branch is already
pushed reports its open PR as pending, or opens the PR an interrupted run did
not, without resolving or pushing again. Each member is fetched again just
before it is planned, so a landed sweep PR reads as current rather than as a
stale base to sweep a second time.

A consumer that cannot advance is a row with its reason, never a silent
omission; the exit status is non-zero if any such row exists. The consumer's
own CI verifies the advance; the `cargo check` catches API breaks before a
runner is spent.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import lockfile  # noqa: E402  (overlay-free cargo runner; shared, not copied)
from atlas_pull_request import open_pull_request  # noqa: E402
from atlas_stack import ROOT, git, registered_members  # noqa: E402

LOG_ROOT = ROOT / "output" / "lock-sweep"
FIRST_PARTY_GIT = "git+https://github.com/ryancinsight/"
# A pushed member branch runs the member's whole pre-push gate, which can queue
# on the shared build-identity lease (900 s) before it builds.
PUSH_TIMEOUT_SECONDS = 3000
SOURCE_LINE = re.compile(r'^source = "(?P<source>[^"]+)"$', re.M)


@dataclass(frozen=True)
class LockedPackage:
    """One `[[package]]` of a lock that resolves through a first-party git source."""

    name: str
    version: str
    url: str
    rev: str

    @property
    def provider(self) -> str:
        return provider_repo_name(self.url)

    @property
    def spec(self) -> str:
        """The package-id spec naming exactly this entry.

        `name@version` alone is ambiguous when one repository is locked under
        two URL spellings (`Mnemosyne` and `Mnemosyne.git`), so the source URL
        is part of the spec."""
        return f"git+{self.url}#{self.name}@{self.version}"


@dataclass(frozen=True)
class Plan:
    """One member's stale first-party sources against the sweep's targets."""

    member: Path
    base: str
    stale: tuple[LockedPackage, ...]

    @property
    def name(self) -> str:
        return self.member.name

    def providers(self) -> list[str]:
        return sorted({package.provider for package in self.stale})


@dataclass(frozen=True)
class Outcome:
    """What the sweep did, or could not do, for one member."""

    member: str
    action: str
    detail: str
    ok: bool


# --- pure functions (unit-tested) ---------------------------------------------


def normalize_repo_url(url: str) -> str:
    """Canonical form for a first-party GitHub URL: lower-case, no `.git`."""
    return url.rstrip("/").removesuffix(".git").lower()


def provider_repo_name(url: str) -> str:
    """The stack member a first-party URL refers to, lower-case."""
    return normalize_repo_url(url).rsplit("/", 1)[-1]


def first_party_packages(lock_text: str) -> list[LockedPackage]:
    """Every lock entry resolved through an unpinned first-party git source.

    A source carrying a query (`?rev=`, `?branch=`, `?tag=`) is a pin the
    manifest states; advancing it is a manifest change, not a lock sweep."""
    packages = []
    for block in lock_text.split("[[package]]")[1:]:
        source = SOURCE_LINE.search(block)
        if not source or not source.group("source").startswith(FIRST_PARTY_GIT):
            continue
        location, _, rev = source.group("source").removeprefix("git+").partition("#")
        if "?" in location or not rev:
            continue
        name = re.search(r'^name = "([^"]+)"$', block, re.M)
        version = re.search(r'^version = "([^"]+)"$', block, re.M)
        if name and version:
            packages.append(LockedPackage(name.group(1), version.group(1), location, rev))
    return packages


def stale_packages(lock_text: str, targets: dict[str, str]) -> tuple[LockedPackage, ...]:
    """The first-party entries whose provider is a target they are not at."""
    return tuple(
        package
        for package in first_party_packages(lock_text)
        if package.provider in targets and package.rev != targets[package.provider]
    )


def pullbacks(lock_text: str, stale: tuple[LockedPackage, ...], targets: dict[str, str]) -> list[tuple[str, str]]:
    """One `(package spec, target)` per stale source cargo resolved past its target.

    An unpinned update resolves every stale source at its provider's branch
    head, which moves on during a sweep -- the sweep's own lock commits in
    providers move it. `--precise` on any one package of a git source moves the
    whole source, so each one returns to its named merge with one call."""
    sources = {(package.url, package.provider) for package in stale}
    chosen: dict[str, tuple[str, str]] = {}
    for package in first_party_packages(lock_text):
        target = targets.get(package.provider)
        if (package.url, package.provider) in sources and package.rev != target:
            chosen.setdefault(package.url, (package.spec, target))
    return [chosen[url] for url in sorted(chosen)]


def unmet_targets(lock_text: str, stale: tuple[LockedPackage, ...], targets: dict[str, str]) -> list[str]:
    """Stale sources the updated lock still does not resolve at their target.

    Cargo resolves an unpinned git source at the branch head it fetches. When
    that head moved past the named merge, the lock would record a revision the
    sweep never named; that is reported, not committed."""
    sources = {(package.url, package.provider) for package in stale}
    misses = []
    for package in first_party_packages(lock_text):
        if (package.url, package.provider) in sources and package.rev != targets[package.provider]:
            misses.append(
                f"{package.name} resolved {package.rev[:8]}, target "
                f"{package.provider}@{targets[package.provider][:8]}"
            )
    return sorted(set(misses))


def failure_detail(member_name: str, stage: str, stderr: str) -> str:
    """Name the failure, and keep the whole diagnostic on disk.

    A cargo resolver error states the unsatisfiable requirement on its first
    `error:` line and spends the remaining lines narrating the dependency
    chain that reached it. Reporting the *last* line therefore named the far
    end of that chain -- "which satisfies git dependency `hephaestus-wgpu`
    (locked to 0.19.0)" -- and every conflict read as a mystery about a
    package that was not the constraint. The first error line is the
    constraint; the rest is written beside it so the chain is still readable.
    """
    lines = stderr.strip().splitlines()
    head = next((line.strip() for line in lines if line.strip().startswith("error")), "")
    if not head:
        head = lines[-1].strip() if lines else "no diagnostic"
    slug = stage.replace(" ", "-")
    log = LOG_ROOT / f"{member_name}-{slug}.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(stderr, encoding="utf-8")
        return f"{stage}: {head} [full: {log.relative_to(ROOT).as_posix()}]"
    except OSError:
        return f"{stage}: {head}"


def coauthor() -> str:
    """The agent this run should be attributed to.

    The trailer names who wrote the commit, and the commit is written by
    whichever agent invokes the sweep -- not by whichever one wrote this
    template. `ATLAS_SWEEP_COAUTHOR` carries it; the default keeps the
    original attribution for a run that does not set it.
    """
    return os.environ.get(
        "ATLAS_SWEEP_COAUTHOR", "Claude Fable 5.1 <noreply@anthropic.com>"
    )


def branch_name(targets: dict[str, str]) -> str:
    """One branch per sweep: the provider and revision when there is one
    target, a digest of the whole target set otherwise."""
    if len(targets) == 1:
        (provider, rev), = targets.items()
        return f"build/deps-{provider}-{rev[:8]}"
    digest = hashlib.sha1(
        "".join(f"{p}={r}\n" for p, r in sorted(targets.items())).encode()
    ).hexdigest()[:8]
    return f"build/deps-lock-sweep-{digest}"


def commit_message(plan: Plan, targets: dict[str, str], item: str | None) -> str:
    providers = plan.providers()
    if len(providers) == 1:
        subject = f"build(deps): Update {providers[0]} to {targets[providers[0]][:8]}"
    else:
        subject = "build(deps): Advance first-party locks"
    refs = "".join(f"Refs: {provider}@{targets[provider]}\n" for provider in providers)
    trailer = f"Item: {item}\n" if item else ""
    return (
        f"{subject}\n\n"
        "Advances each first-party git source below to its named provider\n"
        "merge. Resolved outside the stack overlay; `cargo check --workspace\n"
        "--locked` passed before the push. Opened by scripts/atlas-lock-sweep.py.\n\n"
        f"{refs}{trailer}Co-Authored-By: {coauthor()}"
    )


def with_line_endings_of(base: bytes, updated: bytes) -> bytes:
    """`updated` in the line-ending convention of the committed `base`.

    The export is written through the checkout filters, so on Windows cargo
    may read CRLF; the commit must not turn a one-line advance into a
    whole-file rewrite."""
    lf = updated.replace(b"\r\n", b"\n")
    return lf.replace(b"\n", b"\r\n") if b"\r\n" in base else lf


def render_report(targets: dict[str, str], rows: list[Outcome]) -> str:
    named = ", ".join(f"{p}@{r[:8]}" for p, r in sorted(targets.items()))
    width = max((len(o.member) for o in rows), default=8)
    lines = [f"lock sweep -> {named}", f"{'member':<{width}}  action    detail"]
    lines += [f"{o.member:<{width}}  {o.action:<8}  {o.detail}" for o in rows]
    return "\n".join(lines)


# --- repository operations ---------------------------------------------------


def default_branch(member: Path) -> str:
    ref = git(member, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    return ref.removeprefix("origin/") if ref else "main"


def resolve_targets(members: list[Path], requested: list[str], heads: bool) -> dict[str, str]:
    """Provider name -> full SHA of the merge the sweep advances to."""
    by_name = {member.name.lower(): member for member in members}
    wanted: dict[str, str] = {}
    if heads:
        for name, member in by_name.items():
            wanted[name] = f"origin/{default_branch(member)}"
    for entry in requested:
        provider, _, rev = entry.partition("=")
        if not rev or provider.lower() not in by_name:
            sys.exit(f"error: --target {entry!r} is not <registered provider>=<rev>")
        wanted[provider.lower()] = rev
    targets = {}
    for provider, rev in wanted.items():
        full = git(by_name[provider], "rev-parse", "--verify", f"{rev}^{{commit}}").strip()
        targets[provider] = full
    return targets


def plan_member(member: Path, targets: dict[str, str]) -> Plan | None:
    """The member's stale sources at its fetched default branch; None without a lock."""
    base = git(member, "rev-parse", "--verify", f"origin/{default_branch(member)}^{{commit}}").strip()
    try:
        lock_text = git(member, "show", f"{base}:Cargo.lock")
    except RuntimeError:
        return None
    return Plan(member, base, stale_packages(lock_text, targets))


def export_tree(member: Path, base: str, directory: Path) -> None:
    archive = directory / "tree.tar"
    subprocess.run(
        ["git", "-C", str(member), "archive", "--format=tar", "-o", str(archive), base],
        check=True, capture_output=True,
    )
    with tarfile.open(archive) as tree:
        tree.extractall(directory / "tree", filter="data")
    archive.unlink()


def owned_hooks(directory: Path) -> Path:
    """The stack's owned hooks at its fetched default branch.

    A member's configured hooks path names the stack checkout, which sits on
    whatever branch a peer left there, often with a dirty or stale hook."""
    archive = directory / "hooks.tar"
    subprocess.run(
        ["git", "-C", str(ROOT), "archive", "--format=tar", "-o", str(archive),
         f"origin/{default_branch(ROOT)}", "scripts/git-hooks"],
        check=True, capture_output=True,
    )
    with tarfile.open(archive) as hooks:
        hooks.extractall(directory, filter="data")
    return directory / "scripts" / "git-hooks"


def commit_lock(member: Path, base: str, lock: bytes, message: str, scratch: Path) -> str:
    """Commit `lock` as the member's `Cargo.lock` on top of `base`, without a checkout."""
    environment = {**os.environ, "GIT_INDEX_FILE": str(scratch / "index")}

    def plumbing(*arguments: str, data: bytes | None = None) -> str:
        done = subprocess.run(
            ["git", "-C", str(member), *arguments],
            input=data, env=environment, capture_output=True, check=True,
        )
        return done.stdout.decode().strip()

    plumbing("read-tree", base)
    blob = plumbing("hash-object", "-w", "--no-filters", "--stdin", data=lock)
    plumbing("update-index", "--cacheinfo", f"100644,{blob},Cargo.lock")
    tree = plumbing("write-tree")
    return plumbing("commit-tree", tree, "-p", base, "-F", "-", data=message.encode())


def cargo(tree: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return lockfile.run_outside_the_overlay(list(arguments), manifest=tree / "Cargo.toml")


def resolve_lock(plan: Plan, targets: dict[str, str], tree: Path) -> Outcome | None:
    """Advance the exported lock's stale sources to their targets; a failed row, or None."""
    specs = sorted({package.spec for package in plan.stale})
    update = cargo(tree, "update", *(flag for spec in specs for flag in ("--package", spec)))
    if update.returncode != 0:
        return Outcome(plan.name, "failed", failure_detail(plan.name, "cargo update", update.stderr), False)
    # A precise update of one source re-resolves the git sources its packages
    # depend on, which can carry an already-returned source past its target
    # again; a round per source bounds the repetition.
    for _round in range(len({package.url for package in plan.stale}) + 1):
        resolved = (tree / "Cargo.lock").read_text(encoding="utf-8", errors="replace")
        returns = pullbacks(resolved, plan.stale, targets)
        if not returns:
            break
        for spec, target in returns:
            precise = cargo(tree, "update", "--package", spec, "--precise", target)
            if precise.returncode != 0:
                return Outcome(plan.name, "failed", failure_detail(plan.name, "cargo update --precise", precise.stderr), False)
    resolved = (tree / "Cargo.lock").read_text(encoding="utf-8", errors="replace")
    misses = unmet_targets(resolved, plan.stale, targets)
    if misses:
        return Outcome(plan.name, "failed", "source past its target: " + "; ".join(misses), False)
    return None


def advance(plan: Plan, targets: dict[str, str], hooks: Path | None, item: str | None) -> Outcome:
    member = plan.member
    with tempfile.TemporaryDirectory(prefix=f"lock-sweep-{plan.name}-") as scratch_name:
        scratch = Path(scratch_name)
        export_tree(member, plan.base, scratch)
        tree = scratch / "tree"
        failure = resolve_lock(plan, targets, tree)
        if failure is not None:
            return failure
        updated = (tree / "Cargo.lock").read_bytes()
        check = cargo(tree, "check", "--workspace", "--locked")
        if check.returncode != 0:
            return Outcome(plan.name, "failed", failure_detail(plan.name, "cargo check", check.stderr), False)
        moved = ", ".join(plan.providers())
        if hooks is None:
            return Outcome(plan.name, "would", f"{moved} (dry run; check passed)", True)
        base_lock = subprocess.run(
            ["git", "-C", str(member), "show", f"{plan.base}:Cargo.lock"],
            capture_output=True, check=True,
        ).stdout
        commit = commit_lock(
            member, plan.base, with_line_endings_of(base_lock, updated),
            commit_message(plan, targets, item), scratch,
        )
        branch = branch_name(targets)
        try:
            pushed = subprocess.run(
                ["git", "-C", str(member), "-c", f"core.hooksPath={hooks}",
                 "push", "origin", f"{commit}:refs/heads/{branch}"],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=PUSH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return Outcome(plan.name, "failed", f"push: no verdict within {PUSH_TIMEOUT_SECONDS} s", False)
        if pushed.returncode != 0:
            return Outcome(plan.name, "failed", failure_detail(plan.name, "push", pushed.stderr), False)
        return open_sweep_pull_request(plan, targets, item, branch)


def open_sweep_pull_request(plan: Plan, targets: dict[str, str], item: str | None, branch: str) -> Outcome:
    refs = ", ".join(f"`{p}@{targets[p]}`" for p in plan.providers())
    body = (
        f"Advances this member's first-party lock entries to the named provider merges: "
        f"{refs}.\n\nResolved outside the stack overlay; `cargo check --workspace --locked` "
        "passed before the push. Opened by `scripts/atlas-lock-sweep.py`.\n\n"
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
    )
    title = commit_message(plan, targets, item).splitlines()[0]
    opening = open_pull_request(
        base=default_branch(plan.member), head=branch, title=title, body=body,
        cwd=plan.member, method="rebase",
    )
    if opening.failure is not None:
        return Outcome(plan.name, "failed", opening.failure, False)
    return Outcome(plan.name, "opened", opening.url or "", True)


def resume(plan: Plan, targets: dict[str, str], item: str | None, open_prs: bool) -> Outcome | None:
    """The member's row when this sweep already pushed its branch, else None.

    A sweep is rerun with the same named targets after an interrupted run, so
    its branch name is the same. A second commit to that branch would be
    rejected as non-fast-forward after the whole check had run, and a run
    interrupted between push and PR left a branch nobody collects."""
    branch = branch_name(targets)
    if not git(plan.member, "ls-remote", "origin", f"refs/heads/{branch}").strip():
        return None
    listed = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "url", "--jq", ".[].url"],
        cwd=plan.member, capture_output=True, encoding="utf-8", errors="replace",
    )
    if listed.returncode != 0:
        return Outcome(plan.name, "failed", f"gh pr list: {listed.stderr.strip()[-200:]}", False)
    url = listed.stdout.strip()
    if url:
        return Outcome(plan.name, "pending", f"{url} (pushed by an earlier run of this sweep)", True)
    if not open_prs:
        return Outcome(plan.name, "would", f"open a PR for the pushed {branch}", True)
    return open_sweep_pull_request(plan, targets, item, branch)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--target", action="append", default=[], metavar="PROVIDER=REV",
        help="a provider merge to advance consumers to, e.g. hermes=6da6d139; repeatable",
    )
    parser.add_argument(
        "--heads", action="store_true",
        help="target every registered provider's fetched default-branch head (printed before any change)",
    )
    parser.add_argument("--members", help="comma-separated member names to restrict the sweep to")
    parser.add_argument("--item", help="board item ID for the commits' Item: trailer")
    parser.add_argument("--open-prs", action="store_true", help="commit, push, and open one PR per consumer (default: dry run)")
    arguments = parser.parse_args()
    if not arguments.target and not arguments.heads:
        parser.error("name the merges: --target PROVIDER=REV (repeatable) or --heads")

    members = registered_members()
    for member in members:
        git(member, "fetch", "origin", "--quiet")
    targets = resolve_targets(members, arguments.target, arguments.heads)
    print("targets: " + ", ".join(f"{p}@{r}" for p, r in sorted(targets.items())), flush=True)

    # Exports live outside the stack, where no config names the shared target
    # directory; the member's own position in the stack does.
    if "CARGO_TARGET_DIR" not in os.environ:
        shared = lockfile.shared_target_dir(ROOT / "Cargo.toml")
        if shared is None:
            sys.exit("error: no stack config names build.target-dir; refusing to fork the cache")
        os.environ["CARGO_TARGET_DIR"] = str(shared)

    consumers = members
    if arguments.members:
        wanted = set(arguments.members.split(","))
        consumers = [m for m in members if m.name in wanted]

    outcomes: list[Outcome] = []
    with tempfile.TemporaryDirectory(prefix="lock-sweep-hooks-") as hooks_dir:
        hooks = None
        if arguments.open_prs:
            git(ROOT, "fetch", "origin", "--quiet")
            hooks = owned_hooks(Path(hooks_dir))
        for member in consumers:
            # A sweep outlives many merges: a base fetched when it started
            # predates its own earlier members' landings and any peer's.
            git(member, "fetch", "origin", "--quiet")
            plan = plan_member(member, targets)
            if plan is None:
                outcomes.append(Outcome(member.name, "current", "no Cargo.lock", True))
            elif not plan.stale:
                outcomes.append(Outcome(member.name, "current", "every first-party source at its target", True))
            else:
                outcomes.append(
                    resume(plan, targets, arguments.item, arguments.open_prs)
                    or advance(plan, targets, hooks, arguments.item)
                )
            print(render_report(targets, outcomes[-1:]).splitlines()[-1], flush=True)
    print(render_report(targets, outcomes))
    return 0 if all(o.ok for o in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
