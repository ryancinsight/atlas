"""Append-only record of the build-scope claims runs take, rotated at a size bound."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from atlas_build_lock import EXCLUSIVE, _release, _take

CLAIM_LOG = "claims.jsonl"
CLAIM_LOG_BYTES = 1 << 20
_ROTATION_LOCK = "claims.rotate.lock"
# The rotation lock is held for one `stat` and at most one `os.replace`
# (take, stat, replace and release measured 2.7 ms at the median and 21 ms at
# the worst of 50 rounds on the development host with peer gates running).
# A closer waits in steps of 5 ms for four times that worst, as the sharing
# retry does (atlas_build_lock.py): 20 attempts, 100 ms. One that still finds
# the lock held appends without rotating: the record is never the price of a
# rotation, and the next closer rotates.
_ROTATION_ATTEMPTS = 20
_ROTATION_SECONDS = 0.005


def _pause(seconds: float) -> None:
    time.sleep(seconds)


def _rotate(directory: Path, log: Path, limit: int) -> None:
    """Move an over-limit log to `.1`, once however many closers see it over."""
    try:
        if log.stat().st_size < limit:
            return
    except OSError:
        return
    lock = directory / _ROTATION_LOCK
    handle = None
    for attempt in range(_ROTATION_ATTEMPTS):
        handle = _take(lock, EXCLUSIVE)
        if handle is not None:
            break
        if attempt + 1 < _ROTATION_ATTEMPTS:
            _pause(_ROTATION_SECONDS)
    if handle is None:
        return
    try:
        # Checked again under the lock: the closer ahead of this one has
        # rotated, and replacing now would move its fresh log over `.1`.
        if log.stat().st_size >= limit:
            os.replace(log, log.with_name(CLAIM_LOG + ".1"))
    except OSError as error:
        # On Windows a peer holding the log open refuses the replace. The
        # log stays whole and grows past its bound until a later closer
        # rotates it.
        print(f"atlas-build-identity: claim log not rotated at {log}: {error}", file=sys.stderr)
    finally:
        _release(handle, locked=True)


def append_claim(directory: Path, record: dict[str, object], limit: int | None = None) -> None:
    """Append `record` as one line to `directory`'s claim log, rotating it past `limit` bytes.

    A failure to append is reported on stderr and never raised: the record is
    evidence, and the run that closed its claim is not refused for it.
    """
    log = directory / CLAIM_LOG
    line = json.dumps(record, sort_keys=True).encode("utf-8") + b"\n"
    try:
        _rotate(directory, log, CLAIM_LOG_BYTES if limit is None else limit)
        with open(log, "ab") as handle:
            handle.write(line)
    except OSError as error:
        print(f"atlas-build-identity: claim record not written to {log}: {error}", file=sys.stderr)
