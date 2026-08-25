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

ROOT = Path(__file__).resolve().parent.parent
MEMBER_ROOT = ROOT / "repos"


def registered_member_names() -> set[str]:
    gm = ROOT / ".gitmodules"
    if not gm.is_file():
        return set()
    return {
        m.group(1)
        for m in re.finditer(
            r"path\s*=\s*repos/([^\s/]+)", gm.read_text(errors="replace")
        )
    }


def registered_members() -> list[Path]:
    return [
        MEMBER_ROOT / name
        for name in sorted(registered_member_names())
        if (MEMBER_ROOT / name).is_dir()
    ]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    ).stdout


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
    for rev in ("@{upstream}", "origin/main"):
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
    return subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", str(path.relative_to(ROOT))],
        capture_output=True,
    ).returncode == 0
