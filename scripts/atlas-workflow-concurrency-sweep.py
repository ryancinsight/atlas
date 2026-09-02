#!/usr/bin/env python3
"""Sweep a member's workflows out of the `default_branch_cancel_in_progress` class.

    atlas-workflow-concurrency-sweep.py <member> [--dry-run] [--update]

A workflow with a `push` trigger on the default branch and an unconditional
`cancel-in-progress: true` lets each merge cancel the previous merge's
verification: GitHub supersedes a *pending* run in a shared concurrency group
whatever the flag says, so under runner starvation the default branch's newest
verdict is `cancelled` (ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02; the conformance
class of the same name is the detector this tool imports).

For every flagged workflow at the member's `origin/<default>` it rewrites the
concurrency block:

- verification workflows: the group keys per ref for pull requests and per
  commit on the default branch; cancellation applies to pull requests only;
- deploy/publish workflows (identified by file name — release, pages, publish,
  deploy — or a Pages-deploy action): `cancel-in-progress: false`, so deploys
  queue; a half-cancelled deploy is worse than a superseded one.

The change is authored through the GitHub API on branch
`ci/default-branch-runs-reach-a-verdict` — no shared working tree is touched —
and opened as a pull request. `--dry-run` prints unified diffs and opens
nothing; `--update` rebuilds an existing branch in place from current
`origin/<default>` (never a whole-blob rebase, which reverts what the default
branch changed since). A member with nothing flagged exits 0 with a note.
"""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import ROOT, git  # noqa: E402

BRANCH = "ci/default-branch-runs-reach-a-verdict"
ITEM = "ATLAS-DEFAULT-BRANCH-CANCEL-2026-09-02"
DEPLOY_MARKERS = ("deploy-pages", "upload-pages-artifact", "pypa/gh-action-pypi-publish",
                  "crates-io-auth-action", "softprops/action-gh-release")
DEPLOY_NAME = re.compile(r"(release|pages|publish|deploy)", re.I)
# `[ \t]*\r?$`, not `\s*$`: in multiline mode `\s*` swallows the newline and the
# blank line after it; `\r?` keeps CRLF workflows (six members' book-pages.yml)
# in scope, exactly as the detector's `\s*$` already treats them.
GROUP_LINE = re.compile(r"(?m)^([ \t]+)group:[ \t]*(.+?)[ \t]*\r?$")
CANCEL_LINE = re.compile(r"(?m)^([ \t]+)cancel-in-progress:[ \t]*true[ \t]*\r?$")
PER_COMMIT = "github.event_name == 'pull_request' && github.ref || github.sha"


def load_detector():
    spec = importlib.util.spec_from_file_location("atlas_conformance", ROOT / "scripts" / "atlas-conformance.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.cancels_default_branch_runs


def is_deploy(path: str, text: str) -> bool:
    return bool(DEPLOY_NAME.search(path.rsplit("/", 1)[-1])) or any(marker in text for marker in DEPLOY_MARKERS)


def rewrite(path: str, text: str) -> tuple[str, str]:
    """Return (rewritten text, kind) for one flagged workflow.

    `kind` is `verification`, `deploy`, or `skip: <reason>`; a skip leaves the
    text unchanged and is reported, never silently absorbed.
    """
    cancel = CANCEL_LINE.search(text)
    if cancel is None:
        return text, "skip: no unconditional cancel line"
    indent = cancel.group(1)
    if is_deploy(path, text):
        new = (f"{indent}# Deploys queue behind one another; a half-cancelled deploy is worse than a\n"
               f"{indent}# superseded one, and a cancelled default-branch run leaves that merge undeployed.\n"
               f"{indent}cancel-in-progress: false")
        result = text[: cancel.start()] + new + text[cancel.end():]
        kind = "deploy"
    else:
        group = GROUP_LINE.search(text)
        if group is None or "github.ref" not in group.group(2):
            return text, "skip: group line without github.ref"
        if "github.sha" in group.group(2):
            return text, "skip: group already keyed per commit"
        value = group.group(2).replace("github.ref", PER_COMMIT, 1)
        result = text[: group.start()] + (
            f"{indent}# Pull requests share one group per ref and cancel superseded runs; default-\n"
            f"{indent}# branch runs get one group per commit, since GitHub supersedes a pending run\n"
            f"{indent}# in a shared group whatever `cancel-in-progress` says.\n"
            f"{indent}group: {value}"
        ) + text[group.end():]
        cancel = CANCEL_LINE.search(result)
        result = result[: cancel.start()] + f"{indent}cancel-in-progress: ${{{{ github.event_name == 'pull_request' }}}}" + result[cancel.end():]
        kind = "verification"
    if "\r\n" in text:  # keep the file's own line-ending convention for inserted lines
        result = re.sub(r"(?<!\r)\n", "\r\n", result)
    return result, kind


def gh(*args: str, **options) -> str:
    completed = subprocess.run(["gh", *args], capture_output=True, encoding="utf-8", errors="replace", **options)
    if completed.returncode != 0:
        sys.exit(f"gh {' '.join(args[:3])} failed: {completed.stderr[-500:]}")
    return completed.stdout


def gh_json(*args: str, **options):
    return json.loads(gh(*args, **options))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("member")
    parser.add_argument("--dry-run", action="store_true", help="print diffs, open nothing")
    parser.add_argument("--update", action="store_true", help="rebuild an existing branch in place from origin")
    arguments = parser.parse_args()
    repo = ROOT / "repos" / arguments.member
    if not (repo / ".git").exists():
        print(f"error: {repo} is not a checked-out member", file=sys.stderr)
        return 2
    cancels = load_detector()
    url = (git(repo, "remote", "get-url", "origin") or "").strip()
    slug = re.sub(r"\.git$", "", url.split("github.com/")[1])
    git(repo, "fetch", "-q", "origin")
    head = (git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD") or "").strip()
    default_branch = head.split("/", 1)[1] if "/" in head else "main"
    base = git(repo, "rev-parse", f"origin/{default_branch}").strip()
    paths = [p for p in git(repo, "ls-tree", "-r", "--name-only", base).split("\n")
             if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))]

    changes: dict[str, str] = {}
    kinds: dict[str, str] = {}
    originals: dict[str, str] = {}
    for path in paths:
        text = subprocess.run(["git", "-C", str(repo), "show", f"{base}:{path}"], capture_output=True).stdout.decode("utf-8")
        if not cancels(text):
            continue
        new_text, kind = rewrite(path, text)
        kinds[path] = kind
        if kind.startswith("skip"):
            continue
        if cancels(new_text):
            print(f"error: {path} still flagged after rewrite", file=sys.stderr)
            return 1
        changes[path], originals[path] = new_text, text
    for path, kind in sorted(kinds.items()):
        print(f"  {path}: {kind}")
    if not changes:
        print(f"{arguments.member}: nothing to change")
        return 0
    if arguments.dry_run:
        for path, new_text in changes.items():
            sys.stdout.writelines(difflib.unified_diff(originals[path].splitlines(True), new_text.splitlines(True), path, path, n=1))
        return 0

    branch_exists = subprocess.run(["gh", "api", f"repos/{slug}/git/ref/heads/{BRANCH}"], capture_output=True).returncode == 0
    if branch_exists and not arguments.update:
        print(f"error: {BRANCH} exists on {slug}; pass --update to rebuild it in place", file=sys.stderr)
        return 1

    def blob(content: str) -> str:
        return gh_json("api", "-X", "POST", f"repos/{slug}/git/blobs", "--input", "-",
                       input=json.dumps({"content": content, "encoding": "utf-8"}))["sha"]

    base_tree = gh_json("api", f"repos/{slug}/git/commits/{base}")["tree"]["sha"]
    tree = gh_json("api", "-X", "POST", f"repos/{slug}/git/trees", "--input", "-", input=json.dumps({
        "base_tree": base_tree,
        "tree": [{"path": p, "mode": "100644", "type": "blob", "sha": blob(t)} for p, t in changes.items()]}))["sha"]
    verification = [p.rsplit("/", 1)[-1] for p, k in kinds.items() if k == "verification"]
    deploys = [p.rsplit("/", 1)[-1] for p, k in kinds.items() if k == "deploy"]
    message = f"""ci: Let default-branch runs reach a verdict instead of cancelling each other

Every workflow here shared one concurrency group per ref with an
unconditional cancel-in-progress. GitHub supersedes a *pending* run in a
shared group whatever the flag says, so under runner starvation each
merge cancelled the previous merge's verification before a job started
and the default branch's newest verdict read `cancelled`.

Verification workflows ({', '.join(verification) or 'none'}) now key
default-branch runs per commit and cancel only pull-request runs. Deploy
workflows ({', '.join(deploys) or 'none'}) set cancel-in-progress: false
so deploys queue rather than half-cancel.

Refs: {ITEM}

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"""
    commit = gh_json("api", "-X", "POST", f"repos/{slug}/git/commits", "--input", "-",
                     input=json.dumps({"message": message, "tree": tree, "parents": [base]}))["sha"]
    if branch_exists:
        gh("api", "-X", "PATCH", f"repos/{slug}/git/refs/heads/{BRANCH}", "--input", "-",
           input=json.dumps({"sha": commit, "force": True}))
        print(f"{arguments.member}: {BRANCH} rebuilt -> {commit[:8]} ({len(changes)} workflow(s)); PR unchanged")
        return 0
    gh("api", "-X", "POST", f"repos/{slug}/git/refs", "-f", f"ref=refs/heads/{BRANCH}", "-f", f"sha={commit}")
    body = (
        f"## Change\n\nAtlas's conformance class `default_branch_cancel_in_progress` ({ITEM}) flags {len(changes)} "
        f"workflow(s) here: a `push` trigger on `{default_branch}` with an unconditional `cancel-in-progress: true`. "
        "GitHub supersedes a *pending* run in a shared concurrency group regardless of that flag, so under runner "
        "starvation each merge cancelled the previous merge's verification before any job started.\n\n"
        + "".join(f"- `{w}`: default-branch runs get one group per commit; pull requests keep the per-ref group and its cancellation.\n" for w in verification)
        + "".join(f"- `{w}`: `cancel-in-progress: false` — deploys queue; a half-cancelled deploy is worse than a superseded one.\n" for w in deploys)
        + "\nBehavior on pull requests is unchanged. Oracle: the next two pushes to the default branch both reach a "
        "completed verdict, and atlas's `scripts/atlas-red-workflows.py` stops reporting `cancelled` rows for this repository.\n\n"
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
    )
    pr = gh("pr", "create", "-R", slug, "--base", default_branch, "--head", BRANCH,
            "--title", "ci: Let default-branch runs reach a verdict instead of cancelling each other", "--body", body)
    print(f"{arguments.member}: {len(changes)} workflow(s) ({len(verification)} verification, {len(deploys)} deploy); PR {pr.strip().splitlines()[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
