#!/usr/bin/env python3
"""Regression tests for the Atlas Bash toolchain bootstrap."""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "atlas-toolchain-bootstrap.sh"
SCRIPT_RELATIVE = Path("scripts/atlas-toolchain-bootstrap.sh")


def shell_path(path: Path) -> str:
    """Return a path accepted by the Bash/MSYS process on this host."""
    cygpath = shutil.which("cygpath")
    if cygpath:
        result = subprocess.run(
            [cygpath, "-u", str(path)], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    return str(path).replace("\\", "/")


class ToolchainBootstrapTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bash = shutil.which("bash")
        if cls.bash is None:
            raise unittest.SkipTest("bash is required for the bootstrap regression tests")

    def test_script_is_syntactically_valid(self) -> None:
        result = subprocess.run(
            [self.bash, "-n", "./scripts/atlas-toolchain-bootstrap.sh"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bootstrap_clears_overrides_and_canonicalizes_ucrt(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "RUSTC": "",
                "RUSTDOC": "",
                "PATH": f"/usr/bin:/ucrt64/bin:/bin:/ucrt64/bin",
            }
        )
        command = (
            'source "$(pwd)/scripts/atlas-toolchain-bootstrap.sh"; '
            'test -z "${RUSTC-}" && test -z "${RUSTDOC-}"; '
            'if [[ -d /ucrt64/bin ]]; then '
            'test "${PATH%%:*}" = /ucrt64/bin; '
            'test "$(printf "%s" "$PATH" | /usr/bin/tr ":" "\\n" | /usr/bin/grep -Fx /ucrt64/bin | /usr/bin/wc -l)" -eq 1; '
            'fi'
        )
        result = subprocess.run(
            [self.bash, "-c", command],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()


def test_bash_bootstrap_binds_the_shared_target_dir() -> None:
    # `.cargo/config.toml` sets `target-dir`, but cargo finds it only by walking
    # up from the current directory; a build run from outside the stack forks
    # the cache into the member's own `target/`. Six members grew one within
    # hours of the last sweep, so the binding belongs to the shell.
    script = ROOT / "scripts" / "atlas-toolchain-bootstrap.sh"
    text = script.read_text(encoding="utf-8")
    assert "export CARGO_TARGET_DIR=" in text
    assert "${CARGO_TARGET_DIR:-" in text, "an explicit setting must win"


def test_powershell_bootstrap_binds_the_shared_target_dir() -> None:
    script = ROOT / "scripts" / "atlas-toolchain-bootstrap.ps1"
    text = script.read_text(encoding="utf-8")
    assert "$env:CARGO_TARGET_DIR" in text
    assert "if (-not $env:CARGO_TARGET_DIR)" in text, "an explicit setting must win"
