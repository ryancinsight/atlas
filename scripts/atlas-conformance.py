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

Modes:
    report      per-repo x per-class table (default)
    generate    write scripts/conformance-baseline.json from the clean HEAD
                revision (or the live tree with --worktree)
    check       re-scan and fail (exit 1) on any per-repo class increase
                over the committed baseline; decreases print as tightening
                candidates for a baseline update in the same change

Run from anywhere: paths are anchored to this file's parent repository.
The default scan requires a clean checkout whose provider gitlinks match the
requested root revision. Use --worktree only for an intentional dirty-tree
audit; such a result is not a reproducible gate input.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atlas_stack import ROOT, is_git_ignored

BASELINE = ROOT / "scripts" / "conformance-baseline.json"

PRUNE_DIRS = {".git", "worktrees", "__pycache__", "node_modules", ".claude", "book"}
TEST_PATH_PARTS = {"tests", "benches", "examples", "fuzz"}

SANCTIONED_ROOT = {
    "README.md", "README", "CHANGELOG.md", "LICENSE", "LICENSE.md",
    "LICENSE-MIT", "LICENSE-APACHE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md",
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "copilot-instructions.md",
    "backlog.md", "checklist.md", "gap_audit.md",
    "Cargo.toml", "Cargo.lock", "rust-toolchain.toml", "rustfmt.toml",
    "clippy.toml", "deny.toml", "book.toml", "pyproject.toml",
    ".gitignore", ".gitattributes", ".gitmodules", ".envrc", ".git",
    "Makefile", "justfile", "pytest.ini", ".check_mdbook_links_allowlist",
}

# A submodule's `.git` is a gitlink *file*, not a directory, so it would
# otherwise be counted as unfiled root sprawl in every member repository.

CFG_TEST_MOD = (
    r"#\[cfg\(\s*(?:all\(\s*)?test\b[^\]]*\]\s*"   # #[cfg(test)] / #[cfg(all(test, ...))]
    r"(?:#\[[^\]]*\]\s*)*"                          # any further attributes
    r"(?:pub(?:\([^)]*\))?\s+)?mod\s+{stem}\s*;"    # [pub] mod <stem>;
)

TYPE_NAME = re.compile(r"(?:^|_)(?:f16|bf16|f32|f64|u8|u16|u32|u64|i8|i16|i32|i64)(?:_|$)")
FN_DEF = re.compile(r"\bfn\s+(\w+)")
EXISTENCE_ONLY = re.compile(r"assert!\s*\(\s*[^();]{0,120}\.is_(?:ok|err|some|none)\s*\(\s*\)\s*,?\s*[^();]*\)")
PRINT_DBG = re.compile(r"\b(?:println!|eprintln!|print!|eprint!|dbg!)")
SLEEP = re.compile(r"(?:thread|time)::sleep\b")
MARKER = re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b")
REEXPORT_SHIM = re.compile(r"\bpub\s+use\s+[^;]*\bas\s+\w+\s*;")
COMMENTED_CODE = re.compile(
    r"^\s*//\s?(?:let\s|fn\s|use\s|pub\s|impl\s|match\s|if\s|for\s|while\s"
    r"|struct\s|enum\s|return\b|assert)"
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
    "pull_request_target_use", "missing_cargo_lock", "orphan_modules",
]

MOD_DECL = re.compile(r"\bmod\s+([A-Za-z_][A-Za-z0-9_]*)\s*[;{]")
PATH_ATTR = re.compile(
    r"#\[\s*path\s*=\s*\"([^\"]+)\"\s*\]\s*(?:pub(?:\([^)]*\))?\s*)?$"
)

SHA_PIN = re.compile(r"^\s*(?:-\s+)?uses:\s*[^\s@#]+@([A-Za-z0-9._/-]+)", re.MULTILINE)


def scan_workflows(repo: Path, c: dict[str, int]) -> None:
    """Workflow-hygiene classes (engineering_gates): SHA pins, bounds, tokens."""
    wf_dir = repo / ".github" / "workflows"
    if not wf_dir.is_dir():
        return
    for wf in sorted(wf_dir.iterdir()):
        if wf.suffix not in (".yml", ".yaml"):
            continue
        text = wf.read_text(encoding="utf-8", errors="replace")
        c["tag_pinned_actions"] += sum(
            1 for m in SHA_PIN.finditer(text)
            if not re.fullmatch(r"[0-9a-f]{40}", m.group(1))
        )
        if "timeout-minutes" not in text:
            c["workflow_missing_timeout"] += 1
        if "permissions:" not in text:
            c["workflow_missing_permissions"] += 1
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
    return [base / f"{name}.rs", base / name / "mod.rs"]


def _walk_mods(root: Path, seen: set[Path]) -> None:
    """Depth-first close the `mod` graph reachable from one crate root."""
    root = root.resolve()
    if root in seen or not root.is_file():
        return
    seen.add(root)
    text = root.read_text(encoding="utf-8", errors="replace")
    for m in MOD_DECL.finditer(text):
        attr = PATH_ATTR.search(text[:m.start()].rstrip())
        for cand in _child_candidates(root, m.group(1), attr.group(1) if attr else None):
            if cand.is_file():
                _walk_mods(cand, seen)
                break


def count_orphan_modules(repo: Path) -> int:
    """`.rs` files under a crate `src/` that no `mod` declaration reaches.

    Cargo compiles only what the module graph names, so an undeclared file is
    invisible to rustc, clippy, and the test runner while every text-based
    scan (including this one's other classes) still counts it — dead weight
    that inflates debt figures and silently rots. Crate roots are the targets
    Cargo builds: `src/lib.rs`, `src/main.rs`, `src/bin/*.rs`, and
    `src/bin/<name>/main.rs`.
    """
    sources: set[Path] = set()
    roots: list[Path] = []
    for manifest in repo.rglob("Cargo.toml"):
        if PRUNE_DIRS.intersection(manifest.parts) or \
                any(p.startswith("target") for p in manifest.parts):
            continue
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


def declared_cfg_test(entry: Path) -> bool:
    """True when the parent module declares this file under `#[cfg(test)]`.

    The co-located sidecar convention (`src/foo/tests.rs` declared by
    `src/foo/mod.rs` as `#[cfg(test)] mod tests;`) puts the gate in the
    *parent*, so neither a path-part match nor an in-file `#[cfg(test)]`
    sees it. Without this check such files scan as production code.
    """
    pat = re.compile(CFG_TEST_MOD.format(stem=re.escape(entry.stem)), re.MULTILINE)
    parent = entry.parent
    for cand in (parent / "mod.rs", parent / "lib.rs", parent / "main.rs",
                 parent.with_suffix(".rs")):
        if cand == entry or not cand.is_file():
            continue
        if pat.search(cand.read_text(encoding="utf-8", errors="replace")):
            return True
    return False


def git_output(*args: str, cwd: Path = ROOT) -> str:
    """Run a read-only Git query and return its output or a useful error."""
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
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


def gitlink_revision(root_revision: str, path: str) -> str:
    """Return the gitlink commit recorded at *path* in a root revision."""
    fields = git_output("ls-tree", root_revision, "--", path).strip().split(maxsplit=3)
    if len(fields) != 4 or fields[0] != "160000" or fields[1] != "commit":
        raise RuntimeError(f"{root_revision}:{path} is not a gitlink")
    return fields[2]


def check_clean_revision(revision: str) -> None:
    """Require the live checkout to represent the requested revision exactly.

    A clean checkout is already a materialized revision snapshot. Refusing a
    dirty or mismatched tree keeps the normal gate reproducible without
    creating twenty temporary provider checkouts; `--worktree` is the explicit
    escape hatch for an intentional live-tree audit.
    """
    root_revision = git_output(
        "rev-parse", "--verify", f"{revision}^{{commit}}"
    ).strip()
    current_revision = git_output("rev-parse", "HEAD").strip()
    if root_revision != current_revision:
        raise RuntimeError(
            f"root checkout is {current_revision[:12]}, not requested {root_revision[:12]}"
        )
    root_status = git_output("status", "--porcelain").strip()
    if root_status:
        raise RuntimeError("root worktree is dirty; rerun with --worktree for live state")
    for name in sorted(registered_member_names_at(ROOT)):
        provider = ROOT / "repos" / name
        if not provider.is_dir():
            raise RuntimeError(f"provider checkout missing for {name}; initialize submodules")
        expected = gitlink_revision(root_revision, f"repos/{name}")
        actual = git_output("rev-parse", "HEAD", cwd=provider).strip()
        if actual != expected:
            raise RuntimeError(
                f"repos/{name} is {actual[:12]}, not recorded gitlink {expected[:12]}"
            )
        if git_output("status", "--porcelain", cwd=provider).strip():
            raise RuntimeError(
                f"repos/{name} worktree is dirty; rerun with --worktree for live state"
            )


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
                testish = bool(TEST_PATH_PARTS.intersection(entry.parent.parts)) or \
                    declared_cfg_test(entry)
                yield entry, testish


def split_test_region(text: str) -> tuple[str, str]:
    """Split a source file at its inline test module, if any."""
    idx = text.find("#[cfg(test)]")
    return (text, "") if idx < 0 else (text[:idx], text[idx:])


def strip_doc_comments(text: str) -> str:
    """Drop `///` and `//!` lines: their code fences are doctests, not production."""
    return "\n".join(
        ln for ln in text.splitlines()
        if not ln.lstrip().startswith(("///", "//!"))
    )


def scan_repo(repo: Path) -> dict[str, int]:
    c = dict.fromkeys(CLASSES, 0)
    has_cargo = (repo / "Cargo.toml").is_file()

    for path, testish in rust_files(repo):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.count("\n") + 1
        if lines > 500:
            c["oversized_files"] += 1
        if path.name in ("lib.rs", "mod.rs"):
            body = sum(
                1 for ln in text.splitlines() if not MANIFEST_PASSTHROUGH.match(ln)
            )
            if body > 20:
                c["manifest_implementation"] += 1
            if path.name == "lib.rs" and "deny(missing_docs" not in text \
                    and "forbid(missing_docs" not in text and not testish:
                c["missing_deny_docs"] += 1
        if path.stem in ("utils", "helpers", "misc", "common"):
            c["junk_drawer_modules"] += 1

        prod, test = ("", text) if testish else split_test_region(text)
        is_bin = path.name == "main.rs" or "bin" in path.parts or "benches" in path.parts
        # Doc-comment bodies are doctests, i.e. test code. Counting `.unwrap()`
        # inside `///` lines reported 23 "production unwraps" for a repo whose
        # workspace denies `unwrap_used` outright — every one was a doc example.
        c["unwrap_production"] += strip_doc_comments(prod).count(".unwrap()")
        c["allow_sites"] += prod.count("#[allow(")
        c["markers"] += len(MARKER.findall(prod))
        c["reexport_shims"] += len(REEXPORT_SHIM.findall(prod))
        c["type_suffixed_fns"] += sum(
            1 for m in FN_DEF.finditer(prod) if TYPE_NAME.search(m.group(1))
        )
        c["commented_out_code"] += sum(
            1 for ln in prod.splitlines() if COMMENTED_CODE.match(ln)
        )
        if not is_bin:
            c["print_dbg"] += len(PRINT_DBG.findall(prod))
        c["existence_only_assertions"] += len(EXISTENCE_ONLY.findall(test))
        c["sleep_synced_tests"] += len(SLEEP.findall(test))

    c["root_sprawl"] = count_root_sprawl(repo)
    c["target_forks"] = sum(1 for e in repo.iterdir() if is_cargo_target_dir(e))
    c["gitattributes_missing"] = lf_policy_missing(repo)
    c["orphan_modules"] = count_orphan_modules(repo)
    if has_cargo:
        nx = repo / ".config" / "nextest.toml"
        if not (nx.is_file() and "slow-timeout" in nx.read_text(errors="replace")):
            c["nextest_budget_missing"] = 1
        manifest = (repo / "Cargo.toml").read_text(errors="replace")
        if "[workspace]" in manifest and "[workspace.lints]" not in manifest:
            c["workspace_lints_missing"] = 1
        if not (repo / "Cargo.lock").is_file():
            c["missing_cargo_lock"] = 1
    scan_workflows(repo, c)
    return c


def scan_stack(stack_root: Path = ROOT) -> dict[str, dict[str, int]]:
    out = {}
    member_root = stack_root / "repos"
    members = registered_member_names_at(stack_root)
    meta = dict.fromkeys(CLASSES, 0)
    if member_root.is_dir():
        for repo in sorted(member_root.iterdir()):
            if not repo.is_dir() or repo.name.startswith("."):
                continue
            if repo.name in members:
                out[repo.name] = scan_repo(repo)
            elif stack_root == ROOT and not is_git_ignored(repo):
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
        help="explicitly scan the live worktree, including uncommitted changes",
    )
    args = parser.parse_args()
    mode = args.mode
    try:
        if not args.worktree:
            check_clean_revision(args.revision)
        results = scan_stack(ROOT)
    except RuntimeError as exc:
        print(f"conformance scan unavailable: {exc}", file=sys.stderr)
        print("use --worktree only when a live dirty-tree scan is intentional", file=sys.stderr)
        return 2

    if mode == "report":
        report(results)
        return 0
    if mode == "generate":
        BASELINE.write_text(
            json.dumps(results, indent=1, sort_keys=True) + "\n", newline="\n"
        )
        print(f"baseline written: {BASELINE.relative_to(ROOT)}")
        report(results)
        return 0

    if not BASELINE.is_file():
        print("no committed baseline; run `generate` first", file=sys.stderr)
        return 1
    base = json.loads(BASELINE.read_text())
    regressions, tightenings = [], []
    for repo, counts in results.items():
        for k, v in counts.items():
            b = base.get(repo, {}).get(k, 0)
            if v > b:
                regressions.append(f"{repo}/{k}: {b} -> {v}")
            elif v < b:
                tightenings.append(f"{repo}/{k}: {b} -> {v}")
    for t in tightenings:
        print(f"tightened (update baseline): {t}")
    for r in regressions:
        print(f"RATCHET VIOLATION: {r}")
    print(f"{len(regressions)} regression(s), {len(tightenings)} tightening(s)")
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
