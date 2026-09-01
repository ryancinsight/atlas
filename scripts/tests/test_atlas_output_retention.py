"""Value-semantic tests for the bounded Atlas output retention policy."""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-output-retention.py"
_SPEC = importlib.util.spec_from_file_location("atlas_output_retention", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_retention = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _retention
_SPEC.loader.exec_module(_retention)


def _policy(*, age_days: int = 14, max_bytes: int = 100) -> object:
    return _retention.RetentionPolicy(
        max_age_days=age_days,
        max_bytes=max_bytes,
        ci_queue_report_ring=3,
        declared_experiment_artifacts=(),
    )


def _tree(path: Path, size: int, timestamp: dt.datetime) -> None:
    path.mkdir()
    payload = path / "payload.bin"
    payload.write_bytes(b"x" * size)
    seconds = timestamp.timestamp()
    os.utime(payload, (seconds, seconds))
    os.utime(path, (seconds, seconds))


def test_committed_policy_has_bounded_output_and_report_limits() -> None:
    policy = _retention.load_policy()

    assert policy.max_age_days == 14
    assert policy.max_bytes == 10 * 1024**3
    assert policy.ci_queue_report_ring == 3
    assert policy.declared_experiment_artifacts == ()


def test_age_eviction_removes_an_entire_top_level_unit(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    old = tmp_path / "coeus-derived-artifacts"
    recent = tmp_path / "recent-run"
    _tree(old, 80, now - dt.timedelta(days=15))
    _tree(recent, 80, now - dt.timedelta(days=1))

    plan = _retention.plan_retention(tmp_path, _policy(), now)

    assert [(item.entry.relative.as_posix(), item.reason) for item in plan.evictions] == [
        ("coeus-derived-artifacts", "age")
    ]
    assert plan.projected_bytes == 80


def test_size_eviction_selects_oldest_units_until_budget(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    older = tmp_path / "older"
    newer = tmp_path / "newer"
    _tree(older, 80, now - dt.timedelta(days=2))
    _tree(newer, 80, now - dt.timedelta(days=1))

    plan = _retention.plan_retention(
        tmp_path,
        _policy(age_days=90, max_bytes=100),
        now,
    )

    assert [(item.entry.relative.as_posix(), item.reason) for item in plan.evictions] == [
        ("older", "size")
    ]
    assert plan.projected_bytes == 80


def test_declared_artifact_is_preserved_when_over_budget(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    declared = tmp_path / "experiment-2026-08-01"
    disposable = tmp_path / "disposable"
    _tree(declared, 80, now - dt.timedelta(days=30))
    _tree(disposable, 80, now - dt.timedelta(days=1))
    policy = _retention.RetentionPolicy(
        max_age_days=7,
        max_bytes=100,
        ci_queue_report_ring=3,
        declared_experiment_artifacts=(
            _retention.pathlib.PurePosixPath("experiment-2026-08-01"),
        ),
    )

    plan = _retention.plan_retention(tmp_path, policy, now)

    assert [item.entry.relative.as_posix() for item in plan.evictions] == ["disposable"]
    assert declared.is_dir()
    assert plan.projected_bytes == 80


def test_missing_declared_artifact_blocks_cleanup(tmp_path: Path) -> None:
    policy = _retention.RetentionPolicy(
        max_age_days=14,
        max_bytes=100,
        ci_queue_report_ring=3,
        declared_experiment_artifacts=(
            _retention.pathlib.PurePosixPath("missing-experiment"),
        ),
    )

    with pytest.raises(_retention.RetentionError, match="does not exist"):
        _retention.plan_retention(tmp_path, policy, dt.datetime.now(dt.timezone.utc))


def test_apply_plan_removes_only_planned_derived_units(tmp_path: Path) -> None:
    now = dt.datetime(2026, 9, 1, tzinfo=dt.timezone.utc)
    old = tmp_path / "old"
    keep = tmp_path / "keep"
    _tree(old, 80, now - dt.timedelta(days=15))
    _tree(keep, 80, now - dt.timedelta(days=1))
    plan = _retention.plan_retention(tmp_path, _policy(), now)

    _retention.apply_plan(plan)

    assert not old.exists()
    assert keep.is_dir()
    assert (keep / "payload.bin").read_bytes() == b"x" * 80


def test_reparse_points_are_not_traversed_or_removed(tmp_path: Path) -> None:
    target = tmp_path / "outside"
    target.mkdir()
    (target / "payload.bin").write_bytes(b"x" * 80)
    link = tmp_path / "linked-output"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    plan = _retention.plan_retention(tmp_path, _policy(max_bytes=1), dt.datetime.now(dt.timezone.utc))

    assert plan.evictions == ()
    assert link.is_symlink()
    assert (target / "payload.bin").read_bytes() == b"x" * 80
