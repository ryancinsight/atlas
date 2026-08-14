#!/usr/bin/env python3
"""Compute the dependency-ordered crates.io publish sequence for the Atlas stack.

crates.io rewrites a ``{ version, git }`` dependency to a registry dependency when
packaging, so a git source is not itself a publishing blocker — the dependency
simply has to exist on crates.io already. Verified 2026-07-28 by packaging
``aequitas``, which fails with::

    no matching package named `eunomia` found
    location searched: crates.io index

That makes publish order the real constraint: a crate is publishable only once
every first-party crate it depends on is published. This script derives that
order from the manifests rather than from a hand-maintained list, which would
drift on the first new crate.

Reads every ``Cargo.toml`` under ``repos/`` (excluding directories absent from
``.gitmodules``), builds the first-party dependency graph over publishable
packages, and emits a topological order. Normal and build dependencies constrain
the order; dev-dependencies are reported separately because they do not need to
be on the registry for ``cargo publish --no-verify`` and they routinely form
legal cycles.

Exit status is 0 when a total order exists over normal/build edges, 1 when a
cycle makes the order undefined, and 2 on a usage or parse error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

# Directories under repos/ that are not part of the recorded stack. Anything not
# in .gitmodules is local work (README "Revision contract"); the private
# consumer is additionally never named in stack artifacts.
DEP_SECTIONS_ORDERING = ("dependencies", "build-dependencies")
DEP_SECTIONS_REPORTED = ("dev-dependencies",)


def recorded_packages(root: Path) -> set[str]:
    """Return the submodule directory names recorded in .gitmodules."""
    gitmodules = root / ".gitmodules"
    if not gitmodules.is_file():
        raise SystemExit(f"{gitmodules} not found; run from the Atlas root")
    text = gitmodules.read_text(encoding="utf-8")
    return {Path(m).name for m in re.findall(r"^\s*path\s*=\s*(.+?)\s*$", text, re.M)}


def iter_manifests(root: Path, packages: set[str]):
    """Yield (repo_name, manifest_path) for every Cargo.toml in a recorded package."""
    for repo in sorted(packages):
        repo_dir = root / "repos" / repo
        if not repo_dir.is_dir():
            continue
        for manifest in repo_dir.rglob("Cargo.toml"):
            parts = set(manifest.parts)
            if "target" in parts or "worktrees" in parts:
                continue
            yield repo, manifest


def dependency_names(table: dict, sections: tuple[str, ...]) -> set[str]:
    """Collect dependency names from the given sections, including target-specific ones."""
    names: set[str] = set()

    def harvest(container: dict) -> None:
        for section in sections:
            for name, spec in (container.get(section) or {}).items():
                # `package = "x"` renames the crate; the registry name is what matters.
                if isinstance(spec, dict) and "package" in spec:
                    names.add(spec["package"])
                else:
                    names.add(name)

    harvest(table)
    for cfg in (table.get("target") or {}).values():
        if isinstance(cfg, dict):
            harvest(cfg)
    return names


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def load_graph(root: Path):
    """Return (packages, order_edges, dev_edges, skipped, collisions)."""
    packages: dict[str, dict] = {}
    raw: dict[str, dict] = {}
    skipped: list[tuple[str, str]] = []
    collisions: dict[str, list[dict]] = defaultdict(list)

    for repo, manifest in iter_manifests(root, recorded_packages(root)):
        try:
            table = tomllib.loads(manifest.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
            skipped.append((str(manifest.relative_to(root)), f"parse error: {exc}"))
            continue
        pkg = table.get("package")
        if not pkg or "name" not in pkg:
            continue  # virtual workspace root
        name = pkg["name"]
        publishable = pkg.get("publish", True) is not False
        if name in packages:
            # One registry name cannot serve two crates. Record both sides with
            # their publish status: a collision where every copy is
            # `publish = false` is benign (internal tooling such as `xtask`),
            # but a publishable copy makes the name genuinely contested.
            collisions[name].append({"manifest": rel(manifest, root), "publishable": publishable})
            continue
        collisions[name].append({"manifest": rel(manifest, root), "publishable": publishable})
        packages[name] = {
            "repo": repo,
            "manifest": rel(manifest, root),
            "publishable": publishable,
        }
        raw[name] = table

    order_edges = {n: set() for n in packages}
    dev_edges = {n: set() for n in packages}
    for name, table in raw.items():
        first_party = set(packages)
        order_edges[name] = dependency_names(table, DEP_SECTIONS_ORDERING) & first_party
        dev_edges[name] = (
            dependency_names(table, DEP_SECTIONS_REPORTED) & first_party
        ) - order_edges[name]
        order_edges[name].discard(name)
        dev_edges[name].discard(name)

    contested = {
        name: entries
        for name, entries in collisions.items()
        if len(entries) > 1 and sum(1 for e in entries if e["publishable"]) > 0
    }
    benign = {name for name, entries in collisions.items() if len(entries) > 1} - set(contested)
    return packages, order_edges, dev_edges, skipped, contested, benign


def topo_layers(nodes: set[str], edges: dict[str, set[str]]):
    """Kahn layering restricted to `nodes`. Returns (layers, unresolved)."""
    remaining = {n: {d for d in edges[n] if d in nodes} for n in nodes}
    layers: list[list[str]] = []
    placed: set[str] = set()
    while True:
        ready = sorted(n for n, deps in remaining.items() if not (deps - placed))
        ready = [n for n in ready if n not in placed]
        if not ready:
            break
        layers.append(ready)
        placed.update(ready)
    unresolved = sorted(nodes - placed)
    return layers, unresolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    parser.add_argument(
        "--include-unpublishable",
        action="store_true",
        help="also order crates marked publish = false (shows what a flip would require)",
    )
    args = parser.parse_args()

    # Windows consoles default to a legacy codepage that mangles non-ASCII output.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    root = args.root
    packages, order_edges, dev_edges, skipped, contested, benign = load_graph(root)

    selected = {
        n for n, meta in packages.items() if meta["publishable"] or args.include_unpublishable
    }
    layers, unresolved = topo_layers(selected, order_edges)

    # A publishable crate depending on an unpublishable one can never publish as-is.
    blocked_by_unpublishable = {
        n: sorted(d for d in order_edges[n] if not packages[d]["publishable"])
        for n in selected
        if packages[n]["publishable"]
        and any(not packages[d]["publishable"] for d in order_edges[n])
    }

    if args.json:
        json.dump(
            {
                "layers": layers,
                "unresolved": unresolved,
                "blocked_by_unpublishable": blocked_by_unpublishable,
                "packages": packages,
                "skipped": skipped,
                "contested_names": contested,
                "benign_duplicate_names": sorted(benign),
                "dev_only_edges": {k: sorted(v) for k, v in dev_edges.items() if v},
            },
            sys.stdout,
            indent=2,
            sort_keys=True,
        )
        print()
        return 1 if unresolved else 0

    total = len(packages)
    pub = sum(1 for m in packages.values() if m["publishable"])
    print(f"Atlas publish order — {total} packages, {pub} publishable, {total - pub} publish = false")
    print()
    print("Wave 0 publishes first; every crate in a wave depends only on earlier waves.")
    print("A wave publishes in any internal order, so it parallelizes.")
    print()
    for i, layer in enumerate(layers):
        print(f"  wave {i} ({len(layer)}):")
        for name in layer:
            deps = sorted(order_edges[name] & selected)
            suffix = f"  <- {', '.join(deps)}" if deps else ""
            print(f"    {name}{suffix}")
        print()

    if blocked_by_unpublishable:
        print("BLOCKED — publishable crates depending on publish = false crates:")
        for name, deps in sorted(blocked_by_unpublishable.items()):
            print(f"  {name} needs {', '.join(deps)} published first")
        print()

    if unresolved:
        print("CYCLE — no total order over normal/build dependencies for:")
        for name in unresolved:
            print(f"  {name} <- {', '.join(sorted(order_edges[name] & selected))}")
        print()

    dev_cycles = {k: sorted(v) for k, v in dev_edges.items() if v and k in selected}
    if dev_cycles:
        print(f"dev-dependency-only first-party edges ({len(dev_cycles)} crates)")
        print("  These do not constrain publish order and may legally form cycles;")
        print("  they do matter for `cargo publish` without --no-verify.")
        for name, deps in sorted(dev_cycles.items()):
            print(f"    {name} <- {', '.join(deps)}")
        print()

    if contested:
        print("CONTESTED registry names — one crates.io name claimed by several manifests,")
        print("at least one of them publishable. Mark the internal copies publish = false.")
        for name, entries in sorted(contested.items()):
            print(f"  {name}:")
            for e in entries:
                flag = "PUBLISHABLE" if e["publishable"] else "publish = false"
                print(f"    {flag:<15} {e['manifest']}")
        print()

    if benign:
        print(f"duplicate names, all publish = false ({len(benign)}): {', '.join(sorted(benign))}")
        print("  Internal tooling reusing one name across repos; nothing reaches the registry.")
        print()

    if skipped:
        print(f"skipped manifests ({len(skipped)}):")
        for path, why in skipped:
            print(f"  {path}: {why}")

    return 1 if (unresolved or contested) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # surface the failure rather than a bare traceback
        print(f"publish-order: {exc}", file=sys.stderr)
        sys.exit(2)
