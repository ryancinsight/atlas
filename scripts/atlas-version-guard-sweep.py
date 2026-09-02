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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import run_tool  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def clean_rust_env() -> dict[str, str]:
    env = os.environ.copy()
    for var in ("RUSTC", "RUSTDOC"):
        env.pop(var, None)
    return env


def run_step(command: list[str], *, env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(command, cwd=ROOT, env=env, check=False)
    return proc.returncode


def main() -> int:
    env = clean_rust_env()
    steps = [
        lambda: run_step(
            [sys.executable, str(ROOT / "scripts" / "atlas-toolchain-preflight.py")], env=env
        ),
        # The tool runs from its own workspace (atlas_stack.run_tool), whose
        # bare-version toolchain pin every runner can install.
        lambda: run_tool(
            "version-guard", ["coherence", "--atlas-root", str(ROOT)], env=env
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
        "version-guard sweep: OK - toolchain preflight, coherence,"
        " and provider integration guard clean"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
