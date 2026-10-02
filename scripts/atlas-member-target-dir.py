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
root, and outside every member, which matters because ten members carry a
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
    lane_config,
    lane_config_text,
    lane_target_overrides,
    shared_target_for,
)

ATLAS_ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS = ATLAS_ROOT / "repos"
CONFIG = REPOS / ".cargo" / "config.toml"
LANE_CONFIG = lane_config(ATLAS_ROOT)
TEMPLATE = MARKER + """
#
# Cargo resolves `build.target-dir` relative to the workspace root, not to the
# config that declares it, so the stack root's relative `target-dir = "target"`
# only reaches the shared cache for builds rooted at the stack root. Inside a
# member the workspace root is the member, and the same line would resolve to
# that member's own `target/`.
#
# This file sits between every member and the stack root: cargo merges configs
# from the invocation directory upward, so it is closer than the root and
# outside every member -- which matters, because several members carry a
# tracked `.cargo/config.toml` of their own that this must not touch.
#
# Absolute because that is the only value that survives both roots, and
# gitignored because an absolute path is machine-specific. Delete it and
# in-member builds fork the cache again. Regenerate with
# `python scripts/atlas-member-target-dir.py generate`.
[build]
target-dir = "{target}"
"""

def desired(checkout: pathlib.Path = ATLAS_ROOT) -> str:
    return TEMPLATE.format(target=shared_target_for(checkout).as_posix())


def members() -> list[pathlib.Path]:
    """Registered member directories, in name order."""
    if not REPOS.is_dir():
        return []
    return sorted(p for p in REPOS.iterdir() if (p / "Cargo.toml").is_file())


def members_with_own_pin() -> list[str]:
    """Members that declare `target-dir` themselves and so override this file."""
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
    text = io.open(CONFIG, encoding="utf-8").read().replace(chr(13), "")
    if MARKER not in text:
        return "foreign"
    return "current" if text == desired() else "stale"


def lane_state() -> str:
    """Return the state of the config inherited by linked worktree lanes."""
    if lane_target_overrides(ATLAS_ROOT):
        return "override"
    if not LANE_CONFIG.is_file():
        return "missing"
    text = LANE_CONFIG.read_text(encoding="utf-8").replace("\r\n", "\n")
    if MARKER not in text:
        return "foreign"
    return "current" if text == lane_config_text(ATLAS_ROOT) else "stale"


def generate() -> int:
    status = state()
    lane_status = lane_state()
    if status == "foreign" or lane_status in {"foreign", "override"}:
        if lane_status == "override":
            print("error: a lane-local or legacy Cargo config declares target-dir; "
                  "remove the override before generating the shared config")
            return 1
        foreign = LANE_CONFIG if lane_status == "foreign" else CONFIG
        print(f"error: {rel(foreign)} exists and this tool did not write it -- left alone")
        return 1
    if status == "current":
        print(f"current  {rel(CONFIG)}")
    else:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        io.open(CONFIG, "w", encoding="utf-8", newline=chr(10)).write(desired())
        print(f"{status:8s} -> written  {rel(CONFIG)}")
    ensure_lane_config(ATLAS_ROOT)
    if lane_status != "current":
        print(f"{lane_status:8s} -> written  {rel(LANE_CONFIG)}")
    report_exceptions()
    return 0


def check() -> int:
    status = state()
    lane_status = lane_state()
    report_exceptions()
    if status == "current" and lane_status == "current":
        print(f"pinned   {rel(CONFIG)} -> {shared_target_for(ATLAS_ROOT).as_posix()}")
        print(f"pinned   {rel(LANE_CONFIG)} -> {shared_target_for(ATLAS_ROOT).as_posix()}")
        return 0
    print(
        f"{status}/{lane_status}: target config is missing or stale -- "
        "a build would fork the shared cache; "
        "run `generate`"
    )
    return 1


def report_exceptions() -> None:
    own = members_with_own_pin()
    for name in own:
        print(f"note: {name} declares its own target-dir and overrides this file")


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
