#!/usr/bin/env python3
"""Plan and apply the bounded retention policy for Atlas run output.

The policy operates on direct children of ``output/``. Each ordinary child is
one eviction unit, so a build or figure tree is removed as a whole rather
than being left partially valid. Directory size is the sum of regular files;
the age is the newest descendant modification time. Reparse points and other
special filesystem entries are never traversed or removed.

The committed policy is in ``scripts/data/atlas-output-retention.toml``.
Declared experiment artifacts are relative paths in that file. A declaration
protects the path and every ancestor/descendant needed to keep it intact. A
declaration is validated before planning; a stale or malformed declaration is
an error rather than a reason to delete less visibly.

Usage::

    python scripts/atlas-output-retention.py
    python scripts/atlas-output-retention.py --apply

The default is a dry-run. ``--apply`` is required to remove derived output.
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
DEFAULT_ROOT = ATLAS_ROOT / "output"
DEFAULT_POLICY = ATLAS_ROOT / "scripts" / "data" / "atlas-output-retention.toml"
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class RetentionError(RuntimeError):
    """Describe a filesystem or policy violation that blocks cleanup."""


@dataclass(frozen=True)
class RetentionPolicy:
    """Validated limits and declarations loaded from the committed policy."""

    max_age_days: int
    max_bytes: int
    ci_queue_report_ring: int
    declared_experiment_artifacts: tuple[pathlib.PurePosixPath, ...]


@dataclass(frozen=True)
class _TreeSummary:
    bytes: int
    latest_mtime: float
    contains_reparse: bool
    contains_special: bool


@dataclass(frozen=True)
class ScannedEntry:
    """One direct output child and the metadata used by the eviction plan."""

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
    """The complete bounded cleanup decision for one root snapshot."""

    root: pathlib.Path
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
        """Return the root size after all planned evictions."""
        return self.current_bytes - self.evicted_bytes


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RetentionError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RetentionError(f"{field} must be a non-negative integer")
    return value


def _declared_path(value: object) -> pathlib.PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise RetentionError("declared experiment paths must be non-empty strings")
    normalized = value.replace("\\", "/")
    windows_path = pathlib.PureWindowsPath(normalized)
    posix_path = pathlib.PurePosixPath(normalized)
    parts = tuple(part for part in normalized.split("/") if part)
    if (
        windows_path.is_absolute()
        or bool(windows_path.drive)
        or posix_path.is_absolute()
        or not parts
        or any(part in {".", ".."} for part in parts)
    ):
        raise RetentionError(
            f"declared experiment path must be relative without traversal: {value!r}"
        )
    return pathlib.PurePosixPath(*parts)


def load_policy(path: pathlib.Path = DEFAULT_POLICY) -> RetentionPolicy:
    """Load and validate the committed output-retention policy."""
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise RetentionError(f"cannot read retention policy {path}: {exc}") from exc

    output = document.get("output")
    report = document.get("ci_queue_report")
    if not isinstance(output, dict) or not isinstance(report, dict):
        raise RetentionError("policy must define [output] and [ci_queue_report]")
    raw_declarations = output.get("declared_experiment_artifacts", [])
    if not isinstance(raw_declarations, list):
        raise RetentionError("declared_experiment_artifacts must be a TOML array")
    declarations = tuple(_declared_path(item) for item in raw_declarations)
    return RetentionPolicy(
        max_age_days=_positive_int(output.get("max_age_days"), "output.max_age_days"),
        max_bytes=_positive_int(output.get("max_bytes"), "output.max_bytes"),
        ci_queue_report_ring=_nonnegative_int(
            report.get("ring_size"), "ci_queue_report.ring_size"
        ),
        declared_experiment_artifacts=declarations,
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
        raise RetentionError(f"cannot inspect output entry {path}: {exc}") from exc


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
        raise RetentionError(f"cannot enumerate output directory {path}: {exc}") from exc
    with children:
        for child in children:
            child_path = pathlib.Path(child.path)
            child_summary = _scan_tree(child_path)
            total += child_summary.bytes
            latest = max(latest, child_summary.latest_mtime)
            contains_reparse |= child_summary.contains_reparse
            contains_special |= child_summary.contains_special
    return _TreeSummary(total, latest, contains_reparse, contains_special)


def _path_parts(path: pathlib.PurePosixPath) -> tuple[str, ...]:
    parts = path.parts
    return tuple(part.casefold() for part in parts) if os.name == "nt" else parts


def _protects(
    relative: pathlib.PurePosixPath,
    declarations: tuple[pathlib.PurePosixPath, ...],
) -> bool:
    entry_parts = _path_parts(relative)
    for declaration in declarations:
        declaration_parts = _path_parts(declaration)
        if entry_parts[: len(declaration_parts)] == declaration_parts:
            return True
        if declaration_parts[: len(entry_parts)] == entry_parts:
            return True
    return False


def _validate_declarations(root: pathlib.Path, policy: RetentionPolicy) -> None:
    for relative in policy.declared_experiment_artifacts:
        candidate = root
        for index, part in enumerate(relative.parts):
            candidate /= part
            try:
                metadata = os.lstat(candidate)
            except FileNotFoundError as exc:
                raise RetentionError(
                    f"declared experiment artifact does not exist under output: {relative}"
                ) from exc
            except OSError as exc:
                raise RetentionError(
                    f"cannot inspect declared experiment artifact {relative}: {exc}"
                ) from exc
            if _is_reparse(metadata):
                raise RetentionError(
                    f"declared experiment path cannot traverse a reparse point: {relative}"
                )
            if index + 1 < len(relative.parts) and not stat.S_ISDIR(metadata.st_mode):
                raise RetentionError(
                    f"declared experiment path has a non-directory parent: {relative}"
                )


def scan_output(root: pathlib.Path, policy: RetentionPolicy) -> tuple[ScannedEntry, ...]:
    """Scan direct output children without following reparse points."""
    root_metadata = _lstat(root)
    if _is_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise RetentionError(f"output root is not a normal directory: {root}")
    _validate_declarations(root, policy)

    entries: list[ScannedEntry] = []
    try:
        children = os.scandir(root)
    except OSError as exc:
        raise RetentionError(f"cannot enumerate output root {root}: {exc}") from exc
    with children:
        for child in children:
            path = pathlib.Path(child.path)
            relative = pathlib.PurePosixPath(child.name)
            metadata = _lstat(path)
            if _is_reparse(metadata):
                entries.append(
                    ScannedEntry(
                        path,
                        relative,
                        0,
                        metadata.st_mtime,
                        _protects(relative, policy.declared_experiment_artifacts),
                        False,
                        "reparse point",
                    )
                )
                continue
            summary = _scan_tree(path)
            preservation_reason = None
            if summary.contains_reparse:
                preservation_reason = "contains reparse point"
            elif summary.contains_special:
                preservation_reason = "contains special filesystem entry"
            protected = _protects(relative, policy.declared_experiment_artifacts)
            if protected:
                preservation_reason = "declared experiment artifact"
            entries.append(
                ScannedEntry(
                    path,
                    relative,
                    summary.bytes,
                    summary.latest_mtime,
                    protected,
                    preservation_reason is None,
                    preservation_reason,
                )
            )
    return tuple(entries)


def plan_retention(
    root: pathlib.Path,
    policy: RetentionPolicy,
    now: dt.datetime | None = None,
) -> RetentionPlan:
    """Create an age-then-size eviction plan from one output snapshot."""
    current_time = now or dt.datetime.now(dt.timezone.utc)
    if current_time.tzinfo is None:
        raise RetentionError("planning time must include a timezone")
    entries = scan_output(root, policy)
    current_bytes = sum(entry.bytes for entry in entries)
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
    return RetentionPlan(root, entries, current_bytes, evictions, cutoff, policy.max_bytes)


def _remove_entry(entry: ScannedEntry) -> None:
    current = _lstat(entry.path)
    if _is_reparse(current):
        raise RetentionError(f"refusing to remove reparse point {entry.path}")
    if stat.S_ISDIR(current.st_mode):
        summary = _scan_tree(entry.path)
        if summary.contains_reparse or summary.contains_special:
            raise RetentionError(
                f"output entry changed to contain an unsafe child: {entry.path}"
            )
        shutil.rmtree(entry.path)
    elif stat.S_ISREG(current.st_mode):
        entry.path.unlink()
    else:
        raise RetentionError(f"refusing to remove special output entry {entry.path}")


def apply_plan(plan: RetentionPlan) -> None:
    """Apply a previously planned deletion set with reparse checks."""
    for eviction in plan.evictions:
        _remove_entry(eviction.entry)


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
    print(f"root: {plan.root}")
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
    suffix = " (protected/unsafe entries keep the root above budget)" if projected > plan.max_bytes else ""
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
    """Run the retention planner or apply its bounded deletion plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=DEFAULT_ROOT)
    parser.add_argument("--policy", type=pathlib.Path, default=DEFAULT_POLICY)
    parser.add_argument("--apply", action="store_true", help="remove planned derived output")
    parser.add_argument("--now", help="planning time as an ISO-8601 timestamp (test aid)")
    args = parser.parse_args(argv)

    root = pathlib.Path(os.path.abspath(args.root))
    if not os.path.lexists(root):
        print(f"output root does not exist; nothing to evict: {root}")
        return 0
    try:
        policy = load_policy(args.policy)
        plan = plan_retention(root, policy, _parse_now(args.now) if args.now else None)
        _print_plan(plan, args.apply)
        if args.apply:
            apply_plan(plan)
            final_entries = scan_output(root, policy)
            final_bytes = sum(entry.bytes for entry in final_entries)
            print(f"final bytes: {final_bytes} ({_format_bytes(final_bytes)})")
            if final_bytes > policy.max_bytes and not any(
                entry.protected or not entry.removable for entry in final_entries
            ):
                raise RetentionError("retention plan did not reach the configured byte budget")
    except RetentionError as exc:
        print(f"output retention: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
