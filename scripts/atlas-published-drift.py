#!/usr/bin/env python3
"""Report which published stack crates carry source their registry copy lacks.

A crate whose manifest version is on crates.io reads as current in every release
check, yet its source can have moved on since: members bump the crate they release,
not the providers whose source changed, and `cargo package --no-verify` resolves
versions without compiling. On 2026-09-30, 100 published crates had drifted this
way and their dependents' releases failed at `cargo publish` verification against
the stale registry copy (ATLAS-PUB-011). This is the measurement that item's
acceptance re-runs.

For every stack member (the `repos/*` paths in atlas's `.gitmodules`) it reads the
member's published default branch tip, never the shared working tree, and reports
for each publishable crate in it (`cargo metadata --no-deps`, `publish` not `[]`):

    status      never-published       the index has no entry for the name
                unpublished-version   the name is published, this version is not
                published-current     the registry `.crate` matches the source
                published-drifted     the registry `.crate` differs from the source
    drift       paths changed, added, or removed since the published version
    dependents  other members' crates whose manifests require this crate, with the
                requirement, kind, and any rename

Comparison: the `.crate` at the manifest version comes from static.crates.io; its
`src/**` and `Cargo.toml.orig` are compared by SHA-256 with `src/**` and `Cargo.toml`
in the crate's directory at the tip. `.cargo_vcs_info.json`, `Cargo.lock`, and the
normalized `Cargo.toml` are ignored, as is anything else outside `src/` and the
manifest (a `build.rs`, a README). Line endings are normalized (CRLF to LF) on both
sides: a crate packaged from a Windows checkout differs from a `git archive` of the
same commit only there, and reading that as drift would send a bump to a crate with
nothing to release. Files marked `export-ignore` are absent from the archive read.

An index 404 is "never published". Every other non-200 answer and every network error
fails the tool: an outage is never read as "not drifted".

Exit status: 0 every crate measured and none drifted; 1 a published crate drifted;
2 the measurement failed (registry, git, or cargo).

    python scripts/atlas-published-drift.py                  # JSON, whole stack
    python scripts/atlas-published-drift.py --format md      # markdown table
    python scripts/atlas-published-drift.py --member hermes --member leto
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import http.client
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zlib
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from atlas_git_process import (  # noqa: E402
    GitProcessError,
    archive as git_archive,
    execute as execute_git,
    execute_process,
    extract_archive,
)
from atlas_stack import ROOT  # noqa: E402


def load_sibling(name: str, path: Path):
    """Import a first-party script whose file name is not a Python identifier."""
    loaded = sys.modules.get(name)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The registry index reader and the publishable-set rule are the push-mode planner's:
# one definition of "has this name and version been published".
crates_pending = load_sibling(
    "crates_pending",
    SCRIPTS.parent / ".github" / "actions" / "crates-pending" / "crates_pending.py",
)
# The member universe and the published-default read are the pin-drift guard's.
pin_drift = load_sibling("atlas_pin_drift", SCRIPTS / "atlas-pin-drift.py")

RegistryError = crates_pending.RegistryError

USER_AGENT = "atlas-published-drift (github.com/ryancinsight/atlas)"
CRATE_URL = "https://static.crates.io/crates/{name}/{name}-{version}.crate"
HTTP_TIMEOUT_SECONDS = 120.0
GIT_TIMEOUT_SECONDS = 300
CARGO_TIMEOUT_SECONDS = 600
DEFAULT_JOBS = 4
# Private ref a missing default tip is fetched into: never a remote-tracking ref
# (ATLAS-ORIGIN-REF-CLOBBER-2026-09-21, scripts/atlas-refspec-guard.py).
SCRATCH_TIP_REF = "refs/scratch/atlas-published-drift"

NEVER_PUBLISHED = "never-published"
UNPUBLISHED_VERSION = "unpublished-version"
PUBLISHED_CURRENT = "published-current"
PUBLISHED_DRIFTED = "published-drifted"
STATUSES = (NEVER_PUBLISHED, UNPUBLISHED_VERSION, PUBLISHED_CURRENT, PUBLISHED_DRIFTED)

Fetch = Callable[[str], "tuple[int, bytes]"]


class MeasurementError(RuntimeError):
    """Git or cargo could not give the answer the measurement needs."""


def http_get(url: str, timeout: float = HTTP_TIMEOUT_SECONDS) -> tuple[int, bytes]:
    """GET with the tool's User-Agent and no other identifying header.

    A non-2xx status is returned, not raised: the index's 404 is an answer.
    Transport failures raise `RegistryError`.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (urllib.error.URLError, OSError, http.client.HTTPException) as error:
        raise RegistryError(f"{url}: {error}") from error


def index_versions(name: str, fetch: Fetch) -> list[str] | None:
    """Versions the index lists for `name`, or None when it was never published."""

    def text(url: str) -> tuple[int, str]:
        status, body = fetch(url)
        return status, body.decode("utf-8")

    return crates_pending.published_versions(name, text)


def version_key(version: str) -> tuple:
    """Order key for crates.io versions: a pre-release sorts below its release."""
    core, _, _build = version.partition("+")
    release, _, pre = core.partition("-")
    numbers = tuple(int(part) if part.isdigit() else 0 for part in release.split("."))
    return (*numbers, 0 if pre else 1, pre)


def normalized_digest(data: bytes) -> str:
    """SHA-256 of `data` with CRLF line endings read as LF."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def published_digests(crate: bytes, name: str, version: str) -> dict[str, str]:
    """Digests of the `.crate`'s `src/**` and `Cargo.toml.orig` (keyed `Cargo.toml`)."""
    prefix = f"{name}-{version}/"
    digests: dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(crate), mode="r:gz") as tree:
            for entry in tree:
                if not entry.isfile():
                    continue
                if not entry.name.startswith(prefix):
                    raise RegistryError(
                        f"{name} {version}: `.crate` entry {entry.name!r} is outside {prefix}"
                    )
                relative = entry.name[len(prefix):]
                if relative == "Cargo.toml.orig":
                    relative = "Cargo.toml"
                elif not relative.startswith("src/"):
                    continue
                handle = tree.extractfile(entry)
                if handle is None:
                    raise RegistryError(f"{name} {version}: cannot read {entry.name}")
                digests[relative] = normalized_digest(handle.read())
    except (tarfile.TarError, gzip.BadGzipFile, EOFError, zlib.error) as error:
        raise RegistryError(f"{name} {version}: unreadable `.crate`: {error}") from error
    return digests


def source_digests(package_dir: Path) -> dict[str, str]:
    """Digests of `src/**` and `Cargo.toml` under one crate directory of an export."""
    digests: dict[str, str] = {}
    source = package_dir / "src"
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if path.is_file():
                digests[path.relative_to(package_dir).as_posix()] = normalized_digest(
                    path.read_bytes()
                )
    digests["Cargo.toml"] = normalized_digest((package_dir / "Cargo.toml").read_bytes())
    return digests


@dataclass(frozen=True)
class Drift:
    """Paths by which the source differs from the registry copy."""

    changed: tuple[str, ...] = ()
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()

    @property
    def drifted(self) -> bool:
        return bool(self.changed or self.added or self.removed)


def compare(published: dict[str, str], source: dict[str, str]) -> Drift:
    """Set-difference and digest comparison of the registry copy against the source."""
    return Drift(
        changed=tuple(sorted(p for p in published.keys() & source.keys()
                             if published[p] != source[p])),
        added=tuple(sorted(source.keys() - published.keys())),
        removed=tuple(sorted(published.keys() - source.keys())),
    )


@dataclass
class CrateReading:
    """One publishable crate at a member's default tip."""

    name: str
    version: str
    manifest: str
    status: str
    latest_published: str | None = None
    drift: Drift | None = None
    dependents: list[dict] = field(default_factory=list)

    def as_json(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "manifest": self.manifest,
            "status": self.status,
            "published": self.status in (PUBLISHED_CURRENT, PUBLISHED_DRIFTED),
            "latest_published": self.latest_published,
            "drift": None if self.drift is None else asdict(self.drift),
            "dependents": self.dependents,
        }


def measure_crate(name: str, version: str, manifest: str, package_dir: Path,
                  fetch: Fetch) -> CrateReading:
    """Classify one crate against the registry; download its `.crate` only if published."""
    versions = index_versions(name, fetch)
    if versions is None:
        return CrateReading(name, version, manifest, NEVER_PUBLISHED)
    latest = max(versions, key=version_key) if versions else None
    if version not in versions:
        return CrateReading(name, version, manifest, UNPUBLISHED_VERSION, latest)
    url = CRATE_URL.format(name=name, version=version)
    status, body = fetch(url)
    if status != 200:
        raise RegistryError(
            f"static.crates.io returned HTTP {status} for {name} {version}, "
            "which the index lists"
        )
    drift = compare(published_digests(body, name, version), source_digests(package_dir))
    return CrateReading(name, version, manifest,
                        PUBLISHED_DRIFTED if drift.drifted else PUBLISHED_CURRENT,
                        latest, drift)


def run_cargo_metadata(manifest: Path) -> dict:
    """`cargo metadata --no-deps` from a directory outside every stack and member config.

    Cargo resolves `.cargo/config.toml` and `rust-toolchain.toml` from the working
    directory, never from `--manifest-path`; a neutral directory excludes the stack's
    overlay and its toolchain pin, neither of which the manifests alone need.
    """
    with tempfile.TemporaryDirectory(prefix="atlas-published-drift-cwd-") as neutral:
        result = execute_process(
            ("cargo", "metadata", "--no-deps", "--format-version", "1",
             "--manifest-path", str(manifest)),
            cwd=Path(neutral),
            timeout=CARGO_TIMEOUT_SECONDS,
        )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise MeasurementError(f"cargo metadata failed for {manifest}: {detail}")
    return json.loads(result.stdout.decode("utf-8"))


@dataclass
class MemberReading:
    name: str
    branch: str
    revision: str
    crates: list[CrateReading]
    packages: list[dict]


def measure_member(name: str, repo: Path, branch: str, revision: str,
                   fetch: Fetch) -> MemberReading:
    """Measure every publishable crate of `repo` at commit `revision`."""
    try:
        tree = git_archive(repo, revision, timeout=GIT_TIMEOUT_SECONDS)
    except GitProcessError as error:
        raise MeasurementError(f"{name}: cannot archive {revision}: {error}") from error
    with tempfile.TemporaryDirectory(prefix=f"atlas-published-drift-{name}-") as scratch:
        root = Path(scratch).resolve()
        extract_archive(tree, root)
        manifest = root / "Cargo.toml"
        if not manifest.is_file():
            raise MeasurementError(f"{name}: no root Cargo.toml at {revision}")
        metadata = run_cargo_metadata(manifest)
        crates = []
        for package in sorted(filter(crates_pending.publishable, metadata["packages"]),
                              key=lambda p: p["name"]):
            package_manifest = Path(package["manifest_path"]).resolve()
            relative = package_manifest.relative_to(root)
            crates.append(measure_crate(package["name"], package["version"],
                                        relative.as_posix(), package_manifest.parent, fetch))
        packages = [
            {"name": p["name"], "dependencies": p["dependencies"]} for p in metadata["packages"]
        ]
    return MemberReading(name, branch, revision, crates, packages)


def reverse_edges(members: Sequence[MemberReading]) -> None:
    """Fill each crate's `dependents` with the other members' manifests requiring it.

    `cargo metadata` reports a dependency by the package's real name and carries the
    alias in `rename`, so a `package = "..."` dependency is matched by the crate it names.
    """
    owner = {crate.name: member.name for member in members for crate in member.crates}
    by_name = {crate.name: crate for member in members for crate in member.crates}
    for member in members:
        for package in member.packages:
            for dependency in package["dependencies"]:
                crate = by_name.get(dependency["name"])
                if crate is None or owner[crate.name] == member.name:
                    continue
                crate.dependents.append({
                    "member": member.name,
                    "crate": package["name"],
                    "requirement": dependency["req"],
                    "kind": dependency.get("kind") or "normal",
                    "rename": dependency.get("rename"),
                })
    for crate in by_name.values():
        crate.dependents.sort(key=lambda d: (d["member"], d["crate"], d["kind"]))


def published_tip(repo: Path, url: str) -> tuple[str, str]:
    """The remote's default branch and its tip, present in `repo`'s object store."""
    branch, tip = pin_drift.published_default(repo, url, GIT_TIMEOUT_SECONDS)
    present = execute_git(repo, ("cat-file", "-e", f"{tip}^{{commit}}"),
                          timeout=GIT_TIMEOUT_SECONDS)
    if present.returncode:
        fetched = execute_git(
            repo, ("fetch", "--no-tags", "--quiet", url, f"+{branch}:{SCRATCH_TIP_REF}"),
            timeout=GIT_TIMEOUT_SECONDS)
        if fetched.returncode:
            detail = fetched.stderr.decode("utf-8", errors="replace").strip()
            raise MeasurementError(f"{repo}: cannot fetch {branch}: {detail}")
    return branch, tip


def measure_stack(root: Path, fetch: Fetch, only: Sequence[str] = (),
                  jobs: int = DEFAULT_JOBS) -> tuple[str, list[MemberReading]]:
    """Measure the members registered in `root`'s `.gitmodules` at their default tips."""
    _branch, atlas_tip = published_tip(root, "origin")
    urls = pin_drift.member_urls(root, atlas_tip, GIT_TIMEOUT_SECONDS)
    unknown = sorted(set(only) - urls.keys())
    if unknown:
        raise MeasurementError(f"not registered members: {', '.join(unknown)}")
    names = sorted(only or urls)

    def one(name: str) -> MemberReading:
        repo = root / "repos" / name
        branch, tip = published_tip(repo, urls[name])
        return measure_member(name, repo, branch, tip, fetch)

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        readings = list(pool.map(one, names))
    reverse_edges(readings)
    return atlas_tip, readings


def summarize(readings: Sequence[MemberReading]) -> dict:
    def counts(crates: Sequence[CrateReading]) -> dict[str, int]:
        found = {"crates": len(crates)}
        for status in STATUSES:
            found[status.replace("-", "_")] = sum(1 for c in crates if c.status == status)
        found["drifted"] = found["published_drifted"]
        return found

    every = [crate for member in readings for crate in member.crates]
    return {**counts(every), "by_member": {m.name: counts(m.crates) for m in readings}}


def report(atlas_tip: str, readings: Sequence[MemberReading]) -> dict:
    return {
        "tool": "atlas-published-drift",
        "atlas_revision": atlas_tip,
        "summary": summarize(readings),
        "members": [
            {
                "name": m.name,
                "branch": m.branch,
                "revision": m.revision,
                "crates": [c.as_json() for c in m.crates],
            }
            for m in readings
        ],
    }


def dependents_cell(dependents: Sequence[dict]) -> str:
    """`member crate req` per distinct dependent, merged per member."""
    per_member: dict[str, list[str]] = {}
    for edge in dependents:
        label = edge["crate"] + (f" as {edge['rename']}" if edge["rename"] else "")
        suffix = "" if edge["kind"] == "normal" else f" ({edge['kind']})"
        per_member.setdefault(edge["member"], []).append(
            f"{label} `{edge['requirement']}`{suffix}")
    return "; ".join(f"{member}: {', '.join(items)}" for member, items in per_member.items())


def render_markdown(document: dict) -> str:
    summary = document["summary"]
    lines = [
        f"Measured at atlas `{document['atlas_revision']}`: {summary['crates']} publishable "
        f"crates, {summary['drifted']} drifted, {summary['never_published']} never published, "
        f"{summary['unpublished_version']} at a version the registry lacks, "
        f"{summary['published_current']} current.",
        "",
        "| member | crates | drifted | never published | unpublished version | current | tip |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    revisions = {m["name"]: (m["branch"], m["revision"]) for m in document["members"]}
    for name, counts in summary["by_member"].items():
        branch, revision = revisions[name]
        lines.append(
            f"| {name} | {counts['crates']} | {counts['drifted']} | "
            f"{counts['never_published']} | {counts['unpublished_version']} | "
            f"{counts['published_current']} | {branch} `{revision[:12]}` |")
    lines += [
        "",
        "| member | crate | manifest version | status | latest on registry | "
        "changed | added | removed | required by |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for member in document["members"]:
        for crate in member["crates"]:
            drift = crate["drift"] or {"changed": [], "added": [], "removed": []}
            lines.append(
                f"| {member['name']} | {crate['name']} | {crate['version']} | {crate['status']} | "
                f"{crate['latest_published'] or ''} | {len(drift['changed'])} | "
                f"{len(drift['added'])} | {len(drift['removed'])} | "
                f"{dependents_cell(crate['dependents'])} |")
    return "\n".join(lines) + "\n"


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--stack-root", type=Path, default=ROOT,
                        help="the atlas checkout whose repos/ hold the members")
    parser.add_argument("--member", action="append", default=[],
                        help="measure only this member (repeatable); reverse edges then "
                             "cover the measured members only")
    parser.add_argument("--format", choices=("json", "md"), default="json")
    parser.add_argument("--output", type=Path, help="write the report here instead of stdout")
    parser.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, fetch: Fetch = http_get) -> int:
    options = parse_arguments(argv)
    try:
        atlas_tip, readings = measure_stack(
            options.stack_root, fetch, options.member, options.jobs)
    except (RegistryError, MeasurementError, GitProcessError) as error:
        print(f"atlas-published-drift: {error}", file=sys.stderr)
        return 2
    document = report(atlas_tip, readings)
    text = (render_markdown(document) if options.format == "md"
            else json.dumps(document, indent=2) + "\n")
    if options.output:
        options.output.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 1 if document["summary"]["drifted"] else 0


if __name__ == "__main__":
    sys.exit(main())
