"""ATLAS-PATH-DEP-AUDIT-2 closure round-6a (atlas-root corrective re-emit).

Round-5's stale-strip pass over-stripped ~669 valid `[patch]` subkeys because
its `path_resolves_to_crate` consumer misread `../<sibling>/<sub>` as
`repos/<consumer>/<sibling>/<sub>/Cargo.toml` (consumer-relative, wrong).
Cargo-canonical semantics resolve `../<sibling>/<sub>` relative to the
manifest's directory, so `D:/atlas/repos/cfdrs/Cargo.toml` referencing
`../moirai/moirai-core` correctly resolves to `D:/atlas/repos/moirai/moirai-core`.

Round-6a uses the user-specified verification:

    full = Path('D:/atlas/repos/' + consumer) / path / 'Cargo.toml'
    full.resolve()

…to emit correctly-anchored subkeys for every consumer that ever carried
audit-format hits (13+1 consumers). Includes athena + hephaestus: their
residuals currently sit in PATH_DEP_AUDIT_2_ENTRY.md's
"scope-defined exceptions" table, but the underlying r5-over-strip silent-
fixation applies there too. Round-6a re-emit lifts them out of the
exception framework unless cargo-update's per-package ++ re-resolution
genuinely cannot resolve (e.g. version skew).

Iteration loop:
  For each of MAX_ITERATIONS rounds, per consumer:
    1. Re-parse Cargo.lock for (pkg, source_url) pairs.
    2. Build `[patch."<url>"]` subkey blocks, anchored at atlas-root
       (Path-based verification). Self-patch skip + heuristic
       single-crate fallback for unmapped package names.
    3. Re-emit fresh blocks at end of Cargo.toml, below a hard
       `# ATLAS-PATH-DEP-AUDIT-2 round-6a closure` marker; strip
       any prior r6a section so identity is preserved across runs
       (carrier-state writes only; pre-existing patches untouched).
    4. Per-package `cargo update -p <pkg> --offline` to force
       re-resolution of the locked git-source entries that the
       redirect hits.

Termination: residual audit hit count for the consumer is unchanged
across one iteration (stabilized) OR MAX_ITERATIONS reached.
"""
from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from pathlib import Path

ATLAS_ROOT = Path(r"D:\atlas")
MARKER = "# ATLAS-PATH-DEP-AUDIT-2 round-6a closure"
MAX_ITERATIONS = 3

# --- Workspace registry (carried over from r6b, kept tight) --------------

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

# Final constructs
SUBKEY_LOOKUP: dict[str, tuple[str, str]] = {}
for _ws, _subs in WORKSPACES.items():
    for _name, _path in _subs.items():
        SUBKEY_LOOKUP[_name] = (_ws, _path)
for _ws, _path in SINGLE_PACKAGES.items():
    SUBKEY_LOOKUP[_ws] = (_ws, _path)

# All consumers that ever carried audit-format hits during the cycle.
CONSUMERS = [
    # READY consumers with [patch] already in place
    "apollo",
    "asclepius",
    "CFDrs",
    "coeus",
    "gaia",
    "helios",
    "hephaestus",
    "kwavers",
    "leoneuro-rs",
    "ritk",
    # NEEDS consumers that received round-1 [patch] overlay
    "athena",
    "hermes",
]


# --- Cargo.lock parsing ---------------------------------------------------

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
    """Parse Cargo.lock [[package]] blocks correlating name + source per block."""
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
    """Strip `git+` prefix, `?rev=...` query, `#sha` suffix."""
    base = source[len("git+"):]
    for sep in ("?rev=", "#"):
        idx = base.find(sep)
        if idx != -1:
            base = base[:idx]
    return base


# --- Path resolution (atlas-root semantic) -------------------------------

def atlas_root_publish_path(consumer: str, path_str: str) -> Path:
    """Resolve the path string from the consumer's manifest to a canonical
    atlas-root absolute path, using Path.joinpath + resolve so cargo-canonical
    semantics are honoured.

    Example: atlas_root_publish_path('CFDrs', '../moirai/moirai-core')
             => D:\\atlas\\repos\\moirai\\moirai-core (canonical)
    """
    return (Path(f"D:/atlas/repos/{consumer}") / path_str).resolve()


def path_resolves_to_crate(consumer: str, path_str: str) -> bool:
    """True iff `<resolved>/Cargo.toml` exists.

    This is the round-5-bug-fix predicate: was mis-implemented as
    `repos/<consumer>/<normalised>/Cargo.toml`; correct semantic per cargo
    spec is the manifest-relative walk resolved at atlas-root."""
    full = atlas_root_publish_path(consumer, path_str) / "Cargo.toml"
    return full.exists()


def candidate_path_for(pkg_name: str) -> str | None:
    """Generate the TOML path-string candidate for a package name."""
    lo = SUBKEY_LOOKUP.get(pkg_name)
    if lo is not None:
        ws, rel = lo
        if rel == ".":
            return f"../{ws}"
        return f"../{ws}/{rel}"
    # Heuristic fallback: assume single-package at root for unmapped names.
    # This catches leoneuro-rs's `proteus`, `iris`, `tyche`, `consus`, etc.
    return f"../{pkg_name}"


def consumer_pkg_name(consumer: str) -> str | None:
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
        return None
    txt = p.read_text(encoding="utf-8", errors="replace")[:8000]
    m = re.search(r"^\[package\][\s\S]*?\n\s*name\s*=\s*\"([^\"]+)\"", txt, re.MULTILINE)
    return m.group(1) if m else None


def build_blocks(
    consumer: str,
    pairs: list[tuple[str, str]],
) -> tuple[dict[str, dict[str, str]], list[tuple[str, str]]]:
    """Group pairs by URL stem → emit per-pair subkeys with atlas-root
    verification. Returns (groups, skipped_unmapped_pairs).
    """
    self_name = consumer_pkg_name(consumer)
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    skipped: list[tuple[str, str]] = []
    for pkg, src in pairs:
        if self_name and pkg.lower() == self_name.lower():
            skipped.append((pkg, "self-patch"))
            continue
        path_str = candidate_path_for(pkg)
        if path_str is None:
            skipped.append((pkg, "no-candidate-path"))
            continue
        path_str = path_str.replace("\\", "/")
        if not path_resolves_to_crate(consumer, path_str):
            skipped.append((pkg, f"unresolved={path_str}"))
            continue
        url = url_stem(src)
        grouped[url][pkg] = f'{pkg} = {{ path = "{path_str}" }}'
    return dict(grouped), skipped


# --- Cargo.toml editing ---------------------------------------------------

def rewrite_consumer_toml(
    consumer: str,
    new_blocks: dict[str, dict[str, str]],
) -> int:
    """Append fresh `[patch."<url>"]` blocks below the round-6a marker.

    Marker-based identity: subsequent runs strip the prior round-6a section
    and replace it; pre-existing first-party `[patch.crates-io]` blocks
    above the marker are preserved untouched.

    Returns total subkeys emitted (for logging).
    """
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
        return 0
    if not new_blocks:
        return 0
    txt = p.read_text(encoding="utf-8", errors="replace")
    if MARKER in txt:
        idx = txt.find(MARKER)
        head = txt[:idx].rstrip() + "\n"
    else:
        head = txt.rstrip() + "\n"
    body_lines: list[str] = ["", MARKER, ""]
    for url in sorted(new_blocks):
        body_lines.append(f'[patch."{url}"]')
        for subkey in sorted(new_blocks[url]):
            body_lines.append(new_blocks[url][subkey])
        body_lines.append("")
    tail = "\n".join(body_lines) + "\n"
    p.write_text(head + tail, encoding="utf-8")
    return sum(len(s) for s in new_blocks.values())


# --- Cargo driver ---------------------------------------------------------

PATTERN_RYAN = re.compile(
    r'^source = "git\+https://github\.com/ryancinsight/',
    re.MULTILINE,
)


def cargo_count_residual(consumer: str) -> int:
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.lock"
    if not p.exists():
        return 0
    txt = p.read_text(encoding="utf-8", errors="replace")
    return len(PATTERN_RYAN.findall(txt))


def cargo_update_pkgs(consumer: str, pkgs: list[str]) -> int:
    """Per-package `cargo update -p <pkg> --offline` to force re-resolution."""
    if not pkgs:
        return 0
    cmd = ["cargo", "update"] + sum([["-p", p] for p in pkgs], []) + ["--offline"]
    r = subprocess.run(
        cmd,
        cwd=str(ATLAS_ROOT / "repos" / consumer),
        capture_output=True,
        text=True,
    )
    return r.returncode


# --- Iterate --------------------------------------------------------------

def process_consumer(consumer: str) -> list[str]:
    """Iteratively re-emit [patch] blocks + per-package cargo update until
    residual stabilizes OR MAX_ITERATIONS reached.
    """
    log: list[str] = []
    for it in range(1, MAX_ITERATIONS + 1):
        prev = cargo_count_residual(consumer)
        pairs = extract_lock_pairs(consumer)
        if not pairs:
            log.append(f"  iter {it}: 0 lockfile pairs; break (stable @ 0)")
            break
        grouped, skipped = build_blocks(consumer, pairs)
        added = rewrite_consumer_toml(consumer, grouped)
        all_pkgs = [p for url_block in grouped.values() for p in url_block]
        rc = cargo_update_pkgs(consumer, all_pkgs)
        new = cargo_count_residual(consumer)
        log.append(
            f"  iter {it}: pairs={len(pairs)} added={added} skipped={len(skipped)} "
            f"cargo={rc} residual {prev} -> {new}"
        )
        if new == prev:
            log.append(f"  stabilized @ residual={new}; break")
            break
    return log


# --- Sweep ----------------------------------------------------------------

ALL_AUDIT_CONSUMERS = [
    # R6a main loop
    "apollo",
    "asclepius",
    "CFDrs",
    "coeus",
    "gaia",
    "helios",
    "hephaestus",
    "kwavers",
    "leoneuro-rs",
    "ritk",
    "athena",
    "hermes",
    # Audit-wide, touched by [patch] mechanism indirectly
    "aequitas",
    "harmonia",
    "horae",
    "tyche",
    "themis",
    "mnemosyne",
    "moirai",
    "eunomia",
]


def grand_total_hits() -> int:
    n = 0
    for lock in ATLAS_ROOT.glob("repos/*/Cargo.lock"):
        try:
            n += len(PATTERN_RYAN.findall(lock.read_text(encoding="utf-8", errors="replace")))
        except Exception:
            pass
    return n


def main() -> int:
    print("# PHASE 0: starting snapshot")
    initial_per: dict[str, int] = {}
    initial_grand = 0
    for c in sorted(set(ALL_AUDIT_CONSUMERS + CONSUMERS)):
        n = cargo_count_residual(c)
        initial_per[c] = n
        initial_grand += n
    print(f"  GRAND={initial_grand} (target=0; sentinel=NVlabs/apollo)")
    for c, n in sorted(initial_per.items(), key=lambda kv: -kv[1]):
        if n > 0:
            print(f"  {c:18s} {n}")

    print()
    print("# PHASE 1: iterative r6a re-emit + per-package cargo update")
    for c in CONSUMERS:
        print(f"=== CONSUMER: {c} ===")
        for line in process_consumer(c):
            print(line)

    print()
    print("# PHASE 2: final atlas-wide sweep")
    final_per: dict[str, int] = {}
    final_grand = 0
    for c in sorted(set(ALL_AUDIT_CONSUMERS + CONSUMERS)):
        n = cargo_count_residual(c)
        final_per[c] = n
        final_grand += n
    print(f"  GRAND={final_grand} (target=0)")
    for c, n in sorted(final_per.items(), key=lambda kv: -kv[1]):
        if n > 0:
            print(f"  RES  {c:18s} {n}")
    nv = len(re.findall(
        r'^source = "git\+https://github\.com/NVlabs/',
        (ATLAS_ROOT / "repos" / "apollo" / "Cargo.lock").read_text(encoding="utf-8", errors="replace"),
        re.MULTILINE,
    ))
    print(f"  apollo NVlabs sentinel = {nv} (expected 7)")
    return 0 if final_grand <= nv else 1


if __name__ == "__main__":
    raise SystemExit(main())
