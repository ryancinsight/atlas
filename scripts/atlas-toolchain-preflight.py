"""Assert one compiler identity across the Atlas stack before a sweep.

The shared `CARGO_TARGET_DIR` is usable only when every build routes through
the same rustc identity (AGENTS.md engineering_gates "Supply chain &
toolchain"): a second distribution or an env override silently writes
artifacts no pinned peer can consume, surfacing later as `E0514` on crates
nobody touched. This preflight fails loudly instead:

1. `cargo`/`rustc` on PATH must be rustup shims (no foreign distribution).
2. `RUSTC`/`RUSTDOC` env overrides must be absent.
3. `rustup override list` must be empty (directory overrides bypass pins).
4. For every member with a committed `rust-toolchain.toml`, `rustc -V`
   resolved from inside that member must report the pinned channel.

Exit status is nonzero on the first violated invariant, so CI and the
integration sweep can gate on it. Run: `python scripts/atlas-toolchain-preflight.py`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from atlas_stack import registered_members  # noqa: E402


def fail(message: str) -> None:
    print(f"toolchain preflight: FAIL — {message}")
    raise SystemExit(1)


def rustup_shim_dir() -> Path:
    cargo_home = os.environ.get("CARGO_HOME")
    if cargo_home:
        return Path(cargo_home) / "bin"
    return Path.home() / ".cargo" / "bin"


def check_path_identity() -> None:
    shim_dir = rustup_shim_dir().resolve()
    for tool in ("cargo", "rustc"):
        found = shutil.which(tool)
        if found is None:
            fail(f"`{tool}` is not on PATH")
        resolved = Path(found).resolve().parent
        if resolved != shim_dir:
            fail(
                f"`{tool}` resolves to {found}, not the rustup shim in "
                f"{shim_dir} — a second compiler identity would poison the "
                "shared cache"
            )


def check_env_overrides() -> None:
    for var in ("RUSTC", "RUSTDOC"):
        value = os.environ.get(var)
        if value:
            fail(
                f"{var}={value} is exported — the override substitutes a "
                "compiler behind cargo's back; unset it and let the pins "
                "select the toolchain"
            )


def check_rustup_overrides() -> None:
    result = subprocess.run(
        ["rustup", "override", "list"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        fail(f"`rustup override list` failed: {result.stderr.strip()}")
    listing = result.stdout.strip()
    if listing and "no overrides" not in listing:
        fail(
            "rustup directory overrides are set (they bypass committed "
            f"pins):\n{listing}"
        )


def pinned_channel(manifest: Path) -> str | None:
    text = manifest.read_text(encoding="utf-8")
    match = re.search(r'channel\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def check_member_pins() -> int:
    checked = 0
    for member in registered_members():
        pin = member / "rust-toolchain.toml"
        if not pin.is_file():
            continue
        channel = pinned_channel(pin)
        if channel is None:
            fail(f"{pin} declares no channel")
        result = subprocess.run(
            ["rustc", "-V"], capture_output=True, text=True, check=False, cwd=member
        )
        if result.returncode != 0:
            fail(
                f"`rustc -V` failed under {member.name} (is the pinned "
                f"toolchain {channel} installed?): {result.stderr.strip()}"
            )
        version = result.stdout.strip()
        if channel not in version:
            fail(
                f"{member.name} pins {channel} but resolves `{version}` — "
                "the pin is not what actually runs"
            )
        checked += 1
    if checked == 0:
        fail("no member pins found among registered members")
    return checked


def main() -> int:
    check_path_identity()
    check_env_overrides()
    check_rustup_overrides()
    checked = check_member_pins()
    print(
        f"toolchain preflight: OK — one compiler identity; {checked} member "
        "pins resolve to their declared channels"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
