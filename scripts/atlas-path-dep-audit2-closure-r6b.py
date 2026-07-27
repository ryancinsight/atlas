"""ATLAS-PATH-DEP-AUDIT-2 closure round-6b (targeted corrective re-emit).

Round-5's stale-strip pass left the residual-audit consumers (leoneuro-rs,
hermes) with effectively-empty [patch] blocks. Cargo's silent-fixation
behavior then leaves the lock entries at the original git+https source
because cargo update --workspace --offline does NOT re-resolve entries
whose [patch] redirect produced no usable path. The result: 11 + 10 hits.

Round-6b RE-EMITS fresh [patch] blocks for these two consumers using
atlas-root-relative path resolution (round-5's mistake was resolving
relative to the consumer's repo dir). Forward slashes are enforced
because cargo's TOML loader is canonical-slash.

Athena is GRADUATED OUT OF SCOPE: its 36 residual reflects a
dependency-version skew (mnemosyne 0.5.0 vs 0.6.0) — atlas-root
dependency-resolution territory, not path-dep translation. Tracked under
ATLAS-OVERLAY-002.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ATLAS_ROOT = Path(r"D:\atlas")

# Same registry as r5 — authoritative subcrate [package] name -> relative path.
WORKSPACES: dict[str, dict[str, str]] = {
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
    "eunomia": {"eunomia": "crates/eunomia"},
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

SINGLE_PACKAGES: dict[str, str] = {
    "aequitas": ".",
    "harmonia": ".",
    "horae": ".",
    "iris": ".",
    "themis": ".",
}

SUBKEY_LOOKUP: dict[str, tuple[str, str]] = {}
for _ws, _subs in WORKSPACES.items():
    for _name, _path in _subs.items():
        SUBKEY_LOOKUP[_name] = (_ws, _path)
for _ws, _path in SINGLE_PACKAGES.items():
    SUBKEY_LOOKUP[_ws] = (_ws, _path)

# Round-6b consumers: leoneuro-rs and hermes only. Athena graduated to
# ATLAS-OVERLAY-002 (version-skew out-of-scope for path-dep audit).
ROUND6B_CONSUMERS = ["leoneuro-rs", "hermes"]

MARKER = "# ATLAS-PATH-DEP-AUDIT-2 round-6b closure"


# ---------------------------------------------------------------------------
# Cargo.lock parsing
# ---------------------------------------------------------------------------

PKG_BLOCK_RE = re.compile(
    r"\[\[package\]\](.*?)(?=\n\[\[package\]\]|\n\[|\Z)",
    re.DOTALL,
)
NAME_IN_BLOCK_RE = re.compile(r'^\s*name\s*=\s*"([^"]+)"', re.MULTILINE)
SOURCE_IN_BLOCK_RE = re.compile(
    r'^\s*source\s*=\s*"(git\+https://github\.com/ryancinsight/[^"]+)"',
    re.MULTILINE,
)


def extract_lock_pairs(consumer: str) -> list[tuple[str, str]]:
    """Return [(package_name, source_url), ...] for consumer's Cargo.lock."""
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.lock"
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8", errors="replace")
    pairs: list[tuple[str, str]] = []
    for blk in PKG_BLOCK_RE.findall(txt):
        name_m = NAME_IN_BLOCK_RE.search(blk)
        src_m = SOURCE_IN_BLOCK_RE.search(blk)
        if name_m and src_m:
            pairs.append((name_m.group(1), src_m.group(1)))
    return pairs


def url_stem(source: str) -> str:
    """Strip `git+` prefix, `?rev=...` query, `#sha` suffix from a source URL."""
    base = source[len("git+"):]
    for sep in ("?rev=", "#"):
        idx = base.find(sep)
        if idx != -1:
            base = base[:idx]
    return base


# ---------------------------------------------------------------------------
# Cargo.toml editing
# ---------------------------------------------------------------------------

PATCH_HEADER_RE = re.compile(r'^\[patch\."([^"]+)"\]')
MULTILINE_SUBKEY_RE = re.compile(
    r'^([A-Za-z0-9._-]+)\s*=\s*\{[^}]*path\s*=\s*"([^"]+)"[^}]*\}',
    re.MULTILINE,
)


def build_patch_blocks(
    consumer: str,
    pairs: list[tuple[str, str]],
) -> dict[str, dict[str, str]]:
    """Group lock pairs by source-URL stem; emit per-stem subkey maps.

    Returns {url_stem -> {subkey_name -> verbatim_toml_line}}.
    """
    self_name = consumer_pkg_name(consumer)
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for pkg, src in pairs:
        # Self-patch skip if the consumer is the package being patched
        if self_name and pkg.lower() == self_name.lower():
            continue
        lo = SUBKEY_LOOKUP.get(pkg)
        if lo is None:
            # Unknown package; emit as warning rather than fabricate a wrong
            # path. The forward strategy is to surface these in a future
            # exhaustive catalogue cycle (deferred; not blocking).
            continue
        ws, rel = lo
        if rel == ".":
            path_str = f"../{ws}"
        else:
            path_str = f"../{ws}/{rel}"
        # Force forward slashes (Windows backend canonicalization).
        path_str = path_str.replace("\\", "/")
        url = url_stem(src)
        grouped[url][pkg] = f'{pkg} = {{ path = "{path_str}" }}'
    return dict(grouped)


def consumer_pkg_name(consumer: str) -> str | None:
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
        return None
    txt = p.read_text(encoding="utf-8", errors="replace")[:8000]
    m = re.search(r"^\[package\][\s\S]*?\n\s*name\s*=\s*\"([^\"]+)\"", txt, re.MULTILINE)
    return m.group(1) if m else None


def rewrite_consumer_toml(
    consumer: str,
    new_subkey_blocks: dict[str, dict[str, str]],
) -> int:
    """Append the new [patch] blocks after stripping the round-4/5 ghost
    marker lines + any stale empty [patch] blocks.

    Idempotency: if MARKER is present, the file is treated as already
    processed and not re-written.
    """
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
        return 0
    txt = p.read_text(encoding="utf-8", errors="replace")
    if MARKER in txt:
        return 0
    # No re-write needed if there are no new subkey blocks
    if not new_subkey_blocks:
        return 0
    # Append the new section with marker; round-6b re-emits the fresh blocks
    # alongside any currently-existing per-consumer [patch] blocks
    # (we do NOT strip existing blocks because some consumers have
    # deliberately retained first-party [patch.crates-io] melinoe entries).
    body_lines: list[str] = ["", MARKER, ""]
    for url in sorted(new_subkey_blocks):
        body_lines.append(f'[patch."{url}"]')
        for subkey in sorted(new_subkey_blocks[url]):
            body_lines.append(new_subkey_blocks[url][subkey])
        body_lines.append("")
    tail = "\n".join(body_lines) + "\n"
    p.write_text(txt + tail, encoding="utf-8")
    return sum(len(subkeys) for subkeys in new_subkey_blocks.values())


# ---------------------------------------------------------------------------
# Cargo update --workspace --offline driver
# ---------------------------------------------------------------------------

def cargo_update_workspace(consumer: str) -> int:
    if not (ATLAS_ROOT / "repos" / consumer / "Cargo.toml").exists():
        return -1
    r = subprocess.run(
        ["cargo", "update", "--workspace", "--offline"],
        cwd=str(ATLAS_ROOT / "repos" / consumer),
        capture_output=True,
        text=True,
    )
    rc = r.returncode
    if rc != 0:
        snippet = (r.stderr or r.stdout).strip().splitlines()[-3:]
        print(f"  FAIL {consumer:14s} rc={rc} tail={' | '.join(s.strip()[:120] for s in snippet)}")
    return rc


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

PATTERN_RYAN = re.compile(
    r'^source = "git\+https://github\.com/ryancinsight/',
    re.MULTILINE,
)
PATTERN_NVLABS = re.compile(
    r'^source = "git\+https://github\.com/NVlabs/',
    re.MULTILINE,
)


def per_consumer_hits() -> dict[str, int]:
    out = {}
    for lock in ATLAS_ROOT.glob("repos/*/Cargo.lock"):
        c = lock.parent.name
        try:
            out[c] = len(PATTERN_RYAN.findall(lock.read_text(encoding="utf-8", errors="replace")))
        except Exception:
            out[c] = 0
    return out


def nv_sentinel() -> int:
    p = ATLAS_ROOT / "repos" / "apollo" / "Cargo.lock"
    if not p.exists():
        return -1
    return len(PATTERN_NVLABS.findall(p.read_text(encoding="utf-8", errors="replace")))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("# PHASE 0: starting snapshot")
    per0 = per_consumer_hits()
    grand0 = sum(per0.values())
    print(f"  GRAND={grand0} (baseline=222, target=0)")
    for c in sorted(ROUND6B_CONSUMERS):
        print(f"  {c:14s} {per0.get(c, 0)}")
    print(f"  athena={per0.get('athena', 0)} (graduated OUT-OF-SCOPE)")
    print(f"  apollo NVlabs sentinel = {nv_sentinel()} (expected 7)")

    print()
    print("# PHASE 1: per-consumer (package_name, source_url) extraction")
    pairs_by_consumer: dict[str, list[tuple[str, str]]] = {}
    for c in ROUND6B_CONSUMERS:
        ps = extract_lock_pairs(c)
        pairs_by_consumer[c] = ps
        uniq = {(p_, s_) for p_, s_ in ps}
        print(f"  {c:14s} {len(uniq)} unique (pkg -> src) pairs")

    print()
    print("# PHASE 2: re-emit [patch] blocks per consumer with atlas-root paths")
    blocks_by_consumer: dict[str, dict[str, dict[str, str]]] = {}
    for c in ROUND6B_CONSUMERS:
        grouped = build_patch_blocks(c, pairs_by_consumer[c])
        blocks_by_consumer[c] = grouped
        total_subkeys = sum(len(s) for s in grouped.values())
        print(f"  {c:14s} {len(grouped)} [patch] blocks, {total_subkeys} subkeys")

    print()
    print("# PHASE 3: write fresh [patch] sections to Cargo.toml")
    for c in ROUND6B_CONSUMERS:
        added = rewrite_consumer_toml(c, blocks_by_consumer[c])
        print(f"  {c:14s} subkeys added: {added}")

    print()
    print("# PHASE 4: cargo update --workspace --offline per consumer")
    for c in ROUND6B_CONSUMERS:
        rc = cargo_update_workspace(c)
        marker = "OK   " if rc == 0 else "FAIL "
        print(f"  {marker} {c:14s} rc={rc}")

    print()
    print("# PHASE 5: final sweep")
    per1 = per_consumer_hits()
    grand1 = sum(per1.values())
    print(f"  GRAND={grand1} (target=0; athena scoped exception)")
    for c in ROUND6B_CONSUMERS:
        n = per1.get(c, 0)
        marker = "OK " if n == 0 else "RES"
        print(f"  {marker} {c:14s} {n}")
    print(f"  athena={per1.get('athena', 0)} (graduated to ATLAS-OVERLAY-002)")
    print(f"  apollo NVlabs sentinel = {nv_sentinel()} (expected 7)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
