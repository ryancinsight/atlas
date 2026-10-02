#!/usr/bin/env python3
"""Select, publish, and tag workspace crates whose manifest version is not on crates.io.

Commands, run from the member's workspace root:

    plan                    select the pending set, check it resolves and verifies; write
                            `packages` and `count` to $GITHUB_OUTPUT
    publish PACKAGES        re-check the set against the index, then `cargo publish` what is
                            still pending in one dependency-ordered invocation
    tag PACKAGES            create `<prefix><package>-v<version>` releases for the versions
                            the index now holds

PACKAGES is comma-separated. Every registry answer other than "found" or "not found" is an
error: an outage must never read as "nothing to publish" or "never published".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

USER_AGENT = "atlas-crates-pending (github.com/ryancinsight/atlas)"
WAIT_MARKER = "failed to select a version for the requirement"
# cargo: failed to select a version for the requirement `hermes-simd = "^0.7.0"`
MISSING_REQUIREMENT = re.compile(WAIT_MARKER + r" `([A-Za-z0-9_-]+) = ")
# cargo, when published versions meet the version requirement but none satisfies it here (a
# feature the published versions lack, or a conflict with another requirement):
# failed to select a version for `itoa`.
UNSATISFIED_REQUIREMENT = re.compile(r"failed to select a version for `([A-Za-z0-9_-]+)`")
# cargo, for a name the index has no entry for at all: no matching package named `ritk-x` found
NEVER_PUBLISHED = re.compile(r"no matching package named `([A-Za-z0-9_-]+)` found")
# crates.io's crawler policy: at most one API request per second.
API_INTERVAL_SECONDS = 1.0
# cargo publish waits 60 s (its default `publish.timeout`) for the last uploads to reach the
# index, then warns and exits 0. Tagging waits up to five minutes more before a missing version
# counts as lost: a red run is recoverable by re-running it, a green one without the release is not.
INDEX_POLL_INTERVAL_SECONDS = 10.0
INDEX_POLL_ATTEMPTS = 30


class RegistryError(RuntimeError):
    """The registry gave no usable answer (outage, rate limit, unexpected status)."""


def index_path(name: str) -> str:
    """Sparse-index path of a crate name (https://doc.rust-lang.org/cargo/reference/registry-index.html)."""
    n = name.lower()
    if len(n) <= 2:
        return f"{len(n)}/{n}"
    if len(n) == 3:
        return f"3/{n[0]}/{n}"
    return f"{n[:2]}/{n[2:4]}/{n}"


def http_get(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except (urllib.error.URLError, TimeoutError) as error:
        raise RegistryError(f"{url}: {error}") from error


Fetch = Callable[[str], "tuple[int, str]"]


def published_versions(name: str, fetch: Fetch = http_get) -> list[str] | None:
    """Versions on the index, or None when the name has never been published."""
    status, body = fetch(f"https://index.crates.io/{index_path(name)}")
    if status == 404:
        return None
    if status != 200:
        raise RegistryError(f"crates.io index returned HTTP {status} for {name}")
    return [json.loads(line)["vers"] for line in body.splitlines() if line.strip()]


def owners(name: str, fetch: Fetch = http_get) -> list[str]:
    status, body = fetch(f"https://crates.io/api/v1/crates/{name}/owners")
    if status != 200:
        raise RegistryError(f"crates.io owners API returned HTTP {status} for {name}")
    return [user["login"] for user in json.loads(body)["users"]]


def publishable(package: dict) -> bool:
    registries = package.get("publish")
    return registries is None or "crates-io" in registries


@dataclass
class Plan:
    pending: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def select(metadata: dict, owner: str, fetch: Fetch = http_get,
           sleep: Callable[[float], None] = time.sleep) -> Plan:
    """Publishable packages whose version is absent from an index the expected owner controls."""
    plan = Plan()
    for package in metadata["packages"]:
        if not publishable(package):
            continue
        name, version = package["name"], package["version"]
        versions = published_versions(name, fetch)
        if versions is None:
            plan.notices.append(
                f"{name} has never been published; its first publish needs an API token "
                "before trusted publishing applies")
            continue
        if version in versions:
            continue
        sleep(API_INTERVAL_SECONDS)
        logins = owners(name, fetch)
        if owner not in logins:
            plan.warnings.append(
                f"{name} on crates.io is owned by {', '.join(logins) or 'nobody'}, not {owner}; "
                "it needs a registry name of its own (ADR 0037 section 3)")
            continue
        plan.pending.append(name)
    return plan


Run = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def run(argv: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(argv, capture_output=True, text=True)


def package_args(names: list[str]) -> list[str]:
    return [arg for name in names for arg in ("--package", name)]


def dependents(names: list[str], packages: list[dict], dependency: str) -> list[str]:
    """The names that depend on `dependency`, directly or through other names, in their order.

    Every dependency kind counts: `cargo package` resolves a versioned dev-dependency against
    the registry exactly as it resolves a normal one. A dev-dependency with no version (a path
    or git one, whose requirement cargo metadata reports as `*`) is stripped from the packaged
    manifest, so it is no edge. Edges carry the package name, never a `package =` rename.
    """
    edges = {p["name"]: {d["name"] for d in p.get("dependencies", [])
                         if not (d.get("kind") == "dev" and d.get("req") == "*")}
             for p in packages}
    held = {dependency}
    # Every pass that changes `held` adds a name, so len(names) passes reach the closure.
    for _ in names:
        grown = [name for name in names if name not in held and edges.get(name, set()) & held]
        if not grown:
            break
        held.update(grown)
    return [name for name in names if name in held]


def verify(names: list[str], packages: list[dict], owner: str, fetch: Fetch = http_get,
           runner: Run = run, sleep: Callable[[float], None] = time.sleep) -> list[str]:
    """The names ready to publish: every one whose dependencies all resolve on crates.io.

    Resolution is checked first without compiling, so a wait costs no build. A name waits only
    when it, or a name it depends on, needs a version the index does not hold; the rest are
    re-resolved without it. A version `owner` publishes from another repository is a wait. One
    of a workspace member outside the pending set, or of a crate another account owns, needs a
    person (a first token publish, a requirement fix) and is warned about, but it still holds
    back only the names that need it. Verification then compiles the ready set here, before
    the publish job mints its short-lived registry token.
    """
    members = {package["name"] for package in packages}
    ready = list(names)
    while ready:
        resolved = runner(["cargo", "package", "--locked", "--no-verify", *package_args(ready)])
        if resolved.returncode == 0:
            break
        sys.stderr.write(resolved.stderr)
        missing = (MISSING_REQUIREMENT.search(resolved.stderr)
                   or UNSATISFIED_REQUIREMENT.search(resolved.stderr))
        absent = None if missing else NEVER_PUBLISHED.search(resolved.stderr)
        if missing is None and absent is None:
            raise SystemExit("cargo package failed for a reason other than a missing dependency version")
        dependency = (missing or absent).group(1)
        waiting = dependents(ready, packages, dependency)
        if not waiting:
            raise SystemExit(f"cargo names {dependency}, which no pending package depends on")
        held = " ".join(waiting)
        if absent is not None:
            # No index entry means no owner to ask: the first publish needs an API token.
            print(f"::warning::{dependency} has never been published on crates.io; its first "
                  f"publish needs an API token; held: {held}")
        elif dependency in members:
            print(f"::warning::no version of workspace member {dependency} on crates.io or in "
                  f"this run's pending set satisfies the requirement on it; held: {held}")
        else:
            sleep(API_INTERVAL_SECONDS)
            if owner in owners(dependency, fetch):
                print(f"::notice::waiting for the required {dependency} version to reach the "
                      f"index: {held}")
            else:
                print(f"::warning::{dependency} is owned by another crates.io account and the "
                      f"index lacks the required version; held: {held}")
        ready = [name for name in ready if name not in waiting]
    if not ready:
        return []
    verified = runner(["cargo", "package", "--locked", *package_args(ready)])
    if verified.returncode != 0:
        sys.stderr.write(verified.stderr)
        raise SystemExit("cargo package verification failed")
    return ready


def metadata(runner: Run = run) -> dict:
    result = runner(["cargo", "metadata", "--locked", "--no-deps", "--format-version", "1"])
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("cargo metadata failed")
    return json.loads(result.stdout)


def still_pending(names: list[str], versions: dict[str, str], fetch: Fetch = http_get) -> list[str]:
    return [name for name in names if versions[name] not in (published_versions(name, fetch) or [])]


def write_outputs(values: dict[str, str]) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
        for key, value in values.items():
            out.write(f"{key}={value}\n")


def command_plan(owner: str, fetch: Fetch = http_get, runner: Run = run,
                 sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    workspace = metadata(runner)
    plan = select(workspace, owner, fetch, sleep)
    for notice in plan.notices:
        print(f"::notice::{notice}")
    for warning in plan.warnings:
        print(f"::warning::{warning}")
    if not plan.pending:
        return {"count": "0"}
    ready = verify(plan.pending, workspace["packages"], owner, fetch, runner, sleep)
    held = [name for name in plan.pending if name not in ready]
    if held:
        print(f"::notice::pending packages ({' '.join(held)}) wait on a dependency "
              "version not yet on crates.io; the next push or schedule retries")
    if not ready:
        return {"count": "0"}
    print(f"::notice::publishing {','.join(ready)}")
    return {"packages": ",".join(ready), "count": str(len(ready))}


def command_publish(names: list[str], fetch: Fetch = http_get, runner: Run = run) -> None:
    versions = {p["name"]: p["version"] for p in metadata(runner)["packages"]}
    remaining = still_pending(names, versions, fetch)
    if not remaining:
        print("::notice::every planned version is already on crates.io")
        return
    # Verified in the plan job; the publish token's lifetime is spent on uploads only.
    result = runner(["cargo", "publish", "--locked", "--no-verify", *package_args(remaining)])
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        raise SystemExit("cargo publish failed")


def indexed_after_publish(names: list[str], versions: dict[str, str], published: bool,
                          fetch: Fetch = http_get,
                          sleep: Callable[[float], None] = time.sleep) -> list[str]:
    """Planned names whose version the index holds.

    After a successful publish every planned version must appear; one still missing after the
    poll budget fails the run, so re-running it recovers the release. After a failed publish,
    only the versions that did reach the index are tagged.
    """
    missing = still_pending(names, versions, fetch)
    for _ in range(INDEX_POLL_ATTEMPTS if published else 0):
        if not missing:
            break
        sleep(INDEX_POLL_INTERVAL_SECONDS)
        missing = still_pending(missing, versions, fetch)
    if published and missing:
        sys.stderr.write("re-run the failed job once they appear\n")
        raise SystemExit(f"published versions missing from the index: {', '.join(missing)}")
    return [name for name in names if name not in missing]


def command_tag(names: list[str], prefix: str, sha: str, repo: str, published: bool,
                fetch: Fetch = http_get, runner: Run = run,
                sleep: Callable[[float], None] = time.sleep) -> None:
    versions = {p["name"]: p["version"] for p in metadata(runner)["packages"]}
    for name in indexed_after_publish(names, versions, published, fetch, sleep):
        version = versions[name]
        tag = f"{prefix}{name}-v{version}"
        if runner(["gh", "release", "view", tag, "--repo", repo]).returncode == 0:
            continue
        # A release created with GITHUB_TOKEN starts no workflow run, so the release-event
        # publish path does not fire for this version a second time.
        created = runner(["gh", "release", "create", tag, "--repo", repo, "--target", sha,
                          "--title", f"{name} {version}", "--latest=false",
                          "--notes", f"{name} {version}, published to crates.io from {sha} "
                                     "by trusted publishing."])
        if created.returncode != 0:
            sys.stderr.write(created.stderr)
            raise SystemExit(f"could not create release {tag}")
        print(f"tagged {tag}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--owner", required=True)
    publish = sub.add_parser("publish")
    publish.add_argument("packages")
    tag = sub.add_parser("tag")
    tag.add_argument("packages")
    tag.add_argument("--prefix", required=True)
    tag.add_argument("--sha", required=True)
    tag.add_argument("--repo", required=True)
    tag.add_argument("--publish-outcome", required=True,
                     help="outcome of the publish step: success means every version must be indexed")
    args = parser.parse_args(argv)
    if args.command == "plan":
        write_outputs(command_plan(args.owner))
    elif args.command == "publish":
        command_publish(args.packages.split(","))
    else:
        command_tag(args.packages.split(","), args.prefix, args.sha, args.repo,
                    args.publish_outcome == "success")
    return 0


if __name__ == "__main__":
    sys.exit(main())
