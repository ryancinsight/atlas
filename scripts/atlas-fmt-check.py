#!/usr/bin/env python3
"""Run `cargo fmt --check` across every stack member.

Why this exists: five separate CI failures on 2026-08-03 (four repos, two
authors) came from the same edit shape -- a module or import rename that
leaves the declaration in the old alphabetical position. `cargo check`,
`clippy`, and `nextest` are all structurally blind to it, because the
reorder is semantically invisible; only rustfmt sees it. Each instance was
found after the push, by CI.

`cargo fmt --check` compiles nothing, so scanning the whole stack costs
seconds. Run it before pushing anything that renames a module, a file, or
an imported symbol:

    python scripts/atlas-fmt-check.py            # every member
    python scripts/atlas-fmt-check.py hephaestus hermes

Exit status is nonzero when any member is unformatted, so CI and the
sweep can gate on it.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS = ROOT / "repos"


def members(selected: list[str]) -> list[pathlib.Path]:
    """Stack members holding a Cargo workspace, in stable order.

    Untracked drops (a private consumer kept out of the stack by
    .gitignore) are skipped: they are not ours to gate.
    """
    found = []
    for path in sorted(REPOS.iterdir()):
        if not (path / "Cargo.toml").is_file():
            continue
        if selected and path.name not in selected:
            continue
        tracked = subprocess.run(
            ["git", "check-ignore", "-q", f"repos/{path.name}"],
            cwd=ROOT,
            capture_output=True,
        )
        if tracked.returncode == 0:
            continue
        found.append(path)
    return found


def unformatted_files(repo: pathlib.Path) -> list[str] | None:
    """Files rustfmt would change, or None when the member cannot be read.

    rustfmt reports `Diff in <path>:<line>:` per hunk; one file usually
    yields several, so the paths are de-duplicated before display.
    """
    try:
        proc = subprocess.run(
            ["cargo", "fmt", "--all", "--check"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"  ! {repo.name}: could not run cargo fmt ({exc})", file=sys.stderr)
        return None
    if proc.returncode == 0:
        return []
    seen = []
    for line in proc.stdout.splitlines():
        if not line.startswith("Diff in "):
            continue
        path = line[len("Diff in "):].rsplit(":", 2)[0]
        # Strip the Windows extended-length prefix rustfmt emits.
        path = path.removeprefix("\\\\?\\")
        try:
            path = str(pathlib.Path(path).relative_to(repo))
        except ValueError:
            pass
        if path not in seen:
            seen.append(path)
    # A nonzero exit with no parseable diff is still a failure; surface it.
    return seen or ["(rustfmt reported changes; see `cargo fmt --all --check`)"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("members", nargs="*", help="limit to these members")
    args = parser.parse_args()

    targets = members(args.members)
    if not targets:
        print("no matching stack members", file=sys.stderr)
        return 2

    offenders = 0
    for repo in targets:
        files = unformatted_files(repo)
        if files is None:
            offenders += 1
            continue
        if files:
            offenders += 1
            print(f"UNFORMATTED  {repo.name}")
            for f in files:
                print(f"               {f}")
        else:
            print(f"ok           {repo.name}")

    if offenders:
        print(
            f"\n{offenders} member(s) unformatted. Fix with `cargo fmt --all` "
            "in each, and commit that separately from behavioural changes.",
            file=sys.stderr,
        )
        return 1
    print(f"\nall {len(targets)} members formatted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
