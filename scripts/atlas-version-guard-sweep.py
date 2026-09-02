#!/usr/bin/env python3
"""Run the Atlas version-guard integration sweep.

The version-guard tool has two distinct surfaces:

1. Per-member diff scanning, which belongs in the member repo's own CI.
2. Stack-wide coherence scanning, which belongs at the atlas root.

This wrapper covers the second surface and pairs it with the shared
toolchain preflight so the sweep fails early when the Rust environment is
misconfigured. It also runs the Atlas provider-integration closure guard so
root integration records cannot silently drift. It is intentionally read-only.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def clean_rust_env() -> dict[str, str]:
    env = os.environ.copy()
    for var in ("RUSTC", "RUSTDOC"):
        env.pop(var, None)
    return env


def run_step(
    command: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT
) -> int:
    proc = subprocess.run(command, cwd=cwd, env=env, check=False)
    return proc.returncode


def main() -> int:
    # rustup resolves the toolchain from the working directory, never from
    # `--manifest-path`. The stack root pins a host-qualified channel for the
    # shared target directory (ATLAS-TOOLCHAIN-TRIPLE-083), which no Linux
    # runner can install; the tool workspace carries its own bare-version pin
    # for exactly this run, so cargo runs from there.
    tool = ROOT / "tools" / "version-guard"
    steps = [
        ([sys.executable, str(ROOT / "scripts" / "atlas-toolchain-preflight.py")], ROOT),
        (
            [
                "cargo",
                "run",
                "--quiet",
                "--manifest-path",
                str(tool / "Cargo.toml"),
                "--",
                "coherence",
                "--atlas-root",
                str(ROOT),
            ],
            tool,
        ),
        ([sys.executable, str(ROOT / "scripts" / "atlas-provider-integration-audit.py")], ROOT),
    ]
    env = clean_rust_env()
    for command, cwd in steps:
        code = run_step(command, env=env, cwd=cwd)
        if code != 0:
            return code
    print(
        "version-guard sweep: OK - toolchain preflight, coherence,"
        " and provider integration guard clean"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
