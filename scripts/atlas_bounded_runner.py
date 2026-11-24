#!/usr/bin/env python3
"""One committed runner for every agent process: bounded, tagged.

``run`` launches a command through :func:`process_tree.run` with a deadline:
at the deadline the whole process tree (the root and every descendant) is
retired and the exit reports the limit and the stage. Every run is tagged with
its session, item, command and deadline in the tag store under the shared
target's ``.atlas/`` directory, and the tag is closed with the run's outcome
when the run ends, whatever ends it. ``overdue`` lists the tags of runs still
open past their deadline, so orientation finds a run whose runner outlived its
limit. A tag file is named by time and runner pid; the session stays inside it.

Callable from bash, pwsh and cmd alike: the command follows ``--`` and is
passed as argv. The exit status is the command's own on completion, 124 when
the deadline retired the tree and 125 when the runner itself failed (stage
``cleanup``: retiring the tree failed; ``launch``: the command could not start).
``--deadline`` must be finite and greater than zero.

The tag store is ``.atlas/bounded-runner`` under ``$CARGO_TARGET_DIR`` and, when
the variable is unset, under the shared target beside this checkout's common
Git directory (:func:`atlas_target_dir.shared_target_for`).

Oracle: ``scripts/tests/test_atlas_bounded_runner.py``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Sequence

import atlas_target_dir
import process_tree

EXIT_DEADLINE = 124
EXIT_RUNNER_FAULT = 125


def _seconds(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be finite and greater than zero: {text!r}")
    return value


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
        try:
            tag = json.loads(path.read_text(encoding="utf-8"))
            late = "ended" not in tag and now > tag["started"] + tag["deadline"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"atlas-bounded-runner: skipped {path.name}: {error!r}", file=sys.stderr)
            continue
        if late:
            tags.append(tag)
    return tags


def _close(store: Path, tag: dict[str, object], outcome: str, **fields: object) -> None:
    tag.update(ended=time.time(), outcome=outcome, **fields)
    _write_tag(store, tag)


def _run(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("atlas-bounded-runner: a command is required after --", file=sys.stderr)
        return 2
    tag: dict[str, object] = {
        "id": f"{time.time_ns()}-{os.getpid()}",
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
        _close(store, tag, "deadline")
        print(
            f"atlas-bounded-runner: stage: deadline: {args.deadline} s exceeded; "
            f"process tree retired ({error})",
            file=sys.stderr,
        )
        return EXIT_DEADLINE
    except process_tree.ProcessTreeCleanupError as error:
        _close(store, tag, "cleanup")
        print(f"atlas-bounded-runner: stage: cleanup: {error}", file=sys.stderr)
        return EXIT_RUNNER_FAULT
    except Exception as error:
        _close(store, tag, "launch", error=repr(error))
        print(f"atlas-bounded-runner: stage: launch: {error!r}", file=sys.stderr)
        return EXIT_RUNNER_FAULT
    except BaseException:
        _close(store, tag, "interrupted")
        raise
    _close(store, tag, "exit", returncode=result.returncode)
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
        "--deadline", type=_seconds, required=True, help="seconds before the tree is retired"
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
