#!/usr/bin/env python3
"""Run the Atlas version-guard integration sweep.

The version-guard tool has two distinct surfaces:

1. Per-member diff scanning, which belongs in the member repo's own CI.
2. Stack-wide coherence scanning, which belongs at the atlas root.

This wrapper covers the second surface and pairs it with the shared
toolchain preflight so the sweep fails early when the Rust environment is
misconfigured. It also runs the Atlas provider-integration closure guard so
root integration records cannot silently drift. It is intentionally read-only.

Pass `--against-remotes` to measure each member at its remote default tip
rather than at its checkout. That is the state a consumer resolves, so it is
the mode a scheduled run wants; it fetches, so the default (working-tree) mode
stays the one an advance gate uses.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import run_tool  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

KNOWN_FLAGS = frozenset({"--against-remotes"})


def clean_rust_env() -> dict[str, str]:
    env = os.environ.copy()
    for var in ("RUSTC", "RUSTDOC"):
        env.pop(var, None)
    return env


def coherence_arguments(argv: list[str]) -> list[str]:
    """The coherence step's arguments, adding the remote view when asked."""
    arguments = ["coherence", "--atlas-root", str(ROOT)]
    if "--against-remotes" in argv:
        arguments.append("--against-remotes")
    return arguments


def run_step(command: list[str], *, env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(command, cwd=ROOT, env=env, check=False)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else []
    unknown = sorted({flag for flag in arguments if flag not in KNOWN_FLAGS})
    if unknown:
        print(
            f"atlas-version-guard-sweep: unknown argument(s): {' '.join(unknown)}",
            file=sys.stderr,
        )
        return 2
    view = "remotes" if "--against-remotes" in arguments else "worktree"
    env = clean_rust_env()
    steps = [
        lambda: run_step(
            [sys.executable, str(ROOT / "scripts" / "atlas-toolchain-preflight.py")], env=env
        ),
        # The tool runs from its own workspace (atlas_stack.run_tool), whose
        # bare-version toolchain pin every runner can install.
        lambda: run_tool(
            "version-guard", coherence_arguments(arguments), env=env
        ).returncode,
        lambda: run_step(
            [sys.executable, str(ROOT / "scripts" / "atlas-provider-integration-audit.py")], env=env
        ),
    ]
    for step in steps:
        code = step()
        if code != 0:
            return code
    print(
        f"version-guard sweep: OK - toolchain preflight, coherence ({view} view),"
        " and provider integration guard clean"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
