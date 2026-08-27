#!/usr/bin/env python3
"""Apply the apollo-pilot lockfile pre-commit guard to one member repo.

Replicates commit 5602a20d in ryancinsight/apollo ("fix(apollo): Guard the
lockfile at commit rather than only at push"): adds the `check_staged()`
function, the `--check-staged` flag, and the docstring line to a member's
own `scripts/lockfile.py`, preserving that member's line endings so the diff
is exactly the guard and nothing else.

Usage:
    python scripts/apply-lockfile-guard.py repos/<member>

Verifies the result structurally: the produced file must contain
`def check_staged`, the `--check-staged` argument, and must parse as Python.
"""

from __future__ import annotations

import ast
import pathlib
import sys


USAGE_LINES = [
    "    scripts/lockfile.py --check         # verify the committed lock, offline",
    "    scripts/lockfile.py --check-staged  # fast index-only check, for pre-commit",
    "    scripts/lockfile.py --regenerate    # rewrite it correctly (needs network)",
]

CHECK_STAGED = '''def check_staged() -> int:
    """Structural check of the *staged* `Cargo.lock`, for use from `pre-commit`.

    Deliberately does not run cargo. A pre-commit hook has to be fast enough that
    nobody reaches for `--no-verify`, and the flattened lock has an unmistakable
    signature -- zero first-party git sources -- that a text scan settles
    instantly. Staleness, the other failure `--check` detects, needs real
    resolution and stays a pre-push concern.

    Checking the *staged blob* rather than the working file is the point: the
    working copy may already have been repaired while the poisoned version sits
    in the index, and it is the index that becomes the commit.
    """
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", "Cargo.lock"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if staged.returncode != 0 or not staged.stdout.strip():
        return 0

    blob = subprocess.run(
        ["git", "show", ":Cargo.lock"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if blob.returncode != 0:
        return 0

    if len(FIRST_PARTY_SOURCE.findall(blob.stdout)) > 0:
        return 0

    print(
        "error: the staged Cargo.lock contains no first-party git sources.\\n"
        "\\n"
        "A cargo command run against a tree under the Atlas stack root rewrote\\n"
        "it with the overlay active, which resolves those dependencies to local\\n"
        "paths and drops their git sources. Committing it now is what turns a\\n"
        "working branch into one that can never be pushed.\\n"
        "\\n"
        "Fix: scripts/lockfile.py --regenerate, then stage the result.\\n"
        "To commit anyway: SKIP_LOCKFILE_CHECK=1 git commit",
        file=sys.stderr,
    )
    return 1


'''

ARG_BLOCK = '''    mode.add_argument(
        "--check-staged",
        action="store_true",
        help="fast structural check of the staged lock, for pre-commit",
    )'''

DISPATCH = '''    if arguments.regenerate:
        return regenerate()
    if arguments.check_staged:
        return check_staged()
    return check()'''


def apply(lockfile: pathlib.Path) -> bool:
    raw = lockfile.read_bytes()
    crlf = b"\r\n" in raw
    eol = "\r\n" if crlf else "\n"
    text = raw.decode("utf-8")

    if "def check_staged" in text:
        print(f"{lockfile}: already guarded; skipping")
        return False

    # 1. Docstring usage lines: replace the two existing usage lines with three.
    #    Two historical wordings exist across the fleet; accept either.
    new_usage = eol.join(USAGE_LINES) + eol
    replaced = False
    for wording in (
        "# verify the committed lock, offline",
        "# verify the lock with Cargo's locked resolver",
    ):
        old_usage = (
            f"    scripts/lockfile.py --check        {wording}\n"
            "    scripts/lockfile.py --regenerate   # rewrite it correctly (needs network)\n"
        )
        if crlf:
            old_usage = old_usage.replace("\n", "\r\n")
        if old_usage in text:
            text = text.replace(old_usage, new_usage, 1)
            replaced = True
            break
    if not replaced:
        print(f"{lockfile}: unexpected usage lines; refusing to guess", file=sys.stderr)
        return False

    # 2. Insert check_staged() immediately before "def regenerate()".
    marker = "def regenerate() -> int:"
    if marker not in text:
        print(f"{lockfile}: cannot find regenerate()", file=sys.stderr)
        return False
    block = CHECK_STAGED.replace("\n", eol)
    text = text.replace(marker, block + marker, 1)

    # 3. Add the --check-staged argument after the --regenerate argument.
    regen_arg = '    mode.add_argument("--regenerate", action="store_true", help="rewrite the lock correctly")'
    if crlf:
        regen_arg = regen_arg.replace("\n", "\r\n")
    if regen_arg not in text:
        print(f"{lockfile}: unexpected --regenerate argument line", file=sys.stderr)
        return False
    text = text.replace(regen_arg, regen_arg + eol + ARG_BLOCK.replace("\n", eol), 1)

    # 4. Replace the dispatch with the three-way dispatch.
    old_dispatch = "    return regenerate() if arguments.regenerate else check()"
    if old_dispatch not in text:
        print(f"{lockfile}: unexpected dispatch line", file=sys.stderr)
        return False
    text = text.replace(old_dispatch, DISPATCH.replace("\n", eol), 1)

    # Verify: parses and carries the new surface.
    ast.parse(text)
    for needle in ("def check_staged", "--check-staged", "if arguments.check_staged"):
        if needle not in text:
            print(f"{lockfile}: missing {needle!r} after splice", file=sys.stderr)
            return False

    lockfile.write_bytes(text.encode("utf-8"))
    print(f"{lockfile}: guarded ({'CRLF' if crlf else 'LF'})")
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    lockfile = pathlib.Path(sys.argv[1]) / "scripts" / "lockfile.py"
    return 0 if apply(lockfile) else 1


if __name__ == "__main__":
    raise SystemExit(main())
