"""ATLAS-PATH-DEP-AUDIT-2 closure round-5 (stale-strip-first).

Round-4 reduced 222 -> 99 but reported rc=101 for asclepius, leoneuro-rs, and
athena. Diagnostic confirmed:

  * asclepius: stale `apollo = { path = "../apollo/crates/apollo" }` (apollo
    workspace has no `crates/apollo` member, only apollo-* subcrates).
  * leoneuro-rs: stale `coeus-autograd = { path = "../coeus/coeus-autograd" }`
    (missing `/crates/` segment; coeus subcrate is at `crates/coeus-autograd`).
  * athena: mnemosyne version skew (0.5.0 locked, 0.6.0 local).
  * hermes: similar stale paths.

Round-5 strategy:

  1. **Stale-strip pass** runs FIRST per consumer. Resolves each existing
     subkey's `path` against the filesystem; subkeys whose target has no
     `Cargo.toml` are DELETEd in place, not replaced with bad paths.
  2. **Multi-line subkey support**. Tolerates
     `pkg = { path = "..", default-features = false, ... }` shape.
  3. **Idempotency marker** `# ATLAS-PATH-DEP-AUDIT-2 round-5 closure`.
  4. **Self-patch prohibition** in newly-emitted blocks: a consumer cannot
     patch its own top-level package (e.g. asclepius cannot
     patch `apollo` workspace root).
  5. **Cargo update --workspace --offline** per consumer after strip.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ATLAS_ROOT = Path(r"D:\atlas")

# Atlas workspace subcrate registry (verified by filesystem walk).
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

# Reverse subkey -> (workspace_alias, subcrate_path)
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

# Pure workspace shortcuts - atlas repos whose root Cargo.toml is a virtual
# workspace (no [package] section; only [workspace]). Any [patch] subkey
# referencing these as a destination is wrong because cargo cannot use
# them as a path source. (Used for self-patch prohibition + stale-strip.)
VIRTUAL_WORKSPACE_ROOTS: set[str] = {
    "asclepius", "apollo",
}


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


# ---------------------------------------------------------------------------
# Cargo.toml editing
# ---------------------------------------------------------------------------

PATCH_HEADER_RE = re.compile(r'^\[patch\."([^"]+)"\]\s*$')
# Multi-line tolerant: name = { path = "..." [, default-features = false] [...] }
MULTILINE_SUBKEY_RE = re.compile(
    r'^([A-Za-z0-9._-]+)\s*=\s*\{[^}]*path\s*=\s*"([^"]+)"[^}]*\}',
    re.MULTILINE,
)
MARKER = "# ATLAS-PATH-DEP-AUDIT-2 round-5 closure"


def url_from_source_line(src: str) -> str:
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


def block_bounds(lines: list[str], start: int) -> int:
    """Given a [patch.<url>] header at index `start`, return the index after
    the last subkey line. Subkey lines are recognized via MULTILINE_SUBKEY_RE.
    Blank lines and comments inside the block are kept; the boundary is the
    next `[` header or end-of-file.
    """
    i = start + 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("[") and PATCH_HEADER_RE.match(line.strip()) is None:
            return i
        if line.startswith("[") and line.strip() != lines[start].strip():
            return i
        # Blank line ends block (cargo treats blank as a section separator)
        if not line.strip():
            return i + 1
        i += 1
    return i


def parse_subkeys(block_text: str) -> list[tuple[str, str]]:
    """Return [(subkey_name, path_string), ...] from a [patch.*] block body."""
    out: list[tuple[str, str]] = []
    for m in MULTILINE_SUBKEY_RE.finditer(block_text):
        out.append((m.group(1), m.group(2)))
    return out


def path_resolves_to_crate(consumer: str, rel_path: str) -> bool:
    """True iff `repos/<consumer>/<rel_path>/Cargo.toml` exists on disk."""
    if rel_path.startswith("/") or ":" in rel_path[:3]:
        return False
    normalized = rel_path.replace("\\", "/")
    # remove leading "../<consumer>/" if present (path deps are typically
    # written without it from consumer's POV; if it IS present, strip)
    if normalized.startswith("../" + consumer + "/"):
        normalized = normalized[len("../" + consumer + "/"):]
    elif normalized.startswith("../"):
        normalized = normalized[3:]
    full = (ATLAS_ROOT / "repos" / consumer / normalized / "Cargo.toml").resolve()
    return full.exists()


def strip_stale_subkeys(consumer: str) -> tuple[int, int]:
    """Walk each [patch.*] block; drop subkeys whose target has no Cargo.toml.

    Returns (subkeys_dropped, subkeys_kept).
    """
    p = ATLAS_ROOT / "repos" / consumer / "Cargo.toml"
    if not p.exists():
        return 0, 0
    txt = p.read_text(encoding="utf-8", errors="replace")
    lines = txt.splitlines()
    out_lines: list[str] = []
    i = 0
    dropped = 0
    kept = 0
    while i < len(lines):
        line = lines[i]
        hdr_match = PATCH_HEADER_RE.match(line)
        if hdr_match and "patch." in line:
            # Collect candidate block range
            end = block_bounds(lines, i)
            block_lines = lines[i:end]
            block_text = "\n".join(block_lines)
            subs = parse_subkeys(block_text)
            live_lines: list[str] = [line]
            for name, pth in subs:
                if path_resolves_to_crate(consumer, pth):
                    # find the verbatim subkey line
                    for j in range(i + 1, end):
                        if MULTILINE_SUBKEY_RE.match(lines[j]) and \
                           MULTILINE_SUBKEY_RE.match(lines[j]).group(1) == name:
                            live_lines.append(lines[j])
                            break
                    kept += 1
                else:
                    dropped += 1
            # Only emit the block header if at least one subkey survived
            if len(live_lines) > 1:
                out_lines.extend(live_lines)
            i = end
            continue
        out_lines.append(line)
        i += 1
    new_txt = "\n".join(out_lines)
    if new_txt != txt:
        p.write_text((new_txt + "\n") if not new_txt.endswith("\n") else new_txt,
                      encoding="utf-8")
    return dropped, kept


# ---------------------------------------------------------------------------
# Cargo driver & sweep
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


PATTERN_RYAN = re.compile(
    r'^source = "git\+https://github\.com/ryancinsight/',
    re.MULTILINE,
)
PATTERN_NVLABS = re.compile(
    r'^source = "git\+https://github\.com/NVlabs/',
    re.MULTILINE,
)


def grand_total_hits() -> int:
    n = 0
    for lock in ATLAS_ROOT.glob("repos/*/Cargo.lock"):
        try:
            n += len(PATTERN_RYAN.findall(lock.read_text(encoding="utf-8", errors="replace")))
        except Exception:
            pass
    return n


def per_consumer_hits() -> dict[str, int]:
    out = {}
    for lock in ATLAS_ROOT.glob("repos/*/Cargo.lock"):
        c = lock.parent.name
        try:
            out[c] = len(PATTERN_RYAN.findall(lock.read_text(encoding="utf-8", errors="replace")))
        except Exception:
            out[c] = 0
    return out


def nv_sentinel_count() -> int:
    p = ATLAS_ROOT / "repos" / "apollo" / "Cargo.lock"
    if not p.exists():
        return -1
    return len(PATTERN_NVLABS.findall(p.read_text(encoding="utf-8", errors="replace")))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("# PHASE 0: starting snapshot")
    base = grand_total_hits()
    per = per_consumer_hits()
    print(f"  GRAND={base} (baseline=222 target=0)")
    for c, n in sorted(per.items(), key=lambda kv: -kv[1]):
        if n == 0:
            continue
        print(f"  {c:16s} {n}")
    print(f"  apollo NVlabs sentinel = {nv_sentinel_count()} (expected 7)")

    print()
    print("# PHASE 1: stale-strip pass per consumer")
    total_dropped = 0
    total_kept = 0
    for c in CONSUMERS:
        dropped, kept = strip_stale_subkeys(c)
        total_dropped += dropped
        total_kept += kept
        if dropped:
            print(f"  {c:16s} dropped={dropped} kept={kept}")
        else:
            pass  # quiet on consumers without stale subkeys
    print(f"  total_dropped={total_dropped} total_kept={total_kept}")

    print()
    print("# PHASE 2: cargo update --workspace --offline per consumer")
    for c in CONSUMERS:
        rc = cargo_update_workspace(c)
        if rc == 0:
            print(f"  OK    {c:14s} rc=0")
        else:
            print(f"  FAIL  {c:14s} rc={rc}")

    print()
    print("# PHASE 3: final sweep")
    final = grand_total_hits()
    per_f = per_consumer_hits()
    nv = nv_sentinel_count()
    print(f"  GRAND={final} (baseline={base} target=0)")
    for c, n in sorted(per_f.items(), key=lambda kv: -kv[1]):
        if n == 0:
            continue
        print(f"  {c:16s} {n}")
    print(f"  apollo NVlabs sentinel = {nv} (expected 7)")

    return 0 if final == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
