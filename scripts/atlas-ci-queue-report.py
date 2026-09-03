#!/usr/bin/env python3
"""Per-repository GitHub Actions queue/minutes report for the Atlas fleet.

ATLAS-CI-RUNNER-SATURATION-2026-08-25's measurement instrument. For every
registered member repository it pulls recent workflow runs from the GitHub API
and reports, per repository:

- queue minutes: ``created_at -> run_started_at`` (runner starvation signal),
- run minutes:   ``run_started_at -> updated_at`` (consumed runner minutes),
- event mix:     push / pull_request / schedule / workflow_dispatch,
- conclusion mix,
- the worst queued runs (name, head branch, queue minutes).

The aggregate answers the capacity-vs-load-shedding question with numbers:
which repositories burn the minutes, which events cause them, and how much of
the total is queue delay rather than work.

Usage:
    python scripts/atlas-ci-queue-report.py [--days 7] [--per-repo 200]

Output: a summary table on stdout and a full JSON report under
``output/ci-queue-report/`` (gitignored run-output directory). Authentication
uses ``GH_TOKEN``/``GITHUB_TOKEN``; anonymous mode works for public repos at a
much lower rate limit.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import tomllib
import urllib.error
import urllib.request

FLEET = [
    "ryancinsight/atlas",
    "ryancinsight/CFDrs",
    "ryancinsight/Moirai",
    "ryancinsight/Mnemosyne",
    "ryancinsight/aequitas",
    "ryancinsight/apollo",
    "ryancinsight/asclepius",
    "ryancinsight/athena",
    "ryancinsight/Coeus",
    "ryancinsight/consus",
    "ryancinsight/eunomia",
    "ryancinsight/gaia",
    "ryancinsight/harmonia",
    "ryancinsight/helios",
    "ryancinsight/hephaestus",
    "ryancinsight/hermes",
    "ryancinsight/horae",
    "ryancinsight/hyperion",
    "ryancinsight/iris",
    "ryancinsight/kwavers",
    "ryancinsight/leto",
    "ryancinsight/melinoe",
    "ryancinsight/proteus",
    "ryancinsight/ritk",
    "ryancinsight/themis",
    "ryancinsight/tyche",
]

OUTPUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "output" / "ci-queue-report"
POLICY_PATH = pathlib.Path(__file__).resolve().parent / "data" / "atlas-output-retention.toml"
REPORT_NAME = re.compile(r"^report-(?P<stamp>\d{8}T\d{6}Z)\.json$")


def _token() -> str | None:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def _get(url: str, token: str | None) -> tuple[dict, str]:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response), response.headers.get("X-RateLimit-Remaining", "?")
        except urllib.error.HTTPError as error:
            if error.code in (403, 429) and attempt < 3:
                reset = error.headers.get("X-RateLimit-Reset")
                wait = max(float(reset) - time.time(), 1.0) + 1.0 if reset else 30.0
                print(f"  rate limited; sleeping {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if error.code >= 500 and attempt < 3:
                # Transient gateway failures on the jobs endpoints retry with
                # backoff rather than aborting a whole fleet sweep.
                time.sleep(2**attempt * 2)
                continue
            raise
        except urllib.error.URLError as error:
            if attempt < 3:
                time.sleep(2**attempt)
                continue
            raise
    raise RuntimeError("unreachable")


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _report_ring_size() -> int:
    """Read the shared report-ring size from the committed output policy."""
    document = tomllib.loads(POLICY_PATH.read_text(encoding="utf-8"))
    size = document["ci_queue_report"]["ring_size"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("ci_queue_report.ring_size must be a non-negative integer")
    return size


def prune_report_ring(directory: pathlib.Path, ring_size: int) -> list[pathlib.Path]:
    """Keep the newest report and ``ring_size`` preceding timestamped reports."""
    if ring_size < 0:
        raise ValueError("ring_size must be non-negative")
    reports: list[tuple[dt.datetime, pathlib.Path]] = []
    if not directory.exists():
        return []
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        match = REPORT_NAME.fullmatch(path.name)
        if match:
            stamp = dt.datetime.strptime(match["stamp"], "%Y%m%dT%H%M%SZ").replace(
                tzinfo=dt.timezone.utc
            )
            reports.append((stamp, path))
    reports.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    stale = [path for _, path in reports[ring_size + 1 :]]
    for path in stale:
        path.unlink()
    return stale


def _delete(url: str, token: str) -> None:
    request = urllib.request.Request(url, method="DELETE")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60):
        return


def _list_report_artifacts(repo: str, token: str) -> list[dict]:
    artifacts: list[dict] = []
    for page in range(1, 11):
        payload, _ = _get(
            f"https://api.github.com/repos/{repo}/actions/artifacts?per_page=100&page={page}",
            token,
        )
        batch = payload.get("artifacts", [])
        artifacts.extend(
            artifact
            for artifact in batch
            if artifact.get("name") == "ci-queue-report"
            or artifact.get("name", "").startswith("ci-queue-report-")
        )
        total = payload.get("total_count", 0)
        if len(batch) < 100 or page * 100 >= total:
            return artifacts
    raise RuntimeError("GitHub returned more than 1,000 artifacts; refusing unbounded cleanup")


def prune_remote_artifacts(repo: str, token: str, ring_size: int) -> list[dict]:
    """Delete older CI report artifacts, retaining the latest-plus-ring set."""
    artifacts = _list_report_artifacts(repo, token)
    artifacts.sort(
        key=lambda artifact: (_parse(artifact["created_at"]), int(artifact["id"])),
        reverse=True,
    )
    stale = artifacts[ring_size + 1 :]
    for artifact in stale:
        _delete(
            f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact['id']}",
            token,
        )
    return stale


def collect_runs(repo: str, since: dt.datetime, per_page: int, token: str | None) -> list[dict]:
    # GitHub caps per_page at 100 regardless of the requested value; a larger
    # value silently truncates every page to 100 and the loop below would
    # mistake a full page for the last one.
    page_size = min(per_page, 100)
    runs: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repo}/actions/runs"
            f"?created=>={since.isoformat(timespec='seconds')}&per_page={page_size}&page={page}"
        )
        payload, _ = _get(url, token)
        batch = payload.get("workflow_runs", [])
        runs.extend(batch)
        total = payload.get("total_count", 0)
        if len(batch) < page_size or len(runs) >= total or page >= 40:
            break
        page += 1
    return runs


def summarise(
    repo: str,
    runs: list[dict],
    token: str | None,
    accurate: bool,
    refine_minimum_seconds: float = 1200.0,
    refine_budget: int = 15,
) -> dict:
    """Aggregate one repository's runs into queue and work minutes.

    `accurate` sums job durations rather than trusting run wall time, which
    overcounts a run that hangs after its jobs finish. That costs one API call
    per run, and across the fleet it is thousands of serial round trips — the
    weekly job spent its whole 15-minute budget on them and never wrote a
    report.

    Wall time bounds job-sum from above (jobs run inside the run's span), so
    the amount a refinement can recover from a run is at most that run's wall
    time. The refinement therefore goes to the longest runs first, capped at
    `refine_budget` per repository and skipping runs under
    `refine_minimum_seconds` where there is little to recover. The result
    carries both the refined figure and the all-wall total, so the reader sees
    the bracket the number sits in.
    """
    queue_seconds = 0.0
    wall_seconds = 0.0
    queued_runs = []
    events: dict[str, int] = {}
    conclusions: dict[str, int] = {}
    timed: list[tuple[float, int]] = []
    for run in runs:
        created = _parse(run["created_at"])
        started = run.get("run_started_at")
        updated = _parse(run["updated_at"])
        events[run.get("event", "?")] = events.get(run.get("event", "?"), 0) + 1
        conclusion = run.get("conclusion") or run.get("status", "?")
        conclusions[conclusion] = conclusions.get(conclusion, 0) + 1
        if not started:
            continue
        start = _parse(started)
        q = max((start - created).total_seconds(), 0.0)
        queue_seconds += q
        wall = max((updated - start).total_seconds(), 0.0)
        wall_seconds += wall
        timed.append((wall, run["id"]))
        if q >= 300:
            queued_runs.append(
                {
                    "id": run["id"],
                    "name": run.get("name"),
                    "head_branch": run.get("head_branch"),
                    "event": run.get("event"),
                    "queue_minutes": round(q / 60, 1),
                }
            )
    queued_runs.sort(key=lambda item: item["queue_minutes"], reverse=True)

    work_seconds = wall_seconds
    refined = 0
    if accurate:
        # Longest first: wall time bounds job-sum from above, so a run's wall
        # time is exactly how much a refinement could recover from it.
        for wall, run_id in sorted(timed, reverse=True)[:refine_budget]:
            if wall < refine_minimum_seconds:
                break
            work_seconds += _jobs_work_seconds(repo, run_id, token) - wall
            refined += 1

    return {
        "repository": repo,
        "runs": len(runs),
        "queue_minutes_total": round(queue_seconds / 60, 1),
        "work_minutes_total": round(work_seconds / 60, 1),
        "work_minutes_upper_bound": round(wall_seconds / 60, 1),
        "work_minutes_method": (
            f"job-sum over the {refined} longest run(s), run-wall elsewhere"
            if accurate
            else "run-wall"
        ),
        "runs_refined": refined,
        "events": events,
        "conclusions": conclusions,
        "queued_over_5m": len(queued_runs),
        "worst_queued": queued_runs[:5],
    }


def _jobs_work_seconds(repo: str, run_id: int, token: str | None) -> float:
    total = 0.0
    page = 1
    while True:
        payload, _ = _get(
            f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}",
            token,
        )
        for job in payload.get("jobs", []):
            started = job.get("started_at")
            completed = job.get("completed_at")
            if started and completed:
                total += max(
                    (_parse(completed) - _parse(started)).total_seconds(), 0.0
                )
        if len(payload.get("jobs", [])) < 100 or page >= 10:
            break
        page += 1
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, help="window size in days")
    parser.add_argument("--per-repo", type=int, default=200, help="max runs per repo")
    parser.add_argument(
        "--run-wall",
        action="store_true",
        help="use run wall time instead of summing job durations (faster, overcounts hung runs)",
    )
    parser.add_argument(
        "--refine-budget",
        type=int,
        default=15,
        help="max runs per repository refined by summing job durations",
    )
    parser.add_argument(
        "--refine-minimum-minutes",
        type=float,
        default=20.0,
        help="skip refinement for runs shorter than this; little to recover",
    )
    parser.add_argument(
        "--prune-remote-artifacts",
        action="store_true",
        help="retain the latest CI report artifact plus the configured ring",
    )
    args = parser.parse_args()

    token = _token()
    if args.prune_remote_artifacts:
        repository = os.environ.get("GITHUB_REPOSITORY")
        if not token:
            print("--prune-remote-artifacts requires GH_TOKEN or GITHUB_TOKEN", file=sys.stderr)
            return 2
        if not repository:
            print("--prune-remote-artifacts requires GITHUB_REPOSITORY", file=sys.stderr)
            return 2
        deleted = prune_remote_artifacts(repository, token, _report_ring_size())
        print(f"remote CI report artifacts deleted: {len(deleted)}")
        return 0

    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)

    reports = []
    for repo in FLEET:
        try:
            runs = collect_runs(repo, since, args.per_repo, token)
        except urllib.error.HTTPError as error:
            print(f"{repo}: HTTP {error.code}; skipped", file=sys.stderr)
            continue
        report = summarise(
            repo,
            runs,
            token,
            accurate=not args.run_wall,
            refine_minimum_seconds=args.refine_minimum_minutes * 60,
            refine_budget=args.refine_budget,
        )
        reports.append(report)
        print(
            f"{repo.split('/', 1)[1]:12s} runs={report['runs']:4d} "
            f"queue={report['queue_minutes_total']:8.1f}m "
            f"work={report['work_minutes_total']:8.1f}m "
            f">5m_queue={report['queued_over_5m']:3d} "
            f"refined={report['runs_refined']:3d}",
            flush=True,
        )

    total_q = sum(r["queue_minutes_total"] for r in reports)
    total_w = sum(r["work_minutes_total"] for r in reports)
    by_event: dict[str, int] = {}
    for r in reports:
        for event, count in r["events"].items():
            by_event[event] = by_event.get(event, 0) + count
    print("\n=== fleet totals over {} days ===".format(args.days))
    print(f"runs={sum(r['runs'] for r in reports)} queue_minutes={total_q:.0f} work_minutes={total_w:.0f}")
    print(f"events: {json.dumps(by_event, sort_keys=True)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = OUTPUT_DIR / f"report-{stamp}.json"
    out_path.write_text(json.dumps({"window_days": args.days, "generated": stamp, "repos": reports}, indent=2))
    stale = prune_report_ring(OUTPUT_DIR, _report_ring_size())
    if stale:
        print(f"local CI report files evicted: {len(stale)}")
    print(f"full report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
