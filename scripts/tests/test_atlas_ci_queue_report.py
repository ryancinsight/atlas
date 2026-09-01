#!/usr/bin/env python3
"""Tests for atlas-ci-queue-report.py's run/job accounting.

The instrument exists to separate runner starvation (queue time) from
consumed runner minutes (work time). `summarise` is pure given a list of
workflow-run dicts; only the `accurate` job-duration path touches the
network through `_get`, which this suite stubs.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "atlas-ci-queue-report.py"
_SPEC = importlib.util.spec_from_file_location("atlas_ci_queue_report", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_qr = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _qr
_SPEC.loader.exec_module(_qr)


def _run(rid: int, created: str, started: str | None, updated: str) -> dict:
    run = {
        "id": rid,
        "name": f"run-{rid}",
        "head_branch": "branch",
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "created_at": created,
        "updated_at": updated,
    }
    if started:
        run["run_started_at"] = started
    return run


def test_jobs_work_seconds_sums_across_pages() -> None:
    # The paginator only advances when a page is FULL (100 jobs), so build a
    # full page of one-second jobs plus a short second page.
    full = [
        {"started_at": "2026-08-25T10:00:00Z", "completed_at": "2026-08-25T10:00:01Z"}
        for _ in range(100)
    ]
    page1 = {"jobs": full}
    page2 = {"jobs": [
        {"started_at": "2026-08-25T10:00:00Z", "completed_at": "2026-08-25T10:00:31Z"},
    ]}
    calls = {"n": 0}

    def fake_get(url: str, token):  # noqa: ANN001, ANN201
        calls["n"] += 1
        if "page=2" in url:
            return page2, "5000"
        return page1, "5000"

    with mock.patch.object(_qr, "_get", side_effect=fake_get):
        total = _qr._jobs_work_seconds("ryancinsight/kwavers", 123, None)
    assert total == 100 + 31, total
    # First page fetched, then a second page because page 1 was full.
    assert calls["n"] == 2


def test_jobs_work_seconds_single_page() -> None:
    jobs = {"jobs": [
        {"started_at": "2026-08-25T10:00:00Z", "completed_at": "2026-08-25T10:01:00Z"},
    ]}

    def fake_get(_url, _token):  # noqa: ANN001, ANN202
        return jobs, "5000"

    with mock.patch.object(_qr, "_get", side_effect=fake_get):
        total = _qr._jobs_work_seconds("ryancinsight/x", 1, None)
    assert total == 60


def test_jobs_work_seconds_ignores_incomplete_jobs() -> None:
    # A job without completed_at (still running) contributes nothing.
    jobs = {"jobs": [
        {"started_at": "2026-08-25T10:00:00Z", "completed_at": "2026-08-25T10:01:00Z"},
        {"started_at": "2026-08-25T10:02:00Z", "completed_at": None},
        {"started_at": None, "completed_at": "2026-08-25T10:03:00Z"},
    ]}

    def fake_get(_url, _token):  # noqa: ANN001, ANN202
        return jobs, "5000"

    with mock.patch.object(_qr, "_get", side_effect=fake_get):
        total = _qr._jobs_work_seconds("ryancinsight/x", 1, None)
    assert total == 60


def test_summarise_accurate_uses_job_sum() -> None:
    runs = [
        _run(1, "2026-08-25T10:00:00Z", "2026-08-25T10:05:00Z", "2026-08-25T10:10:00Z"),
    ]

    def fake_get(_url, _token):  # noqa: ANN001, ANN202
        # 120 s of real job work, far less than the 300 s run wall time.
        return {"jobs": [
            {"started_at": "2026-08-25T10:05:00Z", "completed_at": "2026-08-25T10:07:00Z"},
        ]}, "5000"

    with mock.patch.object(_qr, "_get", side_effect=fake_get):
        report = _qr.summarise("ryancinsight/x", runs, None, accurate=True)
    # queue = 05:00 - 10:00 = 300 s = 5.0 min; work = 120 s = 2.0 min.
    assert report["queue_minutes_total"] == 5.0
    assert report["work_minutes_total"] == 2.0
    assert report["work_minutes_method"] == "job-sum"


def test_summarise_run_wall_uses_updated_minus_started() -> None:
    runs = [
        _run(1, "2026-08-25T10:00:00Z", "2026-08-25T10:05:00Z", "2026-08-25T10:10:00Z"),
    ]
    # In wall mode the network is never touched.
    with mock.patch.object(_qr, "_get", side_effect=AssertionError("no network")):
        report = _qr.summarise("ryancinsight/x", runs, None, accurate=False)
    assert report["work_minutes_total"] == 5.0  # 10:10 - 10:05
    assert report["work_minutes_method"] == "run-wall"


def test_summarise_skips_unstarted_runs() -> None:
    runs = [
        _run(1, "2026-08-25T10:00:00Z", None, "2026-08-25T10:30:00Z"),
        _run(2, "2026-08-25T11:00:00Z", "2026-08-25T11:02:00Z", "2026-08-25T11:04:00Z"),
    ]

    def fake_get(_url, _token):  # noqa: ANN001, ANN202
        return {"jobs": [
            {"started_at": "2026-08-25T11:02:00Z", "completed_at": "2026-08-25T11:03:00Z"},
        ]}, "5000"

    with mock.patch.object(_qr, "_get", side_effect=fake_get):
        report = _qr.summarise("ryancinsight/x", runs, None, accurate=True)
    # Only the started run contributes queue/work; runs count stays 2.
    assert report["runs"] == 2
    assert report["queue_minutes_total"] == 2.0
    assert report["work_minutes_total"] == 1.0


def test_worst_queued_reports_top_5_queue_minutes() -> None:
    runs = [
        _run(i, f"2026-08-25T10:{m:02d}:00Z", f"2026-08-25T10:{m+10:02d}:00Z", f"2026-08-25T11:00:00Z")
        for i, m in enumerate([0, 0, 0])  # three runs each queued ~10 min
    ]
    with mock.patch.object(_qr, "_get", return_value=({"jobs": []}, "5000")):
        report = _qr.summarise("ryancinsight/x", runs, None, accurate=True)
    assert report["queued_over_5m"] == 3
    assert len(report["worst_queued"]) == 3
    for item in report["worst_queued"]:
        assert item["queue_minutes"] == round(600 / 60, 1)


def test_prune_report_ring_keeps_latest_plus_configured_ring(tmp_path: Path) -> None:
    stamps = [
        "20260825T205657Z",
        "20260825T210157Z",
        "20260825T223623Z",
        "20260827T165507Z",
        "20260828T165507Z",
    ]
    for stamp in stamps:
        (tmp_path / f"report-{stamp}.json").write_text("{}", encoding="utf-8")
    (tmp_path / "stdout-latest.txt").write_text("summary", encoding="utf-8")

    stale = _qr.prune_report_ring(tmp_path, ring_size=3)

    assert [path.name for path in stale] == ["report-20260825T205657Z.json"]
    assert sorted(path.name for path in tmp_path.glob("report-*.json")) == [
        "report-20260825T210157Z.json",
        "report-20260825T223623Z.json",
        "report-20260827T165507Z.json",
        "report-20260828T165507Z.json",
    ]
    assert (tmp_path / "stdout-latest.txt").read_text(encoding="utf-8") == "summary"


def test_prune_remote_artifacts_keeps_latest_plus_configured_ring() -> None:
    artifacts = [
        {"id": index, "name": "ci-queue-report", "created_at": f"2026-08-{index:02d}T00:00:00Z"}
        for index in range(1, 6)
    ]
    with mock.patch.object(_qr, "_list_report_artifacts", return_value=artifacts):
        with mock.patch.object(_qr, "_delete") as delete:
            stale = _qr.prune_remote_artifacts("ryancinsight/atlas", "token", ring_size=3)

    assert [artifact["id"] for artifact in stale] == [1]
    assert [call.args[0].rsplit("/", 1)[-1] for call in delete.call_args_list] == ["1"]
