#!/usr/bin/env python3
"""Advance every consumer's lock to named first-party provider merges.

# The trap this exists for

A provider merge (hermes `6da6d139`, the Linux processor binding) changes
nothing for a consumer until that consumer's `Cargo.lock` moves. Six members
depend on `hermes-simd`; on 2026-09-01 their locks sat at unrelated hermes
revisions and only the one with an acceptance line advanced, by hand. Pin
discipline says allowlisted consumers never sit more than one sweep behind and
that the sweep is a tool, never agent choreography. This is the tool.

# What it does

A sweep names its targets: `--target <provider>=<rev>` per provider merge, or
`--heads` for every registered provider's fetched default-branch head, each
resolved to a full SHA and printed before anything moves. A sweep is a
deliberate act after specific merges -- defaulting to a provider's moving HEAD
churned three consumer locks on a board-only commit the first time that was
exercised.

For each registered member, read from its fetched default branch:

1. Its lock's first-party git sources whose provider is a target and whose
   revision is not the target's are the stale sources. None: the member is
   current.
2. The default branch is exported (`git archive`) into a temporary directory
   outside the stack, so cargo resolves without the `[patch]` overlay, and
   every package of every stale source is updated in one `cargo update`, by
   full package-id spec, then `cargo check --workspace --locked` runs against
   the shared target directory.
3. Every stale source must now sit at its target. A provider whose head moved
   past the named merge -- the sweep's own lock commits in providers move it
   -- is returned to that merge with `cargo update --precise`; a source that
   cannot return is a failed row, never a lock committed at an unnamed
   revision.
4. With `--open-prs`, the new lock blob is committed through a private index
   onto the default branch -- one commit per consumer per sweep, naming each
   provider merge in a `Refs:` line -- pushed from the member through the
   stack's owned pre-push hook, and opened as a pull request with auto-merge
   (`--rebase`: one commit on an unshared branch).

No working tree is created or switched, so a member at its two-worktree bound
is swept like any other: the bound governs lanes, and this tool needs none.

`--retarget-sources` constructs a source-only candidate instead of consulting
provider branch heads. It accepts only an unchanged package graph validated by
full locked offline Cargo metadata, then runs the ordinary native check. Missing
cached commits or graph changes fail; this mode never falls back to an update.

A rerun with the same targets resumes: a member whose sweep branch is already
pushed reports its open PR as pending, or opens the PR an interrupted run did
not, without resolving or pushing again. Each member is fetched again just
before it is planned, so a landed sweep PR reads as current rather than as a
stale base to sweep a second time.

A consumer that cannot advance is a row with its reason, never a silent
omission; the exit status is non-zero if any such row exists. The consumer's
own CI verifies the advance; the `cargo check` catches API breaks before a
runner is spent.
"""

from __future__ import annotations

import argparse
import copy
import json
import tomllib
from collections.abc import Callable
import hashlib
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import lockfile  # noqa: E402  (overlay-free cargo runner; shared, not copied)
from atlas_pull_request import open_pull_request  # noqa: E402
from atlas_stack import (  # noqa: E402
    ROOT, git, load_sibling, registered_member_names, registered_members,
)

stack_overlay = load_sibling("atlas_stack_overlay", SCRIPTS / "atlas-stack-overlay.py")

LOG_ROOT = ROOT / "output" / "lock-sweep"
# A pushed member branch runs the member's whole pre-push gate, which can queue
# on the shared build-identity lease (900 s) before it builds.
PUSH_TIMEOUT_SECONDS = 3000


@dataclass(frozen=True)
class LockedPackage:
    """One `[[package]]` of a lock that resolves through a first-party git source."""

    name: str
    version: str
    url: str
    rev: str

    @property
    def provider(self) -> str:
        return provider_repo_name(self.url)

    @property
    def spec(self) -> str:
        """The package-id spec naming exactly this entry.

        `name@version` alone is ambiguous when one repository is locked under
        two URL spellings (`Mnemosyne` and `Mnemosyne.git`), so the source URL
        is part of the spec."""
        return f"git+{self.url}#{self.name}@{self.version}"


@dataclass(frozen=True)
class Plan:
    """One member's stale first-party sources against the sweep's targets."""

    member: Path
    base: str
    stale: tuple[LockedPackage, ...]

    @property
    def name(self) -> str:
        return self.member.name

    def providers(self) -> list[str]:
        return sorted({package.provider for package in self.stale})


@dataclass(frozen=True)
class Outcome:
    """What the sweep did, or could not do, for one member."""

    member: str
    action: str
    detail: str
    ok: bool


@dataclass(frozen=True)
class RevisionCheck:
    revision: str
    reports: tuple[str, ...]
    problems: tuple[str, ...]
    locks: int


RevisionTarget = tuple[str, dict[str, frozenset[str | None]]]

# --- pure functions (unit-tested) ---------------------------------------------


class SourceOperation(Enum):
    """How provider revisions and their lock representation change."""

    UPDATE = "update"
    RETARGET = "retarget"

    def lock_bytes(self, base: bytes, updated: bytes) -> bytes:
        """Keep a validated retarget exact; format a generated update like its base."""
        return (updated if self is SourceOperation.RETARGET
                else with_line_endings_of(base, updated))


def normalize_repo_url(url: str) -> str:
    """Canonical provider URL: lower-case, without query or `.git`."""
    base = url.split("?", 1)[0].rstrip("/")
    if base.lower().endswith(".git"):
        base = base[:-4]
    return base.lower()


def provider_repo_name(url: str) -> str:
    """The stack member a first-party URL refers to, lower-case."""
    return normalize_repo_url(url).rsplit("/", 1)[-1]


def revision_lock_findings(
    member: str,
    lock: str,
    lock_text: str,
    targets: dict[str, RevisionTarget],
    path_fixture: bool,
) -> tuple[str, list[str]]:
    """Report one measured lock and every source identity mismatch it contains."""
    label = f"{member}/{lock}"
    try:
        identities = locked_packages(lock_text)
    except ValueError as error:
        return f"{label}: measured 0 first-party package(s)", [f"{label}: {error}"]
    findings: list[str] = []
    if path_fixture:
        report = f"{label}: path fixture ({len(identities)} first-party Git identities)"
        findings = [
            f"{label}: path-unification required for {identity.name}: "
                f"{identity.provider}@{identity.rev} cannot be judged against a gitlink while sibling "
                "dependencies remain paths"
            for identity in identities
        ]
        return report, findings
    for identity in identities:
        target = targets.get(identity.provider)
        if target is None:
            findings.append(f"{label}: {identity.name} uses unknown registered first-party "
                            f"identity {identity.provider}@{identity.rev}")
            continue
        if identity.rev != target[0]:
            findings.append(f"{label}: {identity.name} locks {identity.provider}@{identity.rev}; "
                            f"selected {target[0]}")
        versions = target[1].get(identity.name)
        if versions is None:
            findings.append(f"{label}: selected {identity.provider} does not define "
                            f"package {identity.name} with a readable version")
        elif identity.version not in versions:
            declared = ", ".join(sorted(version or "<unreadable>" for version in versions))
            findings.append(f"{label}: {identity.name} locks version {identity.version}; "
                            f"selected {identity.provider} manifests declare {declared}")
    state = "measured" if findings else "aligned"
    return f"{label}: {state} {len(identities)} first-party package(s)", findings


def committed_member_names(repository: Path, selected: str) -> set[str]:
    """Read every submodule path from one committed `.gitmodules`."""
    try:
        configuration = git(
            repository, "config", "--no-includes", "--blob",
            f"{selected}:.gitmodules", "--null", "--list",
        )
    except RuntimeError as error:
        raise RuntimeError(f"cannot parse .gitmodules at {selected}: {error}") from error
    fields: dict[str, dict[str, list[str]]] = {}
    for record in configuration.split("\0"):
        if not record:
            continue
        key, separator, value = record.partition("\n")
        if not separator:
            raise RuntimeError(f"unreadable Git config record in .gitmodules at {selected}")
        match = re.fullmatch(r"submodule\.(.+)\.([^.]+)", key, re.IGNORECASE)
        if match is None:
            continue
        section, field = match.groups()
        fields.setdefault(section, {}).setdefault(field.lower(), []).append(value)
    if not fields:
        raise RuntimeError(f"no registered members in .gitmodules at {selected}")

    names: set[str] = set()
    identities: set[str] = set()
    for section in sorted(fields):
        for required in ("path", "url"):
            values = fields[section].get(required, [])
            if len(values) != 1 or not values[0]:
                multiple = len(values) > 1
                state, field = ("multiple", f"{required}s") if multiple else ("no", required)
                raise RuntimeError(f"submodule {section!r} has {state} {field} "
                                   f"in .gitmodules at {selected}")
        path = fields[section]["path"][0]
        parts = path.split("/")
        if len(parts) != 2 or parts[0] != "repos":
            raise RuntimeError(f"unsupported submodule path {path!r} in .gitmodules at {selected}")
        name = parts[1]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            raise RuntimeError(f"unsafe registered member name {name!r}")
        identity = name.lower()
        if identity in identities:
            raise RuntimeError(f"duplicate registered submodule path repos/{name} at {selected}")
        identities.add(identity)
        names.add(name)

    return names


def selected_gitlinks(repository: Path, revision: str) -> tuple[str, dict[str, tuple[str, str, Path]]]:
    """Resolve one meta revision and its complete registered gitlink set."""
    selected = git(repository, "rev-parse", "--verify", f"{revision}^{{commit}}").strip()
    names = committed_member_names(repository, selected)
    links: dict[str, tuple[str, str, Path]] = {}
    for line in git(repository, "ls-tree", "-r", selected).splitlines():
        metadata, _, path = line.partition("\t")
        fields = metadata.split()
        if len(fields) != 3 or fields[:2] != ["160000", "commit"]:
            continue
        parts = path.split("/")
        if len(parts) != 2 or parts[0] != "repos":
            raise RuntimeError(f"unsupported gitlink {path} at {selected}")
        name = parts[1]
        if name not in names:
            raise RuntimeError(f"unregistered gitlink repos/{name} at {selected}")
        local = repository / path
        if not local.is_dir():
            raise RuntimeError(f"registered member {name} has no local object repository")
        top_level = Path(git(local, "rev-parse", "--show-toplevel").strip()).resolve()
        if top_level != local.resolve():
            raise RuntimeError(f"registered member {name} has no independent object repository")
        links[name.lower()] = (name, fields[2], local)
    missing = sorted(name for name in names if name.lower() not in links)
    if missing:
        raise RuntimeError(f"registered member {missing[0]} has no gitlink at {selected}")
    return selected, links


def check_revision(repository: Path, revision: str) -> RevisionCheck:
    """Judge every committed member lock against one exact meta revision."""
    try:
        selected, links = selected_gitlinks(repository, revision)
    except (RuntimeError, lockfile.GitUnavailable) as error:
        return RevisionCheck("unresolved", (), (f"meta revision {revision}: {error}",), 0)
    reports, problems = [], []
    measured = 0
    selected_texts: dict[str, dict[str, str]] = {}
    targets = {provider: (pin, {}) for provider, (_, pin, _) in links.items()}
    for provider in sorted(links):
        name, pin, member = links[provider]
        try:
            texts = lockfile.tracked_texts(member, staged=False, revision=pin)
        except lockfile.GitUnavailable as error:
            problems.append(f"{name}@{pin}: selected object cannot be read: {error}")
            continue
        selected_texts[provider] = texts
        manifests = [(PurePosixPath(path).parent, text) for path, text in texts.items()
                     if path.endswith("Cargo.toml")]
        try:
            facts = stack_overlay.load_package_facts(manifests)
        except ValueError as error:
            problems.append(f"{name}@{pin}: package facts cannot be read: {error}")
            continue
        targets[provider] = (pin, stack_overlay.package_versions(facts))
    for provider in sorted(selected_texts):
        name, pin, _ = links[provider]
        texts = selected_texts[provider]
        locks = sorted(path for path in texts if Path(path).name == "Cargo.lock")
        if not locks:
            problems.append(f"{name}@{pin}: no committed Cargo.lock")
            continue
        if "Cargo.lock" not in locks: problems.append(f"{name}@{pin}: no committed root Cargo.lock")
        for lock in locks:
            manifest = (PurePosixPath(lock).parent / "Cargo.toml").as_posix()
            if manifest not in texts:
                problems.append(f"{name}/{lock}: workspace has no committed Cargo.toml")
        standalone, fixtures = lockfile.judge_locks(texts, locks)
        problems.extend(f"{name}/{problem}" for problem in standalone)
        fixture_set = set(fixtures)
        for lock in locks:
            report, findings = revision_lock_findings(
                name, lock, texts[lock], targets, lock in fixture_set
            )
            reports.append(report)
            problems.extend(findings)
            measured += 1
    return RevisionCheck(selected, tuple(reports), tuple(sorted(set(problems))), measured)


def print_revision_check(result: RevisionCheck) -> int:
    """Print revision evidence in stable member/lock order."""
    print(f"selected meta revision: {result.revision}")
    for report in result.reports:
        print(report)
    for problem in result.problems:
        print(f"COHERENCE VIOLATION: {problem}", file=sys.stderr)
    print(f"checked {result.locks} committed lock(s)")
    return 1 if result.problems else 0
def supported_first_party_location(location: str, package_index: int) -> bool:
    """Whether a Git location has the supported first-party authority and path."""
    try:
        parsed = urlsplit(location)
    except ValueError:
        return False
    if (parsed.hostname or "").lower() != "github.com":
        return False

    owner = next((component for component in parsed.path.split("/") if component), None)
    if owner is None or unquote(owner).lower() != "ryancinsight":
        return False
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in location):
        raise ValueError(
            f"lock package {package_index} has unreadable first-party Git source identity"
        )
    if owner.lower() != "ryancinsight":
        raise ValueError(
            f"lock package {package_index} has unsupported first-party Git source path"
        )
    if parsed.scheme.lower() != "https" or parsed.username is not None or parsed.password is not None:
        raise ValueError(
            f"lock package {package_index} has unsupported first-party Git source authority"
        )
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(
            f"lock package {package_index} has unreadable first-party Git source authority"
        ) from error
    if port not in (None, 443):
        raise ValueError(
            f"lock package {package_index} has unsupported first-party Git source authority"
        )
    if not re.fullmatch(
        r"/ryancinsight/[A-Za-z0-9][A-Za-z0-9._-]*/?",
        parsed.path,
        re.IGNORECASE | re.ASCII,
    ):
        raise ValueError(
            f"lock package {package_index} has unreadable first-party Git source identity"
        )
    return True


def locked_packages(lock_text: str) -> list[LockedPackage]:
    """Read every complete Git identity in the supported first-party namespace."""
    locked: list[LockedPackage] = []
    for index, package in enumerate(lockfile.locked_package_records(lock_text)):
        source = package.get("source")
        if not isinstance(source, str):
            continue
        if not source.lower().startswith("git+"):
            continue
        payload = source[4:]
        location, separator, revision = payload.rpartition("#")
        candidate = location if separator else payload
        if not supported_first_party_location(candidate, index):
            continue
        if not separator or "#" in location or not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
            raise ValueError(
                f"lock package {index} has unreadable first-party Git source identity"
            )
        locked.append(
            LockedPackage(package["name"], package["version"], location, revision.lower())
        )
    return locked


def first_party_packages(lock_text: str) -> list[LockedPackage]:
    """First-party packages update mode may move: explicit query pins excluded."""
    return [package for package in locked_packages(lock_text) if "?" not in package.url]


def stale_packages(lock_text: str, targets: dict[str, str],
                   read_packages: Callable[[str], list[LockedPackage]] = first_party_packages
                   ) -> tuple[LockedPackage, ...]:
    """The first-party entries whose provider is a target they are not at."""
    return tuple(
        package
        for package in read_packages(lock_text)
        if package.provider in targets and package.rev != targets[package.provider]
    )


def pullbacks(lock_text: str, stale: tuple[LockedPackage, ...], targets: dict[str, str]) -> list[tuple[str, str]]:
    """One `(package spec, target)` per stale source cargo resolved past its target.

    An unpinned update resolves every stale source at its provider's branch
    head, which moves on during a sweep -- the sweep's own lock commits in
    providers move it. `--precise` on any one package of a git source moves the
    whole source, so each one returns to its named merge with one call."""
    sources = {(package.url, package.provider) for package in stale}
    chosen: dict[str, tuple[str, str]] = {}
    for package in first_party_packages(lock_text):
        target = targets.get(package.provider)
        if (package.url, package.provider) in sources and package.rev != target:
            chosen.setdefault(package.url, (package.spec, target))
    return [chosen[url] for url in sorted(chosen)]


def unmet_targets(lock_text: str, stale: tuple[LockedPackage, ...], targets: dict[str, str]) -> list[str]:
    """Stale sources the updated lock still does not resolve at their target.

    Cargo resolves an unpinned git source at the branch head it fetches. When
    that head moved past the named merge, the lock would record a revision the
    sweep never named; that is reported, not committed."""
    sources = {(package.url, package.provider) for package in stale}
    misses = []
    for package in first_party_packages(lock_text):
        if (package.url, package.provider) in sources and package.rev != targets[package.provider]:
            misses.append(
                f"{package.name} resolved {package.rev[:8]}, target "
                f"{package.provider}@{targets[package.provider][:8]}"
            )
    return sorted(set(misses))


def failure_detail(member_name: str, stage: str, stderr: str) -> str:
    """Name the failure, and keep the whole diagnostic on disk.

    A cargo resolver error states the unsatisfiable requirement on its first
    `error:` line and spends the remaining lines narrating the dependency
    chain that reached it. Reporting the *last* line therefore named the far
    end of that chain -- "which satisfies git dependency `hephaestus-wgpu`
    (locked to 0.19.0)" -- and every conflict read as a mystery about a
    package that was not the constraint. The first error line is the
    constraint; the rest is written beside it so the chain is still readable.
    """
    lines = stderr.strip().splitlines()
    head = next((line.strip() for line in lines if line.strip().startswith("error")), "")
    if not head:
        head = lines[-1].strip() if lines else "no diagnostic"
    slug = stage.replace(" ", "-")
    log = LOG_ROOT / f"{member_name}-{slug}.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(stderr, encoding="utf-8")
        return f"{stage}: {head} [full: {log.relative_to(ROOT).as_posix()}]"
    except OSError:
        return f"{stage}: {head}"


def coauthor() -> str:
    """The agent this run should be attributed to.

    The trailer names who wrote the commit, and the commit is written by
    whichever agent invokes the sweep -- not by whichever one wrote this
    template. `ATLAS_SWEEP_COAUTHOR` carries it; the default keeps the
    original attribution for a run that does not set it.
    """
    return os.environ.get(
        "ATLAS_SWEEP_COAUTHOR", "Claude Fable 5.1 <noreply@anthropic.com>"
    )


def branch_name(targets: dict[str, str]) -> str:
    """One branch per sweep: the provider and revision when there is one
    target, a digest of the whole target set otherwise."""
    if len(targets) == 1:
        (provider, rev), = targets.items()
        return f"build/deps-{provider}-{rev[:8]}"
    digest = hashlib.sha1(
        "".join(f"{p}={r}\n" for p, r in sorted(targets.items())).encode()
    ).hexdigest()[:8]
    return f"build/deps-lock-sweep-{digest}"


def commit_message(plan: Plan, targets: dict[str, str], item: str | None) -> str:
    providers = plan.providers()
    if len(providers) == 1:
        subject = f"build(deps): Update {providers[0]} to {targets[providers[0]][:8]}"
    else:
        subject = "build(deps): Advance first-party locks"
    refs = "".join(f"Refs: {provider}@{targets[provider]}\n" for provider in providers)
    trailer = f"Item: {item}\n" if item else ""
    return (
        f"{subject}\n\n"
        "Advances each first-party git source below to its named provider\n"
        "merge. Resolved outside the stack overlay; `cargo check --workspace\n"
        "--locked` passed before the push. Opened by scripts/atlas-lock-sweep.py.\n\n"
        f"{refs}{trailer}Co-Authored-By: {coauthor()}"
    )


def with_line_endings_of(base: bytes, updated: bytes) -> bytes:
    """`updated` in the line-ending convention of the committed `base`.

    The export is written through the checkout filters, so on Windows cargo
    may read CRLF; the commit must not turn a one-line advance into a
    whole-file rewrite."""
    lf = updated.replace(b"\r\n", b"\n")
    return lf.replace(b"\n", b"\r\n") if b"\r\n" in base else lf


def render_report(targets: dict[str, str], rows: list[Outcome]) -> str:
    named = ", ".join(f"{p}@{r[:8]}" for p, r in sorted(targets.items()))
    width = max((len(o.member) for o in rows), default=8)
    lines = [f"lock sweep -> {named}", f"{'member':<{width}}  action    detail"]
    lines += [f"{o.member:<{width}}  {o.action:<8}  {o.detail}" for o in rows]
    return "\n".join(lines)


# --- repository operations ---------------------------------------------------


def default_branch(member: Path) -> str:
    ref = git(member, "symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
    return ref.removeprefix("origin/") if ref else "main"


def resolve_targets(members: list[Path], requested: list[str], heads: bool) -> dict[str, str]:
    """Provider name -> full SHA of the merge the sweep advances to."""
    by_name = {member.name.lower(): member for member in members}
    wanted: dict[str, str] = {}
    if heads:
        for name, member in by_name.items():
            wanted[name] = f"origin/{default_branch(member)}"
    for entry in requested:
        provider, _, rev = entry.partition("=")
        if not rev or provider.lower() not in by_name:
            sys.exit(f"error: --target {entry!r} is not <registered provider>=<rev>")
        wanted[provider.lower()] = rev
    targets = {}
    for provider, rev in wanted.items():
        full = git(by_name[provider], "rev-parse", "--verify", f"{rev}^{{commit}}").strip()
        targets[provider] = full
    return targets


def plan_member(member: Path, targets: dict[str, str],
                read_packages: Callable[[str], list[LockedPackage]] = first_party_packages
                ) -> Plan | None:
    """The member's stale sources at its fetched default branch; None without a lock."""
    base = git(member, "rev-parse", "--verify", f"origin/{default_branch(member)}^{{commit}}").strip()
    try:
        lock_text = git(member, "show", f"{base}:Cargo.lock")
    except RuntimeError:
        return None
    return Plan(member, base, stale_packages(lock_text, targets, read_packages))


def export_tree(member: Path, base: str, directory: Path) -> None:
    archive = directory / "tree.tar"
    subprocess.run(
        ["git", "-C", str(member), "archive", "--format=tar", "-o", str(archive), base],
        check=True, capture_output=True,
    )
    with tarfile.open(archive) as tree:
        tree.extractall(directory / "tree", filter="data")
    archive.unlink()


def owned_hooks(directory: Path) -> Path:
    """The stack's owned hooks at its fetched default branch.

    A member's configured hooks path names the stack checkout, which sits on
    whatever branch a peer left there, often with a dirty or stale hook."""
    archive = directory / "hooks.tar"
    subprocess.run(
        ["git", "-C", str(ROOT), "archive", "--format=tar", "-o", str(archive),
         f"origin/{default_branch(ROOT)}", "scripts/git-hooks"],
        check=True, capture_output=True,
    )
    with tarfile.open(archive) as hooks:
        hooks.extractall(directory, filter="data")
    return directory / "scripts" / "git-hooks"


def commit_lock(member: Path, base: str, lock: bytes, message: str, scratch: Path) -> str:
    """Commit `lock` as the member's `Cargo.lock` on top of `base`, without a checkout."""
    environment = {**os.environ, "GIT_INDEX_FILE": str(scratch / "index")}

    def plumbing(*arguments: str, data: bytes | None = None) -> str:
        done = subprocess.run(
            ["git", "-C", str(member), *arguments],
            input=data, env=environment, capture_output=True, check=True,
            timeout=lockfile.GIT_DEADLINE_SECONDS,
        )
        return done.stdout.decode().strip()

    plumbing("read-tree", base)
    blob = plumbing("hash-object", "-w", "--no-filters", "--stdin", data=lock)
    plumbing("update-index", "--cacheinfo", f"100644,{blob},Cargo.lock")
    tree = plumbing("write-tree")
    return plumbing("commit-tree", tree, "-p", base, "-F", "-", data=message.encode())


def cargo(tree: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return lockfile.run_outside_the_overlay(list(arguments), manifest=tree / "Cargo.toml")
    except lockfile.CargoDeadlineExceeded as error:
        # The sweep reports a row per failure from `returncode`/`stderr`; a
        # deadline is a failed row like any other, with the runner's note as
        # the detail.
        return subprocess.CompletedProcess(error.cmd, 124, "", str(error))


def retarget_sources(text: str, revisions: dict[str, str]) -> str:
    """Change only existing unqueried Git source revision fields.

    Package/dependency records remain identical apart from their source SHA.
    This constructs a candidate; locked offline Cargo metadata must establish
    that the selected commits still resolve the unchanged package graph.
    """
    records = lockfile.locked_package_records(text)
    sources = {record.get("source") for record in records}
    replacements = {}
    for source, revision in revisions.items():
        location, separator, old = source.rpartition("#")
        if (source not in sources or not location.startswith("git+") or not separator
                or "?" in location or not re.fullmatch(r"[0-9a-fA-F]{40}", old)
                or not re.fullmatch(r"[0-9a-fA-F]{40}", revision)):
            raise ValueError("retargeting requires an existing unqueried Git identity and full SHA")
        replacements[source] = location + "#" + revision.lower()
    expected = copy.deepcopy(tomllib.loads(text))
    for package in expected.get("package", []):
        if package.get("source") in replacements:
            package["source"] = replacements[package["source"]]
    pattern = re.compile(r"""(?m)^([ \t]*source[ \t]*=[ \t]*)(["'])([^"'\r\n]*)\2""")
    candidate = pattern.sub(
        lambda match: (match[1] + match[2] + replacements[match[3]] + match[2]
                       if match[3] in replacements else match[0]), text)
    if tomllib.loads(candidate) != expected:
        raise ValueError("source retargeting cannot preserve this lock representation")
    return candidate


def retarget_lock(plan: Plan, targets: dict[str, str], tree: Path) -> Outcome | None:
    """Validate an exact-source candidate in the sweep's private export.

    No floating update runs. A changed package graph, unavailable cached commit,
    missing selected package, or Cargo lock write rejects the candidate.
    """
    lock = tree / "Cargo.lock"
    try:
        original = lock.read_bytes().decode("utf-8")
        revisions = {f"git+{package.url}#{package.rev}": targets[package.provider]
                     for package in plan.stale}
        candidate = retarget_sources(original, revisions).encode("utf-8")
    except (OSError, UnicodeError, ValueError) as error:
        return Outcome(plan.name, "failed", f"source retargeting: {error}", False)
    lock.write_bytes(candidate)
    metadata = cargo(tree, "metadata", "--locked", "--offline", "--all-features",
                     "--format-version", "1")
    if metadata.returncode:
        return Outcome(plan.name, "failed", failure_detail(
            plan.name, "locked offline metadata", metadata.stderr), False)
    if lock.read_bytes() != candidate:
        return Outcome(plan.name, "failed", "Cargo rewrote the source-only candidate", False)
    try:
        packages = {(package["name"], package["version"], package.get("source"))
                    for package in json.loads(metadata.stdout)["packages"]}
    except (KeyError, TypeError, ValueError) as error:
        return Outcome(plan.name, "failed", f"unreadable Cargo metadata: {error}", False)
    for package in plan.stale:
        source = f"git+{package.url}#{targets[package.provider]}"
        if (package.name, package.version, source) not in packages:
            return Outcome(plan.name, "failed", "selected package absent from locked metadata: "
                           + package.name + " " + package.version, False)
    return None


def resolve_lock(plan: Plan, targets: dict[str, str], tree: Path) -> Outcome | None:
    """Advance the exported lock's stale sources to their targets; a failed row, or None."""
    specs = sorted({package.spec for package in plan.stale})
    update = cargo(tree, "update", *(flag for spec in specs for flag in ("--package", spec)))
    if update.returncode != 0:
        return Outcome(plan.name, "failed", failure_detail(plan.name, "cargo update", update.stderr), False)
    # A precise update of one source re-resolves the git sources its packages
    # depend on, which can carry an already-returned source past its target
    # again; a round per source bounds the repetition.
    for _round in range(len({package.url for package in plan.stale}) + 1):
        resolved = (tree / "Cargo.lock").read_text(encoding="utf-8", errors="replace")
        returns = pullbacks(resolved, plan.stale, targets)
        if not returns:
            break
        for spec, target in returns:
            precise = cargo(tree, "update", "--package", spec, "--precise", target)
            if precise.returncode != 0:
                return Outcome(plan.name, "failed", failure_detail(plan.name, "cargo update --precise", precise.stderr), False)
    resolved = (tree / "Cargo.lock").read_text(encoding="utf-8", errors="replace")
    misses = unmet_targets(resolved, plan.stale, targets)
    if misses:
        return Outcome(plan.name, "failed", "source past its target: " + "; ".join(misses), False)
    return None


def advance(plan: Plan, targets: dict[str, str], hooks: Path | None, item: str | None,
            operation: SourceOperation = SourceOperation.UPDATE) -> Outcome:
    if operation is SourceOperation.UPDATE:
        resumed = resume(plan, targets, item, hooks is not None)
        if resumed is not None:
            return resumed
    member = plan.member
    with tempfile.TemporaryDirectory(prefix=f"lock-sweep-{plan.name}-") as scratch_name:
        scratch = Path(scratch_name)
        export_tree(member, plan.base, scratch)
        tree = scratch / "tree"
        resolver = retarget_lock if operation is SourceOperation.RETARGET else resolve_lock
        failure = resolver(plan, targets, tree)
        if failure is not None:
            return failure
        updated = (tree / "Cargo.lock").read_bytes()
        check = cargo(tree, "check", "--workspace", "--locked")
        if check.returncode != 0:
            return Outcome(plan.name, "failed", failure_detail(plan.name, "cargo check", check.stderr), False)
        if operation is SourceOperation.RETARGET and (tree / "Cargo.lock").read_bytes() != updated:
            return Outcome(plan.name, "failed", "native check rewrote the exact source candidate", False)
        moved = ", ".join(plan.providers())
        if hooks is None:
            return Outcome(plan.name, "would", f"{moved} (dry run; check passed)", True)
        base_lock = subprocess.run(
            ["git", "-C", str(member), "show", f"{plan.base}:Cargo.lock"],
            capture_output=True, check=True,
        ).stdout
        commit = commit_lock(
            member, plan.base, operation.lock_bytes(base_lock, updated),
            commit_message(plan, targets, item), scratch,
        )
        branch = branch_name(targets)
        try:
            pushed = subprocess.run(
                ["git", "-C", str(member), "-c", f"core.hooksPath={hooks}",
                 "push", "origin", f"{commit}:refs/heads/{branch}"],
                capture_output=True, encoding="utf-8", errors="replace",
                timeout=PUSH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return Outcome(plan.name, "failed", f"push: no verdict within {PUSH_TIMEOUT_SECONDS} s", False)
        if pushed.returncode != 0:
            return Outcome(plan.name, "failed", failure_detail(plan.name, "push", pushed.stderr), False)
        return open_sweep_pull_request(plan, targets, item, branch)


def open_sweep_pull_request(plan: Plan, targets: dict[str, str], item: str | None, branch: str) -> Outcome:
    refs = ", ".join(f"`{p}@{targets[p]}`" for p in plan.providers())
    body = (
        f"Advances this member's first-party lock entries to the named provider merges: "
        f"{refs}.\n\nResolved outside the stack overlay; `cargo check --workspace --locked` "
        "passed before the push. Opened by `scripts/atlas-lock-sweep.py`.\n\n"
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
    )
    title = commit_message(plan, targets, item).splitlines()[0]
    opening = open_pull_request(
        base=default_branch(plan.member), head=branch, title=title, body=body,
        cwd=plan.member, method="rebase",
    )
    if opening.failure is not None:
        return Outcome(plan.name, "failed", opening.failure, False)
    return Outcome(plan.name, "opened", opening.url or "", True)


def resume(plan: Plan, targets: dict[str, str], item: str | None, open_prs: bool) -> Outcome | None:
    """The member's row when this sweep already pushed its branch, else None.

    A sweep is rerun with the same named targets after an interrupted run, so
    its branch name is the same. A second commit to that branch would be
    rejected as non-fast-forward after the whole check had run, and a run
    interrupted between push and PR left a branch nobody collects."""
    branch = branch_name(targets)
    if not git(plan.member, "ls-remote", "origin", f"refs/heads/{branch}").strip():
        return None
    listed = subprocess.run(
        ["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "url", "--jq", ".[].url"],
        cwd=plan.member, capture_output=True, encoding="utf-8", errors="replace",
    )
    if listed.returncode != 0:
        return Outcome(plan.name, "failed", f"gh pr list: {listed.stderr.strip()[-200:]}", False)
    url = listed.stdout.strip()
    if url:
        return Outcome(plan.name, "pending", f"{url} (pushed by an earlier run of this sweep)", True)
    if not open_prs:
        return Outcome(plan.name, "would", f"open a PR for the pushed {branch}", True)
    return open_sweep_pull_request(plan, targets, item, branch)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--target", action="append", default=[], metavar="PROVIDER=REV",
        help="a provider merge to advance consumers to, e.g. hermes=6da6d139; repeatable",
    )
    parser.add_argument(
        "--heads", action="store_true",
        help="target every registered provider's fetched default-branch head (printed before any change)",
    )
    parser.add_argument(
        "--check-revision", metavar="META_REF",
        help="read-only check of every committed member lock at an exact meta revision",
    )
    parser.add_argument("--members", help="comma-separated member names to restrict the sweep to")
    parser.add_argument("--item", help="board item ID for the commits' Item: trailer")
    parser.add_argument("--open-prs", action="store_true", help="commit, push, and open one PR per consumer (default: dry run)")
    parser.add_argument("--retarget-sources", action="store_true",
                        help="preserve the package graph and validate exact source SHAs offline")
    arguments = parser.parse_args()
    if arguments.check_revision is not None:
        if (arguments.target or arguments.heads or arguments.members or arguments.item
                or arguments.open_prs or arguments.retarget_sources):
            parser.error("--check-revision cannot be combined with sweep/update options")
        return print_revision_check(check_revision(ROOT, arguments.check_revision))
    if arguments.retarget_sources and arguments.heads:
        parser.error("--retarget-sources requires explicit --target revisions, not --heads")
    if not arguments.target and not arguments.heads:
        parser.error("name the merges: --target PROVIDER=REV (repeatable) or --heads")

    members = registered_members()
    for member in members:
        git(member, "fetch", "origin", "--quiet")
    targets = resolve_targets(members, arguments.target, arguments.heads)
    print("targets: " + ", ".join(f"{p}@{r}" for p, r in sorted(targets.items())), flush=True)

    # Exports live outside the stack, where no config names the shared target
    # directory; the member's own position in the stack does.
    if "CARGO_TARGET_DIR" not in os.environ:
        shared = lockfile.shared_target_dir(ROOT / "Cargo.toml")
        if shared is None:
            sys.exit("error: no stack config names build.target-dir; refusing to fork the cache")
        os.environ["CARGO_TARGET_DIR"] = str(shared)

    operation = SourceOperation.RETARGET if arguments.retarget_sources else SourceOperation.UPDATE
    consumers = members
    if arguments.members:
        wanted = set(arguments.members.split(","))
        consumers = [m for m in members if m.name in wanted]

    outcomes: list[Outcome] = []
    with tempfile.TemporaryDirectory(prefix="lock-sweep-hooks-") as hooks_dir:
        hooks = None
        if arguments.open_prs:
            git(ROOT, "fetch", "origin", "--quiet")
            hooks = owned_hooks(Path(hooks_dir))
        for member in consumers:
            # A sweep outlives many merges: a base fetched when it started
            # predates its own earlier members' landings and any peer's.
            git(member, "fetch", "origin", "--quiet")
            plan = plan_member(member, targets,
                               locked_packages if operation is SourceOperation.RETARGET else first_party_packages)
            if plan is None:
                outcomes.append(Outcome(member.name, "current", "no Cargo.lock", True))
            elif not plan.stale:
                outcomes.append(Outcome(member.name, "current", "every targeted source at its target", True))
            else:
                outcomes.append(
                    advance(plan, targets, hooks, arguments.item,
                            operation)
                )
            print(render_report(targets, outcomes[-1:]).splitlines()[-1], flush=True)
    print(render_report(targets, outcomes))
    return 0 if all(o.ok for o in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
