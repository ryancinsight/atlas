"""Discover exact [package] name for every atlas subcrate.

Outputs path -> name mapping for all sub-crates under each atlas workspace.
Used to build correct [patch.Y.git] blocks for ATLAS-PATH-DEP-AUDIT-001 closure.
"""
import os
import re

ATLAS_ROOT = r"D:\atlas"

WORKSPACES = [
    "apollo", "coeus", "eunomia", "hephaestus", "hermes",
    "leto", "tyche", "mnemosyne", "moirai",
]

PRUNE_DIRS = {
    "target", ".git", "node_modules", "docs", "examples",
    ".github", ".benchmarks", ".cargo", ".claude", ".config",
    ".pytest_cache", "tests", "src", "benches",
}


def find_crate_dirs(ws_dir):
    """Walk findings: every dir under ws that contains its own Cargo.toml."""
    p = os.path.join(ATLAS_ROOT, "repos", ws_dir)
    if not os.path.isdir(p):
        return []
    out = []
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
        rel = os.path.relpath(root, p)
        if rel == ".":
            continue
        if "Cargo.toml" in files:
            out.append(rel.replace("\\", "/"))
    return out


def name_of(ws_dir, rel):
    p = os.path.join(ATLAS_ROOT, "repos", ws_dir, rel, "Cargo.toml")
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            txt = f.read(8000)
    except Exception:
        return None
    m = re.search(
        r"^\[package\][\s\S]*?\n\s*name\s*=\s*\"([^\"]+)\"",
        txt,
        re.MULTILINE,
    )
    return m.group(1) if m else None


def main():
    print(f"ROOT={ATLAS_ROOT}")
    print("=== WORKSPACE SUBCRATES: path -> [package] name ===")
    for ws in WORKSPACES:
        subs = find_crate_dirs(ws)
        if not subs:
            print(f"# {ws}: NO crates found")
            continue
        print(f"\n# === {ws} ({len(subs)} candidates) ===")
        for s in sorted(subs):
            n = name_of(ws, s)
            marker = "OK " if n else "MISS"
            print(f"{marker} {ws:12s} | {s:40s} | {n}")


if __name__ == "__main__":
    main()
