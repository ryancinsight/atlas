#!/usr/bin/env python3
"""Create, re-point, and close member worktree lanes; export A/B baselines.

The only sanctioned way to make a worktree in the stack (docs/adr/0066). Each
transition enforces the lane rules (AGENTS.md git_discipline: Worktrees) as a
precondition instead of leaving them to an audit after the fact:

  create <member> <branch> [--from <ref>]
      At most two trees per repository, the lane at
      `worktrees/<member>-<branch-slug>`, on a named branch -- a new branch
      starts from the fetched default unless `--from` names another ref.
  repoint <lane> <branch> [--unlanded]
      Moves a clean lane to another branch (and renames it to match) once its
      current work passes the landed-work proof. `--unlanded` is the user's
      explicit override of that proof; a dirty lane is never re-pointed.
  close <lane>
      Removes a clean lane whose work is landed, or whose branch is pushed.
  export <member> <rev> <dir>
      A/B baselines: `git archive <rev>^{tree}` into a directory outside the
      lane root -- a tree, never a checkout.

Non-interactive; every refusal exits 1 with the reason on stderr.

Run: `python scripts/atlas-lane.py create kwavers fix/kw-thing`
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_git_process import (
    GitProcessError, archive, extract_archive, execute as execute_git,
)
from atlas_stack import LANE_ROOT, ROOT, WORKTREE_BOUND, git, worktree_entries
from atlas_target_dir import (
    ensure_lane_config, ensure_member_config, generation_refusal,
)

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
REVISION_SHAPED = re.compile(r"[0-9a-f]{7,40}")


class Refusal(Exception):
    """A precondition the requested transition does not meet."""


def member_repo(member: str) -> Path:
    repos = (ROOT / "repos").resolve()
    repo = ROOT / "repos" / member
    if (member in {"", ".", ".."} or "/" in member or "\\" in member
            or repo.resolve().parent != repos or not (repo / ".git").exists()):
        raise Refusal(f"{member} is not a member checkout under repos/ "
                      "(the umbrella repository opens no lanes)")
    return repo


def lane_name(repo_name: str, branch: str) -> str:
    """`<repo>-<branch-slug>`: the branch with path separators flattened."""
    return f"{repo_name}-{re.sub(r'[^A-Za-z0-9._-]+', '-', branch).strip('.-')}"


def default_branch(repo: Path) -> str:
    try:
        return git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    except RuntimeError as exc:
        raise Refusal(f"{repo.name}: origin/HEAD unset "
                      "(run `git remote set-head origin -a`)") from exc


def landed(repo: Path, rev: str, default: str) -> bool:
    """The landed-work proof: merging `rev` into the default changes nothing."""
    try:
        merged = git(repo, "-c", f"attr.tree={EMPTY_TREE}",
                     "merge-tree", "--write-tree", default, rev).split()[0]
    except RuntimeError:
        return False
    return merged == git(repo, "rev-parse", f"{default}^{{tree}}").strip()


def lane_checkout(argument: str) -> tuple[Path, Path]:
    """Resolve a lane (path, or name under the lane root) to (lane, main repo)."""
    lane = Path(argument)
    if not lane.is_absolute() and not lane.exists():
        lane = LANE_ROOT / argument
    lane = lane.resolve()
    common = Path(git(lane, "rev-parse", "--path-format=absolute",
                      "--git-common-dir").strip())
    repo = Path(worktree_entries(common)[0]["worktree"]).resolve()
    if lane == repo:
        raise Refusal(f"{lane} is a main tree, not a lane")
    return lane, repo


def clean_and_current(lane: Path, repo: Path) -> tuple[str, str | None]:
    """Refuse a dirty lane; return (the fetched default, its branch or None)."""
    dirt = git(lane, "status", "--porcelain", "--untracked-files=all").strip()
    if dirt:
        raise Refusal(f"{lane} has uncommitted work:\n{dirt}")
    git(repo, "fetch", "--quiet", "origin")
    branch = execute_git(lane, ("symbolic-ref", "--quiet", "--short", "HEAD"), timeout=60)
    name = branch.stdout.decode().strip() if branch.returncode == 0 else None
    return default_branch(repo), name


def pin_worktree(repo: Path, lane: Path) -> None:
    """Give a lane its own `core.worktree` when its repository sets a shared one.

    A stack member is a submodule whose gitdir config carries
    `core.worktree = ../../../../repos/<member>`. Git resolves that relative to
    each worktree's own gitdir, so a lane inherits a path that lands on the
    gitdir itself: the files are present, but `git status` reads every tracked
    file as deleted and `git add -A` stages their deletion. A per-worktree
    value overrides the shared one for the lane alone; the main tree keeps it.
    """
    shared = execute_git(repo, ("config", "--get", "core.worktree"), timeout=60)
    if shared.returncode == 0:
        git(repo, "config", "extensions.worktreeConfig", "true")
        git(lane, "config", "--worktree", "core.worktree", lane.as_posix())
    toplevel = Path(git(lane, "rev-parse", "--show-toplevel").strip()).resolve()
    if toplevel != lane.resolve():
        raise Refusal(f"{lane} resolves its working tree to {toplevel}")


def check_target_config() -> None:
    """Apply `atlas-member-target-dir.py generate`'s pre-write check.

    A file Atlas did not write at either generated path, or a Cargo config
    that already redirects a lane's output, refuses the creation before any
    config or lane is written.
    """
    refusal = generation_refusal(ROOT.resolve())
    if refusal is not None:
        raise Refusal(refusal)


def write_target_config() -> None:
    """Refresh the generated target configs the new lane inherits."""
    root = ROOT.resolve()
    try:
        ensure_member_config(root)
        ensure_lane_config(root)
    except RuntimeError as exc:
        raise Refusal(f"cannot write shared target config: {exc}") from exc


def create(member: str, branch: str, start: str | None) -> Path:
    repo = member_repo(member)
    if (branch == "HEAD" or REVISION_SHAPED.fullmatch(branch)
            or execute_git(repo, ("check-ref-format", "--branch", branch),
                           timeout=60).returncode):
        raise Refusal(f"{branch!r} is not a branch name; a lane on it would be "
                      "detached HEAD")
    root = LANE_ROOT.resolve()
    lane = root / lane_name(member, branch)
    if not root.is_relative_to(ROOT.resolve()) or lane.parent != root:
        raise Refusal(f"{lane} is outside the canonical lane root {LANE_ROOT}")
    if lane.exists():
        raise Refusal(f"{lane} already exists")
    git(repo, "fetch", "--quiet", "origin")
    trees = worktree_entries(repo)
    if len(trees) >= WORKTREE_BOUND:
        held = "; ".join(f"{t['worktree']} on {t.get('branch', 'detached HEAD')}"
                         for t in trees[1:])
        raise Refusal(f"{member} already has {len(trees)} trees (bound "
                      f"{WORKTREE_BOUND}): {held} -- re-point or close that lane")
    exists = execute_git(repo, ("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"),
                         timeout=60).returncode == 0
    if exists and start is not None:
        raise Refusal(f"{branch} exists; --from applies only to a new branch")
    check_target_config()
    if exists:
        git(repo, "worktree", "add", str(lane), branch)
    else:
        git(repo, "worktree", "add", "-b", branch, str(lane),
            start or default_branch(repo))
    pin_worktree(repo, lane)
    write_target_config()
    return lane


def repoint(argument: str, branch: str, unlanded: bool) -> Path:
    lane, repo = lane_checkout(argument)
    pin_worktree(repo, lane)
    if lane.parent != LANE_ROOT.resolve():
        raise Refusal(f"{lane} is outside the canonical lane root; close it instead")
    default, _ = clean_and_current(lane, repo)
    if not unlanded and not landed(lane, "HEAD", default):
        raise Refusal(f"{lane} holds work not on {default}; land it, or pass "
                      "--unlanded to re-point anyway")
    if execute_git(repo, ("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"),
                   timeout=60).returncode == 0:
        git(lane, "switch", "--quiet", branch)
    else:
        git(lane, "switch", "--quiet", "-c", branch, default)
    target = lane.parent / lane_name(repo.name, branch)
    if target != lane:
        git(repo, "worktree", "move", str(lane), str(target))
        pin_worktree(repo, target)
    return target


def close(argument: str) -> Path:
    lane, repo = lane_checkout(argument)
    pin_worktree(repo, lane)
    default, branch = clean_and_current(lane, repo)
    pushed = branch is not None and execute_git(
        lane, ("merge-base", "--is-ancestor", "HEAD", f"origin/{branch}"), timeout=60,
    ).returncode == 0
    if not pushed and not landed(lane, "HEAD", default):
        raise Refusal(f"{lane} holds work neither on {default} nor pushed to "
                      f"origin/{branch or '<no branch>'}; push or land it first")
    git(repo, "worktree", "remove", str(lane))
    return lane


def export(member: str, rev: str, directory: Path) -> Path:
    repo = member_repo(member)
    target = directory.resolve()
    if target.is_relative_to(LANE_ROOT.resolve()):
        raise Refusal(f"{target} is inside the lane root; exports live elsewhere")
    if target.exists() and any(target.iterdir()):
        raise Refusal(f"{target} is not empty")
    try:
        payload = archive(repo, f"{rev}^{{tree}}", timeout=600)
    except GitProcessError as exc:
        raise Refusal(str(exc)) from exc
    target.mkdir(parents=True, exist_ok=True)
    extract_archive(payload, target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create")
    p.add_argument("member")
    p.add_argument("branch")
    p.add_argument("--from", dest="start")
    p = sub.add_parser("repoint")
    p.add_argument("lane")
    p.add_argument("branch")
    p.add_argument("--unlanded", action="store_true",
                   help="override the landed-work proof (never cleanliness)")
    p = sub.add_parser("close")
    p.add_argument("lane")
    p = sub.add_parser("export")
    p.add_argument("member")
    p.add_argument("rev")
    p.add_argument("dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create(args.member, args.branch, args.start)
        elif args.command == "repoint":
            result = repoint(args.lane, args.branch, args.unlanded)
        elif args.command == "close":
            result = close(args.lane)
        else:
            result = export(args.member, args.rev, args.dir)
    except (Refusal, RuntimeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
