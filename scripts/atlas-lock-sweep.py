#!/usr/bin/env python3
"""Advance every consumer's lock to a merged first-party provider commit.

# The trap this exists for

A provider merge (hermes `6da6d139`, the Linux processor binding) changes
nothing for a consumer until that consumer's `Cargo.lock` moves. Six members
depend on `hermes-simd`; on 2026-09-01 their locks sat at unrelated hermes
revisions and only the one with an acceptance line advanced, by hand. Pin
discipline says allowlisted consumers never sit more than one sweep behind and
that the sweep is a tool, never agent choreography. This is the tool.

# What it does

For one first-party crate and one provider commit, in registered-member order:

1. Find consumers: members whose manifests declare the crate with a
   `git = "https://github.com/ryancinsight/<provider>"` source.
2. Read each consumer's locked revision; skip the ones already at the target.
3. For each consumer that needs the advance, on a fresh branch in a temporary
   lane under `worktrees/` (removed afterwards, so the member's two-tree bound
   holds): `cargo update -p <crate> --precise <rev>` resolved outside the
   stack overlay, `cargo check --workspace --locked`, a `build(deps)` commit,
   a push, and a pull request. Nothing is pushed without `--open-prs`.
4. Print a report. A consumer that cannot advance is a row with its reason,
   never a silent omission; the exit status is non-zero if any such row exists.

The consumer's own CI verifies the advance; this tool's `cargo check` catches
API breaks before a runner is spent.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import lockfile  # noqa: E402  (overlay-free cargo runner; shared, not copied)
from atlas_stack import ROOT, git, registered_members  # noqa: E402

LANE_ROOT = ROOT / "worktrees"
GIT_SOURCE = re.compile(r'git\s*=\s*"(?P<url>https://github\.com/ryancinsight/[^"\s]+)"')


@dataclass(frozen=True)
class Consumer:
    """A member that depends on the crate through a first-party git source."""

    member: Path
    provider_url: str

    @property
    def name(self) -> str:
        return self.member.name


@dataclass(frozen=True)
class PlanRow:
    """One consumer's position relative to the target revision."""

    consumer: Consumer
    locked: str | None
    target: str

    @property
    def needs_advance(self) -> bool:
        return self.locked is None or not self.target.startswith(self.locked)


@dataclass(frozen=True)
class Outcome:
    """What the sweep did, or could not do, for one consumer."""

    consumer: Consumer
    action: str
    detail: str
    ok: bool


# --- pure functions (unit-tested) ---------------------------------------------


def normalize_repo_url(url: str) -> str:
    """Canonical form for a first-party GitHub URL: lower-case, no `.git`."""
    return url.rstrip("/").removesuffix(".git").lower()


def provider_repo_name(url: str) -> str:
    """The stack member directory a first-party URL refers to."""
    return normalize_repo_url(url).rsplit("/", 1)[-1]


def declared_git_source(manifest_text: str, crate: str) -> str | None:
    """The git URL a manifest declares for `crate`, if the line is single-line
    and first-party. Workspace and per-crate tables share this line shape."""
    pattern = re.compile(rf"^\s*{re.escape(crate)}\s*=\s*\{{(?P<body>.*)\}}\s*$", re.M)
    for match in pattern.finditer(manifest_text):
        source = GIT_SOURCE.search(match.group("body"))
        if source:
            return source.group("url")
    return None


def locked_rev(lock_text: str, crate: str) -> str | None:
    """The git revision `crate` is locked to, or `None` if absent or not git."""
    for block in lock_text.split("[[package]]"):
        if re.search(rf'^name = "{re.escape(crate)}"$', block, re.M):
            source = re.search(r'^source = "git\+[^"#]+#(?P<rev>[0-9a-f]+)"$', block, re.M)
            return source.group("rev") if source else None
    return None


def branch_name(crate: str, rev: str) -> str:
    return f"build/{crate}-{rev[:8]}"


def render_report(crate: str, target: str, rows: list[Outcome]) -> str:
    width = max((len(o.consumer.name) for o in rows), default=8)
    lines = [f"lock sweep: {crate} -> {target[:8]}", f"{'member':<{width}}  action    detail"]
    lines += [f"{o.consumer.name:<{width}}  {o.action:<8}  {o.detail}" for o in rows]
    return "\n".join(lines)


# --- repository operations ---------------------------------------------------


def default_branch(member: Path) -> str:
    ref = git(member, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    return ref.removeprefix("origin/") if ref else "main"


def at_origin(member: Path, path: str) -> str:
    """A file's content at the member's fetched default branch.

    Never the working tree: a shared checkout is routinely behind origin, and
    a lock read from it reports an advance that already landed (apollo showed
    the pre-#256 revision this way on the first dry run).
    """
    return git(member, "show", f"origin/{default_branch(member)}:{path}")


def manifest_paths(member: Path) -> list[str]:
    listing = git(member, "ls-tree", "-r", "--name-only", f"origin/{default_branch(member)}")
    return [
        line for line in listing.splitlines()
        if line == "Cargo.toml" or re.fullmatch(r"crates/[^/]+/Cargo\.toml", line)
    ]


def find_consumers(crate: str, members: list[Path]) -> list[Consumer]:
    found = []
    for member in members:
        git(member, "fetch", "origin", "--quiet")
        for path in manifest_paths(member):
            url = declared_git_source(at_origin(member, path), crate)
            if url:
                found.append(Consumer(member, url))
                break
    return found


def resolve_target(consumers: list[Consumer], rev: str | None) -> str:
    """The provider's `origin/<default>` HEAD unless `--rev` names a commit."""
    provider = ROOT / "repos" / provider_repo_name(consumers[0].provider_url)
    git(provider, "fetch", "origin", "--quiet")
    if rev:
        full = git(provider, "rev-parse", "--verify", f"{rev}^{{commit}}").strip()
        if not full:
            sys.exit(f"error: {rev} is not a commit in {provider.name}")
        return full
    return git(provider, "rev-parse", f"origin/{default_branch(provider)}").strip()


def plan(crate: str, target: str, consumers: list[Consumer]) -> list[PlanRow]:
    rows = []
    for consumer in consumers:
        lock_text = at_origin(consumer.member, "Cargo.lock")
        locked = locked_rev(lock_text, crate) if lock_text else None
        rows.append(PlanRow(consumer, locked, target))
    return rows


def cargo(member: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return lockfile.run_outside_the_overlay(list(arguments), manifest=member / "Cargo.toml")


def advance(row: PlanRow, crate: str, open_prs: bool) -> Outcome:
    consumer = row.consumer
    member = consumer.member
    target = row.target
    trees = [line for line in git(member, "worktree", "list").splitlines() if line.strip()]
    if len(trees) >= 2:
        return Outcome(consumer, "skipped", "member already at its two-worktree bound", False)
    lane = LANE_ROOT / f"{consumer.name}-lock-sweep"
    branch = branch_name(crate, target)
    base = f"origin/{default_branch(member)}"
    LANE_ROOT.mkdir(exist_ok=True)
    added = subprocess.run(
        ["git", "-C", str(member), "worktree", "add", "-b", branch, str(lane), base],
        capture_output=True, encoding="utf-8", errors="replace",
    )
    if added.returncode != 0:
        return Outcome(consumer, "failed", f"worktree add: {added.stderr.strip().splitlines()[-1]}", False)
    try:
        update = cargo(lane, "update", "-p", crate, "--precise", target)
        if update.returncode != 0:
            return Outcome(consumer, "failed", f"cargo update: {update.stderr.strip().splitlines()[-1]}", False)
        check = cargo(lane, "check", "--workspace", "--locked")
        if check.returncode != 0:
            error = next((l for l in check.stderr.splitlines() if l.startswith("error")), check.stderr.strip()[-200:])
            return Outcome(consumer, "failed", f"cargo check: {error}", False)
        after = locked_rev((lane / "Cargo.lock").read_text(encoding="utf-8"), crate)
        if not after or not target.startswith(after):
            return Outcome(consumer, "failed", f"lock did not move to {target[:8]} (now {after})", False)
        if not open_prs:
            return Outcome(consumer, "would", f"{row.locked or 'absent'} -> {target[:8]} (dry run; check passed)", True)
        message = (
            f"build(deps): Update {crate} to {target[:8]}\n\n"
            f"Advances the {crate} git source to the provider's merged commit.\n"
            f"Resolved outside the stack overlay; `cargo check --workspace --locked`\n"
            f"passed before this push. Opened by scripts/atlas-lock-sweep.py.\n\n"
            f"Refs: {provider_repo_name(consumer.provider_url)}@{target}\n\n"
            f"Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
        )
        for args in (["add", "Cargo.lock"], ["commit", "-q", "-m", message]):
            done = subprocess.run(["git", "-C", str(lane), *args], capture_output=True, encoding="utf-8", errors="replace")
            if done.returncode != 0:
                return Outcome(consumer, "failed", f"git {args[0]}: {done.stderr.strip()[-200:]}", False)
        pushed = subprocess.run(["git", "-C", str(lane), "push", "-u", "origin", branch], capture_output=True, encoding="utf-8", errors="replace")
        if pushed.returncode != 0:
            return Outcome(consumer, "failed", f"push: {pushed.stderr.strip().splitlines()[-1]}", False)
        body = (
            f"Consumer half of a first-party provider merge: `{crate}` advances to "
            f"`{target}`.\n\nResolved outside the stack overlay; "
            f"`cargo check --workspace --locked` passed before push. Opened by "
            f"`scripts/atlas-lock-sweep.py` (ATLAS-FIRST-PARTY-LOCK-SWEEP-2026-09-01).\n\n"
            "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
        )
        pr = subprocess.run(
            ["gh", "pr", "create", "--base", default_branch(member), "--head", branch,
             "--title", f"build(deps): Update {crate} to {target[:8]}", "--body", body],
            cwd=lane, capture_output=True, encoding="utf-8", errors="replace",
        )
        if pr.returncode != 0:
            return Outcome(consumer, "failed", f"gh pr create: {pr.stderr.strip()[-200:]}", False)
        return Outcome(consumer, "opened", pr.stdout.strip().splitlines()[-1], True)
    finally:
        subprocess.run(["git", "-C", str(member), "worktree", "remove", "--force", str(lane)], capture_output=True)
        if not open_prs:
            subprocess.run(["git", "-C", str(member), "branch", "-D", branch], capture_output=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("crate", help="first-party crate name as consumers declare it, e.g. hermes-simd")
    parser.add_argument("--rev", help="provider commit to pin (default: the provider's origin default HEAD)")
    parser.add_argument("--members", help="comma-separated member names to restrict the sweep to")
    parser.add_argument("--open-prs", action="store_true", help="commit, push, and open one PR per consumer (default: dry run)")
    arguments = parser.parse_args()

    members = registered_members()
    if arguments.members:
        wanted = set(arguments.members.split(","))
        members = [m for m in members if m.name in wanted]
    consumers = find_consumers(arguments.crate, members)
    if not consumers:
        print(f"no registered member declares {arguments.crate} from a first-party git source")
        return 1
    target = resolve_target(consumers, arguments.rev)

    outcomes: list[Outcome] = []
    for row in plan(arguments.crate, target, consumers):
        if not row.needs_advance:
            outcomes.append(Outcome(row.consumer, "current", f"already at {row.locked}", True))
            continue
        outcomes.append(advance(row, arguments.crate, arguments.open_prs))
    print(render_report(arguments.crate, target, outcomes))
    return 0 if all(o.ok for o in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
