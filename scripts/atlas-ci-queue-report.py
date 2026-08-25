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
import subprocess
import sys
import time
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


def summarise(repo: str, runs: list[dict], token: str | None, accurate: bool) -> dict:
    queue_seconds = 0.0
    work_seconds = 0.0
    queued_runs = []
    events: dict[str, int] = {}
    conclusions: dict[str, int] = {}
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
        if accurate:
            # Run wall time overcounts: a GitHub-side hang after jobs finish
            # (one observed MSRV run sat 24h past its 43s of work) bills none
            # of it, and sequential job gaps bill nothing either. Summing job
            # durations gives consumed runner-minutes.
            work_seconds += _jobs_work_seconds(repo, run["id"], token)
        else:
            work_seconds += max((updated - start).total_seconds(), 0.0)
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
    return {
        "repository": repo,
        "runs": len(runs),
        "queue_minutes_total": round(queue_seconds / 60, 1),
        "work_minutes_total": round(work_seconds / 60, 1),
        "work_minutes_method": "job-sum" if accurate else "run-wall",
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
    args = parser.parse_args()

    token = _token()
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)

    reports = []
    for repo in FLEET:
        try:
            runs = collect_runs(repo, since, args.per_repo, token)
        except urllib.error.HTTPError as error:
            print(f"{repo}: HTTP {error.code}; skipped", file=sys.stderr)
            continue
        report = summarise(repo, runs, token, accurate=not args.run_wall)
        reports.append(report)
        print(
            f"{repo.split('/', 1)[1]:12s} runs={report['runs']:4d} "
            f"queue={report['queue_minutes_total']:8.1f}m "
            f"work={report['work_minutes_total']:8.1f}m "
            f">5m_queue={report['queued_over_5m']:3d}"
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
    print(f"full report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
