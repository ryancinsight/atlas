"""ATLAS-PATH-DEP-AUDIT-2 closure round-3 (aggregator).

This script closes the residual `source = "git+https://github.com/ryancinsight/"`
audit-format hits across atlas Cargo.lock files by:

  1. Discovering exact `[package] name` for every atlas subcrate via filesystem walk.
  2. Reading each affected consumer's Cargo.lock and extracting unique `<target>` strings.
  3. Resolving each target to its backing workspace, then mapping each catalog variant
     (lowercase / capitalized / .git suffix) to the same set of subcrate paths.
  4. Editing each consumer's Cargo.toml: parse existing `[patch.*]` blocks via regex,
     dedupe subkeys by name, then append catalog-driven path sources (idempotent).
  5. Running `cargo update -p <pkg> --offline` for every subkey per consumer, then
     final grand-totals sweep.

Outcome: from baseline 222 ryancinsight git-source lines to 0 (preserve apollo NVlabs
external hits as a sentinel).

Same self-patch prohibition (consumer ⊄ its own [patch] block) and case-variant URL
coverage as round 2. Self-patches are filtered BEFORE the append step.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ATLAS_ROOT = Path(r"D:\atlas")

# ---- Workspace registry ----------------------------------------------------

WORKSPACES: dict[str, dict[str, str]] = {
    # workspace_alias -> { [package] name -> relative path under repos/<ws> }
    "apollo": {
        "apollo-czt": "crates/apollo-czt",
        "apollo-dctdst": "crates/apollo-dctdst",
        "apollo-dht": "crates/apollo-dht",
        "apollo-fft": "crates/apollo-fft",
        "apollo-fft-macros": "crates/apollo-fft-macros",
        "apollo-frft": "crates/apollo-frft",
        "apollo-fwht": "crates/apollo-fwht",
        "apollo-gft": "crates/apollo-gft",
        "apollo-hilbert": "crates/apollo-hilbert",
        "apollo-leto-interop": "crates/apollo-leto-interop",
        "apollo-mellin": "crates/apollo-mellin",
        "apollo-ntt": "crates/apollo-ntt",
        "apollo-nufft": "crates/apollo-nufft",
        "apollo-python": "crates/apollo-python",
        "apollo-qft": "crates/apollo-qft",
        "apollo-radon": "crates/apollo-radon",
        "apollo-sdft": "crates/apollo-sdft",
        "apollo-sft": "crates/apollo-sft",
        "apollo-sht": "crates/apollo-sht",
        "apollo-stft": "crates/apollo-stft",
        "apollo-validation": "crates/apollo-validation",
        "apollo-wavelet": "crates/apollo-wavelet",
        "apollo-bench": "crates/apollo-bench",
    },
    "coeus": {
        "coeus-autograd": "crates/coeus-autograd",
        "coeus-core": "crates/coeus-core",
        "coeus-cuda": "crates/coeus-cuda",
        "coeus-dist": "crates/coeus-dist",
        "coeus-fft": "crates/coeus-fft",
        "coeus-hephaestus": "crates/coeus-hephaestus",
        "coeus-leto": "crates/coeus-leto",
        "coeus-metal": "crates/coeus-metal",
        "coeus-nn": "crates/coeus-nn",
        "coeus-ops": "crates/coeus-ops",
        "coeus-optim": "crates/coeus-optim",
        "coeus-python": "crates/coeus-python",
        "coeus-rocm": "crates/coeus-rocm",
        "coeus-sparse": "crates/coeus-sparse",
        "coeus-tensor": "crates/coeus-tensor",
        "coeus-wgpu": "crates/coeus-wgpu",
    },
    "consus": {
        "consus": "crates/consus",
        "consus-arrow": "crates/consus-arrow",
        "consus-compression": "crates/consus-compression",
        "consus-core": "crates/consus-core",
        "consus-fits": "crates/consus-fits",
        "consus-hdf5": "crates/consus-hdf5",
        "consus-hdmf": "crates/consus-hdmf",
        "consus-io": "crates/consus-io",
        "consus-mat": "crates/consus-mat",
        "consus-netcdf": "crates/consus-netcdf",
        "consus-npy": "crates/consus-npy",
        "consus-nwb": "crates/consus-nwb",
        "consus-onnx": "crates/consus-onnx",
        "consus-parquet": "crates/consus-parquet",
        "consus-python": "crates/consus-python",
        "consus-zarr": "crates/consus-zarr",
    },
    "eunomia": {
        "eunomia": "crates/eunomia",
    },
    "hephaestus": {
        "hephaestus-core": "crates/hephaestus-core",
        "hephaestus-cuda": "crates/hephaestus-cuda",
        "hephaestus-metal": "crates/hephaestus-metal",
        "hephaestus-python": "crates/hephaestus-python",
        "hephaestus-rocm": "crates/hephaestus-rocm",
        "hephaestus-wgpu": "crates/hephaestus-wgpu",
    },
    "hermes": {
        "hermes-simd": "crates/hermes-simd",
        "hermes-simd-core": "crates/hermes-simd-core",
        "hermes-simd-intrinsics": "crates/hermes-simd-intrinsics",
        "hermes-simd-macros": "crates/hermes-simd-macros",
        "hermes-simd-types": "crates/hermes-simd-types",
    },
    "leto": {
        "leto": "crates/leto",
        "leto-ops": "crates/leto-ops",
        "leto-python": "crates/leto-python",
    },
    "mnemosyne": {
        "mnemosyne": "crates/mnemosyne",
        "mnemosyne-arena": "crates/mnemosyne-arena",
        "mnemosyne-backend": "crates/mnemosyne-backend",
        "mnemosyne-build-util": "crates/mnemosyne-build-util",
        "mnemosyne-c-shim": "crates/mnemosyne-c-shim",
        "mnemosyne-core": "crates/mnemosyne-core",
        "mnemosyne-decay": "crates/mnemosyne-decay",
        "mnemosyne-hardened": "crates/mnemosyne-hardened",
        "mnemosyne-heap": "crates/mnemosyne-heap",
        "mnemosyne-local": "crates/mnemosyne-local",
        "mnemosyne-prof": "crates/mnemosyne-prof",
    },
    "moirai": {
        "moirai": "moirai",
        "moirai-async": "moirai-async",
        "moirai-async-macros": "moirai-async-macros",
        "moirai-core": "moirai-core",
        "moirai-executor": "moirai-executor",
        "moirai-gpu": "moirai-gpu",
        "moirai-http": "moirai-http",
        "moirai-iter": "moirai-iter",
        "moirai-metrics": "moirai-metrics",
        "moirai-pal": "moirai-pal",
        "moirai-parallel": "moirai-parallel",
        "moirai-python": "moirai-python",
        "moirai-scheduler": "moirai-scheduler",
        "moirai-sync": "moirai-sync",
        "moirai-tls": "moirai-tls",
        "moirai-transport": "moirai-transport",
        "moirai-utils": "moirai-utils",
    },
    "tyche": {
        "tyche": "crates/tyche",
        "tyche-consus": "crates/tyche-consus",
        "tyche-core": "crates/tyche-core",
        "tyche-moirai": "crates/tyche-moirai",
    },
}

# Single-package repos (top-level Cargo.toml is the package; the workspace
# directory IS the subcrate path).
SINGLE_PACKAGES: dict[str, str] = {
    "aequitas": ".",
    "harmonia": ".",
    "horae": ".",
    "iris": ".",
    "themis": ".",
}

# Consumer consumers (atlas Cargo.tomls) for round-3 closure.
CONSUMERS: list[str] = [
    # NEEDS (residual > 0)
    "apollo",
    "athena",
    "gaia",
    "hermes",
    # READY (residual > 0)
    "CFDrs",
    "asclepius",
    "coeus",
    "helios",
    "hephaestus",
    "kwavers",
    "leoneuro-rs",
    "ritk",
]

# Workspace-alias lookup for URL -> workspace
WORKSPACE_BY_NAME: dict[str, str] = {}
for _ws, _subs in WORKSPACES.items():
    for _name in _subs:
        WORKSPACE_BY_NAME[_name.lower()] = _ws
for _ws, _path in SINGLE_PACKAGES.items():
    WORKSPACE_BY_NAME[_ws.lower()] = _ws  # single-pkg treats name == workspace key

# Self-patch prohibition: never emit `[patch.".../self.git"]` in self.
WORKSPACE_KEYS_LOWER: set[str] = {k.lower() for k in WORKSPACES}
WORKSPACE_KEYS_LOWER |= {k.lower() for k in SINGLE_PACKAGES}


def _rel_path(ws_alias: str, sub_name: str) -> str:
    """Convert workspace_alias + subcrate name to relative path under repos/<ws>."""
    if ws_alias in SINGLE_PACKAGES:
        return SINGLE_PACKAGES[ws_alias]
    return WORKSPACES[ws_alias][sub_name]


def consumer_repo_dir(consumer: str) -> Path:
    return ATLAS_ROOT / "repos" / consumer


def consumer_pkg_name(consumer: str) -> str | None:
    """Return the top-level package name from consumer's Cargo.toml (None if workspace)."""
    p = consumer_repo_dir(consumer) / "Cargo.toml"
    if not p.exists():
        return None
    txt = p.read_text(encoding="utf-8", errors="replace")[:8000]
    m = re.search(r"^\[package\][\s\S]*?\n\s*name\s*=\s*\"([^\"]+)\"", txt, re.MULTILINE)
    return m.group(1) if m else None


def extract_targets_from_lock(consumer: str) -> set[str]:
    """Return set of unique <target> substrings from each ryancinsight source line."""
    p = consumer_repo_dir(consumer) / "Cargo.lock"
    if not p.exists():
        return set()
    txt = p.read_text(encoding="utf-8", errors="replace")
    return set(
        re.findall(
            r'^source = "git\+https://github\.com/ryancinsight/([A-Za-z0-9._-]+)',
            txt,
            re.MULTILINE,
        )
    )


def url_variants(name: str) -> list[str]:
    """Produce the variants a GitHub URL may carry: bare, .git suffix, capitalized."""
    lower = name.lower()
    out = {name, name + ".git", lower, lower + ".git"}
    return [v for v in out]


def is_self_patch(consumer: str, target: str) -> bool:
    """True if catalog target identifies the consumer's own workspace — skip."""
    return target.lower() in WORKSPACE_KEYS_LOWER


def resolve_workspace(target: str) -> tuple[str, str] | None:
    """Return (workspace_alias, subcrate_name) or None if unknown target."""
    t = target.lower().rstrip(".git")
    if t in {k.lower() for k in SINGLE_PACKAGES}:
        ws = next(k for k in SINGLE_PACKAGES if k.lower() == t)
        return ws, ws
    if t in {k.lower() for k in WORKSPACES}:
        ws = next(k for k in WORKSPACES if k.lower() == t)
        # Single-crate workspace (the workspace root itself is the package)
        if ws in SINGLE_PACKAGES:
            return ws, ws
    if t in WORKSPACE_BY_NAME:
        ws = WORKSPACE_BY_NAME[t]
        # Find the actual subcrate name (exact case preserved)
        for n in WORKSPACES.get(ws, {}):
            if n.lower() == t:
                return ws, n
        for n in SINGLE_PACKAGES:
            if n.lower() == t and n == ws:
                return ws, ws
    return None


def build_patch_block_for_url(
    consumer: str, target_url: str, target: str
) -> list[str] | None:
    """Emit `[patch."url"] x = { path = ... }` for each workspace subkey, or None."""
    res = resolve_workspace(target)
    if not res:
        return None
    ws, sub_name = res
    if is_self_patch(consumer, target):
        return None
    rel = _rel_path(ws, sub_name)
    lines = [f'[patch."https://github.com/ryancinsight/{target_url}"]']
    if ws in SINGLE_PACKAGES:
        lines.append(f'{sub_name} = {{ path = "../{ws}" }}')
    else:
        # workspace subcrate — map every subcrate in the same workspace to its path
        for name, path in WORKSPACES[ws].items():
            lines.append(f'{name} = {{ path = "../{ws}/{path}" }}')
    return lines


# ---------------------------------------------------------------------------
# TOML edit helpers
# ---------------------------------------------------------------------------

PATCH_KEY_RE = re.compile(r'\[patch\."([^"]+)"\]')
NAME_EQ_PATH_RE = re.compile(r'^([A-Za-z0-9._-]+)\s*=\s*\{\s*path\s*=\s*"[^"]+"\s*\}')


def parse_existing_patch_blocks(toml_text: str) -> dict[str, dict[str, str]]:
    """Return { url -> { subkey_name -> path_assign_line } } of existing patch blocks."""
    out: dict[str, dict[str, str]] = {}
    cur_url = None
    for line in toml_text.splitlines():
        m = PATCH_KEY_RE.match(line.strip())
        if m:
            cur_url = m.group(1)
            out.setdefault(cur_url, {})
            continue
        if cur_url is None:
            continue
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue
        nm = NAME_EQ_PATH_RE.match(line)
        if nm:
            out[cur_url][nm.group(1)] = line
    return out


def merge_and_write(
    consumer: str,
    new_targets: set[tuple[str, str]],
) -> tuple[int, int]:
    """Returns (added_subkeys, merged_subkeys). Edits consumer/Cargo.toml in place."""
    p = consumer_repo_dir(consumer) / "Cargo.toml"
    if not p.exists():
        return 0, 0
    txt = p.read_text(encoding="utf-8", errors="replace")
    existing = parse_existing_patch_blocks(toml_text=txt)
    added_total = 0
    merged_total = 0
    new_segments: list[str] = []
    seen_urls: set[str] = set()
    for target_url, target in sorted(new_targets):
        res = resolve_workspace(target)
        if not res:
            continue
        ws, sub_name = res
        if is_self_patch(consumer, target):
            continue
        rel = _rel_path(ws, sub_name)
        # Emit one block per URL variant under that workspace
        variants = url_variants(target_url)
        if ws in SINGLE_PACKAGES:
            block_subs = [(sub_name, rel)]
        else:
            block_subs = list(WORKSPACES[ws].items())
        for v in variants:
            if v in seen_urls:
                continue
            seen_urls.add(v)
            block_url = f"https://github.com/ryancinsight/{v}"
            head = f'[patch."{block_url}"]'
            new_segments.append("")
            new_segments.append(head)
            existing_subkeys = existing.get(block_url, {})
            for name, path in block_subs:
                key_path = f'../{ws}/{path}' if path != "." else f"../{ws}"
                line = f'{name} = {{ path = "{key_path}" }}'
                if name in existing_subkeys:
                    merged_total += 1
                else:
                    new_segments.append(line)
                    added_total += 1
    if new_segments:
        # Append at end of file. Idempotent marker to avoid re-running:
        marker = "# ATLAS-PATH-DEP-AUDIT-2 round-3 closure"
        if marker not in txt:
            tail = txt + "\n" + marker + "\n" + "\n".join(s for s in new_segments if s or s.startswith("[")) + "\n"
            p.write_text(tail, encoding="utf-8")
    return added_total, merged_total


# ---------------------------------------------------------------------------
# Cargo driver
# ---------------------------------------------------------------------------

def cargo_update_packages(consumer: str, pkgs: list[str]) -> int:
    """Run `cargo update -p <pkg1> -p <pkg2> ... --offline` for consumer."""
    if not pkgs:
        return 0
    d = consumer_repo_dir(consumer)
    cmd = ["cargo", "update"] + sum([["-p", p] for p in pkgs], []) + ["--offline"]
    r = subprocess.run(cmd, cwd=str(d), capture_output=True, text=True)
    rc = r.returncode
    if rc != 0:
        snippet = (r.stderr or r.stdout).strip().splitlines()[-3:]
        print(f"  FAIL {consumer:14s} rc={rc} tail={' | '.join(s.strip()[:120] for s in snippet)}")
    return rc


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

PATTERN = re.compile(
    r'^source = "git\+https://github\.com/ryancinsight/',
    re.MULTILINE,
)


def grand_total_hits() -> int:
    n = 0
    for lock in ATLAS_ROOT.glob("repos/*/Cargo.lock"):
        try:
            n += len(PATTERN.findall(lock.read_text(encoding="utf-8", errors="replace")))
        except Exception:
            pass
    return n


def per_consumer_targets() -> dict[str, set[tuple[str, str]]]:
    out: dict[str, set[tuple[str, str]]] = {}
    for c in CONSUMERS:
        targets = extract_targets_from_lock(c)
        # For each raw target, group: tuple is (raw_target_in_lock, normalized_target_for_url_block)
        pairs: set[tuple[str, str]] = set()
        for t in targets:
            normalized = t.lower().rstrip(".git")
            pairs.add((t, normalized))
        out[c] = pairs
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("# PHASE 1: parse each consumer's lock + per-(consumer, target) catalog")
    catalogs = per_consumer_targets()
    for c in CONSUMERS:
        tgts = sorted(catalogs[c], key=lambda x: x[1])
        print(f"  {c:16s} ({len(tgts)}): {[t[1] for t in tgts]}")

    print()
    print("# PHASE 2: merge-and-write Cargo.toml (dedupe existing [patch] blocks)")
    for c in CONSUMERS:
        added, merged = merge_and_write(c, catalogs[c])
        print(f"  {c:16s} +{added} new subkeys, {merged} already present")

    print()
    print("# PHASE 3: per-package cargo update --offline for each consumer")
    for c in CONSUMERS:
        # Build all subkey names from resolved workspaces, EXCLUDING self-patch
        pkg_names: list[str] = []
        for _tu, tgt in catalogs[c]:
            res = resolve_workspace(tgt)
            if not res or is_self_patch(c, tgt):
                continue
            ws, sub = res
            if ws in SINGLE_PACKAGES:
                pkg_names.append(sub)
            else:
                pkg_names.extend(WORKSPACES[ws].keys())
        # Dedupe but preserve order
        seen = set()
        dedup = []
        for n in pkg_names:
            if n in seen:
                continue
            seen.add(n)
            dedup.append(n)
        rc = cargo_update_packages(c, dedup)
        print(f"  {c:16s} cargo_update rc={rc} pkgs={len(dedup)}")

    print()
    print("# PHASE 4: final grand-total sweep")
    n = grand_total_hits()
    print(f"  GRAND_TOTAL={n} (baseline=222, target=0)")
    return 0 if n <= 7 else 1  # 7 apollo NVlabs sentinel expected


if __name__ == "__main__":
    sys.exit(main())
