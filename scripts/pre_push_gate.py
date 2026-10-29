#!/usr/bin/env python3
"""Own the complete pre-push or documentation process tree and wall bound."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import process_tree

DEADLINE_SECONDS = 600
LOG_TAIL_BYTES = 32768


def _emit(value: bytes | None, stream) -> None:
    if value:
        stream.buffer.write(value)
        stream.flush()


def _progress_report(progress: Path) -> None:
    marker = progress / "stages.log"
    if marker.is_file():
        print("pre-push: bounded stage timings:", file=sys.stderr)
        print(
            marker.read_text(encoding="utf-8", errors="replace"),
            end="",
            file=sys.stderr,
        )


def main() -> int:
    if len(sys.argv) < 4:
        print("pre-push: BLOCKED -- malformed process-tree bootstrap", file=sys.stderr)
        return 2
    entry_kind, phase, hook, *arguments = sys.argv[1:]
    if entry_kind not in {"direct", "shim"}:
        print(
            f"pre-push: BLOCKED -- invalid bounded entry kind {entry_kind}",
            file=sys.stderr,
        )
        return 2
    if phase not in {"push", "documentation"}:
        print(f"pre-push: BLOCKED -- invalid bounded phase {phase}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="pg-progress.") as temporary:
        progress = Path(temporary)
        os.environ["ATLAS_GATE_PROGRESS_DIR"] = str(progress)
        if entry_kind == "shim":
            os.environ["ATLAS_GATE_BOUNDED"] = "1"
            command = ["bash", hook, "--atlas-shim-bounded", *arguments]
        else:
            command = ["bash", hook, "--bounded-entry", *arguments]
        try:
            # Inherit the native environment block. Rebuilding it from
            # os.environ on Windows uppercases caller variable and exported
            # function names, changing the hook's input contract.
            result = process_tree.run(
                command,
                timeout=DEADLINE_SECONDS,
            )
        except process_tree.ProcessTreeTimeout as error:
            _emit(error.output, sys.stdout)
            _emit(error.stderr, sys.stderr)
            _progress_report(progress)
            log = progress / "gate.log"
            if log.is_file():
                print("pre-push: final bounded gate log bytes:", file=sys.stderr)
                _emit(log.read_bytes()[-LOG_TAIL_BYTES:], sys.stderr)
            print(
                f"pre-push: BLOCKED -- {phase} phase exceeded "
                f"{DEADLINE_SECONDS} seconds; its process tree was retired",
                file=sys.stderr,
            )
            return 124
        except process_tree.ProcessTreeCleanupError as error:
            print(
                f"pre-push: BLOCKED -- {phase} phase cleanup failed: {error}",
                file=sys.stderr,
            )
            return 1
        _emit(result.stdout, sys.stdout)
        _emit(result.stderr, sys.stderr)
        _progress_report(progress)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
