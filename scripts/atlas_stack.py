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

import re
import subprocess
from pathlib import Path

from atlas_git_process import GitProcessError, execute as execute_git

ROOT = Path(__file__).resolve().parent.parent
TOOL_ROOT = ROOT / "tools"


def run_tool(
    tool: str, arguments: list[str], **run_options: object
) -> subprocess.CompletedProcess:
    """Run an atlas tool workspace binary through cargo, from inside its workspace.

    rustup resolves the toolchain from the working directory, never from
    `--manifest-path`. The stack root pins the host-qualified msvc channel the
    shared target directory needs (ATLAS-TOOLCHAIN-TRIPLE-083), which no
    Linux runner can install; each tool workspace carries a bare-version pin
    for exactly this run. Every cargo invocation of a tool goes through here
    so no caller can reintroduce the root working directory.
    """
    workspace = TOOL_ROOT / tool
    command = [
        "cargo", "run", "--quiet", "--manifest-path", str(workspace / "Cargo.toml"),
        "--", *arguments,
    ]
    return subprocess.run(command, cwd=workspace, check=False, **run_options)


def registered_member_names(
    repo: Path | None = None, revision: str | None = None
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
            ("show", f"{revision}:.gitmodules"),
            timeout=30,
        )
        if result.returncode:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(detail or f"cannot read .gitmodules at {revision}")
        text = result.stdout.decode("utf-8", errors="replace")
    return {
        match.group(1)
        for match in re.finditer(r"path\s*=\s*repos/([^\s/]+)", text)
    }


def registered_members(repo: Path | None = None) -> list[Path]:
    repository = ROOT if repo is None else repo
    member_root = repository / "repos"
    return [
        member_root / name
        for name in sorted(registered_member_names(repository))
        if (member_root / name).is_dir()
    ]


def member_pins(repo: Path | None = None) -> dict[str, str]:
    """Registered member -> the gitlink SHA ``HEAD`` records for it.

    The pin, never the checkout. A member is routinely parked on a feature
    branch -- that is what conversion work looks like -- so any artifact
    derived from the working tree measures unlanded work and changes whenever
    somebody checks something else out. Reading the pins is what lets the
    oracle be regenerated for a gitlink sweep without checking all ~28 members
    out at the new commits, which a shared tree cannot do.

    ``HEAD`` rather than the index: peers stage gitlink advances constantly,
    and a census that moves when somebody else runs ``git add`` turns the gate
    into noise. In CI the index and ``HEAD`` coincide on a fresh checkout, so
    the gate means the same thing there; locally this keeps it stable until a
    pin is actually committed. ``repo`` selects another Atlas-shaped fixture
    without duplicating gitlink parsing.
    """
    repository = ROOT if repo is None else repo
    result = execute_git(
        repository,
        ("ls-tree", "HEAD", "--", "repos/"),
        timeout=30,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"cannot read member pins from {repository}")
    registered = registered_member_names(repository, "HEAD")
    pins: dict[str, str] = {}
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        meta, _, path = line.partition("\t")
        fields = meta.split()
        if len(fields) != 3 or fields[0] != "160000":
            continue
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "repos" and parts[1] in registered:
            pins[parts[1]] = fields[2]
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
