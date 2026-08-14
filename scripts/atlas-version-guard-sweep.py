#!/usr/bin/env python3
"""Run the Atlas version-guard integration sweep.

The version-guard tool has two distinct surfaces:

1. Per-member diff scanning, which belongs in the member repo's own CI.
2. Stack-wide coherence scanning, which belongs at the atlas root.

This wrapper covers the second surface and pairs it with the shared
toolchain preflight so the sweep fails early when the Rust environment is
misconfigured. It is intentionally read-only.
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


def run_step(command: list[str], *, env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(command, cwd=ROOT, env=env, check=False)
    return proc.returncode


def main() -> int:
    steps = [
        [sys.executable, str(ROOT / "scripts" / "atlas-toolchain-preflight.py")],
        [
            "cargo",
            "run",
            "--quiet",
            "--manifest-path",
            str(ROOT / "tools" / "version-guard" / "Cargo.toml"),
            "--",
            "coherence",
            "--atlas-root",
            str(ROOT),
        ],
    ]
    env = clean_rust_env()
    for command in steps:
        code = run_step(command, env=env)
        if code != 0:
            return code
    print("version-guard sweep: OK — toolchain preflight and coherence clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
