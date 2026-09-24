#!/usr/bin/env python3
"""Fail when a recorded gitlink has drifted from its member's default branch.

Atlas records one commit per member. That pin is what every gate measures: the
conformance ratchet, the artifact budgets and the board audits all read the
member tree the pin selects, not whatever the member has since merged. A pin
left behind therefore does not merely age -- it silently redirects verification
onto superseded state. On 2026-09-21 all twenty-five members were behind their
defaults, by 2 to 701 commits, and the ratchet was measuring member boards at
commits predating their compaction; three unrelated pull requests failed on
debt those members had already deleted.

Two conditions, deliberately separated:

    behind      the pin is an ancestor of the default tip and `--max-behind`
                commits or fewer separate them -- ordinary sweep lag, clean;
                more than that is drift, and fails unless a waiver explains it
    ahead       the default tip is not a descendant of the pin: atlas records a
                commit that is not on the member's default branch at all. This
                is the worse condition and a different one -- not late, wrong.
                It fails on its own, and no waiver excuses it, because a waiver
                records a pin deliberately held *back*, which this is not.

Default resolution uses the network: `git ls-remote --symref <url> HEAD` reads
the member's published default branch and its tip. The alternative -- a local
clone's `origin/HEAD` -- is itself cached state that goes stale exactly when
this check matters most, so trusting it would let the guard agree with a drift
it exists to find. The cost is one remote round trip per member, which is why
the CI job runs on a schedule and on gitlink changes rather than on every pull
request.

An unreachable remote, or a pin whose object the member clone does not carry,
is reported as `unavailable` and exits 2. That is neither a pass nor drift: the
measurement did not happen. Only a member actually measured can be called
clean, so an offline run can never turn a drifted pin green.

Exit status:

    0   every member measured, none drifted, no off-default pin
    1   unexplained drift, an off-default pin, or a malformed waiver
    2   at least one member could not be measured (and nothing failed under 1)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_git_process import (  # noqa: E402
    GitProcessError,
    clean_process_env,
    execute as execute_git,
)
from atlas_stack import ROOT  # noqa: E402

WAIVERS = Path(__file__).resolve().parent / "pin-drift-waivers.json"
WAIVER_FIELDS = ("member", "reason", "reopen")
GITLINK_MODE = "160000"
SYMREF = re.compile(r"^ref:\s+refs/heads/(\S+)\s+HEAD$", re.MULTILINE)
OBJECT_ID = re.compile(r"[0-9a-f]{40}([0-9a-f]{24})?")

# Private scratch namespace for the branch this tool fetches to measure
# distance. Never `refs/remotes/*`: a bare `git fetch <url> <branch>` (no
# colon) still opportunistically updates the matching remote-tracking ref
# when `<url>` equals a configured remote's URL, and a destination under
# `refs/remotes/` risks colliding with the *caller's* own tracking ref when
# `-C`/git-dir resolution lands on the wrong repository. That is exactly
# ATLAS-ORIGIN-REF-CLOBBER-2026-09-21: a sweep fetching five different
# members' `main` landed each, forced, in Atlas's own `refs/remotes/origin/
# main` in turn. `refs/scratch/` is disposable, reused across members, and
# never read by anything but this measurement.
SCRATCH_REF_PREFIX = "refs/scratch/"
SCRATCH_HEAD_REF = f"{SCRATCH_REF_PREFIX}atlas-pin-drift-head"


def fetch_refspec(branch: str) -> str:
    """The refspec `distance` passes to `git fetch` for `branch`.

    Force-updates `SCRATCH_HEAD_REF` only -- never a `refs/remotes/*`
    destination -- so this tool's fetch can never overwrite a caller's
    remote-tracking ref, however `-C`/git-dir resolution lands.
    """
    return f"+{branch}:{SCRATCH_HEAD_REF}"


# Every refspec this tool ever passes to `git fetch`, in the form a caller
# might supply a branch name. Exercised by
# `test_atlas_pin_drift.FetchRefspecTestCase` so a future edit that routes a
# fetch destination back through `refs/remotes/` fails the suite immediately
# rather than waiting for another clobbered tracking ref to surface it.
FETCH_REFSPECS = tuple(fetch_refspec(branch) for branch in ("main", "master", "trunk"))

# One commit of lag is the race between a member landing a pull request and the
# next integration sweep advancing the pin; failing on it would make the gate
# red as a matter of course, and a gate nobody can keep green is worse than no
# gate. Two is already outside that race: the shallowest drift in the sweep
# that motivated this check was 2 commits, so this threshold catches every
# member of the observed defect population without firing on the unavoidable
# merge-then-sweep window.
DEFAULT_MAX_BEHIND = 1
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_JOBS = 8


@dataclass(frozen=True)
class Reading:
    """What one member's pin measured against its published default branch."""

    member: str
    url: str
    gitlink: str
    branch: str | None = None
    tip: str | None = None
    behind: int | None = None
    ahead: int | None = None
    unavailable: str | None = None


def _text(result) -> str:
    return result.stdout.decode("utf-8", errors="replace")


def _git(repo: Path, *args: str, timeout: int):
    return execute_git(repo, args, env=clean_process_env(), timeout=timeout)


def member_urls(repo: Path, rev: str, timeout: int) -> dict[str, str]:
    """Registered member name -> remote URL, read from `.gitmodules` at `rev`.

    Applies `atlas_stack`'s universe rule -- a `repos/<name>` path registered in
    `.gitmodules`, never a directory listing -- to the revision under test
    rather than to the checked-out file, so the pins judged and the members
    judged come from the same commit.
    """
    result = _git(
        repo,
        "config",
        "--blob",
        f"{rev}:.gitmodules",
        "--get-regexp",
        r"^submodule\..*\.(path|url)$",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise GitProcessError(
            f"cannot read .gitmodules at {rev}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    paths: dict[str, str] = {}
    urls: dict[str, str] = {}
    for line in _text(result).splitlines():
        key, _, value = line.partition(" ")
        section, _, field = key.rpartition(".")
        if field == "path":
            paths[section] = value.strip()
        elif field == "url":
            urls[section] = value.strip()
    resolved: dict[str, str] = {}
    for section, path in paths.items():
        prefix, _, name = path.rpartition("/")
        if prefix == "repos" and name and section in urls:
            resolved[name] = urls[section]
    return resolved


def recorded_gitlinks(repo: Path, rev: str, timeout: int) -> dict[str, str]:
    """Registered member name -> the commit atlas records for it at `rev`."""
    result = _git(repo, "ls-tree", "-z", rev, "repos/", timeout=timeout)
    if result.returncode != 0:
        raise GitProcessError(
            f"cannot list repos/ at {rev}: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )
    gitlinks: dict[str, str] = {}
    for record in _text(result).split("\0"):
        if not record.strip():
            continue
        meta, _, path = record.partition("\t")
        fields = meta.split()
        if len(fields) >= 3 and fields[0] == GITLINK_MODE:
            gitlinks[path.strip().rsplit("/", 1)[-1]] = fields[2]
    return gitlinks


def published_default(repo: Path, url: str, timeout: int) -> tuple[str, str]:
    """The member's default branch name and tip, read from the remote.

    Raises `GitProcessError` when the remote cannot be reached, so the caller
    records the member as unmeasured instead of clean.
    """
    result = _git(repo, "ls-remote", "--symref", url, "HEAD", timeout=timeout)
    if result.returncode != 0:
        raise GitProcessError(
            f"ls-remote failed: "
            f"{result.stderr.decode('utf-8', errors='replace').strip() or 'no output'}"
        )
    out = _text(result)
    match = SYMREF.search(out)
    if match is None:
        raise GitProcessError("remote published no symbolic HEAD")
    branch = match.group(1)
    for line in out.splitlines():
        # The symref line answers with the same `HEAD` in its second field, so
        # it must be skipped explicitly or it is read as the tip itself.
        if line.startswith("ref:"):
            continue
        sha, _, ref = line.partition("\t")
        if ref.strip() == "HEAD" and OBJECT_ID.fullmatch(sha.strip()):
            return branch, sha.strip()
    raise GitProcessError("remote published no HEAD tip")


def distance(clone: Path, url: str, branch: str, gitlink: str, timeout: int) -> tuple[int, int]:
    """Commits the pin is (behind, ahead of) the published default tip.

    Force-fetches the branch into `SCRATCH_HEAD_REF` -- a private
    `refs/scratch/` ref, never a remote-tracking one -- and no working tree
    of the member clone is touched. A bare `git fetch <url> <branch>` (what
    this used to do) opportunistically updates the matching
    `refs/remotes/*` ref whenever `<url>` equals a configured remote's URL;
    routing the destination through `fetch_refspec` instead means this
    tool's fetch can never land in a `refs/remotes/` ref, the caller's
    included (ATLAS-ORIGIN-REF-CLOBBER-2026-09-21).
    """
    fetched = _git(
        clone, "fetch", "--no-tags", "--quiet", url, fetch_refspec(branch), timeout=timeout
    )
    if fetched.returncode != 0:
        raise GitProcessError(
            f"fetch failed: "
            f"{fetched.stderr.decode('utf-8', errors='replace').strip() or 'no output'}"
        )
    counted = _git(
        clone,
        "rev-list",
        "--left-right",
        "--count",
        f"{gitlink}...{SCRATCH_HEAD_REF}",
        timeout=timeout,
    )
    if counted.returncode != 0:
        raise GitProcessError(
            "cannot count against the default tip (is the recorded commit present?): "
            f"{counted.stderr.decode('utf-8', errors='replace').strip() or 'no output'}"
        )
    fields = _text(counted).split()
    if len(fields) != 2 or not all(field.isdigit() for field in fields):
        raise GitProcessError(f"unreadable rev-list output: {_text(counted)!r}")
    ahead, behind = (int(field) for field in fields)
    return behind, ahead


def measure(repo: Path, member: str, url: str, gitlink: str, timeout: int) -> Reading:
    try:
        branch, tip = published_default(repo, url, timeout)
    except GitProcessError as exc:
        return Reading(member, url, gitlink, unavailable=f"default branch unresolved: {exc}")
    clone = repo / "repos" / member
    if not (clone / ".git").exists():
        return Reading(
            member, url, gitlink, branch, tip,
            unavailable=f"no member clone at repos/{member}",
        )
    try:
        behind, ahead = distance(clone, url, branch, gitlink, timeout)
    except GitProcessError as exc:
        return Reading(member, url, gitlink, branch, tip, unavailable=str(exc))
    return Reading(member, url, gitlink, branch, tip, behind, ahead)


def load_waivers(path: Path) -> tuple[dict[str, dict], list[str]]:
    """Member -> waiver, plus every reason a declared waiver is unusable."""
    if not path.is_file():
        return {}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {}, [f"{path}: unreadable ({exc})"]
    if not isinstance(data, dict) or not isinstance(data.get("waivers"), list):
        return {}, [f"{path}: root must contain a `waivers` list"]
    waivers: dict[str, dict] = {}
    problems: list[str] = []
    for entry in data["waivers"]:
        values = [entry.get(field) if isinstance(entry, dict) else None for field in WAIVER_FIELDS]
        if not all(isinstance(value, str) and value.strip() for value in values):
            problems.append(
                f"{path}: waiver needs non-empty string "
                f"`{'`, `'.join(WAIVER_FIELDS)}`: {entry!r}"
            )
            continue
        waivers[entry["member"]] = entry
    return waivers, problems


def report(readings: list[Reading], waivers: dict[str, dict], max_behind: int) -> tuple[int, int, int]:
    """Print one verdict per member; return (failures, waived, unavailable)."""
    failures = waived = unavailable = 0
    for reading in sorted(readings, key=lambda item: item.member):
        if reading.unavailable is not None:
            unavailable += 1
            print(f"UNAVAILABLE: {reading.member} -- {reading.unavailable}")
            print("        Not measured, so not clean. Re-run with the remote reachable.")
            continue
        where = f"{reading.branch} @ {reading.tip[:10]}"
        if reading.ahead:
            failures += 1
            print(f"OFF-DEFAULT: {reading.member} -- pin {reading.gitlink[:10]} is not on {where}")
            print(
                f"        {reading.ahead} commit(s) of the pin are absent from the default "
                f"branch, which trails it by {reading.behind}."
            )
            print(
                "        Atlas records a commit the member does not publish. Land it on the "
                "default branch or re-pin; a waiver does not cover this."
            )
            continue
        if reading.behind > max_behind:
            entry = waivers.get(reading.member)
            if entry is not None:
                waived += 1
                print(
                    f"waived: {reading.member} -- {reading.behind} behind {where} "
                    f"(pin {reading.gitlink[:10]})"
                )
                print(f"        {entry['reason']}")
                print(f"        re-open: {entry['reopen']}")
                continue
            failures += 1
            print(
                f"PIN DRIFT: {reading.member} -- {reading.behind} commit(s) behind {where} "
                f"(pin {reading.gitlink[:10]}, allowed {max_behind})"
            )
            print(
                f"        Advance the gitlink: git -C repos/{reading.member} fetch origin "
                f"{reading.branch} && git add repos/{reading.member}"
            )
            print("        Holding it deliberately? Record the reason and re-open trigger.")
            continue
        print(f"ok: {reading.member} -- {reading.behind} behind {where}")
    return failures, waived, unavailable


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=str(ROOT), help="meta-repository to read pins from")
    parser.add_argument("--rev", default="HEAD", help="revision whose recorded pins are judged")
    parser.add_argument("--waivers", default=str(WAIVERS))
    parser.add_argument(
        "--max-behind",
        type=int,
        default=DEFAULT_MAX_BEHIND,
        help=f"commits of sweep lag tolerated before drift is reported (default {DEFAULT_MAX_BEHIND})",
    )
    parser.add_argument(
        "--member", action="append", default=None, help="restrict the scan to this member (repeatable)"
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--jobs",
        type=int,
        default=DEFAULT_JOBS,
        help=f"members measured concurrently (default {DEFAULT_JOBS})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repo = Path(args.repo).resolve()
        waivers, problems = load_waivers(Path(args.waivers))
        for problem in problems:
            print(f"WAIVER PROBLEM: {problem}")
        urls = member_urls(repo, args.rev, args.timeout)
        gitlinks = recorded_gitlinks(repo, args.rev, args.timeout)
        selected = sorted(set(urls) & set(gitlinks))
        if args.member:
            selected = [name for name in selected if name in set(args.member)]
        if args.jobs < 1:
            raise ValueError("--jobs must be at least 1")

        def read_member(name: str) -> Reading:
            return measure(repo, name, urls[name], gitlinks[name], args.timeout)

        workers = min(args.jobs, len(selected)) or 1
        with ThreadPoolExecutor(max_workers=workers) as executor:
            readings = list(executor.map(read_member, selected))
    except (GitProcessError, OSError, UnicodeError, ValueError) as exc:
        print(f"atlas-pin-drift: ERROR - {exc}")
        return 2
    failures, waived, unavailable = report(readings, waivers, args.max_behind)
    for member in sorted(set(waivers) - {reading.member for reading in readings}):
        print(f"note: waiver for {member} explains nothing in this scan")
    suffix = f", {waived} waived" if waived else ""
    if problems or failures:
        print(
            f"\natlas-pin-drift: FAIL - {failures} member(s) drifted or off-default"
            f"{suffix}, {len(problems)} malformed waiver(s)"
        )
        return 1
    if unavailable:
        print(
            f"\natlas-pin-drift: UNAVAILABLE - {unavailable} of {len(readings)} member(s) "
            f"could not be measured{suffix}; this is not a pass"
        )
        return 2
    print(f"atlas-pin-drift: OK - {len(readings)} member(s) within {args.max_behind}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
