#!/usr/bin/env python3
"""Bounded merge gate for pull requests: wait, verify by name, rebase-merge.

    atlas-pr-waiter.py --require 'ADR index' owner/repo#12 owner/other#7 ...
    atlas-pr-waiter.py --timeout-minutes 60 --require 'msrv|floor|Rust 1' ...

Every target is polled once a minute until the cap. A target merges when the
check rollup has no pending and no failed check, at least one check whose name
matches `--require` is SUCCESS, and the merge then verifiably lands (`MERGED`
is echoed only after re-reading the PR). Advisory bots (recurseml,
CodeRabbit) are ignored. The cap is the point: a merge wait is a bounded
external interaction, never an open-ended posture, and a target still pending
at the cap is reported with its pending checks so the next orientation
re-launches it deliberately.

Why the name gate is mandatory: a PR that changes a workflow file and breaks
it schedules none of that workflow's jobs, so "every listed check is green"
holds vacuously on the unrelated ones. melinoe#23 and eunomia#76 merged a
rejected `msrv.yml` that way on 2026-09-02. Name the changed workflow's job
(or the decisive gate) in `--require`; a rollup lacking it never merges.
Item: ATLAS-MSRV-JOBS-OVERRIDDEN-2026-09-02 (incident record).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time

ADVISORY = ("recurseml", "coderabbit")
FAILED_STATES = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
POLL_SECONDS = 60


def gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], capture_output=True, encoding="utf-8", errors="replace", check=False)


def check_status(check: dict) -> str:
    """One state per rollup entry: SUCCESS, PENDING, or a failure conclusion.

    CheckRun entries carry `status`/`conclusion`; StatusContext entries carry
    `state`. An unfinished CheckRun is PENDING whatever its conclusion field says.
    """
    if check.get("status") is not None:
        if check.get("status") != "COMPLETED":
            return "PENDING"
        return (check.get("conclusion") or "PENDING").upper()
    return (check.get("state") or "PENDING").upper()


def check_name(check: dict) -> str:
    return check.get("name") or check.get("context") or "?"


def decisive_checks(rollup: list[dict]) -> dict[str, str]:
    """Name → state for every non-advisory rollup entry."""
    return {check_name(c): check_status(c) for c in rollup
            if not any(bot in check_name(c).lower() for bot in ADVISORY)}


def gate(names: dict[str, str], required: re.Pattern[str]) -> str:
    """'merge', 'red', or 'wait' for one rollup snapshot."""
    if any(state in FAILED_STATES for state in names.values()):
        return "red"
    if not names or any(state == "PENDING" for state in names.values()):
        return "wait"
    if not any(required.search(name) and state == "SUCCESS" for name, state in names.items()):
        return "wait"  # the decisive check is absent — a rejected workflow file looks exactly like this
    return "merge"


def wait_for(target: str, required: re.Pattern[str], limit_minutes: int, report) -> None:
    slug, number = target.split("#")
    deadline = time.time() + limit_minutes * 60
    names: dict[str, str] = {}
    while time.time() < deadline:
        view = gh("pr", "view", number, "-R", slug, "--json", "state,statusCheckRollup,mergeCommit")
        try:
            pr = json.loads(view.stdout)
        except json.JSONDecodeError:
            time.sleep(POLL_SECONDS)
            continue
        if pr["state"] == "MERGED":
            return report(target, f"{target} MERGED {(pr.get('mergeCommit') or {}).get('oid', '')[:8]} (already)")
        if pr["state"] != "OPEN":
            return report(target, f"{target} is {pr['state']}")
        names = decisive_checks(pr["statusCheckRollup"])
        verdict = gate(names, required)
        if verdict == "red":
            # Confirm before giving up: for about a minute after a push the
            # rollup still carries the previous commit's runs, so a failure
            # already fixed on the new head reads as terminal. Mnemosyne #115
            # was abandoned that way, one commit after the fix for exactly the
            # check that reported it.
            failed = [n for n, s in names.items() if s in FAILED_STATES]
            time.sleep(POLL_SECONDS)
            recheck = gh("pr", "view", number, "-R", slug, "--json", "state,statusCheckRollup")
            try:
                names = decisive_checks(json.loads(recheck.stdout)["statusCheckRollup"])
            except (json.JSONDecodeError, KeyError):
                names = {}
            if gate(names, required) == "red":
                return report(target, f"{target} RED: {[n for n, s in names.items() if s in FAILED_STATES]}")
            report(target, f"{target} red cleared on recheck (was {failed}); still waiting", final=False)
            continue
        if verdict == "merge":
            merge = gh("pr", "merge", number, "-R", slug, "--rebase", "--delete-branch")
            after = json.loads(gh("pr", "view", number, "-R", slug, "--json", "state,mergeCommit").stdout)
            if after["state"] == "MERGED":
                return report(target, f"{target} MERGED {(after.get('mergeCommit') or {}).get('oid', '')[:8]} "
                                      f"(checks: {len(names)} green, required check present)")
            return report(target, f"{target} merge did not land: state={after['state']} {merge.stderr.strip()[-300:]}")
        time.sleep(POLL_SECONDS)
    pending = [n for n, s in names.items() if s == "PENDING"]
    report(target, f"{target} TIMEOUT after {limit_minutes} min; pending: {pending or 'required check absent'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("targets", nargs="+", metavar="owner/repo#N")
    parser.add_argument("--require", required=True, metavar="REGEX",
                        help="case-insensitive pattern a SUCCESS check name must match before merging")
    parser.add_argument("--timeout-minutes", type=int, default=60)
    arguments = parser.parse_args()
    required = re.compile(arguments.require, re.I)
    results: dict[str, str] = {}
    lock = threading.Lock()

    def report(target: str, text: str, final: bool = True) -> None:
        with lock:
            if final:
                results[target] = text
            print(text, flush=True)

    threads = [threading.Thread(target=wait_for, args=(t, required, arguments.timeout_minutes, report), daemon=True)
               for t in arguments.targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    unmerged = [t for t, text in results.items() if "MERGED" not in text]
    print(f"done: {len(results) - len(unmerged)} merged, {len(unmerged)} not: {unmerged}")
    return 1 if unmerged else 0


if __name__ == "__main__":
    raise SystemExit(main())
