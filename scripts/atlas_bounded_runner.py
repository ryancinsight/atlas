#!/usr/bin/env python3
"""One committed runner for every agent process: bounded, tagged.

``run`` launches a command through :func:`process_tree.run` with a deadline: at
the deadline the whole process tree is retired and the exit reports the limit
and the stage. Every run is tagged with its session, item, command and deadline
in the tag store under the shared target's ``.atlas/`` directory.

The store is append-only. A run creates ``<stamp>-<pid>.json`` before it
launches and ``<stamp>-<pid>.end.json`` with its outcome when the command ends,
each by exclusive create and never rewritten, so a reader holding a tag open
cannot disturb the runner. The session stays inside the tag, never in a file
name. A run has no end file when its runner died or when retiring its tree
failed (a descendant may survive); ``overdue`` lists such runs once past their
deadline, so orientation finds a run whose runner outlived its limit.

Callable from bash, pwsh and cmd alike: the command follows ``--`` as argv. The
exit status is the command's own on completion, 124 when the deadline retired
the tree and 125 when the runner itself failed, with a ``stage:`` line on
stderr: ``store`` (no tag could be created, so the command did not run),
``cleanup`` (retiring the tree failed; no end file is written) or ``launch``
(the command could not start). An end file that cannot be created is reported
as stage ``store`` and leaves the exit status unchanged. A command that itself
exits 124, 125 or 2 differs from the runner only by the missing ``stage:`` line
and the end file's outcome ``exit``. ``--deadline`` must be finite and greater
than zero.

The tag store is ``.atlas/bounded-runner`` under ``$CARGO_TARGET_DIR`` and, when
the variable is unset, under the shared target beside this checkout's common
Git directory (:func:`atlas_target_dir.shared_target_for`). A tag is visible
as soon as it is created, so a reader may catch one mid-write; ``overdue``
skips it with a warning and lists it on the next call.

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
END_SUFFIX = ".end.json"
# The note process_tree.run adds to an exception when retiring the tree failed too.
CLEANUP_NOTE = "process-tree cleanup failed"


def _seconds(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f"must be finite and greater than zero: {text!r}")
    return value


def tag_store() -> Path:
    """Directory holding the tag files of every run, under the shared target."""
    configured = os.environ.get("CARGO_TARGET_DIR")
    if configured:
        target = Path(configured)
    else:
        target = atlas_target_dir.shared_target_for(Path(__file__).resolve().parents[1])
    return target / ".atlas" / "bounded-runner"


def _create(path: Path, tag: dict[str, object]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(tag, indent=2, sort_keys=True) + "\n")


def _open_tag(store: Path, tag: dict[str, object]) -> Path:
    store.mkdir(parents=True, exist_ok=True)
    stamp = time.time_ns()
    while True:
        path = store / f"{stamp}-{os.getpid()}.json"
        try:
            _create(path, {**tag, "id": path.stem})
        except FileExistsError:
            stamp += 1
        else:
            return path


def _close_tag(opened: Path, outcome: str, **fields: object) -> None:
    end = {"id": opened.stem, "ended": time.time(), "outcome": outcome, **fields}
    try:
        _create(opened.with_suffix(END_SUFFIX), end)
    except OSError as error:
        print(
            f"atlas-bounded-runner: stage: store: could not close {opened.name}: {error!r}",
            file=sys.stderr,
        )


def _survivor_possible(error: BaseException) -> bool:
    return any(CLEANUP_NOTE in note for note in getattr(error, "__notes__", ()))


def _cleanup_fault(error: BaseException) -> int:
    print(f"atlas-bounded-runner: stage: cleanup: {error}", file=sys.stderr)
    return EXIT_RUNNER_FAULT


def overdue_tags(store: Path, now: float) -> list[dict[str, object]]:
    """Tags of runs with no end file whose deadline passed before ``now``.

    Each tag file is read at most once and nothing is written.
    """
    tags = []
    for path in sorted(store.glob("*.json")):
        if path.name.endswith(END_SUFFIX):
            continue
        try:
            tag = json.loads(path.read_text(encoding="utf-8"))
            late = now > tag["started"] + tag["deadline"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"atlas-bounded-runner: skipped {path.name}: {error!r}", file=sys.stderr)
            continue
        if late and not path.with_suffix(END_SUFFIX).exists():
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
        "session": args.session,
        "item": args.item,
        "command": command,
        "deadline": args.deadline,
        "runner_pid": os.getpid(),
        "started": time.time(),
    }
    try:
        opened = _open_tag(tag_store(), tag)
    except (OSError, RuntimeError) as error:
        print(
            f"atlas-bounded-runner: stage: store: could not create the tag, "
            f"the command did not run: {error!r}",
            file=sys.stderr,
        )
        return EXIT_RUNNER_FAULT
    try:
        result = process_tree.run(
            command, timeout=args.deadline, output_mode=process_tree.OutputMode.INHERIT
        )
    except process_tree.ProcessTreeTimeout as error:
        if error.cleanup_error is not None:
            return _cleanup_fault(error)
        _close_tag(opened, "deadline")
        print(
            f"atlas-bounded-runner: stage: deadline: {args.deadline} s exceeded; "
            f"process tree retired ({error})",
            file=sys.stderr,
        )
        return EXIT_DEADLINE
    except process_tree.ProcessTreeCleanupError as error:
        return _cleanup_fault(error)
    except Exception as error:
        notes = "".join(f"\n{note}" for note in getattr(error, "__notes__", ()))
        print(f"atlas-bounded-runner: stage: launch: {error!r}{notes}", file=sys.stderr)
        if not _survivor_possible(error):
            _close_tag(opened, "launch", error=repr(error))
        return EXIT_RUNNER_FAULT
    except BaseException as error:
        if not _survivor_possible(error):
            _close_tag(opened, "interrupted")
        raise
    _close_tag(opened, "exit", returncode=result.returncode)
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
