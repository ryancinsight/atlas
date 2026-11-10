"""Shared stack-universe helpers for the atlas meta-repo scripts.

One definition of the scan universe: `.gitmodules`-registered members only.
Deriving members any other way (directory listing, globbing under `repos/`)
re-creates the defect this module exists to prevent — an unregistered,
git-ignored directory under the member namespace is the sanctioned
private-consumer trace and must never surface in tool output or committed
artifacts, while an unregistered, un-ignored one is namespace pollution to
count without naming (AGENTS.md architecture_scoping: "Private consumers",
"Member namespace hygiene").
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from atlas_git_process import GitProcessError, execute as execute_git

# The stack these scripts measure: the tree they sit in, unless
# `ATLAS_STACK_ROOT` names another. The member pre-push gate runs the copy
# of these scripts committed at the stack's default branch, extracted outside
# the stack, so the stack checkout's branch -- whatever a peer left there --
# never decides which checker runs; this names the live stack it measures.
ROOT = Path(
    os.environ.get("ATLAS_STACK_ROOT") or Path(__file__).resolve().parent.parent
).resolve()
TOOL_ROOT = ROOT / "tools"


def load_sibling(name: str, path: Path):
    """Import a first-party script whose file name is not a Python identifier, once."""
    loaded = sys.modules.get(name)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_tool(
    tool: str, arguments: list[str], **run_options: object
) -> subprocess.CompletedProcess:
    """Run a locked tool with root profiles but without development patches.

    Cargo builds from a neutral directory using a mirrored root config and the
    shared target. A runner restores the tool workspace as the binary's current
    directory. The tool's bare-version pin selects a portable toolchain without
    inheriting the stack root's host-qualified channel.
    """
    workspace = TOOL_ROOT / tool
    process_tree = load_sibling(
        "atlas_process_tree", Path(__file__).resolve().parent / "process_tree.py"
    )
    timeout = run_options.pop("timeout", 600)
    capture_output = run_options.pop("capture_output", False)
    encoding = run_options.pop("encoding", None)
    errors = run_options.pop("errors", None)
    input_value = run_options.pop("input", None)
    configured_environment = run_options.pop("env", None)
    if run_options:
        unexpected = ", ".join(sorted(run_options))
        raise TypeError(f"unsupported run option(s): {unexpected}")
    if isinstance(input_value, str):
        input_value = input_value.encode(encoding or "utf-8", errors or "strict")
    environment = dict(os.environ if configured_environment is None else configured_environment)
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR"):
        environment.pop(name, None)
    environment.setdefault("CARGO_TARGET_DIR", str(ROOT / "target"))
    with (workspace / "rust-toolchain.toml").open("rb") as stream:
        channel = tomllib.load(stream).get("toolchain", {}).get("channel")
    if not isinstance(channel, str) or not channel:
        raise ValueError(f"{workspace / 'rust-toolchain.toml'} has no toolchain channel")
    environment["RUSTUP_TOOLCHAIN"] = channel
    source = load_sibling(
        "atlas_tool_build_source", Path(__file__).resolve().parent / "atlas_build_source.py"
    )
    with tempfile.TemporaryDirectory() as neutral_name:
        neutral = Path(neutral_name)
        config = neutral / "config.toml"
        config.write_text(
            source.cargo_config_without_patches(ROOT / ".cargo" / "config.toml"),
            encoding="utf-8",
            newline="\n",
        )
        runner = neutral / "tool_runner.py"
        runner.write_text(
            "import os, sys\nos.chdir(sys.argv[1])\nos.execv(sys.argv[2], sys.argv[2:])\n",
            encoding="utf-8",
            newline="\n",
        )
        runner_value = json.dumps([sys.executable, str(runner), str(workspace)])
        command = [
            "cargo", "--config", str(config), "--config",
            f"target.'cfg(all())'.runner={runner_value}",
            "run", "--quiet", "--locked", "--manifest-path", str(workspace / "Cargo.toml"),
            "--", *arguments,
        ]
        result = process_tree.run(
            command,
            cwd=neutral,
            env=environment,
            input=input_value,
            timeout=timeout,
            output_mode=(process_tree.OutputMode.CAPTURE if capture_output
                         else process_tree.OutputMode.INHERIT),
        )
    if encoding is None:
        return result
    return subprocess.CompletedProcess(
        result.args,
        result.returncode,
        None if result.stdout is None else result.stdout.decode(encoding, errors or "strict"),
        None if result.stderr is None else result.stderr.decode(encoding, errors or "strict"),
    )


def registered_member_names(
    repo: Path | None = None,
    revision: str | None = None,
    *,
    environment: dict[str, str] | None = None,
) -> set[str]:
    repository = ROOT if repo is None else repo
    if revision is None:
        modules = repository / ".gitmodules"
        if not modules.is_file():
            return set()
        text = modules.read_text(errors="replace")
    else:
        result = execute_git(
            repository,
            ("--no-replace-objects", "show", f"{revision}:.gitmodules"),
            env=environment,
            timeout=30,
        )
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(detail or f"cannot read .gitmodules at {revision}")
        text = result.stdout.decode("utf-8")
    return {
        match.group(1)
        for match in re.finditer(r"path\s*=\s*repos/([^\s/]+)", text)
    }


# The one lane root (AGENTS.md git_discipline: Worktrees). Lanes live here so
# they inherit the stack's shared `.cargo` configuration and build cache.
LANE_ROOT = ROOT / "worktrees"

# Trees per repository: the main tree plus one linked lane. A creation
# precondition in `atlas-lane.py`; a measured class in the conformance scan,
# because nothing checked it before and one member reached five trees.
WORKTREE_BOUND = 2


def canonical_lane(path: Path) -> bool:
    """Whether a linked tree sits under a sanctioned lane root.

    The stack root's `worktrees/`, or a harness-managed `.claude/worktrees/`
    (a sanctioned lane outside the root, bound by every other lane rule).
    """
    parents = {p.name for p in path.parents}
    return path.is_relative_to(LANE_ROOT) or (
        "worktrees" in parents and ".claude" in parents
    )


def worktree_entries(repo: Path) -> list[dict[str, str]]:
    """`git worktree list --porcelain` as records; the first is the main tree."""
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in git(repo, "worktree", "list", "--porcelain").splitlines() + [""]:
        if line.strip():
            key, _, value = line.partition(" ")
            current[key] = value
        elif current:
            entries.append(current)
            current = {}
    return entries


def registered_members(repo: Path | None = None) -> list[Path]:
    repository = ROOT if repo is None else repo
    member_root = repository / "repos"
    return [
        member_root / name
        for name in sorted(registered_member_names(repository))
        if (member_root / name).is_dir()
    ]


def member_pins(
    repo: Path | None = None,
    *,
    revision: str = "HEAD",
    environment: dict[str, str] | None = None,
) -> dict[str, str]:
    """Registered member gitlinks from one committed Atlas revision.

    The index and member checkouts never select the pins. An explicit revision
    also keeps a collected cohort stable when a peer moves the Atlas checkout.
    Raw tree paths avoid Git's display quoting and ignore unregistered entries.
    """
    repository = ROOT if repo is None else repo
    result = execute_git(
        repository,
        ("--no-replace-objects", "ls-tree", "-z", revision, "--", "repos/"),
        env=environment,
        timeout=30,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"cannot read member pins from {repository}")
    paths = {
        f"repos/{name}".encode(): name
        for name in registered_member_names(
            repository, revision, environment=environment
        )
    }
    pins: dict[str, str] = {}
    for record in result.stdout.split(b"\0"):
        meta, _, path = record.partition(b"\t")
        fields = meta.split()
        if len(fields) == 3 and fields[0] == b"160000" and path in paths:
            pins[paths[path]] = fields[2].decode("ascii")
    return pins


def git(repo: Path, *args: str) -> str:
    try:
        result = execute_git(repo, args, timeout=60)
    except GitProcessError as exc:
        raise RuntimeError(str(exc)) from exc
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed in {repo}")
    return result.stdout.decode("utf-8", errors="replace")


def commits_behind_upstream(repo: Path) -> int:
    """How many commits this checkout is behind its tracked upstream.

    Gates report against whichever revision happens to be checked out, and
    members of this stack are routinely behind — eight of twenty-five were,
    the day this was written. A stale checkout then manufactures findings
    that upstream already fixed: coeus reported a drifted ADR index whose
    missing row `origin/main` had carried for six commits.

    Falls back to `origin/main` when `@{upstream}` does not resolve, which
    is the common case rather than an edge one: a detached HEAD has no
    upstream, and detached checkouts are exactly the stale ones.

    Zero when neither resolves, so a caller's note appears only when it
    means something.
    """
    if not (repo / ".git").exists():
        return 0
    for rev in ("@{upstream}", "origin/main"):
        probe = execute_git(
            repo,
            ("rev-parse", "--verify", "--quiet", rev),
            timeout=60,
        )
        if probe.returncode == 1:
            continue
        if probe.returncode:
            detail = probe.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(detail or f"cannot resolve revision {rev} in {repo}")
        out = git(repo, "rev-list", "--count", f"HEAD..{rev}").strip()
        if out.isdigit():
            return int(out)
    return 0


def staleness_note(repo: Path) -> str:
    """Suffix naming how far behind upstream a reporting checkout is."""
    behind = commits_behind_upstream(repo)
    if not behind:
        return ""
    return (
        f" (checkout is {behind} commit(s) behind upstream; "
        "confirm against the current revision before treating this as a defect)"
    )


def is_git_ignored(path: Path) -> bool:
    try:
        result = execute_git(
            ROOT,
            ("check-ignore", "-q", str(path.relative_to(ROOT))),
            timeout=60,
        )
    except GitProcessError as exc:
        raise RuntimeError(str(exc)) from exc
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = result.stderr.decode("utf-8", errors="replace").strip()
    raise RuntimeError(detail or "git check-ignore failed")
