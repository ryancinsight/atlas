#!/usr/bin/env python3
"""
ATLAS-PATH-DEP-AUDIT-2 round-2 closure (READY side):

Appends targeted catalog-driven [patch] blocks to 8 READY consumer atlas
submodule Cargo.toml files based on the per-consumer residual audit-format
catalog. Single-crate siblings use `../<target>`; multi-crate workspaces
(apollo, athena, coeus, consus, hermes, hephaestus, leto, moirai, tyche)
use `../<target>/crates/<subcrate>` paths.

Catalog (from prior extraction):
- CFDrs:    Mnemosyne.git, Moirai.git, consus, consus.git, hermes.git, iris, melinoe.git
- asclepius: Coeus.git, Mnemosyne.git, Moirai.git, aequitas, apollo.git, eunomia,
             hermes.git, leto.git, melinoe.git, themis
- coeus:    Moirai.git
- helios:   eunomia.git, tyche
- hephaestus: Mnemosyne.git, Moirai.git, aequitas, eunomia, hermes.git, leto.git,
              melinoe.git, themis
- kwavers:  asclepius, consus, hyperion, iris, tyche
- leoneuro-rs: asclepius, consus, hyperion, iris, proteus, tyche
- ritk:     consus, iris

NEEDS consumers (apollo, athena, gaia, hermes) already have catalog-coverage
from the round-1 unified [patch] overlay; skip here.
"""

import os
import sys

ATLAS_ROOT = r"D:\atlas"

# Per-consumer catalog: list of (URL-suffix, package-subkey, path-string) tuples.
# For multi-crate workspaces, multiple subkeys per URL are emitted.
# Path form is determined by the sibling's directory structure:
#   - single-crate repo (aequitas, hyperion, iris, melinoe, proteus, themis, tyche):
#     `../<repo>` if root has [package], else `../<repo>/crates/<subcrate>`
#   - workspace repo (apollo, athena, coeus, consus, hermes, hephaestus, leto,
#     moirai, mnemosyne): `../<repo>/crates/<subcrate>` or `../<repo>/<subcrate>`

# Helper: standard URL suffixes (we cover both .git and no-.git variants for each)
def url_block(url_base, subkeys):
    """Emit one [patch.<url>] block with the given subkeys dict {pkg: path}."""
    lines = [f'[patch."https://github.com/ryancinsight/{url_base}"]']
    for pkg, path in subkeys.items():
        lines.append(f'{pkg} = {{ path = "{path}" }}')
    return "\n".join(lines) + "\n"

# Mappings: sibling -> { subkey: path }
PATHS = {
    # Single-crate repos
    "aequitas": {"aequitas": "../aequitas"},
    "hyperion": {"hyperion": "../hyperion"},
    "iris": {"iris": "../iris"},
    "melinoe": {"melinoe": "../melinoe"},
    "proteus": {"proteus": "../proteus"},
    "themis": {"themis": "../themis"},
    # Multi-crate workspaces
    "Mnemosyne.git": {pkg: f"../mnemosyne/crates/{pkg}" for pkg in [
        "mnemosyne", "mnemosyne-core", "mnemosyne-arena", "mnemosyne-backend",
        "mnemosyne-build-util", "mnemosyne-decay", "mnemosyne-hardened",
        "mnemosyne-heap", "mnemosyne-local", "mnemosyne-prof",
    ]},
    "mnemosyne.git": {pkg: f"../mnemosyne/crates/{pkg}" for pkg in [
        "mnemosyne", "mnemosyne-core", "mnemosyne-arena", "mnemosyne-backend",
        "mnemosyne-build-util", "mnemosyne-decay", "mnemosyne-hardened",
        "mnemosyne-heap", "mnemosyne-local", "mnemosyne-prof",
    ]},
    "Moirai.git": {pkg: f"../moirai/{pkg}" for pkg in [
        "moirai", "moirai-core", "moirai-executor", "moirai-scheduler",
        "moirai-sync", "moirai-async", "moirai-async-macros", "moirai-pal",
        "moirai-iter", "moirai-parallel", "moirai-transport", "moirai-utils",
        "moirai-gpu", "moirai-http", "moirai-metrics", "moirai-tls",
    ]},
    "moirai.git": {pkg: f"../moirai/{pkg}" for pkg in [
        "moirai", "moirai-core", "moirai-executor", "moirai-scheduler",
        "moirai-sync", "moirai-async", "moirai-async-macros", "moirai-pal",
        "moirai-iter", "moirai-parallel", "moirai-transport", "moirai-utils",
        "moirai-gpu", "moirai-http", "moirai-metrics", "moirai-tls",
    ]},
    "hermes.git": {pkg: f"../hermes/crates/{pkg}" for pkg in [
        "hermes-simd", "hermes-simd-core", "hermes-simd-intrinsics",
        "hermes-simd-macros", "hermes-simd-types",
    ]},
    "hermes": {pkg: f"../hermes/crates/{pkg}" for pkg in [
        "hermes-simd", "hermes-simd-core", "hermes-simd-intrinsics",
        "hermes-simd-macros", "hermes-simd-types",
    ]},
    "leto.git": {pkg: f"../leto/crates/{pkg}" for pkg in [
        "leto", "leto-ops", "leto-python",
    ]},
    "hephaestus.git": {pkg: f"../hephaestus/crates/{pkg}" for pkg in [
        "hephaestus-core", "hephaestus-cuda", "hephaestus-wgpu",
    ]},
    "consus": {pkg: f"../consus/crates/{pkg}" for pkg in [
        "consus-core", "consus-hdf5", "consus-io", "consus-zarr",
        "consus-compression", "consus-fits", "consus-netcdf", "consus-parquet",
        "consus-arrow", "consus-npy", "consus-mat", "consus-nwb",
        "consus-hdmf", "consus-onnx",
    ]},
    "consus.git": {pkg: f"../consus/crates/{pkg}" for pkg in [
        "consus-core", "consus-hdf5", "consus-io", "consus-zarr",
        "consus-compression", "consus-fits", "consus-netcdf", "consus-parquet",
        "consus-arrow", "consus-npy", "consus-mat", "consus-nwb",
        "consus-hdmf", "consus-onnx",
    ]},
    "asclepius": {
        "asclepius": "../asclepius/crates/asclepius",
        "asclepius-coeus": "../asclepius/crates/asclepius-coeus",
    },
    "asclepius.git": {
        "asclepius": "../asclepius/crates/asclepius",
        "asclepius-coeus": "../asclepius/crates/asclepius-coeus",
    },
    "apollo.git": {pkg: f"../apollo/crates/{pkg}" for pkg in [
        "apollo", "apollo-czt", "apollo-dctdst", "apollo-dht", "apollo-fft",
        "apollo-fft-macros", "apollo-bench", "apollo-frft", "apollo-fwht",
        "apollo-gft", "apollo-hilbert", "apollo-leto-interop", "apollo-mellin",
        "apollo-ntt", "apollo-nufft", "apollo-qft", "apollo-radon", "apollo-sdft",
        "apollo-sft", "apollo-sht", "apollo-stft", "apollo-validation",
        "apollo-wavelet",
    ]},
    "tyche": {
        "tyche": "../tyche/crates/tyche",
        "tyche-core": "../tyche/crates/tyche-core",
        "tyche-moirai": "../tyche/crates/tyche-moirai",
        "tyche-consus": "../tyche/crates/tyche-consus",
    },
    "tyche.git": {
        "tyche": "../tyche/crates/tyche",
        "tyche-core": "../tyche/crates/tyche-core",
        "tyche-moirai": "../tyche/crates/tyche-moirai",
        "tyche-consus": "../tyche/crates/tyche-consus",
    },
    "eunomia.git": {"eunomia": "../eunomia/crates/eunomia"},
    "eunomia": {"eunomia": "../eunomia/crates/eunomia"},
    "melinoe.git": {"melinoe": "../melinoe"},
    "melinoe": {"melinoe": "../melinoe"},
    "themis.git": {"themis": "../themis"},
    "themis": {"themis": "../themis"},
}

# Per-consumer catalog: list of URL-suffixes to add
CONSUMER_CATALOG = {
    "CFDrs": ["Mnemosyne.git", "Moirai.git", "consus", "consus.git", "hermes.git",
              "iris", "melinoe.git"],
    "asclepius": ["Coeus.git", "Mnemosyne.git", "Moirai.git", "aequitas",
                  "apollo.git", "eunomia", "hermes.git", "leto.git",
                  "melinoe.git", "themis"],
    "coeus": ["Moirai.git"],
    "helios": ["eunomia.git", "tyche"],
    "hephaestus": ["Mnemosyne.git", "Moirai.git", "aequitas", "eunomia",
                   "hermes.git", "leto.git", "melinoe.git", "themis"],
    "kwavers": ["asclepius", "consus", "hyperion", "iris", "tyche"],
    "leoneuro-rs": ["asclepius", "consus", "hyperion", "iris", "proteus",
                    "tyche"],
    "ritk": ["consus", "iris"],
}


def build_appendix(consumer):
    """Build the [patch] block appendix for a consumer from its catalog."""
    urls = CONSUMER_CATALOG.get(consumer, [])
    parts = [
        "",
        "# ATLAS-PATH-DEP-AUDIT-2 round-2 (2026-07-27): targeted catalog-driven",
        "# [patch] blocks per per-consumer audit-format residual. Each URL-suffix",
        "# appears once with the FULL subkey set for the sibling's workspace",
        "# members; cargo treats unused subkeys as warnings only.",
    ]
    for url_suffix in urls:
        if url_suffix not in PATHS:
            print(f"  WARN  no path mapping for {url_suffix} in {consumer}")
            continue
        parts.append("")
        parts.append(url_block(url_suffix, PATHS[url_suffix]))
    parts.append("")
    return "\n".join(parts)


def main() -> int:
    failures = []
    successes = []
    for consumer, _urls in CONSUMER_CATALOG.items():
        path = os.path.join(ATLAS_ROOT, "repos", consumer, "Cargo.toml")
        if not os.path.isfile(path):
            failures.append((consumer, "FILE_NOT_FOUND"))
            continue
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()
        # Check idempotency: if our marker is already present, skip.
        if "ATLAS-PATH-DEP-AUDIT-2 round-2" in original:
            print(f"  SKIP  {consumer} (already appended)")
            successes.append(consumer)
            continue
        appendix = build_appendix(consumer)
        with open(path, "a", encoding="utf-8") as f:
            f.write(appendix)
        successes.append(consumer)
        print(f"  OK    {consumer}")
    print()
    print(f"Result: {len(successes)}/{len(CONSUMER_CATALOG)} consumers patched")
    if failures:
        print(f"Failures: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())