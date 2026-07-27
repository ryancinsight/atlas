"""ATLAS-PATH-DEP-AUDIT-2 closure round-4 (precision aggregator).

Round-3 reduced 222 -> 181 hits but logged 'pkgs=0' because it full-workspace-
populated [patch] blocks and the existing round-1/2 blocks were already present.
Round-4 extracts each (package_name, source_url) pair directly from each
consumer's Cargo.lock and emits ONLY the subkeys actually required, which lets
`cargo update --workspace --offline` settle residual hashes per consumer.

Key differences vs round-3:

  * Cargo.lock parsing is precise: regex over `[[package]]` blocks correlates
    `name = "X"` with the first `source = "..."` line that follows. Every pair
    contributes exactly one subkey.
  * Self-patch prohibition operates on the resolved subkey NAME (not the URL
    stem), so an apollo consumer can keep `apollo-fft` subkeys (different from
    `apollo-czt`, etc.).
  * Self-patch check ignores the consumer's own top-level package name only.
  * Existing [patch] blocks are READ ONCE then RE-WRITTEN with survivors +
    newly-emitted subkeys in canonical order (no double `[patch."X"]` headers).
  * Per-consumer `cargo update --workspace --offline` (not `cargo update -p`)
    to let cargo process the merged [patch] block without re-running on
    unrelated siblings.
"""
from __future__ import annotations

import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ATLAS_ROOT = Path(r"D:\atlas")

# --- Workspace registry (carried over from r3, kept tight) -----------------

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

SINGLE_PACKAGES: dict[str, str] = {
    "aequitas": ".",
    "harmonia": ".",
    "horae": ".",
    "iris": ".",
    "themis": ".",
}


# Reverse lookup: subkey -> (workspace_alias, relative subcrate path)
SUBKEY_LOOKUP: dict[str, tuple[str, str]] = {}
for _ws, _subs in WORKSPACES.items():
    for _name, _path in _subs.items():
        SUBKEY_LOOKUP[_name] = (_ws, _path)
for _ws, _path in SINGLE_PACKAGES.items():
    SUBKEY_LOOKUP[_ws] = (_ws, _path)

CONSUMERS = [
    "apollo", "athena", "gaia", "hermes",
    "CFDrs", "asclepius", "coeus", "helios",
    "hephaestus", "kwavers", "leoneuro-rs", "ritk",
]

# Url variant map produced from each catalog target URL stem
def url_variants(stem: str) -> list[str]:
    """Returns url-stems suitable for `[patch."<url>"]` header keying.

    Includes the original-stemmed case, lower-cased, with-and-without `.git`.
    """
    lower = stem.lower()
    seen = []
    for v in [stem, lower, stem + ".git", lower + ".git"]:
        if v not in seen:
            seen.append(v)
    return seen


# --- Cargo.lock parsing ----------------------------------------------------

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
    """Return [(package_name, source_url), ...] for consumer's Cargo.lock.

    Reads each `[[package]]` block as a unit and joins name + source on the
    same block. This guarantees correctness even when source lines wrap or
    the lock is large.
    """
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.lock"
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8", errors="replace")
    pairs: list[tuple[str, str]] = []
    for blk in PKG_BLOCK_RE.findall(txt):
        name_m = NAME_IN_BLOCK_RE.search(blk)
        src_m = SOURCE_IN_BLOCK_RE.search(blk)
        if not (name_m and src_m):
            continue
        pairs.append((name_m.group(1), src_m.group(1)))
    return pairs


# --- Cargo.toml editing ----------------------------------------------------

PATCH_HEADER_RE = re.compile(r'^\[patch\."([^"]+)"\]')
NAME_EQ_PATH_BARE_RE = re.compile(r'^([A-Za-z0-9._-]+)\s*=\s*\{\s*path\s*=\s*"[^"]+"\s*\}')
MARKER = "# ATLAS-PATH-DEP-AUDIT-2 round-4 closure"


def url_from_source_line(src: str) -> str:
    """Strip `git+` prefix and any `?rev=...#sha` suffix from a source line."""
    if not src.startswith("git+"):
        return src
    base = src[len("git+"):]
    for sep in ("?rev=", "#"):
        idx = base.find(sep)
        if idx != -1:
            base = base[:idx]
    return base


def consumer_pkg_name(consumer: str) -> str | None:
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
        return None
    txt = p.read_text(encoding="utf-8", errors="replace")[:8000]
    m = re.search(r"^\[package\][\s\S]*?\n\s*name\s*=\s*\"([^\"]+)\"", txt, re.MULTILINE)
    return m.group(1) if m else None


def parse_existing_patch_blocks(toml: str) -> list[tuple[str, dict[str, str]]]:
    """Return [ (url_header, {subkey_name -> verbatim_line}) ] preserving order."""
    out: list[tuple[str, dict[str, str]]] = []
    cur: tuple[str, dict[str, str]] | None = None
    for line in toml.splitlines():
        m = PATCH_HEADER_RE.match(line.strip())
        if m:
            if cur is not None:
                out.append(cur)
            cur = (m.group(1), {})
            continue
        if cur is None:
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        nm = NAME_EQ_PATH_BARE_RE.match(line)
        if nm:
            cur[1][nm.group(1)] = line
    if cur is not None:
        out.append(cur)
    return out


def rewrite_with_merged_blocks(
    consumer: str,
    needed: dict[str, dict[str, str]],
) -> tuple[int, int]:
    """Replace/append [patch] blocks per URL with merged subkeys.

    `needed[url_header][subkey_name] = path_assign_line` is the canonical map.
    Returns (added_subkeys, kept_subkeys).
    """
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
        return 0, 0
    txt = p.read_text(encoding="utf-8", errors="replace")
    if MARKER in txt:
        # idempotent: count existing subkeys but do not re-emit
        existing = parse_existing_patch_blocks(txt)
        kept = sum(len(subs) for _, subs in existing)
        return 0, kept

    existing = parse_existing_patch_blocks(txt)
    survivor: dict[str, dict[str, str]] = {}
    for url, subs in existing:
        survivor[url] = subs

    added = 0
    kept = 0
    new_blocks: list[str] = []
    for url_h, sub_lines in needed.items():
        existing_subs = survivor.get(url_h, {})
        merged = dict(existing_subs)
        for sub_name, line in sub_lines.items():
            if sub_name in merged:
                # Potential fix-up: ensure path is present and correct
                new_line = line
                if merged[sub_name] == new_line:
                    kept += 1
                else:
                    merged[sub_name] = new_line
                    added += 1
            else:
                merged[sub_name] = line
                added += 1
        if merged != existing_subs:
            survivor[url_h] = merged

    # Compose replacement block list (any URL with at least one subkey)
    final_blocks: list[str] = []
    seen_urls: set[str] = set()
    for url, subs in survivor.items():
        if not subs:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        final_blocks.append(f'[patch."{url}"]')
        for sub_name in sorted(subs):
            final_blocks.append(subs[sub_name])

    if not final_blocks:
        return 0, kept

    # Strip any existing [patch] sections from text (we'll re-emit canonically)
    cleaned_lines: list[str] = []
    i = 0
    lines = txt.splitlines()
    while i < len(lines):
        line = lines[i]
        if PATCH_HEADER_RE.match(line.strip()):
            # Skip until next non-continuation (next top-level [ or end)
            i += 1
            while i < len(lines):
                inner = lines[i]
                if inner.strip() == "":
                    i += 1
                    continue
                if inner.startswith("["):
                    break
                i += 1
            continue
        cleaned_lines.append(line)
        i += 1

    cleaned = "\n".join(cleaned_lines).rstrip() + "\n"
    out = cleaned + "\n" + MARKER + "\n" + "\n".join(final_blocks) + "\n"
    p.write_text(out, encoding="utf-8")
    return added, kept


# --- Cargo driver ----------------------------------------------------------

def cargo_update_workspace(consumer: str) -> int:
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
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


# --- Sweep -----------------------------------------------------------------

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


def per_consumer_hits() -> dict[str, int]:
    out = {}
    for lock in ATLAS_ROOT.glob("repos/*/Cargo.lock"):
        c = lock.parent.name
        out[c] = len(PATTERN.findall(lock.read_text(encoding="utf-8", errors="replace")))
    return out


# --- Main ------------------------------------------------------------------

def main() -> int:
    print("# PHASE 0: starting grand-total snapshot")
    base = grand_total_hits()
    per = per_consumer_hits()
    print(f"  GRAND={base}")
    for c, n in sorted(per.items(), key=lambda kv: -kv[1]):
        if n == 0:
            continue
        print(f"  {c:16s} {n}")

    print()
    print("# PHASE 1: per-consumer (package_name, source_url) extraction")
    pairs_by_consumer: dict[str, list[tuple[str, str]]] = {}
    for c in CONSUMERS:
        ps = extract_lock_pairs(c)
        pairs_by_consumer[c] = ps
        # collapse to (pkg_name -> source_url) unique
        uniq: dict[str, str] = {}
        for n_, s_ in ps:
            uniq.setdefault(n_, s_)
        print(f"  {c:16s} {len(uniq)} unique (pkg -> src) pairs")

    print()
    print("# PHASE 2: build + rewrite [patch] blocks per consumer")
    self_patch_total = 0
    unk_total = 0
    for c in CONSUMERS:
        self_name = consumer_pkg_name(c)
        uniq: dict[str, str] = {}
        for n_, s_ in pairs_by_consumer[c]:
            uniq.setdefault(n_, s_)
        needed: dict[str, dict[str, str]] = {}
        self_count = 0
        unk_count = 0
        for pkg_name, src in uniq.items():
            if self_name and pkg_name.lower() == self_name.lower():
                self_count += 1
                continue
            lo = SUBKEY_LOOKUP.get(pkg_name)
            if lo is None:
                # We could still derive: the package name itself ('apollo-czt')
                # Don't auto-derive when package_name is bare 'apollo'.
                unk_count += 1
                continue
            ws, rel = lo
            url_h = url_from_source_line(src)
            sub_line = f'{pkg_name} = {{ path = "../{ws}/{rel}" }}' if rel != "." else f'{pkg_name} = {{ path = "../{ws}" }}'
            needed.setdefault(url_h, {})[pkg_name] = sub_line
        added, kept = rewrite_with_merged_blocks(c, needed)
        self_patch_total += self_count
        unk_total += unk_count
        print(f"  {c:16s} added={added} kept={kept} self-patch-skipped={self_count} unknown-pkg={unk_count} blocks={len(needed)}")

    print()
    print("# PHASE 3: cargo update --workspace --offline per consumer")
    rc_total = 0
    for c in CONSUMERS:
        rc = cargo_update_workspace(c)
        rc_total += max(rc, 0)

    print()
    print("# PHASE 4: final grand-totals sweep")
    final = grand_total_hits()
    per_final = per_consumer_hits()
    print(f"  GRAND={final} (baseline={base}, target=0, sentinel=0)")
    for c, n in sorted(per_final.items(), key=lambda kv: -kv[1]):
        if n == 0:
            continue
        print(f"  {c:16s} {n}")

    return 0 if final == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
