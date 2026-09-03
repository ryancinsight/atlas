#!/usr/bin/env python3
"""Scripted conformance scan: the mechanical form of the AGENTS.md debt classes.

AGENTS.md `engineering_gates` (lint floor) mandates a scripted scan that
enumerates every measured debt class per repo and holds the counts under a
non-increasing ratchet; until now the recorded baseline (backlog
ATLAS-HYGIENE-BASELINE-001) came from ad-hoc greps with no committed
instrument. This script is that instrument. Beyond the eleven recorded
classes it covers the mechanically checkable rules that previously had no
enforcement: line-ending policy (`.gitattributes`), committed nextest
budgets, `[workspace.lints]` inheritance, sleep-synced tests, commented-out
code, repo-local target forks, and alias re-export shims.

Heuristics are deliberately simple and stable — the ratchet compares this
instrument against itself, so consistency outranks per-class perfection;
changing a detector regenerates the baseline in the same change (generator
contract, AGENTS.md architecture_scoping).

Workflow files are additionally checked for structural validity, not just
string hygiene: a workflow that does not parse as YAML — or that repeats a
mapping key like `name:` — is rejected by GitHub Actions, so it is counted
as `workflow_malformed_yaml` rather than silently passing the substring
scans. This is the class that lets a duplicate `name:` key reach a shared
release pipeline, which is the downstream cost this class exists to avoid.

A large `LaneKernel::call` body that is not `#[inline(always)]` is counted
as `lane_kernel_uninlined`. The `#[runtime_dispatch]` expansion inlines the
feature-carrying helper into a *small* body but declines for a large one, so
the body codegens at the baseline ISA — the ~30x cost hermes
`HS-VECTORIZE-LARGE-KERNEL-2026-08-28` documents. The detector is a
line-count heuristic over the body; it is the mechanized form of the manual
brace-match census so the class cannot be reintroduced silently.

Modes:
    report      per-repo x per-class table (default)
    generate    write scripts/conformance-baseline.json from the clean HEAD
                revision (or the live tree with --worktree)
    check       re-scan and fail (exit 1) on any per-repo class increase
                over the committed baseline; decreases print as tightening
                candidates for a baseline update in the same change. With
                --json, emit an object containing the scan results,
                regressions, and tightenings without human-readable lines.

Run from anywhere: paths are anchored to this file's parent repository.
The default scan requires a clean checkout whose provider gitlinks match the
requested root revision. Use --worktree only for an intentional dirty-tree
audit; such a result is not a reproducible gate input. Both modes require every
registered provider checkout to be materialized so an empty gitlink directory
cannot be mistaken for a zero-debt repository.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - optional for environments without PyYAML
    _yaml = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import ROOT, is_git_ignored, staleness_note

BASELINE = ROOT / "scripts" / "conformance-baseline.json"

PRUNE_DIRS = {
    ".git", "worktrees", "__pycache__", "node_modules", ".claude", "book",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", ".tox", ".nox", ".venv",
    "venv",
    # Ad-hoc diagnostic workspaces (`fn main()` programs run by hand, not on
    # CI). Carrying them as production code would inflate `print_dbg` and
    # related classes by diagnostic `println!` calls that the ratchet cannot
    # otherwise distinguish from library output. RITK and Hermes hold one;
    # exclude by convention.
    "scratch",
}
TEST_PATH_PARTS = {"tests", "benches", "examples", "fuzz"}


def _is_testish_path_part(part: str) -> bool:
    """True for a path component naming test code.

    Beyond the canonical directories, sidecar modules follow the
    `<module>_tests` convention in both forms the stack uses: the file
    (`cfft_tests.rs`) and the directory holding such files
    (`apollo-fft/src/lib_tests/`). A cfg-gated `mod lib_tests;` is the same
    kind of test sidecar as a cfg-gated `mod tests;`, and its println!s are
    test output, not library output.
    """
    return part in TEST_PATH_PARTS or part.endswith("_tests")

SANCTIONED_ROOT = {
    "README.md", "README", "CHANGELOG.md", "LICENSE", "LICENSE.md",
    "LICENSE-MIT", "LICENSE-APACHE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "copilot-instructions.md",
    "backlog.md", "checklist.md", "gap_audit.md",
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "rustfmt.toml",
    "clippy.toml", "deny.toml", "book.toml", "pyproject.toml",
    ".gitignore", ".gitattributes", ".gitmodules", ".git-blame-ignore-revs",
    ".envrc", ".git",
    "Makefile", "justfile", "pytest.ini", ".check_mdbook_links_allowlist",
}

# A submodule's `.git` is a gitlink *file*, not a directory, so it would
# otherwise be counted as unfiled root sprawl in every member repository.

# Stacked attributes may carry comment lines between them — apollo declares
# `#[cfg(test)]`, a five-line rationale, then `#[cfg(not(miri))] mod
# retained_footprint;` — so the run of "further attributes" admits `//`
# lines; without that the sidecar scanned as production and its report
# `println!`s counted as library output.
CFG_TEST_MOD = (
    r"#\[cfg\(\s*(?:all\(\s*)?test\b[^\]]*\]\s*"   # #[cfg(test)] / #[cfg(all(test, ...))]
    r"(?:(?:#\[[^\]]*\]|//[^\n]*)\s*)*"             # further attributes and comment lines
    r"(?:pub(?:\([^)]*\))?\s+)?mod\s+{stem}\s*;"    # [pub] mod <stem>;
)
CFG_TEST_MOD_ALL = re.compile(
    r"#\[cfg\(\s*(?:all\(\s*)?test\b[^\]]*\]\s*"
    r"(?P<attrs>(?:(?:#\[[^\]]*\]|//[^\n]*)\s*)*)"
    r"(?:pub(?:\([^)]*\))?\s+)?mod\s+(?P<stem>[A-Za-z_][A-Za-z0-9_]*)\s*;"
)

TYPE_NAME = re.compile(r"(?:^|_)(?:f16|bf16|f32|f64|u8|u16|u32|u64|i8|i16|i32|i64)(?:_|$)")
FN_DEF = re.compile(r"\bfn\s+(\w+)")
WORKSPACE_LINTS_TABLE = re.compile(
    r"(?m)^\s*\[workspace\.lints(?:\.[^\]]+)?\]\s*$"
)
# `is_none()` is not counted: an `Option` carries no value in `None`, so
# asserting absence is the complete value assertion (`assert_eq!(x, None)`
# needs `PartialEq` for nothing). `is_ok()`/`is_some()` hide the value and
# `is_err()` hides the variant; those are the existence-only forms.
EXISTENCE_ONLY = re.compile(r"assert!\s*\(\s*[^();]{0,120}\.is_(?:ok|err|some)\s*\(\s*\)\s*,?\s*[^();]*\)")
PRINT_DBG = re.compile(r"\b(?:println!|eprintln!|print!|eprint!|dbg!)")
# `println!("cargo:...")` is the canonical Cargo build-script protocol: it
# is the *required* way to emit build instructions (rerun-if-changed,
# rustc-cfg, rustc-link-arg, etc.) from a `build.rs` file.  Counting it as
# production print debt is a false positive — the directive cannot be
# removed without breaking the build.  The scanner exempts these writes
# only inside files named `build.rs`.
CARGO_PROTOCOL_PRINT = re.compile(r'\bprintln!\s*\(\s*"cargo:')
SLEEP = re.compile(r"(?:thread|time)::sleep\b")
MARKER = re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b")
REEXPORT_SHIM = re.compile(r"\bpub\s+use\s+[^;]*\bas\s+\w+\s*;")
# Code-shaped, not keyword-led: `// for all k1 in 0..n1`, `// let a NaN in
# the first chunk`, `// asserted where they are built`, and `// for this: an
# ISA minimum` are prose that begins with a Rust keyword, and the previous
# keyword-prefix form counted twelve such comments across apollo and hermes
# as commented-out code (ATLAS-RATCHET-REGRESSIONS-2026-09-02). Each
# alternative now demands the syntax that follows the keyword in code.
COMMENTED_CODE = re.compile(
    r"^\s*//\s?(?:"
    r"let\s+(?:mut\s+)?[A-Za-z_]\w*\s*(?::|=)"                     # let x = / let x:
    r"|fn\s+[A-Za-z_]\w*\s*[<(]"                                    # fn name(
    r"|use\s+[\w:]+(?:::\{|::\*|;)"                                 # use a::b;
    r"|pub(?:\([^)]*\))?\s+(?:fn|struct|enum|mod|use|const|static|type|trait)\b"
    r"|impl(?:<[^>]*>)?\s+[A-Za-z_][^{]*\{\s*$"                      # impl Foo for Bar {
    r"|match\s+[^{]+\{\s*$"                                         # match x {
    r"|if\s+(?:let\s+)?[^{]+\{\s*$"                                 # if cond {
    r"|for\s+(?:&(?:mut\s+)?)?(?:[A-Za-z_]\w*|\([^)]*\))\s+in\s"  # for i in
    r"|while\s+[^{]+\{\s*$"                                         # while cond {
    r"|struct\s+[A-Za-z_]\w*\s*[{<(;]"                              # struct Foo {
    r"|enum\s+[A-Za-z_]\w*\s*[{<]"                                  # enum Foo {
    r"|return\b[^;]*;\s*$"                                           # return x;
    r"|assert(?:_eq|_ne)?!\s*\("                                     # assert!(
    r")"
)
MANIFEST_PASSTHROUGH = re.compile(
    r"^\s*(?:$|//|#\[|#!\[|pub\s+use\b|use\b|pub\s+mod\b|mod\b"
    r"|pub\(crate\)\s+(?:use|mod)\b|extern\s+crate\b|\}|\{)"
)

CLASSES = [
    "oversized_files", "manifest_implementation", "unwrap_production",
    "allow_sites", "print_dbg", "existence_only_assertions",
    "type_suffixed_fns", "junk_drawer_modules", "missing_deny_docs",
    "root_sprawl", "markers", "reexport_shims", "sleep_synced_tests",
    "commented_out_code", "target_forks", "gitattributes_missing",
    "nextest_budget_missing", "workspace_lints_missing",
    "member_namespace_pollution", "tag_pinned_actions",
    "workflow_missing_timeout", "workflow_missing_permissions",
    "workflow_malformed_yaml", "pull_request_target_use",
    "missing_cargo_lock", "orphan_modules",
    "seqcst_production", "crate_level_allows", "excess_worktrees",
    "lane_kernel_uninlined", "toolchain_request_overridden",
    "default_branch_cancel_in_progress",
]

# Working trees beyond the two a repository may hold: its main tree plus one
# linked lane (AGENTS.md `git_discipline: Worktrees`).
#
# The bound is a creation precondition, so it only holds if something checks
# it. Nothing did, and the count reached five on one member and 26 lane
# directories stack-wide before anyone measured. Counting it here makes the
# audit mechanical: the ratchet then refuses a third tree the same way it
# refuses any other debt increase.
WORKTREE_BOUND = 2

# Crate- and module-level `#![allow(...)]`, counted separately from the
# per-item `#[allow(...)]` that `allow_sites` tracks.
#
# These were invisible to the ratchet until 2026-08-18: `allow_sites` counts
# the substring `#[allow(`, and `#![allow(` does not contain it -- the `!`
# breaks the match. So the blanket form, which the lint floor singles out
# ("suppressions are per-site `#[expect(lint, reason = ...)]`, never blanket
# or crate-level"), was the one form nothing measured.
#
# It is its own class rather than folded into `allow_sites` because it is the
# more severe form: an inner attribute silences a lint across every item in
# the module or crate, including code written after it, so it cannot be
# reviewed at the site it affects.
CRATE_LEVEL_ALLOW = re.compile(r"^\s*#!\[allow\(", re.MULTILINE)

# `SeqCst` in shipped code. The ordering rule is that each atomic access
# names the happens-before edge it needs and uses the weakest ordering that
# supplies it. `SeqCst` is the strongest and costliest on every target and is
# rarely the edge actually required, so it is not banned but should be a
# recorded decision rather than a default -- which a ratchet at the current
# count enforces. Test code is excluded: `SeqCst` on a drop counter costs
# nothing and proves nothing.
SEQCST = re.compile("SeqCst")

MOD_DECL = re.compile(r"\bmod\s+(r#[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\s*[;{]")
PATH_ATTR = re.compile(
    r"#\[\s*path\s*=\s*\"([^\"]+)\"\s*\]"
    r"(?:\s*(?:\#\[[^\]]*\]|//[^\n]*))*"
    r"\s*(?:pub(?:\([^)]*\))?\s*)?$"
)
INCLUDE_PATH = re.compile(
    r"include!\s*\(\s*(?:concat!\s*\(.*?['\"](?P<concat>[^'\"]+\.rs)['\"]|"
    r"['\"](?P<relative>[^'\"]+\.rs)['\"])",
    re.DOTALL,
)

SHA_PIN = re.compile(r"^\s*(?:-\s+)?uses:\s*[^\s@#]+@([A-Za-z0-9._/-]+)", re.MULTILINE)


def _yaml_loader():
    """Build a PyYAML SafeLoader that rejects duplicate mapping keys.

    GitHub Actions rejects a workflow with two `name:` keys even though stock
    ``yaml.safe_load`` accepts it (last one wins). Adding a duplicate-key
    constructor makes the detector fail the same way the runner does, so a
    malformed workflow cannot reach a shared release pipeline. Returns ``None``
    when PyYAML is not installed, in which case the scan cannot parse the file
    and treats it as unverifiable.
    """
    if _yaml is None:
        return None

    class UniqueKeyLoader(_yaml.SafeLoader):
        pass

    def _no_duplicate_keys(loader, node):
        mapping = {}
        for key_node, _value_node in node.value:
            key = loader.construct_object(key_node, deep=True)
            if key in mapping:
                raise ValueError(
                    f"duplicate key {key!r} (line {mapping[key]} and "
                    f"line {key_node.start_mark.line + 1})"
                )
            mapping[key] = key_node.start_mark.line + 1
        return _yaml.SafeLoader.construct_mapping(loader, node)

    UniqueKeyLoader.add_constructor(
        _yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
    )
    return UniqueKeyLoader


def workflow_yaml_is_valid(text: str) -> bool:
    """True when a workflow parses as YAML with no duplicate mapping keys.

    Returns True for a file PyYAML is absent to parse (the callers treat an
    unverifiable file as clean; only a *provably* malformed file is a defect),
    which keeps the ratchet from counting a missing dependency as debt.
    """
    loader = _yaml_loader()
    if loader is None:
        return True
    try:
        _yaml.load(text, Loader=loader)
    except Exception:
        return False
    return True


def is_reusable_workflow_caller(text: str) -> bool:
    """Return whether a workflow delegates all jobs to reusable workflows.

    GitHub does not allow ``timeout-minutes`` on a job that uses a reusable
    workflow. The called workflow owns the effective job bounds, so treating a
    pure caller as an unbounded local job creates a false conformance defect.
    Mixed workflows remain subject to the local timeout check.
    """
    return (
        bool(re.search(r"(?m)^jobs:\s*$", text))
        and bool(re.search(r"(?m)^\s+uses:\s+\S+/.github/workflows/\S+@\S+", text))
        and not re.search(r"(?m)^\s+runs-on:\s*", text)
        and not re.search(r"(?m)^\s+steps:\s*", text)
    )


TOOLCHAIN_REQUEST = re.compile(r'(?m)^\s+toolchain:\s*"?([0-9][0-9.]*)"?\s*$')
JOB_KEY = re.compile(r"(?m)^(?=  [A-Za-z_-]+:\s*$)")
PINNED_CHANNEL = re.compile(r'(?m)^\s*channel\s*=\s*"([^"]+)"')


def pinned_channel(repo: Path) -> str | None:
    """The committed `rust-toolchain.toml` channel, or None when there is none."""
    pin = repo / "rust-toolchain.toml"
    if not pin.is_file():
        return None
    match = PINNED_CHANNEL.search(pin.read_text(encoding="utf-8", errors="replace"))
    return match.group(1) if match else None


def same_release(requested: str, pinned: str) -> bool:
    """`1.95` names every 1.95.x; a host-qualified pin compares on its version."""
    pinned_version = pinned.split("-", 1)[0]
    wanted = requested.rstrip(".").split(".")
    return pinned_version.split(".")[: len(wanted)] == wanted


PUSH_TRIGGER = re.compile(r"(?ms)^on:.*?(?=^\S)")
UNCONDITIONAL_CANCEL = re.compile(r"(?m)^\s+cancel-in-progress:\s*true\s*$")


def cancels_default_branch_runs(text: str) -> bool:
    """A default-branch `push` trigger with an unconditional `cancel-in-progress: true`.

    GitHub supersedes a *pending* run in a shared concurrency group whatever
    the flag says, so a shared per-ref group on the default branch lets each
    merge cancel the previous merge's verification under runner starvation.
    The conforming form keys default-branch runs on `github.sha` and reserves
    cancellation for pull requests (`cancel-in-progress: ${{ github.event_name
    == 'pull_request' }}`), which this detector does not match.
    """
    trigger = PUSH_TRIGGER.search(text + "\n")
    if trigger is None or not re.search(r"(?m)^\s+push:", trigger.group(0)):
        return False
    return UNCONDITIONAL_CANCEL.search(text) is not None


def count_toolchain_requests_overridden(text: str, pinned: str | None) -> int:
    """Jobs whose install step requests a toolchain the committed pin outranks.

    `dtolnay/rust-toolchain` runs `rustup toolchain install` and `rustup
    default`; a committed `rust-toolchain.toml` ranks above a default, so the
    job compiles with the pinned channel and an MSRV job verifies nothing.
    `RUSTUP_TOOLCHAIN` — at workflow or job level — ranks above the file and
    exempts the job. A request naming the pinned release is not a defect.
    """
    if pinned is None or "jobs:" not in text:
        return 0
    head, _, jobs = text.partition("jobs:")
    if "RUSTUP_TOOLCHAIN" in head:
        return 0
    count = 0
    for block in JOB_KEY.split(jobs):
        if "RUSTUP_TOOLCHAIN" in block:
            continue
        count += sum(
            1 for m in TOOLCHAIN_REQUEST.finditer(block) if not same_release(m.group(1), pinned)
        )
    return count


def scan_workflows(repo: Path, c: dict[str, int]) -> None:
    """Workflow-hygiene classes (engineering_gates): SHA pins, bounds, tokens."""
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return
    pinned = pinned_channel(repo)
    for wf in sorted(wf_dir.iterdir()):
        if wf.suffix not in (".yml", ".yaml"):
            continue
        text = wf.read_text(encoding="utf-8", errors="replace")
        c["toolchain_request_overridden"] += count_toolchain_requests_overridden(text, pinned)
        if cancels_default_branch_runs(text):
            c["default_branch_cancel_in_progress"] += 1
        c["tag_pinned_actions"] += sum(
            1 for m in SHA_PIN.finditer(text)
            if not re.fullmatch(r"[0-9a-f]{40}", m.group(1))
        )
        if "timeout-minutes" not in text and not is_reusable_workflow_caller(text):
            c["workflow_missing_timeout"] += 1
        if "permissions:" not in text:
            c["workflow_missing_permissions"] += 1
        if not workflow_yaml_is_valid(text):
            c["workflow_malformed_yaml"] += 1
        if "pull_request_target" in text or "workflow_run" in text:
            c["pull_request_target_use"] += 1


def is_cargo_target_dir(entry: Path) -> bool:
    """True only for a real cargo build cache, not any dir named `target*`.

    The stack shares one `CARGO_TARGET_DIR`, so a repo-local cargo cache is a
    fork worth failing on. But a name test alone also flags directories that
    merely happen to be called `target` — athena's Pages workflow renders its
    mdBook to `target/book/athena`, which materializes `repos/athena/target`
    holding nothing but HTML. Counting that as a build-cache fork is a false
    positive that would push a repo over its ratchet for output it is
    supposed to produce.

    Cargo stamps every target directory it owns, so the marker is exact
    rather than heuristic: `.rustc_info.json` (and `CACHEDIR.TAG`, which
    cargo also writes) appear only in a cache cargo created.
    """
    if not entry.is_dir() or not entry.name.startswith("target"):
        return False
    markers = (".rustc_info.json", "CACHEDIR.TAG", "debug", "release")
    return any((entry / marker).exists() for marker in markers)


def count_root_sprawl(repo: Path) -> int:
    return sum(
        1 for e in repo.iterdir() if e.is_file() and e.name not in SANCTIONED_ROOT
    )


def count_excess_worktrees(repo: Path) -> int:
    """Registered working trees beyond [`WORKTREE_BOUND`] (main plus one lane).

    Reads the entries under `.git/worktrees/`, one per *linked* worktree; the
    primary checkout has no entry, which is why the bound is reduced by one
    before subtracting. Registration is the right thing to count: a directory
    left behind by a removed worktree is not a tree, and a tree whose
    directory was hand-deleted still is one until `git worktree prune` runs.
    Both were present in the stack when this was written.

    Zero when there is nothing to read, so a non-repository contributes no
    violation it cannot substantiate.
    """
    git_dir = repo / ".git"
    # A checkout may expose a real `.git` directory (as athena currently
    # does) instead of the gitdir file used by ordinary submodules. Keep
    # the directory form observable rather than guessing its provenance.
    if not git_dir.is_dir():
        # Submodule — .git is a file; read the actual gitdir
        if git_dir.is_file():
            gitdir_ref = git_dir.read_text(errors="replace").strip()
            if gitdir_ref.startswith("gitdir:"):
                git_dir = (repo / gitdir_ref[len("gitdir:"):].strip()).resolve()
    wt_dir = git_dir / "worktrees"
    if not wt_dir.is_dir():
        return 0
    linked = sum(1 for entry in wt_dir.iterdir() if entry.is_dir())
    return max(0, linked - (WORKTREE_BOUND - 1))


def lf_policy_missing(repo: Path) -> int:
    ga = repo / ".gitattributes"
    return 0 if ga.is_file() and "text=auto" in ga.read_text(errors="replace") else 1


def _child_candidates(owner: Path, name: str, explicit: str | None) -> list[Path]:
    """Files a `mod` declaration in `owner` can resolve to."""
    if explicit:
        # A `#[path]` on a non-inline `mod` resolves against the directory
        # holding the *declaring file*, never against that file's module
        # directory — `#[path = "x.rs"] mod x;` inside `a/b.rs` is `a/x.rs`.
        return [owner.parent / explicit]
    base = owner.parent if owner.name in ("lib.rs", "main.rs", "mod.rs") \
        else owner.with_suffix("")
    file_name = name[2:] if name.startswith("r#") else name
    return [base / f"{file_name}.rs", base / file_name / "mod.rs"]


def cargo_manifests(repo: Path):
    """Yield Cargo.toml paths under a repo, pruning caches and lanes.

    Mirrors the `rust_files` walker: `target*`, `.git`, mdBook `book`
    output, and lane roots hold no manifests belonging to the scanned tree,
    and crawling them (as `rglob` would) dominates scan time on repos with
    materialized build caches.
    """
    stack = [repo]
    while stack:
        d = stack.pop()
        for entry in d.iterdir():
            name = entry.name
            if entry.is_dir():
                if name in PRUNE_DIRS or name.startswith("target"):
                    continue
                stack.append(entry)
            elif name == "Cargo.toml":
                yield entry


MAX_SCAN_WORKERS = 4

_scan_local = threading.local()


def _file_text_cache() -> dict[Path, str | None]:
    """Return the current scan worker's source-text cache."""
    cache = getattr(_scan_local, "file_text", None)
    if cache is None:
        cache = {}
        _scan_local.file_text = cache
    return cache


def _cfg_test_decl_cache() -> dict[Path, tuple[frozenset[str], frozenset[Path]]]:
    """Return the current scan worker's cfg-test declaration cache."""
    cache = getattr(_scan_local, "cfg_test_decls", None)
    if cache is None:
        cache = {}
        _scan_local.cfg_test_decls = cache
    return cache


def _clear_scan_caches() -> None:
    """Drop per-scan read caches so repeated scans see fresh content."""
    _file_text_cache().clear()
    _cfg_test_decl_cache().clear()


def _cfg_test_decls(cand: Path) -> tuple[frozenset[str], frozenset[Path]]:
    """Stems and redirected files a candidate declares under `#[cfg(test)]`.

    One regex pass over each parent file serves both matchers
    (`src/foo/tests.rs` vs `src/foo/mod.rs` is O(n) per directory, not
    O(n^2)). A declaration may redirect its file with `#[path]`, resolved
    against the declaring file's directory like `_child_candidates`, so a
    sidecar can live outside the declarer's own directory — moirai-iter
    gates `#[path = "../async_iter_tests.rs"] mod async_iter_tests;` from
    `src/async_iter/mod.rs`.
    """
    cache = _cfg_test_decl_cache()
    cached = cache.get(cand)
    if cached is None:
        text = _cached_text(cand)
        if text:
            stems: set[str] = set()
            paths: set[Path] = set()
            for match in CFG_TEST_MOD_ALL.finditer(text):
                stems.add(match.group("stem"))
                attr = PATH_ATTR.search(match.group("attrs").rstrip())
                if attr:
                    paths.add((cand.parent / attr.group(1)).resolve())
            cached = (frozenset(stems), frozenset(paths))
        else:
            cached = (frozenset(), frozenset())
        cache[cand] = cached
    return cached


def _cfg_test_sidecars(cand: Path) -> frozenset[str]:
    """Module stems a candidate parent declares under `#[cfg(test)]`."""
    return _cfg_test_decls(cand)[0]


def _cached_text(path: Path) -> str | None:
    """Read a file at most once per scan; `None` when unreadable.

    `scan_repo` touches the same sources in up to three passes (the class
    scan, `declared_cfg_test`'s parent lookups, and the module-graph walk),
    so a shared canonical-path cache turns cold scans' repeated disk I/O and
    transient allocations into one read per file.
    """
    key = path.resolve()
    cache = _file_text_cache()
    if key not in cache:
        try:
            cache[key] = key.read_text(encoding="utf-8", errors="replace")
        except OSError:
            cache[key] = None
    return cache[key]


def _walk_mods(root: Path, seen: set[Path]) -> None:
    """Depth-first close the module and include graphs from one crate root."""
    root = root.resolve()
    if root in seen or not root.is_file():
        return
    seen.add(root)
    text = _cached_text(root)
    if text is None:
        return
    for m in MOD_DECL.finditer(text):
        attr = PATH_ATTR.search(text[:m.start()].rstrip())
        for cand in _child_candidates(root, m.group(1), attr.group(1) if attr else None):
            if cand.is_file():
                _walk_mods(cand, seen)
                break
    crate_root = next(
        (parent for parent in (root.parent, *root.parents)
         if (parent / "Cargo.toml").is_file()),
        root.parent,
    )
    for match in INCLUDE_PATH.finditer(text):
        relative = match.group("relative")
        included = match.group("concat") or relative
        owner = crate_root if match.group("concat") else root.parent
        candidate = owner / included.lstrip("/\\")
        if candidate.is_file():
            _walk_mods(candidate, seen)


def count_orphan_modules(repo: Path, manifests: list[Path] | None = None) -> int:
    """`.rs` files under a crate `src/` that no source edge reaches.

    Cargo compiles only what the module or include graph names, so an undeclared
    file is
    invisible to rustc, clippy, and the test runner while every text-based
    scan (including this one's other classes) still counts it — dead weight
    that inflates debt figures and silently rots. Crate roots are the targets
    Cargo builds: `src/lib.rs`, `src/main.rs`, `src/bin/*.rs`, and
    `src/bin/<name>/main.rs`.

    `manifests` is the per-repository inventory collected by [scan_repo].
    Reusing it avoids a second full directory traversal when the caller has
    already collected the manifest set.
    """
    sources: set[Path] = set()
    roots: list[Path] = []
    if manifests is None:
        manifests = list(cargo_manifests(repo))
    for manifest in manifests:
        src = manifest.parent / "src"
        if not src.is_dir():
            continue
        sources.update(p.resolve() for p in src.rglob("*.rs"))
        roots.extend(src / stem for stem in ("lib.rs", "main.rs")
                     if (src / stem).is_file())
        bins = src / "bin"
        if bins.is_dir():
            roots.extend(bins.glob("*.rs"))
            roots.extend(d / "main.rs" for d in bins.iterdir()
                         if (d / "main.rs").is_file())
    seen: set[Path] = set()
    for r in roots:
        _walk_mods(r, seen)
    return len(sources - seen)


# Module trees are shallow; the bound only stops a cycle from a `#[path]`
# attribute pointing a module at its own directory.
_MAX_MODULE_DEPTH = 16


def declared_cfg_test(entry: Path, _depth: int = 0) -> bool:
    """True when this file is declared under `#[cfg(test)]`, directly or above.

    The co-located sidecar convention (`src/foo/tests.rs` declared by
    `src/foo/mod.rs` as `#[cfg(test)] mod tests;`) puts the gate in the
    *parent*, so neither a path-part match nor an in-file `#[cfg(test)]`
    sees it. A `#[path]` attribute can place the sidecar anywhere relative
    to its declarer, so sibling-directory `mod.rs` files are consulted too:
    moirai-iter gates `../async_iter_tests.rs` from `src/async_iter/mod.rs`,
    which no parent-of-entry lookup reaches. Without these checks such
    files scan as production code.

    A directory module's own gate sits one level up: `src/foo/mod.rs` named
    by `mod foo;` declares through its *file stem*, but when the directory
    is declared as `#[cfg(test)] mod codelet;` the file is
    `src/foo/codelet/mod.rs`, whose entry stem (`mod`) matches nothing —
    apollo's test-only `codelet` counted as production code (the 4th
    `lane_kernel_uninlined` site). When the entry is a `mod.rs`, the parent
    directory's name is the module stem, so the grandparent's declarers are
    consulted with it.
    """
    parent = entry.parent
    resolved = entry.resolve()
    stems_to_check = [entry.stem]
    if entry.name in ("mod.rs", "lib.rs"):
        stems_to_check.append(parent.name)
    candidates = [parent / "mod.rs", parent / "lib.rs", parent / "main.rs",
                  parent.with_suffix(".rs")]
    candidates.extend(parent.glob("*/mod.rs"))
    if entry.name in ("mod.rs", "lib.rs"):
        grandparent = parent.parent
        candidates.extend([grandparent / "mod.rs", grandparent / "lib.rs",
                           grandparent / "main.rs", grandparent / f"{parent.name}.rs"])
        candidates.extend(grandparent.glob("*/mod.rs"))
    for cand in candidates:
        if cand == entry:
            continue
        stems, paths = _cfg_test_decls(cand)
        if any(stem in stems for stem in stems_to_check) or resolved in paths:
            return True
    # A gate is inherited: `#[cfg(test)] mod probe;` makes every module under
    # `probe/` test code too, and only `probe/mod.rs` carries the declaration
    # the loop above can see. Splitting one gated file into a directory of
    # modules therefore reclassified all of them as production — apollo's
    # pinned probe turned 25 measurement `println!`s into print debt without a
    # line of it changing. Ask the declaring file the same question.
    if entry.name != "mod.rs" and _depth < _MAX_MODULE_DEPTH:
        owner = parent / "mod.rs"
        if owner.is_file() and owner != entry:
            return declared_cfg_test(owner, _depth + 1)
    return False


def git_output(*args: str, cwd: Path = ROOT) -> str:
    """Run a read-only Git query and return its output or a useful error."""
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        encoding="utf-8", errors="replace",
        check=False,
    )
    if proc.returncode:
        detail = proc.stderr.strip() or "git command failed"
        raise RuntimeError(detail)
    return proc.stdout


def registered_member_names_at(root: Path) -> set[str]:
    """Read the stack universe from the `.gitmodules` in a scan root."""
    gm = root / ".gitmodules"
    if not gm.is_file():
        return set()
    return {
        m.group(1)
        for m in re.finditer(
            r"path\s*=\s*repos/([^\s/]+)",
            gm.read_text(encoding="utf-8", errors="replace"),
        )
    }


def require_materialized_providers(
    stack_root: Path,
    members: set[str],
) -> list[Path]:
    """Return registered provider roots after proving each is materialized.

    A linked Atlas worktree contains the registered ``repos/<name>``
    directories even when their submodules were never initialized. Scanning
    those empty directories reports false zeroes and can make an incomplete
    scan appear faster. A real submodule or standalone checkout always owns a
    ``.git`` file or directory at its root, which is the exact distinction the
    scan needs before traversing source.
    """
    member_root = stack_root / "repos"
    providers = [member_root / name for name in sorted(members)]
    missing = [provider.name for provider in providers if not (provider / ".git").exists()]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"provider checkouts are not materialized: {names}; initialize submodules"
        )
    return providers


def gitlink_revision(root_revision: str, path: str, root: Path = ROOT) -> str:
    """Return the gitlink commit recorded at *path* in a root revision."""
    fields = git_output("ls-tree", root_revision, "--", path, cwd=root).strip().split(maxsplit=3)
    if len(fields) != 4 or fields[0] != "160000" or fields[1] != "commit":
        raise RuntimeError(f"{root_revision}:{path} is not a gitlink")
    return fields[2]


def rust_files(repo: Path):
    """Yield (path, is_testish) for every .rs file, pruning caches and lanes."""
    stack = [repo]
    while stack:
        d = stack.pop()
        for entry in d.iterdir():
            name = entry.name
            if entry.is_dir():
                if name in PRUNE_DIRS or name.startswith("target"):
                    continue
                stack.append(entry)
            elif name.endswith(".rs"):
                # Match directory parts only: `entry.parts` includes the file
                # name, so a file literally named `tests.rs` never matched the
                # `tests` part and was scanned as production.
                testish = any(
                    _is_testish_path_part(p) for p in entry.parent.parts
                ) or declared_cfg_test(entry)
                yield entry, testish


def executable_source_dirs(
    repo: Path,
    manifests: list[Path] | None = None,
) -> set[Path]:
    """Return source roots whose package entry point is a binary.

    Binary support modules are executable surfaces even when their own file
    is not named `main.rs`; counting their stdout/stderr as library output
    produces false positives for task runners such as `xtask`.

    `manifests` reuses the inventory collected by [scan_repo] when available;
    the optional argument preserves the direct helper contract used by tests.
    """
    roots: set[Path] = set()
    if manifests is None:
        manifests = list(cargo_manifests(repo))
    for manifest in manifests:
        source = manifest.parent / "src"
        if (source / "main.rs").is_file():
            roots.add(source)
    return roots


CFG_ATTR_OPEN = re.compile(r"#\[\s*cfg\s*\(")
CFG_PREDICATE_TOKEN = re.compile(r"[A-Za-z_]\w*|\(|\)")


def cfg_predicate_is_test_gated(predicate: str) -> bool:
    """True when the predicate can only hold under `test`.

    Structural, not textual: `test` requires test; `all(..)` requires it when
    any conjunct does; `any(..)` only when every branch does — an item under
    `any(test, feature = "std")` is production whenever the feature is on
    (consus gates 370 production `unwrap()`s that way); `not(..)` never
    requires it. String values are blanked so `feature = "test-utils"` names
    no predicate.
    """
    tokens = CFG_PREDICATE_TOKEN.findall(re.sub(r'"[^"]*"', '""', predicate))
    position = 0

    def parse() -> bool:
        nonlocal position
        if position >= len(tokens):
            return False
        token = tokens[position]
        position += 1
        if token in ("(", ")"):
            return False
        if position < len(tokens) and tokens[position] == "(":
            position += 1
            branches = []
            while position < len(tokens) and tokens[position] != ")":
                branches.append(parse())
            position += 1  # the closing parenthesis
            if token == "all":
                return any(branches)
            if token == "any":
                return bool(branches) and all(branches)
            return False  # `not(..)` and unknown operators
        return token == "test"

    return parse()


def _paren_end(text: str, open_index: int) -> int:
    """Index just past the `)` matching the `(` at `open_index`."""
    depth = 0
    for i in range(open_index, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _item_end(text: str, start: int) -> int:
    """Index just past the item that begins after its attributes at `start`.

    Skips further attributes and comments, then ends the item at the first
    top-level `{` block (through its matching brace) or `;`; bracket depth
    keeps a `;` inside `[u8; 3]` or a `{` inside `Lazy::new(|| { .. })`
    from ending it early.
    """
    i, n = start, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
        elif text.startswith("#[", i) or text.startswith("#![", i):
            close = text.find("]", i)
            i = n if close < 0 else close + 1
        elif text.startswith("//", i):
            newline = text.find("\n", i)
            i = n if newline < 0 else newline + 1
        else:
            break
    depth = 0
    while i < n:
        c = text[i]
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "{" and depth == 0:
            return _brace_end(text, i)
        elif c == ";" and depth == 0:
            return i + 1
        i += 1
    return n


def split_test_region(text: str) -> tuple[str, str]:
    """Split a source file into its production and test-gated text.

    Every item under a `#[cfg(..)]` whose predicate names `test` outside a
    `not(...)` is test text — `#[cfg(test)] mod tests { .. }`, a
    `#[cfg(all(test, windows))] macro_rules!`, a `#[cfg(test)] mod tests;`
    sidecar declaration — scoped to that item, so production code that
    follows a test item stays production. The earlier form cut the file at
    the first literal `#[cfg(test)]`, which missed compound predicates (two
    apollo timing macros counted as library `eprintln!`) and swept everything
    after the cut into the test side.
    """
    production: list[str] = []
    tests: list[str] = []
    cursor = 0
    for match in CFG_ATTR_OPEN.finditer(text):
        if match.start() < cursor:
            continue
        close = _paren_end(text, match.end() - 1)
        attribute_end = text.find("]", close)
        if attribute_end < 0:
            break
        if not cfg_predicate_is_test_gated(text[match.end():close - 1]):
            continue
        item_end = _item_end(text, attribute_end + 1)
        production.append(text[cursor:match.start()])
        tests.append(text[match.start():item_end])
        cursor = item_end
    production.append(text[cursor:])
    return "".join(production), "".join(tests)


def strip_doc_comments(text: str) -> str:
    """Drop `///` and `//!` lines: their code fences are doctests, not production."""
    return "\n".join(
        ln for ln in text.splitlines()
        if not ln.lstrip().startswith(("///", "//!"))
    )


LANE_KERNEL_IMPL = re.compile(r"impl(?:<[^>]*>)?\s+LaneKernel\s*<")
LANE_KERNEL_CALL = re.compile(r"\bfn\s+call\s*<")
INLINE_ALWAYS = re.compile(r"#\[\s*inline\s*\(\s*always\s*\)\s*\]")
# A `LaneKernel::call` body above this many lines must be
# `#[inline(always)]` (hermes HS-VECTORIZE-LARGE-KERNEL-2026-08-28). The
# `#[runtime_dispatch]` expansion's `#[target_feature]` helper is the only
# feature-carrying frame; a large body makes LLVM decline to inline it, and
# the body then codegens at the baseline ISA — zero FMA, per-operation
# feature detection, ~30x. Small bodies inline anyway, so they are exempt.
LANE_KERNEL_INLINE_THRESHOLD = 100


def _brace_end(text: str, open_index: int) -> int:
    """Index just past the `}` matching the `{` at `open_index`."""
    depth = 0
    i = open_index
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def count_lane_kernel_uninlined(text: str) -> int:
    """Count `LaneKernel::call` bodies above the threshold without the inline attr.

    A large `#[target_feature]` kernel body that is not `#[inline(always)]`
    silently compiles at the baseline ISA — the exact ~30x defect hermes
    `HS-VECTORIZE-LARGE-KERNEL-2026-08-28` documents. This closes the
    consumer half: hermes owns the kernel entry, but a consumer's large
    `call` body must still be inlined into the feature-carrying wrapper. The
    detector is a line-count heuristic, deliberately mirroring the manual
    brace-match census the backlog records; `#[inline(always)]` is searched
    in the text immediately preceding the `fn call` within the same impl.
    """
    count = 0
    for impl in LANE_KERNEL_IMPL.finditer(text):
        brace = text.find("{", impl.end())
        if brace == -1:
            continue
        end = _brace_end(text, brace)
        impl_body = text[brace:end]
        for call in LANE_KERNEL_CALL.finditer(impl_body):
            call_brace = impl_body.find("{", call.start())
            if call_brace == -1:
                continue
            body = impl_body[call_brace:_brace_end(impl_body, call_brace)]
            lines = body.count("\n") + 1
            if lines < LANE_KERNEL_INLINE_THRESHOLD:
                continue
            preceding = impl_body[max(0, call.start() - 250):call.start()]
            if not INLINE_ALWAYS.search(preceding):
                count += 1
    return count


def scan_repo(repo: Path, live_repo: Path | None = None) -> dict[str, int]:
    """Count every debt class in `repo`'s content.

    `live_repo` is the checkout whose registration state the two live-only
    classes read (`excess_worktrees` from `.git/worktrees`, `target_forks`
    from the directory listing) when `repo` is an archived snapshot of a
    recorded revision rather than the checkout itself.
    """
    live_repo = live_repo or repo
    _clear_scan_caches()
    c = dict.fromkeys(CLASSES, 0)
    has_cargo = (repo / "Cargo.toml").is_file()
    manifests = list(cargo_manifests(repo))
    executable_dirs = executable_source_dirs(repo, manifests)

    for path, testish in rust_files(repo):
        text = _cached_text(path)
        if text is None:
            continue
        # Test sidecars under `src/` are commonly named `tests_*.rs` (or
        # `tests.rs`). Their parent manifest carries the cfg gate, so the
        # filename convention is the only signal available without building a
        # full module graph.
        production_testish = testish or path.stem == "tests" or path.stem.startswith("tests_")
        lines = text.count("\n") + 1
        if lines > 500:
            c["oversized_files"] += 1
        if path.name in ("lib.rs", "mod.rs"):
            body = sum(
                1 for ln in text.splitlines() if not MANIFEST_PASSTHROUGH.match(ln)
            )
            if body > 20 and not production_testish:
                c["manifest_implementation"] += 1
            if path.name == "lib.rs" and "deny(missing_docs" not in text \
                    and "forbid(missing_docs" not in text and not production_testish:
                c["missing_deny_docs"] += 1
        if path.stem in ("utils", "helpers", "misc", "common"):
            c["junk_drawer_modules"] += 1

        if production_testish and not testish:
            # A sidecar's whole file is test-only for production-debt classes,
            # but preserve the existing inline cfg split for test-debt counts
            # so reclassifying the file does not manufacture new assertions.
            _, test = split_test_region(text)
            prod = ""
        else:
            prod, test = ("", text) if testish else split_test_region(text)
        is_bin = path.name == "main.rs" or "bin" in path.parts or \
            "benches" in path.parts or any(
                source in path.parents for source in executable_dirs
            )
        # Doc-comment bodies are doctests, i.e. test code. Counting `.unwrap()`
        # inside `///` lines reported 23 "production unwraps" for a repo whose
        # workspace denies `unwrap_used` outright — every one was a doc example.
        c["unwrap_production"] += strip_doc_comments(prod).count(".unwrap()")
        c["allow_sites"] += prod.count("#[allow(")
        c["crate_level_allows"] += len(CRATE_LEVEL_ALLOW.findall(prod))
        c["seqcst_production"] += len(SEQCST.findall(prod))
        c["markers"] += len(MARKER.findall(prod))
        c["reexport_shims"] += len(REEXPORT_SHIM.findall(prod))
        c["type_suffixed_fns"] += sum(
            1 for m in FN_DEF.finditer(prod) if TYPE_NAME.search(m.group(1))
        )
        c["commented_out_code"] += sum(
            1 for ln in prod.splitlines() if COMMENTED_CODE.match(ln)
        )
        if not is_bin:
            hits = len(PRINT_DBG.findall(prod))
            # Exempt `println!("cargo:...")` in build.rs — the canonical
            # Cargo build-script protocol.  These are required build
            # instructions, not debug print debt.
            if path.name == "build.rs" and hits:
                hits -= len(CARGO_PROTOCOL_PRINT.findall(prod))
            c["print_dbg"] += hits
        c["lane_kernel_uninlined"] += count_lane_kernel_uninlined(prod)
        c["existence_only_assertions"] += len(EXISTENCE_ONLY.findall(test))
        c["sleep_synced_tests"] += len(SLEEP.findall(test))

    c["root_sprawl"] = count_root_sprawl(repo)
    c["excess_worktrees"] = count_excess_worktrees(live_repo)
    c["target_forks"] = sum(1 for e in live_repo.iterdir() if is_cargo_target_dir(e))
    c["gitattributes_missing"] = lf_policy_missing(repo)
    c["orphan_modules"] = count_orphan_modules(repo, manifests)
    if has_cargo:
        nx = repo / ".config" / "nextest.toml"
        if not (nx.is_file() and "slow-timeout" in nx.read_text(errors="replace")):
            c["nextest_budget_missing"] = 1
        manifest = (repo / "Cargo.toml").read_text(errors="replace")
        if "[workspace]" in manifest and not WORKSPACE_LINTS_TABLE.search(manifest):
            c["workspace_lints_missing"] = 1
        if not (repo / "Cargo.lock").is_file():
            c["missing_cargo_lock"] = 1
    scan_workflows(repo, c)
    _clear_scan_caches()
    return c


def materialize_member(
    provider: Path, expected: str, scratch: Path
) -> tuple[Path, Path]:
    """Return `(content, live)` for a provider whose recorded gitlink is `expected`.

    A clean checkout at `expected` is its own snapshot. Otherwise the recorded
    revision is extracted with `git archive` into `scratch` (fetching first
    when the object is absent), so a peer holding the checkout behind or
    dirty never blocks a recorded-revision scan and never leaks its state
    into the counts: members of this stack are routinely behind — eight of
    twenty-five the day the clean-checkout gate was written.
    """
    actual = git_output("rev-parse", "HEAD", cwd=provider).strip()
    dirty = git_output("status", "--porcelain", "--ignore-submodules=all", cwd=provider).strip()
    if actual == expected and not dirty:
        return provider, provider
    archive = subprocess.run(
        ["git", "-C", str(provider), "archive", "--format=tar", expected],
        capture_output=True, check=False,
    )
    if archive.returncode:
        subprocess.run(["git", "-C", str(provider), "fetch", "--quiet", "origin"],
                       capture_output=True, check=False)
        archive = subprocess.run(
            ["git", "-C", str(provider), "archive", "--format=tar", expected],
            capture_output=True, check=False,
        )
    if archive.returncode:
        raise RuntimeError(
            f"repos/{provider.name}: recorded gitlink {expected[:12]} is not in the "
            f"provider's object store: {archive.stderr.decode('utf-8', 'replace').strip()}"
        )
    content = scratch / provider.name
    content.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(content, filter="data")
    # The provider gate accepts a checkout by its `.git` marker; the snapshot
    # carries one so the same gate admits it.
    (content / ".git").write_text(f"gitdir: archived {expected}\n", encoding="utf-8")
    return content, provider


def scan_stack(
    stack_root: Path = ROOT, root_revision: str | None = None
) -> dict[str, dict[str, int]]:
    """Scan every registered member.

    With `root_revision`, each member is scanned at the gitlink that revision
    records — from the checkout when it is clean and at that commit, else from
    an archived snapshot (`materialize_member`). Without it, the live trees
    are scanned as they are (`--worktree`).
    """
    out = {}
    member_root = stack_root / "repos"
    members = registered_member_names_at(stack_root)
    meta = dict.fromkeys(CLASSES, 0)
    if member_root.is_dir():
        repos = require_materialized_providers(stack_root, members)
        if repos:
            with tempfile.TemporaryDirectory(prefix="atlas-conformance-") as scratch:
                targets = []
                for repo in repos:
                    if root_revision is None:
                        targets.append((repo, repo))
                    else:
                        expected = gitlink_revision(root_revision, f"repos/{repo.name}", stack_root)
                        targets.append(materialize_member(repo, expected, Path(scratch)))
                # Four workers match the smallest hosted runner while avoiding
                # unbounded parallel metadata and filesystem traversal.
                worker_count = min(MAX_SCAN_WORKERS, len(repos))
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    counts_by_repo = executor.map(
                        lambda target: scan_repo(target[0], live_repo=target[1]), targets
                    )
                    for repo, counts in zip(repos, counts_by_repo, strict=True):
                        out[repo.name] = counts
        if stack_root == ROOT:
            for repo in sorted(member_root.iterdir()):
                if (
                    repo.is_dir()
                    and not repo.name.startswith(".")
                    and repo.name not in members
                    and not is_git_ignored(repo)
                ):
                    meta["member_namespace_pollution"] += 1
    meta["root_sprawl"] = count_root_sprawl(ROOT)
    meta["gitattributes_missing"] = lf_policy_missing(ROOT)
    scan_workflows(ROOT, meta)
    out["<meta>"] = meta
    return out


def report(results: dict[str, dict[str, int]]) -> None:
    totals = dict.fromkeys(CLASSES, 0)
    for counts in results.values():
        for k, v in counts.items():
            totals[k] += v
    width = max(len(k) for k in CLASSES)
    print(f"{'class':<{width}}  total  worst offenders")
    for k in CLASSES:
        worst = sorted(
            ((r, c[k]) for r, c in results.items() if c[k]),
            key=lambda t: -t[1],
        )[:3]
        offenders = ", ".join(f"{r}={n}" for r, n in worst) or "-"
        print(f"{k:<{width}}  {totals[k]:>5}  {offenders}")


def render_baseline(results: dict[str, dict[str, int]]) -> str:
    """The exact on-disk form of the committed baseline.

    Sole owner of the artifact's formatting, because a generator that does
    not reproduce its own committed output is not idempotent: `generate`
    wrote `indent=1` against a file committed at `indent=2`, so every
    baseline change arrived as a ~1500-line whole-file diff. A single
    laundered count is invisible in a diff that size -- which is how
    `e9c5821`'s `ritk/print_dbg: 12 -> 17` passed review. Pinned by a test
    against the committed file.
    """
    return json.dumps(results, indent=2, sort_keys=True) + "\n"


def baseline_raises(
    previous: dict[str, dict[str, int]],
    current: dict[str, dict[str, int]],
) -> list[tuple[str, str, int, int]]:
    """Every (repo, class, was, now) where `current` exceeds `previous`.

    A repo or class absent from `previous` is not a raise: it has no recorded
    value to exceed, so a newly measured repo or a newly added detector class
    enters at whatever it measures.
    """
    raises = []
    for repo, counts in sorted(current.items()):
        for cls, value in sorted(counts.items()):
            was = previous.get(repo, {}).get(cls)
            if was is not None and value > was:
                raises.append((repo, cls, was, value))
    return raises


def ratchet_delta(
    baseline: dict[str, dict[str, int]],
    results: dict[str, dict[str, int]],
) -> tuple[list[str], list[str]]:
    """Return baseline regressions and tightening candidates."""
    regressions, tightenings = [], []
    for repo, counts in results.items():
        for class_name, value in counts.items():
            previous = baseline.get(repo, {}).get(class_name, 0)
            if value > previous:
                regressions.append(f"{repo}/{class_name}: {previous} -> {value}")
            elif value < previous:
                tightenings.append(f"{repo}/{class_name}: {previous} -> {value}")
    return regressions, tightenings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="report",
                        choices=["report", "generate", "check"])
    parser.add_argument(
        "--revision",
        default="HEAD",
        metavar="REV",
        help="scan this root Git revision and its recorded provider gitlinks",
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="scan the live member trees as they are, including uncommitted "
             "changes, instead of the gitlinks the root revision records",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of the summary table",
    )
    parser.add_argument(
        "--repo",
        metavar="NAME",
        help="scan only this provider repo (live tree, bypasses the clean-stack gate)",
    )
    parser.add_argument(
        "--accept-raises",
        metavar="REASON",
        help="permit `generate` to raise counts above the committed baseline, "
             "recording REASON. Only a detector change legitimately raises a "
             "count; absorbing a code regression is what the ratchet exists to "
             "prevent, so this must never be used to clear a failing check",
    )
    args = parser.parse_args()
    mode = args.mode
    if mode == "generate" and args.repo:
        print("refusing to generate a baseline from a single repo; omit --repo",
              file=sys.stderr)
        return 2
    try:
        if args.repo:
            member = ROOT / "repos" / args.repo
            if not member.is_dir():
                print(f"no such provider repo: {args.repo}", file=sys.stderr)
                return 2
            require_materialized_providers(ROOT, {args.repo})
            results = {args.repo: scan_repo(member)}
        elif args.worktree:
            results = scan_stack(ROOT)
        else:
            root_revision = git_output(
                "rev-parse", "--verify", f"{args.revision}^{{commit}}"
            ).strip()
            results = scan_stack(ROOT, root_revision)
    except RuntimeError as exc:
        print(f"conformance scan unavailable: {exc}", file=sys.stderr)
        return 2

    if mode == "report":
        if args.json:
            print(json.dumps(results, indent=1, sort_keys=True))
        else:
            report(results)
        return 0
    if mode == "generate":
        # A ratchet whose baseline can be rewritten upward is not a ratchet.
        # `check` already refuses a raise; without the same rule here, any
        # failing check can be cleared by running `generate`, which satisfies
        # the gate's form while inverting its purpose. Observed once:
        # e9c5821 lifted ritk/print_dbg 12 -> 17 under the description
        # "update baseline after ... advances".
        #
        # A detector change is the one legitimate raise (generator contract:
        # changing a detector regenerates the baseline in the same change),
        # so the escape hatch exists -- but it is explicit, it names a reason,
        # and it is loud.
        raises = []
        if BASELINE.is_file():
            raises = baseline_raises(json.loads(BASELINE.read_text()), results)
        if raises and not args.accept_raises:
            print("refusing to raise the baseline; the ratchet only decreases:",
                  file=sys.stderr)
            for repo, cls, was, value in raises:
                print(f"  RAISE {repo}/{cls}: {was} -> {value}", file=sys.stderr)
            print("\nFix the debt, or -- if a detector changed and this is the "
                  "generator contract, not a regression --\nre-run with "
                  "--accept-raises 'why the detector changed'.", file=sys.stderr)
            return 2
        if raises:
            print(f"baseline raised, reason: {args.accept_raises}")
            for repo, cls, was, value in raises:
                print(f"  RAISE {repo}/{cls}: {was} -> {value}")
        BASELINE.write_text(render_baseline(results), newline="\n")
        print(f"baseline written: {BASELINE.relative_to(ROOT)}")
        if args.json:
            print(render_baseline(results), end="")
        else:
            report(results)
        return 0

    if not BASELINE.is_file():
        print("no committed baseline; run `generate` first", file=sys.stderr)
        return 1
    base = json.loads(BASELINE.read_text())
    regressions, tightenings = ratchet_delta(base, results)
    if args.json:
        print(json.dumps({
            "results": results,
            "regressions": regressions,
            "tightenings": tightenings,
        }, indent=1, sort_keys=True))
        return 1 if regressions else 0
    for t in tightenings:
        print(f"tightened (update baseline): {t}")
    # A `--worktree` scan measures whatever is checked out, and members of
    # this stack are routinely behind — eight of twenty-five were the day
    # this was added. The default path scans the recorded gitlinks
    # (`materialize_member`); `--worktree` is the deliberate live audit, so
    # every count it produces needs its provenance attached. Without this,
    # upstream-fixed debt reads as a fresh regression.
    stale = {}
    if args.worktree:
        for repo_name in {r.split("/", 1)[0] for r in regressions}:
            member = ROOT / "repos" / repo_name
            if member.is_dir():
                note = staleness_note(member)
                if note:
                    stale[repo_name] = note
    for r in regressions:
        print(f"RATCHET VIOLATION: {r}{stale.get(r.split('/', 1)[0], '')}")
    print(f"{len(regressions)} regression(s), {len(tightenings)} tightening(s)")
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
