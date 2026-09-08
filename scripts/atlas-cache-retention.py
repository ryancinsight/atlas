#!/usr/bin/env python3
"""Plan and apply the bounded retention policy for the shared build cache.

The stack routes every repo through one ``CARGO_TARGET_DIR`` (see
``.cargo/config.toml``), so the shared cache is one unbounded store used by
every member and every lane. Cargo never garbage-collects it: stale
``incremental`` cache generations accumulate per package, and abandoned
target-triple or tool profiles persist until removed by hand.

Eviction units are the direct children of a scan root ("containers": the
cargo profiles and nested target directories) plus the direct children of any
``incremental`` directory within them. Removing one incremental child costs
at most a recompile of that package when cargo next touches its fingerprint;
removing a stale whole container costs a cold rebuild of that target only.
Containers whose name is on the policy's protected list — the live host
profiles — are never evicted as units, but their growth surface is exactly
the incremental children planned underneath them. Directory size is the sum
of regular files; the age is the newest descendant modification time. Reparse
points and other special filesystem entries are never traversed or removed.

Incremental units are collected only beneath protected containers, which are
never evicted themselves, so a plan never lists overlapping units and byte
accounting stays exact: only container bytes enter the budget, and every
evacuation (container or incremental child) subtracts exactly its own size.

The committed policy is in ``scripts/data/atlas-cache-retention.toml``.
Usage::

    python scripts/atlas-cache-retention.py
    python scripts/atlas-cache-retention.py --apply

The default is a dry-run. ``--apply`` is required to remove cached state.

Unlike ``atlas-output-retention.py``, apply tolerates per-unit failures: a
shared live cache is being built by other lanes concurrently, and one locked
directory must not abort the remaining plan.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import shutil
import stat
import sys
import tomllib
from dataclasses import dataclass

ATLAS_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ATLAS_ROOT / "scripts" / "data" / "atlas-cache-retention.toml"
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
# How deep below a container an ``incremental`` directory may sit
# (target/debug/incremental is depth 1; bench-quick/debug/incremental is 2).
MAX_INCREMENTAL_DEPTH = 4


class RetentionError(RuntimeError):
    """Describe a filesystem or policy violation that blocks cleanup."""


@dataclass(frozen=True)
class RetentionPolicy:
    """Validated limits loaded from the committed cache-retention policy."""

    max_age_days: int
    max_bytes: int
    roots: tuple[str, ...]
    protected_names: tuple[str, ...]


@dataclass(frozen=True)
class _TreeSummary:
    bytes: int
    latest_mtime: float
    contains_reparse: bool
    contains_special: bool


@dataclass(frozen=True)
class ScannedEntry:
    """One eviction unit and the metadata used by the eviction plan."""

    path: pathlib.Path
    relative: pathlib.PurePosixPath
    bytes: int
    latest_mtime: float
    protected: bool
    removable: bool
    preservation_reason: str | None


@dataclass(frozen=True)
class Eviction:
    """One planned deletion and the budget that made it eligible."""

    entry: ScannedEntry
    reason: str


@dataclass(frozen=True)
class RetentionPlan:
    """The complete bounded cleanup decision for one roots snapshot."""

    roots: tuple[pathlib.Path, ...]
    entries: tuple[ScannedEntry, ...]
    current_bytes: int
    evictions: tuple[Eviction, ...]
    cutoff: dt.datetime
    max_bytes: int

    @property
    def evicted_bytes(self) -> int:
        """Return the bytes removed by the plan."""
        return sum(item.entry.bytes for item in self.evictions)

    @property
    def projected_bytes(self) -> int:
        """Return the total cache size after all planned evictions."""
        return self.current_bytes - self.evicted_bytes


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RetentionError(f"{field} must be a positive integer")
    return value


def _name_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise RetentionError(f"{field} must be a TOML array of strings")
    if not value:
        raise RetentionError(f"{field} must not be empty")
    return tuple(value)


def load_policy(path: pathlib.Path = DEFAULT_POLICY) -> RetentionPolicy:
    """Load and validate the committed cache-retention policy."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RetentionError(f"cannot read cache-retention policy {path}: {exc}") from exc

    cache = document.get("cache")
    if not isinstance(cache, dict):
        raise RetentionError("policy must define [cache]")
    return RetentionPolicy(
        max_age_days=_positive_int(cache.get("max_age_days"), "cache.max_age_days"),
        max_bytes=_positive_int(cache.get("max_bytes"), "cache.max_bytes"),
        roots=_name_list(cache.get("roots"), "cache.roots"),
        protected_names=_name_list(cache.get("protected_names"), "cache.protected_names"),
    )


def _is_reparse(metadata: os.stat_result) -> bool:
    """Return whether metadata identifies a link or Windows reparse point."""
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & REPARSE_POINT
    )


def _lstat(path: pathlib.Path) -> os.stat_result:
    try:
        return os.lstat(path)
    except OSError as exc:
        raise RetentionError(f"cannot inspect cache entry {path}: {exc}") from exc


def _scan_tree(path: pathlib.Path) -> _TreeSummary:
    metadata = _lstat(path)
    if _is_reparse(metadata):
        return _TreeSummary(0, metadata.st_mtime, True, False)
    if stat.S_ISREG(metadata.st_mode):
        return _TreeSummary(metadata.st_size, metadata.st_mtime, False, False)
    if not stat.S_ISDIR(metadata.st_mode):
        return _TreeSummary(0, metadata.st_mtime, False, True)

    total = 0
    latest = metadata.st_mtime
    contains_reparse = False
    contains_special = False
    try:
        children = os.scandir(path)
    except OSError as exc:
        raise RetentionError(f"cannot enumerate cache directory {path}: {exc}") from exc
    with children:
        for child in children:
            child_path = pathlib.Path(child.path)
            child_summary = _scan_tree(child_path)
            total += child_summary.bytes
            latest = max(latest, child_summary.latest_mtime)
            contains_reparse |= child_summary.contains_reparse
            contains_special |= child_summary.contains_special
    return _TreeSummary(total, latest, contains_reparse, contains_special)


def _is_protected(relative: pathlib.PurePosixPath, policy: RetentionPolicy) -> bool:
    """Return whether a container name is protected (case-insensitively on Windows)."""
    name = relative.name
    return any(
        name.casefold() == protected.casefold() for protected in policy.protected_names
    )


def _container_entry(
    path: pathlib.Path, base: pathlib.Path, policy: RetentionPolicy
) -> ScannedEntry:
    """Build the scan entry for one level-1 container."""
    root_name = path.relative_to(base).parts[0]
    relative = path.relative_to(base).as_posix()
    metadata = _lstat(path)
    protected = _is_protected(pathlib.PurePosixPath(relative), policy)
    if _is_reparse(metadata):
        return ScannedEntry(
            path, pathlib.PurePosixPath(relative), 0, metadata.st_mtime, protected,
            False, "reparse point",
        )
    summary = _scan_tree(path)
    preservation_reason: str | None = None
    if summary.contains_reparse:
        preservation_reason = "contains reparse point"
    elif summary.contains_special:
        preservation_reason = "contains special filesystem entry"
    elif protected:
        preservation_reason = f"protected container ({root_name} host profile)"
    removable = preservation_reason is None and not protected
    return ScannedEntry(
        path,
        pathlib.PurePosixPath(relative),
        summary.bytes,
        summary.latest_mtime,
        protected,
        removable,
        preservation_reason,
    )


def _incremental_units(
    container: pathlib.Path, base: pathlib.Path, policy: RetentionPolicy
) -> list[ScannedEntry]:
    """Collect the children of every ``incremental`` directory below a container.

    Only called for protected containers (which are never evicted themselves),
    so the units collected here are disjoint from whole-container units.
    """
    units: list[ScannedEntry] = []

    def walk(directory: pathlib.Path, depth: int) -> None:
        if depth > MAX_INCREMENTAL_DEPTH:
            return
        try:
            children = list(os.scandir(directory))
        except OSError:
            return
        for child in children:
            child_path = pathlib.Path(child.path)
            try:
                metadata = child.stat(follow_symlinks=False)
            except OSError:
                continue
            if _is_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
                continue
            if child.name == "incremental":
                prefix = child_path.relative_to(base).as_posix()
                try:
                    inner = list(os.scandir(child_path))
                except OSError:
                    continue
                for pkg in inner:
                    pkg_path = pathlib.Path(pkg.path)
                    units.append(_unit_entry(pkg_path, prefix))
            else:
                walk(child_path, depth + 1)

    walk(container, 1)
    return units


def _unit_entry(path: pathlib.Path, prefix: str) -> ScannedEntry:
    """Build the scan entry for one incremental package-cache unit."""
    relative = pathlib.PurePosixPath(prefix, path.name)
    try:
        metadata = _lstat(path)
    except OSError as exc:
        raise RetentionError(f"cannot inspect cache unit {path}: {exc}") from exc
    if _is_reparse(metadata):
        return ScannedEntry(path, relative, 0, metadata.st_mtime, False, False, "reparse point")
    summary = _scan_tree(path)
    preservation_reason: str | None = None
    if summary.contains_reparse:
        preservation_reason = "contains reparse point"
    elif summary.contains_special:
        preservation_reason = "contains special filesystem entry"
    return ScannedEntry(
        path,
        relative,
        summary.bytes,
        summary.latest_mtime,
        False,
        preservation_reason is None,
        preservation_reason,
    )


def scan_roots(
    policy: RetentionPolicy, base: pathlib.Path = ATLAS_ROOT
) -> tuple[ScannedEntry, ...]:
    """Scan every configured root under ``base`` without following reparse points."""
    entries: list[ScannedEntry] = []
    for root_name in policy.roots:
        root = base / root_name
        if not os.path.lexists(root):
            continue
        try:
            root_metadata = _lstat(root)
        except FileNotFoundError:
            continue
        if _is_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
            raise RetentionError(f"cache root is not a normal directory: {root}")
        try:
            children = list(os.scandir(root))
        except OSError as exc:
            raise RetentionError(f"cannot enumerate cache root {root}: {exc}") from exc
        for child in children:
            child_path = pathlib.Path(child.path)
            if not child.is_dir(follow_symlinks=False):
                continue
            container = _container_entry(child_path, base, policy)
            entries.append(container)
            if container.protected:
                # Protected containers are never evicted, so their only
                # reclaimable space is their per-package incremental caches;
                # collecting units here keeps plans disjoint from the
                # whole-container units collected for unprotected names.
                entries.extend(_incremental_units(child_path, base, policy))
    return tuple(entries)


def plan_retention(
    policy: RetentionPolicy,
    now: dt.datetime | None = None,
    base: pathlib.Path = ATLAS_ROOT,
) -> RetentionPlan:
    """Create an age-then-size eviction plan from one cache snapshot."""
    current_time = now or dt.datetime.now(dt.timezone.utc)
    if current_time.tzinfo is None:
        raise RetentionError("planning time must include a timezone")
    entries = scan_roots(policy, base)
    # Containers partition the cache: every byte belongs to exactly one
    # container, and units (collected only under protected containers) live
    # inside their container's count. Sizing on containers alone therefore
    # counts each byte once.
    current_bytes = sum(
        entry.bytes for entry in entries if len(entry.relative.parts) == 2
    )
    cutoff = current_time - dt.timedelta(days=policy.max_age_days)

    reasons: dict[pathlib.Path, str] = {}
    for entry in entries:
        if (
            entry.removable
            and not entry.protected
            and dt.datetime.fromtimestamp(entry.latest_mtime, dt.timezone.utc) <= cutoff
        ):
            reasons[entry.path] = "age"

    remaining = current_bytes - sum(
        entry.bytes for entry in entries if entry.path in reasons
    )
    if remaining > policy.max_bytes:
        candidates = sorted(
            (
                entry
                for entry in entries
                if entry.removable
                and not entry.protected
                and entry.path not in reasons
            ),
            key=lambda entry: (entry.latest_mtime, entry.relative.as_posix()),
        )
        for entry in candidates:
            reasons[entry.path] = "size"
            remaining -= entry.bytes
            if remaining <= policy.max_bytes:
                break

    evictions = tuple(
        Eviction(entry, reasons[entry.path])
        for entry in sorted(entries, key=lambda item: (item.latest_mtime, item.relative.as_posix()))
        if entry.path in reasons
    )
    return RetentionPlan(
        tuple(base / name for name in policy.roots),
        entries,
        current_bytes,
        evictions,
        cutoff,
        policy.max_bytes,
    )


def _remove_entry(entry: ScannedEntry) -> None:
    current = _lstat(entry.path)
    if _is_reparse(current):
        raise RetentionError(f"refusing to remove reparse point {entry.path}")
    if stat.S_ISDIR(current.st_mode):
        summary = _scan_tree(entry.path)
        if summary.contains_reparse or summary.contains_special:
            raise RetentionError(
                f"cache unit changed to contain an unsafe child: {entry.path}"
            )
        shutil.rmtree(entry.path)
    elif stat.S_ISREG(current.st_mode):
        entry.path.unlink()
    else:
        raise RetentionError(f"refusing to remove special cache entry {entry.path}")


def apply_plan(plan: RetentionPlan) -> tuple[int, int]:
    """Apply the planned deletions; return (applied, failed) unit counts.

    Failures are tolerated per unit: the shared cache is live for other
    lanes, and one locked directory must not abort the remaining plan.
    """
    applied = 0
    failed = 0
    for eviction in plan.evictions:
        try:
            _remove_entry(eviction.entry)
            applied += 1
        except (OSError, RetentionError) as exc:
            failed += 1
            print(f"  failed: {eviction.entry.relative.as_posix()}: {exc}")
    return applied, failed


def _format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def _print_plan(plan: RetentionPlan, apply: bool) -> None:
    action = "apply" if apply else "dry-run"
    print(f"action: {action}")
    print(f"current bytes: {plan.current_bytes} ({_format_bytes(plan.current_bytes)})")
    print(f"max bytes: {plan.max_bytes} ({_format_bytes(plan.max_bytes)})")
    print(f"age cutoff: {plan.cutoff.isoformat()}")
    print(f"planned evictions: {len(plan.evictions)} ({_format_bytes(plan.evicted_bytes)})")
    for eviction in plan.evictions:
        print(
            f"  {eviction.reason:4s} {_format_bytes(eviction.entry.bytes):>12s} "
            f"{eviction.entry.relative.as_posix()}"
        )
    preserved = [entry for entry in plan.entries if not entry.removable or entry.protected]
    for entry in preserved:
        reason = entry.preservation_reason or "protected"
        print(f"  keep {reason:28s} {entry.relative.as_posix()}")
    projected = plan.projected_bytes
    suffix = (
        " (protected/unsafe entries keep the cache above budget)"
        if projected > plan.max_bytes
        else ""
    )
    print(f"projected bytes: {projected} ({_format_bytes(projected)}){suffix}")


def _parse_now(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RetentionError(f"--now must be an ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise RetentionError("--now must include a timezone")
    return parsed


def main(argv: list[str] | None = None) -> int:
    """Run the cache retention planner or apply its bounded deletion plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=pathlib.Path, default=DEFAULT_POLICY)
    parser.add_argument("--apply", action="store_true", help="remove planned cached state")
    parser.add_argument("--now", help="planning time as an ISO-8601 timestamp (test aid)")
    args = parser.parse_args(argv)

    try:
        policy = load_policy(args.policy)
        plan = plan_retention(policy, _parse_now(args.now) if args.now else None)
        _print_plan(plan, args.apply)
        if args.apply:
            applied, failed = apply_plan(plan)
            print(f"applied: {applied} evictions, {failed} failed")
            if failed:
                print("cache retention: some units could not be removed", file=sys.stderr)
                return 2
            if plan.projected_bytes > plan.max_bytes:
                print(
                    "cache retention: plan did not reach the configured byte budget",
                    file=sys.stderr,
                )
                return 2
    except RetentionError as exc:
        print(f"cache retention: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
