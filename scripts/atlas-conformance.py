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
    generate    write scripts/conformance-baseline.json from the live tree
    check       re-scan and fail (exit 1) on any per-repo class increase
                over the committed baseline; decreases print as tightening
                candidates for a baseline update in the same change

Run from anywhere: paths are anchored to this file's parent repository.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMBER_ROOT = ROOT / "repos"
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
    ".gitignore", ".gitattributes", ".gitmodules", ".envrc",
    "Makefile", "justfile",
}

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
    "member_namespace_pollution",
]


def registered_members() -> set[str]:
    """Member directory names registered in .gitmodules — the scan universe.

    Scanning only registered members is what keeps the baseline an artifact
    of the documented stack: an unregistered, git-ignored directory is the
    sanctioned private-consumer trace (never named in stack artifacts), and
    an unregistered, un-ignored one is namespace pollution counted without
    being named (architecture_scoping: member namespace hygiene).
    """
    gm = ROOT / ".gitmodules"
    if not gm.is_file():
        return set()
    return {
        m.group(1)
        for m in re.finditer(r"path\s*=\s*repos/([^\s/]+)", gm.read_text(errors="replace"))
    }


def is_git_ignored(path: Path) -> bool:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", str(path.relative_to(ROOT))],
        capture_output=True,
    ).returncode == 0


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
                testish = bool(TEST_PATH_PARTS.intersection(entry.parts))
                yield entry, testish


def split_test_region(text: str) -> tuple[str, str]:
    """Split a source file at its inline test module, if any."""
    idx = text.find("#[cfg(test)]")
    return (text, "") if idx < 0 else (text[:idx], text[idx:])


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
        is_bin = path.name == "main.rs" or "bin" in path.parts
        c["unwrap_production"] += prod.count(".unwrap()")
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

    for entry in repo.iterdir():
        if entry.is_file() and entry.name not in SANCTIONED_ROOT:
            c["root_sprawl"] += 1
        if entry.is_dir() and entry.name.startswith("target") and repo != ROOT:
            c["target_forks"] += 1

    ga = repo / ".gitattributes"
    if not (ga.is_file() and "text=auto" in ga.read_text(errors="replace")):
        c["gitattributes_missing"] = 1
    if has_cargo:
        nx = repo / ".config" / "nextest.toml"
        if not (nx.is_file() and "slow-timeout" in nx.read_text(errors="replace")):
            c["nextest_budget_missing"] = 1
        manifest = (repo / "Cargo.toml").read_text(errors="replace")
        if "[workspace]" in manifest and "[workspace.lints]" not in manifest:
            c["workspace_lints_missing"] = 1
    return c


def scan_stack() -> dict[str, dict[str, int]]:
    out = {}
    members = registered_members()
    meta = dict.fromkeys(CLASSES, 0)
    if MEMBER_ROOT.is_dir():
        for repo in sorted(MEMBER_ROOT.iterdir()):
            if not repo.is_dir() or repo.name.startswith("."):
                continue
            if repo.name in members:
                out[repo.name] = scan_repo(repo)
            elif not is_git_ignored(repo):
                meta["member_namespace_pollution"] += 1
    for entry in ROOT.iterdir():
        if entry.is_file() and entry.name not in SANCTIONED_ROOT:
            meta["root_sprawl"] += 1
    ga = ROOT / ".gitattributes"
    if not (ga.is_file() and "text=auto" in ga.read_text(errors="replace")):
        meta["gitattributes_missing"] = 1
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
    mode = parser.parse_args().mode
    results = scan_stack()

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
