#!/usr/bin/env python3
"""Guard: no committed tool writes another repository's refs into the
remote-tracking namespace (ATLAS-ORIGIN-REF-CLOBBER-2026-09-21).

On 2026-09-21 a pin sweep fetched a member's branch with a refspec that
mapped that branch, bare, onto the shared remote-tracking ref of the same
name -- in the recorded incident the member's `main` onto
`refs/remotes/origin/main` -- snapping atlas's shared tracking ref five
times in twenty seconds (17:10:11..17:10:31, restored 17:17:38). Everything
atlas's own reasoning and gates read as "what origin publishes" is that one
shared tracking ref: `origin/main..main`, `main..origin/main`, and every
closer that diff against `origin/main`. A member branch's tip pinned over it
masquerades as atlas's own published state, so the sweep's measured "drift"
was partly a lie the sweep itself had written. The incident refspec, in its
exact literal form, is recorded in the item file
`backlog/atlas-origin-ref-clobber-2026-09-21.md`.

The one sanctioned write is the conformance self-fetch of atlas's *own*
origin (`.github/workflows/atlas-conformance.yml`):

    git fetch --prune --no-tags origin '+refs/heads/*:refs/remotes/origin/*'

a wildcard mirror of the same repository, which is how a tracking ref stays
truthful. Everything else with a remote-tracking destination is the clobber
shape. `scripts/atlas-pin-drift.py` needs no refspec at all: it reads
`ls-remote --symref` for the published tip and fetches into `FETCH_HEAD`,
writing no ref anywhere; a tool that must keep fetched refs writes them under
`refs/scratch/` -- the sanctioned scratch namespace -- never into
`refs/remotes/`.

This guard scans the committed tree (scripts, hooks, workflows, tool
sources) for refspec tokens whose destination is `refs/remotes/`, allowing
only the own-origin wildcard mirror and tag mirrors, and fails on anything
else. The name of the source repository is not load-bearing: the wildcard
mirror is the one benign way to reach the remote-tracking namespace, so the
destination rule alone is the robust discriminator. The unit test drives the
policy directly over a refspec list (any `refs/remotes/` destination from a
non-atlas repository fails), and a scan of this repository's own committed
tooling stays at zero violations.

    python scripts/atlas-refspec-guard.py check                 # working tree
    python scripts/atlas-refspec-guard.py check --root . --rev HEAD
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Refspec tokens as they appear in committed source: an optional force sign,
# a source (left of the colon) that may be a ref, a remote-tracking name, a
# branch, or a generated value, and a destination that names a ref namespace.
# The destination is the write target, which is exactly what the guard
# decides on; the source is captured only for the report.
REFSPEC_TOKEN = re.compile(
    r"([+-]?)([^\s:'\"`]+):(refs/(?:remotes|scratch|tags|heads)/[^\s'\"#`]+)"
)

# Paths a committed tool that runs git actually lives in. Documents, boards,
# ADRs, and item files are evidence and prose -- the wording that *describes*
# the clobber belongs there and is not tooling to gate (the item file
# records the literal incident refspec, which is why the acceptance is scoped
# to committed tooling).
SCOPE_PREFIXES = ("scripts/", ".githooks/", ".github/workflows/", "tools/")
TEXT_SUFFIXES = (".py", ".sh", ".yml", ".yaml", ".rs")


def refspec_outcome(src: str, dst: str) -> str | None:
    """None when `dst` is a sanctioned write target; else a reason string.

    Sanctioned:
    * `refs/scratch/...` -- the scratch namespace a tool keeps fetched refs
      under, never the shared tracking namespace;
    * `+refs/heads/*:refs/remotes/origin/*` -- the own-origin wildcard
      mirror, the only benign way to touch `refs/remotes/`;
    * `refs/tags/...` destinations -- tag mirrors, not remote-tracking state;
    * any other destination (local branch writes, bare refs) -- never the
      shared tracking namespace.

    Everything else under `refs/remotes/` is the clobber shape: a specific
    ref from another repository pinned over a remote-tracking ref, whatever
    repository the refspec names as its source.
    """
    if dst.startswith("refs/scratch/"):
        return None
    if dst == "refs/remotes/origin/*" and src == "refs/heads/*":
        return None
    if dst.startswith("refs/tags/"):
        return None
    if dst.startswith("refs/remotes/"):
        return (
            f"destination {dst} is the remote-tracking namespace; only the "
            "own-origin wildcard mirror `+refs/heads/*:refs/remotes/origin/*` "
            "may write it -- keep fetched member refs under refs/scratch/"
        )
    return None


def tracked_tooling(root: Path) -> list[Path]:
    """The committed tooling files under `root`'s scope prefixes."""
    files: list[Path] = []
    for prefix in SCOPE_PREFIXES:
        base = root / prefix
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in TEXT_SUFFIXES:
                files.append(path)
    return files


def violations_at(root: Path, rev: str | None) -> list[tuple[str, int, str, str]]:
    """(path, line, refspec, reason) for every clobber refspec in scope.

    With a `rev` the scan reads each file from that revision's tree (a
    pre-push hook judges the commit being pushed, never the working tree a
    peer may be editing); without one it walks the working tree so local
    development sees the same verdict the gate would.
    """
    if rev is not None:
        try:
            listing = subprocess.run(
                ["git", "-C", str(root), "ls-tree", "-r", "--name-only", rev],
                capture_output=True, text=True, check=True, encoding="utf-8",
                errors="replace",
            ).stdout
        except subprocess.CalledProcessError:
            return []
        paths = [
            line for line in listing.splitlines()
            if line.startswith(SCOPE_PREFIXES) and line.endswith(TEXT_SUFFIXES)
        ]
        readers: list[tuple[str, str]] = []
        for relpath in paths:
            try:
                text = subprocess.run(
                    ["git", "-C", str(root), "show", f"{rev}:{relpath}"],
                    capture_output=True, text=True, check=True, encoding="utf-8",
                    errors="replace",
                ).stdout
            except subprocess.CalledProcessError:
                continue
            readers.append((relpath, text))
    else:
        readers = []
        for path in tracked_tooling(root):
            readers.append((path.relative_to(root).as_posix(),
                            path.read_text(encoding="utf-8", errors="replace")))

    found: list[tuple[str, int, str, str]] = []
    for relpath, text in readers:
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in REFSPEC_TOKEN.finditer(line):
                sign, src, dst = match.group(1), match.group(2), match.group(3)
                reason = refspec_outcome(src, dst)
                if reason is not None:
                    found.append((relpath, lineno, f"{sign}{src}:{dst}", reason))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("mode", nargs="?", default="check",
                        choices=["check"], help="check scans committed tooling")
    parser.add_argument("--root", type=Path, default=Path.cwd(),
                        help="repository root (default: current directory)")
    parser.add_argument("--rev", metavar="REF",
                        help="scan this revision's tree instead of the working tree")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"no such directory: {root}", file=sys.stderr)
        return 2

    found = violations_at(root, args.rev)
    for relpath, lineno, refspec, reason in found:
        print(f"refspec-guard: FAIL {relpath}:{lineno} `{refspec}` -- {reason}")
    if found:
        sys.stdout.flush()
        print(
            "refspec-guard: a committed tool writes a non-atlas ref into the "
            "remote-tracking namespace. A fetched member ref lands in "
            "refs/scratch/, or is not kept at all (fetch into FETCH_HEAD); "
            "only the own-origin wildcard mirror may touch refs/remotes/.",
            file=sys.stderr,
        )
        return 1
    print("refspec-guard: no committed tool writes a remote-tracking ref "
          "outside the sanctioned own-origin mirror")
    return 0


if __name__ == "__main__":
    sys.exit(main())