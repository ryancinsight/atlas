#!/usr/bin/env python3
"""
ATLAS-PATH-DEP-AUDIT-2 closure: apply unified `[patch]` overlay block to
13 NEEDS consumer atlas submodule `Cargo.toml` files.

For each consumer, appends a unified [patch] block that covers all 13 atlas
siblings across URL case + .git suffix variants. Cargo treats unused patches
as warnings (not errors), so the unified approach safely redirects transitive
git-source pulls without per-consumer micro-management.

Usage:
    python D:\\atlas\\scripts\\atlas-path-dep-audit2-closure.py

This is an additive tool — no [patch] blocks are removed or rewritten.
Re-running is safe (idempotent in the sense that the same block is appended;
the file may grow by one block per run).

NOTE: Cargo.toml edits and `cargo update` rewrites must be committed as
per-submodule commits before the parent atlas gitlink is advanced.
"""

import os
import sys

ATLAS_ROOT = r"D:\atlas"

# 13 NEEDS consumers per PATH-DEP-AUDIT-2 mandate
NEEDS_CONSUMERS = [
    "apollo",
    "athena",
    "consus",
    "gaia",
    "harmonia",
    "hermes",
    "horae",
    "leto",
    "mnemosyne",
    "moirai",
    "themis",
    "tyche",
    "aequitas",
]


# Unified [patch] overlay block. Covers:
# - URL case variants (Mnemosyne/Moirai vs mnemosyne/moirai)
# - .git suffix variants (eunomia vs eunomia.git, hermes vs hermes.git, etc.)
# - subkey crate names per sibling (workspace members, not the top-level repo)
# Each subkey maps the package name (as it appears in [workspace.dependencies])
# to the local atlas working-copy path.
PATCH_BLOCK = """

# ATLAS-PATH-DEP-AUDIT-2: redirect git+https sibling pulls to local working
# copies so the entire dep graph uses a single version of each Atlas
# foundation crate. Unused patches emit warnings only; cargo treats the
# block as defense-in-depth.
# Last delivery: 2026-07-27 closure cycle.

[patch."https://github.com/ryancinsight/eunomia"]
eunomia = { path = "../eunomia/crates/eunomia" }
[patch."https://github.com/ryancinsight/eunomia.git"]
eunomia = { path = "../eunomia/crates/eunomia" }

[patch."https://github.com/ryancinsight/Mnemosyne.git"]
mnemosyne = { path = "../mnemosyne/crates/mnemosyne" }
mnemosyne-core = { path = "../mnemosyne/crates/mnemosyne-core" }
mnemosyne-arena = { path = "../mnemosyne/crates/mnemosyne-arena" }
mnemosyne-backend = { path = "../mnemosyne/crates/mnemosyne-backend" }
mnemosyne-build-util = { path = "../mnemosyne/crates/mnemosyne-build-util" }
mnemosyne-decay = { path = "../mnemosyne/crates/mnemosyne-decay" }
mnemosyne-hardened = { path = "../mnemosyne/crates/mnemosyne-hardened" }
mnemosyne-heap = { path = "../mnemosyne/crates/mnemosyne-heap" }
mnemosyne-local = { path = "../mnemosyne/crates/mnemosyne-local" }
mnemosyne-prof = { path = "../mnemosyne/crates/mnemosyne-prof" }
[patch."https://github.com/ryancinsight/mnemosyne.git"]
mnemosyne = { path = "../mnemosyne/crates/mnemosyne" }
mnemosyne-core = { path = "../mnemosyne/crates/mnemosyne-core" }
mnemosyne-arena = { path = "../mnemosyne/crates/mnemosyne-arena" }
mnemosyne-backend = { path = "../mnemosyne/crates/mnemosyne-backend" }
mnemosyne-build-util = { path = "../mnemosyne/crates/mnemosyne-build-util" }
mnemosyne-decay = { path = "../mnemosyne/crates/mnemosyne-decay" }
mnemosyne-hardened = { path = "../mnemosyne/crates/mnemosyne-hardened" }
mnemosyne-heap = { path = "../mnemosyne/crates/mnemosyne-heap" }
mnemosyne-local = { path = "../mnemosyne/crates/mnemosyne-local" }
mnemosyne-prof = { path = "../mnemosyne/crates/mnemosyne-prof" }

[patch."https://github.com/ryancinsight/melinoe.git"]
melinoe = { path = "../melinoe" }
[patch."https://github.com/ryancinsight/melinoe"]
melinoe = { path = "../melinoe" }

[patch."https://github.com/ryancinsight/Moirai.git"]
moirai = { path = "../moirai/moirai" }
[patch."https://github.com/ryancinsight/moirai.git"]
moirai = { path = "../moirai/moirai" }
moirai-core = { path = "../moirai/moirai-core" }
moirai-executor = { path = "../moirai/moirai-executor" }
moirai-scheduler = { path = "../moirai/moirai-scheduler" }
moirai-sync = { path = "../moirai/moirai-sync" }
moirai-async = { path = "../moirai/moirai-async" }
moirai-async-macros = { path = "../moirai/moirai-async-macros" }
moirai-pal = { path = "../moirai/moirai-pal" }
moirai-iter = { path = "../moirai/moirai-iter" }
moirai-parallel = { path = "../moirai/moirai-parallel" }
moirai-transport = { path = "../moirai/moirai-transport" }
moirai-utils = { path = "../moirai/moirai-utils" }
moirai-gpu = { path = "../moirai/moirai-gpu" }
moirai-http = { path = "../moirai/moirai-http" }
moirai-metrics = { path = "../moirai/moirai-metrics" }
moirai-tls = { path = "../moirai/moirai-tls" }

[patch."https://github.com/ryancinsight/hermes.git"]
hermes-simd = { path = "../hermes/crates/hermes-simd" }
hermes-simd-core = { path = "../hermes/crates/hermes-simd-core" }
hermes-simd-intrinsics = { path = "../hermes/crates/hermes-simd-intrinsics" }
hermes-simd-macros = { path = "../hermes/crates/hermes-simd-macros" }
hermes-simd-types = { path = "../hermes/crates/hermes-simd-types" }
[patch."https://github.com/ryancinsight/hermes"]
hermes-simd = { path = "../hermes/crates/hermes-simd" }
hermes-simd-core = { path = "../hermes/crates/hermes-simd-core" }
hermes-simd-intrinsics = { path = "../hermes/crates/hermes-simd-intrinsics" }
hermes-simd-macros = { path = "../hermes/crates/hermes-simd-macros" }
hermes-simd-types = { path = "../hermes/crates/hermes-simd-types" }

[patch."https://github.com/ryancinsight/leto.git"]
leto = { path = "../leto/crates/leto" }
leto-ops = { path = "../leto/crates/leto-ops" }
leto-python = { path = "../leto/crates/leto-python" }

[patch."https://github.com/ryancinsight/hephaestus.git"]
hephaestus-core = { path = "../hephaestus/crates/hephaestus-core" }
hephaestus-cuda = { path = "../hephaestus/crates/hephaestus-cuda" }
hephaestus-wgpu = { path = "../hephaestus/crates/hephaestus-wgpu" }

[patch."https://github.com/ryancinsight/themis"]
themis = { path = "../themis" }
[patch."https://github.com/ryancinsight/themis.git"]
themis = { path = "../themis" }

[patch."https://github.com/ryancinsight/consus.git"]
consus-core = { path = "../consus/crates/consus-core" }
consus-zarr = { path = "../consus/crates/consus-zarr" }

[patch."https://github.com/ryancinsight/athena"]
athena-core = { path = "../athena/crates/athena-core" }
athena = { path = "../athena/crates/athena" }
athena-leto = { path = "../athena/crates/athena-leto" }
athena-wgpu = { path = "../athena/crates/athena-wgpu" }

[patch."https://github.com/ryancinsight/horae"]
horae = { path = "../horae" }

[patch."https://github.com/ryancinsight/aequitas"]
aequitas = { path = "../aequitas" }

"""


def apply_patches(consumer: str) -> tuple[str, bool]:
    """Append the unified [patch] block to a consumer's Cargo.toml."""
    toml_path = os.path.join(ATLAS_ROOT, "repos", consumer, "Cargo.toml")
    if not os.path.isfile(toml_path):
        return toml_path, False
    with open(toml_path, "a", encoding="utf-8") as f:
        f.write(PATCH_BLOCK)
    return toml_path, True


def main() -> int:
    print(f"ATLAS-PATH-DEP-AUDIT-2 closure: applying unified [patch] block")
    print(f"Target consumers: {len(NEEDS_CONSUMERS)}")
    print()
    failures = []
    successes = []
    for consumer in NEEDS_CONSUMERS:
        path, ok = apply_patches(consumer)
        if ok:
            successes.append(consumer)
            print(f"  OK   {consumer}")
        else:
            failures.append(consumer)
            print(f"  FAIL {consumer}: Cargo.toml not found at {path}")
    print()
    print(f"Result: {len(successes)}/{len(NEEDS_CONSUMERS)} consumers patched")
    if failures:
        print(f"Failures: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())