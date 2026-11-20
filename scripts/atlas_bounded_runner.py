#!/usr/bin/env python3
"""One committed runner for every agent process: bounded, tagged.

Launches a command through :func:`process_tree.run` with a deadline: at the
deadline the whole process tree (the root and every descendant) is retired, and
the exit reports the limit and the stage. Every run is tagged with its session,
item, command and deadline in the tag store under the shared target's
``.atlas/`` directory, so orientation lists tagged runs and kills those past
their limit.

Callable from bash, pwsh and cmd alike: the command follows ``--`` and is
passed as argv; the exit status is the command's on success or nonzero when a
bound fired (124: deadline; 125: cleanup failure).

Oracle: ``scripts/tests/test_atlas_bounded_runner.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import process_tree  # noqa: E402


def _tag_store() -> Path:
    """The shared target's ``.atlas/`` tag store (one per stack)."""
    return Path(__file__).resolve().parents[1] / "target" / ".atlas" / "bounded-runner"


def _write_tag(store: Path, tag: dict[str, object]) -> None:
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{tag['id']}.json").write_text(
        json.dumps(tag, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atlas-bounded-runner",
        description="Run one command with bounded ownership of its process tree.",
    )
    parser.add_argument(
        "--deadline", type=float, required=True,
        help="seconds before the process tree is retired",
    )
    parser.add_argument("--session", required=True, help="session id tagging the run")
    parser.add_argument("--item", default="", help="item id tagging the run")
    parser.add_argument("--note", default="", help="free-form description of the run")
    parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="command to run after --",
    )
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")

    started = time.time()
    tag = {
        "id": f"{args.session}-{int(started)}",
        "session": args.session,
        "item": args.item,
        "command": command,
        "deadline": args.deadline,
        "started": started,
        "note": args.note,
    }
    _write_tag(_tag_store(), tag)

    try:
        result = process_tree.run(command, timeout=args.deadline)
        return result.returncode or 0
    except process_tree.ProcessTreeTimeout:
        print(
            f"atlas-bounded-runner: stage: deadline: exceeded after "
            f"{args.deadline} s; process tree retired",
            file=sys.stderr,
        )
        return 124
    except process_tree.ProcessTreeCleanupError as exc:
        print(f"atlas-bounded-runner: stage: cleanup: {exc}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    raise SystemExit(main())
