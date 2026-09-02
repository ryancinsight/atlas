#!/usr/bin/env python3
"""List default-branch workflows whose latest completed run is not green.

Orientation reads own PRs and the board; nothing reads default-branch workflow
verdicts, so atlas's `version-guard` stayed red for eight days (2026-08-25 →
2026-09-02) with no collector (ATLAS-RED-WORKFLOW-COLLECTOR-2026-09-02). This
tool is that collector: one batched `gh run list` per allowlisted repository
(the umbrella plus every registered member) plus its `gh workflow list`, the
latest *completed* run per workflow that still exists, and a row for each
whose conclusion is not success. A cancelled or
skipped latest run is reported too — a merge-gate run that never finished
leaves that merge unverified (engineering_gates: workflow hygiene).

    atlas-red-workflows.py                 # report; exit 0
    atlas-red-workflows.py --fail-on-red   # exit 1 when any row is reported
    atlas-red-workflows.py --first-error   # append the failing step's first error line

`--first-error` costs one `gh run view --log-failed` per red run; the default
report is two calls per repository.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import ROOT, git, registered_members  # noqa: E402

RUN_FIELDS = "databaseId,workflowName,status,conclusion,headSha,createdAt,url,event"
RUN_LIMIT = 80  # covers every workflow's latest completed run on an active repository
GREEN = {"success"}
ERROR_LINE = re.compile(r"(##\[error\]|\berror(\[E\d+\])?:|\bpanicked at\b|FAILED|RATCHET VIOLATION|Process completed with exit code [1-9])")


def slug_of(repo: Path) -> str | None:
    url = (git(repo, "remote", "get-url", "origin") or "").strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?$", url)
    return match.group(1) if match else None


def default_branch_of(repo: Path) -> str:
    head = (git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD") or "").strip()
    return head.split("/", 1)[1] if "/" in head else "main"


def latest_completed_per_workflow(runs: list[dict]) -> dict[str, dict]:
    """`gh run list` is newest-first; keep each workflow's newest completed run."""
    latest: dict[str, dict] = {}
    for run in runs:
        if run.get("status") != "completed":
            continue
        latest.setdefault(run["workflowName"], run)
    return latest


def red_runs(runs: list[dict], active: set[str] | None = None) -> list[dict]:
    """Non-green newest completed runs; with `active`, only workflows that still
    exist on the default branch (`gh run list` keeps runs of deleted workflows,
    whose logs expire and which nothing can ever turn green)."""
    return [
        run for run in latest_completed_per_workflow(runs).values()
        if run.get("conclusion") not in GREEN and (active is None or run["workflowName"] in active)
    ]


def first_error_line(log: str) -> str:
    for line in log.splitlines():
        text = line.split("\t")[-1]
        text = re.sub(r"^\S+Z\s*", "", text)
        if ERROR_LINE.search(text):
            return text.strip()[:200]
    return "(no error line matched)"


def gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], capture_output=True, encoding="utf-8", errors="replace", check=False)


def list_runs(slug: str, branch: str) -> list[dict] | None:
    completed = gh("run", "list", "-R", slug, "--branch", branch, "--limit", str(RUN_LIMIT), "--json", RUN_FIELDS)
    if completed.returncode != 0:
        return None
    return json.loads(completed.stdout or "[]")


def active_workflows(slug: str) -> set[str] | None:
    completed = gh("workflow", "list", "-R", slug, "--json", "name,state", "--limit", "200")
    if completed.returncode != 0:
        return None
    return {w["name"] for w in json.loads(completed.stdout or "[]") if w.get("state") == "active"}


def repositories() -> list[tuple[str, str, str]]:
    """(name, slug, default branch) for the umbrella and every registered member."""
    found: list[tuple[str, str, str]] = []
    umbrella = slug_of(ROOT)
    if umbrella:
        found.append(("atlas", umbrella, default_branch_of(ROOT)))
    for member in registered_members():
        if not (member / ".git").exists():
            continue
        slug = slug_of(member)
        if slug:
            found.append((member.name, slug, default_branch_of(member)))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fail-on-red", action="store_true", help="exit 1 when any workflow is reported")
    parser.add_argument("--first-error", action="store_true", help="fetch each red run's first error line")
    arguments = parser.parse_args()
    reported = 0
    for name, slug, branch in repositories():
        runs = list_runs(slug, branch)
        if runs is None:
            print(f"{name}: gh run list failed for {slug} (access or slug)")
            reported += 1
            continue
        for run in sorted(red_runs(runs, active_workflows(slug)), key=lambda r: r["workflowName"]):
            reported += 1
            line = f"{name}: {run['workflowName']} {run.get('conclusion') or '-'} @ {run['headSha'][:8]} {run['createdAt'][:10]} {run['url']}"
            if arguments.first_error:
                log = gh("run", "view", str(run["databaseId"]), "-R", slug, "--log-failed").stdout
                line += f"\n    {first_error_line(log)}"
            print(line)
    if reported == 0:
        print("every default-branch workflow's latest completed run is green")
    return 1 if reported and arguments.fail_on_red else 0


if __name__ == "__main__":
    raise SystemExit(main())
