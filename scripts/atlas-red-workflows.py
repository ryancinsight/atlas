#!/usr/bin/env python3
"""List default-branch workflows whose latest completed run is not green.

Orientation reads own PRs and the board; nothing reads default-branch workflow
verdicts, so atlas's `version-guard` stayed red for eight days (2026-08-25 →
2026-09-02) with no collector (ATLAS-RED-WORKFLOW-COLLECTOR-2026-09-02). This
tool is that collector: for every active workflow of every allowlisted
repository (the umbrella plus each registered member) it asks for that
workflow's newest *completed* run on the default branch and reports the ones
that are not green. A cancelled or skipped latest run is reported too — a
merge-gate run that never finished leaves that merge unverified
(engineering_gates: workflow hygiene).

The query is per workflow rather than one batched page of recent runs,
because a fixed page makes the report depend on how busy the repository is:
the same pass reported a three-week-old apollo failure that its own run list
contradicted, and moirai rows appeared and vanished between two runs minutes
apart as the page slid over them.

    atlas-red-workflows.py                 # report; exit 0
    atlas-red-workflows.py --fail-on-red   # exit 1 when any row is reported
    atlas-red-workflows.py --first-error   # append the failing step's first error line

Each row carries the trigger that produced it, because a red row is only a
verdict on the code when a merge produced it: a manual dispatch and a
scheduled run are their own events. A cancelled run additionally reports
whether a runner ever took it — a run no runner accepted (queued until
GitHub cancelled it, the state kwavers's GPU parity job is designed to sit
in without a registered CUDA runner) is starved infrastructure, not a
defect in the tree, and reading it as a defect is how a daily red teaches
the eye to skip the list.

`--first-error` costs one `gh run view --log-failed` per red run, and a
cancelled row costs one `gh api .../jobs`; the default report is one
`gh workflow list` per repository plus one `gh run list` per active
workflow.
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
GREEN = {"success"}
# GitHub's own Pages build workflow; it supersedes itself on every deploy and
# nothing in the repository configures it, so its cancelled runs carry no signal.
PLATFORM_WORKFLOWS = {"pages-build-deployment"}
ERROR_LINE = re.compile(r"(##\[error\]|\berror(\[E\d+\])?:|\bpanicked at\b|FAILED|RATCHET VIOLATION|Process completed with exit code [1-9])")


def slug_of(repo: Path) -> str | None:
    url = (git(repo, "remote", "get-url", "origin") or "").strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?$", url)
    return match.group(1) if match else None


def default_branch_of(repo: Path) -> str:
    head = (git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD") or "").strip()
    return head.split("/", 1)[1] if "/" in head else "main"


def latest_completed_per_workflow(runs: list[dict]) -> dict[str, dict]:
    """Keep each workflow's newest completed run.

    `gh run list` is documented newest-first, but on 2026-09-02 two passes
    (coeus, apollo) surfaced an August run ahead of the same day's; the
    selection sorts by `createdAt` itself rather than trust the list order.
    """
    latest: dict[str, dict] = {}
    for run in sorted(runs, key=lambda r: r.get("createdAt", ""), reverse=True):
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
        if run.get("conclusion") not in GREEN
        and run["workflowName"] not in PLATFORM_WORKFLOWS
        and (active is None or run["workflowName"] in active)
    ]


# A merge's own verdict. Every other trigger is someone or something else
# asking for a run, so its failure says nothing about the default branch.
MERGE_EVENTS = {"push", "merge_group"}


def trigger_note(run: dict) -> str:
    """How the run was triggered, when that is not a merge of the branch."""
    event = run.get("event")
    if event in MERGE_EVENTS or not event:
        return ""
    return {"workflow_dispatch": " (manual dispatch)",
            "schedule": " (scheduled)",
            "pull_request": " (pull request)"}.get(event, f" ({event})")


def no_runner_accepted(jobs: list[dict]) -> bool:
    """True when no job of the run was ever assigned a runner.

    `started_at` cannot decide this: GitHub stamps a queued job with its
    queue time and cancels it exactly 24 hours later, so kwavers's GPU
    parity job reports a start and a completion a day apart having never
    run. The runner assignment is the direct evidence — an empty
    `runner_name` on every job means the labels the workflow asks for
    (`self-hosted, linux, x64, cuda`) match no registered runner.
    """
    return bool(jobs) and all(not (job.get("runner_name") or "").strip() for job in jobs)


def first_error_line(log: str) -> str:
    for line in log.splitlines():
        text = line.split("\t")[-1]
        text = re.sub(r"^\S+Z\s*", "", text)
        if ERROR_LINE.search(text):
            return text.strip()[:200]
    return "(no error line matched)"


def gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], capture_output=True, encoding="utf-8", errors="replace", check=False)


def latest_completed_run(slug: str, branch: str, workflow: str | int) -> dict | None:
    """The newest completed run of one workflow on `branch`, or None.

    The window is a few runs rather than one so a cancelled row can say
    whether something newer already exists: GitHub's own CodeQL setup
    supersedes its runs, so its newest *completed* run is routinely a
    cancellation with a success behind it and a fresh run ahead of it.
    """
    completed = gh("run", "list", "-R", slug, "--workflow", str(workflow), "--branch", branch,
                   "--limit", "5", "--json", RUN_FIELDS)
    if completed.returncode != 0:
        return None
    runs = sorted(json.loads(completed.stdout or "[]"),
                  key=lambda r: r.get("createdAt", ""), reverse=True)
    for index, run in enumerate(runs):
        if run.get("status") == "completed":
            run = dict(run)
            run["_superseded"] = index > 0
            return run
    return None


def active_workflows(slug: str) -> list[dict] | None:
    """Active workflows as `{name, id, path}`; `gh run list` keeps runs of
    deleted workflows, whose logs expire and which nothing can turn green."""
    completed = gh("workflow", "list", "-R", slug, "--json", "name,state,id,path", "--limit", "200")
    if completed.returncode != 0:
        return None
    return [w for w in json.loads(completed.stdout or "[]") if w.get("state") == "active"]


def only_trigger_is_workflow_call(text: str) -> bool:
    """True when the workflow's only trigger is `workflow_call`.

    Such a workflow never runs on the default branch by itself, so its newest
    run there can never be superseded: atlas's `semver-gate.yml` still
    reports the phantom failure GitHub recorded while the file carried two
    `name:` keys, long after the parse error was fixed.
    """
    # `(?m)` only: with DOTALL, `.` swallows newlines and the block runs to
    # the end of the file, so `permissions:` reads as a second trigger.
    block = re.search(r"(?m)^on:[ \t]*\n((?:(?:[ \t]+\S.*|[ \t]*)\n)*)", text)
    if not block:
        return False
    return re.findall(r"(?m)^  ([a-z_]+):", block.group(1)) == ["workflow_call"]


def repository_runs(slug: str, branch: str, repo: Path | None = None) -> list[dict] | None:
    """Each active workflow's newest completed run on the default branch."""
    workflows = active_workflows(slug)
    if workflows is None:
        return None
    runs = []
    for workflow in workflows:
        if workflow["name"] in PLATFORM_WORKFLOWS:
            continue
        path = workflow.get("path")
        if repo is not None and path:
            if only_trigger_is_workflow_call(git(repo, "show", f"origin/{branch}:{path}") or ""):
                continue
        run = latest_completed_run(slug, branch, workflow["id"])
        if run is not None:
            runs.append(run)
    return runs


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
    repo_paths = {member.name: member for member in registered_members()}
    repo_paths['atlas'] = ROOT
    for name, slug, branch in repositories():
        runs = repository_runs(slug, branch, repo_paths.get(name))
        if runs is None:
            print(f"{name}: gh workflow list failed for {slug} (access or slug)")
            reported += 1
            continue
        for run in sorted(red_runs(runs), key=lambda r: r["workflowName"]):
            reported += 1
            line = (f"{name}: {run['workflowName']} {run.get('conclusion') or '-'}"
                    f"{trigger_note(run)} @ {run['headSha'][:8]} {run['createdAt'][:10]} {run['url']}")
            if run.get("conclusion") == "cancelled":
                jobs = gh("api", f"repos/{slug}/actions/runs/{run['databaseId']}/jobs",
                          "--jq", ".jobs")
                try:
                    parsed = json.loads(jobs.stdout or "[]")
                except json.JSONDecodeError:
                    parsed = []
                if no_runner_accepted(parsed):
                    line += ("\n    no runner accepted it: queued, then cancelled"
                             " — starved infrastructure, not a defect in the tree")
                elif run.get("_superseded"):
                    line += "\n    superseded: a newer run of this workflow already exists"
            if arguments.first_error:
                log = gh("run", "view", str(run["databaseId"]), "-R", slug, "--log-failed").stdout
                line += f"\n    {first_error_line(log)}"
            print(line)
    if reported == 0:
        print("every default-branch workflow's latest completed run is green")
    return 1 if reported and arguments.fail_on_red else 0


if __name__ == "__main__":
    raise SystemExit(main())
