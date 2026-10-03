"""Fixtures the root hook tests share.

The tests in `test_root_hook_pre_commit.py`, `test_root_hook_pre_push.py`,
`test_root_hook_lanes.py` and `test_root_hook_stack_root.py` run
`.githooks/pre-commit`, `.githooks/pre-push` and `.githooks/stack-root.sh` in
throwaway repositories. This module builds those repositories (the hook
install, the demo member and its gitlink, the separate-git-dir lane), runs git
as a test committer under one deadline, and counts what the hooks launch.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRE_PUSH = ROOT / ".githooks" / "pre-push"
PRE_COMMIT = ROOT / ".githooks" / "pre-commit"
STACK_ROOT = ROOT / ".githooks" / "stack-root.sh"

# The scripts the pre-push hook runs a gate from, when the pushed tip has them.
GATE_SCRIPTS = (
    "scripts/atlas-artifact-budget.py",
    "scripts/atlas-secret-scan.py",
    "scripts/atlas-refspec-guard.py",
)

# Hang guard for every subprocess a fixture starts: git calls (some run a
# hook that launches a few dozen processes), hook invocations, and `cargo
# build`. It is the 10-minute foreground default of the agent process budget,
# not a speed bound: a call taking 30 s on a loaded host is slow, not hung,
# and failed the old fixed 30 s bound. Hook speed is held instead by counting
# what one lane commit and one push launch (see test_root_hook_lanes.py): the
# git processes a `GIT_TRACE2_EVENT` trace records and the interpreter
# launches a PATH shim records. Other tools (grep, awk, mktemp) are not
# counted.
FIXTURE_PROCESS_TIMEOUT_SECONDS = 600


def fixture_environment() -> dict[str, str]:
    """The process environment without `GIT_*`, and with no user or system git config."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return environment


def git(
    environment: dict[str, str], path: Path, *arguments: str, check: bool = True,
) -> subprocess.CompletedProcess:
    """`git -C path ...` as a test committer, under the fixture deadline."""
    return subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=Test",
         "-c", "user.email=test@example.invalid", *arguments],
        env=environment, check=check, capture_output=True,
        text=True, encoding="utf-8", timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
    )


def git_runner(
    environment: dict[str, str] | None = None,
) -> Callable[..., subprocess.CompletedProcess]:
    """`git(path, *arguments, check=True)` bound to `environment`, read at each call.

    The environment is `fixture_environment()` unless one is given.
    """
    environment = fixture_environment() if environment is None else environment

    def run(path: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        return git(environment, path, *arguments, check=check)

    return run


def repo_git_runner(
    repo: Path, environment: dict[str, str] | None = None,
) -> Callable[..., subprocess.CompletedProcess]:
    """`git(*arguments, check=True)` in `repo`, bound like `git_runner`."""
    run_in = git_runner(environment)

    def run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        return run_in(repo, *arguments, check=check)

    return run


def publish_as_origin_default(environment: dict[str, str], repo: Path, revision: str) -> None:
    """Make `revision` the tip of `repo`'s `origin/main`, and `origin/main` its `origin/HEAD`."""
    git(environment, repo, "update-ref", "refs/remotes/origin/main", revision)
    git(environment, repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")


# The `.gitmodules` text recording the demo member every hook fixture pins.
DEMO_SUBMODULE = '[submodule "repos/demo"]\n\tpath = repos/demo\n\turl = https://example.invalid/demo.git\n'


def init_demo_member(environment: dict[str, str], member: Path) -> None:
    """An empty repository at `member`, which may sit in directories not yet created."""
    member.mkdir(parents=True)
    git(environment, member, "init", "-q", "-b", "main")


def advance_demo_member(environment: dict[str, str], member: Path, value: str) -> str:
    """Commit `value` as the member's `value.txt` and publish it as origin's default.

    Everything else in the member's worktree is committed with it. Returns the
    commit.
    """
    (member / "value.txt").write_text(f"{value}\n", encoding="utf-8")
    git(environment, member, "add", "--all")
    git(environment, member, "commit", "-qm", value)
    commit = git(environment, member, "rev-parse", "HEAD").stdout.strip()
    publish_as_origin_default(environment, member, commit)
    return commit


def demo_member(environment: dict[str, str], member: Path, *values: str) -> list[str]:
    """A published member with one commit per value; returns the commits in order."""
    init_demo_member(environment, member)
    return [advance_demo_member(environment, member, value) for value in values]


def set_gitlink(environment: dict[str, str], repo: Path, commit: str) -> None:
    """Point `repo`'s index entry for the demo member at `commit`."""
    git(environment, repo, "update-index", "--add", "--cacheinfo", f"160000,{commit},repos/demo")


def stage_demo_gitlink(environment: dict[str, str], repo: Path, commit: str) -> None:
    """Stage `.gitmodules` for the demo member and its gitlink at `commit`."""
    (repo / ".gitmodules").write_text(DEMO_SUBMODULE, encoding="utf-8")
    git(environment, repo, "add", ".gitmodules")
    set_gitlink(environment, repo, commit)


def git_processes(trace: Path) -> list[list[str]]:
    """The argv of every git process a `GIT_TRACE2_EVENT` trace records."""
    events = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line]
    return [event["argv"] for event in events if event.get("event") == "start"]


def record_launches(
    environment: dict[str, str], directory: Path, name: str,
) -> tuple[dict[str, str], Path, Path]:
    """`environment` set to record what a hook launches, with the log and trace paths.

    `python3` and `python` shims go first on `PATH`; each appends its
    arguments to the returned log and runs this interpreter, so the log holds
    one line per launch, the probe included. `PYTHON` is unset, so the hook
    does probe. `GIT_TRACE2_EVENT` writes every git process the hook starts to
    the returned trace. All three files live in `directory`, named for `name`,
    so one test records several runs.
    """
    shims = directory / f"{name}-shims"
    launches_log = directory / f"{name}.interpreter.log"
    trace = directory / f"{name}.trace.json"
    shims.mkdir()
    for shim_name in ("python3", "python"):
        shim = shims / shim_name
        shim.write_text(
            "#!/bin/sh\n"
            f'printf \'%s\\n\' "$*" >> "{launches_log.as_posix()}"\n'
            f'exec "{Path(sys.executable).as_posix()}" "$@"\n',
            encoding="utf-8", newline="\n",
        )
        shim.chmod(0o755)
    recorded = {key: value for key, value in environment.items() if key != "PYTHON"}
    recorded["GIT_TRACE2_EVENT"] = str(trace)
    recorded["PATH"] = f"{shims}{os.pathsep}{environment['PATH']}"
    return recorded, launches_log, trace


def install_hook(repo: Path) -> None:
    """The pre-commit hook, its resolver and the scripts it runs, copied into `repo`."""
    (repo / "scripts").mkdir()
    for name in (
        "atlas-stale-side-guard.py", "atlas_stale_side_git.py",
        "atlas_stale_side_basis.py", "atlas_git_process.py", "stale-side-waivers.json",
        "atlas-provider-integration-audit.py", "atlas_stack.py", "check_mdbook_links.py",
    ):
        shutil.copyfile(ROOT / "scripts" / name, repo / "scripts" / name)
    (repo / ".githooks").mkdir()
    for hook in (PRE_COMMIT, STACK_ROOT):
        shutil.copyfile(hook, repo / ".githooks" / hook.name)
        (repo / ".githooks" / hook.name).chmod(0o755)


def init_superproject(environment: dict[str, str], repo: Path) -> None:
    """An empty repository at `repo` that keeps line endings as written."""
    repo.mkdir(exist_ok=True)
    git(environment, repo, "init", "-q", "-b", "main")
    git(environment, repo, "config", "core.autocrlf", "false")


def record_demo_member(
    environment: dict[str, str], repo: Path, commit: str, *paths: str,
) -> None:
    """Install the hook in `repo` and commit it with the demo member's gitlink at `commit`.

    `paths` are further files, relative to `repo`, that the commit takes. No
    hook is enabled: a test sets `core.hooksPath` when it needs one.
    """
    install_hook(repo)
    stage_demo_gitlink(environment, repo, commit)
    git(environment, repo, "add", ".githooks", "scripts", *paths)
    git(environment, repo, "commit", "-qm", "Record demo")


def init_separate_git_dir(
    environment: dict[str, str], worktree: Path, metadata: Path,
) -> None:
    """A repository at `worktree` whose Git metadata is the separate directory `metadata`.

    The worktree's `.git` is then a file naming the metadata, the only marker
    of the canonical worktree from a linked lane. The parents of both are
    created, and nothing is committed.
    """
    worktree.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)
    git(environment, worktree.parent, "init", "-q", "-b", "main",
        "--separate-git-dir", str(metadata), str(worktree))


def separate_git_dir_lane(
    root: Path, populate: Callable[[Path, dict[str, str]], None] | None = None,
) -> tuple[Path, Path, dict[str, str]]:
    """A canonical worktree whose `.git` file points at its metadata, and a lane of it.

    Returns the canonical worktree, the lane and the fixture environment. The
    metadata sits beside the worktree's parent, so only a scan of ancestor
    directories can name the canonical worktree from the lane. The root
    commit holds the installed hook and its scripts; `populate(worktree,
    environment)` runs before it and may add and stage more. No hook is
    enabled: a test sets `core.hooksPath` when it needs one.
    """
    worktree = root / "checkouts" / "canonical"
    environment = fixture_environment()
    init_separate_git_dir(environment, worktree, root / "metadata" / "repo.git")
    install_hook(worktree)
    if populate is not None:
        populate(worktree, environment)
    git(environment, worktree, "add", ".githooks", "scripts")
    git(environment, worktree, "commit", "-qm", "root")
    lane = root / "lane"
    git(environment, worktree, "worktree", "add", "-q", "-b", "lane", str(lane))
    return worktree, lane, environment

