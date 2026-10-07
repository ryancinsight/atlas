"""Shared pieces for the root hook tests.

`build_coherence_auditor` builds `tools/gitlink-coherence` once in the
stack's shared cache: the fixture suites reuse the binary instead of
forking a second target directory beside the shared one (the
`target_forks` class) or waiting on a cold build per test.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import tomllib
from pathlib import Path

from atlas_target_dir import shared_target_for

ROOT = Path(__file__).resolve().parents[2]

FIXTURE_PROCESS_TIMEOUT_SECONDS = 600


OVERLAY_BEGIN = "# >>> atlas stack development overlay (generated) >>>"
OVERLAY_END = "# <<< atlas stack development overlay (generated) <<<"


def config_without_overlay(destination: Path) -> Path:
    """The stack's cargo config minus its `[patch]` overlay and its `target-dir`, written to `destination`.

    What stays is the profile budget every build of the stack shares, so a
    build outside the overlay compiles with the same hash-bearing profile keys
    as one inside it and writes no second variant of any dependency into the
    shared cache. `target-dir` goes because cargo resolves it relative to the
    workspace root; the caller passes the shared target explicitly.
    """
    kept: list[str] = []
    inside_overlay = False
    for line in (ROOT / ".cargo" / "config.toml").read_text(encoding="utf-8").splitlines():
        if line == OVERLAY_BEGIN:
            inside_overlay = True
        elif line == OVERLAY_END:
            inside_overlay = False
        elif not inside_overlay and not line.lstrip().startswith("target-dir"):
            kept.append(line)
    destination.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return destination


def shared_target_directory() -> Path:
    """The cache every build of the stack writes: `CARGO_TARGET_DIR`, else the lane tool's `shared_target_for`."""
    configured = os.environ.get("CARGO_TARGET_DIR")
    return Path(configured) if configured else shared_target_for(ROOT)


def build_coherence_auditor() -> Path:
    """The release build of `tools/gitlink-coherence` in the shared cache; returns its binary.

    Cargo reads its config from the working directory upward, never from
    `--manifest-path`, and the stack's own config holds the `[patch]` overlay
    the committed lock does not describe. The build therefore runs from a
    neutral directory, with the shared target, the pinned toolchain and the
    stack's profile keys passed explicitly, so it neither forks the cache nor
    adds a second profile variant to it.
    """
    environment = dict(os.environ, CARGO_TARGET_DIR=str(shared_target_directory()))
    if "RUSTUP_TOOLCHAIN" not in environment:
        # The tool's own pin carries a bare version channel, unlike the root
        # pin whose full host triple (ATLAS-TOOLCHAIN-TRIPLE-083) keeps local
        # cache buckets coherent but cannot resolve on another platform's CI.
        pin = tomllib.loads(
            (ROOT / "tools" / "gitlink-coherence" / "rust-toolchain.toml").read_text(encoding="utf-8")
        )
        environment["RUSTUP_TOOLCHAIN"] = pin["toolchain"]["channel"]
    with tempfile.TemporaryDirectory() as neutral:
        config = config_without_overlay(Path(neutral) / "stack-config.toml")
        subprocess.run(
            ["cargo", "build", "--release", "--locked", "--config", str(config),
             "--manifest-path", str(ROOT / "tools" / "gitlink-coherence" / "Cargo.toml")],
            cwd=neutral, env=environment, check=True, capture_output=True,
            text=True, timeout=FIXTURE_PROCESS_TIMEOUT_SECONDS,
        )
    name = "gitlink-coherence.exe" if os.name == "nt" else "gitlink-coherence"
    return Path(environment["CARGO_TARGET_DIR"]) / "release" / name
