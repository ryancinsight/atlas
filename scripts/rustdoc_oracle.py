#!/usr/bin/env python3
"""Emit and query rustdoc JSON as the machine-readable API oracle.

Per AGENTS.md `context_and_memory: code-search ladder`, rustdoc JSON is the
oracle that resolves the anti-hallucination check: before calling an
external symbol, confirm it exists in the pinned source. Like miri, it runs
under the nightly verification toolchain (`cargo +nightly rustdoc -- -Z
unstable-options --output-format json`), so it is invoked explicitly and
never rides the pinned stable build.

The JSON is emitted per library package of each Cargo stack member, then
copied to `.rustdoc-json/<member>/<sha>/<crate>.json` with a manifest
recording the covered set. `check` verifies each recorded entry against the
member's current HEAD; coverage is exactly the set present in the manifest
(rustdoc emission compiles the crate, so coverage is per-selection, unlike
the SCIP index which is cheap to emit for the whole stack).

The reader targets rustdoc JSON format_version 57 (the shape the nightly
toolchain emits): `paths` maps item id to {crate_id, path, kind} and
`index` maps item id to the item body carrying `span`, `inner`, and `name`.
Type rendering covers the common `Type` variants and falls back to a JSON
dump of the type object rather than fabricating a signature.

Modes:

    generate  emit rustdoc JSON for every covered library package at the
              member's current HEAD (use `--members` to bound the set)
    check     verify each manifest entry is present, non-empty, and covers
              the member's current HEAD; nonzero exit on drift
    api       print items whose qualified name contains a query, with kind,
              source span, and a rendered signature for functions

    python scripts/rustdoc-oracle.py generate --members leto
    python scripts/rustdoc-oracle.py check
    python scripts/rustdoc-oracle.py api SparseLuSolver
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPOS = ROOT / "repos"
INDEX_DIR = ROOT / ".rustdoc-json"
MANIFEST = INDEX_DIR / "manifest.json"
NIGHTLY = "+nightly"


def members(selected: list[str]) -> list[pathlib.Path]:
    found = []
    for path in sorted(REPOS.iterdir()):
        if not (path / "Cargo.toml").is_file():
            continue
        if selected and path.name not in selected:
            continue
        tracked = subprocess.run(
            ["git", "check-ignore", "-q", f"repos/{path.name}"],
            cwd=ROOT,
            capture_output=True,
        )
        if tracked.returncode == 0:
            continue
        found.append(path)
    return found


def head_sha(repo: pathlib.Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    )
    return proc.stdout.strip()


def lib_packages(repo: pathlib.Path) -> list[str]:
    """Package names with a library target, in metadata order."""
    proc = subprocess.run(
        ["cargo", "metadata", "--no-deps", "--format-version", "1"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip().splitlines()[-1])
    data = json.loads(proc.stdout)
    return [p["name"] for p in data["packages"] if any("lib" in k for k in p["targets"][0]["kind"])]


def rustdoc_crate_json(repo: pathlib.Path, pkg: str, timeout: int) -> pathlib.Path | None:
    """Run nightly rustdoc for one package; return the shared target JSON path.

    The emitted file lands in `target/doc/<crate>.json` under the shared
    stack target directory (configured at the stack root, so every member
    build writes there).
    """
    proc = subprocess.run(
        [
            "cargo",
            NIGHTLY,
            "rustdoc",
            "-p",
            pkg,
            "--lib",
            "--",
            "-Z",
            "unstable-options",
            "--output-format",
            "json",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else f"exit {proc.returncode}")
    candidate = ROOT / "target" / "doc" / f"{pkg.replace('-', '_')}.json"
    return candidate if candidate.is_file() and candidate.stat().st_size > 0 else None


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def generate(selected: list[str], timeout: int) -> int:
    targets = members(selected)
    if not targets:
        print("no matching stack members", file=sys.stderr)
        return 2
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    failed = 0
    for repo in targets:
        sha = head_sha(repo)
        try:
            packages = lib_packages(repo)
        except RuntimeError as exc:
            print(f"  ! {repo.name}: cargo metadata failed ({exc})", file=sys.stderr)
            failed += 1
            continue
        entry_dir = INDEX_DIR / repo.name / sha
        entry_dir.mkdir(parents=True, exist_ok=True)
        crates: dict[str, str] = {}
        for pkg in packages:
            try:
                emitted = rustdoc_crate_json(repo, pkg, timeout)
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                print(f"  ! {repo.name}: rustdoc {pkg} failed ({exc})", file=sys.stderr)
                failed += 1
                continue
            if emitted is None:
                print(f"  ! {repo.name}: rustdoc {pkg} produced no output", file=sys.stderr)
                failed += 1
                continue
            dest = entry_dir / f"{pkg.replace('-', '_')}.json"
            shutil.copy2(emitted, dest)
            crates[pkg.replace("-", "_")] = f"{repo.name}/{sha}/{dest.name}"
            print(f"indexed     {repo.name}  {pkg}  {sha[:12]}")
        if crates:
            manifest[repo.name] = {"revision": sha, "crates": crates}
        else:
            manifest.pop(repo.name, None)
        for old in (INDEX_DIR / repo.name).glob("*"):
            if old.is_dir() and old.name != sha:
                shutil.rmtree(old)
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failed:
        print(f"\n{failed} rustdoc emission(s) failed", file=sys.stderr)
        return 1
    print(f"\ncovered {len(manifest)} member(s) under {INDEX_DIR}")
    return 0


def check() -> int:
    manifest = load_manifest()
    if not manifest:
        print("no rustdoc manifest; run `generate` first", file=sys.stderr)
        return 2
    stale = 0
    for repo_name, entry in sorted(manifest.items()):
        repo = REPOS / repo_name
        if not repo.is_dir():
            stale += 1
            print(f"STALE       {repo_name}  (member missing)")
            continue
        sha = head_sha(repo)
        if entry.get("revision") != sha:
            stale += 1
            print(f"STALE       {repo_name}  (need {sha[:12]}, have {entry.get('revision', '?')[:12]})")
            continue
        missing = [c for c, rel in entry["crates"].items() if not (INDEX_DIR / rel).is_file()]
        if missing:
            stale += 1
            print(f"STALE       {repo_name}  (missing: {', '.join(missing)})")
            continue
        print(f"ok          {repo_name}  {sha[:12]}  {len(entry['crates'])} crates")
    if stale:
        print(f"\n{stale} member(s) stale. Regenerate with `python scripts/rustdoc-oracle.py generate`", file=sys.stderr)
        return 1
    print(f"\nall {len(manifest)} manifest entries fresh")
    return 0


def render_type(ty: object) -> str:
    """Render a rustdoc JSON `Type` object as source text.

    Recognized variants carry their display text; anything else is dumped
    as JSON rather than guessed, so the oracle never fabricates a type.
    """
    if not isinstance(ty, dict):
        return json.dumps(ty)
    if "primitive" in ty:
        return str(ty["primitive"])
    if "generic" in ty:
        return str(ty["generic"])
    if "infer" in ty:
        return "_"
    if "never" in ty:
        return "!"
    if "slice" in ty:
        return f"[{render_type(ty['slice'])}]"
    if "borrowed_ref" in ty:
        ref = ty["borrowed_ref"]
        lt = ref.get("lifetime") or ""
        mut = "mut " if ref.get("is_mutable") else ""
        return f"&{lt} {mut}{render_type(ref['type'])}".replace("& ", "&")
    if "raw_pointer" in ty:
        ptr = ty["raw_pointer"]
        mut = "mut " if ptr.get("is_mutable") else "const "
        return f"*{mut}{render_type(ptr['type'])}"
    if "tuple" in ty:
        return "(" + ", ".join(render_type(t) for t in ty["tuple"]) + ")"
    if "array" in ty:
        arr = ty["array"]
        return f"[{render_type(arr['type'])}; {arr.get('len', '?')}]"
    if "resolved_path" in ty:
        rp = ty["resolved_path"]
        name = rp.get("path", "?")
        args = rp.get("args")
        if isinstance(args, list) and args:
            return f"{name}<{', '.join(render_type(a) for a in args)}>"
        return name
    if "function_pointer" in ty:
        fp = ty["function_pointer"]
        sig = fp.get("sig", {})
        args = ", ".join(render_type(t) for _, t in sig.get("inputs", []))
        out = render_type(sig["output"]) if sig.get("output") is not None else ""
        prefix = "unsafe " if fp.get("is_unsafe") else ""
        abi = fp.get("abi")
        abi = f'extern "{abi}" ' if abi else ""
        return f"{prefix}{abi}fn({args}){' -> ' + out if out else ''}"
    if "impl_trait" in ty:
        return "impl " + " + ".join(render_type(t) for t in ty["impl_trait"])
    if "qualified_path" in ty:
        qp = ty["qualified_path"]
        return f"<{render_type(qp.get('self_type', '?'))} as {qp.get('trait', '?')}>::{qp.get('name', '?')}"
    if "dyn_trait" in ty:
        dyn = ty["dyn_trait"]
        tr = dyn.get("trait", {})
        name = tr.get("path") or render_type(tr.get("type", {}))
        return f"dyn {name}"
    return json.dumps(ty)


def render_signature(name: str, sig: object) -> str:
    inputs = [(n, render_type(t)) for n, t in sig.get("inputs", [])]
    args = ", ".join(f"{n}: {t}" for n, t in inputs)
    out = render_type(sig["output"]) if sig.get("output") is not None else ""
    return f"fn {name}({args})" + (f" -> {out}" if out else "")


def scan_crate(data: dict, query: str, exact: bool) -> list[str]:
    """Return display lines for items whose qualified name matches a query.

    A line is `::qualified  kind  file:line:col` with the rendered signature
    appended for function items. Tested against a synthetic rustdoc JSON
    index; `api_lookup` prefixes the member and crate for the caller.
    """
    lines = []
    for item_id, pinfo in data.get("paths", {}).items():
        qualified = "::".join(pinfo.get("path", []))
        match = qualified == query if exact else query in qualified
        if not match:
            continue
        item = data["index"].get(item_id, {})
        span = item.get("span") or {}
        loc = span.get("filename", "?")
        if "begin" in span:
            loc += f":{span['begin'][0]}:{span['begin'][1]}"
        line = f"::{qualified}  {pinfo.get('kind', '?')}  {loc}"
        fn = item.get("inner", {}).get("function")
        if fn:
            line += "\n    " + render_signature(item.get("name", "?"), fn.get("sig", {}))
        lines.append(line)
    return lines


def api_lookup(query: str, member: str | None, exact: bool, limit: int) -> int:
    manifest = load_manifest()
    if not manifest:
        print("no rustdoc manifest; run `generate` first", file=sys.stderr)
        return 2
    shown = 0
    for repo_name, entry in sorted(manifest.items()):
        if member and repo_name != member:
            continue
        for crate in sorted(entry["crates"]):
            path = INDEX_DIR / entry["crates"][crate]
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  ! {repo_name}: cannot read {crate} index ({exc})", file=sys.stderr)
                continue
            for line in scan_crate(data, query, exact):
                if shown >= limit:
                    return 0
                print(f"{repo_name}  {crate}  {line}")
                shown += 1
    if shown == 0:
        print(f"no API match for {query!r}" + (f" in {member}" if member else ""))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    gen = sub.add_parser("generate", help="emit rustdoc JSON for covered library packages")
    gen.add_argument("--members", nargs="*", help="limit to these members")
    gen.add_argument("--timeout", type=int, default=600, help="per-package rustdoc timeout (s)")

    sub.add_parser("check", help="verify manifest entries are fresh")

    api = sub.add_parser("api", help="print items whose qualified name matches a query")
    api.add_argument("query")
    api.add_argument("--member", help="limit to one member")
    api.add_argument("--exact", action="store_true", help="match the full qualified name")
    api.add_argument("--limit", type=int, default=50, help="max matches to print")

    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    if args.mode == "generate":
        return generate(args.members or [], args.timeout)
    if args.mode == "check":
        return check()
    return api_lookup(args.query, args.member, args.exact, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
