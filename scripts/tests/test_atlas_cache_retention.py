"""Value-semantic tests for the bounded Atlas build-cache retention policy."""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-cache-retention.py"
_SPEC = importlib.util.spec_from_file_location("atlas_cache_retention", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_cache_retention = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _cache_retention
_SPEC.loader.exec_module(_cache_retention)


def _policy(*, age_days: int = 14, max_bytes: int = 100) -> object:
    return _cache_retention.RetentionPolicy(
        max_age_days=age_days,
        max_bytes=max_bytes,
        roots=("target", "target-miri"),
        protected_names=("debug", "release"),
    )


def _tree(path: Path, size: int, timestamp: dt.datetime, base: Path) -> None:
    """Create a populated subtree and backdate it and its ancestors within base.

    Directories created implicitly by ``mkdir(parents=True)`` keep the current
    time otherwise, and creating a child refreshes its parent's mtime — the
    scanner treats both as a recent write, which in production they are. Every
    backdated node lies strictly inside ``base`` (the pytest sandbox).
    """
    seconds = timestamp.timestamp()
    chain = []
    node = path
    while node != base:
        chain.append(node)
        node = node.parent
    path.mkdir(parents=True)
    payload = path / "payload.bin"
    payload.write_bytes(b"x" * size)
    os.utime(payload, (seconds, seconds))
    for created in chain:
        os.utime(created, (seconds, seconds))


def test_committed_policy_has_bounded_limits() -> None:
    policy = _cache_retention.load_policy()

    assert policy.max_age_days == 14
    assert policy.max_bytes == 64 * 1024**3
    assert policy.roots == ("target", "target-miri")
    assert policy.protected_names == ("debug", "release")


def test_age_eviction_removes_stale_incremental_unit_under_protected_profile(
    tmp_path: Path,
) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    stale = tmp_path / "target" / "debug" / "incremental" / "pkg-stale"
    fresh = tmp_path / "target" / "debug" / "incremental" / "pkg-fresh"
    _tree(stale, 80, now - dt.timedelta(days=15), tmp_path)
    _tree(fresh, 80, now - dt.timedelta(days=1), tmp_path)

    plan = _cache_retention.plan_retention(_policy(), now, tmp_path)

    assert [(item.entry.relative.as_posix(), item.reason) for item in plan.evictions] == [
        ("target/debug/incremental/pkg-stale", "age")
    ]
    assert (tmp_path / "target" / "debug").is_dir()
    assert fresh.is_dir()
    assert plan.projected_bytes == 80


def test_protected_container_is_never_evicted_as_a_unit(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    profile = tmp_path / "target" / "debug"
    _tree(profile, 10_000, now - dt.timedelta(days=60), tmp_path)

    plan = _cache_retention.plan_retention(_policy(), now, tmp_path)

    assert plan.evictions == ()
    assert profile.is_dir()


def test_size_eviction_selects_oldest_units_until_budget(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    older = tmp_path / "target" / "debug" / "incremental" / "pkg-old"
    newer = tmp_path / "target" / "debug" / "incremental" / "pkg-new"
    _tree(older, 80, now - dt.timedelta(days=2), tmp_path)
    _tree(newer, 80, now - dt.timedelta(days=1), tmp_path)

    plan = _cache_retention.plan_retention(
        _cache_retention.RetentionPolicy(
            max_age_days=90,
            max_bytes=100,
            roots=("target", "target-miri"),
            protected_names=("debug", "release"),
        ),
        now,
        tmp_path,
    )

    assert [(item.entry.relative.as_posix(), item.reason) for item in plan.evictions] == [
        ("target/debug/incremental/pkg-old", "size")
    ]
    assert plan.projected_bytes == 80


def test_stale_unprotected_container_is_evicted_whole(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    container = tmp_path / "target" / "stale-triple"
    _tree(container / "incremental" / "pkg", 80, now - dt.timedelta(days=30), tmp_path)
    _tree(container / "deps", 20, now - dt.timedelta(days=30), tmp_path)

    plan = _cache_retention.plan_retention(_policy(), now, tmp_path)

    # Unprotected containers are single whole-container units: no interior
    # enumeration, one eviction, exact byte accounting.
    assert [(item.entry.relative.as_posix(), item.reason) for item in plan.evictions] == [
        ("target/stale-triple", "age")
    ]
    assert plan.evicted_bytes == 100
    assert plan.projected_bytes == 0


def test_profile_interiors_are_never_units(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    deps = tmp_path / "target" / "release" / "deps"
    _tree(deps, 10_000, now - dt.timedelta(days=60), tmp_path)

    plan = _cache_retention.plan_retention(_policy(), now, tmp_path)

    assert plan.evictions == ()
    assert deps.is_dir()


def test_missing_root_is_skipped(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    (tmp_path / "target").mkdir()

    plan = _cache_retention.plan_retention(_policy(), now, tmp_path)

    assert plan.entries == ()


def test_apply_plan_removes_only_planned_units(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    stale = tmp_path / "target" / "debug" / "incremental" / "pkg-stale"
    fresh = tmp_path / "target" / "debug" / "incremental" / "pkg-fresh"
    _tree(stale, 80, now - dt.timedelta(days=15), tmp_path)
    _tree(fresh, 80, now - dt.timedelta(days=1), tmp_path)
    plan = _cache_retention.plan_retention(_policy(), now, tmp_path)

    applied, failed = _cache_retention.apply_plan(plan)

    assert (applied, failed) == (1, 0)
    assert not stale.exists()
    assert (fresh / "payload.bin").read_bytes() == b"x" * 80


def test_reparse_points_are_not_traversed_or_removed(tmp_path: Path) -> None:
    root = tmp_path / "target" / "debug" / "incremental"
    root.mkdir(parents=True)
    target = tmp_path / "outside"
    target.mkdir()
    (target / "payload.bin").write_bytes(b"x" * 80)
    link = root / "linked-pkg"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    plan = _cache_retention.plan_retention(
        _policy(), dt.datetime.now(dt.timezone.utc), tmp_path
    )

    assert plan.evictions == ()
    assert link.is_symlink()
    assert (target / "payload.bin").read_bytes() == b"x" * 80


def test_nested_triple_container_is_evicted_whole(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    unit = tmp_path / "target" / "x86_64-pc-windows-msvc" / "debug" / "incremental" / "pkg"
    _tree(unit, 80, now - dt.timedelta(days=30), tmp_path)

    plan = _cache_retention.plan_retention(_policy(), now, tmp_path)

    # The triple container is unprotected, so it is one whole-container unit;
    # its interior is never enumerated separately.
    assert [item.entry.relative.as_posix() for item in plan.evictions] == [
        "target/x86_64-pc-windows-msvc"
    ]
    assert plan.evicted_bytes == 80
