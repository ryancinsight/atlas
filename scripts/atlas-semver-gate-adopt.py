#!/usr/bin/env python3
"""Adopt Atlas's shared SemVer gate in one member, as an API pull request.

    atlas-semver-gate-adopt.py <member> [--dry-run] [--update]

`cargo-semver-checks` is authoritative for Rust public-surface compatibility
(versioning policy), and the stack owns one reusable workflow for it
(`.github/workflows/semver-gate.yml`, ATLAS-SEMVER-GATE-FLEETWIDE-2026-08-28).
Adoption is a `workflow_call` in the member, never a per-repo copy — a
divergent copy is the duplication defect ADR 0035 exists to prevent.

Two calls land per member:

- the member's pull-request workflow gains an informational job, which diffs
  against the pull request's base commit and needs no published version, so
  every publishable crate goes in its list;
- the member's release workflow gains the blocking job (`release-gate: true`)
  and every other job in that workflow gains `needs: semver`, so a break the
  manifest version does not cover stops the release instead of racing it. The
  default registry baseline resolves the latest *published* version, so only
  crates the registry already carries go in that list; a member with none
  gets the informational job alone.

Package lists come from the member's own manifests at `origin/<default>`:
every `[package]` whose `publish` is neither `false` nor `[]` — the stack
uses `publish = false` as a release-ordering guard, and those crates have no
public contract to gate.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import difflib
import json
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import ROOT, git  # noqa: E402

BRANCH = "ci/semver-gate-adoption"
ITEM = "ATLAS-SEMVER-GATE-FLEETWIDE-2026-08-28"
SHARED = "ryancinsight/atlas/.github/workflows/semver-gate.yml"
INDEX = "https://index.crates.io"
# A workflow that verifies pull requests, in preference order. The others a
# member carries on `pull_request` (docs, ADR index, lockfile, MSRV) are
# single-purpose gates; the semver job belongs beside the crate verification.
CI_NAMES = ("ci.yml", "rust-ci.yml", "ci.yaml", "rust-ci.yaml")
RELEASE_NAMES = ("rust-release.yml", "release.yml", "crates-release.yml")
JOBS_LINE = re.compile(r"(?m)^jobs:[ \t]*\r?$")
TOP_LEVEL_JOB = re.compile(r"(?m)^  (?P<name>[A-Za-z_][\w-]*):[ \t]*\r?$")


def sparse_index_path(name: str) -> str:
    """The crate's path in the sparse registry index (cargo's own layout)."""
    name = name.lower()
    if len(name) == 1:
        return f"1/{name}"
    if len(name) == 2:
        return f"2/{name}"
    if len(name) == 3:
        return f"3/{name[0]}/{name}"
    return f"{name[:2]}/{name[2:4]}/{name}"


def published(names: list[str], opener=urllib.request.urlopen) -> set[str]:
    """The subset of `names` the registry already carries.

    A crate absent from the index has no published baseline, so the release
    gate cannot compare against one; it is left to the informational job
    until its first publish.
    """

    def probe(name: str) -> tuple[str, bool]:
        request = urllib.request.Request(
            f"{INDEX}/{sparse_index_path(name)}",
            headers={"User-Agent": "atlas-semver-gate-adoption"},
        )
        try:
            with opener(request, timeout=20) as response:
                return name, response.status == 200
        except (urllib.error.URLError, OSError, ValueError):
            return name, False

    if not names:
        return set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return {name for name, exists in pool.map(probe, sorted(set(names))) if exists}


def publishable_packages(manifests: dict[str, str]) -> list[str]:
    """Package names from `path -> manifest text`, in manifest-path order."""
    names = []
    for path in sorted(manifests):
        try:
            data = tomllib.loads(manifests[path])
        except tomllib.TOMLDecodeError:
            continue
        package = data.get("package")
        if not isinstance(package, dict) or not isinstance(package.get("name"), str):
            continue
        publish = package.get("publish", True)
        if publish is False or publish == []:
            continue
        names.append(package["name"])
    return names


def job_block(
    *,
    name: str,
    packages: list[str],
    atlas_ref: str,
    toolchain: str | None,
    guard: str | None,
    release: bool,
    comment: str,
) -> str:
    """One `workflow_call` job, indented for a workflow's `jobs:` mapping."""
    lines = [f"  # {line}" for line in comment.splitlines()]
    lines.append(f"  {name}:")
    lines.append(f"    name: SemVer gate{' (release)' if release else ''}")
    if guard:
        lines.append("    if: >-")
        lines.extend(f"      {part}" for part in guard.splitlines())
    lines.append(f"    uses: {SHARED}@{atlas_ref}")
    lines.append("    with:")
    if release:
        lines.append("      release-gate: true")
    lines.append(f"      package: {','.join(packages)}")
    if toolchain:
        lines.append(f"      rust-toolchain: {toolchain}")
    lines.append("    permissions:")
    lines.append("      contents: read")
    return "\n".join(lines) + "\n\n"


def insert_job(text: str, block: str) -> str:
    """Insert `block` as the first entry of the workflow's `jobs:` mapping."""
    match = JOBS_LINE.search(text)
    if match is None:
        raise ValueError("workflow has no top-level `jobs:` key")
    cut = match.end() + len(text[match.end():]) - len(text[match.end():].lstrip("\r\n"))
    return text[:cut] + block + text[cut:]


def add_needs(text: str, job: str) -> str:
    """Give every other top-level job a `needs:` on `job`.

    Without this the gate runs beside the publish job instead of before it:
    a failed job does not stop an independent one, so the release would ship
    while the gate was still red. A job that already declares `needs` is left
    alone — it is downstream of one that now waits.

    The scan starts at `jobs:` because two-space keys appear above it too: a
    release workflow's own `on: release:` trigger is one, and treating it as
    a job put `needs:` inside the trigger block.
    """
    jobs = JOBS_LINE.search(text)
    if jobs is None:
        raise ValueError("workflow has no top-level `jobs:` key")
    newline = "\r\n" if "\r\n" in text else "\n"
    result = text
    # Reverse order keeps each match's offsets valid as earlier lines shift.
    for match in reversed(list(TOP_LEVEL_JOB.finditer(text, jobs.end()))):
        if match.group("name") == job:
            continue
        line_end = text.find("\n", match.end())
        body_start = len(text) if line_end < 0 else line_end + 1
        body = text[body_start:]
        end = TOP_LEVEL_JOB.search(body)
        if re.search(r"(?m)^    needs:", body[: end.start()] if end else body):
            continue
        result = result[:body_start] + f"    needs: {job}{newline}" + result[body_start:]
    return result


def guard_of(text: str) -> str | None:
    """The release workflow's own job guard, so the gate shares its events."""
    match = re.search(
        r"(?m)^    if: >-\r?\n(?P<body>(?:^      .*\r?\n)+)", text
    )
    if match is None:
        return None
    return "\n".join(line.strip() for line in match.group("body").strip().splitlines())


def gh(*args: str, **options) -> str:
    completed = subprocess.run(["gh", *args], capture_output=True, encoding="utf-8",
                               errors="replace", **options)
    if completed.returncode != 0:
        sys.exit(f"gh {' '.join(args[:3])} failed: {completed.stderr[-500:]}")
    return completed.stdout


def gh_json(*args: str, **options):
    return json.loads(gh(*args, **options))


def read(repo: Path, ref: str, path: str) -> str | None:
    completed = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{path}"],
                               capture_output=True)
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8", "replace")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("member")
    parser.add_argument("--dry-run", action="store_true", help="print diffs, open nothing")
    parser.add_argument("--update", action="store_true", help="rebuild an existing branch in place")
    arguments = parser.parse_args()

    repo = ROOT / "repos" / arguments.member
    if not (repo / ".git").exists():
        print(f"error: {repo} is not a checked-out member", file=sys.stderr)
        return 2
    url = (git(repo, "remote", "get-url", "origin") or "").strip()
    slug = re.sub(r"\.git$", "", url.split("github.com/")[1])
    git(repo, "fetch", "-q", "origin")
    head = (git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD") or "").strip()
    default_branch = head.split("/", 1)[1] if "/" in head else "main"
    ref = f"origin/{default_branch}"
    base = git(repo, "rev-parse", ref).strip()
    atlas_ref = git(ROOT, "rev-parse", "origin/main").strip()

    paths = git(repo, "ls-tree", "-r", "--name-only", base).split("\n")
    manifests = {p: read(repo, base, p) or "" for p in paths if p.endswith("Cargo.toml")}
    packages = publishable_packages(manifests)
    if not packages:
        print(f"{arguments.member}: no publishable crates; the gate has no contract to check")
        return 0

    workflows = {p.rsplit("/", 1)[-1]: p for p in paths if p.startswith(".github/workflows/")}
    ci_name = next((n for n in CI_NAMES if n in workflows), None)
    if ci_name is None:
        print(f"error: {arguments.member} has no recognized verification workflow "
              f"({', '.join(CI_NAMES)})", file=sys.stderr)
        return 1
    ci_text = read(repo, base, workflows[ci_name]) or ""
    if f"{SHARED}@" in ci_text:
        print(f"{arguments.member}: {ci_name} already calls the shared gate")
        return 0

    toolchain = None
    pin = read(repo, base, "rust-toolchain.toml")
    if pin:
        channel = re.search(r'channel\s*=\s*"([^"]+)"', pin)
        toolchain = channel.group(1).split("-", 1)[0] if channel else None

    changes: dict[str, str] = {}
    originals: dict[str, str] = {}
    ci_block = job_block(
        name="semver", packages=packages, atlas_ref=atlas_ref, toolchain=toolchain,
        guard=None, release=False,
        comment=("Public-surface compatibility, informational on pull requests: the\n"
                 "detected change class is visible while the change is still in\n"
                 "review. The blocking comparison runs on release.\n"
                 f"Atlas {ITEM}."),
    )
    changes[workflows[ci_name]] = insert_job(ci_text, ci_block)
    originals[workflows[ci_name]] = ci_text

    release_name = next((n for n in RELEASE_NAMES if n in workflows), None)
    registry = sorted(published(packages))
    note = ""
    if release_name and registry:
        release_text = read(repo, base, workflows[release_name]) or ""
        if f"{SHARED}@" not in release_text:
            release_block = job_block(
                name="semver", packages=registry, atlas_ref=atlas_ref, toolchain=toolchain,
                guard=guard_of(release_text), release=True,
                comment=("A public-surface break the manifest version does not cover\n"
                         "stops the release here. The baseline is the latest published\n"
                         "version, so the list is the crates the registry carries.\n"
                         f"Atlas {ITEM}."),
            )
            updated = add_needs(insert_job(release_text, release_block), "semver")
            changes[workflows[release_name]] = updated
            originals[workflows[release_name]] = release_text
    elif release_name:
        note = " (release gate deferred: no package is on the registry yet)"

    for path, text in changes.items():
        try:
            import yaml  # noqa: PLC0415 - optional local validation
        except ImportError:
            break
        yaml.safe_load(text)

    if arguments.dry_run:
        for path, text in changes.items():
            sys.stdout.writelines(difflib.unified_diff(
                originals[path].splitlines(True), text.splitlines(True), path, path, n=2))
        print(f"{arguments.member}: {len(packages)} publishable, {len(registry)} published{note}")
        return 0

    exists = subprocess.run(["gh", "api", f"repos/{slug}/git/ref/heads/{BRANCH}"],
                            capture_output=True).returncode == 0
    if exists and not arguments.update:
        print(f"error: {BRANCH} exists on {slug}; pass --update to rebuild it", file=sys.stderr)
        return 1

    def blob(content: str) -> str:
        return gh_json("api", "-X", "POST", f"repos/{slug}/git/blobs", "--input", "-",
                       input=json.dumps({"content": content, "encoding": "utf-8"}))["sha"]

    base_tree = gh_json("api", f"repos/{slug}/git/commits/{base}")["tree"]["sha"]
    tree = gh_json("api", "-X", "POST", f"repos/{slug}/git/trees", "--input", "-", input=json.dumps({
        "base_tree": base_tree,
        "tree": [{"path": p, "mode": "100644", "type": "blob", "sha": blob(t)}
                 for p, t in changes.items()]}))["sha"]
    message = f"""ci: Adopt the shared SemVer gate

`cargo-semver-checks` is authoritative for public-surface compatibility,
and nothing here ran it: a break could ship under a patch bump, as one
did in mnemosyne (MN-458 removed a `pub unsafe fn` and shipped labelled
[patch]). Atlas owns the gate as one reusable workflow; this adopts it
rather than copying it.

{ci_name} gains the informational job, which diffs against the pull
request's base commit and reports the detected change class while the
change is still in review ({len(packages)} publishable crate(s)).
{f'{release_name} gains the blocking job over the {len(registry)} published crate(s), and its other jobs now wait on it, so a break the manifest version does not cover stops the release.' if release_name in changes else 'The blocking release comparison follows once a crate is on the registry.'}

Refs: {ITEM}

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"""
    commit = gh_json("api", "-X", "POST", f"repos/{slug}/git/commits", "--input", "-",
                     input=json.dumps({"message": message, "tree": tree, "parents": [base]}))["sha"]
    if exists:
        gh("api", "-X", "PATCH", f"repos/{slug}/git/refs/heads/{BRANCH}", "--input", "-",
           input=json.dumps({"sha": commit, "force": True}))
        print(f"{arguments.member}: {BRANCH} rebuilt -> {commit[:8]}; PR unchanged")
        return 0
    gh("api", "-X", "POST", f"repos/{slug}/git/refs", "-f", f"ref=refs/heads/{BRANCH}",
       "-f", f"sha={commit}")
    body = (
        f"## Change\n\nThis repository ran no `cargo-semver-checks`, so a public-surface break could "
        f"ship under a patch bump — one did in mnemosyne (`MN-458` removed a `pub unsafe fn` and "
        f"shipped labelled `[patch]`). Atlas owns the gate as one reusable workflow "
        f"(`semver-gate.yml`, atlas `{ITEM}`); this adopts it by `workflow_call` rather than "
        f"copying it, so the gate's own fixes arrive by advancing one pin.\n\n"
        f"- `{ci_name}`: informational job over the {len(packages)} publishable crate(s), diffing "
        f"against the pull request's base commit. `continue-on-error`, so it reports the detected "
        f"change class in review without blocking.\n"
        + (f"- `{release_name}`: blocking job over the {len(registry)} published crate(s), sharing "
           f"the workflow's own release guard; the other jobs now `needs: semver`, so a break the "
           f"manifest version does not cover stops the release instead of racing it.\n"
           if release_name in changes else
           f"- The blocking release comparison is deferred: no crate here is on the registry yet, "
           f"so there is no published baseline to compare against.\n")
        + "\nNo manifest version changes here, and no classification is retrofitted onto merged "
        "history.\n\nOracle: this pull request's own `SemVer (informational)` job completes and "
        "reports its change class.\n\n"
        f"Refs: atlas `{ITEM}`\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)"
    )
    pr = gh("pr", "create", "-R", slug, "--base", default_branch, "--head", BRANCH,
            "--title", "ci: Adopt the shared SemVer gate", "--body", body)
    print(f"{arguments.member}: {len(changes)} workflow(s), {len(packages)} publishable, "
          f"{len(registry)} published; PR {pr.strip().splitlines()[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
