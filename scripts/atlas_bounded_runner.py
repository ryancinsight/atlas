#!/usr/bin/env python3
"""One committed runner for every agent process: bounded, tagged.

``run`` launches a command through :func:`process_tree.run` with a deadline:
at the deadline the whole process tree (the root and every descendant) is
retired and the exit reports the limit and the stage. Every run is tagged with
its session, item, command and deadline in the tag store under the shared
target's ``.atlas/`` directory, and the tag is closed with the run's outcome
when the run ends. ``overdue`` lists the tags of runs still open past their
deadline, so orientation finds a run whose runner outlived its limit.

Callable from bash, pwsh and cmd alike: the command follows ``--`` and is
passed as argv. The exit status is the command's own on completion, 124 when
the deadline retired the tree and 125 when retiring the tree failed.

The tag store is ``.atlas/bounded-runner`` under ``$CARGO_TARGET_DIR`` and, when
the variable is unset, under the shared target beside this checkout's common
Git directory (:func:`atlas_target_dir.shared_target_for`).

Oracle: ``scripts/tests/test_atlas_bounded_runner.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Sequence

import atlas_target_dir
import process_tree

EXIT_DEADLINE = 124
EXIT_CLEANUP = 125


def tag_store() -> Path:
    """Directory holding one JSON tag per run, under the shared target."""
    configured = os.environ.get("CARGO_TARGET_DIR")
    if configured:
        target = Path(configured)
    else:
        target = atlas_target_dir.shared_target_for(Path(__file__).resolve().parents[1])
    return target / ".atlas" / "bounded-runner"


def _write_tag(store: Path, tag: dict[str, object]) -> None:
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{tag['id']}.json"
    partial = path.with_suffix(".json.part")
    partial.write_text(json.dumps(tag, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def overdue_tags(store: Path, now: float) -> list[dict[str, object]]:
    """Tags of runs never closed whose deadline passed before ``now``."""
    tags = []
    for path in sorted(store.glob("*.json")):
        tag = json.loads(path.read_text(encoding="utf-8"))
        if "ended" not in tag and now > tag["started"] + tag["deadline"]:
            tags.append(tag)
    return tags


def _run(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("atlas-bounded-runner: a command is required after --", file=sys.stderr)
        return 2
    tag: dict[str, object] = {
        "id": f"{args.session.replace(':', '_')}-{time.time_ns()}-{os.getpid()}",
        "session": args.session,
        "item": args.item,
        "command": command,
        "deadline": args.deadline,
        "runner_pid": os.getpid(),
        "started": time.time(),
    }
    store = tag_store()
    _write_tag(store, tag)
    try:
        result = process_tree.run(
            command, timeout=args.deadline, output_mode=process_tree.OutputMode.INHERIT
        )
    except process_tree.ProcessTreeTimeout as error:
        tag.update(ended=time.time(), outcome="deadline")
        _write_tag(store, tag)
        print(
            f"atlas-bounded-runner: stage: deadline: {args.deadline} s exceeded; "
            f"process tree retired ({error})",
            file=sys.stderr,
        )
        return EXIT_DEADLINE
    except process_tree.ProcessTreeCleanupError as error:
        tag.update(ended=time.time(), outcome="cleanup")
        _write_tag(store, tag)
        print(f"atlas-bounded-runner: stage: cleanup: {error}", file=sys.stderr)
        return EXIT_CLEANUP
    tag.update(ended=time.time(), outcome="exit", returncode=result.returncode)
    _write_tag(store, tag)
    return result.returncode


def _overdue(args: argparse.Namespace) -> int:
    for tag in overdue_tags(tag_store(), time.time()):
        print(json.dumps(tag, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="atlas-bounded-runner",
        description="Run one command with bounded ownership of its process tree.",
    )
    modes = parser.add_subparsers(dest="mode", required=True)
    run = modes.add_parser("run", help="run a command under a deadline")
    run.add_argument(
        "--deadline", type=float, required=True, help="seconds before the tree is retired"
    )
    run.add_argument("--session", required=True, help="agent id tagging the run")
    run.add_argument("--item", default="", help="item id tagging the run")
    run.add_argument("command", nargs=argparse.REMAINDER, help="-- followed by the command")
    run.set_defaults(handler=_run)
    listing = modes.add_parser("overdue", help="list open tags past their deadline")
    listing.set_defaults(handler=_overdue)
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
