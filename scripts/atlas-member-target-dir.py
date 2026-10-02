#!/usr/bin/env python3
"""Keep in-member builds on the one shared cache.

The stack root's `.cargo/config.toml` sets `build.target-dir = "target"`, and
its comment claims cargo resolves that "from the parent of `.cargo`". It does
not: cargo resolves `build.target-dir` **relative to the workspace root**. The
line therefore reaches `<stack>/target` only for invocations whose workspace
root is the stack root. Run anything inside `repos/<member>` -- a `cargo fmt`,
a package-scoped `clippy`, a `cargo metadata` -- and the workspace root is the
member, the same line resolves to `repos/<member>/target`, and the shared cache
forks. Nine members had forked this way when the class was first measured, one
of them 1.8 GB, and they regrew within minutes of being swept.

The fix is one file: `repos/.cargo/config.toml`, holding an absolute
`target-dir`. Cargo merges config files from the invocation directory upward,
so this one sits between every member and the stack root -- closer than the
root, and outside every member, which matters because members carry a
*tracked* `.cargo/config.toml` of their own. An absolute path is
machine-specific and must never be committed to a member; this file is
generated and gitignored instead.

    atlas-member-target-dir.py generate   write or refresh it
    atlas-member-target-dir.py check      report whether it is present and current

`check` exits nonzero when the pin is missing or stale, so the conformance scan
and CI can gate on it. A member that declares its own `target-dir` still wins
for itself -- that is cargo's precedence, and `check` reports any such member so
the exception is visible rather than silent.
"""

from __future__ import annotations

import argparse
import io
import pathlib
import sys

from atlas_target_dir import (
    MARKER,
    declares_target_dir,
    ensure_lane_config,
    ensure_member_config,
    generation_refusal,
    lane_config,
    lane_config_text,
    lane_target_overrides,
    member_config,
    member_config_text,
    shared_target_for,
)

ATLAS_ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS = ATLAS_ROOT / "repos"
CONFIG = member_config(ATLAS_ROOT)
LANE_CONFIG = lane_config(ATLAS_ROOT)


def desired(checkout: pathlib.Path | None = None) -> str:
    return member_config_text(ATLAS_ROOT if checkout is None else checkout)


def members() -> list[pathlib.Path]:
    """Registered member directories, in name order."""
    if not REPOS.is_dir():
        return []
    return sorted(p for p in REPOS.iterdir() if (p / "Cargo.toml").is_file())


def members_with_own_pin() -> list[str]:
    """Members that declare an output directory themselves and so override this file."""
    found = []
    for member in members():
        path = member / ".cargo" / "config.toml"
        if not path.is_file():
            continue
        if declares_target_dir(path):
            found.append(member.name)
    return found


def state() -> str:
    """One of: missing, foreign, stale, current."""
    if not CONFIG.is_file():
        return "missing"
    text = io.open(CONFIG, encoding="utf-8", errors="replace").read().replace(chr(13), "")
    if MARKER not in text:
        return "foreign"
    return "current" if text == desired() else "stale"


def lane_state() -> str:
    """Return the state of the config inherited by linked worktree lanes.

    One of: absent (no `worktrees/` yet, so no lane inherits anything),
    missing, foreign, stale, current, override.
    """
    if lane_target_overrides(ATLAS_ROOT):
        return "override"
    if not LANE_CONFIG.is_file():
        return "missing" if LANE_CONFIG.parent.parent.is_dir() else "absent"
    text = LANE_CONFIG.read_text(encoding="utf-8", errors="replace").replace(
        "\r\n", "\n"
    )
    if MARKER not in text:
        return "foreign"
    return "current" if text == lane_config_text(ATLAS_ROOT) else "stale"


def generate() -> int:
    refusal = generation_refusal(ATLAS_ROOT)
    if refusal is not None:
        print(f"error: {refusal}")
        return 1
    status = state()
    lane_status = lane_state()
    ensure_member_config(ATLAS_ROOT)
    if status == "current":
        print(f"current  {rel(CONFIG)}")
    else:
        print(f"{status:8s} -> written  {rel(CONFIG)}")
    ensure_lane_config(ATLAS_ROOT)
    if lane_status != "current":
        print(f"{lane_status:8s} -> written  {rel(LANE_CONFIG)}")
    report_exceptions()
    return 0


ACTIONS = {
    "missing": "run `generate`",
    "stale": "run `generate`",
    "foreign": "move the file aside, then run `generate`",
    "override": "remove the target-dir or build-dir declaration it names",
}


def check() -> int:
    status = state()
    lane_status = lane_state()
    report_exceptions()
    if status == "current" and lane_status in {"current", "absent"}:
        print(f"pinned   {rel(CONFIG)} -> {shared_target_for(ATLAS_ROOT).as_posix()}")
        if lane_status == "current":
            print(f"pinned   {rel(LANE_CONFIG)} -> {shared_target_for(ATLAS_ROOT).as_posix()}")
        return 0
    for label, config, config_status in (
        ("member", CONFIG, status), ("lane", LANE_CONFIG, lane_status),
    ):
        if config_status not in {"current", "absent"}:
            print(f"{label} target config {config_status} ({rel(config)}): "
                  f"{ACTIONS[config_status]}; a build would fork the shared cache")
    if lane_status == "override":
        for path in lane_target_overrides(ATLAS_ROOT):
            print(f"  override: {rel(path)}")
    return 1


def report_exceptions() -> None:
    own = members_with_own_pin()
    for name in own:
        print(f"note: {name} declares its own output directory and overrides this file")


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ATLAS_ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["generate", "check"], nargs="?", default="check")
    args = parser.parse_args()
    try:
        return generate() if args.mode == "generate" else check()
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
